#!/usr/bin/env python3
"""Bridge between a grill work item and the external backlog owned by backlogctl.

Every read and write goes through ``backlogctl --json``; the SQLite store is
never touched directly. Mutations are preview-first: nothing changes without an
explicit ``--apply``, which is the human confirmation the backlog contract
requires.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
SCHEMA = "grill-backlog/v1"
DEFAULT_DB = "~/.backlog/backlog.db"
CONTRACT_VERSION = "2"
CATEGORY = "general"
CRITICALITY = {"critical", "high", "medium", "low"}
DEFAULT_CRITICALITY = "medium"
DEFAULT_STATE = "open"
# ADR-0023 of this work item: a deferred decision is born ``in_progress`` because
# ``open -> done`` is not a legal transition, so an item created ``open`` could
# never reach ``done`` in one step and would force a fabricated intermediate.
STATE_TARGET = {"open": "in_progress", "resolved": "done", "superseded": "cancelled"}
# Measured exhaustively against backlogctl 2.4.0; the bridge never emits a
# destination outside this table.
LEGAL_TRANSITIONS = {
    "open": {"open", "in_progress", "cancelled"},
    "in_progress": {"open", "in_progress", "done", "cancelled"},
    "done": {"done", "merged"},
    "cancelled": {"open", "cancelled"},
    "merged": {"merged"},
}
BLOCK = re.compile(r"(?m)^##\s+(BL-\d{4})\s+—\s+(.+?)\s*$")
WORK_ID_MARKER = "grill-work-id"
BL_MARKER = "grill-bl"


def sibling(name: str) -> Any:
    """Load a sibling script by path so imports work under any loader."""
    path = HERE.with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"grill_sibling_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(name)
    module = importlib.util.module_from_spec(spec)
    # dataclass resolution looks the module up in sys.modules while the body runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def store_path(db: str | None) -> str:
    """Resolve the store a run targets, before anything can fail.

    Every envelope reports it, including the refusals, so an operator always
    knows which backlog was addressed even when the CLI is missing.
    """
    return str(Path(db or DEFAULT_DB).expanduser())


class BacklogUnavailable(RuntimeError):
    """backlogctl could not be resolved or answered outside its contract."""


def resolve_cli(tools: Any = None) -> tuple[str, Any]:
    dependencies = sibling("ensure_dependencies")
    tools = tools or dependencies.Toolchain()
    manifest = dependencies.load_manifest()
    entry = next((item for item in manifest["dependencies"] if item["id"] == "backlogctl"), None)
    if entry is None:
        raise BacklogUnavailable("backlogctl missing from the dependency manifest")
    location = dependencies.resolve_binary(entry, tools)
    if location is None:
        raise BacklogUnavailable("backlogctl not installed; install the backlog plugin")
    return location, tools


def call(cli: str, tools: Any, db: str, argv: list[str], *, timeout: int = 30) -> dict[str, Any]:
    command = [cli, "--json", *argv, "--db", db]
    code, output = tools.run(command, timeout=timeout)
    try:
        payload = json.loads(output.strip().splitlines()[-1]) if output.strip() else {}
    except (json.JSONDecodeError, IndexError):
        raise BacklogUnavailable(f"non-JSON answer from {' '.join(argv)}") from None
    if code != 0 or payload.get("result") != "ok" or payload.get("contract_version") != CONTRACT_VERSION:
        raise BacklogUnavailable(f"{' '.join(argv)}: {payload.get('error') or output.strip()[:200]}")
    return payload


def derive_identity(root: Path, taken: set[str]) -> tuple[str, str]:
    """Derive a stable backlog code from the repository name, avoiding collisions."""
    name = root.name
    letters = [part[0] for part in re.split(r"[^A-Za-z0-9]+", name) if part]
    code = "".join(letters).upper()[:3] or re.sub(r"[^A-Za-z0-9]", "", name).upper()[:3]
    code = (code + "XXX")[:3]
    if code not in taken:
        return code, name
    for suffix in range(1, 100):
        candidate = f"{code[:2]}{suffix}" if suffix < 10 else f"{code[:1]}{suffix}"
        if candidate not in taken:
            return candidate, name
    raise BacklogUnavailable("no free backlog code derived from the repository name")


def resolve_backlog(root: Path, cli: str, tools: Any, db: str, requested: str | None = None) -> dict[str, Any]:
    """Decide which backlog owns this repository.

    A repository name rarely matches the backlog code it inherited, so an
    explicit ``requested`` code wins over every derivation.
    """
    backlogs = call(cli, tools, db, ["backlog", "list"]).get("data") or []
    target = str(root)
    bound = next((item for item in backlogs if item.get("bound_path") == target), None)
    if bound is not None:
        if requested and bound["code"] != requested:
            raise BacklogUnavailable(f"{target} is already bound to {bound['code']}, not {requested}")
        return {"status": "BOUND", "code": bound["code"], "name": bound.get("name"), "bound_path": target}
    if requested:
        declared = next((item for item in backlogs if item.get("code") == requested), None)
        if declared is not None and declared.get("bound_path"):
            raise BacklogUnavailable(f"{requested} is already bound to {declared['bound_path']}")
        return {
            "status": "NEEDS-BIND" if declared is not None else "NEEDS-CREATE",
            "code": requested,
            "name": declared.get("name") if declared else root.name,
            "bound_path": target,
        }
    taken = {item.get("code") for item in backlogs if item.get("code")}
    unbound = next((item for item in backlogs if item.get("name") == root.name and not item.get("bound_path")), None)
    if unbound is not None:
        return {"status": "NEEDS-BIND", "code": unbound["code"], "name": unbound.get("name"), "bound_path": target}
    code, name = derive_identity(root, taken)
    return {"status": "NEEDS-CREATE", "code": code, "name": name, "bound_path": target}


def ensure_bind(root: Path, *, apply: bool = False, db: str | None = None, tools: Any = None,
                code: str | None = None) -> dict[str, Any]:
    store = store_path(db)
    cli, tools = resolve_cli(tools)
    resolution = resolve_backlog(root, cli, tools, store, code)
    payload = {"schema": SCHEMA, "db": store, "backlog": resolution, "changed": False}
    if resolution["status"] == "BOUND" or not apply:
        payload["verdict"] = "OK" if resolution["status"] == "BOUND" else "PREVIEW"
        return payload
    if resolution["status"] == "NEEDS-CREATE":
        call(cli, tools, store, ["backlog", "create", "--code", resolution["code"],
                                 "--name", resolution["name"], "--profile", "software"])
    call(cli, tools, store, ["backlog", "bind", "--code", resolution["code"], "--path", str(root)])
    payload["backlog"] = resolve_backlog(root, cli, tools, store, code)
    payload["changed"] = True
    payload["verdict"] = "APPLIED"
    return payload


def parse_deferred(path: Path) -> list[dict[str, str]]:
    """Read every BL block of one work item's DECISION-BACKLOG.md.

    State is carried out, never used to filter: mirroring only ``open`` blocks
    made the mirror useful exactly while the audit gate refused the phase, so
    a closed milestone had nothing left to mirror.
    """
    if not path.is_file():
        return []
    audit = sibling("audit_decisions")
    text = path.read_text(encoding="utf-8")
    matches = list(BLOCK.finditer(text))
    entries: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        values = audit.fields(text[match.end():end])
        entries.append({"id": match.group(1), "title": match.group(2), **values})
    return entries


def index_existing(existing: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Map (work_id, BL) to the item that already represents it.

    The store accepts duplicates without complaining, so this index is the only
    thing standing between a rerun and a second copy of every decision.
    """
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for item in existing:
        markers = dict(re.findall(rf"(?m)^({WORK_ID_MARKER}|{BL_MARKER}):\s*(.+)$", item.get("description") or ""))
        work_id, bl_id = markers.get(WORK_ID_MARKER), markers.get(BL_MARKER)
        if not (work_id and bl_id):
            continue
        key = (work_id.strip(), bl_id.strip())
        if key in index:
            # Duplicates predate this deduplication and the store never refused
            # them. Reconciling the first silently would hide the rest, so the
            # extra identities travel with the entry and surface in the report.
            index[key].setdefault("duplicates", []).append(item.get("id"))
            continue
        index[key] = dict(item)
    return index


