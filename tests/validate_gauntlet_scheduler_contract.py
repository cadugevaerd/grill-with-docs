#!/usr/bin/env python3
"""Public-contract harness for FASE-003 Claude Scheduler Waves.

This validator deliberately owns its fixtures, following the exact fixture
style ``validate_gauntlet_run_contract.py`` (FASE-002) established: each case
starts from an isolated Git repository and reaches the public command surface
through the same V2 -> V3 -> rebound -> activation path an operator uses,
via real subprocess invocation of ``grill_workspace.py``.  This file does not
import from ``validate_gauntlet_run_contract.py`` -- the module-level
helpers it needs (``strict_json_bytes``, ``invoke``, ``git``, the V2->V3
activation bootstrap) are duplicated here so this file stays self-contained,
exactly the way ``validate_gauntlet_run_contract.py`` itself does not import
from ``validate_gauntlet_activation_contract.py``.

Phase 2 (T007-T009) adds only regression-pinning cases: they prove FASE-003's
core assumption -- that ``agent-execute`` is dispatched and checkpointed
through the existing, unmodified ``checkpoint`` command exactly like every
other of the eleven macro-steps, with no attestation exception -- already
holds in shipped ``grill_workspace.py``/``grill_core/attestation.py`` code.
No production code changes in this phase; later phases (T010 onward) add the
DAG validation, wave/worker declaration, progress, and remediation cases once
``gauntlet-dag-validate``/``gauntlet-wave-declare``/etc. exist.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin/skills/grill-with-docs"
ASSETS = SKILL / "assets"
WORKSPACE = SKILL / "scripts/grill_workspace.py"
WORKFLOW_MIGRATOR = SKILL / "scripts/grill_core/workflow_v3.py"
WORKFLOW_TEMPLATE = ASSETS / "WORKFLOW.template.md"
SCRIPTS = SKILL / "scripts"
WORK_ID = "scheduler-waves-a1b2"

# Mirrors grill_workspace.SEQUENCE (the eleven canonical macro-steps).  Kept
# as a literal here -- not imported -- the same way validate_checkpoint_
# contract.py already duplicates its own ``STEPS`` constant rather than
# reaching into grill_workspace.py's module globals.
SEQUENCE = [
    "specify", "plan", "checklist", "tasks", "analyze", "agent-assign",
    "agent-execute", "converge", "verify", "review", "ship",
]

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from grill_core import store


def _load_module(path: Path, name: str):
    """Load a sibling test module's fixture helpers in-process.

    ``validate_attestation_contract.py`` owns the production-hash chain
    builder (dispatch_key / skill_invocation_key / step_execution_id math);
    re-deriving that formula chain here would duplicate authority this file
    has no independent claim over.  ``validate_v3_wiring_contract.py``
    already reuses it this exact way.  This is a peer test module, not the
    FASE-002 gauntlet-run contract file this file is instructed to stay
    independent of.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ATTESTATION_FIXTURES = _load_module(
    REPO / "tests/validate_attestation_contract.py", "gauntlet_scheduler_attestation_fixtures"
)


