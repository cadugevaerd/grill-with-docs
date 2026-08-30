#!/usr/bin/env python3
"""Read-only, deterministic status inventory for Grill work items."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location("grill_workspace_status", HERE.with_name("grill_workspace.py"))
if spec is None or spec.loader is None:
    raise ImportError("cannot load grill_workspace")
workspace = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = workspace
spec.loader.exec_module(workspace)

SEQUENCE = ["specify", "plan", "checklist", "tasks", "analyze", "partition", "implement-parallel", "converge", "verify", "review", "ship"]
STATES = {"pending", "in-progress", "complete", "blocked"}
TERMINAL_PHASE_STATES = {"complete", "superseded"}

def git(root: Path, *args: str, raw: bool = False) -> str | bytes:
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=not raw, check=False)
    return p.stdout if raw else p.stdout.strip()

def live(root: Path) -> dict[str, Any]:
    return {"branch": git(root, "branch", "--show-current") or "DETACHED", "head": git(root, "rev-parse", "--verify", "HEAD"), "dirty": bool(git(root, "status", "--porcelain=v1", "--untracked-files=all"))}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def parse_json(bundle: Any, name: str) -> dict[str, Any]:
    raw = bundle.files.get(name)
    if raw is None:
        raise workspace.CliFailure(workspace.EXIT_NO_GO, "NO-GO", "MALFORMED-STRUCTURE", name)
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise workspace.CliFailure(workspace.EXIT_NO_GO, "NO-GO", "INVALID-UTF8", name) from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise workspace.CliFailure(workspace.EXIT_NO_GO, "NO-GO", "MALFORMED-JSON", name) from exc
    if not isinstance(value, dict):
        raise workspace.CliFailure(workspace.EXIT_NO_GO, "NO-GO", "MALFORMED-STRUCTURE", name)
    return value

def phases_and_map(files: dict[str, bytes]) -> tuple[list[str], dict[str, str], list[str], list[str], list[str]]:
    def text(name: str) -> str:
        raw = files.get(name, b"")
        try: return raw.decode("utf-8")
        except UnicodeError as exc: raise workspace.CliFailure(1, "NO-GO", "INVALID-UTF8", name) from exc
    roadmap, delivery = text("ROADMAP.md"), text("DELIVERY-MAP.md")
    phases = re.findall(r"(?m)^##\s+(FASE-\d{3})\b", roadmap)
    execution = re.search(r"(?m)^-\s+execution-order:\s*(.+)$", roadmap)
    ordered = [x for x in re.split(r"[ ,]+", execution.group(1)) if re.fullmatch(r"FASE-\d{3}", x)] if execution else phases
    phase_state = {m.group(1): m.group(2) for m in re.finditer(r"(?ms)^##\s+(FASE-\d{3})\b.*?^-\s+state:\s*(\S+)", roadmap)}
    modules = sorted(set(re.findall(r"(?m)^##\s+(MOD-\d{3})\b", delivery)))
    units = sorted(set(re.findall(r"(?m)^###\s+(DU-\d{3})\b", delivery)))
    types = sorted(set(re.findall(r"(?m)^-\s+development-type:\s*(\S+)\s*$", delivery)))
    return ordered, phase_state, modules, units, types

def item_payload(
    root: Path,
    bundle: Any,
    *,
    live_state: dict[str, Any],
    local_branches: set[str],
) -> dict[str, Any]:
    immutable = workspace.validate_metadata(bundle.metadata, bundle.work_id)
    state = parse_json(bundle, "state.json")
    dev = state.get("development")
    findings: list[str] = []
    if dev is None:
        tracking, current, completed, blocked, steps, item_sequence = "legacy-untracked", "unknown", [], [], {}, SEQUENCE
    elif workspace.development_sequence(dev) is None or dev.get("sequence") != workspace.development_sequence(dev) or not isinstance(dev.get("steps"), dict):
        tracking, current, completed, blocked, steps, item_sequence = "invalid", "unknown", [], [], dev.get("steps", {}) if isinstance(dev, dict) else {}, SEQUENCE
        findings.append("INVALID-DEVELOPMENT-SCHEMA")
    else:
        # Projected against the bundle's OWN sequence. A bundle written under
        # v3 still reports 11/11 after this build ships; it is not stale, it is
        # a finished cycle of the version that ran it.
        item_sequence = workspace.development_sequence(dev)
        tracking, steps = "tracked", dev["steps"]
        current = dev.get("current_step")
        completed = [s for s in item_sequence if steps.get(s) == "complete"]
        blocked = [s for s in item_sequence if steps.get(s) == "blocked"]
        if any(steps.get(s) not in STATES for s in item_sequence) or any(steps.get(s) == "complete" and any(steps.get(p) != "complete" for p in item_sequence[:item_sequence.index(s)]) for s in item_sequence):
            findings.append("INVALID-DEVELOPMENT-SEQUENCE")
    phases, phase_states, modules, units, types = phases_and_map(bundle.files)
    lv = live_state
    # `immutable.branch` is creation provenance. The first canonical
    # `specify` checkpoint records a separate execution branch after the
    # before-specify hook has created it; old bundles without that field keep
    # their historic immutable binding. This preserves the wrong-branch gate
    # without mistaking a legitimate post-init branch creation for drift.
    execution_branch = immutable.get("branch")
    if tracking == "tracked" and isinstance(dev, dict) and "execution_branch" in dev:
        candidate = dev["execution_branch"]
        # `None` is the explicit boundary between phases.  No phase has begun
        # yet, therefore there is no execution branch to compare; the next
        # canonical specify checkpoint must create one before work resumes.
        if candidate is None:
            execution_branch = None
        elif not isinstance(candidate, str) or not candidate:
            findings.append("INVALID-DEVELOPMENT-SCHEMA")
        else:
            execution_branch = candidate
    terminal = state.get("status") == "complete" and state.get("milestone_status") == "completed"
    branch_alive = bool(execution_branch) and execution_branch in local_branches
    if not terminal and branch_alive and execution_branch != lv["branch"]:
        findings.append("LIVE-VS-RECORDED")
    # Re-read all governance evidence through the same no-follow reader used by
    # writes.  The bundle walk is not sufficient: a symlink can be introduced
    # between discovery and this projection, and root-level constitution files
    # are outside the item bundle.
    constitution, constitution_text, _ = workspace.constitution_info(root)
    # Only for a work item that can still act. A finished item pinning the
    # constitution it was decided under is provenance, not drift: flagging it
    # forever means every constitutional amendment blocks the repository's own
    # status permanently, which makes amending expensive for the wrong reason.
    # An item still in flight is a different matter -- it would go on making
    # decisions under a constitution that has since changed.
    if not terminal and immutable.get("constitution", {}).get("sha256") != constitution.get("sha256"):
        findings.append("CONSTITUTION-HASH-MISMATCH")
    check_path = bundle.origin and Path(bundle.origin) / "CONSTITUTION-CHECK.md"
    audit_path = bundle.origin and Path(bundle.origin) / "AUDIT.md"
    check = workspace.safe_read(check_path, root=root) if check_path and check_path.exists() else None
    audit = workspace.safe_read(audit_path, root=root) if audit_path and audit_path.exists() else None
    if check is not None:
        try:
            workspace.parse_check(check)
        except workspace.CliFailure as exc:
            raise workspace.CliFailure(workspace.EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", exc.code, exc.message) from exc
    receipt = root / ".grill" / "global" / "receipts" / f"{bundle.work_id}.json"
    receipt_bytes = None
    if receipt.exists() or receipt.is_symlink():
        receipt_bytes = workspace.safe_read(receipt, root=root)
    item_location = {"worktree": str(root), "path": bundle.origin, "branch": lv["branch"], "head": lv["head"], "dirty": lv["dirty"], "current": False}
    active = state.get("active_phase")
    snapshot = {name: {"size": len(data), "mtime_ns": (Path(bundle.origin) / name).stat().st_mtime_ns} for name, data in sorted(bundle.files.items())}
    planning = {"status": state.get("status"), "milestone_status": state.get("milestone_status"), "active_phase": active, "phase_state": phase_states.get(active, state.get("phase_state")), "execution_order": phases, "phases": phase_states, "modules": modules, "delivery_units": units, "development_types": types}
    governance = {"constitution": {"state": constitution.get("state"), "path": constitution.get("path"), "hash": constitution.get("sha256")}, "check": {"state": "present" if check is not None else "missing", "hash": digest(check) if check is not None else None}, "audit": {"verdict": state.get("audit_verdict"), "hash": digest(audit) if audit is not None else None}, "reconciled": {"path": str(receipt) if receipt_bytes is not None else None, "hash": digest(receipt_bytes) if receipt_bytes is not None else None}}
    development = {"tracking": tracking, "current_step": current, "completed": completed, "blocked": blocked, "steps": steps, "execution_branch": execution_branch}
    closed, operational_status, pending_reasons = classify_item(
        planning=planning, development=development, governance=governance,
        findings=findings, blockers=blocked, sequence=item_sequence,
    )
    return {"work_id": bundle.work_id, "type": immutable["type"], "slug": immutable["slug"], "fingerprint": bundle.fingerprint, "locations": [item_location], "snapshot": snapshot, "recorded": {"branch": immutable.get("branch"), "head": immutable.get("head"), "base_ref": immutable.get("base_ref"), "base_commit": immutable.get("base_commit")}, "planning": planning, "development": development, "governance": governance, "blockers": blocked, "findings": sorted(findings), "closed": closed, "operational_status": operational_status, "pending_reasons": pending_reasons, "next_gate": "BLOCKED" if findings or blocked else (item_sequence[len(completed)] if len(completed) < len(item_sequence) else "complete")}


def classify_item(*, planning: dict[str, Any], development: dict[str, Any], governance: dict[str, Any], findings: list[str], blockers: list[str], sequence: list[str] | None = None) -> tuple[bool, str, list[str]]:
    """Classify one item without hiding contradictory terminal markers.

    `sequence` is the bundle's OWN canonical sequence. A bundle finished
    under v3 is complete against the v3 steps; judging it against the v4
    step names would report every finished v3 cycle as blocked.
    """
    sequence = SEQUENCE if sequence is None else sequence
    steps = development.get("steps") if isinstance(development.get("steps"), dict) else {}
    tracking = development.get("tracking")
    phase_states = planning.get("phases") if isinstance(planning.get("phases"), dict) else {}
    all_phases_terminal = bool(phase_states) and all(state in TERMINAL_PHASE_STATES for state in phase_states.values())
    all_steps_complete = tracking == "tracked" and all(steps.get(step) == "complete" for step in sequence)
    terminal_markers = planning.get("status") == "complete" and planning.get("milestone_status") == "completed"
    closure_gaps: list[str] = []
    if planning.get("status") != "complete": closure_gaps.append("state.status não é complete")
    if planning.get("milestone_status") != "completed": closure_gaps.append("milestone_status não é completed")
    if planning.get("active_phase") is not None: closure_gaps.append("active_phase não é null")
    if not all_phases_terminal: closure_gaps.append("fases não são todas terminais")
    if governance.get("audit", {}).get("verdict") != "GO": closure_gaps.append("auditoria não é GO")
    if not all_steps_complete: closure_gaps.append("etapas GWD incompletas")
    closed = not findings and not blockers and not closure_gaps
    reasons: list[str] = []
    if findings:
        reasons.append("findings: " + ", ".join(sorted(set(str(value) for value in findings))))
    if blockers:
        reasons.append("etapa GWD bloqueada: " + ", ".join(sorted(set(str(value) for value in blockers))))
    if terminal_markers and not closed:
        reasons.append("fechamento inconsistente: " + ", ".join(closure_gaps))
    if findings or blockers or (terminal_markers and not closed):
        return closed, "blocked", reasons
    in_progress = [step for step in sequence if steps.get(step) == "in-progress"]
    if in_progress:
        return closed, "in-progress", [f"etapa GWD em andamento: {in_progress[0]}"]
    pending = [step for step in sequence if steps.get(step) == "pending"]
    if pending:
        return closed, "pending", [f"etapa GWD pendente: {pending[0]}"]
    if not closed:
        return closed, "pending", ["fechamento pendente: " + ", ".join(closure_gaps)]
    return closed, "complete", []


def markdown_cell(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("|", "\\|")


def render_markdown(payload: dict[str, Any]) -> str:
    """Render the human status contract from the canonical JSON projection."""
    items = payload.get("work_items")
    if not isinstance(items, list):
        code = markdown_cell(payload.get("code", "STATUS-SCHEMA"))
        detail = markdown_cell(payload.get("error", "payload work_items inválido"))
        return f"| Item | Status | Pendência |\n|---|---|---|\n| workspace | blocked | {code}: {detail} |\n"
    actionable = [item for item in items if isinstance(item, dict) and not item.get("closed", False)]
    if actionable:
        lines = ["| Item | Status | Pendência |", "|---|---|---|"]
        for item in sorted(actionable, key=lambda value: str(value.get("work_id", ""))):
            reasons = item.get("pending_reasons")
            detail = "; ".join(str(reason) for reason in reasons) if isinstance(reasons, list) and reasons else "pendência não classificada"
            lines.append(f"| {markdown_cell(item.get('work_id', '?'))} | {markdown_cell(item.get('operational_status', 'blocked'))} | {markdown_cell(detail)} |")
        return "\n".join(lines) + "\n"
    if payload.get("verdict") == "BLOCKED" or payload.get("code") not in {"OK", "EMPTY"}:
        code = markdown_cell(payload.get("code", "STATUS-ERROR"))
        detail = markdown_cell(payload.get("error", "erro global de status"))
        return f"| Item | Status | Pendência |\n|---|---|---|\n| workspace | blocked | {code}: {detail} |\n"
    if not items:
        return "| Item | Status | Pendência |\n|---|---|---|\n| workspace | pending | GWD não inicializado |\n"
    return "all good\n"

def worktree_roots(root: Path, current: bool) -> list[Path]:
    if current: return [root]
    def common_dir(tree: Path) -> Path:
        value = Path(str(git(tree, "rev-parse", "--git-common-dir")))
        return (tree / value).resolve() if not value.is_absolute() else value.resolve()
    common = common_dir(root)
    out = git(root, "worktree", "list", "--porcelain", "-z", raw=True)
    assert isinstance(out, bytes)
    roots: list[Path] = []
    for record in out.split(b"\0"):
        if record.startswith(b"worktree "):
            candidate = Path(record[9:].decode("utf-8"))
            if candidate.is_dir() and not candidate.is_symlink() and common_dir(candidate) == common: roots.append(candidate.resolve())
    return sorted(set(roots))

def build_status(root_arg: str | Path, work_id: str | None = None, current_worktree: bool = False) -> tuple[dict[str, Any], int]:
    root = workspace.project_root(root_arg)
    grouped: dict[str, list[dict[str, Any]]] = {}
    # Branch refs belong to the repository, while branch/head/dirty belong to
    # each worktree.  Resolve each at its actual scope instead of spawning four
    # git processes for every copied work item.  A gauntlet repository commonly
    # has many items in many worker worktrees, making the old O(items) git
    # probing exceed the public entry point's bounded timeout.
    local_branches = set(git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines())
    for worktree in worktree_roots(root, current_worktree):
        directory = worktree / ".grill" / "work-items"
        if not directory.exists(): continue
        workspace.reject_symlink_chain(worktree, directory, allow_missing=False)
        live_state = live(worktree)
        for item in sorted(directory.iterdir(), key=lambda p: p.name):
            if item.is_symlink():
                raise workspace.CliFailure(workspace.EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(item))
            if not item.is_dir() or (work_id and item.name != work_id): continue
            bundle = workspace.read_local_bundle(worktree, item)
            value = item_payload(
                worktree,
                bundle,
                live_state=live_state,
                local_branches=local_branches,
            )
            value["locations"][0]["current"] = worktree == root
            grouped.setdefault(bundle.work_id, []).append(value)
    if work_id and work_id not in grouped: return {"schema":"grill-status/v1","verdict":"NO-GO","code":"WORK-ITEM-MISSING","project_root":str(root),"summary":{"total":0,"in_progress":0,"blocked":0,"completed":0},"work_items":[],"next_action":"iniciar"}, 1
    items=[]; global_findings=[]
    for key, variants in sorted(grouped.items()):
        fps={v["fingerprint"] for v in variants}
        base=variants[0]
        base["locations"]=[loc for v in variants for loc in v["locations"]]
        base["locations"] = sorted(base["locations"], key=lambda x: (x["worktree"], x["path"]))
        if len(fps)>1:
            base["variants"] = sorted((copy.deepcopy(v) for v in variants), key=lambda x: (x["fingerprint"], x["locations"][0]["worktree"]))
            base["findings"]=sorted(set(base["findings"]+["DUPLICATE-WORK-ID"])); base["next_gate"]="BLOCKED"; global_findings.append("DUPLICATE-WORK-ID")
        items.append(base)
    summary={"total":len(items),"in_progress":sum(1 for x in items if x["next_gate"] not in {"BLOCKED","complete"}),"blocked":sum(1 for x in items if x["next_gate"]=="BLOCKED"),"completed":sum(1 for x in items if x["next_gate"]=="complete")}
    item_findings = sorted({f for x in items for f in x["findings"]})
    global_findings.extend(item_findings)
    code=global_findings[0] if global_findings else ("OK" if items else "EMPTY")
    return {"schema":"grill-status/v1","verdict":"BLOCKED" if global_findings else "OK","code":code,"project_root":str(root),"summary":summary,"work_items":items,"next_action":"iniciar" if not items else ("resolver-bloqueios" if summary["blocked"] else "continuar")}, 2 if global_findings else 0

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("root"); parser.add_argument("--work-id"); parser.add_argument("--current-worktree",action="store_true"); parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try: payload, code=build_status(args.root, args.work_id, args.current_worktree)
    except workspace.CliFailure as exc: payload, code={"schema":"grill-status/v1","verdict":exc.verdict,"code":exc.code,"error":exc.message}, exc.exit_code
    if args.format == "markdown":
        sys.stdout.write(render_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return code
if __name__ == "__main__": raise SystemExit(main())
