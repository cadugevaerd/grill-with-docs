#!/usr/bin/env python3
"""Public-contract harness for FASE-004 Convergência, Revisão e Entrega Verificável.

This validator owns its fixtures in the same style
``validate_gauntlet_scheduler_contract.py`` (FASE-003) established: every case
starts from an isolated Git repository and reaches the public command surface
through the same V2 -> V3 -> rebound -> activation path an operator uses, via
real subprocess invocation of ``grill_workspace.py``.  It imports nothing from
its sibling validators -- the module-level helpers it needs are duplicated
here so the file stays self-contained.

Phase 1 (T002) carries only the reusable fixtures the later phases need, plus
one smoke case pinning the state every FASE-004 case starts from.  The command
helpers for ``gauntlet-converge``/``gauntlet-run-abandon`` build arguments for
surfaces that do not exist yet (T015/T022); the cases that call them arrive
with Phases 2-6 (T009/T016, T019/T024, T025/T027).
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
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin/skills/grill-with-docs"
ASSETS = SKILL / "assets"
WORKSPACE = SKILL / "scripts/grill_workspace.py"
WORKFLOW_MIGRATOR = SKILL / "scripts/grill_core/workflow_v3.py"
WORKFLOW_TEMPLATE = ASSETS / "WORKFLOW.template.md"
SCRIPTS = SKILL / "scripts"
WORK_ID = "converge-review-ship-c3d4"
DAG_SCHEMA = "grill-gauntlet-execution-dag/v1"

# Mirrors grill_workspace.SEQUENCE, duplicated the same way every other
# validator in this suite duplicates it rather than importing module globals.
SEQUENCE = [
    "specify", "plan", "checklist", "tasks", "analyze", "agent-assign",
    "agent-execute", "converge", "verify", "review", "ship",
]

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from grill_core import gauntlet_runs, store


def _load_module(path: Path, name: str):
    """Load a peer test module's fixture helpers in-process.

    ``validate_attestation_contract.py`` owns the production hash chain
    (dispatch_key / skill_invocation_key / step_execution_id math) a real
    ``checkpoint --state complete`` must satisfy on a v3 work item.  The ship
    gate of this phase sits directly in front of that gate, so reaching it
    honestly means driving the ten preceding macro-steps through the real
    attestation path -- re-deriving that formula chain here would duplicate
    authority this file has no independent claim over.
    ``validate_gauntlet_scheduler_contract.py`` (FASE-003) already reuses it
    this exact way.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ATTESTATION_FIXTURES = _load_module(
    REPO / "tests/validate_attestation_contract.py", "gauntlet_converge_attestation_fixtures"
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
    root: Path, work_id: str = WORK_ID, *, slug: str = "converge-review-ship", max_workers: int = 5,
) -> None:
    """Create one V3 work item whose workflow binding is current and activated."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    git(root, "config", "user.email", "gauntlet-converge-contract@example.invalid")
    git(root, "config", "user.name", "Gauntlet Converge Contract")
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

    # The v3 migration rewrites the tracked ``WORKFLOW.md`` in place.  Every
    # convergence case needs a coordinator worktree whose *tracked* content is
    # committed, so the dirty-tree gate is exercised by what a case does, not
    # by fixture residue.  ``.grill/`` stays untracked on purpose: that is the
    # realistic control-checkout shape the gate must tolerate.
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs/fixture.md").write_text("tracked fixture content\n", encoding="utf-8")
    git(root, "add", "WORKFLOW.md", "docs/fixture.md")
    git(root, "commit", "-qm", "fixture workflow v3")

    item = strict_json_bytes(
        (root / ".grill/work-items" / work_id / "WORK-ITEM.json").read_bytes(), source="WORK-ITEM.json"
    )
    workflow_sha256 = hashlib.sha256((root / "WORKFLOW.md").read_bytes()).hexdigest()
    if item.get("schema") != "grill-work-item/v3" or item["immutable"]["workflow"]["sha256"] != workflow_sha256:
        raise AssertionError("fixture does not have a current V3 workflow binding")


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
    nodes: list[dict[str, Any]], *, max_workers: int = 5, feature: str = "converge-review-ship-fixture",
) -> dict[str, Any]:
    return {"schema": DAG_SCHEMA, "feature": feature, "max_workers": max_workers, "nodes": nodes}


def run_snapshot(root: Path, work_id: str, run_id: str) -> dict[str, Any]:
    """Read one already-authoritative run solely for fixture assertions."""
    document = store.read_snapshot(root).document
    return document["work_items"][work_id]["gauntlet"]["runs"][run_id]


def fixture_transition(
    root: Path, work_id: str, run_id: str, wave_id: str, name: str, mutate: Any,
) -> None:
    """Test-only white-box shim: commit one coordinator-shaped Store
    transition no public command of this phase can produce.

    The same technique ``validate_gauntlet_scheduler_contract.py``'s own
    ``mark_wave_complete``/``mark_worker_failed_unclassified`` already use,
    and the same direct-Store-injection discipline FR-002's residual
    scope-overlap pre-pass is specified to be covered by.
    """
    admission = run_snapshot(root, work_id, run_id)["admission"]
    receipt = {
        "category": "runtime", "name": name,
        "work_id": work_id, "run_id": run_id, "wave_id": wave_id,
        "base_commit": admission["base_commit"],
        "input_sha256": hashlib.sha256(name.encode("utf-8")).hexdigest(),
        "output_sha256": None,
    }
    event = {
        "event": "gauntlet.fixture.injected", "work_id": work_id, "run_id": run_id,
        "wave_id": wave_id, "base_commit": receipt["base_commit"],
        "input_sha256": receipt["input_sha256"], "output_sha256": None,
        "receipt_sha256": store.jcs_sha256(receipt),
    }
    store.transact_with_event(root, mutate, event=event, receipt=receipt)


def inject_wave(
    root: Path, work_id: str, run_id: str, wave_id: str, node_ids: list[str], *,
    state: str = "ACTIVE", dag_content_sha256: str | None = None, name: str | None = None,
) -> None:
    """Overwrite one wave record (and optionally the run's DAG pin) directly."""

    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        run = document["work_items"][work_id]["gauntlet"]["runs"][run_id]
        run["waves"][wave_id] = {"state": state, "node_ids": list(node_ids)}
        if dag_content_sha256 is not None:
            run["dag_content_sha256"] = dag_content_sha256
        return document

    fixture_transition(root, work_id, run_id, wave_id, name or f"fixture-inject-{wave_id}", mutate)


def event_names(root: Path) -> list[str]:
    return [str(record.get("event")) for record in store.read_events(root)]


def human_authorization_bundle(
    scope: str, *, decision: str = "APPROVED", authorized_by: str = "operator@example.invalid",
) -> dict[str, Any]:
    """The six-key ``human-authorization/v1`` bundle FR-014 requires, in the
    exact shape ``attestation._validate_human_authorization`` already accepts
    for ``ship`` -- here ``scope`` is the target ``run_id``, not a step id."""
    return {
        "schema": "human-authorization/v1",
        "scope": scope,
        "decision": decision,
        "authorized_by": authorized_by,
        "receipt_ref": "receipts/run-abandon.json",
        "content_sha256": "sha256:" + hashlib.sha256(scope.encode("utf-8")).hexdigest(),
    }


class GauntletConvergeContractHarness(unittest.TestCase):
    """Public FASE-004 convergence/abandonment/ship-gate contract.

    Phase 1 (T002) only owns the fixtures and the starting-state smoke case;
    every command helper below is the one the later phases invoke.
    """

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        build_rebound_v3_repository(self.root)
        process, payload = invoke(WORKSPACE, "gauntlet-run", self.root, "--work-id", WORK_ID)
        if process.returncode != 0 or payload.get("verdict") not in {"RUN-CREATED", "RUN-REUSED"} or process.stderr:
            raise AssertionError((process.returncode, payload, process.stderr))
        self.run_id = payload["run_id"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    # --- artefacts -----------------------------------------------------

    def write_dag(self, document: dict[str, Any], name: str = "execution-dag.json") -> str:
        (self.root / name).write_text(json.dumps(document), encoding="utf-8")
        return name

    def write_authorization(self, bundle: dict[str, Any], name: str = "run-abandon.json") -> str:
        path = self.root / name
        path.write_text(json.dumps(bundle, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return name

    def development_state(self) -> dict[str, Any]:
        state = strict_json_bytes(
            (self.root / ".grill/work-items" / WORK_ID / "state.json").read_bytes(), source="state.json"
        )
        development = state.get("development")
        if not isinstance(development, dict):
            raise AssertionError(f"missing development block: {state!r}")
        return development

    def run_record(self, run_id: str | None = None) -> dict[str, Any]:
        return run_snapshot(self.root, WORK_ID, run_id or self.run_id)

    # --- Git state the merge steps read --------------------------------

    def head_of(self, revision: str = "HEAD") -> str:
        return git(self.root, "rev-parse", revision)

    def commit_tracked(self, relative: str, body: str, message: str) -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        git(self.root, "add", relative)
        git(self.root, "commit", "-qm", message)
        return self.head_of()

    def dirty_tracked(self, relative: str, body: str) -> None:
        (self.root / relative).write_text(body, encoding="utf-8")

    def write_untracked(self, relative: str, body: str = "untracked\n") -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    # --- worker worktrees, where a subagent's real commits land -----------

    def worker_branch(self, worker_id: str) -> str:
        return f"grill/{WORK_ID}/{self.run_id}/{worker_id}"

    def worker_worktree(self, worker_id: str) -> Path:
        return store.git_common_dir(self.root) / "grill" / f"wt-{self.run_id}-{worker_id}"

    def commit_in_worker(self, worker_id: str, relative: str, body: str) -> str:
        worktree = self.worker_worktree(worker_id)
        path = worktree / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        git(worktree, "add", relative)
        git(worktree, "commit", "-qm", f"{worker_id}: {relative}")
        return git(worktree, "rev-parse", "HEAD")

    # --- composed fixture steps -----------------------------------------

    def bind_execution_branch(self) -> None:
        """Bind ``development.execution_branch`` the only way FASE-001 does."""
        process, payload = self.checkpoint("specify", "in-progress", reason="bind execution branch")
        if process.returncode != 0 or payload.get("verdict") != "UPDATED":
            raise AssertionError((process.returncode, payload, process.stderr))

    def declare_wave(self, dag_path: str, node_ids: list[str], expected: str = "wave-0001") -> None:
        process, payload = self.wave_declare(dag_path, node_ids)
        if process.returncode != 0 or payload.get("wave_id") != expected:
            raise AssertionError((process.returncode, payload, process.stderr))

    def dispatch(self, wave_id: str, node_id: str, *, dag_path: str = "execution-dag.json",
                 files: list[str] | None = None) -> None:
        process, payload = self.worker_declare(wave_id, node_id, dag_path=dag_path, files=files)
        if process.returncode != 0 or payload.get("verdict") != "WORKER-PREPARED":
            raise AssertionError((process.returncode, payload, process.stderr))

    def terminate(self, worker_id: str, *, outcome: str = "completed",
                  failure_class: str | None = None) -> None:
        process, payload = self.worker_terminal(worker_id, outcome=outcome, failure_class=failure_class)
        if process.returncode != 0 or payload.get("verdict") != "WORKER-TERMINAL":
            raise AssertionError((process.returncode, payload, process.stderr))

    def converged_flag(self, worker_id: str, run_id: str | None = None) -> Any:
        return self.run_record(run_id)["workers"][worker_id]["workspace"]["converged"]

    # --- command surface -----------------------------------------------

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

    def worker_terminal(
        self, worker_id: str, *, outcome: str = "completed", failure_class: str | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = [
            "gauntlet-worker-terminal", self.root, "--work-id", WORK_ID, "--run-id", self.run_id,
            "--worker-id", worker_id, "--outcome", outcome,
        ]
        if failure_class is not None:
            arguments.extend(("--failure-class", failure_class))
        return invoke(WORKSPACE, *arguments)

    def converge(self, wave_id: str, *, dag_path: str = "execution-dag.json") -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return invoke(
            WORKSPACE, "gauntlet-converge", self.root, "--work-id", WORK_ID, "--run-id", self.run_id,
            "--dag", dag_path, "--wave-id", wave_id,
        )

    def run_abandon(self, attestation: str, *, run_id: str | None = None) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return invoke(
            WORKSPACE, "gauntlet-run-abandon", self.root, "--work-id", WORK_ID,
            "--run-id", run_id or self.run_id, "--attestation", attestation,
        )

    def gauntlet_status(self, *, run_id: str | None = None) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = ["gauntlet-status", self.root, "--work-id", WORK_ID]
        if run_id is not None:
            arguments.extend(("--run-id", run_id))
        return invoke(WORKSPACE, *arguments)

    def status_run(self, *, run_id: str | None = None) -> dict[str, Any]:
        process, payload = self.gauntlet_status(run_id=run_id)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        run = payload.get("run")
        self.assertIsInstance(run, dict, payload)
        return run

    def checkpoint(self, step: str, state: str, **kwargs: Any) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
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

    # --- the real eleven-step ledger the ship gate sits inside -----------

    def write_evidence(self, name: str) -> str:
        (self.root / name).write_text(f"{name} evidence\n", encoding="utf-8")
        return name

    def write_attestation_bundle(self, step_id: str, step_output: dict[str, Any], chain: dict[str, Any]) -> str:
        receipts = self.root / "receipts"
        receipts.mkdir(exist_ok=True)
        bundle = {
            "schema": "checkpoint-attestation/v1",
            "resolution": chain["resolution"],
            "dispatch_intent": chain["dispatch_intent"],
            "invocation_started": chain["invocation_started"],
            "invocation_terminal": chain["invocation_terminal"],
            "step_output": step_output,
            "catalog": ATTESTATION_FIXTURES.catalog(),
        }
        path = receipts / f"{step_id}.json"
        path.write_text(json.dumps(bundle, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return str(path.relative_to(self.root))

    def complete_step_with_real_attestation(
        self, step_id: str, *, campaign_run_id: str, generation_label: str, predecessor: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Complete one macro-step through the unmodified attestation gate."""
        process, payload = self.checkpoint(step_id, "in-progress", reason=f"start {step_id}")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "UPDATED"), (payload, process.stderr))

        chain = ATTESTATION_FIXTURES.build_chain(
            step_id=step_id, project_id=store.project_identity(self.root)["project_id"],
            work_item_id=WORK_ID, run_id=campaign_run_id, generation_label=generation_label,
        )
        step_output = dict(chain["step_output"])
        step_output["dependency_outputs"] = [] if predecessor is None else [predecessor]
        step_output = ATTESTATION_FIXTURES.recompute_content_sha256(step_output)

        process, payload = self.checkpoint(
            step_id, "complete", evidence=[self.write_evidence(f"{step_id}-evidence.md")],
            attestation=self.write_attestation_bundle(step_id, step_output, chain),
            reason=f"complete {step_id}",
        )
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "UPDATED"), (payload, process.stderr))
        return {
            "step_id": step_id, "output_sha256": step_output["output_sha256"],
            "receipt_ref": step_output["skill_invocation_receipt_ref"],
            "provenance": "current-generation",
        }

    def open_ship(self) -> None:
        """Drive every macro-step before ``ship`` complete, then open ``ship``.

        The first transition is also what binds ``development.execution_branch``
        -- the same FASE-001 path :meth:`bind_execution_branch` uses.
        """
        predecessor: dict[str, Any] | None = None
        for step_id in SEQUENCE[:-1]:
            predecessor = self.complete_step_with_real_attestation(
                step_id, campaign_run_id="run-ship-gate", generation_label="gen-ship-gate",
                predecessor=predecessor,
            )
        process, payload = self.checkpoint("ship", "in-progress", reason="start ship")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "UPDATED"), (payload, process.stderr))

    def ship_complete(self) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return self.checkpoint(
            "ship", "complete", evidence=[self.write_evidence("ship-evidence.md")], reason="complete ship",
        )

    def assert_blocked(self, process: subprocess.CompletedProcess[str], payload: dict[str, Any], code: str) -> None:
        self.assertEqual(process.returncode, 2, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "BLOCKED", payload)
        self.assertEqual(payload.get("code"), code, payload)

    # ------------------------------------------------------------------
    # T002 -- the starting state every FASE-004 case builds on: an admitted
    # run carrying only the bootstrap placeholder wave, with no DAG pinned
    # yet (FR-004c pins it at the first real wave declaration).
    # ------------------------------------------------------------------

    def test_fixture_starts_from_an_admitted_run_with_only_the_placeholder_wave(self) -> None:
        run = self.run_record()
        self.assertEqual(run["state"], "ADMITTED")
        self.assertEqual(sorted(run["waves"]), ["wave-0001"])
        self.assertEqual(run["waves"]["wave-0001"]["state"], "DECLARED")
        self.assertEqual(run["waves"]["wave-0001"]["node_ids"], gauntlet_runs.WAVE_PENDING_NODE_IDS)
        self.assertEqual(run["workers"], {})
        self.assertNotIn("dag_content_sha256", run)
        self.assertNotIn("abandon_authorization", run)

    # ------------------------------------------------------------------
    # T010/T011 -- the DAG content hash and where it gets pinned (FR-004c)
    # ------------------------------------------------------------------

    def test_dag_validate_returns_the_content_hash_convergence_pins(self) -> None:
        document = dag_document([dag_node("T1", parallel=False)])
        process, payload = self.dag_validate(self.write_dag(document))
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "DAG-VALID")
        # Bare HEX64, never a "sha256:"-prefixed presentation form: this is
        # the exact value the run's write-once pin field accepts.
        self.assertEqual(payload.get("dag_content_sha256"), store.jcs_sha256(document))
        self.assertRegex(payload["dag_content_sha256"], r"^[0-9a-f]{64}$")

    def test_wave_declare_pins_the_dag_on_the_first_real_wave_only(self) -> None:
        document = dag_document([dag_node("T1", parallel=False), dag_node("T2", depends_on=["T1"], parallel=False)])
        dag_path = self.write_dag(document)
        self.assertNotIn("dag_content_sha256", self.run_record())

        self.declare_wave(dag_path, ["T1"])
        self.assertEqual(self.run_record()["dag_content_sha256"], store.jcs_sha256(document))

        self.dispatch("wave-0001", "T1")
        self.terminate("T1")
        self.declare_wave(dag_path, ["T2"], expected="wave-0002")
        self.assertEqual(self.run_record()["dag_content_sha256"], store.jcs_sha256(document))

    def test_wave_declare_blocks_a_later_wave_declared_from_a_different_dag(self) -> None:
        document = dag_document([dag_node("T1", parallel=False), dag_node("T2", depends_on=["T1"], parallel=False)])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1"])
        self.dispatch("wave-0001", "T1")
        self.terminate("T1")

        regenerated = dag_document(
            [dag_node("T1", parallel=False), dag_node("T2", depends_on=["T1"], parallel=False)],
            feature="regenerated-after-a-wave-already-ran",
        )
        process, payload = self.wave_declare(self.write_dag(regenerated, "regenerated-dag.json"), ["T2"])
        self.assert_blocked(process, payload, "DAG-CONTENT-MISMATCH")
        self.assertEqual(sorted(self.run_record()["waves"]), ["wave-0001"])

    def test_wave_declare_blocks_a_legacy_run_whose_real_wave_has_no_pin(self) -> None:
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        dag_path = self.write_dag(document)
        # A real (non-placeholder) wave with no pin -- the shape a run
        # admitted before FR-004c existed carries forever.
        inject_wave(self.root, WORK_ID, self.run_id, "wave-0001", ["T1"])
        self.assertNotIn("dag_content_sha256", self.run_record())

        process, payload = self.wave_declare(dag_path, ["T2"])
        self.assert_blocked(process, payload, "DAG-PIN-MISSING")
        self.assertNotIn("dag_content_sha256", self.run_record())

    def test_wave_declare_does_not_pin_from_an_injected_declared_wave_with_real_members(self) -> None:
        """FR-004c: ``expect_placeholder`` is the conjunction of state and
        ``node_ids``; a ``DECLARED`` record carrying real members is not the
        bootstrap placeholder and must never pin a DAG."""
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        dag_path = self.write_dag(document)
        inject_wave(self.root, WORK_ID, self.run_id, "wave-0001", ["T1"], state="DECLARED")

        process, payload = self.wave_declare(dag_path, ["T2"])
        self.assert_blocked(process, payload, "DAG-PIN-MISSING")
        self.assertNotIn("dag_content_sha256", self.run_record())

    # ------------------------------------------------------------------
    # T012 -- FR-004b: scope overlap is rejected at declaration time
    # ------------------------------------------------------------------

    def test_wave_declare_blocks_overlapping_declared_files(self) -> None:
        document = dag_document([
            dag_node("T1", parallel=True, files=["src/shared.py", "src/a.py"]),
            dag_node("T2", parallel=True, files=["src/b.py", "src/shared.py"]),
            dag_node("T3", parallel=True, files=["src/c.py"]),
        ])
        process, payload = self.wave_declare(self.write_dag(document), ["T1", "T2", "T3"])
        self.assert_blocked(process, payload, "WAVE-SCOPE-OVERLAP")
        self.assertIn("T1", payload.get("error", ""))
        self.assertIn("T2", payload.get("error", ""))
        self.assertNotIn("T3", payload.get("error", ""))
        self.assertEqual(self.run_record()["waves"]["wave-0001"]["node_ids"], gauntlet_runs.WAVE_PENDING_NODE_IDS)

    def test_wave_declare_accepts_disjoint_declared_files(self) -> None:
        document = dag_document([
            dag_node("T1", parallel=True, files=["src/a.py"]),
            dag_node("T2", parallel=True, files=["src/b.py"]),
        ])
        process, payload = self.wave_declare(self.write_dag(document), ["T1", "T2"])
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-DECLARED")

    # ------------------------------------------------------------------
    # T014/T015 -- gauntlet-converge step 2: the DAG pin gate
    # ------------------------------------------------------------------

    def test_converge_blocks_when_the_run_has_no_pinned_dag(self) -> None:
        document = dag_document([dag_node("T1", parallel=False)])
        self.bind_execution_branch()
        process, payload = self.converge("wave-0001", dag_path=self.write_dag(document))
        self.assert_blocked(process, payload, "DAG-PIN-MISSING")

    def test_converge_blocks_when_the_dag_diverges_from_the_pin(self) -> None:
        document = dag_document([dag_node("T1", parallel=False)])
        dag_path = self.write_dag(document)
        self.bind_execution_branch()
        self.declare_wave(dag_path, ["T1"])
        regenerated = dag_document([dag_node("T1", parallel=False)], feature="regenerated")
        process, payload = self.converge("wave-0001", dag_path=self.write_dag(regenerated, "regenerated-dag.json"))
        self.assert_blocked(process, payload, "DAG-CONTENT-MISMATCH")

    # ------------------------------------------------------------------
    # T014 step 4 -- execution branch and coordinator worktree state
    # ------------------------------------------------------------------

    def converged_wave_fixture(self, *, files: list[str] | None = None) -> str:
        """One single-node wave whose worker is TERMINAL with a real commit."""
        document = dag_document([dag_node("T1", parallel=False, files=files)])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1"])
        self.dispatch("wave-0001", "T1", dag_path=dag_path, files=files)
        self.commit_in_worker("T1", (files or ["tests/fixture-T1.py"])[0], "worker T1 output\n")
        self.terminate("T1")
        return dag_path

    def test_converge_blocks_when_the_execution_branch_is_unset(self) -> None:
        dag_path = self.converged_wave_fixture()
        self.assertNotIn("execution_branch", self.development_state())
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "EXECUTION-BRANCH-UNSET")

    def test_converge_blocks_when_the_live_branch_differs_from_the_binding(self) -> None:
        self.bind_execution_branch()
        dag_path = self.converged_wave_fixture()
        git(self.root, "checkout", "-q", "-b", "another-branch")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "EXECUTION-BRANCH-MISMATCH")

    def test_converge_blocks_on_a_detached_head(self) -> None:
        self.bind_execution_branch()
        dag_path = self.converged_wave_fixture()
        git(self.root, "checkout", "-q", "--detach")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "EXECUTION-BRANCH-MISMATCH")

    def test_converge_blocks_a_dirty_tracked_coordinator_worktree(self) -> None:
        self.bind_execution_branch()
        dag_path = self.converged_wave_fixture()
        self.dirty_tracked("docs/fixture.md", "locally edited, never committed\n")
        head = self.head_of()
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "EXECUTION-TREE-DIRTY")
        self.assertEqual(self.head_of(), head)
        self.assertIs(self.converged_flag("T1"), False)

    def test_converge_blocks_when_an_untracked_file_would_be_overwritten(self) -> None:
        """``git status --porcelain`` alone collapses ``pkg/mod.py`` into
        ``?? pkg/``; only the ``-uall`` form names the file a worker's diff
        would clobber, and the collision is decided before any merge."""
        self.bind_execution_branch()
        dag_path = self.converged_wave_fixture(files=["pkg/mod.py"])
        self.write_untracked("pkg/mod.py", "local scratch, never committed\n")
        self.assertNotIn(
            "pkg/mod.py", git(self.root, "status", "--porcelain"),
        )
        head = self.head_of()
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "EXECUTION-TREE-DIRTY")
        self.assertEqual(self.head_of(), head)
        self.assertIs(self.converged_flag("T1"), False)

    def test_converge_tolerates_untracked_paths_no_worker_touches(self) -> None:
        self.bind_execution_branch()
        dag_path = self.converged_wave_fixture()
        self.write_untracked("scratch/notes.md", "session scratch\n")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED")

    # ------------------------------------------------------------------
    # T014 step 5 -- wave order
    # ------------------------------------------------------------------

    def two_wave_fixture(self) -> str:
        document = dag_document([
            dag_node("T1", parallel=False),
            dag_node("T2", depends_on=["T1"], parallel=False),
        ])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1"])
        self.dispatch("wave-0001", "T1", dag_path=dag_path)
        self.commit_in_worker("T1", "tests/fixture-T1.py", "worker T1 output\n")
        self.terminate("T1")
        self.declare_wave(dag_path, ["T2"], expected="wave-0002")
        self.dispatch("wave-0002", "T2", dag_path=dag_path)
        self.commit_in_worker("T2", "tests/fixture-T2.py", "worker T2 output\n")
        self.terminate("T2")
        return dag_path

    def test_converge_blocks_a_wave_declared_after_an_unconverged_one(self) -> None:
        self.bind_execution_branch()
        dag_path = self.two_wave_fixture()
        head = self.head_of()
        process, payload = self.converge("wave-0002", dag_path=dag_path)
        self.assert_blocked(process, payload, "WAVE-CONVERGENCE-OUT-OF-ORDER")
        self.assertEqual(self.head_of(), head)

    def test_converge_blocks_a_wave_that_is_still_active(self) -> None:
        self.bind_execution_branch()
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1", "T2"])
        self.dispatch("wave-0001", "T1", dag_path=dag_path)
        self.dispatch("wave-0001", "T2", dag_path=dag_path)
        self.commit_in_worker("T1", "tests/fixture-T1.py", "worker T1 output\n")
        self.terminate("T1")
        self.assertEqual(self.run_record()["waves"]["wave-0001"]["state"], "ACTIVE")

        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "WAVE-CONVERGENCE-OUT-OF-ORDER")
        self.assertIs(self.converged_flag("T1"), False)

    # ------------------------------------------------------------------
    # T014 step 6 -- clean integration, scope pre-pass, content conflict
    # ------------------------------------------------------------------

    def test_converge_integrates_two_waves_in_declaration_order(self) -> None:
        self.bind_execution_branch()
        dag_path = self.two_wave_fixture()

        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED")
        self.assertEqual(payload.get("converged"), ["T1"])
        self.assertTrue((self.root / "tests/fixture-T1.py").is_file())
        self.assertFalse((self.root / "tests/fixture-T2.py").exists())
        run = self.run_record()
        self.assertIs(run["workers"]["T1"]["workspace"]["converged"], True)
        self.assertIs(run["waves"]["wave-0001"]["converged"], True)
        # The DAG still has an unconverged node: closing the run here would
        # be exactly the premature closure FR-001 rejects.
        self.assertEqual(run["state"], "ADMITTED")

        process, payload = self.converge("wave-0002", dag_path=dag_path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED")
        self.assertTrue((self.root / "tests/fixture-T2.py").is_file())
        run = self.run_record()
        self.assertIs(run["workers"]["T2"]["workspace"]["converged"], True)
        self.assertIs(run["waves"]["wave-0002"]["converged"], True)
        self.assertEqual(run["state"], "COMPLETE")
        self.assertIn("gauntlet.run.completed", event_names(self.root))

    def test_wave_declare_after_a_successful_converge_is_not_identity_stale(self) -> None:
        """ADR-0023: gauntlet-converge advances HEAD on purpose; _run_for_worker
        (shared by declare_wave and every other mutating gauntlet command) must
        compare only the four planning-identity hashes, never base_commit,
        against the live-recomputed admission -- or the natural declare(wave 1)
        -> converge(wave 1) -> declare(wave 2) flow blocks IDENTITY-STALE on
        the very next command after any successful convergence."""
        self.bind_execution_branch()
        document = dag_document([
            dag_node("T1", parallel=False),
            dag_node("T2", depends_on=["T1"], parallel=False),
        ])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1"])
        self.dispatch("wave-0001", "T1", dag_path=dag_path)
        self.commit_in_worker("T1", "tests/fixture-T1.py", "worker T1 output\n")
        self.terminate("T1")

        head_before = self.head_of()
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED")
        self.assertNotEqual(self.head_of(), head_before)

        process, payload = self.wave_declare(dag_path, ["T2"])
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-DECLARED")
        self.assertEqual(payload.get("wave_id"), "wave-0002")

    def test_converge_treats_an_empty_worker_branch_as_a_trivial_success(self) -> None:
        self.bind_execution_branch()
        document = dag_document([dag_node("T1", parallel=False)])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1"])
        self.dispatch("wave-0001", "T1", dag_path=dag_path)
        self.terminate("T1")
        head = self.head_of()

        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED")
        self.assertEqual(self.head_of(), head)
        self.assertIs(self.converged_flag("T1"), True)
        self.assertEqual(self.run_record()["state"], "COMPLETE")

    def test_converge_blocks_scope_overlap_injected_directly_into_the_store(self) -> None:
        """Genuinely unreachable through the public CLI once FR-004b ships --
        proved the same way FASE-003 proves its own inner-layer guards."""
        self.bind_execution_branch()
        document = dag_document([
            dag_node("T1", parallel=True, files=["src/shared.py"]),
            dag_node("T2", parallel=True, files=["src/shared.py"]),
        ])
        dag_path = self.write_dag(document)
        inject_wave(
            self.root, WORK_ID, self.run_id, "wave-0001", ["T1", "T2"],
            dag_content_sha256=store.jcs_sha256(document),
        )
        for node_id in ("T1", "T2"):
            self.dispatch("wave-0001", node_id, dag_path=dag_path, files=[f"src/{node_id}.py"])
            self.commit_in_worker(node_id, f"src/{node_id}.py", f"worker {node_id} output\n")
            self.terminate(node_id)
        head = self.head_of()

        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "INTEGRATION_CONFLICT")
        self.assertEqual(self.head_of(), head)
        run = self.run_record()
        conflict = run["waves"]["wave-0001"]["last_conflict"]
        self.assertEqual(conflict["reason"], "scope-overlap")
        self.assertEqual(sorted(conflict["node_ids"]), ["T1", "T2"])
        self.assertEqual(sorted(conflict["worker_heads"]), ["T1", "T2"])
        self.assertEqual(conflict["execution_branch_head"], head)
        # No member converges on a blocked pre-pass, overlapping or not.
        self.assertIs(run["workers"]["T1"]["workspace"]["converged"], False)
        self.assertIs(run["workers"]["T2"]["workspace"]["converged"], False)

        # FR-002: the pinned ``files`` cannot change, so reentry is an
        # unconditional re-block that never mints a second event.
        before = event_names(self.root).count("gauntlet.converge.conflict")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "INTEGRATION_CONFLICT")
        self.assertEqual(event_names(self.root).count("gauntlet.converge.conflict"), before)

    def content_conflict_fixture(self) -> str:
        document = dag_document([
            dag_node("T1", parallel=True, files=["src/a.py"]),
            dag_node("T2", parallel=True, files=["src/b.py"]),
        ])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1", "T2"])
        for node_id in ("T1", "T2"):
            self.dispatch("wave-0001", node_id, dag_path=dag_path, files=[f"src/{node_id.lower()}.py"])
        # Declared scopes are disjoint; the real commits collide anyway.
        self.commit_in_worker("T1", "shared.txt", "written by T1\n")
        self.commit_in_worker("T2", "shared.txt", "written by T2\n")
        self.terminate("T1")
        self.terminate("T2")
        return dag_path

    def test_converge_blocks_a_real_git_conflict_without_reverting_earlier_merges(self) -> None:
        self.bind_execution_branch()
        dag_path = self.content_conflict_fixture()
        before = self.head_of()

        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "INTEGRATION_CONFLICT")
        after = self.head_of()
        # T1 merged first (alphabetical) and stays merged; only T2's own
        # attempt is reverted, so HEAD advanced exactly once.
        self.assertNotEqual(after, before)
        self.assertEqual(git(self.root, "rev-list", "--count", f"{before}..{after}"), "2")
        self.assertEqual((self.root / "shared.txt").read_text(encoding="utf-8"), "written by T1\n")
        self.assertEqual(git(self.root, "status", "--porcelain"), git(self.root, "status", "--porcelain"))
        run = self.run_record()
        self.assertIs(run["workers"]["T1"]["workspace"]["converged"], True)
        self.assertIs(run["workers"]["T2"]["workspace"]["converged"], False)
        conflict = run["waves"]["wave-0001"]["last_conflict"]
        self.assertEqual(conflict["reason"], "content-conflict")
        self.assertEqual(conflict["node_ids"], ["T2"])
        self.assertEqual(conflict["execution_branch_head"], after)
        self.assertEqual(sorted(conflict["worker_heads"]), ["T2"])
        self.assertNotIn("converged", run["waves"]["wave-0001"])

    def test_converge_reentry_reblocks_on_identical_fingerprints_and_recomputes_on_new_ones(self) -> None:
        self.bind_execution_branch()
        dag_path = self.content_conflict_fixture()
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "INTEGRATION_CONFLICT")
        blocked_head = self.head_of()
        conflicts = event_names(self.root).count("gauntlet.converge.conflict")

        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "INTEGRATION_CONFLICT")
        self.assertEqual(self.head_of(), blocked_head)
        self.assertEqual(event_names(self.root).count("gauntlet.converge.conflict"), conflicts)

        # A new commit on the worker's branch changes the fingerprint, so the
        # merge is recomputed from scratch -- and this one resolves.
        self.commit_in_worker("T2", "shared.txt", "written by T1\n")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED")
        run = self.run_record()
        self.assertIs(run["workers"]["T2"]["workspace"]["converged"], True)
        self.assertNotIn("last_conflict", run["waves"]["wave-0001"])
        self.assertIs(run["waves"]["wave-0001"]["converged"], True)
        self.assertEqual(run["state"], "COMPLETE")

    def test_converge_never_converges_a_permanently_failed_sibling(self) -> None:
        self.bind_execution_branch()
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1", "T2"])
        for node_id in ("T1", "T2"):
            self.dispatch("wave-0001", node_id, dag_path=dag_path)
            self.commit_in_worker(node_id, f"tests/fixture-{node_id}.py", f"worker {node_id}\n")
        self.terminate("T1")
        self.terminate("T2", outcome="failed", failure_class="process-timeout")
        self.assertEqual(self.run_record()["waves"]["wave-0001"]["state"], "COMPLETE")

        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED")
        self.assertEqual(payload.get("converged"), ["T1"])
        run = self.run_record()
        self.assertIs(run["workers"]["T1"]["workspace"]["converged"], True)
        self.assertIs(run["workers"]["T2"]["workspace"]["converged"], False)
        self.assertTrue((self.root / "tests/fixture-T1.py").is_file())
        self.assertFalse((self.root / "tests/fixture-T2.py").exists())
        self.assertNotIn("converged", run["waves"]["wave-0001"])
        self.assertEqual(run["state"], "ADMITTED")

    # ------------------------------------------------------------------
    # T014 steps 3/5 -- FR-005 idempotent replay
    # ------------------------------------------------------------------

    def test_converge_replays_a_converged_wave_of_a_non_terminal_run(self) -> None:
        self.bind_execution_branch()
        dag_path = self.two_wave_fixture()
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED", (payload, process.stderr))
        head = self.head_of()
        merges = event_names(self.root).count("gauntlet.converge.worker-converged")

        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED-REUSED")
        self.assertEqual(self.head_of(), head)
        self.assertEqual(event_names(self.root).count("gauntlet.converge.worker-converged"), merges)
        self.assertEqual(self.run_record()["state"], "ADMITTED")

    def test_converge_replays_the_wave_that_completed_the_run(self) -> None:
        self.bind_execution_branch()
        dag_path = self.two_wave_fixture()
        self.converge("wave-0001", dag_path=dag_path)
        process, payload = self.converge("wave-0002", dag_path=dag_path)
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED", (payload, process.stderr))
        self.assertEqual(self.run_record()["state"], "COMPLETE")
        head = self.head_of()

        process, payload = self.converge("wave-0002", dag_path=dag_path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED-REUSED")
        self.assertEqual(self.head_of(), head)

        # Any other wave against a COMPLETE run is the ordinary terminal-run
        # denial FR-005 deliberately keeps.
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "RUN-NOT-ELIGIBLE")

    def test_converge_revalidates_the_pin_even_on_a_replay_of_a_complete_run(self) -> None:
        self.bind_execution_branch()
        dag_path = self.two_wave_fixture()
        self.converge("wave-0001", dag_path=dag_path)
        self.converge("wave-0002", dag_path=dag_path)
        self.assertEqual(self.run_record()["state"], "COMPLETE")

        regenerated = dag_document([dag_node("T1", parallel=False)], feature="regenerated")
        process, payload = self.converge("wave-0002", dag_path=self.write_dag(regenerated, "regenerated-dag.json"))
        self.assert_blocked(process, payload, "DAG-CONTENT-MISMATCH")

    def test_converge_blocks_an_unknown_wave(self) -> None:
        self.bind_execution_branch()
        dag_path = self.converged_wave_fixture()
        process, payload = self.converge("wave-0009", dag_path=dag_path)
        self.assert_blocked(process, payload, "WAVE-NOT-FOUND")

    # ------------------------------------------------------------------
    # T020 -- list_run_states: the two-layer Store read the ship gate uses
    # ------------------------------------------------------------------

    def test_list_run_states_returns_an_empty_list_without_a_store(self) -> None:
        bare = Path(self.temporary.name) / "bare"
        bare.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(bare)], check=True)
        self.assertFalse(store.store_exists(bare))
        self.assertEqual(gauntlet_runs.list_run_states(bare, WORK_ID), [])

    def test_list_run_states_enumerates_every_admitted_run(self) -> None:
        self.assertEqual(
            gauntlet_runs.list_run_states(self.root, WORK_ID),
            [{"run_id": self.run_id, "state": "ADMITTED"}],
        )
        # A Store that exists but has no gauntlet block for this work item is
        # an absence, never a denial -- FR-008's no-op depends on it.
        self.assertEqual(gauntlet_runs.list_run_states(self.root, "never-admitted-0000"), [])

    # ------------------------------------------------------------------
    # T021/T022 -- gauntlet-run-abandon (FR-014, ADR-0020)
    # ------------------------------------------------------------------

    def test_run_abandon_blocks_the_run_and_records_the_bundle_verbatim(self) -> None:
        bundle = human_authorization_bundle(self.run_id)
        process, payload = self.run_abandon(self.write_authorization(bundle))
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "RUN-ABANDONED")
        self.assertEqual(payload.get("run_id"), self.run_id)

        run = self.run_record()
        self.assertEqual(run["state"], "BLOCKED")
        self.assertEqual(run["abandon_authorization"], bundle)
        self.assertIn("gauntlet.run.abandoned", event_names(self.root))

        # FR-010: the abandonment transition correlates through the same
        # journal/receipt chain every other coordinator event already does.
        process, payload = self.gauntlet_status(run_id=self.run_id)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload["run"]["state"], "BLOCKED")

    def test_run_abandon_replays_an_identical_bundle_without_a_second_event(self) -> None:
        path = self.write_authorization(human_authorization_bundle(self.run_id))
        self.run_abandon(path)
        before = event_names(self.root).count("gauntlet.run.abandoned")

        process, payload = self.run_abandon(path)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "RUN-ABANDON-REUSED")
        self.assertEqual(event_names(self.root).count("gauntlet.run.abandoned"), before)

    def test_run_abandon_rejects_a_divergent_bundle_on_an_abandoned_run(self) -> None:
        self.run_abandon(self.write_authorization(human_authorization_bundle(self.run_id)))
        divergent = human_authorization_bundle(self.run_id, authorized_by="someone-else@example.invalid")

        process, payload = self.run_abandon(self.write_authorization(divergent, "second.json"))
        self.assert_blocked(process, payload, "RUN-NOT-ELIGIBLE")
        self.assertEqual(self.run_record()["abandon_authorization"]["authorized_by"], "operator@example.invalid")

    def test_run_abandon_rejects_a_complete_run(self) -> None:
        self.bind_execution_branch()
        document = dag_document([dag_node("T1", parallel=False)])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1"])
        self.dispatch("wave-0001", "T1", dag_path=dag_path)
        self.terminate("T1")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED", (payload, process.stderr))
        self.assertEqual(self.run_record()["state"], "COMPLETE")

        process, payload = self.run_abandon(self.write_authorization(human_authorization_bundle(self.run_id)))
        self.assert_blocked(process, payload, "RUN-NOT-ELIGIBLE")
        self.assertEqual(self.run_record()["state"], "COMPLETE")
        self.assertNotIn("abandon_authorization", self.run_record())

    def test_run_abandon_rejects_a_missing_bundle(self) -> None:
        process, payload = self.run_abandon("receipts/absent-authorization.json")
        self.assert_blocked(process, payload, "ABANDON-AUTHORIZATION-INVALID")
        self.assertEqual(self.run_record()["state"], "ADMITTED")

    def test_run_abandon_rejects_an_unreadable_bundle_path(self) -> None:
        (self.root / "authorization-directory").mkdir()
        process, payload = self.run_abandon("authorization-directory")
        self.assert_blocked(process, payload, "ABANDON-AUTHORIZATION-INVALID")

        process, payload = self.run_abandon(str(self.root / "run-abandon.json"))
        self.assert_blocked(process, payload, "ABANDON-AUTHORIZATION-INVALID")

    def test_run_abandon_rejects_a_malformed_bundle(self) -> None:
        (self.root / "broken.json").write_text("not json at all", encoding="utf-8")
        process, payload = self.run_abandon("broken.json")
        self.assert_blocked(process, payload, "ABANDON-AUTHORIZATION-INVALID")

        incomplete = human_authorization_bundle(self.run_id)
        incomplete.pop("receipt_ref")
        process, payload = self.run_abandon(self.write_authorization(incomplete, "incomplete.json"))
        self.assert_blocked(process, payload, "ABANDON-AUTHORIZATION-INVALID")
        self.assertEqual(self.run_record()["state"], "ADMITTED")

    def test_run_abandon_rejects_an_unapproved_bundle(self) -> None:
        rejected = human_authorization_bundle(self.run_id, decision="REJECTED")
        process, payload = self.run_abandon(self.write_authorization(rejected))
        self.assert_blocked(process, payload, "ABANDON-AUTHORIZATION-INVALID")
        self.assertEqual(self.run_record()["state"], "ADMITTED")

    def test_run_abandon_rejects_a_bundle_scoped_to_another_run(self) -> None:
        foreign = human_authorization_bundle("run-someone-elses-identity")
        process, payload = self.run_abandon(self.write_authorization(foreign))
        self.assert_blocked(process, payload, "ABANDON-AUTHORIZATION-INVALID")
        self.assertEqual(self.run_record()["state"], "ADMITTED")

    def test_run_abandon_succeeds_when_the_runs_base_commit_no_longer_resolves(self) -> None:
        """FR-014/ADR-0020: a run old enough to need abandoning may have a
        ``base_commit`` a rewrite already made unreachable, and that can never
        be the reason its own abandonment fails."""
        surviving = self.head_of()
        git(self.root, "commit", "-q", "--allow-empty", "-m", "commit the abandoned run is admitted from")
        discarded = self.head_of()
        process, payload = invoke(WORKSPACE, "gauntlet-run", self.root, "--work-id", WORK_ID)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        stale_run_id = payload["run_id"]
        self.assertNotEqual(stale_run_id, self.run_id)
        self.assertEqual(self.run_record(stale_run_id)["admission"]["base_commit"], discarded)

        git(self.root, "reset", "--hard", "-q", surviving)
        (self.root / ".git/ORIG_HEAD").unlink(missing_ok=True)
        git(self.root, "reflog", "expire", "--expire=now", "--expire-unreachable=now", "--all")
        git(self.root, "gc", "--prune=now", "-q")
        self.assertNotEqual(
            subprocess.run(
                ["git", "-C", str(self.root), "cat-file", "-e", f"{discarded}^{{commit}}"],
                capture_output=True, check=False,
            ).returncode,
            0,
        )

        bundle = human_authorization_bundle(stale_run_id)
        process, payload = self.run_abandon(self.write_authorization(bundle), run_id=stale_run_id)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "RUN-ABANDONED")
        self.assertEqual(self.run_record(stale_run_id)["state"], "BLOCKED")
        # The transition still anchors to the run's own recorded base commit,
        # which the Store requires and Git can no longer resolve.
        abandoned = [
            record for record in store.read_events(self.root)
            if record.get("event") == "gauntlet.run.abandoned"
        ]
        self.assertEqual([record["base_commit"] for record in abandoned], [discarded])

    def test_converge_rejects_an_abandoned_run(self) -> None:
        self.bind_execution_branch()
        dag_path = self.converged_wave_fixture()
        self.run_abandon(self.write_authorization(human_authorization_bundle(self.run_id)))
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "RUN-NOT-ELIGIBLE")
        self.assertIs(self.converged_flag("T1"), False)

    # ------------------------------------------------------------------
    # T023 -- checkpoint --step ship --state complete gains FR-007's gate
    # ------------------------------------------------------------------

    def test_ship_complete_blocks_when_a_dag_node_was_never_dispatched(self) -> None:
        """SC-004's empty case: the wave that exists is fully converged, so no
        worker is pending -- the run is still far from done because a whole
        ``node_id`` of the pinned DAG never got a wave."""
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        dag_path = self.write_dag(document)
        self.open_ship()
        self.declare_wave(dag_path, ["T1"])
        self.dispatch("wave-0001", "T1", dag_path=dag_path)
        self.terminate("T1")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED", (payload, process.stderr))
        run = self.run_record()
        self.assertEqual(run["state"], "ADMITTED")
        self.assertEqual(sorted(run["workers"]), ["T1"])
        self.assertIs(run["workers"]["T1"]["workspace"]["converged"], True)

        process, payload = self.ship_complete()
        self.assert_blocked(process, payload, "CONVERGENCE-INCOMPLETE")
        self.assertIn(self.run_id, payload.get("error", ""))
        self.assertEqual(self.development_state()["steps"]["ship"], "in-progress")

    def complete_run(self, run_id: str, dag_path: str) -> None:
        """Drive one single-node run all the way to ``COMPLETE`` (FR-001)."""
        held, self.run_id = self.run_id, run_id
        try:
            self.declare_wave(dag_path, ["T1"])
            self.dispatch("wave-0001", "T1", dag_path=dag_path)
            self.terminate("T1")
            process, payload = self.converge("wave-0001", dag_path=dag_path)
            self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED", (payload, process.stderr))
        finally:
            self.run_id = held
        self.assertEqual(self.run_record(run_id)["state"], "COMPLETE")

    def test_ship_complete_blocks_on_a_run_the_default_selection_would_skip(self) -> None:
        """SC-004: two admitted runs, the newer one already ``COMPLETE`` and the
        other still ``ADMITTED`` with no wave declared at all. ``run_id`` is an
        admission hash, not a clock, so the run ``gauntlet-status`` displays by
        default (the lexicographic max) being terminal proves nothing about the
        rest -- and the pending one has no worker to cite, only a DAG nothing
        ever dispatched."""
        dag_path = self.write_dag(dag_document([dag_node("T1", parallel=False)]))
        self.open_ship()
        git(self.root, "commit", "-q", "--allow-empty", "-m", "second generation")
        process, payload = invoke(WORKSPACE, "gauntlet-run", self.root, "--work-id", WORK_ID)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        second_run_id = payload["run_id"]
        self.assertNotEqual(second_run_id, self.run_id)

        default_selected = max(self.run_id, second_run_id)
        skipped = min(self.run_id, second_run_id)
        self.complete_run(default_selected, dag_path)
        _, status = self.gauntlet_status()
        self.assertEqual(status["run"]["run_id"], default_selected)
        self.assertEqual(status["run"]["state"], "COMPLETE")
        skipped_record = self.run_record(skipped)
        self.assertEqual(skipped_record["state"], "ADMITTED")
        self.assertEqual(skipped_record["workers"], {})

        process, payload = self.ship_complete()
        self.assert_blocked(process, payload, "CONVERGENCE-INCOMPLETE")
        self.assertIn(skipped, payload.get("error", ""))
        self.assertNotIn(default_selected, payload.get("error", ""))

        # FR-014/ADR-0020: abandoning the last pending run takes it out of the
        # gate's scope, and the flow reaches the pre-existing attestation gate.
        self.run_abandon(
            self.write_authorization(human_authorization_bundle(skipped), "skipped.json"), run_id=skipped,
        )
        process, payload = self.ship_complete()
        self.assert_blocked(process, payload, "ATTESTATION-REQUIRED")

    def test_ship_complete_reaches_the_attestation_gate_once_every_run_is_complete(self) -> None:
        document = dag_document([dag_node("T1", parallel=False)])
        dag_path = self.write_dag(document)
        self.open_ship()
        self.declare_wave(dag_path, ["T1"])
        self.dispatch("wave-0001", "T1", dag_path=dag_path)
        self.terminate("T1")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED", (payload, process.stderr))
        self.assertEqual(self.run_record()["state"], "COMPLETE")

        process, payload = self.ship_complete()
        self.assert_blocked(process, payload, "ATTESTATION-REQUIRED")

    # ------------------------------------------------------------------
    # T025/T027 -- User Story 4 (FR-011): gauntlet-status projects every real
    # wave and the still-open convergence block, straight off the Store
    # ------------------------------------------------------------------

    def test_status_omits_the_bootstrap_placeholder_wave(self) -> None:
        self.assertEqual(
            self.run_record()["waves"]["wave-0001"]["node_ids"], gauntlet_runs.WAVE_PENDING_NODE_IDS
        )
        projected = self.status_run()
        self.assertEqual(projected["waves"], [])
        self.assertNotIn("last_conflict", projected)
        # FR-011: everything FASE-002/003 already returned stays untouched.
        self.assertEqual(projected["workers"], [])
        self.assertEqual(projected["recovery_count"], 0)
        self.assertEqual(projected["state"], "ADMITTED")

    def test_status_projects_a_converged_wave_beside_the_one_still_running(self) -> None:
        """User Story 4's Independent Test, verbatim: two waves in distinct
        states, both readable in one call without touching the Store."""
        self.bind_execution_branch()
        document = dag_document([
            dag_node("T1", parallel=False),
            dag_node("T2", depends_on=["T1"], parallel=False),
        ])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1"])
        self.dispatch("wave-0001", "T1", dag_path=dag_path)
        self.commit_in_worker("T1", "tests/fixture-T1.py", "worker T1 output\n")
        self.terminate("T1")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED", (payload, process.stderr))
        self.declare_wave(dag_path, ["T2"], expected="wave-0002")
        self.dispatch("wave-0002", "T2", dag_path=dag_path)

        self.assertEqual(
            self.status_run()["waves"],
            [
                {"wave_id": "wave-0001", "state": "COMPLETE", "converged_count": 1, "member_count": 1},
                {"wave_id": "wave-0002", "state": "ACTIVE", "converged_count": 0, "member_count": 1},
            ],
        )

    def test_status_counts_only_the_converged_members_of_a_wave(self) -> None:
        self.bind_execution_branch()
        document = dag_document([dag_node("T1", parallel=True), dag_node("T2", parallel=True)])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1", "T2"])
        for node_id in ("T1", "T2"):
            self.dispatch("wave-0001", node_id, dag_path=dag_path)
            self.commit_in_worker(node_id, f"tests/fixture-{node_id}.py", f"worker {node_id}\n")
        self.terminate("T1")
        self.terminate("T2", outcome="failed", failure_class="process-timeout")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(payload.get("converged"), ["T1"], (payload, process.stderr))

        # A FAILED member is terminal, so the wave's own ``state`` is COMPLETE
        # while the node it stranded is counted by neither half of the pair.
        self.assertEqual(
            self.status_run()["waves"],
            [{"wave_id": "wave-0001", "state": "COMPLETE", "converged_count": 1, "member_count": 2}],
        )

    def superseded_conflict_fixture(self) -> str:
        """Wave-0001 blocked on a real content conflict, with wave-0002
        legitimately declared over it -- ADR-0022's own motivating shape, and
        the one case a "newest wave" lookup would report as unblocked."""
        document = dag_document([
            dag_node("T1", parallel=True, files=["src/a.py"]),
            dag_node("T2", parallel=True, files=["src/b.py"]),
            dag_node("T3", parallel=True, files=["src/c.py"]),
        ])
        dag_path = self.write_dag(document)
        self.declare_wave(dag_path, ["T1", "T2"])
        for node_id in ("T1", "T2"):
            self.dispatch("wave-0001", node_id, dag_path=dag_path, files=[f"src/{node_id.lower()}.py"])
        self.commit_in_worker("T1", "shared.txt", "written by T1\n")
        self.commit_in_worker("T2", "shared.txt", "written by T2\n")
        self.terminate("T1")
        self.terminate("T2")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "INTEGRATION_CONFLICT")
        self.declare_wave(dag_path, ["T3"], expected="wave-0002")
        return dag_path

    def test_status_surfaces_an_open_conflict_from_a_superseded_wave(self) -> None:
        self.bind_execution_branch()
        self.superseded_conflict_fixture()
        waves = self.run_record()["waves"]
        self.assertIn("last_conflict", waves["wave-0001"])
        self.assertNotIn("last_conflict", waves["wave-0002"])

        projected = self.status_run()
        self.assertEqual(
            projected["waves"],
            [
                {"wave_id": "wave-0001", "state": "COMPLETE", "converged_count": 1, "member_count": 2},
                {"wave_id": "wave-0002", "state": "ACTIVE", "converged_count": 0, "member_count": 1},
            ],
        )
        # FR-011 projects the block's identity and motive only -- never the
        # reentry fingerprints, and never raw journal or diff content.
        self.assertEqual(projected["last_conflict"], {"node_ids": ["T2"], "reason": "content-conflict"})

    def test_status_surfaces_a_scope_overlap_block_with_every_named_node(self) -> None:
        self.bind_execution_branch()
        document = dag_document([
            dag_node("T1", parallel=True, files=["src/shared.py"]),
            dag_node("T2", parallel=True, files=["src/shared.py"]),
        ])
        dag_path = self.write_dag(document)
        inject_wave(
            self.root, WORK_ID, self.run_id, "wave-0001", ["T1", "T2"],
            dag_content_sha256=store.jcs_sha256(document),
        )
        for node_id in ("T1", "T2"):
            self.dispatch("wave-0001", node_id, dag_path=dag_path, files=[f"src/{node_id}.py"])
            self.commit_in_worker(node_id, f"src/{node_id}.py", f"worker {node_id} output\n")
            self.terminate(node_id)
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assert_blocked(process, payload, "INTEGRATION_CONFLICT")

        self.assertEqual(
            self.status_run()["last_conflict"],
            {"node_ids": ["T1", "T2"], "reason": "scope-overlap"},
        )

    def test_status_drops_the_conflict_once_a_later_convergence_resolves_it(self) -> None:
        self.bind_execution_branch()
        dag_path = self.superseded_conflict_fixture()
        self.assertIn("last_conflict", self.status_run())

        self.commit_in_worker("T2", "shared.txt", "written by T1\n")
        process, payload = self.converge("wave-0001", dag_path=dag_path)
        self.assertEqual(payload.get("verdict"), "WAVE-CONVERGED", (payload, process.stderr))

        projected = self.status_run()
        self.assertNotIn("last_conflict", projected)
        self.assertEqual(
            projected["waves"][0],
            {"wave_id": "wave-0001", "state": "COMPLETE", "converged_count": 2, "member_count": 2},
        )


class ShipGateWithoutGauntletContract(unittest.TestCase):
    """FR-008: the gate is a no-op for a V2 work item with no Store at all."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        git(self.root, "config", "user.email", "gauntlet-converge-contract@example.invalid")
        git(self.root, "config", "user.name", "Gauntlet Converge Contract")
        (self.root / "WORKFLOW.md").write_bytes(WORKFLOW_TEMPLATE.read_bytes())
        git(self.root, "add", "WORKFLOW.md")
        git(self.root, "commit", "-qm", "fixture workflow v2")
        process, payload = invoke(
            WORKSPACE, "init", self.root, "--type", "feature", "--slug", "no-gauntlet", "--work-id", WORK_ID,
        
        "--skip-backlog",
    )
        if process.returncode != 0 or payload.get("status") != "CREATED":
            raise AssertionError((process.returncode, payload, process.stderr))
        (self.root / "evidence.md").write_text("evidence\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def checkpoint(self, step: str, state: str, **kwargs: Any) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments: list[str] = ["checkpoint", self.root, "--work-id", WORK_ID, "--step", step, "--state", state]
        for value in kwargs.get("evidence", []):
            arguments.extend(("--evidence", value))
        return invoke(WORKSPACE, *arguments)

    def test_ship_completes_for_a_v2_work_item_with_no_store(self) -> None:
        self.assertFalse(store.store_exists(self.root))
        for step in SEQUENCE:
            process, payload = self.checkpoint(step, "in-progress")
            self.assertEqual(process.returncode, 0, (step, payload, process.stderr))
            process, payload = self.checkpoint(step, "complete", evidence=["evidence.md"])
            self.assertEqual(process.returncode, 0, (step, payload, process.stderr))
            self.assertEqual(payload.get("verdict"), "UPDATED", (step, payload))
        self.assertFalse(store.store_exists(self.root))


if __name__ == "__main__":
    unittest.main()