def strict_json_bytes(value: bytes, *, source: str) -> dict[str, Any]:
    """Decode one JSON object and reject duplicate keys in test fixtures."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise AssertionError(f"duplicate key {key!r} in {source}")
            result[key] = item
        return result

    parsed = json.loads(value.decode("utf-8"), object_pairs_hook=unique)
    if not isinstance(parsed, dict):
        raise AssertionError(f"expected JSON object in {source}")
    return parsed


def invoke(program: Path, *args: object) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    """Run one public command and require exactly one JSON object on stdout."""
    process = subprocess.run(
        [sys.executable, str(program), *(str(value) for value in args)],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    lines = process.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError(
            f"expected exactly one JSON line from {program.name}: "
            f"stdout={process.stdout!r} stderr={process.stderr!r}"
        )
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON from {program.name}: {process.stdout!r}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"expected JSON object from {program.name}, got {payload!r}")
    return process, payload


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], text=True, capture_output=True, check=True
    ).stdout.strip()


def build_rebound_v3_repository(
    root: Path, work_id: str = WORK_ID, *, slug: str = "scheduler-waves", max_workers: int = 1,
) -> None:
    """Create one V3 work item whose workflow binding is current and activated.

    The same V2 -> V3 -> rebound -> activation path an operator uses,
    duplicated from ``validate_gauntlet_run_contract.py``'s
    ``build_rebound_v3_repository`` so this file has no import dependency on
    that FASE-002 test module.
    """
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    git(root, "config", "user.email", "gauntlet-scheduler-contract@example.invalid")
    git(root, "config", "user.name", "Gauntlet Scheduler Contract")
    (root / "WORKFLOW.md").write_bytes(WORKFLOW_TEMPLATE.read_bytes())
    git(root, "add", "WORKFLOW.md")
    git(root, "commit", "-qm", "fixture workflow v2")

    process, payload = invoke(WORKSPACE, "init", root, "--type", "feature", "--slug", slug, "--work-id", work_id, "--skip-backlog")
    if process.returncode != 0 or payload.get("status") != "CREATED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, payload = invoke(WORKSPACE, "migrate-v3", root, "--work-id", work_id, "--apply")
    if process.returncode != 0 or payload.get("verdict") != "APPLIED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, preview = invoke(WORKFLOW_MIGRATOR, "migrate", root)
    if process.returncode != 0 or preview.get("verdict") != "PREVIEW" or process.stderr:
        raise AssertionError((process.returncode, preview, process.stderr))
    process, payload = invoke(
        WORKFLOW_MIGRATOR, "migrate", root, "--apply", "--expected-sha256", preview["current_sha256"]
    )
    if process.returncode != 0 or payload.get("verdict") != "APPLIED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, payload = invoke(WORKSPACE, "migrate-v3", root, "--work-id", work_id, "--rebind-workflow", "--apply")
    if process.returncode != 0 or payload.get("verdict") not in {"APPLIED", "REUSED"} or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, payload = invoke(WORKSPACE, "gauntlet-init", root, "--work-id", work_id, "--max-workers", max_workers)
    if process.returncode != 0 or payload.get("verdict") != "ACTIVATED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))

    item = strict_json_bytes(
        (root / ".grill/work-items" / work_id / "WORK-ITEM.json").read_bytes(), source="WORK-ITEM.json"
    )
    workflow_sha256 = hashlib.sha256((root / "WORKFLOW.md").read_bytes()).hexdigest()
    if item.get("schema") != "grill-work-item/v3" or item["immutable"]["workflow"]["sha256"] != workflow_sha256:
        raise AssertionError("fixture does not have a current V3 workflow binding")


class GauntletSchedulerContractHarness(unittest.TestCase):
    """Public FASE-003 scheduler contract.

    Phase 2 (T007) only pins the User Story 1 boundary the rest of this
    phase depends on: dispatch order and per-step attestation are already
    enforced by the unmodified ``checkpoint`` command, with no special case
    for ``agent-execute``.
    """

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        build_rebound_v3_repository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def development_state(self) -> dict[str, Any]:
        state = strict_json_bytes(
            (self.root / ".grill/work-items" / WORK_ID / "state.json").read_bytes(), source="state.json"
        )
        development = state.get("development")
        if not isinstance(development, dict):
            raise AssertionError(f"missing development block: {state!r}")
        return development

    def checkpoint(self, step: str, state: str, **kwargs: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments: list[str] = ["checkpoint", self.root, "--work-id", WORK_ID, "--step", step, "--state", state]
        for value in kwargs.pop("evidence", []):
            arguments.extend(("--evidence", value))
        attestation = kwargs.pop("attestation", None)
        if attestation is not None:
            arguments.extend(("--attestation", attestation))
        reason = kwargs.pop("reason", None)
        if reason is not None:
            arguments.extend(("--reason", reason))
        if kwargs:
            raise AssertionError(f"unsupported checkpoint kwargs: {sorted(kwargs)}")
        return invoke(WORKSPACE, *arguments)

    def write_evidence(self, name: str) -> str:
        path = self.root / name
        path.write_text(f"{name} evidence\n", encoding="utf-8")
        return name

    def write_attestation_bundle(self, step_id: str, step_output: dict[str, Any], chain: dict[str, Any]) -> str:
        receipts_dir = self.root / "receipts"
        receipts_dir.mkdir(exist_ok=True)
        bundle = {
            "schema": "checkpoint-attestation/v1",
            "resolution": chain["resolution"],
            "dispatch_intent": chain["dispatch_intent"],
            "invocation_started": chain["invocation_started"],
            "invocation_terminal": chain["invocation_terminal"],
            "step_output": step_output,
            "catalog": ATTESTATION_FIXTURES.catalog(),
        }
        path = receipts_dir / f"{step_id}.json"
        path.write_text(json.dumps(bundle, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return str(path.relative_to(self.root))

    def complete_step_with_real_attestation(
        self, step_id: str, *, run_id: str, generation_label: str, predecessor: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Drive one real ``checkpoint --state complete`` through the actual,
        unmodified attestation gate -- not a fixture backdoor around it.

        Returns the predecessor-output shape (``schema`` ``step-output/v1``'s
        ``dependency_outputs`` entry) the next step of the same campaign must
        declare, so a caller can chain this across the whole macro-step
        sequence exactly the way the coordinator's real campaign does.
        """
        process, payload = self.checkpoint(step_id, "in-progress", reason=f"start {step_id}")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "UPDATED"), (payload, process.stderr))

        project_id = store.project_identity(self.root)["project_id"]
        chain = ATTESTATION_FIXTURES.build_chain(
            step_id=step_id, project_id=project_id, work_item_id=WORK_ID, run_id=run_id,
            generation_label=generation_label,
        )
        step_output = dict(chain["step_output"])
        step_output["dependency_outputs"] = [] if predecessor is None else [predecessor]
        step_output = ATTESTATION_FIXTURES.recompute_content_sha256(step_output)

        evidence = self.write_evidence(f"{step_id}-evidence.md")
        attestation_path = self.write_attestation_bundle(step_id, step_output, chain)

        process, payload = self.checkpoint(
            step_id, "complete", evidence=[evidence], attestation=attestation_path, reason=f"complete {step_id}",
        )
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "UPDATED"), (payload, process.stderr))

        return {
            "step_id": step_id,
            "output_sha256": step_output["output_sha256"],
            "receipt_ref": step_output["skill_invocation_receipt_ref"],
            "provenance": "current-generation",
        }

    # ------------------------------------------------------------------
    # T007.1 -- agent-execute gets no special-case exemption from the
    # attestation gate; it goes through verify_checkpoint_attestation
    # exactly like any other step (ADR-0016, FR-001).
    # ------------------------------------------------------------------

    def test_agent_execute_completion_without_attestation_is_rejected_like_any_other_step(self) -> None:
        run_id = "run-scheduler-checkpoint"
        generation_label = "gen-scheduler-checkpoint"
        predecessor: dict[str, Any] | None = None
        for step_id in SEQUENCE[: SEQUENCE.index("agent-execute")]:
            predecessor = self.complete_step_with_real_attestation(
                step_id, run_id=run_id, generation_label=generation_label, predecessor=predecessor,
            )

        process, payload = self.checkpoint("agent-execute", "in-progress", reason="start agent-execute")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "UPDATED"), (payload, process.stderr))

        # --evidence is present so the run reaches the attestation-specific
        # check; EVIDENCE-REQUIRED would fire first if it were absent, which
        # would prove nothing about the attestation gate itself.
        evidence = self.write_evidence("agent-execute-evidence.md")
        process, payload = self.checkpoint(
            "agent-execute", "complete", evidence=[evidence], reason="complete agent-execute",
        )

        self.assertEqual(process.returncode, 2, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "BLOCKED")
        self.assertEqual(payload.get("code"), "ATTESTATION-REQUIRED")

        development = self.development_state()
        self.assertEqual(development["steps"]["agent-execute"], "in-progress")
        self.assertEqual(development["current_step"], "agent-execute")

    # ------------------------------------------------------------------
    # T007.2 -- a blocked step never advances current_step past itself
    # (grill_workspace.py's ``next((s for s in sequence if steps.get(s) !=
    # "complete"), "complete")`` recompute).
    # ------------------------------------------------------------------

    def test_blocked_step_never_advances_current_step(self) -> None:
        process, payload = self.checkpoint("specify", "in-progress", reason="start specify")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "UPDATED"), (payload, process.stderr))

        process, payload = self.checkpoint("specify", "blocked", reason="waiting on FASE-002 evidence")
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "UPDATED")
        self.assertEqual(payload.get("current_step"), "specify")

        development = self.development_state()
        self.assertEqual(development["steps"]["specify"], "blocked")
        self.assertEqual(development["current_step"], "specify")

    # ------------------------------------------------------------------
    # T007.3 -- in-progress is a valid resume transition from a prior
    # blocked state on the same step (the FASE-003 specify session's own
    # resume path).
    # ------------------------------------------------------------------

    def test_in_progress_is_a_valid_resume_transition_from_blocked(self) -> None:
        process, payload = self.checkpoint("specify", "in-progress", reason="start specify")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "UPDATED"), (payload, process.stderr))
        process, payload = self.checkpoint("specify", "blocked", reason="waiting on FASE-002 evidence")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "UPDATED"), (payload, process.stderr))

        process, payload = self.checkpoint("specify", "in-progress", reason="resume specify")

        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "UPDATED")
        self.assertEqual(payload.get("current_step"), "specify")

        development = self.development_state()
        self.assertEqual(development["steps"]["specify"], "in-progress")
        self.assertEqual(development["current_step"], "specify")


# ==========================================================================
# Phase 3 (T010-T015) -- User Story 2: DAG validation and wave/worker
# declaration.  Fixtures below duplicate the two real corpus scope-violation
# nodes T010 names verbatim (011's execution-dag.json T019, 012's T019/T020)
# so the FR-004/ADR-0018 rejection is proven against real prior evidence, not
# an invented example.
# ==========================================================================

DAG_SCHEMA = "grill-gauntlet-execution-dag/v1"
GRILL_SCOPE_FILES = [
    "tests/validate_gauntlet_activation_contract.py",
    "tests/validate_work_item_v3_contract.py",
    "tests/validate_step_skill_registry_contract.py",
    "tests/run_validators.py",
    ".grill/work-items/feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420/ROUND-LOG.jsonl",
]
SPECIFY_REPORTS_SCOPE_FILES = [
    "tests/run_validators.py",
    ".specify/reports/verify-review-ship/verify.md",
]


def dag_node(
    node_id: str, *, depends_on: list[str] | None = None, tier: str = "medium",
    parallel: bool = True, files: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "depends_on": list(depends_on or []),
        "tier": tier,
        "parallel": parallel,
        "files": list(files or [f"tests/fixture-{node_id}.py"]),
    }


def dag_document(
    nodes: list[dict[str, Any]], *, max_workers: int = 5, feature: str = "scheduler-waves-fixture",
) -> dict[str, Any]:
    return {"schema": DAG_SCHEMA, "feature": feature, "max_workers": max_workers, "nodes": nodes}


def run_snapshot(root: Path, work_id: str, run_id: str) -> dict[str, Any]:
    """Read one already-authoritative run solely for fixture assertions."""
    document = store.read_snapshot(root).document
    return document["work_items"][work_id]["gauntlet"]["runs"][run_id]


