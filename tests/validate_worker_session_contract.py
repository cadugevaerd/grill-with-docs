#!/usr/bin/env python3
"""Offline Orca worker session registration and release contract."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import orchestration_fixture
import validate_orchestrator_store_contract as schema_fixture

SCRIPTS = Path(__file__).resolve().parents[1] / "plugin/skills/grill-with-docs/scripts"
sys.path.insert(0, str(SCRIPTS))
import grill_workspace
from grill_core import agent_orchestration, agent_runtime, gauntlet_runs


class WorkerSession(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "worker"
        self.target.mkdir()
        (self.target / "result.json").write_text('{"accepted": true}\n')
        self.dispatch = "ctx-worker"
        self.ref = "orca:" + self.dispatch
        self.show = orchestration_fixture.native_show(self.target, "codex", self.dispatch)
        self.document = {"revision": 1, "agent_orchestration": {"work_items": {"w": {
            "current_context_id": "context-1", "resources": {},
            "contexts": {"context-1": {"leader": {"session_ref": "orca:ctx-leader"},
                                        "scheduler_runs": {}}}}}}}
        self.worker = {"state": "PREPARED", "workspace": {"branch": "grill/worker"}}
        self.run = {"workers": {"node": self.worker}, "admission": {}, "dag_content_sha256": "d" * 64}
        self.calls = []
        self.released = False
        self.release_unknown = False
        self.identity_override = None

        def transact(_root, mutate):
            self.document = mutate(copy.deepcopy(self.document))
            self.document["revision"] += 1
            return SimpleNamespace(document=self.document, revision=self.document["revision"])

        self.store = SimpleNamespace(read_snapshot=lambda *_args, **_kwargs:
            SimpleNamespace(document=copy.deepcopy(self.document), revision=self.document["revision"]),
            transact=transact, StoreError=Exception, STATE_DIVERGENCE="STATE-DIVERGENCE",
            jcs_sha256=lambda _value: "a" * 64)
        self.runs = SimpleNamespace(store=self.store, GauntletRunError=gauntlet_runs.GauntletRunError,
            _run_for_worker=lambda *_a, **_k: self.run,
            _worker_wave_id=lambda *_a: "wave-0001", _workspace_identity=lambda *_a: (self.target, {}),
            _workspace_is_registered=lambda *_a: True)
        def read(_argv):
            self.calls.append("show")
            return json.dumps(self.show).encode()
        def observe_released():
            self.calls.append("readback")
            if not self.released:
                raise agent_runtime.RuntimeError("release pending")
            resource = next(iter(self.document["agent_orchestration"]["work_items"]["w"]["resources"].values()))
            return {**resource["identity"], "owner_dispatch": self.identity_override or self.dispatch,
                    "release_proof": "archive", "source_sha256": "a" * 64}
        self.boundary = SimpleNamespace(read=read, observe_released=observe_released)
        self.patches = [
            mock.patch.object(grill_workspace, "gauntlet_run_admission", return_value=(self.root, self.runs, {}, {"runtime": {"id": "codex"}})),
            mock.patch.object(grill_workspace, "_leader_boundary", return_value=self.boundary),
            mock.patch.object(grill_workspace, "grill_core_module", side_effect=lambda name:
                agent_runtime if name == "agent_runtime" else self.runs if name == "gauntlet_runs" else object()),
        ]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.args = SimpleNamespace(root=str(self.root), work_id="w", run_id="run-1", worker_id="node",
                                    dispatch=self.dispatch, phase="register", result=None, session_ref="orca:ctx-leader")

    def resource(self):
        return next(iter(self.document["agent_orchestration"]["work_items"]["w"]["resources"].values()))

    def register(self):
        return grill_workspace.gauntlet_worker_session_command.__wrapped__(self.args)

    def settle(self):
        self.worker["state"] = "TERMINAL"
        show = self.show["result"]
        show["worker"].update({"state": "succeeded", "stage": "settled"})
        show["dispatch"].update({"status": "completed", "completedAt": "2026-01-01T00:00:00Z",
                                 "capabilityRevokedAt": "2026-01-01T00:00:00Z"})
        self.args.phase = "release"
        self.args.result = "result.json"

    def release(self):
        def request(*_args, **_kwargs):
            self.calls.append("release")
            if self.release_unknown:
                raise TimeoutError()
            self.released = True
            return SimpleNamespace(returncode=0)
        with mock.patch.object(grill_workspace.subprocess, "run", side_effect=request):
            return grill_workspace.gauntlet_worker_session_command.__wrapped__(self.args)

    def test_success_release_once_and_reuse(self):
        self.assertEqual(self.register()[0]["verdict"], "REGISTERED")
        self.assertEqual(self.document["agent_orchestration"]["work_items"]["w"]["contexts"]["context-1"]
                         ["scheduler_runs"]["run-1"]["dag_sha256"], "d" * 64)
        agent_orchestration._scheduler_runs(
            self.document["agent_orchestration"]["work_items"]["w"]["contexts"]["context-1"]["scheduler_runs"],
            {"context-1": {}})
        resource_id = next(iter(self.document["agent_orchestration"]["work_items"]["w"]["resources"]))
        agent_orchestration._resource(resource_id, self.resource(), {"context-1": {}})
        self.settle()
        self.assertEqual(self.release()[0]["verdict"], "RELEASED")
        self.assertEqual(self.resource()["state"], "CLOSED")
        agent_orchestration._resource(resource_id, self.resource(), {"context-1": {}})
        self.assertEqual(self.release()[0]["verdict"], "REUSED")
        self.assertEqual(self.calls.count("release"), 1)

    def test_store_accepts_bound_worker_resource(self):
        self.register()
        context = schema_fixture.ORCHESTRATION_CONTEXT()
        context["scheduler_runs"] = {"run-1": {"admission_sha256": "a" * 64,
            "dag_sha256": "d" * 64, "origin_context_id": "ctx-1"}}
        item = schema_fixture.ORCHESTRATION_ITEM({"ctx-1": context})
        resource = copy.deepcopy(self.resource())
        resource["origin_context_id"] = "ctx-1"
        item["resources"] = {"session-worker": resource}
        agent_orchestration.validate_block({"schema": agent_orchestration.SCHEMA,
                                            "work_items": {"work-x": item}})

    def test_pending_reconciles_readback_without_second_release(self):
        self.register()
        self.settle()
        self.release_unknown = True
        self.assertEqual(self.release()[0]["verdict"], "UNKNOWN")
        self.assertEqual(self.resource()["state"], "CLOSE_PENDING")
        self.assertEqual(self.release()[0]["verdict"], "UNKNOWN")
        self.assertEqual(self.calls.count("release"), 1)
        self.released = True
        self.assertEqual(self.release()[0]["verdict"], "RELEASED")
        self.assertEqual(self.calls.count("release"), 1)

    def test_result_settlement_identity_and_host_fail_closed(self):
        self.register()
        self.settle()
        self.args.result = "missing.json"
        with self.assertRaises(grill_workspace.CliFailure):
            self.release()
        self.assertEqual(self.resource()["state"], "REGISTERED")
        self.args.result = "result.json"
        self.show["result"]["worker"]["stage"] = "input_accepted"
        with self.assertRaises(grill_workspace.CliFailure):
            self.release()
        self.show["result"]["worker"]["stage"] = "settled"
        self.identity_override = "ctx-other"
        with self.assertRaises(grill_workspace.CliFailure):
            self.release()
        self.assertEqual(self.resource()["state"], "CLOSE_PENDING")

    def test_historical_settled_dispatch_can_register(self):
        self.settle()
        self.args.phase = "register"
        self.assertEqual(self.register()[0]["verdict"], "REGISTERED")

    def test_fast_settlement_can_register_before_scheduler_terminal(self):
        self.settle()
        self.worker["state"] = "PREPARED"
        self.args.phase = "register"
        self.assertEqual(self.register()[0]["verdict"], "REGISTERED")

    def test_failed_worker_releases_after_accepted_failure(self):
        self.register()
        self.settle()
        self.worker["state"] = "FAILED"
        self.show["result"]["worker"]["state"] = "failed"
        self.show["result"]["dispatch"]["status"] = "failed"
        self.assertEqual(self.release()[0]["verdict"], "RELEASED")

    def test_unavailable_host_preserves_registration(self):
        with mock.patch.object(self.boundary, "read", side_effect=agent_runtime.RuntimeError("host unavailable")):
            with self.assertRaises(grill_workspace.CliFailure):
                self.register()
        self.assertEqual(self.document["agent_orchestration"]["work_items"]["w"]["resources"], {})


class ReleaseGate(unittest.TestCase):
    def test_missing_pending_and_closed(self):
        item = {"current_context_id": "ctx", "contexts": {"ctx": {"leader": {"session_ref": "orca:ctx-leader"}}},
                "resources": {}}
        snapshot = SimpleNamespace(document={"agent_orchestration": {"work_items": {"w": item}}})
        with mock.patch.object(gauntlet_runs.store, "read_snapshot", return_value=snapshot), \
                mock.patch.object(gauntlet_runs, "_worker_wave_id", return_value="wave-0001"):
            with self.assertRaises(gauntlet_runs.GauntletRunError):
                gauntlet_runs.require_worker_session_released("/tmp", "w", "run-1", "node")
            item["resources"]["session-1"] = {"kind": "session", "scheduler_run_id": "run-1", "worker_id": "node",
                "state": "CLOSE_PENDING", "result_acceptance_ref": None}
            with self.assertRaises(gauntlet_runs.GauntletRunError):
                gauntlet_runs.require_worker_session_released("/tmp", "w", "run-1", "node")
            item["resources"]["session-1"].update({"state": "CLOSED", "result_acceptance_ref": "result.json",
                "wave_id": "wave-0001", "identity": {"owner_dispatch": "ctx-worker"}, "last_observation": "orca:ctx-worker:release",
                "evidence_manifest": {"receipts": [{"ref": "orca:ctx-worker:release"}]}})
            gauntlet_runs.require_worker_session_released("/tmp", "w", "run-1", "node")


if __name__ == "__main__":
    unittest.main()
