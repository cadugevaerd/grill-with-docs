#!/usr/bin/env python3
"""Deterministic tasks.md -> Execution DAG partitioning for the ``partition`` step.

Stdlib only, no network, no Store I/O. Pure functions over text in, documents
out; the CLI owns reading and writing bytes.

Why this is code and not a prompt
---------------------------------
The same ``tasks.md`` must always produce the same DAG. A run pins
``dag_content_sha256``; if the grouping were a judgement call made by whatever
model happened to be dispatched, that pin would record noise and a resume
could legitimately disagree with the run it resumes. ADR-0012 states this.

Why phases are barriers (ADR-0012)
----------------------------------
The first design took weakly-connected components of (dependency edges ∪
same-file edges) and emitted one node per component. Measured against the
fifteen real ``tasks.md`` in this repository it produced **K=1 in fourteen of
them**: the phase spine chains every task into a single component, so the
partition degenerated to one node and one worker every time. Parallelism has
to come from somewhere the spine does not reach, so it comes from file
disjointness *inside* a phase, with the phase boundary kept as a barrier --
which is also what ``speckit-implement`` itself does ("Complete each phase
before moving to the next").

Tasks whose description names no file are not guessed at and not dropped: they
land on a ``parallel: false`` node that the scheduler dispatches alone, so no
concurrent writer can collide with it. Its declared scope is every mapped path
in the feature, which is the honest bound for "we do not know which of these it
touches" -- deliberately wide, and reported as such rather than pretended away.
"""
from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Iterable, NamedTuple

try:  # normal library use, as a package
    from . import gauntlet_runs
except ImportError:  # pragma: no cover - direct-file load, mirrors gauntlet_runs
    _spec = importlib.util.spec_from_file_location(
        "grill_core_gauntlet_runs", Path(__file__).resolve().parent / "gauntlet_runs.py"
    )
    gauntlet_runs = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(gauntlet_runs)

DAG_SCHEMA = gauntlet_runs.DAG_SCHEMA
REPORT_SCHEMA = "grill-partition-report/v1"
TASK_FILES_MARKER = "<!-- grill-task-files:v1 -->"
TASK_FILES_SCHEMA = "task-files/v1"
DAG_V2_SCHEMA = "grill-gauntlet-execution-dag/v2"
REPORT_V2_SCHEMA = "grill-partition-report/v2"

#: Requested parallel width. A ceiling, never a promise -- see ``_pack``.
DEFAULT_GROUPS = 3
#: Floor tier for every node this module emits. Matches
#: ``workflow_versions.TIER_POLICY_V4["implement-parallel"]``; the CLI passes
#: the live floor in so the two can never drift silently.
DEFAULT_TIER = "medium"

VERDICT_COMPLETE = "PARTITION-COMPLETE"
VERDICT_DEGRADED = "PARTITION-DEGRADED"
REASON_CONFLICT_GROUPS = "CONFLICT_GROUPS_BELOW_LIMIT"
REASON_UNMAPPED = "UNMAPPED_TASKS"
REASON_EVIDENCE = "EVIDENCE_BOUNDARY_TASKS"

_TASK_RE = re.compile(r"^- \[[ xX]\]\s+(T\d+)((?:\s*\[[^\]]+\])*)\s+(.*)$")
_PHASE_RE = re.compile(r"^##\s+Phase\s+(\d+)\s*:?\s*(.*)$")
_MARKER_RE = re.compile(r"\[([^\]]+)\]")
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_LINE_SUFFIX_RE = re.compile(r":\d+(?:-\d+)?$")
_BIN_LABELS = "abcdefghijklmnopqrstuvwxyz"
#: Wrapping punctuation, stripped from both ends. The leading dot is
#: deliberately absent: stripping it would turn ``.grill/x`` into ``grill/x``
#: and walk a forbidden path straight past the scope rule.
_WRAP = "`\"'()[]{}<>"
#: Sentence punctuation, stripped from the right end only.
_TRAIL = ".,;:!?"