def describe(entry: dict[str, str], work_id: str, root: Path) -> str:
    """Render the decision body, minus anything the item itself owns.

    ``state`` is deliberately excluded: the item's own status is the authority
    for it, and copying it into free text would freeze the value written at
    creation while transitions moved the real one, leaving the description
    asserting ``open`` on an item already ``done``.
    """
    body = "\n".join(f"- {key}: {value}" for key, value in entry.items() if key not in {"id", "title", "state"})
    return (f"{body}\n\n---\n{WORK_ID_MARKER}: {work_id}\n{BL_MARKER}: {entry['id']}\n"
            f"repo: {root}\norigem: grill-with-docs backlog-sync")


def sync_items(root: Path, work_item: Path, work_id: str, *, apply: bool = False,
               db: str | None = None, tools: Any = None) -> dict[str, Any]:
    store = store_path(db)
    cli, tools = resolve_cli(tools)
    resolution = resolve_backlog(root, cli, tools, store)
    if resolution["status"] != "BOUND":
        return {"schema": SCHEMA, "db": store, "verdict": "BLOCKED", "code": "BACKLOG-NOT-BOUND",
                "backlog": resolution, "changed": False}
    code = resolution["code"]
    entries = parse_deferred(work_item / "DECISION-BACKLOG.md")
    existing = call(cli, tools, store, ["item", "list", "--code", code]).get("data") or []
    known = index_existing(existing)
    # FR-014: the whole proposal set is computed before the first mutation, so
    # every precondition refusal happens with the backlog untouched.
    proposals: list[dict[str, Any]] = []
    for entry in entries:
        state = entry.get("state") or DEFAULT_STATE
        if state not in STATE_TARGET:
            # Coercing an unrecognised state to open would report a resolved
            # decision as still in flight. Fail closed and name the offender
            # instead of guessing; the bridge may run on a bundle the audit
            # has not vetted.
            proposals.append({"id": entry["id"], "state": state, "target": None,
                              "action": "none", "status": "STATE-UNKNOWN"})
            continue
        target = STATE_TARGET[state]
        shared = {"id": entry["id"], "state": state, "target": target}
        found = known.get((work_id, entry["id"]))
        if found is None:
            criticality = entry.get("criticality", DEFAULT_CRITICALITY)
            proposals.append({
                **shared,
                "action": "create",
                "status": "APPLIED" if apply else "PROPOSED",
                "argv": ["item", "add", "--code", code,
                         "--title", f"{entry['id']} — {entry['title']}",
                         "--description", describe(entry, work_id, root),
                         "--category", CATEGORY,
                         "--criticality", criticality if criticality in CRITICALITY else DEFAULT_CRITICALITY,
                         "--status", target],
            })
            continue
        duplicates = found.get("duplicates")
        if duplicates:
            shared["duplicates"] = list(duplicates)
        current = found.get("status") or ""
        # An item whose status the store did not report gives nothing to
        # reconcile against; unknown is not evidence of divergence, so the
        # link alone is enough to call it mirrored.
        if not current or current == target:
            proposals.append({**shared, "action": "none", "status": "REUSED", "item_id": found.get("id")})
        elif target in LEGAL_TRANSITIONS.get(current, set()):
            proposals.append({
                **shared,
                "action": "transition",
                "status": "TRANSITIONED" if apply else "PROPOSED",
                "item_id": found.get("id"),
                "argv": ["item", "transition", "--id", str(found.get("id")), "--status", target],
            })
        else:
            # No legal path from current to target. The bridge refuses instead of
            # reaching for reconcile-status, which the backlog contract forbids
            # as an ordinary transition.
            proposals.append({**shared, "action": "none", "status": "TRANSITION-REFUSED",
                              "item_id": found.get("id"), "current": current})
    changed = False
    failure: str | None = None
    if apply:
        for proposal in proposals:
            if proposal.get("action") not in {"create", "transition"}:
                continue
            if failure is not None:
                # Something already broke. Stop writing, but keep the entry in
                # the report so the operator sees what was left undone.
                proposal["status"] = "SKIPPED"
                continue
            try:
                proposal["item"] = call(cli, tools, store, proposal["argv"]).get("data")
                changed = True
            except BacklogUnavailable as error:
                # There is no transaction across successive calls. Reporting a
                # bare failure would assert that nothing happened while earlier
                # items had already landed, so the partial record travels with
                # the refusal.
                proposal["status"] = "FAILED"
                proposal["detail"] = str(error)
                failure = str(error)
    if failure is not None:
        return {"schema": SCHEMA, "db": store, "verdict": "BLOCKED", "code": "BACKLOG-UNAVAILABLE",
                "detail": failure, "backlog": resolution, "changed": changed, "items": proposals}
    return {"schema": SCHEMA, "db": store, "verdict": "APPLIED" if changed else "PREVIEW",
            "backlog": resolution, "changed": changed, "items": proposals}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--work-item")
    parser.add_argument("--work-id")
    parser.add_argument("--db")
    parser.add_argument("--code")
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).expanduser().resolve()
    try:
        if arguments.work_item and arguments.work_id:
            payload = sync_items(root, Path(arguments.work_item).resolve(), arguments.work_id,
                                 apply=arguments.apply, db=arguments.db)
        else:
            payload = ensure_bind(root, apply=arguments.apply, db=arguments.db, code=arguments.code)
    except BacklogUnavailable as error:
        payload = {"schema": SCHEMA, "db": store_path(arguments.db), "verdict": "BLOCKED",
                   "code": "BACKLOG-UNAVAILABLE", "detail": str(error)}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if payload.get("verdict") in {"OK", "PREVIEW", "APPLIED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