def mark_worker_terminal(root: Path, work_id: str, run_id: str, worker_id: str) -> None:
    """Test-only white-box shim.

    Phase 3 has no public command that ever drives a worker to a terminal
    state (``gauntlet-worker-terminal`` is T018, Phase 4, out of this file's
    scope) -- so proving a downstream node's readiness gate, and proving the
    wave-sequencing gate below, needs one coordinator-shaped WAL transition
    here, the same way ``validate_gauntlet_run_contract.py``'s own
    ``mark_run_recovery_eligible``/``coordinator_fixture_transition`` seed
    FASE-002 fixture state that no public command produces yet either.
    """
    run = run_snapshot(root, work_id, run_id)
    admission = run["admission"]
    worker = run["workers"][worker_id]
    receipt = {
        "category": "runtime", "name": f"fixture-{worker_id}-terminal",
        "work_id": work_id, "run_id": run_id, "wave_id": "wave-0001",
        "base_commit": admission["base_commit"],
        "input_sha256": hashlib.sha256(f"{worker_id}:terminal".encode()).hexdigest(),
        "output_sha256": None,
    }
    event = {
        "event": "gauntlet.worker.terminal.fixture", "work_id": work_id, "run_id": run_id,
        "wave_id": receipt["wave_id"], "base_commit": receipt["base_commit"],
        "input_sha256": receipt["input_sha256"], "output_sha256": None,
        "worker_id": worker_id,
        "lease_id": worker["lease"]["lease_id"], "fencing_token": worker["lease"]["fencing_token"],
    }
    payload = {"category": receipt["category"], "name": receipt["name"], **{
        key: event[key] for key in event if key not in {"event", "receipt_sha256"}
    }}
    event["receipt_sha256"] = store.jcs_sha256(payload)

    def mark(document: dict[str, Any]) -> dict[str, Any]:
        document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]["state"] = "TERMINAL"
        return document

    store.transact_with_event(root, mark, event=event, receipt=receipt)


def mark_wave_complete(root: Path, work_id: str, run_id: str, wave_id: str) -> None:
    """Test-only white-box shim: no public command completes a wave in this
    phase (that is T018, Phase 4) -- see ``mark_worker_terminal`` above."""
    admission = run_snapshot(root, work_id, run_id)["admission"]
    receipt = {
        "category": "runtime", "name": f"fixture-{wave_id}-complete",
        "work_id": work_id, "run_id": run_id, "wave_id": wave_id,
        "base_commit": admission["base_commit"],
        "input_sha256": hashlib.sha256(f"{wave_id}:complete".encode()).hexdigest(),
        "output_sha256": None,
    }
    event = {
        "event": "gauntlet.wave.completed.fixture", "work_id": work_id, "run_id": run_id,
        "wave_id": wave_id, "base_commit": receipt["base_commit"],
        "input_sha256": receipt["input_sha256"], "output_sha256": None,
        "receipt_sha256": store.jcs_sha256(receipt),
    }

    def mark(document: dict[str, Any]) -> dict[str, Any]:
        document["work_items"][work_id]["gauntlet"]["runs"][run_id]["waves"][wave_id]["state"] = "COMPLETE"
        return document

    store.transact_with_event(root, mark, event=event, receipt=receipt)


def mark_worker_failed_unclassified(root: Path, work_id: str, run_id: str, worker_id: str) -> None:
    """Test-only white-box shim: drive a worker straight to ``FAILED`` without
    minting the failure-classification evidence receipt ``terminate_worker``
    always writes alongside a real failed transition.

    No public command can construct a ``FAILED`` worker without a valid
    ``--failure-class`` from FR-010's closed set (``gauntlet-worker-terminal``
    itself enforces it, T018) -- so proving ``gauntlet-remediate --reason
    transient-failure`` checks against the closed set, and not merely
    ``worker.state == "FAILED"``, needs this one coordinator-shaped WAL
    transition a real dispatch could never produce, the same class of
    fixture shim ``mark_worker_terminal``/``fake_last_activity`` above
    already use for state this phase's own commands cannot otherwise reach.
    """
    run = run_snapshot(root, work_id, run_id)
    admission = run["admission"]
    worker = run["workers"][worker_id]
    receipt = {
        "category": "runtime", "name": f"fixture-{worker_id}-failed-unclassified",
        "work_id": work_id, "run_id": run_id, "wave_id": "wave-0001",
        "base_commit": admission["base_commit"],
        "input_sha256": hashlib.sha256(f"{worker_id}:failed-unclassified".encode()).hexdigest(),
        "output_sha256": None,
    }
    event = {
        "event": "gauntlet.worker.terminal.fixture", "work_id": work_id, "run_id": run_id,
        "wave_id": receipt["wave_id"], "base_commit": receipt["base_commit"],
        "input_sha256": receipt["input_sha256"], "output_sha256": None,
        "worker_id": worker_id,
        "lease_id": worker["lease"]["lease_id"], "fencing_token": worker["lease"]["fencing_token"],
    }
    payload = {"category": receipt["category"], "name": receipt["name"], **{
        key: event[key] for key in event if key not in {"event", "receipt_sha256"}
    }}
    event["receipt_sha256"] = store.jcs_sha256(payload)

    def mark(document: dict[str, Any]) -> dict[str, Any]:
        document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]["state"] = "FAILED"
        return document

    store.transact_with_event(root, mark, event=event, receipt=receipt)