class PartitionError(Exception):
    """Named, public-safe denial, mirroring ``gauntlet.GauntletError``."""

    def __init__(self, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


class Task(NamedTuple):
    id: str
    phase: int
    phase_title: str
    parallel: bool
    stories: tuple[str, ...]
    files: tuple[str, ...]
    line_no: int


class TaskFilesTask(NamedTuple):
    """One fully-declared v1 task.  It deliberately has no description grant."""

    id: str
    phase: int
    phase_title: str
    parallel: bool
    stories: tuple[str, ...]
    files: tuple[str, ...]
    result: str | None
    line_no: int


def _candidate_paths(description: str) -> Iterable[str]:
    """Backticked tokens first, then bare whitespace tokens.

    Both are yielded because real task lines mix the two: a path inside
    backticks is the convention, but plenty of lines write one bare.
    """
    yield from _BACKTICK_RE.findall(description)
    yield from description.split()


def extract_files(description: str) -> tuple[str, ...]:
    """Repo-relative paths named by a task line, de-duplicated and sorted.

    A token qualifies only if it contains ``/`` and survives the same
    escape-proof rule a worker grant scope obeys. A bare filename with no
    directory (``store.py``) is deliberately *not* a path: it is ambiguous, and
    guessing its directory is exactly the inference this module refuses.
    """
    found: set[str] = set()
    for raw in _candidate_paths(description):
        token = raw.strip()
        while token and token[-1] in _WRAP + _TRAIL:
            token = token[:-1]
        while token and token[0] in _WRAP:
            token = token[1:]
        token = _LINE_SUFFIX_RE.sub("", token).rstrip("/")
        if "/" not in token or "://" in token:
            continue
        if gauntlet_runs._is_safe_relative_path(token):
            found.add(token)
    return tuple(sorted(found))


def parse_tasks(text: str) -> tuple[Task, ...]:
    """Parse a Spec Kit ``tasks.md`` into ordered, phase-tagged tasks."""
    tasks: list[Task] = []
    phase = 0
    phase_title = ""
    for line_no, line in enumerate(text.splitlines(), start=1):
        heading = _PHASE_RE.match(line)
        if heading:
            phase = int(heading.group(1))
            phase_title = heading.group(2).strip()
            continue
        match = _TASK_RE.match(line)
        if not match:
            continue
        markers = tuple(m.strip() for m in _MARKER_RE.findall(match.group(2) or ""))
        tasks.append(
            Task(
                id=match.group(1),
                phase=phase,
                phase_title=phase_title,
                parallel="P" in markers,
                stories=tuple(m for m in markers if m != "P"),
                files=extract_files(match.group(3)),
                line_no=line_no,
            )
        )
    return tuple(tasks)


def _conflict_groups(tasks: list[Task]) -> list[list[Task]]:
    """Group tasks of one phase so that two tasks naming the same file share a group.

    Union-find over file sharing only. The phase spine is deliberately not an
    edge here: it is the barrier *between* phases, already expressed as
    ``depends_on``, and folding it in is what collapsed the whole graph into a
    single component in the first design.
    """
    parent: dict[str, str] = {task.id: task.id for task in tasks}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        parent[find(left)] = find(right)

    owner: dict[str, str] = {}
    for task in tasks:
        for path in task.files:
            if path in owner:
                union(task.id, owner[path])
            else:
                owner[path] = task.id

    grouped: dict[str, list[Task]] = {}
    for task in tasks:
        grouped.setdefault(find(task.id), []).append(task)
    # Order by first appearance so the output is stable across runs.
    return sorted(grouped.values(), key=lambda group: group[0].line_no)


def _pack(groups: list[list[Task]], width: int) -> list[list[Task]]:
    """Longest-processing-time bin packing. Never splits a conflict group.

    Splitting one would put two writers of the same file in different waves and
    ``declare_wave`` would reject the overlap anyway -- so the ceiling gives way
    before the invariant does.
    """
    bins: list[list[Task]] = [[] for _ in range(min(width, len(groups)))]
    ordered = sorted(groups, key=lambda group: (-len(group), group[0].line_no))
    for group in ordered:
        target = min(bins, key=lambda b: (len(b), bins.index(b)))
        target.extend(group)
    for b in bins:
        b.sort(key=lambda task: task.line_no)
    return [b for b in bins if b]


def _sidecar(sidecar_dir: str, node_id: str) -> str:
    return f"{sidecar_dir.rstrip('/')}/{node_id}.tasks.json"


def _node(node_id: str, *, depends_on: list[str], tier: str, parallel: bool,
          files: Iterable[str]) -> dict[str, Any]:
    return {
        "id": node_id,
        "depends_on": sorted(depends_on),
        "tier": tier,
        "parallel": parallel,
        "files": sorted(set(files)),
    }


def partition(text: str, *, feature: str, sidecar_dir: str,
              groups: int = DEFAULT_GROUPS,
              tier: str = DEFAULT_TIER) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the Execution DAG and its report from a ``tasks.md`` body.

    Returns ``(execution_dag, partition_report)``. Raises :class:`PartitionError`
    rather than emitting a document that only looks parallel.
    """
    if TASK_FILES_MARKER in text:
        return partition_task_files(text, feature=feature, groups=groups, tier=tier)
    if groups < 1:
        raise PartitionError("PARTITION-INVALID-WIDTH", "requested width must be at least 1")
    tasks = parse_tasks(text)
    if not tasks:
        raise PartitionError("PARTITION-NO-TASKS", "tasks.md declares no tasks")

    # A task that writes coordinator evidence (.grill/, .specify/reports/) may
    # never run in a worker -- that rule is what stops a worker forging its own
    # proof. It is not a reason to refuse the whole feature: ADR-0010 makes the
    # coordinator the single Evidence Boundary, so such a task is *the leader's*
    # work. It is withheld from every wave and handed back by name.
    deferred = [
        task for task in tasks
        if any(gauntlet_runs._dag_scope_violation(path) for path in task.files)
    ]
    deferred_ids = [task.id for task in deferred]
    dispatchable = [task for task in tasks if task.id not in set(deferred_ids)]
    if not dispatchable:
        raise PartitionError(
            "PARTITION-COORDINATOR-ONLY",
            "every task writes coordinator evidence, so no worker may run any of them",
            tasks=len(tasks),
            deferred_to_leader=deferred_ids,
        )

    feature_files = sorted({path for task in dispatchable for path in task.files})
    if not feature_files:
        raise PartitionError(
            "PARTITION-UNSCOPED-FEATURE",
            "no task names a repo-relative path, so no worker scope can be fenced",
            tasks=len(tasks),
        )

    phases: list[int] = []
    for task in dispatchable:
        if task.phase not in phases:
            phases.append(task.phase)

    nodes: list[dict[str, Any]] = []
    phase_reports: list[dict[str, Any]] = []
    node_reports: list[dict[str, Any]] = []
    previous_phase_ids: list[str] = []
    unmapped_ids: list[str] = []

    for phase in phases:
        members = [task for task in dispatchable if task.phase == phase]
        mapped = [task for task in members if task.files]
        unmapped = [task for task in members if not task.files]
        prefix = f"p{phase:02d}"
        parallel_ids: list[str] = []

        for index, packed in enumerate(_pack(_conflict_groups(mapped), groups)):
            node_id = f"{prefix}-{_BIN_LABELS[index]}"
            files = {path for task in packed for path in task.files}
            files.add(_sidecar(sidecar_dir, node_id))
            nodes.append(_node(node_id, depends_on=list(previous_phase_ids),
                               tier=tier, parallel=True, files=files))
            node_reports.append({
                "id": node_id, "phase": phase, "parallel": True,
                "task_ids": [task.id for task in packed], "scope": "DECLARED",
            })
            parallel_ids.append(node_id)

        serial_id = None
        if unmapped:
            serial_id = f"{prefix}-serial"
            files = set(feature_files)
            files.add(_sidecar(sidecar_dir, serial_id))
            nodes.append(_node(serial_id,
                               depends_on=list(parallel_ids or previous_phase_ids),
                               tier=tier, parallel=False, files=files))
            node_reports.append({
                "id": serial_id, "phase": phase, "parallel": False,
                "task_ids": [task.id for task in unmapped], "scope": "FEATURE_WIDE",
            })
            unmapped_ids.extend(task.id for task in unmapped)

        reasons: list[str] = []
        if any(task.phase == phase for task in deferred):
            reasons.append(REASON_EVIDENCE)
        if len(parallel_ids) < groups:
            reasons.append(REASON_CONFLICT_GROUPS)
        if unmapped:
            reasons.append(REASON_UNMAPPED)
        phase_reports.append({
            "phase": phase,
            "title": members[0].phase_title,
            "tasks": len(members),
            "achieved_groups": len(parallel_ids),
            "requested_groups": groups,
            "unmapped_tasks": len(unmapped),
            "reasons": reasons,
        })
        previous_phase_ids = parallel_ids + ([serial_id] if serial_id else [])

    if not nodes:  # pragma: no cover - guarded by PARTITION-NO-TASKS above
        raise PartitionError("PARTITION-NO-TASKS", "no node could be emitted")

    # The widest wave this DAG can actually fill, capped by the requested
    # width: promising three workers for a DAG whose widest phase holds two
    # would reserve a slot nothing can ever occupy.
    widest = max(report["achieved_groups"] for report in phase_reports)
    dag = {
        "schema": DAG_SCHEMA,
        "feature": feature,
        "max_workers": max(1, min(groups, widest)),
        "nodes": nodes,
    }

    degraded = bool(deferred_ids) or any(report["reasons"] for report in phase_reports)
    report = {
        "schema": REPORT_SCHEMA,
        "feature": feature,
        "verdict": VERDICT_DEGRADED if degraded else VERDICT_COMPLETE,
        "requested_groups": groups,
        "max_workers": dag["max_workers"],
        "tasks": len(tasks),
        "dispatchable_tasks": len(dispatchable),
        "unmapped_task_ids": unmapped_ids,
        "deferred_to_leader": deferred_ids,
        "phases": phase_reports,
        "nodes": node_reports,
    }
    return dag, report


# The historical parser above is intentionally retained for audit-only v1
# documents.  A candidate document opts into this closed grammar explicitly;
# its task descriptions are never consulted for write authority.
def _strict_json(value: str, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = item
        return result

    try:
        return json.loads(value, object_pairs_hook=pairs,
                          parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PartitionError("TASK-FILES-INVALID", f"{label} is not strict JSON") from exc


def normalize_task_path(value: Any) -> str:
    """Canonicalize the one allowed spelling variation before validating it."""
    if not isinstance(value, str):
        raise PartitionError("TASK-FILES-INVALID", "task file path is not a string")
    path = value[2:] if value.startswith("./") else value
    if value.startswith("././") or not path or not gauntlet_runs._is_safe_relative_path(path):
        raise PartitionError("TASK-FILES-INVALID", "task file path is unsafe", path=value)
    pieces = path.split("/")
    # A path accepted by POSIX but interpreted as a device, ADS, or alias on a
    # Windows checkout is not portable enough to grant to a worker.
    devices = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if any(part.endswith((" ", ".")) or ":" in part or part.upper().split(".", 1)[0] in devices
           for part in pieces):
        raise PartitionError("TASK-FILES-INVALID", "task file path is not portable", path=value)
    return path


def _validate_leaf(root: str | Path | None, path: str) -> None:
    """Prove that existing parents stay inside ``root`` without following links."""
    if root is None:
        return
    cursor = Path(root)
    try:
        root_stat = os.lstat(cursor)
    except OSError as exc:
        raise PartitionError("TASK-SCOPE-VIOLATION", "task root is unavailable") from exc
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise PartitionError("TASK-SCOPE-VIOLATION", "task root is not a real directory")
    pieces = path.split("/")
    for index, piece in enumerate(pieces):
        cursor /= piece
        try:
            observed = os.lstat(cursor)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise PartitionError("TASK-SCOPE-VIOLATION", "could not prove task path boundary", path=path) from exc
        if stat.S_ISLNK(observed.st_mode):
            raise PartitionError("TASK-SCOPE-VIOLATION", "task path traverses a link", path=path)
        if index < len(pieces) - 1 and not stat.S_ISDIR(observed.st_mode):
            raise PartitionError("TASK-SCOPE-VIOLATION", "task path parent is not a directory", path=path)
        if index == len(pieces) - 1 and not stat.S_ISREG(observed.st_mode):
            raise PartitionError("TASK-SCOPE-VIOLATION", "task path leaf is not a regular file", path=path)


def parse_task_files(text: str, *, feature: str, root: str | Path | None = None,
                     scope_files: Iterable[str] | None = None) -> tuple[TaskFilesTask, ...]:
    """Parse the adopted ``task-files/v1`` grammar before any grant exists."""
    lines = text.splitlines()
    fenced = False
    markers: list[int] = []
    phase = None
    previous_phase = 0
    phase_title = ""
    seen_ids: set[str] = set()
    consumed: set[int] = set()
    visible: set[int] = set()
    tasks: list[TaskFilesTask] = []
    normalized_scope = None if scope_files is None else {normalize_task_path(path) for path in scope_files}
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            index += 1
            continue
        if fenced:
            index += 1
            continue
        visible.add(index)
        if line.strip() == TASK_FILES_MARKER:
            markers.append(index + 1)
            index += 1
            continue
        heading = _PHASE_RE.match(line)
        if heading:
            candidate = int(heading.group(1))
            if candidate <= previous_phase:
                raise PartitionError("TASKS-STRUCTURE-INVALID", "phases must be strictly ordered", line=index + 1)
            phase, previous_phase, phase_title = candidate, candidate, heading.group(2).strip()
            index += 1
            continue
        match = _TASK_RE.match(line)
        if not match:
            index += 1
            continue
        if phase is None:
            raise PartitionError("TASKS-STRUCTURE-INVALID", "task is outside a phase", line=index + 1)
        task_id = match.group(1)
        if task_id in seen_ids:
            raise PartitionError("TASKS-STRUCTURE-INVALID", "task id is duplicated", task_id=task_id, line=index + 1)
        if index + 1 >= len(lines) or not lines[index + 1].startswith("  Files: "):
            raise PartitionError("TASK-FILES-MISSING", "Files must immediately follow a task", task_id=task_id, line=index + 1)
        raw_files = _strict_json(lines[index + 1][9:], "Files")
        if not isinstance(raw_files, list) or any(not isinstance(path, str) for path in raw_files):
            raise PartitionError("TASK-FILES-INVALID", "Files must be a JSON string array", task_id=task_id)
        files = tuple(normalize_task_path(path) for path in raw_files)
        if len(set(files)) != len(files) or len({path.casefold() for path in files}) != len(files):
            raise PartitionError("TASK-FILES-DUPLICATE", "Files contains a duplicate path", task_id=task_id)
        if normalized_scope is not None and not set(files).issubset(normalized_scope):
            raise PartitionError("TASK-SCOPE-VIOLATION", "Files exceeds adopted scope", task_id=task_id)
        for path in files:
            _validate_leaf(root, path)
        consumed.add(index + 1)
        result: str | None = None
        next_index = index + 2
        if next_index < len(lines) and lines[next_index].startswith("  Result: "):
            raw_result = _strict_json(lines[next_index][10:], "Result")
            if not isinstance(raw_result, str):
                raise PartitionError("TASK-FILES-INVALID", "Result must be a JSON string", task_id=task_id)
            result = normalize_task_path(raw_result)
            consumed.add(next_index)
            next_index += 1
        deferred = any(gauntlet_runs._dag_scope_violation(path) for path in files)
        if files and not deferred and result is None:
            raise PartitionError("TASK-RESULT-MISSING", "worker task needs a declared Result", task_id=task_id)
        if result is not None:
            if result not in files:
                raise PartitionError("TASK-RESULT-UNDECLARED", "Result is not declared in Files", task_id=task_id)
            expected = f"specs/{feature}/implement/{task_id}.tasks.json"
            if result != expected:
                raise PartitionError("TASK-RESULT-UNDECLARED", "Result has the wrong public path", task_id=task_id)
        markers_found = tuple(marker.strip() for marker in _MARKER_RE.findall(match.group(2) or ""))
        tasks.append(TaskFilesTask(task_id, phase, phase_title, "P" in markers_found,
                                   tuple(marker for marker in markers_found if marker != "P"), files, result, index + 1))
        seen_ids.add(task_id)
        index = next_index
    if fenced:
        raise PartitionError("TASKS-STRUCTURE-INVALID", "markdown fence is not closed")
    if len(markers) != 1:
        raise PartitionError("TASK-FILES-MIGRATION-REQUIRED", "task-files/v1 marker must appear exactly once")
    for line_no, line in enumerate(lines):
        if line_no in visible and line_no not in consumed and line.startswith(("  Files:", "  Result:")):
            raise PartitionError("TASK-FILES-INVALID", "orphan or duplicate task field", line=line_no + 1)
    if not tasks:
        raise PartitionError("TASKS-STRUCTURE-INVALID", "tasks.md declares no tasks")
    return tuple(tasks)


def tasks_semantic_sha256(text: str, tasks: Iterable[TaskFilesTask] | None = None) -> str:
    """Pin every byte except parsed checklist state, which reconciliation owns."""
    parsed = tuple(tasks) if tasks is not None else parse_task_files(text, feature=_feature_from_result_hint(text))
    lines = text.splitlines(keepends=True)
    for task in parsed:
        lines[task.line_no - 1] = re.sub(r"^- \[[ xX]\]", "- [ ]", lines[task.line_no - 1])
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def _feature_from_result_hint(text: str) -> str:
    match = re.search(r'"specs/([^/]+)/implement/T\d+\.tasks\.json"', text)
    if not match:
        raise PartitionError("TASK-RESULT-UNDECLARED", "cannot determine feature from Result")
    return match.group(1)


def partition_task_files(text: str, *, feature: str, groups: int = DEFAULT_GROUPS,
                         tier: str = DEFAULT_TIER, root: str | Path | None = None,
                         scope_files: Iterable[str] | None = None,
                         accepted_tasks: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Emit v2 only from explicit task grants; accepted tasks never remint work."""
    if groups < 1:
        raise PartitionError("PARTITION-INVALID-WIDTH", "requested width must be at least 1")
    tasks = parse_task_files(text, feature=feature, root=root, scope_files=scope_files)
    semantic = tasks_semantic_sha256(text, tasks)
    accepted = dict(accepted_tasks or {})
    task_ids = {task.id for task in tasks}
    if set(accepted) - task_ids:
        raise PartitionError("TASK-RESULT-DIVERGENT", "accepted task is absent from current tasks")
    pending = [task for task in tasks if task.id not in accepted]
    readonly = [task for task in pending if not task.files]
    deferred = [task for task in pending if task.files and any(gauntlet_runs._dag_scope_violation(path) for path in task.files)]
    dispatchable = [task for task in pending if task.files and task not in deferred]
    if not dispatchable:
        raise PartitionError("PARTITION-NO-WORKERS", "no dispatchable task remains", phases=[task.phase for task in tasks],
                             read_only_tasks=[task.id for task in readonly], deferred_to_leader=[task.id for task in deferred],
                             accepted_tasks=sorted(accepted))
    phases: list[int] = []
    for task in tasks:
        if task.phase not in phases:
            phases.append(task.phase)
    nodes: list[dict[str, Any]] = []
    node_reports: list[dict[str, Any]] = []
    phase_reports: list[dict[str, Any]] = []
    previous: list[str] = []
    for phase in phases:
        phase_tasks = [task for task in tasks if task.phase == phase]
        members = [task for task in dispatchable if task.phase == phase]
        phase_nodes: list[str] = []
        for number, packed in enumerate(_pack(_conflict_groups(members), groups)):
            node_id = f"p{phase:02d}-{_BIN_LABELS[number]}"
            node_files = sorted({path for task in packed for path in task.files})
            result_files = {task.id: task.result for task in packed if task.result is not None}
            node = {"id": node_id, "depends_on": sorted(previous), "tier": tier, "parallel": True,
                    "files": node_files, "task_ids": [task.id for task in packed], "result_files": result_files}
            nodes.append(node)
            node_reports.append({"id": node_id, "phase": phase, "task_ids": node["task_ids"],
                                 "files": node_files, "result_files": result_files})
            phase_nodes.append(node_id)
        phase_reports.append({"phase": phase, "title": phase_tasks[0].phase_title,
                              "task_ids": [task.id for task in phase_tasks], "node_ids": phase_nodes,
                              "read_only_tasks": [task.id for task in readonly if task.phase == phase],
                              "deferred_to_leader": [task.id for task in deferred if task.phase == phase],
                              "accepted_tasks": [task.id for task in phase_tasks if task.id in accepted]})
        previous = phase_nodes
    widest = max(len(report["node_ids"]) for report in phase_reports)
    dag = {"schema": DAG_V2_SCHEMA, "tasks_contract": TASK_FILES_SCHEMA, "feature": feature,
           "max_workers": max(1, min(groups, widest)), "tasks_semantic_sha256": semantic,
           "accepted_tasks": accepted, "nodes": nodes}
    report = {"schema": REPORT_V2_SCHEMA, "tasks_contract": TASK_FILES_SCHEMA, "feature": feature,
              "verdict": VERDICT_DEGRADED if readonly or deferred or accepted else VERDICT_COMPLETE,
              "requested_groups": groups, "max_workers": dag["max_workers"], "tasks": len(tasks),
              "dispatchable_tasks": len(dispatchable), "read_only_tasks": [task.id for task in readonly],
              "deferred_to_leader": [task.id for task in deferred], "accepted_tasks": sorted(accepted),
              "tasks_semantic_sha256": semantic, "phases": phase_reports, "nodes": node_reports}
    return dag, report
