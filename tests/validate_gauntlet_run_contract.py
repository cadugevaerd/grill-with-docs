#!/usr/bin/env python3
"""Shared public-contract harness for FASE-002 durable Gauntlet runs.

This validator deliberately owns its fixtures.  Each case starts from an
isolated Git repository and reaches the public command surface through the
same V2 -> V3 -> rebound -> activation path an operator uses.  Later FASE-002
tasks add the admission, recovery, evidence, and worktree matrices here; the
helpers below make their no-write assertions cover the project, common-Git
Store, and Git worktree state independently.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin/skills/grill-with-docs"
ASSETS = SKILL / "assets"
WORKSPACE = SKILL / "scripts/grill_workspace.py"
WORKFLOW_MIGRATOR = SKILL / "scripts/grill_core/workflow_v3.py"
WORKFLOW_TEMPLATE = ASSETS / "WORKFLOW.template.md"
WORK_ID = "durable-run-a1b2"
SECOND_WORK_ID = "durable-run-second-b2c3"
SCRIPTS = SKILL / "scripts"

# A recovery-eligible record is durable state prepared by the Store fixture,
# not an implementation back door.  The public CLI is still the only surface
# exercised for admission, status, and resume.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from grill_core import store


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


def _file_snapshot(root: Path) -> dict[str, tuple[bytes, int, int]]:
    """Capture regular files by bytes, mode, and mtime without following links."""
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes(),
            path.stat().st_mode & 0o777,
            path.stat().st_mtime_ns,
        )
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def root_snapshot(root: Path) -> dict[str, tuple[bytes, int, int]]:
    """Snapshot project-owned files while excluding Git's mutable administration."""
    return {
        relative: value
        for relative, value in _file_snapshot(root).items()
        if relative != ".git" and not relative.startswith(".git/")
    }


def common_git_dir(root: Path) -> Path:
    value = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    path = Path(value)
    if not path.is_absolute():
        raise AssertionError(f"Git returned a non-absolute common directory: {value!r}")
    return path


def store_snapshot(root: Path) -> dict[str, tuple[bytes, int, int]]:
    """Snapshot the authoritative common-Git Store, including receipts and WAL."""
    return _file_snapshot(common_git_dir(root) / "grill")


def worktree_snapshot(root: Path) -> dict[str, Any]:
    """Snapshot the visible worktree identity and all registered worktrees.

    The root tree is included so future prepare/cleanup cases can prove that a
    derived worktree did not alter the coordinator worktree.  Store bytes are
    intentionally absent: callers compare :func:`store_snapshot` separately.
    """
    return {
        "head": git(root, "rev-parse", "HEAD"),
        "branch": git(root, "branch", "--show-current"),
        "status": git(root, "status", "--porcelain=v1", "--untracked-files=all"),
        "registered": git(root, "worktree", "list", "--porcelain"),
        "tree": root_snapshot(root),
    }


def run_snapshot(root: Path, work_id: str, run_id: str) -> dict[str, Any]:
    """Read one already-authoritative run solely for fixture assertions."""
    document = store.read_snapshot(root).document
    return document["work_items"][work_id]["gauntlet"]["runs"][run_id]


def mark_run_recovery_eligible(root: Path, work_id: str, run_id: str) -> None:
    """Seed the interrupted durable state that an operator subsequently resumes.

    This models the prior, coordinator-recorded interruption through the same
    Store WAL transition protocol the implementation must use.  It does not
    call a future Gauntlet-runs helper, so this remains a public CLI contract
    test rather than a test coupled to its implementation.
    """
    current = run_snapshot(root, work_id, run_id)
    admission = current["admission"]
    receipt = {
        "category": "runtime",
        "name": f"gauntlet-recovery-eligible-{run_id}",
        "work_id": work_id,
        "run_id": run_id,
        "wave_id": "wave-0001",
        "base_commit": admission["base_commit"],
        "input_sha256": hashlib.sha256(b"fixture interrupted lease").hexdigest(),
        "output_sha256": None,
    }
    event = {
        "event": "gauntlet.run.recovery-eligible",
        "work_id": work_id,
        "run_id": run_id,
        "wave_id": "wave-0001",
        "base_commit": receipt["base_commit"],
        "input_sha256": receipt["input_sha256"],
        "output_sha256": None,
        "receipt_sha256": store.jcs_sha256(receipt),
    }

    def mark(document: dict[str, Any]) -> dict[str, Any]:
        record = document["work_items"][work_id]["gauntlet"]["runs"][run_id]
        record["state"] = "RECOVERY_ELIGIBLE"
        return document

    store.transact_with_event(root, mark, event=event, receipt=receipt)


def coordinator_fixture_transition(
    root: Path,
    work_id: str,
    run_id: str,
    *,
    name: str,
    event_name: str,
    input_sha256: str,
    output_sha256: str | None,
    worker_id: str | None = None,
    lease_id: str | None = None,
    fencing_token: int | None = None,
    mutate: Any,
) -> None:
    """Record deliberately coordinator-owned fixture evidence.

    US2 uses Store-prepared state because FASE-002 exposes diagnosis only; it
    does not expose a worker evidence-writing CLI.  This helper still takes
    the same WAL path as production coordinator transitions, which makes the
    later public status assertions independent of an implementation backdoor.
    """
    admission = run_snapshot(root, work_id, run_id)["admission"]
    receipt: dict[str, Any] = {
        "category": "runtime",
        "name": name,
        "work_id": work_id,
        "run_id": run_id,
        "wave_id": "wave-0001",
        "base_commit": admission["base_commit"],
        "input_sha256": input_sha256,
        "output_sha256": output_sha256,
    }
    event: dict[str, Any] = {
        "event": event_name,
        "work_id": work_id,
        "run_id": run_id,
        "wave_id": receipt["wave_id"],
        "base_commit": receipt["base_commit"],
        "input_sha256": input_sha256,
        "output_sha256": output_sha256,
        "receipt_sha256": "",
    }
    if worker_id is not None or lease_id is not None or fencing_token is not None:
        if not all(value is not None for value in (worker_id, lease_id, fencing_token)):
            raise AssertionError("worker evidence requires worker, lease, and fencing correlation")
        event.update({"worker_id": worker_id, "lease_id": lease_id, "fencing_token": fencing_token})
    receipt_payload = {
        "category": receipt["category"],
        "name": receipt["name"],
        **{key: event[key] for key in event if key not in {"event", "receipt_sha256"}},
    }
    event["receipt_sha256"] = store.jcs_sha256(receipt_payload)
    store.transact_with_event(root, mutate, event=event, receipt=receipt)


