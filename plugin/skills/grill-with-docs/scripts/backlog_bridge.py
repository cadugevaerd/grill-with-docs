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
    cli, tools = resolve_cli(tools)
    store = str(Path(db or DEFAULT_DB).expanduser())
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
    """Read the open BL blocks of one work item's DECISION-BACKLOG.md."""
    if not path.is_file():
        return []
    audit = sibling("audit_decisions")
    text = path.read_text(encoding="utf-8")
    matches = list(BLOCK.finditer(text))
    entries: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        values = audit.fields(text[match.end():end])
        if values.get("state") != "open":
            continue
        entries.append({"id": match.group(1), "title": match.group(2), **values})
    return entries


def describe(entry: dict[str, str], work_id: str, root: Path) -> str:
    body = "\n".join(f"- {key}: {value}" for key, value in entry.items() if key not in {"id", "title"})
    return (f"{body}\n\n---\n{WORK_ID_MARKER}: {work_id}\n{BL_MARKER}: {entry['id']}\n"
            f"repo: {root}\norigem: grill-with-docs backlog-sync")


def sync_items(root: Path, work_item: Path, work_id: str, *, apply: bool = False,
               db: str | None = None, tools: Any = None) -> dict[str, Any]:
    cli, tools = resolve_cli(tools)
    store = str(Path(db or DEFAULT_DB).expanduser())
    resolution = resolve_backlog(root, cli, tools, store)
    if resolution["status"] != "BOUND":
        return {"schema": SCHEMA, "db": store, "verdict": "BLOCKED", "code": "BACKLOG-NOT-BOUND",
                "backlog": resolution, "changed": False}
    code = resolution["code"]
    entries = parse_deferred(work_item / "DECISION-BACKLOG.md")
    existing = call(cli, tools, store, ["item", "list", "--code", code]).get("data") or []
    known = {
        (found.get(WORK_ID_MARKER), found.get(BL_MARKER))
        for found in (dict(re.findall(rf"(?m)^({WORK_ID_MARKER}|{BL_MARKER}):\s*(.+)$",
                                      item.get("description") or "")) for item in existing)
    }
    proposals: list[dict[str, Any]] = []
    for entry in entries:
        if (work_id, entry["id"]) in known:
            proposals.append({"id": entry["id"], "status": "REUSED"})
            continue
        criticality = entry.get("criticality", DEFAULT_CRITICALITY)
        proposals.append({
            "id": entry["id"],
            "status": "APPLIED" if apply else "PROPOSED",
            "argv": ["item", "add", "--code", code,
                     "--title", f"{entry['id']} — {entry['title']}",
                     "--description", describe(entry, work_id, root),
                     "--category", CATEGORY,
                     "--criticality", criticality if criticality in CRITICALITY else DEFAULT_CRITICALITY],
        })
    changed = False
    if apply:
        for proposal in proposals:
            if proposal["status"] != "APPLIED":
                continue
            proposal["item"] = call(cli, tools, store, proposal["argv"]).get("data")
            changed = True
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
        payload = {"schema": SCHEMA, "verdict": "BLOCKED", "code": "BACKLOG-UNAVAILABLE", "detail": str(error)}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if payload.get("verdict") in {"OK", "PREVIEW", "APPLIED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