class GauntletDagAndWaveContractHarness(unittest.TestCase):
    """Public FASE-003 DAG validation and wave/worker declaration contract
    (T010-T015, User Story 2).  ``max_workers=5`` at activation so the
    effective-cap tests below can exercise a real, non-degenerate cap."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        build_rebound_v3_repository(self.root, max_workers=5)
        process, payload = invoke(WORKSPACE, "gauntlet-run", self.root, "--work-id", WORK_ID)
        if process.returncode != 0 or payload.get("verdict") not in {"RUN-CREATED", "RUN-REUSED"} or process.stderr:
            raise AssertionError((process.returncode, payload, process.stderr))
        self.run_id = payload["run_id"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_dag(self, document: dict[str, Any], name: str = "execution-dag.json") -> str:
        (self.root / name).write_text(json.dumps(document), encoding="utf-8")
        return name

    def dag_validate(self, dag_path: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return invoke(
            WORKSPACE, "gauntlet-dag-validate", self.root, "--work-id", WORK_ID,
            "--run-id", self.run_id, "--dag", dag_path,
        )

    def wave_declare(self, dag_path: str, node_ids: list[str]) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = [
            "gauntlet-wave-declare", self.root, "--work-id", WORK_ID, "--run-id", self.run_id, "--dag", dag_path,
        ]
        for node_id in node_ids:
            arguments.extend(("--node-id", node_id))
        return invoke(WORKSPACE, *arguments)

    def worker_declare(
        self, wave_id: str, node_id: str, *, dag_path: str = "execution-dag.json",
        tier: str = "medium", files: list[str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = [
            "gauntlet-worker-declare", self.root, "--work-id", WORK_ID, "--run-id", self.run_id,
            "--wave-id", wave_id, "--node-id", node_id, "--tier", tier, "--dag", dag_path,
        ]
        for path in files or [f"tests/fixture-{node_id}.py"]:
            arguments.extend(("--files", path))
        return invoke(WORKSPACE, *arguments)

    def assert_blocked(self, process, payload, code) -> None:
        self.assertEqual(process.returncode, 2, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "BLOCKED", payload)
        self.assertEqual(payload.get("code"), code, payload)

    def prepare_worker(
        self, worker_id: str, *, scope: list[str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = [
            "gauntlet-prepare-worker", self.root, "--work-id", WORK_ID, "--run-id", self.run_id,
            "--worker-id", worker_id,
        ]
        for path in scope or [f"tests/fixture-{worker_id}.py"]:
            arguments.extend(("--scope", path))
        return invoke(WORKSPACE, *arguments)

    # ------------------------------------------------------------------
    # T010/T011 -- gauntlet-dag-validate structural/scope/tier gates
    # ------------------------------------------------------------------

    def test_dag_validate_accepts_a_well_formed_dag(self) -> None:
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", depends_on=["T1"], parallel=False)])
        process, payload = self.dag_validate(self.write_dag(document))
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "DAG-VALID")
        self.assertEqual(payload.get("max_workers"), 5)
        self.assertEqual({node["id"] for node in payload["nodes"]}, {"T1", "T2"})

    def test_dag_validate_rejects_missing_required_field(self) -> None:
        document = dag_document([dag_node("T1")])
        del document["nodes"][0]["parallel"]
        process, payload = self.dag_validate(self.write_dag(document))
        self.assert_blocked(process, payload, "DAG-MALFORMED")

    def test_dag_validate_rejects_missing_dag_file(self) -> None:
        process, payload = self.dag_validate("execution-dag-does-not-exist.json")
        self.assert_blocked(process, payload, "DAG-MALFORMED")

    def test_dag_validate_rejects_cyclic_dag(self) -> None:
        document = dag_document([
            dag_node("T1", depends_on=["T2"]),
            dag_node("T2", depends_on=["T1"]),
        ])
        process, payload = self.dag_validate(self.write_dag(document))
        self.assert_blocked(process, payload, "DAG-CYCLIC")

    def test_dag_validate_rejects_duplicate_node_id(self) -> None:
        document = dag_document([dag_node("T1"), dag_node("T1")])
        process, payload = self.dag_validate(self.write_dag(document))
        self.assert_blocked(process, payload, "DAG-MALFORMED")

    def test_dag_validate_rejects_reserved_remediation_suffix_id(self) -> None:
        document = dag_document([dag_node("T1-r1")])
        process, payload = self.dag_validate(self.write_dag(document))
        self.assert_blocked(process, payload, "DAG-MALFORMED")

    def test_dag_validate_rejects_grill_scoped_node_matching_real_corpus(self) -> None:
        """Mirrors specs/011-gauntlet-loop/execution-dag.json T019 verbatim."""
        document = dag_document([dag_node("T019", files=GRILL_SCOPE_FILES)])
        process, payload = self.dag_validate(self.write_dag(document))
        self.assert_blocked(process, payload, "DAG-NODE-OUT-OF-SCOPE")

    def test_dag_validate_rejects_specify_reports_scoped_node_matching_real_corpus(self) -> None:
        """Mirrors specs/012-durable-run-state/execution-dag.json T019 verbatim."""
        document = dag_document([dag_node("T019", files=SPECIFY_REPORTS_SCOPE_FILES)])
        process, payload = self.dag_validate(self.write_dag(document))
        self.assert_blocked(process, payload, "DAG-NODE-OUT-OF-SCOPE")

    def test_dag_validate_rejects_tier_below_floor(self) -> None:
        document = dag_document([dag_node("T1", tier="small", files=["tests/fixture.py"])])
        process, payload = self.dag_validate(self.write_dag(document))
        self.assert_blocked(process, payload, "DAG-NODE-TIER-UNRESOLVED")

    def test_dag_validate_allows_markdown_only_node_at_small_tier(self) -> None:
        document = dag_document([dag_node("T1", tier="small", files=["specs/013-scheduler-waves/quickstart.md"])])
        process, payload = self.dag_validate(self.write_dag(document))
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "DAG-VALID")

    # ------------------------------------------------------------------
    # T012/T015 -- gauntlet-wave-declare readiness/cap/sequencing gates
    # ------------------------------------------------------------------

    def test_wave_declare_happy_path_single_node(self) -> None:
        document = dag_document([dag_node("T1", parallel=False)])
        process, payload = self.wave_declare(self.write_dag(document), ["T1"])
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-DECLARED")
        self.assertEqual(payload.get("wave_id"), "wave-0001")

    def test_wave_declare_shares_wave_across_parallel_nodes(self) -> None:
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        process, payload = self.wave_declare(self.write_dag(document), ["T1", "T2"])
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-DECLARED")

    def test_wave_declare_rejects_parallel_false_node_sharing_wave(self) -> None:
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=False)])
        process, payload = self.wave_declare(self.write_dag(document), ["T1", "T2"])
        self.assert_blocked(process, payload, "WAVE-NODE-NOT-PARALLEL")

    def test_wave_declare_rejects_when_dependency_not_terminal(self) -> None:
        document = dag_document([dag_node("T1", parallel=False), dag_node("T2", depends_on=["T1"], parallel=False)])
        process, payload = self.wave_declare(self.write_dag(document), ["T2"])
        self.assert_blocked(process, payload, "WAVE-NODE-NOT-READY")

    def test_wave_declare_rejects_unknown_node(self) -> None:
        document = dag_document([dag_node("T1")])
        process, payload = self.wave_declare(self.write_dag(document), ["T-unknown"])
        self.assert_blocked(process, payload, "WAVE-NODE-UNKNOWN")

    def test_wave_declare_rejects_when_exceeding_run_activation_cap(self) -> None:
        capped_root = Path(self.temporary.name) / "repo-capped"
        build_rebound_v3_repository(capped_root, max_workers=1)
        process, payload = invoke(WORKSPACE, "gauntlet-run", capped_root, "--work-id", WORK_ID)
        run_id = payload["run_id"]
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        (capped_root / "execution-dag.json").write_text(json.dumps(document), encoding="utf-8")
        process, payload = invoke(
            WORKSPACE, "gauntlet-wave-declare", capped_root, "--work-id", WORK_ID, "--run-id", run_id,
            "--dag", "execution-dag.json", "--node-id", "T1", "--node-id", "T2",
        )
        self.assert_blocked(process, payload, "WAVE-CAP-EXCEEDED")

    def test_wave_declare_rejects_when_exceeding_dag_declared_cap(self) -> None:
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)], max_workers=1)
        process, payload = self.wave_declare(self.write_dag(document), ["T1", "T2"])
        self.assert_blocked(process, payload, "WAVE-CAP-EXCEEDED")

    def test_wave_declare_blocks_second_wave_while_first_is_active(self) -> None:
        document = dag_document([dag_node("T1", parallel=False), dag_node("T2", parallel=False)])
        dag_path = self.write_dag(document)
        process, payload = self.wave_declare(dag_path, ["T1"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))

        process, payload = self.wave_declare(dag_path, ["T2"])
        self.assert_blocked(process, payload, "WAVE-PREREQUISITE-INCOMPLETE")

    def test_wave_declare_allocates_second_wave_once_first_is_complete(self) -> None:
        document = dag_document([dag_node("T1", parallel=False), dag_node("T2", depends_on=["T1"], parallel=False)])
        dag_path = self.write_dag(document)
        process, payload = self.wave_declare(dag_path, ["T1"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))

        process, payload = self.worker_declare("wave-0001", "T1")
        # declare_worker is a thin wrapper over prepare_worker's own FASE-002
        # intent protocol (see its docstring) and deliberately reports that
        # protocol's own verdict vocabulary rather than inventing a parallel
        # one, so it is WORKER-PREPARED here, not a distinct WORKER-DECLARED.
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))
        mark_worker_terminal(self.root, WORK_ID, self.run_id, "T1")
        mark_wave_complete(self.root, WORK_ID, self.run_id, "wave-0001")

        process, payload = self.wave_declare(dag_path, ["T2"])
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-DECLARED")
        self.assertEqual(payload.get("wave_id"), "wave-0002")

    # ------------------------------------------------------------------
    # T013/T015 -- gauntlet-worker-declare: exactly-once first dispatch
    # ------------------------------------------------------------------

    def test_worker_declare_rejects_reserved_remediation_suffix_node_id(self) -> None:
        process, payload = self.worker_declare("wave-0001", "T1-r1")
        self.assert_blocked(process, payload, "INVALID-IDENTIFIER")

    def test_worker_declare_rejects_tier_below_floor(self) -> None:
        document = dag_document([dag_node("T1", parallel=False)])
        self.wave_declare(self.write_dag(document), ["T1"])
        process, payload = self.worker_declare("wave-0001", "T1", tier="small", files=["tests/fixture-T1.py"])
        self.assert_blocked(process, payload, "DAG-NODE-TIER-UNRESOLVED")

    def test_worker_declare_rejects_wave_that_is_not_active(self) -> None:
        process, payload = self.worker_declare("wave-9999", "T1")
        self.assert_blocked(process, payload, "WAVE-NOT-FOUND")

    def test_worker_declare_is_exactly_once_per_node(self) -> None:
        document = dag_document([dag_node("T1", parallel=False)])
        self.wave_declare(self.write_dag(document), ["T1"])

        process, payload = self.worker_declare("wave-0001", "T1", files=["tests/fixture-T1.py"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))
        self.assertEqual(payload.get("worker_id"), "T1")

        # Idempotent retry with the exact same grant is reported REUSED.
        process, payload = self.worker_declare("wave-0001", "T1", files=["tests/fixture-T1.py"])
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "REUSED")

        # A second declaration of the same node with a different grant conflicts.
        process, payload = self.worker_declare("wave-0001", "T1", files=["tests/fixture-T1-other.py"])
        self.assert_blocked(process, payload, "WORKER-CONFLICT")

    # ------------------------------------------------------------------
    # B3/B4 fixes -- gauntlet-worker-declare no longer bypasses the
    # DAG-scope and wave-membership checks gauntlet-wave-declare already
    # enforces.
    # ------------------------------------------------------------------

    def test_worker_declare_rejects_grill_scoped_grant_even_when_dag_node_files_are_in_scope(self) -> None:
        """The DAG node's own declared ``files`` pass FR-004's scope rules,
        but the caller's ``--files`` grant does not -- B3 closes exactly this
        gap: the grant itself, not merely the DAG node's declaration, is
        checked."""
        document = dag_document([dag_node("T1", parallel=False)])
        dag_path = self.write_dag(document)
        process, payload = self.wave_declare(dag_path, ["T1"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        process, payload = self.worker_declare(
            "wave-0001", "T1", dag_path=dag_path,
            files=[".grill/work-items/feature-x/state.json"],
        )
        self.assert_blocked(process, payload, "DAG-NODE-OUT-OF-SCOPE")

    # ------------------------------------------------------------------
    # F1 fix -- gauntlet-prepare-worker (the FASE-002 command declare_worker
    # itself extends) now applies the same FR-004/ADR-0018 scope rejection
    # unconditionally to its own --scope, with no DAG document required or
    # consulted.  Two independent code reviews found the FASE-002 command
    # never applied it; the operator explicitly decided this is a security
    # invariant, not a FASE-003-only concern, and approved the resulting
    # behavior change to the existing command (see plan.md and
    # DECISION-BACKLOG.md BL-0002).
    # ------------------------------------------------------------------

    def test_prepare_worker_rejects_grill_scoped_grant(self) -> None:
        process, payload = self.prepare_worker(
            "w-scope-grill", scope=[".grill/work-items/feature-x/state.json"],
        )
        self.assert_blocked(process, payload, "GRANT-OUT-OF-SCOPE")

    def test_prepare_worker_rejects_specify_reports_scoped_grant(self) -> None:
        process, payload = self.prepare_worker(
            "w-scope-reports", scope=[".specify/reports/verify-review-ship/verify.md"],
        )
        self.assert_blocked(process, payload, "GRANT-OUT-OF-SCOPE")

    def test_prepare_worker_accepts_legitimate_scope(self) -> None:
        """Regression guard: an ordinary, in-scope --scope is unaffected by
        the F1 fix -- proves the new check rejects only the two closed
        rules, not a broadened notion of out-of-scope."""
        process, payload = self.prepare_worker(
            "w-scope-ok", scope=["plugin/skills/grill-with-docs/scripts/grill_workspace.py"],
        )
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WORKER-PREPARED", payload)

    def test_worker_declare_rejects_node_not_a_member_of_the_named_wave(self) -> None:
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        dag_path = self.write_dag(document)
        process, payload = self.wave_declare(dag_path, ["T1"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        # T2 is a real DAG node, but wave-0001 only ever named T1.
        process, payload = self.worker_declare("wave-0001", "T2", dag_path=dag_path)
        self.assert_blocked(process, payload, "WAVE-NODE-NOT-MEMBER")

    def test_wave_declare_rejects_dependency_that_failed_and_was_never_remediated(self) -> None:
        """Secondary fix: dependency readiness requires the lineage head be
        specifically TERMINAL (success), not merely any terminal-class
        state -- a FAILED-and-never-remediated dependency must never satisfy
        a dependent's readiness check."""
        document = dag_document([dag_node("T1", parallel=False), dag_node("T2", depends_on=["T1"], parallel=False)])
        dag_path = self.write_dag(document)
        process, payload = self.wave_declare(dag_path, ["T1"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        process, payload = self.worker_declare("wave-0001", "T1", dag_path=dag_path)
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))
        process, payload = invoke(
            WORKSPACE, "gauntlet-worker-terminal", self.root, "--work-id", WORK_ID, "--run-id", self.run_id,
            "--worker-id", "T1", "--outcome", "failed", "--failure-class", "process-timeout",
        )
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        process, payload = self.wave_declare(dag_path, ["T2"])
        self.assert_blocked(process, payload, "WAVE-NODE-NOT-READY")