def seed_worker_diagnosis(root: Path, work_id: str, run_id: str, worker_id: str, terminal_state: str) -> dict[str, str]:
    """Create a correlated declared -> prepared -> diagnostic worker fixture."""
    if terminal_state not in {"FAILED", "STALLED"}:
        raise AssertionError(f"unsupported diagnostic state: {terminal_state}")
    admission = run_snapshot(root, work_id, run_id)["admission"]
    lease_id = f"lease-{worker_id}"
    hashes = {
        "declared": hashlib.sha256(f"{worker_id}:declared".encode()).hexdigest(),
        "preparing": hashlib.sha256(f"{worker_id}:preparing".encode()).hexdigest(),
        "prepared": hashlib.sha256(f"{worker_id}:prepared".encode()).hexdigest(),
        "terminal": hashlib.sha256(f"{worker_id}:{terminal_state}".encode()).hexdigest(),
        "output": hashlib.sha256(f"{worker_id}:output".encode()).hexdigest(),
    }

    def declared(document: dict[str, Any]) -> dict[str, Any]:
        document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id] = {
            # FASE-003 (T005): node_id/remediates are now required worker keys;
            # this fixture is a plain first-dispatch worker, so node_id mirrors
            # worker_id verbatim and remediates stays null, matching what the
            # real `gauntlet-prepare-worker` CLI's own defaults now produce.
            "state": "DECLARED", "lease": None, "grant": None, "workspace": None,
            "node_id": worker_id, "remediates": None,
        }
        return document

    coordinator_fixture_transition(
        root, work_id, run_id, name=f"fixture-{worker_id}-declared",
        event_name="gauntlet.worker.declared", input_sha256=hashes["declared"], output_sha256=None,
        mutate=declared,
    )

    def preparing(document: dict[str, Any]) -> dict[str, Any]:
        worker = document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]
        worker["state"] = "PREPARING"
        worker["lease"] = {
            "lease_id": lease_id, "fencing_token": 1,
            "acquired_at": "2098-08-14T12:00:00Z", "expires_at": "2099-08-14T13:00:00Z",
            "state": "ACTIVE", "recovery_count": 0,
        }
        return document

    coordinator_fixture_transition(
        root, work_id, run_id, name=f"fixture-{worker_id}-preparing",
        event_name="gauntlet.worker.preparing", input_sha256=hashes["preparing"], output_sha256=None,
        worker_id=worker_id, lease_id=lease_id, fencing_token=1, mutate=preparing,
    )

    def prepared(document: dict[str, Any]) -> dict[str, Any]:
        document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]["state"] = "PREPARED"
        return document

    coordinator_fixture_transition(
        root, work_id, run_id, name=f"fixture-{worker_id}-prepared",
        event_name="gauntlet.worker.prepared", input_sha256=hashes["prepared"], output_sha256=hashes["output"],
        worker_id=worker_id, lease_id=lease_id, fencing_token=1, mutate=prepared,
    )

    def diagnostic(document: dict[str, Any]) -> dict[str, Any]:
        document["work_items"][work_id]["gauntlet"]["runs"][run_id]["workers"][worker_id]["state"] = terminal_state
        return document

    coordinator_fixture_transition(
        root, work_id, run_id, name=f"fixture-{worker_id}-{terminal_state.lower()}",
        event_name=f"gauntlet.worker.{terminal_state.lower()}", input_sha256=hashes["terminal"], output_sha256=None,
        worker_id=worker_id, lease_id=lease_id, fencing_token=1, mutate=diagnostic,
    )
    return {"lease_id": lease_id, **hashes, "base_commit": admission["base_commit"]}


def add_activated_rebound_v3_work_item(root: Path, work_id: str) -> None:
    """Add a separate current V3 item through the public FASE-001 surface."""
    process, payload = invoke(
        WORKSPACE, "init", root, "--type", "feature", "--slug", "durable-run-second",
        "--work-id", work_id, "--skip-backlog",
    )
    if process.returncode != 0 or payload.get("status") != "CREATED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, payload = invoke(WORKSPACE, "migrate-v3", root, "--work-id", work_id, "--apply")
    if process.returncode != 0 or payload.get("verdict") != "APPLIED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, payload = invoke(
        WORKSPACE, "migrate-v3", root, "--work-id", work_id, "--rebind-workflow", "--apply"
    )
    if process.returncode != 0 or payload.get("verdict") not in {"APPLIED", "REUSED"} or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, payload = invoke(WORKSPACE, "gauntlet-init", root, "--work-id", work_id, "--max-workers", 1)
    if process.returncode != 0 or payload.get("verdict") != "ACTIVATED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))


