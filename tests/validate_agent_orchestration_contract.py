#!/usr/bin/env python3
"""Offline contract checks for the native Orca observation seam."""
import contextlib
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "plugin/skills/grill-with-docs/scripts"
sys.path.insert(0, str(SCRIPTS))
from grill_core.agent_runtime import RuntimeBoundary, RuntimeError, validate_observation
from grill_core import store
import grill_workspace

ORCA_CAPABILITIES = {
    "orchestration.worker-launch-preferences.v1",
    "orchestration.federation-structured-read.v1",
    "orchestration.federation-lifecycle-settlement.v1",
    "orchestration.federation-release-archive.v1",
}


def pack(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def native_sources(released=False):
    dispatch = "ctx-1"; task = "task-1"; worktree = "worktree-1"; handle = "term-1"
    launch = {"ok": True, "result": {
        "dispatchId": dispatch, "taskId": task,
        "launch": {"requested": {"agent": "codex", "model": "gpt-6-astra", "effort": "high"}, "effective": {"agent": "codex", "model": "gpt-6-astra", "effort": "high"}},
        "prompt": {"processIncarnation": "inc-1"},
    }}
    show = {"ok": True, "result": {
        "dispatch": {"id": dispatch, "taskId": task, "hostScope": {"hostId": "host-1"}, "status": "completed" if released else "dispatched"},
        "worker": {"dispatchId": dispatch, "runtimeEpoch": "runtime-1", "worktreeId": worktree, "agentTerminalHandle": handle, "state": "succeeded" if released else "ready", "stage": "settled" if released else "input_accepted", "startOptions": {"launch": copy.deepcopy(launch["result"]["launch"])}},
        "terminalResource": {"terminalHandle": handle, "worktreeId": worktree, "endpointId": "runtime-1", "endpointIncarnation": "dispatch-inc-1", "ownerDispatchId": dispatch, "releaseState": "released" if released else "not_requested"},
        "projection": {"taskId": task, "provider": {"id": "codex"}, "host": {"id": "host-1"}, "liveness": {"verdict": "exited" if released else "live", "source": "resource_release" if released else "agent_status"}, "resource": {"ownerDispatchId": dispatch, "releaseState": "released" if released else "not_requested"}},
        "terminal": None if released else {"handle": handle, "incarnationId": "inc-1", "worktreeId": worktree, "executionHostId": "host-1"},
    }}
    return pack(launch), pack(show)


def release_source(dispatch="ctx-1"):
    return pack({"ok": True, "result": {"dispatchId": dispatch, "state": "released", "processAction": "closed_agent_terminal", "archive": {"status": "captured"}}})


class AgentOrchestrationContract(unittest.TestCase):
    def run_cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = grill_workspace.main(list(argv))
        return code, json.loads(output.getvalue())

    def fixture(self):
        temp = tempfile.TemporaryDirectory(); root = Path(temp.name)
        for args in (("init",), ("config", "user.email", "test@example.invalid"), ("config", "user.name", "Test")):
            subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.DEVNULL)
        (root / "README.md").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-m", "fixture"], check=True, stdout=subprocess.DEVNULL)
        return temp, root

    def test_rollout_and_canonical_pins(self):
        temp, root = self.fixture()
        with temp:
            dependencies = grill_workspace.sibling("ensure_dependencies")
            probes = []; commands = []
            def sentinel_tool(_tools, command):
                probes.append(command)
                return f"/offline/{command}"
            def sentinel_probe(_tools, argv, **_kwargs):
                commands.append(argv)
                return 1, ""
            with mock.patch.dict("os.environ", {"GRILL_SKIP_DEPENDENCIES": ""}), \
                 mock.patch.object(dependencies.Toolchain, "which", sentinel_tool), \
                 mock.patch.object(dependencies.Toolchain, "run", sentinel_probe):
                self.assertEqual(self.run_cli("init", str(root), "--type", "feature", "--slug", "x", "--work-id", "work-x", "--runtime", "codex", "--skip-backlog")[0], 2)
                self.assertFalse((root / ".grill").exists())
                code, init = self.run_cli("init", str(root), "--type", "feature", "--slug", "x", "--work-id", "work-x", "--runtime", "codex", "--session-ref", "observed-session", "--skip-backlog")
                self.assertEqual(code, 0); self.assertEqual(init["orchestration"], "INITIALIZED")
                before = store.read_snapshot(root).content_sha256
                args = ("gauntlet-orchestration-adopt", str(root), "--work-id", "work-x", "--runtime", "codex", "--session-ref", "observed-session", "--scope-file", "src/a.py")
                code, preview = self.run_cli(*args); self.assertEqual(code, 0); self.assertEqual(preview["verdict"], "PREVIEW")
                self.assertEqual(store.read_snapshot(root).content_sha256, before)
                self.assertEqual(self.run_cli(*args, "--apply")[0], 2)
                code, adopted = self.run_cli(*args, "--apply", "--expected-sha256", preview["expected_sha256"])
                self.assertEqual(code, 0); self.assertEqual(adopted["verdict"], "ORCHESTRATION-ADOPTED")
                self.assertEqual(self.run_cli(*args, "--apply", "--expected-sha256", preview["expected_sha256"])[1]["verdict"], "REUSED")
                document = store.read_snapshot(root).document
                context = document["agent_orchestration"]["work_items"]["work-x"]["contexts"][adopted["context_id"]]
                self.assertIsNone(context["activation"]); self.assertIsNone(context["campaign"]); self.assertEqual(context["scheduler_runs"], {})
                checkpoint_args = ("checkpoint", str(root), "--work-id", "work-x", "--step", "specify", "--state", "in-progress", "--operation-id", "checkpoint-1", "--session-ref", "observed-session")
                code, checkpoint = self.run_cli(*checkpoint_args)
                self.assertEqual((code, checkpoint["verdict"]), (0, "UPDATED"))
                self.assertEqual(self.run_cli(*checkpoint_args)[1]["verdict"], "REUSED")
                stale = self.run_cli(*args, "--scope-file", "src/b.py", "--apply", "--expected-sha256", preview["expected_sha256"])
                self.assertEqual(stale[0], 2)
            self.assertTrue(probes); self.assertTrue(commands)
            self.assertTrue(all(argv[0].startswith("/offline/") for argv in commands))

    def test_adopted_direct_effect_requires_the_current_context_proof(self):
        temp, root = self.fixture()
        with temp:
            store.bootstrap(root)
            origin = {"state_sha256": "1" * 64, "metadata_sha256": "2" * 64, "activation": None,
                      "campaign": None, "lifecycle": "ACTIVE", "worktree": {"root": str(root), "branch": "main"}}
            contract = grill_workspace.grill_core_module("agent_orchestration")
            inputs = contract.adoption_inputs(work_id="work-x", runtime="codex", session_ref="session-1", scope_files=[], origin=origin)
            item = contract.new_work_item(inputs, policy_ref="policy/v1", policy_sha256="a" * 64,
                                          adopted_at="2026-01-01T00:00:00Z", context_id="ctx-1")
            store.transact(root, lambda document: {**document, "agent_orchestration": {"schema": contract.SCHEMA, "work_items": {"work-x": item}}})
            with self.assertRaises(store.StoreError):
                store.require_orchestration_authority(root, "work-x", purpose="prepare")
            with store.orchestration_authority(root, "work-x", context_id="ctx-1", epoch=1, session_ref="session-1"):
                store.require_orchestration_authority(root, "work-x", purpose="prepare")
    def boundary(self, probe=None, after=None, release=None, adapter="orca", capabilities=None, calls=None):
        probe = probe or native_sources()
        after = after or native_sources(released=True)
        release = release or release_source()
        calls = calls if calls is not None else []
        return RuntimeBoundary(adapter, "orca:worker-show:ctx-1", capabilities or ORCA_CAPABILITIES, lambda: (calls.append("probe") or probe), lambda: (calls.append("observe") or probe), lambda: (calls.append("release") or release), lambda: (calls.append("readback") or after)), calls

    def verified(self):
        boundary, calls = self.boundary()
        return boundary, boundary.verified("gpt-6-astra", "high"), calls

    def test_native_bytes_prove_effective_pair_and_full_identity(self):
        boundary, observed, calls = self.verified()
        self.assertEqual(calls, ["probe", "observe"])
        self.assertEqual(observed["effective_model"], "gpt-6-astra")
        self.assertEqual(observed["effective_effort"], "high")
        self.assertEqual(observed["incarnation"], "inc-1")
        self.assertEqual(observed["dispatch_incarnation"], "dispatch-inc-1")
        self.assertEqual(observed["task_id"], "task-1")
        self.assertEqual(observed["worktree_id"], "worktree-1")

    def test_unrelated_or_invented_native_source_is_refused_before_payload(self):
        boundary, calls = self.boundary(probe=(b"unrelated bytes", native_sources()[1]))
        with self.assertRaises(RuntimeError):
            boundary.verified("gpt-6-astra", "high")
        self.assertEqual(calls, ["probe"])
        boundary, calls = self.boundary(adapter="invented", capabilities=ORCA_CAPABILITIES)
        with self.assertRaisesRegex(RuntimeError, "SPECIALIST-CAPABILITY-UNPROVEN"):
            boundary.verified("gpt-6-astra", "high")
        self.assertEqual(calls, [])

    def test_claimed_digest_without_the_observed_bytes_is_refused(self):
        boundary, observed, _ = self.verified()
        observed["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
            validate_observation(observed, native_sources())

    def test_missing_effective_or_unresolved_alias_is_refused_before_payload(self):
        launch, show = native_sources()
        invalid = json.loads(show); del invalid["result"]["worker"]["startOptions"]["launch"]["effective"]["effort"]
        boundary, calls = self.boundary(probe=(launch, pack(invalid)))
        with self.assertRaises(RuntimeError):
            boundary.verified("gpt-6-astra", "high")
        self.assertEqual(calls, ["probe"])
        alias_launch = json.loads(launch); alias_show = json.loads(show)
        alias_launch["result"]["launch"]["requested"]["model"] = "astra"
        alias_show["result"]["worker"]["startOptions"]["launch"]["requested"]["model"] = "astra"
        boundary, calls = self.boundary(probe=(pack(alias_launch), pack(alias_show)))
        with self.assertRaisesRegex(RuntimeError, "SPECIALIST-CAPABILITY-UNPROVEN"):
            boundary.verified("astra", "high")
        self.assertEqual(calls, ["probe", "observe"])

    def test_close_requires_correlated_release_and_readback_once(self):
        boundary, observed, calls = self.verified()
        closed = boundary.close(observed)
        self.assertEqual(closed["close"], "closed")
        self.assertEqual(calls, ["probe", "observe", "release", "readback"])
        with self.assertRaises(RuntimeError):
            boundary.close(observed)
        self.assertEqual(calls, ["probe", "observe", "release", "readback"])

    def test_missing_readback_cannot_close(self):
        boundary, observed, calls = self.verified()
        boundary.read_after_close = lambda calls=calls: (calls.append("readback") or (b"", b""))
        with self.assertRaises(RuntimeError):
            boundary.close(observed)
        self.assertEqual(calls, ["probe", "observe", "release", "readback"])

    def test_launch_and_current_incarnation_must_correlate_to_worker_show(self):
        for key, value in (("dispatchId", "ctx-other"), ("taskId", "task-other")):
            launch, show = native_sources(); changed = json.loads(launch); changed["result"][key] = value
            boundary, calls = self.boundary(probe=(pack(changed), show))
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                boundary.verified("gpt-6-astra", "high")
            self.assertEqual(calls, ["probe"])
        launch, show = native_sources(); changed = json.loads(show); changed["result"]["terminal"] = None
        boundary, calls = self.boundary(probe=(launch, pack(changed)))
        with self.assertRaisesRegex(RuntimeError, "current session incarnation unproven"):
            boundary.verified("gpt-6-astra", "high")
        self.assertEqual(calls, ["probe"])

    def test_liveness_is_authoritative_and_unknown_or_exited_cannot_verify(self):
        for mutation in (
            lambda value: value["result"]["projection"].update(liveness={"verdict": "unverifiable"}),
            lambda value: value["result"]["worker"].pop("state"),
            lambda value: (value["result"]["projection"].update(liveness={"verdict": "exited", "source": "agent_status"}), value["result"]["terminal"].update(status="live")),
        ):
            launch, show = native_sources(); changed = json.loads(show); mutation(changed)
            boundary, calls = self.boundary(probe=(launch, pack(changed)))
            with self.assertRaisesRegex(RuntimeError, "SPECIALIST-CAPABILITY-UNPROVEN"):
                boundary.verified("gpt-6-astra", "high")
            self.assertEqual(calls, ["probe", "observe"])
        launch, show = native_sources(); idle = json.loads(show); idle["result"]["worker"]["state"] = "idle"
        boundary, calls = self.boundary(probe=(launch, pack(idle)))
        self.assertEqual(boundary.verified("gpt-6-astra", "high")["activity"], "idle")
        self.assertEqual(calls, ["probe", "observe"])

    def test_unknown_close_readback_reconciles_before_another_release(self):
        boundary, observed, calls = self.verified(); after = [(b"", b""), native_sources(released=True)]
        boundary.read_after_close = lambda: (calls.append("readback") or after.pop(0))
        with self.assertRaises(RuntimeError):
            boundary.close(observed)
        closed = boundary.close(observed)
        self.assertEqual((closed["close"], calls.count("release"), calls), ("closed", 1, ["probe", "observe", "release", "readback", "readback"]))

    def test_close_refuses_pending_unknown_and_changed_identity(self):
        for change in (
            ("releaseState", "release_pending"),
            ("agentWait", None),
            ("runtimeEpoch", "runtime-2"),
            ("host", "host-2"),
            ("dispatch", "ctx-2"),
            ("incarnation", "inc-2"),
        ):
            launch, after = native_sources(released=True)
            after_value = json.loads(after)
            key, value = change
            if key == "releaseState":
                after_value["result"]["terminalResource"]["releaseState"] = value
            elif key == "agentWait":
                after_value["result"]["worker"][key] = value
            elif key == "runtimeEpoch":
                after_value["result"]["worker"][key] = value
            elif key == "host":
                after_value["result"]["dispatch"]["hostScope"]["hostId"] = value
            elif key == "dispatch":
                after_value["result"]["terminalResource"]["ownerDispatchId"] = value
            else:
                launch_value = json.loads(launch); launch_value["result"]["prompt"]["processIncarnation"] = value; launch = pack(launch_value)
            boundary, observed, calls = self.verified()
            boundary.read_after_close = lambda launch=launch, after=pack(after_value), calls=calls: (calls.append("readback") or (launch, after))
            with self.assertRaises(RuntimeError):
                boundary.close(observed)
            self.assertEqual(calls, ["probe", "observe", "release", "readback"])


if __name__ == "__main__":
    unittest.main()
