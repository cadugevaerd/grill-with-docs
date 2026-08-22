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
import re
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