# ==========================================================================
# Phase 4 (T016-T021) -- User Story 3: progress recording (with lease-TTL
# renewal), worker termination (success/failure, wave completion), and one
# bounded stall remediation per node.
# ==========================================================================


class GauntletProgressTerminationRemediationHarness(unittest.TestCase):
    """Public FASE-003 progress/termination/remediation contract (T016-T021,
    User Story 3).  ``max_workers=5`` at activation, matching Phase 3's
    harness, so the non-terminal-cap test below can exercise a real,
    non-degenerate cap."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        build_rebound_v3_repository(self.root, max_workers=5)
        process, payload = invoke(WORKSPACE, "gauntlet-run", self.root, "--work-id", WORK_ID)
        if process.returncode != 0 or payload.get("verdict") not in {"RUN-CREATED", "RUN-REUSED"} or process.stderr:
            raise AssertionError((process.returncode, payload, process.stderr))
        self.run_id = payload["run_id"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    # ------------------------------------------------------------------
    # Shared invocation helpers, mirroring GauntletDagAndWaveContractHarness.
    # ------------------------------------------------------------------

    def write_dag(self, document: dict[str, Any], name: str = "execution-dag.json") -> str:
        (self.root / name).write_text(json.dumps(document), encoding="utf-8")
        return name

    def wave_declare(self, dag_path: str, node_ids: list[str]) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = [
            "gauntlet-wave-declare", self.root, "--work-id", WORK_ID, "--run-id", self.run_id, "--dag", dag_path,
        ]
        for node_id in node_ids:
            arguments.extend(("--node-id", node_id))
        return invoke(WORKSPACE, *arguments)

    def worker_declare(
        self, wave_id: str, node_id: str, *, dag_path: str = "execution-dag.json",
        tier: str = "medium", files: list[str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = [
            "gauntlet-worker-declare", self.root, "--work-id", WORK_ID, "--run-id", self.run_id,
            "--wave-id", wave_id, "--node-id", node_id, "--tier", tier, "--dag", dag_path,
        ]
        for path in files or [f"tests/fixture-{node_id}.py"]:
            arguments.extend(("--files", path))
        return invoke(WORKSPACE, *arguments)

    def progress_record(self, worker_id: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return invoke(
            WORKSPACE, "gauntlet-progress-record", self.root, "--work-id", WORK_ID,
            "--run-id", self.run_id, "--worker-id", worker_id,
        )

    def worker_terminal(
        self, worker_id: str, outcome: str, failure_class: str | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = [
            "gauntlet-worker-terminal", self.root, "--work-id", WORK_ID, "--run-id", self.run_id,
            "--worker-id", worker_id, "--outcome", outcome,
        ]
        if failure_class is not None:
            arguments.extend(("--failure-class", failure_class))
        return invoke(WORKSPACE, *arguments)

    def remediate(self, worker_id: str, reason: str = "stall") -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return invoke(
            WORKSPACE, "gauntlet-remediate", self.root, "--work-id", WORK_ID, "--run-id", self.run_id,
            "--worker-id", worker_id, "--reason", reason,
        )

    def status(self) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return invoke(WORKSPACE, "gauntlet-status", self.root, "--work-id", WORK_ID, "--run-id", self.run_id)

    def assert_blocked(self, process, payload, code) -> None:
        self.assertEqual(process.returncode, 2, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "BLOCKED", payload)
        self.assertEqual(payload.get("code"), code, payload)

    def dispatch_single_worker(self, node_id: str = "T1", *, tier: str = "medium", files: list[str] | None = None) -> str:
        """Declare a one-node wave and drive its worker all the way to
        ``PREPARED``, returning the worker id (``== node_id`` for a first
        dispatch, FR-007)."""
        document = dag_document([dag_node(node_id, parallel=False, tier=tier, files=files)])
        dag_path = self.write_dag(document, name=f"{node_id}-dag.json")
        process, payload = self.wave_declare(dag_path, [node_id])
        if process.returncode != 0 or payload.get("verdict") != "WAVE-DECLARED":
            raise AssertionError((process.returncode, payload, process.stderr))
        process, payload = self.worker_declare("wave-0001", node_id, dag_path=dag_path, tier=tier, files=files)
        if process.returncode != 0 or payload.get("verdict") != "WORKER-PREPARED":
            raise AssertionError((process.returncode, payload, process.stderr))
        return node_id

    def fake_last_activity(self, worker_id: str, *, minutes_ago: int) -> None:
        """Test-only white-box shim: back-date a worker's lease renewal so it
        reads as stalled (or freshly active) without a real 15-minute wait.

        ``record_progress``/``_new_coordinator_lease`` both set
        ``lease.expires_at`` to ``<event time> + LEASE_DURATION`` (one hour);
        ``remediate_node`` derives "last activity" by subtracting that same
        fixed duration back out (``_last_activity_at``).  Faking
        ``expires_at`` to ``now + 1h - minutes_ago`` therefore fakes "last
        activity was ``minutes_ago`` minutes ago" exactly, the same class of
        WAL-shaped fixture shim ``mark_worker_terminal``/``mark_wave_complete``
        above already use for state this phase's own commands cannot yet
        reach directly.
        """
        run = run_snapshot(self.root, WORK_ID, self.run_id)
        admission = run["admission"]
        worker = run["workers"][worker_id]
        new_expires_at = (
            datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=1) - timedelta(minutes=minutes_ago)
        ).isoformat().replace("+00:00", "Z")
        receipt = {
            "category": "runtime", "name": f"fixture-{worker_id}-lease-{minutes_ago}",
            "work_id": WORK_ID, "run_id": self.run_id, "wave_id": "wave-0001",
            "base_commit": admission["base_commit"],
            "input_sha256": hashlib.sha256(f"{worker_id}:lease:{minutes_ago}".encode()).hexdigest(),
            "output_sha256": None,
        }
        event = {
            "event": "gauntlet.worker.lease-faked.fixture", "work_id": WORK_ID, "run_id": self.run_id,
            "wave_id": receipt["wave_id"], "base_commit": receipt["base_commit"],
            "input_sha256": receipt["input_sha256"], "output_sha256": None,
            "worker_id": worker_id,
            "lease_id": worker["lease"]["lease_id"], "fencing_token": worker["lease"]["fencing_token"],
        }
        payload = {"category": receipt["category"], "name": receipt["name"], **{
            key: event[key] for key in event if key not in {"event", "receipt_sha256"}
        }}
        event["receipt_sha256"] = store.jcs_sha256(payload)

        def mutate(document: dict[str, Any]) -> dict[str, Any]:
            target = document["work_items"][WORK_ID]["gauntlet"]["runs"][self.run_id]["workers"][worker_id]
            target["lease"]["expires_at"] = new_expires_at
            return document

        store.transact_with_event(self.root, mutate, event=event, receipt=receipt)

    # ------------------------------------------------------------------
    # T016/T017 -- gauntlet-progress-record: TTL renewal, PREPARED-only gate
    # ------------------------------------------------------------------

    def test_progress_record_renews_lease_past_near_expiry(self) -> None:
        self.dispatch_single_worker("T1")
        self.fake_last_activity("T1", minutes_ago=59)  # ~1 minute left on the original grant
        run = run_snapshot(self.root, WORK_ID, self.run_id)
        near_expiry = datetime.fromisoformat(run["workers"]["T1"]["lease"]["expires_at"].replace("Z", "+00:00"))
        self.assertLess(near_expiry - datetime.now(timezone.utc), timedelta(minutes=5))

        process, payload = self.progress_record("T1")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "PROGRESS-RECORDED"), (payload, process.stderr))

        run = run_snapshot(self.root, WORK_ID, self.run_id)
        renewed_expiry = datetime.fromisoformat(run["workers"]["T1"]["lease"]["expires_at"].replace("Z", "+00:00"))
        # A naive "no renewal" reading would still show ``near_expiry``; the
        # real record-time-anchored renewal must land far later than that.
        self.assertGreater(renewed_expiry, near_expiry + timedelta(minutes=30))

    def test_progress_record_rejects_worker_not_prepared(self) -> None:
        self.dispatch_single_worker("T1")
        process, payload = self.worker_terminal("T1", "completed")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        process, payload = self.progress_record("T1")
        self.assert_blocked(process, payload, "WORKER-NOT-PREPARED")

    # ------------------------------------------------------------------
    # T016/T018 -- gauntlet-worker-terminal: outcomes, cap release, wave
    # completion
    # ------------------------------------------------------------------

    def test_worker_terminal_completed_transitions_to_terminal(self) -> None:
        self.dispatch_single_worker("T1")
        process, payload = self.worker_terminal("T1", "completed")
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WORKER-TERMINAL")
        self.assertEqual(payload.get("state"), "TERMINAL")
        run = run_snapshot(self.root, WORK_ID, self.run_id)
        self.assertEqual(run["workers"]["T1"]["state"], "TERMINAL")

    def test_worker_terminal_failed_requires_failure_class(self) -> None:
        self.dispatch_single_worker("T1")
        process, payload = self.worker_terminal("T1", "failed")
        self.assert_blocked(process, payload, "FAILURE-CLASS-REQUIRED")

    def test_worker_terminal_failed_records_and_exposes_failure_class(self) -> None:
        self.dispatch_single_worker("T1")
        process, payload = self.worker_terminal("T1", "failed", failure_class="process-timeout")
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WORKER-TERMINAL")
        self.assertEqual(payload.get("state"), "FAILED")
        self.assertEqual(payload.get("failure_class"), "process-timeout")

        process, payload = self.status()
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        workers = {worker["worker_id"]: worker for worker in payload["run"]["workers"]}
        self.assertEqual(workers["T1"]["state"], "FAILED")
        self.assertEqual(workers["T1"]["failure_class"], "process-timeout")

    def test_worker_terminal_frees_the_non_terminal_cap_slot(self) -> None:
        document = dag_document(
            [dag_node(f"T{i}", parallel=True) for i in range(1, 6)] + [dag_node("T6", parallel=True)]
        )
        dag_path = self.write_dag(document)
        process, payload = self.wave_declare(dag_path, [f"T{i}" for i in range(1, 6)])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        for i in range(1, 6):
            process, payload = self.worker_declare("wave-0001", f"T{i}", dag_path=dag_path)
            self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))

        # T6 is a real DAG node but was never named into wave-0001's own
        # declaration -- gauntlet-worker-declare now requires wave membership
        # (B4 fix), so this is rejected before the cap is even consulted,
        # closing the bypass a direct call used to have around
        # gauntlet-wave-declare's own cap gate.
        process, payload = self.worker_declare("wave-0001", "T6", dag_path=dag_path)
        self.assert_blocked(process, payload, "WAVE-NODE-NOT-MEMBER")

        def non_terminal_count() -> int:
            run = run_snapshot(self.root, WORK_ID, self.run_id)
            return sum(1 for w in run["workers"].values() if w["state"] in {"DECLARED", "PREPARING", "PREPARED"})

        self.assertEqual(non_terminal_count(), 5)
        process, payload = self.worker_terminal("T1", "completed")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))
        # Terminating T1 alone frees exactly one non-terminal slot.
        self.assertEqual(non_terminal_count(), 4)

        # Complete the rest of wave-0001 so it reaches COMPLETE, then prove
        # the freed capacity is real: T6 -- now legitimately declared into a
        # new wave -- is within the run's effective cap.
        for i in range(2, 6):
            process, payload = self.worker_terminal(f"T{i}", "completed")
            self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))
        process, payload = self.wave_declare(dag_path, ["T6"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        process, payload = self.worker_declare("wave-0002", "T6", dag_path=dag_path)
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))

    def test_worker_terminal_completes_wave_and_unlocks_next_wave_declare(self) -> None:
        document = dag_document([
            dag_node("T1", parallel=False),
            dag_node("T2", depends_on=["T1"], parallel=False),
        ])
        dag_path = self.write_dag(document)
        process, payload = self.wave_declare(dag_path, ["T1"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        process, payload = self.worker_declare("wave-0001", "T1")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))

        process, payload = self.worker_terminal("T1", "completed")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        # Declaring wave-0002 requires wave-0001 already COMPLETE (Phase 3's
        # gate) -- the only way this can succeed is if terminating T1, the
        # wave's one and only declared node, completed the wave in the same
        # operation.
        process, payload = self.wave_declare(dag_path, ["T2"])
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-DECLARED")
        self.assertEqual(payload.get("wave_id"), "wave-0002")

    # ------------------------------------------------------------------
    # T016/T019 -- gauntlet-remediate --reason stall
    # ------------------------------------------------------------------

    def test_remediate_stall_mints_replacement_with_spent_budget(self) -> None:
        self.dispatch_single_worker("T1")
        self.fake_last_activity("T1", minutes_ago=20)  # past the 15-minute stall window

        process, payload = self.remediate("T1")
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "REMEDIATION-RECORDED")
        self.assertEqual(payload.get("worker_id"), "T1-r1")
        self.assertEqual(payload.get("remediates"), "T1")
        self.assertEqual(payload.get("recovery_count"), 1)

        run = run_snapshot(self.root, WORK_ID, self.run_id)
        replacement = run["workers"]["T1-r1"]
        self.assertEqual(replacement["node_id"], "T1")
        self.assertEqual(replacement["remediates"], "T1")
        self.assertEqual(replacement["lease"]["recovery_count"], 1)
        self.assertEqual(replacement["state"], "PREPARED")
        # The original worker itself is left exactly as it was (still its
        # own, separately-recorded PREPARED lease, budget untouched).
        self.assertEqual(run["workers"]["T1"]["lease"]["recovery_count"], 0)

    def test_remediate_stall_rejects_worker_with_recent_progress(self) -> None:
        self.dispatch_single_worker("T1")
        process, payload = self.progress_record("T1")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "PROGRESS-RECORDED"), (payload, process.stderr))

        process, payload = self.remediate("T1")
        self.assert_blocked(process, payload, "STALL-NOT-ELIGIBLE")

    def test_remediate_stall_second_attempt_blocks_budget_spent(self) -> None:
        self.dispatch_single_worker("T1")
        self.fake_last_activity("T1", minutes_ago=20)
        process, payload = self.remediate("T1")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "REMEDIATION-RECORDED"), (payload, process.stderr))

        self.fake_last_activity("T1-r1", minutes_ago=20)
        process, payload = self.remediate("T1-r1")
        self.assert_blocked(process, payload, "REMEDIATION-BUDGET-SPENT")

        run = run_snapshot(self.root, WORK_ID, self.run_id)
        self.assertNotIn("T1-r2", run["workers"])

    # ------------------------------------------------------------------
    # T022/T023 -- gauntlet-remediate --reason transient-failure
    # (User Story 4, FR-010): closed classification, shared budget.
    # ------------------------------------------------------------------

    def test_remediate_transient_failure_mints_replacement_with_spent_budget(self) -> None:
        self.dispatch_single_worker("T1")
        process, payload = self.worker_terminal("T1", "failed", failure_class="process-timeout")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        process, payload = self.remediate("T1", reason="transient-failure")
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "REMEDIATION-RECORDED")
        self.assertEqual(payload.get("worker_id"), "T1-r1")
        self.assertEqual(payload.get("remediates"), "T1")
        self.assertEqual(payload.get("recovery_count"), 1)

        run = run_snapshot(self.root, WORK_ID, self.run_id)
        replacement = run["workers"]["T1-r1"]
        self.assertEqual(replacement["node_id"], "T1")
        self.assertEqual(replacement["remediates"], "T1")
        self.assertEqual(replacement["lease"]["recovery_count"], 1)
        self.assertEqual(replacement["state"], "PREPARED")
        # The original FAILED worker itself is left exactly as it was.
        self.assertEqual(run["workers"]["T1"]["state"], "FAILED")

    def test_remediate_transient_failure_works_for_transport_failure_classification(self) -> None:
        """The read-back and the remediation check both match either of the
        two closed transient values, not just one hardcoded string."""
        self.dispatch_single_worker("T1")
        process, payload = self.worker_terminal("T1", "failed", failure_class="transport-failure")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        process, payload = self.remediate("T1", reason="transient-failure")
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "REMEDIATION-RECORDED")
        self.assertEqual(payload.get("worker_id"), "T1-r1")

    def test_remediate_transient_failure_rejects_worker_not_failed(self) -> None:
        """The classification must be a real recorded fact -- a worker that
        never terminated at all is rejected, not treated as remediable."""
        self.dispatch_single_worker("T1")
        process, payload = self.remediate("T1", reason="transient-failure")
        self.assert_blocked(process, payload, "WORKER-NOT-FAILED")

    def test_remediate_transient_failure_rejects_worker_completed(self) -> None:
        """A cleanly TERMINAL worker is a different state than FAILED --
        completion is never inferable as a transient failure."""
        self.dispatch_single_worker("T1")
        process, payload = self.worker_terminal("T1", "completed")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        process, payload = self.remediate("T1", reason="transient-failure")
        self.assert_blocked(process, payload, "WORKER-NOT-FAILED")

    def test_remediate_transient_failure_rejects_unclassified_failure(self) -> None:
        """No public command can leave a FAILED worker without a recorded
        transient classification (T018 requires --failure-class); this
        proves gauntlet-remediate's check is against the closed evidence-
        backed classification, not merely ``state == FAILED``."""
        self.dispatch_single_worker("T1")
        mark_worker_failed_unclassified(self.root, WORK_ID, self.run_id, "T1")

        process, payload = self.remediate("T1", reason="transient-failure")
        self.assert_blocked(process, payload, "FAILURE-CLASS-NOT-TRANSIENT")

    # ------------------------------------------------------------------
    # T022/T025 -- cross-mechanism budget sharing, both orderings
    # ------------------------------------------------------------------

    def test_remediate_transient_failure_blocked_after_stall_spent_budget(self) -> None:
        """Ordering (a): stall spends the budget first; a transient-failure
        remediation of the replacement is rejected on the same shared budget."""
        self.dispatch_single_worker("T1")
        self.fake_last_activity("T1", minutes_ago=20)
        process, payload = self.remediate("T1")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "REMEDIATION-RECORDED"), (payload, process.stderr))
        self.assertEqual(payload.get("worker_id"), "T1-r1")

        process, payload = self.worker_terminal("T1-r1", "failed", failure_class="process-timeout")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        process, payload = self.remediate("T1-r1", reason="transient-failure")
        self.assert_blocked(process, payload, "REMEDIATION-BUDGET-SPENT")

        run = run_snapshot(self.root, WORK_ID, self.run_id)
        self.assertNotIn("T1-r2", run["workers"])

    def test_remediate_stall_blocked_after_transient_failure_spent_budget(self) -> None:
        """Ordering (b): a transient-failure retry spends the budget first;
        a stall remediation of the replacement is rejected on the same
        shared budget -- proving the budget is genuinely shared, not two
        independent per-reason budgets under the same field name."""
        self.dispatch_single_worker("T1")
        process, payload = self.worker_terminal("T1", "failed", failure_class="transport-failure")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        process, payload = self.remediate("T1", reason="transient-failure")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "REMEDIATION-RECORDED"), (payload, process.stderr))
        self.assertEqual(payload.get("worker_id"), "T1-r1")

        self.fake_last_activity("T1-r1", minutes_ago=20)
        process, payload = self.remediate("T1-r1", reason="stall")
        self.assert_blocked(process, payload, "REMEDIATION-BUDGET-SPENT")

        run = run_snapshot(self.root, WORK_ID, self.run_id)
        self.assertNotIn("T1-r2", run["workers"])

    # ------------------------------------------------------------------
    # F2 fix -- FR-005's effective concurrent cap also binds remediation:
    # neither remediate_node nor _mint_remediation_worker previously
    # computed or checked it before minting a replacement worker, so only
    # the Store's unconditional five-worker ceiling backed it.
    # ------------------------------------------------------------------

    def test_remediate_rejects_when_replacement_would_exceed_run_activation_cap(self) -> None:
        """With the run's own activation cap at 1 and node A already
        non-terminal, a transient-failure remediation of a DIFFERENT,
        already-FAILED node (B) must be rejected rather than silently
        minting B-r1 and pushing the run's non-terminal worker count to 2."""
        capped_root = Path(self.temporary.name) / "repo-capped"
        build_rebound_v3_repository(capped_root, max_workers=1)
        process, payload = invoke(WORKSPACE, "gauntlet-run", capped_root, "--work-id", WORK_ID)
        if process.returncode != 0 or payload.get("verdict") not in {"RUN-CREATED", "RUN-REUSED"} or process.stderr:
            raise AssertionError((process.returncode, payload, process.stderr))
        run_id = payload["run_id"]
        document = dag_document([dag_node("B", parallel=False), dag_node("A", parallel=False)], max_workers=5)
        (capped_root / "execution-dag.json").write_text(json.dumps(document), encoding="utf-8")

        process, payload = invoke(
            WORKSPACE, "gauntlet-wave-declare", capped_root, "--work-id", WORK_ID, "--run-id", run_id,
            "--dag", "execution-dag.json", "--node-id", "B",
        )
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        process, payload = invoke(
            WORKSPACE, "gauntlet-worker-declare", capped_root, "--work-id", WORK_ID, "--run-id", run_id,
            "--wave-id", "wave-0001", "--node-id", "B", "--tier", "medium", "--files", "tests/fixture-B.py",
            "--dag", "execution-dag.json",
        )
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))
        process, payload = invoke(
            WORKSPACE, "gauntlet-worker-terminal", capped_root, "--work-id", WORK_ID, "--run-id", run_id,
            "--worker-id", "B", "--outcome", "failed", "--failure-class", "process-timeout",
        )
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        # wave-0001 (B's only member) is now COMPLETE, freeing the cap;
        # wave-0002 for A is within it (0 non-terminal + 1 requested <= 1).
        process, payload = invoke(
            WORKSPACE, "gauntlet-wave-declare", capped_root, "--work-id", WORK_ID, "--run-id", run_id,
            "--dag", "execution-dag.json", "--node-id", "A",
        )
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        process, payload = invoke(
            WORKSPACE, "gauntlet-worker-declare", capped_root, "--work-id", WORK_ID, "--run-id", run_id,
            "--wave-id", "wave-0002", "--node-id", "A", "--tier", "medium", "--files", "tests/fixture-A.py",
            "--dag", "execution-dag.json",
        )
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))

        # A is PREPARED (non-terminal) and alone already saturates the cap
        # of 1.  Remediating B -- a different node, currently FAILED with a
        # transient classification -- must be rejected before minting.
        process, payload = invoke(
            WORKSPACE, "gauntlet-remediate", capped_root, "--work-id", WORK_ID, "--run-id", run_id,
            "--worker-id", "B", "--reason", "transient-failure",
        )
        self.assert_blocked(process, payload, "REMEDIATION-CAP-EXCEEDED")

        run = run_snapshot(capped_root, WORK_ID, run_id)
        self.assertNotIn("B-r1", run["workers"])
        self.assertEqual(run["workers"]["A"]["state"], "PREPARED")
        self.assertEqual(run["workers"]["B"]["state"], "FAILED")

    # ------------------------------------------------------------------
    # B1/B2 fixes -- a remediation replacement can record progress and
    # terminate; the original it replaced is STALLED, frees its cap slot,
    # and no longer blocks a dependent's readiness check.
    # ------------------------------------------------------------------

    def test_remediation_replacement_records_progress_and_terminates(self) -> None:
        """B1: record_progress/terminate_worker used to resolve a worker's
        wave via an invariant-asserting helper that is false the moment a
        replacement worker's own wave already went COMPLETE -- both calls
        used to fail ORCHESTRATOR-INVALID for a replacement worker."""
        self.dispatch_single_worker("T1")
        self.fake_last_activity("T1", minutes_ago=20)
        process, payload = self.remediate("T1")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "REMEDIATION-RECORDED"), (payload, process.stderr))
        self.assertEqual(payload.get("worker_id"), "T1-r1")

        process, payload = self.progress_record("T1-r1")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "PROGRESS-RECORDED"), (payload, process.stderr))

        process, payload = self.worker_terminal("T1-r1", "completed")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))
        self.assertEqual(payload.get("state"), "TERMINAL")

    def test_remediated_original_is_stalled_frees_slot_and_unblocks_dependent(self) -> None:
        """B2: nothing used to transition the ORIGINAL worker out of
        PREPARED when a remediation minted its replacement -- it stranded
        forever in PREPARED, permanently occupying a non-terminal-cap slot
        and permanently blocking any dependent node's readiness check."""
        document = dag_document([dag_node("T1", parallel=False), dag_node("T2", depends_on=["T1"], parallel=False)])
        dag_path = self.write_dag(document, name="t1-t2-dag.json")
        process, payload = self.wave_declare(dag_path, ["T1"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        process, payload = self.worker_declare("wave-0001", "T1", dag_path=dag_path)
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))

        self.fake_last_activity("T1", minutes_ago=20)
        process, payload = self.remediate("T1")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "REMEDIATION-RECORDED"), (payload, process.stderr))
        self.assertEqual(payload.get("worker_id"), "T1-r1")

        run = run_snapshot(self.root, WORK_ID, self.run_id)
        self.assertEqual(run["workers"]["T1"]["state"], "STALLED")
        # STALLED is not in NON_TERMINAL_WORKER_STATES: the original's slot
        # is free -- only T1-r1 (PREPARED) occupies the cap.
        non_terminal = [
            worker_id for worker_id, worker in run["workers"].items()
            if worker["state"] in {"DECLARED", "PREPARING", "PREPARED", "RECOVERY_ELIGIBLE", "RECOVERY_RECORDED"}
        ]
        self.assertEqual(non_terminal, ["T1-r1"])

        # T2 depends on T1 -- still not ready while only the STALLED
        # original and the still-PREPARED replacement exist (neither is
        # TERMINAL): T1's lineage head (T1-r1, PREPARED) is not yet
        # TERMINAL, so the dependency-readiness check itself blocks first.
        process, payload = self.wave_declare(dag_path, ["T2"])
        self.assert_blocked(process, payload, "WAVE-NODE-NOT-READY")

        process, payload = self.worker_terminal("T1-r1", "completed")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        # The replacement's success is what the lineage-head resolution
        # (_node_lineage_head/_node_ready) must recognize -- the STALLED
        # original must never be consulted for T1's own readiness.
        process, payload = self.wave_declare(dag_path, ["T2"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))
        self.assertEqual(payload.get("wave_id"), "wave-0002")

    # ------------------------------------------------------------------
    # B5 fix -- a wave member with no worker declared yet is not invisible
    # to wave-completion detection; the wave never completes prematurely,
    # and the never-dispatched member can still be declared into it.
    # ------------------------------------------------------------------

    def test_wave_does_not_complete_prematurely_when_a_member_was_never_declared(self) -> None:
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        dag_path = self.write_dag(document, name="premature-complete-dag.json")
        process, payload = self.wave_declare(dag_path, ["T1", "T2"])
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WAVE-DECLARED"), (payload, process.stderr))

        # Only T1 is ever declared+terminated; T2 -- a real wave member per
        # its own node_ids -- never gets a worker at all.
        process, payload = self.worker_declare("wave-0001", "T1", dag_path=dag_path)
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))
        process, payload = self.worker_terminal("T1", "completed")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        run = run_snapshot(self.root, WORK_ID, self.run_id)
        self.assertEqual(run["waves"]["wave-0001"]["state"], "ACTIVE")
        self.assertEqual(run["waves"]["wave-0001"]["node_ids"], ["T1", "T2"])

        # T2 can still be declared into its own wave -- it was never
        # stranded by a premature COMPLETE.
        process, payload = self.worker_declare("wave-0001", "T2", dag_path=dag_path)
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))
        process, payload = self.worker_terminal("T2", "completed")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-TERMINAL"), (payload, process.stderr))

        run = run_snapshot(self.root, WORK_ID, self.run_id)
        self.assertEqual(run["waves"]["wave-0001"]["state"], "COMPLETE")


if __name__ == "__main__":
    unittest.main()