def build_rebound_v3_repository(root: Path) -> None:
    """Create one V3 work item whose workflow binding is current and activated."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    git(root, "config", "user.email", "gauntlet-run-contract@example.invalid")
    git(root, "config", "user.name", "Gauntlet Run Contract")
    (root / "WORKFLOW.md").write_bytes(WORKFLOW_TEMPLATE.read_bytes())
    git(root, "add", "WORKFLOW.md")
    git(root, "commit", "-qm", "fixture workflow v2")

    process, payload = invoke(
        WORKSPACE, "init", root, "--type", "feature", "--slug", "durable-run", "--work-id", WORK_ID, "--skip-backlog"
    )
    if process.returncode != 0 or payload.get("status") != "CREATED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, payload = invoke(WORKSPACE, "migrate-v3", root, "--work-id", WORK_ID, "--apply")
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
    process, payload = invoke(
        WORKSPACE, "migrate-v3", root, "--work-id", WORK_ID, "--rebind-workflow", "--apply"
    )
    if process.returncode != 0 or payload.get("verdict") not in {"APPLIED", "REUSED"} or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, payload = invoke(WORKSPACE, "gauntlet-init", root, "--work-id", WORK_ID, "--max-workers", 1)
    if process.returncode != 0 or payload.get("verdict") != "ACTIVATED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))

    item = strict_json_bytes(
        (root / ".grill/work-items" / WORK_ID / "WORK-ITEM.json").read_bytes(), source="WORK-ITEM.json"
    )
    workflow_sha256 = hashlib.sha256((root / "WORKFLOW.md").read_bytes()).hexdigest()
    if item.get("schema") != "grill-work-item/v3" or item["immutable"]["workflow"]["sha256"] != workflow_sha256:
        raise AssertionError("fixture does not have a current V3 workflow binding")


class GauntletRunContractHarness(unittest.TestCase):
    """Public FASE-002 admission and explicit-recovery contract."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        build_rebound_v3_repository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_activated_v3_fixture_is_isolated_and_status_is_read_only(self) -> None:
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)
        process, payload = invoke(WORKSPACE, "gauntlet-status", self.root, "--work-id", WORK_ID)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "STATUS")
        self.assertEqual(payload.get("work_id"), WORK_ID)
        self.assertEqual(payload.get("activation_state"), "ACTIVATED")
        self.assertEqual(root_snapshot(self.root), root_before)
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assertEqual(worktree_snapshot(self.root), worktree_before)

    def admit_run(self) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return invoke(WORKSPACE, "gauntlet-run", self.root, "--work-id", WORK_ID)

    def resume_run(self, run_id: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return invoke(WORKSPACE, "gauntlet-resume", self.root, "--work-id", WORK_ID, "--run-id", run_id)

    def prepare_worker(
        self, run_id: str, worker_id: str = "worker-a", *scopes: str
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments: list[str] = [
            "gauntlet-prepare-worker", self.root, "--work-id", WORK_ID,
            "--run-id", run_id, "--worker-id", worker_id,
        ]
        for scope in scopes or ("plugin",):
            arguments.extend(("--scope", scope))
        return invoke(WORKSPACE, *arguments)

    def cleanup_worker(self, run_id: str, worker_id: str = "worker-a") -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        return invoke(
            WORKSPACE, "gauntlet-cleanup", self.root, "--work-id", WORK_ID,
            "--run-id", run_id, "--worker-id", worker_id,
        )

    def seed_worker(
        self, run_id: str, worker_id: str, state: str, *,
        clean: bool = False, converged: bool = False, cleanup_eligible: bool = False,
        lease_state: str = "ACTIVE", acquired_at: str = "2098-08-14T12:00:00Z",
        expires_at: str = "2099-08-14T13:00:00Z",
    ) -> dict[str, Any]:
        """Install a coordinator-recorded interrupted worker intent fixture.

        This represents a crash after the durable intent, before its Git side
        effect.  The public command under test must reconcile it; this helper
        never creates or removes a worktree itself.
        """
        admission = run_snapshot(self.root, WORK_ID, run_id)["admission"]
        workspace = {
            "worktree_key": f"wt-{run_id}-{worker_id}",
            "branch": f"grill/{WORK_ID}/{run_id}/{worker_id}",
            "base_commit": admission["base_commit"],
            "clean": clean,
            "converged": converged,
            "cleanup_eligible": cleanup_eligible,
        }
        lease = {
            "lease_id": f"lease-{worker_id}", "fencing_token": 1,
            "acquired_at": acquired_at, "expires_at": expires_at,
            "state": lease_state, "recovery_count": 0,
        }

        def declared(document: dict[str, Any]) -> dict[str, Any]:
            document["work_items"][WORK_ID]["gauntlet"]["runs"][run_id]["workers"][worker_id] = {
                # FASE-003 (T005): see the sibling fixture in seed_worker_diagnosis
                # for why node_id/remediates are populated the same way here.
                "state": "DECLARED", "lease": None, "grant": None, "workspace": None,
                "node_id": worker_id, "remediates": None,
            }
            return document

        coordinator_fixture_transition(
            self.root, WORK_ID, run_id, name=f"fixture-{worker_id}-declared",
            event_name="gauntlet.worker.declared",
            input_sha256=hashlib.sha256(f"{worker_id}:declared".encode()).hexdigest(), output_sha256=None,
            mutate=declared,
        )
        def preparing(document: dict[str, Any]) -> dict[str, Any]:
            record = document["work_items"][WORK_ID]["gauntlet"]["runs"][run_id]["workers"][worker_id]
            record.update({
                "state": "PREPARING",
                "lease": lease,
                "grant": {"scope_paths": ["plugin"], "capabilities": ["git-local", "workspace-read-write"]},
                "workspace": workspace,
            })
            return document
        coordinator_fixture_transition(
            self.root, WORK_ID, run_id, name=f"fixture-{worker_id}-preparing",
            event_name="gauntlet.worker.preparing",
            input_sha256=hashlib.sha256(f"{worker_id}:preparing".encode()).hexdigest(), output_sha256=None,
            mutate=preparing,
        )
        if state == "ORPHANED":
            def orphan(document: dict[str, Any]) -> dict[str, Any]:
                document["work_items"][WORK_ID]["gauntlet"]["runs"][run_id]["workers"][worker_id]["state"] = "ORPHANED"
                return document
            coordinator_fixture_transition(
                self.root, WORK_ID, run_id, name=f"fixture-{worker_id}-orphaned",
                event_name="gauntlet.worker.orphaned",
                input_sha256=hashlib.sha256(f"{worker_id}:orphaned".encode()).hexdigest(), output_sha256=None,
                mutate=orphan,
            )
        elif state != "PREPARING":
            raise AssertionError(f"unsupported interrupted worker fixture state: {state}")
        return workspace

    def assert_no_execution_artifacts(
        self,
        root_before: dict[str, tuple[bytes, int, int]],
        worktree_before: dict[str, Any],
    ) -> None:
        """FASE-002 may persist coordinator state, never execute or schedule work."""
        self.assertEqual(root_snapshot(self.root), root_before)
        self.assertEqual(worktree_snapshot(self.root), worktree_before)
        self.assertFalse((self.root / ".grill" / "workers").exists())
        self.assertFalse((self.root / ".grill" / "runs").exists())

    def assert_no_store_residue(self, *, event_name: str, receipt_prefix: str) -> None:
        """One winning transition leaves no retry, lock, or WAL residue behind."""
        paths = store.store_paths(self.root)
        self.assertFalse((paths.locks / store.PENDING_TRANSITION_NAME).exists())
        self.assertEqual(list(paths.locks.iterdir()), [])
        events = [event for event in store.read_events(self.root) if event.get("event") == event_name]
        self.assertEqual(len(events), 1)
        receipts = sorted((paths.receipts / "runtime").glob(f"{receipt_prefix}*.json"))
        self.assertEqual(len(receipts), 1)

    def concurrent_calls(
        self, count: int, call: Any
    ) -> list[tuple[subprocess.CompletedProcess[str], dict[str, Any]]]:
        """Start the public CLI calls together, preserving each one-JSON check."""
        barrier = threading.Barrier(count)

        def invoke_after_barrier() -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
            barrier.wait(timeout=10)
            return call()

        with ThreadPoolExecutor(max_workers=count) as pool:
            return [future.result(timeout=30) for future in [pool.submit(invoke_after_barrier) for _ in range(count)]]

    def test_admission_creates_one_durable_run_without_execution_artifacts(self) -> None:
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        process, payload = self.admit_run()

        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "RUN-CREATED")
        self.assertEqual(payload.get("work_id"), WORK_ID)
        self.assertRegex(payload.get("run_id", ""), r"^run-[A-Za-z0-9][A-Za-z0-9._-]*$")
        self.assertRegex(payload.get("base_commit", ""), r"^[0-9a-f]{40}$")
        self.assertNotEqual(store_snapshot(self.root), store_before)
        self.assert_no_execution_artifacts(root_before, worktree_before)

        run = run_snapshot(self.root, WORK_ID, payload["run_id"])
        self.assertEqual(run["state"], "ADMITTED")
        self.assertEqual(run["recovery_count"], 0)
        self.assertEqual(run["workers"], {})
        self.assertEqual(run["admission"]["base_commit"], payload["base_commit"])

    def test_identical_admission_reuses_same_run_without_store_or_execution_churn(self) -> None:
        first_process, first = self.admit_run()
        self.assertEqual((first_process.returncode, first.get("verdict")), (0, "RUN-CREATED"), first)
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        second_process, second = self.admit_run()

        self.assertEqual(second_process.returncode, 0, (second, second_process.stderr))
        self.assertEqual(second_process.stderr, "")
        self.assertEqual(
            second,
            {
                "verdict": "RUN-REUSED",
                "work_id": WORK_ID,
                "run_id": first["run_id"],
                "base_commit": first["base_commit"],
            },
        )
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assert_no_execution_artifacts(root_before, worktree_before)

    def test_explicit_eligible_resume_records_once_then_reuses_without_relaunch_or_retry(self) -> None:
        created_process, created = self.admit_run()
        self.assertEqual((created_process.returncode, created.get("verdict")), (0, "RUN-CREATED"), created)
        run_id = created["run_id"]
        mark_run_recovery_eligible(self.root, WORK_ID, run_id)
        root_before = root_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        resumed_process, resumed = self.resume_run(run_id)

        self.assertEqual(resumed_process.returncode, 0, (resumed, resumed_process.stderr))
        self.assertEqual(resumed_process.stderr, "")
        self.assertEqual(
            resumed,
            {"verdict": "RESUME-RECORDED", "work_id": WORK_ID, "run_id": run_id, "recovery_count": 1},
        )
        self.assert_no_execution_artifacts(root_before, worktree_before)
        recovered = run_snapshot(self.root, WORK_ID, run_id)
        self.assertEqual((recovered["state"], recovered["recovery_count"]), ("RECOVERY_RECORDED", 1))

        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)
        repeat_process, repeat = self.resume_run(run_id)
        self.assertEqual(repeat_process.returncode, 0, (repeat, repeat_process.stderr))
        self.assertEqual(repeat_process.stderr, "")
        self.assertEqual(
            repeat,
            {"verdict": "RESUME-REUSED", "work_id": WORK_ID, "run_id": run_id, "recovery_count": 1},
        )
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assert_no_execution_artifacts(root_before, worktree_before)

    def test_stale_admission_and_resume_are_blocked_without_creating_or_replacing_a_run(self) -> None:
        created_process, created = self.admit_run()
        self.assertEqual((created_process.returncode, created.get("verdict")), (0, "RUN-CREATED"), created)
        (self.root / "WORKFLOW.md").write_bytes((self.root / "WORKFLOW.md").read_bytes() + b"\n")
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        for command, arguments in (
            ("gauntlet-run", ()),
            ("gauntlet-resume", ("--run-id", created["run_id"])),
        ):
            with self.subTest(command=command):
                process, payload = invoke(WORKSPACE, command, self.root, "--work-id", WORK_ID, *arguments)
                self.assertEqual(process.returncode, 2, (payload, process.stderr))
                self.assertEqual(process.stderr, "")
                self.assertEqual(payload.get("verdict"), "BLOCKED")
                self.assertIsInstance(payload.get("code"), str)
                self.assertTrue(payload["code"])
                self.assertEqual(store_snapshot(self.root), store_before)
                self.assert_no_execution_artifacts(root_before, worktree_before)

    def test_status_projects_created_run_read_only(self) -> None:
        created_process, created = self.admit_run()
        self.assertEqual((created_process.returncode, created.get("verdict")), (0, "RUN-CREATED"), created)
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        process, payload = invoke(
            WORKSPACE, "gauntlet-status", self.root, "--work-id", WORK_ID, "--run-id", created["run_id"]
        )

        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "STATUS")
        self.assertEqual(payload.get("work_id"), WORK_ID)
        self.assertEqual(payload.get("activation_state"), "ACTIVATED")
        self.assertEqual(payload.get("run", {}).get("run_id"), created["run_id"])
        self.assertEqual(payload.get("run", {}).get("state"), "ADMITTED")
        self.assertEqual(payload.get("run", {}).get("workers"), [])
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assert_no_execution_artifacts(root_before, worktree_before)

    def test_explicit_unknown_run_status_is_blocked_without_initializing_the_store(self) -> None:
        unknown_run_id = "run-unknown-a1b2"
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        process, payload = invoke(
            WORKSPACE, "gauntlet-status", self.root, "--work-id", WORK_ID, "--run-id", unknown_run_id
        )

        self.assertEqual(process.returncode, 2, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(
            (payload.get("verdict"), payload.get("code"), payload.get("work_id")),
            ("BLOCKED", "RUN-NOT-FOUND", WORK_ID),
        )
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assert_no_execution_artifacts(root_before, worktree_before)

    def test_explicit_unknown_run_status_is_blocked_when_store_lacks_the_work_item(self) -> None:
        unknown_run_id = "run-unknown-a1b2"
        bootstrap = store.bootstrap(self.root)
        self.assertEqual(bootstrap["verdict"], "CREATED")
        self.assertEqual(store.read_snapshot(self.root).document["work_items"], {})
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        process, payload = invoke(
            WORKSPACE, "gauntlet-status", self.root, "--work-id", WORK_ID, "--run-id", unknown_run_id
        )

        self.assertEqual(process.returncode, 2, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(
            (payload.get("verdict"), payload.get("code"), payload.get("work_id")),
            ("BLOCKED", "RUN-NOT-FOUND", WORK_ID),
        )
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assert_no_execution_artifacts(root_before, worktree_before)

    def test_activated_second_item_with_existing_store_projects_no_run_read_only(self) -> None:
        first_process, first = self.admit_run()
        self.assertEqual((first_process.returncode, first.get("verdict")), (0, "RUN-CREATED"), first)
        add_activated_rebound_v3_work_item(self.root, SECOND_WORK_ID)
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        process, payload = invoke(WORKSPACE, "gauntlet-status", self.root, "--work-id", SECOND_WORK_ID)

        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(
            payload,
            {"verdict": "STATUS", "work_id": SECOND_WORK_ID, "activation_state": "ACTIVATED"},
        )
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assert_no_execution_artifacts(root_before, worktree_before)

    def test_eight_concurrent_identical_admissions_create_once_and_reuse_without_residue(self) -> None:
        root_before = root_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        results = self.concurrent_calls(8, self.admit_run)

        for process, payload in results:
            self.assertEqual(process.stderr, "")
            self.assertEqual(process.returncode, 0, payload)
            self.assertEqual(payload.get("work_id"), WORK_ID)
            self.assertIn(payload.get("verdict"), {"RUN-CREATED", "RUN-REUSED"})
        created = [payload for _, payload in results if payload["verdict"] == "RUN-CREATED"]
        reused = [payload for _, payload in results if payload["verdict"] == "RUN-REUSED"]
        self.assertEqual((len(created), len(reused)), (1, 7), results)
        self.assertEqual({payload["run_id"] for _, payload in results}, {created[0]["run_id"]})
        self.assertEqual({payload["base_commit"] for _, payload in results}, {created[0]["base_commit"]})
        self.assert_no_execution_artifacts(root_before, worktree_before)
        self.assert_no_store_residue(event_name="gauntlet.run.admitted", receipt_prefix="gauntlet-run-admit-")
        snapshot = store.read_snapshot(self.root)
        self.assertEqual(snapshot.revision, 2)
        self.assertEqual(set(snapshot.document["work_items"][WORK_ID]["gauntlet"]["runs"]), {created[0]["run_id"]})

    def test_eight_concurrent_eligible_resumes_record_once_and_reuse_without_residue(self) -> None:
        created_process, created = self.admit_run()
        self.assertEqual((created_process.returncode, created.get("verdict")), (0, "RUN-CREATED"), created)
        run_id = created["run_id"]
        mark_run_recovery_eligible(self.root, WORK_ID, run_id)
        root_before = root_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        results = self.concurrent_calls(8, lambda: self.resume_run(run_id))

        for process, payload in results:
            self.assertEqual(process.stderr, "")
            self.assertEqual(process.returncode, 0, payload)
            self.assertEqual(
                (payload.get("work_id"), payload.get("run_id"), payload.get("recovery_count")),
                (WORK_ID, run_id, 1),
            )
            self.assertIn(payload.get("verdict"), {"RESUME-RECORDED", "RESUME-REUSED"})
        recorded = [payload for _, payload in results if payload["verdict"] == "RESUME-RECORDED"]
        reused = [payload for _, payload in results if payload["verdict"] == "RESUME-REUSED"]
        self.assertEqual((len(recorded), len(reused)), (1, 7), results)
        self.assert_no_execution_artifacts(root_before, worktree_before)
        self.assert_no_store_residue(
            event_name="gauntlet.run.recovery-recorded", receipt_prefix="gauntlet-resume-"
        )
        self.assertEqual(store.read_snapshot(self.root).revision, 4)
        recovered = run_snapshot(self.root, WORK_ID, run_id)
        self.assertEqual((recovered["state"], recovered["recovery_count"]), ("RECOVERY_RECORDED", 1))

    def test_status_projects_correlated_progress_failure_and_stall_without_writes(self) -> None:
        created_process, created = self.admit_run()
        self.assertEqual((created_process.returncode, created.get("verdict")), (0, "RUN-CREATED"), created)
        run_id = created["run_id"]
        failed = seed_worker_diagnosis(self.root, WORK_ID, run_id, "worker-failed", "FAILED")
        stalled = seed_worker_diagnosis(self.root, WORK_ID, run_id, "worker-stalled", "STALLED")
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        process, payload = invoke(
            WORKSPACE, "gauntlet-status", self.root, "--work-id", WORK_ID, "--run-id", run_id
        )

        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        run = payload.get("run", {})
        self.assertEqual((payload.get("verdict"), run.get("run_id"), run.get("base_commit")),
                         ("STATUS", run_id, created["base_commit"]))
        self.assertEqual(
            {
                worker["worker_id"]: (worker["state"], worker["lease"]["lease_id"], worker["lease"]["fencing_token"])
                for worker in run.get("workers", [])
            },
            {
                "worker-failed": ("FAILED", failed["lease_id"], 1),
                "worker-stalled": ("STALLED", stalled["lease_id"], 1),
            },
        )
        # US2 must make the coordinator evidence that explains the latest
        # diagnostic state inspectable, rather than exposing only a label.
        evidence = run.get("last_transition", {})
        self.assertEqual(
            evidence,
            {
                "work_id": WORK_ID,
                "run_id": run_id,
                "wave_id": "wave-0001",
                "worker_id": "worker-stalled",
                "lease_id": stalled["lease_id"],
                "fencing_token": 1,
                "base_commit": created["base_commit"],
                "input_sha256": stalled["terminal"],
                "output_sha256": None,
                "receipt_sha256": run_snapshot(self.root, WORK_ID, run_id)["last_transition"]["receipt_sha256"],
            },
        )
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assert_no_execution_artifacts(root_before, worktree_before)

    def test_coordinator_receipt_binds_exact_transition_correlation_with_bare_hex_digests(self) -> None:
        created_process, created = self.admit_run()
        self.assertEqual((created_process.returncode, created.get("verdict")), (0, "RUN-CREATED"), created)
        run_id = created["run_id"]
        diagnosis = seed_worker_diagnosis(self.root, WORK_ID, run_id, "worker-failed", "FAILED")
        event = [
            item for item in store.read_events(self.root)
            if item.get("event") == "gauntlet.worker.failed"
        ][-1]
        receipt_path = store.receipt_path(self.root, "runtime", "fixture-worker-failed-failed")
        receipt = strict_json_bytes(receipt_path.read_bytes(), source="worker failure receipt")
        expected = {
            "work_id": WORK_ID, "run_id": run_id, "wave_id": "wave-0001",
            "worker_id": "worker-failed", "lease_id": diagnosis["lease_id"], "fencing_token": 1,
            "base_commit": created["base_commit"], "input_sha256": diagnosis["terminal"],
            "output_sha256": None,
        }
        for key, value in expected.items():
            self.assertEqual(event.get(key), value, key)
            self.assertEqual(receipt.get(key), value, key)
        self.assertEqual(event.get("receipt_sha256"), store.jcs_sha256(receipt))
        self.assertEqual(run_snapshot(self.root, WORK_ID, run_id)["last_transition"]["receipt_sha256"], event["receipt_sha256"])
        for digest in (event["input_sha256"], event["receipt_sha256"], receipt["input_sha256"]):
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertFalse(digest.startswith("sha256:"))

    def test_worker_originated_or_prefixed_digest_evidence_is_rejected_without_mutation(self) -> None:
        created_process, created = self.admit_run()
        self.assertEqual((created_process.returncode, created.get("verdict")), (0, "RUN-CREATED"), created)
        run_id = created["run_id"]
        admission = run_snapshot(self.root, WORK_ID, run_id)["admission"]
        bare = hashlib.sha256(b"strict evidence").hexdigest()
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        for label, receipt_patch, event_patch in (
            ("worker-category", {"category": "worker"}, {}),
            ("worker-authority", {"authority": "worker"}, {}),
            ("prefixed-input", {"input_sha256": f"sha256:{bare}"}, {"input_sha256": f"sha256:{bare}"}),
            ("prefixed-output", {"output_sha256": f"sha256:{bare}"}, {"output_sha256": f"sha256:{bare}"}),
            ("mismatched-wave", {"wave_id": "wave-other"}, {}),
        ):
            with self.subTest(label=label):
                receipt: dict[str, Any] = {
                    "category": "runtime", "name": f"rejected-{label}", "work_id": WORK_ID,
                    "run_id": run_id, "wave_id": "wave-0001", "base_commit": admission["base_commit"],
                    "input_sha256": bare, "output_sha256": None,
                }
                receipt.update(receipt_patch)
                event: dict[str, Any] = {
                    "event": "gauntlet.worker.untrusted", "work_id": WORK_ID, "run_id": run_id,
                    "wave_id": "wave-0001", "base_commit": admission["base_commit"],
                    "input_sha256": bare, "output_sha256": None, "receipt_sha256": bare,
                }
                event.update(event_patch)
                with self.assertRaises(store.StoreError):
                    store.transact_with_event(self.root, lambda document: document, event=event, receipt=receipt)
                self.assertEqual(store_snapshot(self.root), store_before)
                self.assert_no_execution_artifacts(root_before, worktree_before)

    def test_worker_evidence_cannot_name_an_unrecorded_worker_or_lease(self) -> None:
        created_process, created = self.admit_run()
        self.assertEqual((created_process.returncode, created.get("verdict")), (0, "RUN-CREATED"), created)
        run_id = created["run_id"]
        admission = run_snapshot(self.root, WORK_ID, run_id)["admission"]
        digest = hashlib.sha256(b"unrecorded worker evidence").hexdigest()
        receipt = {
            "category": "runtime", "name": "rejected-unrecorded-worker", "work_id": WORK_ID,
            "run_id": run_id, "wave_id": "wave-0001", "base_commit": admission["base_commit"],
            "input_sha256": digest, "output_sha256": None,
        }
        event = {
            "event": "gauntlet.worker.progress", "work_id": WORK_ID, "run_id": run_id,
            "wave_id": "wave-0001", "base_commit": admission["base_commit"],
            "input_sha256": digest, "output_sha256": None,
            "worker_id": "worker-unrecorded", "lease_id": "lease-unrecorded", "fencing_token": 1,
            "receipt_sha256": "",
        }
        receipt_payload = {
            "category": receipt["category"], "name": receipt["name"],
            **{key: event[key] for key in event if key not in {"event", "receipt_sha256"}},
        }
        event["receipt_sha256"] = store.jcs_sha256(receipt_payload)
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        with self.assertRaises(store.StoreError):
            store.transact_with_event(self.root, lambda document: document, event=event, receipt=receipt)

        self.assertEqual(store_snapshot(self.root), store_before)
        self.assert_no_execution_artifacts(root_before, worktree_before)

    # US3 — all cases below are deliberately RED until T015/T016 provide the
    # coordinator's worktree intent protocol and the two public controls.

    def test_prepare_pins_base_and_derives_only_the_declared_branch_and_key(self) -> None:
        _, created = self.admit_run()
        run_id = created["run_id"]
        base_commit = created["base_commit"]
        root_before = root_snapshot(self.root)

        process, payload = self.prepare_worker(run_id, "worker-a", "plugin")

        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(
            payload,
            {"verdict": "WORKER-PREPARED", "work_id": WORK_ID, "run_id": run_id,
             "worker_id": "worker-a", "worktree_key": f"wt-{run_id}-worker-a", "base_commit": base_commit},
        )
        worker = run_snapshot(self.root, WORK_ID, run_id)["workers"]["worker-a"]
        self.assertEqual(worker["state"], "PREPARED")
        self.assertEqual(worker["workspace"], {
            "worktree_key": f"wt-{run_id}-worker-a",
            "branch": f"grill/{WORK_ID}/{run_id}/worker-a",
            "base_commit": base_commit,
            "clean": True, "converged": False, "cleanup_eligible": False,
        })
        self.assertEqual(worker["grant"], {
            "scope_paths": ["plugin"], "capabilities": ["git-local", "workspace-read-write"],
        })
        registered = git(self.root, "worktree", "list", "--porcelain")
        prepared_block = next(
            block for block in registered.split("\n\n")
            if f"branch refs/heads/grill/{WORK_ID}/{run_id}/worker-a" in block
        )
        self.assertIn(f"HEAD {base_commit}", prepared_block)
        self.assertEqual(root_snapshot(self.root), root_before)

    def test_prepare_rejects_unsafe_or_duplicate_grant_scope_without_mutation(self) -> None:
        _, created = self.admit_run()
        run_id = created["run_id"]
        for scopes in (("../escape",), ("/host/path",), ("plugin", "plugin"), ("plugin\\escape",)):
            with self.subTest(scopes=scopes):
                root_before = root_snapshot(self.root)
                store_before = store_snapshot(self.root)
                worktree_before = worktree_snapshot(self.root)
                process, payload = self.prepare_worker(run_id, "worker-a", *scopes)
                self.assertEqual(process.returncode, 2, (payload, process.stderr))
                self.assertEqual(process.stderr, "")
                self.assertEqual(payload.get("verdict"), "BLOCKED")
                self.assertIsInstance(payload.get("code"), str)
                self.assertEqual(root_snapshot(self.root), root_before)
                self.assertEqual(store_snapshot(self.root), store_before)
                self.assertEqual(worktree_snapshot(self.root), worktree_before)

    def test_prepare_binds_each_worker_transition_receipt_and_last_transition_to_its_lease(self) -> None:
        _, created = self.admit_run()
        run_id = created["run_id"]

        process, payload = self.prepare_worker(run_id, "worker-evidence", "plugin")

        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))
        run = run_snapshot(self.root, WORK_ID, run_id)
        worker = run["workers"]["worker-evidence"]
        lease = worker["lease"]
        self.assertIsInstance(lease, dict)
        self.assertRegex(lease["lease_id"], r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
        self.assertIsInstance(lease["fencing_token"], int)
        self.assertGreater(lease["fencing_token"], 0)
        events = [
            event for event in store.read_events(self.root)
            if event.get("work_id") == WORK_ID and event.get("run_id") == run_id
            and event.get("worker_id") == "worker-evidence"
        ]
        self.assertTrue(events, "prepare must record coordinator-owned worker transitions")
        self.assertIn("gauntlet.worker.prepared", {event["event"] for event in events})
        receipt_dir = store.store_paths(self.root).receipts / "runtime"
        receipts = [strict_json_bytes(path.read_bytes(), source=str(path)) for path in receipt_dir.glob("*.json")]
        for event in events:
            with self.subTest(sequence=event["sequence"], event=event["event"]):
                self.assertEqual(event["lease_id"], lease["lease_id"])
                self.assertEqual(event["fencing_token"], lease["fencing_token"])
                self.assertEqual(event["base_commit"], created["base_commit"])
                for digest_field in ("input_sha256", "receipt_sha256"):
                    self.assertRegex(event[digest_field], r"^[0-9a-f]{64}$")
                    self.assertFalse(event[digest_field].startswith("sha256:"))
                if event["output_sha256"] is not None:
                    self.assertRegex(event["output_sha256"], r"^[0-9a-f]{64}$")
                matching_receipts = [receipt for receipt in receipts if store.jcs_sha256(receipt) == event["receipt_sha256"]]
                self.assertEqual(len(matching_receipts), 1)
                receipt = matching_receipts[0]
                self.assertEqual(
                    {
                        key: receipt.get(key) for key in (
                            "work_id", "run_id", "wave_id", "worker_id", "lease_id", "fencing_token",
                            "base_commit", "input_sha256", "output_sha256",
                        )
                    },
                    {
                        key: event.get(key) for key in (
                            "work_id", "run_id", "wave_id", "worker_id", "lease_id", "fencing_token",
                            "base_commit", "input_sha256", "output_sha256",
                        )
                    },
                )
        latest = max(events, key=lambda event: event["sequence"])
        self.assertEqual(run["last_transition"], {
            "event_sequence": latest["sequence"], "receipt_sha256": latest["receipt_sha256"],
        })

    def test_preparing_intent_with_no_git_effect_is_reconciled_to_exact_prepared_workspace(self) -> None:
        _, created = self.admit_run()
        run_id = created["run_id"]
        workspace = self.seed_worker(run_id, "worker-intent", "PREPARING")
        self.assertNotIn(f"branch refs/heads/{workspace['branch']}", git(self.root, "worktree", "list", "--porcelain"))

        process, payload = self.prepare_worker(run_id, "worker-intent", "plugin")

        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload.get("verdict"), "WORKER-PREPARED")
        self.assertEqual(run_snapshot(self.root, WORK_ID, run_id)["workers"]["worker-intent"]["state"], "PREPARED")
        self.assertIn(f"branch refs/heads/{workspace['branch']}", git(self.root, "worktree", "list", "--porcelain"))

    def test_expired_or_nonactive_preparing_lease_cannot_auto_resume_or_create_a_worktree(self) -> None:
        _, created = self.admit_run()
        run_id = created["run_id"]
        cases = (
            ("worker-expired", "EXPIRED", "2000-08-14T12:00:00Z", "2000-08-14T13:00:00Z"),
            ("worker-recovery-eligible", "RECOVERY_ELIGIBLE", "2098-08-14T12:00:00Z", "2099-08-14T13:00:00Z"),
        )
        for worker_id, lease_state, acquired_at, expires_at in cases:
            with self.subTest(lease_state=lease_state):
                workspace = self.seed_worker(
                    run_id, worker_id, "PREPARING", lease_state=lease_state,
                    acquired_at=acquired_at, expires_at=expires_at,
                )
                root_before = root_snapshot(self.root)
                store_before = store_snapshot(self.root)
                worktree_before = worktree_snapshot(self.root)
                worker_before = run_snapshot(self.root, WORK_ID, run_id)["workers"][worker_id]

                process, payload = self.prepare_worker(run_id, worker_id, "plugin")

                self.assertIn(process.returncode, {0, 2}, (payload, process.stderr))
                self.assertEqual(process.stderr, "")
                self.assertIn(payload.get("verdict"), {"BLOCKED", "PRESERVED"})
                if payload.get("verdict") == "BLOCKED":
                    self.assertIsInstance(payload.get("code"), str)
                self.assertEqual(root_snapshot(self.root), root_before)
                self.assertEqual(store_snapshot(self.root), store_before)
                self.assertEqual(worktree_snapshot(self.root), worktree_before)
                self.assertEqual(run_snapshot(self.root, WORK_ID, run_id)["workers"][worker_id], worker_before)
                self.assertNotIn(f"branch refs/heads/{workspace['branch']}", worktree_before["registered"])

    def test_orphaned_worker_is_preserved_and_never_auto_deleted(self) -> None:
        _, created = self.admit_run()
        run_id = created["run_id"]
        workspace = self.seed_worker(run_id, "worker-orphan", "ORPHANED")
        # A directory not registered as the declared Git worktree is evidence
        # that a future cleanup implementation must preserve, not discover.
        orphan = common_git_dir(self.root) / "grill" / workspace["worktree_key"]
        orphan.mkdir(parents=True)
        (orphan / "diagnostic.txt").write_text("preserve\n", encoding="utf-8")
        root_before = root_snapshot(self.root)
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        process, payload = self.cleanup_worker(run_id, "worker-orphan")

        self.assertEqual(process.returncode, 2, (payload, process.stderr))
        self.assertEqual(process.stderr, "")
        self.assertEqual(payload.get("verdict"), "PRESERVED")
        self.assertTrue((orphan / "diagnostic.txt").is_file())
        self.assertEqual(run_snapshot(self.root, WORK_ID, run_id)["workers"]["worker-orphan"]["state"], "ORPHANED")
        self.assertEqual(root_snapshot(self.root), root_before)
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assertEqual(worktree_snapshot(self.root), worktree_before)

    def test_cleanup_requires_all_predicates_then_removes_only_exact_worker_and_reconciles_cleaning(self) -> None:
        _, created = self.admit_run()
        run_id = created["run_id"]
        process, payload = self.prepare_worker(run_id, "worker-clean", "plugin")
        self.assertEqual((process.returncode, payload.get("verdict")), (0, "WORKER-PREPARED"), (payload, process.stderr))
        sibling_process, sibling = self.prepare_worker(run_id, "worker-sibling", "plugin")
        self.assertEqual(
            (sibling_process.returncode, sibling.get("verdict")), (0, "WORKER-PREPARED"),
            (sibling, sibling_process.stderr),
        )
        worker = run_snapshot(self.root, WORK_ID, run_id)["workers"]["worker-clean"]
        branch = worker["workspace"]["branch"]
        registered = git(self.root, "worktree", "list", "--porcelain")
        worker_block = next(block for block in registered.split("\n\n") if f"branch refs/heads/{branch}" in block)
        worker_path = Path(next(line.removeprefix("worktree ") for line in worker_block.splitlines() if line.startswith("worktree ")))
        sibling_worker = run_snapshot(self.root, WORK_ID, run_id)["workers"]["worker-sibling"]
        sibling_branch = sibling_worker["workspace"]["branch"]
        sibling_block = next(
            block for block in registered.split("\n\n") if f"branch refs/heads/{sibling_branch}" in block
        )
        sibling_path = Path(
            next(line.removeprefix("worktree ") for line in sibling_block.splitlines() if line.startswith("worktree "))
        )
        # Each false predicate must preserve the exact registered workspace.
        for field in ("clean", "converged", "cleanup_eligible"):
            def deny(document: dict[str, Any], field: str = field) -> dict[str, Any]:
                record = document["work_items"][WORK_ID]["gauntlet"]["runs"][run_id]["workers"]["worker-clean"]
                record["state"] = "TERMINAL"
                record["workspace"]["clean"] = True
                record["workspace"]["converged"] = True
                record["workspace"]["cleanup_eligible"] = True
                record["workspace"][field] = False
                return document
            coordinator_fixture_transition(self.root, WORK_ID, run_id, name=f"fixture-cleanup-deny-{field}",
                event_name="gauntlet.worker.terminal", input_sha256=hashlib.sha256(field.encode()).hexdigest(),
                output_sha256=None, mutate=deny)
            root_before = root_snapshot(self.root)
            store_before = store_snapshot(self.root)
            worktree_before = worktree_snapshot(self.root)
            denied_process, denied = self.cleanup_worker(run_id, "worker-clean")
            self.assertEqual(denied_process.returncode, 2, (denied, denied_process.stderr))
            self.assertEqual(denied.get("verdict"), "PRESERVED")
            self.assertTrue(worker_path.exists(), field)
            self.assertTrue(sibling_path.exists(), field)
            self.assertEqual(root_snapshot(self.root), root_before)
            self.assertEqual(store_snapshot(self.root), store_before)
            self.assertEqual(worktree_snapshot(self.root), worktree_before)
        # Restore all recorded predicates.  Cleanup must remove no sibling
        # worktree and a repeated command must reconcile the CLEANING intent.
        def eligible(document: dict[str, Any]) -> dict[str, Any]:
            record = document["work_items"][WORK_ID]["gauntlet"]["runs"][run_id]["workers"]["worker-clean"]
            record["state"] = "TERMINAL"
            record["workspace"].update({"clean": True, "converged": True, "cleanup_eligible": True})
            return document
        coordinator_fixture_transition(self.root, WORK_ID, run_id, name="fixture-cleanup-eligible",
            event_name="gauntlet.worker.terminal", input_sha256=hashlib.sha256(b"eligible").hexdigest(),
            output_sha256=None, mutate=eligible)
        cleaned_process, cleaned = self.cleanup_worker(run_id, "worker-clean")
        self.assertEqual((cleaned_process.returncode, cleaned.get("verdict")), (0, "CLEANED"), (cleaned, cleaned_process.stderr))
        self.assertFalse(worker_path.exists())
        self.assertTrue(sibling_path.exists())
        self.assertIn(f"branch refs/heads/{sibling_branch}", git(self.root, "worktree", "list", "--porcelain"))
        self.assertEqual(run_snapshot(self.root, WORK_ID, run_id)["workers"]["worker-clean"]["state"], "CLEANED")
        self.assertEqual(run_snapshot(self.root, WORK_ID, run_id)["workers"]["worker-sibling"]["state"], "PREPARED")
        repeated_process, repeated = self.cleanup_worker(run_id, "worker-clean")
        self.assertEqual((repeated_process.returncode, repeated.get("verdict")), (0, "REUSED"), (repeated, repeated_process.stderr))

    def test_cleanup_preserves_terminal_eligible_worker_when_exact_worktree_is_untracked_dirty(self) -> None:
        _, created = self.admit_run()
        run_id = created["run_id"]
        process, prepared = self.prepare_worker(run_id, "worker-dirty", "plugin")
        self.assertEqual((process.returncode, prepared.get("verdict")), (0, "WORKER-PREPARED"), (prepared, process.stderr))
        worker = run_snapshot(self.root, WORK_ID, run_id)["workers"]["worker-dirty"]
        branch = worker["workspace"]["branch"]
        registered = git(self.root, "worktree", "list", "--porcelain")
        worker_block = next(block for block in registered.split("\n\n") if f"branch refs/heads/{branch}" in block)
        worker_path = Path(next(line.removeprefix("worktree ") for line in worker_block.splitlines() if line.startswith("worktree ")))

        def terminal_eligible(document: dict[str, Any]) -> dict[str, Any]:
            record = document["work_items"][WORK_ID]["gauntlet"]["runs"][run_id]["workers"]["worker-dirty"]
            record["state"] = "TERMINAL"
            record["workspace"].update({"clean": True, "converged": True, "cleanup_eligible": True})
            return document

        coordinator_fixture_transition(
            self.root, WORK_ID, run_id, name="fixture-cleanup-dirty-terminal",
            event_name="gauntlet.worker.terminal", input_sha256=hashlib.sha256(b"dirty terminal").hexdigest(),
            output_sha256=None, mutate=terminal_eligible,
        )
        dirty_file = worker_path / "untracked-dirty-fixture.txt"
        dirty_file.write_text("must survive cleanup denial\n", encoding="utf-8")
        self.assertIn("?? untracked-dirty-fixture.txt", git(worker_path, "status", "--porcelain=v1", "--untracked-files=all"))
        store_before = store_snapshot(self.root)
        worktree_before = worktree_snapshot(self.root)

        denied_process, denied = self.cleanup_worker(run_id, "worker-dirty")

        self.assertIn(denied_process.returncode, {0, 2}, (denied, denied_process.stderr))
        self.assertEqual(denied_process.stderr, "")
        self.assertIn(denied.get("verdict"), {"PRESERVED", "BLOCKED"})
        self.assertTrue(dirty_file.is_file())
        self.assertEqual(run_snapshot(self.root, WORK_ID, run_id)["workers"]["worker-dirty"]["state"], "TERMINAL")
        self.assertEqual(store_snapshot(self.root), store_before)
        self.assertEqual(worktree_snapshot(self.root), worktree_before)


if __name__ == "__main__":
    unittest.main()
