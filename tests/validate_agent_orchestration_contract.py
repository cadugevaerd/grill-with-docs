#!/usr/bin/env python3
"""Offline contract checks for the native Orca observation seam."""
import orchestration_fixture
import concurrent.futures
import contextlib
import copy
import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "plugin/skills/grill-with-docs/scripts"
sys.path.insert(0, str(SCRIPTS))
from grill_core.agent_runtime import (RuntimeBoundary, RuntimeError, approved_presentation_reference,
                                      presentation_state, validate_observation)
from grill_core import agent_orchestration, attestation, gauntlet_runs, store
import grill_workspace

ORCA_CAPABILITIES = {
    "orchestration.worker-launch-preferences.v1",
    "orchestration.federation-structured-read.v1",
    "orchestration.federation-lifecycle-settlement.v1",
    "orchestration.federation-release-archive.v1",
}


def pack(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def native_sources(released=False, *, provider="codex", model="gpt-6-astra", effort="high"):
    dispatch = "ctx-1"; task = "task-1"; worktree = "worktree-1"; handle = "term-1"
    launch = {"ok": True, "result": {
        "dispatchId": dispatch, "taskId": task,
        "launch": {"requested": {"agent": provider, "model": model, "effort": effort}, "effective": {"agent": provider, "model": model, "effort": effort}},
        "prompt": {"processIncarnation": "inc-1"},
    }}
    show = {"ok": True, "result": {
        "dispatch": {"id": dispatch, "taskId": task, "hostScope": {"hostId": "host-1"}, "status": "completed" if released else "dispatched"},
        "worker": {"dispatchId": dispatch, "runtimeEpoch": "runtime-1", "worktreeId": worktree, "agentTerminalHandle": handle, "state": "succeeded" if released else "ready", "stage": "settled" if released else "input_accepted", "startOptions": {"launch": copy.deepcopy(launch["result"]["launch"])}},
        "terminalResource": {"terminalHandle": handle, "worktreeId": worktree, "endpointId": "runtime-1", "endpointIncarnation": "dispatch-inc-1", "ownerDispatchId": dispatch, "releaseState": "released" if released else "not_requested"},
        "projection": {"taskId": task, "provider": {"id": provider}, "host": {"id": "host-1"}, "liveness": {"verdict": "exited" if released else "live", "source": "resource_release" if released else "agent_status"}, "resource": {"ownerDispatchId": dispatch, "releaseState": "released" if released else "not_requested"}},
        "terminal": None if released else {"handle": handle, "incarnationId": "inc-1", "worktreeId": worktree, "executionHostId": "host-1"},
    }}
    return pack(launch), pack(show)


def release_source(dispatch="ctx-1"):
    return pack({"ok": True, "result": {"dispatchId": dispatch, "state": "released", "processAction": "closed_agent_terminal", "archive": {"status": "captured"}}})


def takeover_show(dispatch_id, *, status=None, revoked=None, liveness=None):
    """T007/T014: a worker-show reply for _takeover_observation (grill_workspace.py).

    observe_predecessor_termination (agent_runtime.py) parses this raw response
    through the enveloped ``{"ok": true, "result": {...}}`` shape every other
    native worker-show fixture in this file uses (native_show/native_sources).
    _takeover_observation's own dispatch.status/liveness extraction now reads
    the same unwrapped ``result`` mapping via agent_runtime._object, so this
    fixture produces only the real, enveloped shape.
    """
    dispatch = {"id": dispatch_id}
    if status is not None:
        dispatch["status"] = status
    dispatch["capabilityRevokedAt"] = revoked
    payload = {"dispatch": dispatch, "projection": {"liveness": liveness} if liveness is not None else {}}
    return json.dumps({"ok": True, "result": payload}).encode()


class AgentOrchestrationContract(unittest.TestCase):
    def test_current_leader_adapter_and_exact_read_sources(self):
        core = grill_workspace.grill_core_module("agent_runtime")
        temp, root = self.fixture()
        with temp, orchestration_fixture.offline_leader(grill_workspace):
            policy_raw = (grill_workspace.ASSETS / "agent-orchestration.v1.json").read_bytes()
            kwargs = {"policy": json.loads(policy_raw), "policy_sha256": grill_workspace.hash_bytes(policy_raw),
                "gwd_skill_sha256": grill_workspace.hash_bytes((grill_workspace.ASSETS.parent / "SKILL.md").read_bytes()),
                "scope": {"kind": "gwd", "root": str(root), "work_id": "work-x"}}
            for runtime in ("codex", "claude"):
                kwargs["runtime"] = runtime
                adapter, show, transcript = orchestration_fixture.boundary(
                    grill_workspace, root, runtime, orchestration_fixture.SESSION, "work-x")
                observed, ready = core.project_leader_presentation(adapter, **kwargs)
                self.assertTrue(ready["work_ready"])
                self.assertFalse(ready["functional_verified"])
                with self.assertRaisesRegex(core.RuntimeError, "LEADER-AUTHORITY-UNPROVEN"):
                    core.project_leader_presentation({**observed, "presentation": ready}, **kwargs)
                # A source from another session, wrong host/root, revoked dispatch,
                # partial transcript or model self-report cannot authorize entry.
                original_show, original_transcript = copy.deepcopy(show), copy.deepcopy(transcript)
                show["result"]["terminalResource"]["releaseState"] = "retained"
                self.assertEqual(adapter.observe(), observed)
                show["result"]["terminalResource"]["releaseState"] = "not_requested"
                for container, key, value in (
                    (show["result"]["terminal"], "handle", "another-terminal"),
                    (show["result"]["terminal"], "worktreePath", "/other"),
                    (show["result"]["terminal"], "incarnationId", "new-incarnation"),
                    (show["result"]["dispatch"], "capabilityRevokedAt", "revoked"),
                    (show["result"]["dispatch"], "status", {}),
                    (show["result"]["worker"], "state", "unknown"),
                    (show["result"]["worker"], "state", {}),
                    (show["result"]["terminalResource"], "releaseState", "released"),
                    (show["result"]["terminalResource"], "releaseState", "release_pending"),
                    (show["result"]["terminalResource"], "releaseState", "release_unknown"),
                    (transcript["result"], "contentComplete", False),
                    (transcript["result"], "sourceExact", False),
                    (transcript["result"], "dispatchId", "other-dispatch"),
                    (transcript["result"], "provider", "other-provider"),
                ):
                    previous = container[key]; container[key] = value
                    with self.assertRaises(core.RuntimeError):
                        core.project_leader_presentation(adapter, **kwargs)
                    container[key] = previous
                messages = transcript["result"]["transcript"]["messages"]
                for mutation_index, mutate in enumerate((
                    lambda: messages[1].update(role="assistant"),
                    lambda: messages[3].update(role="assistant"),
                    lambda: messages[3].update(id=""),
                    lambda: messages[3]["blocks"][0].update(output="loaded=true"),
                    lambda: messages[2]["blocks"][0].update(name={}),
                    lambda: messages[3]["blocks"][0].update(output=orchestration_fixture.REFERENCE.read_text()[:-1]),
                    lambda: messages[2]["blocks"][0]["input"].update(
                        {"command" if runtime == "claude" else "cmd": "echo loaded"}),
                    lambda: messages.reverse(),
                )):
                    mutate()
                    expected = runtime == "claude" and mutation_index == 5
                    self.assertEqual(core.project_leader_presentation(adapter, **kwargs)[1]["work_ready"], expected)
                    messages[:] = copy.deepcopy(original_transcript["result"]["transcript"]["messages"])
                request_payload = json.loads(messages[1]["blocks"][0]["output"])
                for key in ("policy_sha256", "gwd_skill_sha256", "skill_ref", "body_sha256", "scope", "session_identity", "config_fingerprint"):
                    altered = copy.deepcopy(request_payload)
                    altered["presentation"]["load_request"][key] = "stale"
                    messages[1]["blocks"][0]["output"] = json.dumps(altered)
                    self.assertFalse(core.project_leader_presentation(adapter, **kwargs)[1]["work_ready"])
                messages[1]["blocks"][0]["output"] = json.dumps(request_payload)
                probe = adapter.presentation_probe
                adapter.presentation_probe = lambda *args: {key: value for key, value in probe(*args).items() if key != "configuration"}
                unproven = core.project_leader_presentation(adapter, **kwargs)[1]
                self.assertEqual(unproven["config_fingerprint"], "unobserved")
                self.assertEqual(unproven["diagnostics"][0]["code"], "STYLE-CONFIG-UNPROVEN")
                self.assertFalse(unproven["work_ready"])
                adapter.presentation_probe = core._orca_presentation_axes
                native = core.project_leader_presentation(adapter, **kwargs)[1]
                self.assertEqual(native["trust"], "undetermined")
                self.assertFalse(native["work_ready"])
                self.assertEqual(show, original_show)

    def test_public_init_adopt_refuse_assertions_and_preserve_load_request(self):
        temp, root = self.fixture()
        core = grill_workspace.grill_core_module("agent_runtime")
        with temp, orchestration_fixture.offline_leader(grill_workspace):
            args = ("init", str(root), "--type", "feature", "--slug", "x", "--work-id", "work-x",
                    "--runtime", "codex", "--skip-backlog")
            for ref in ("bare-session", "asserted.json"):
                (root / "asserted.json").write_text(json.dumps({"presentation": self.ready_presentation()}))
                code, result = self.run_cli(*args, "--session-ref", ref)
                self.assertEqual((code, result["code"]), (2, "LEADER-ADAPTER-UNSUPPORTED"))
                self.assertFalse((root / ".grill").exists())
            adapter, _, _ = orchestration_fixture.boundary(grill_workspace, root, "codex",
                orchestration_fixture.SESSION, "work-x", loaded=False)
            with mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter):
                code, pending = self.run_cli(*args, "--session-ref", orchestration_fixture.SESSION)
                self.assertEqual((code, pending["code"]), (2, "STYLE-LOAD-UNCONFIRMED"))
                self.assertEqual(pending["presentation"]["load_request"]["scope"]["work_id"], "work-x")
                self.assertFalse((root / ".grill").exists())
            code, created = self.run_cli(*args, "--session-ref", orchestration_fixture.SESSION)
            self.assertEqual(code, 0, created)
            before = store.read_snapshot(root).content_sha256
            for ref in ("asserted.json", "bare-session"):
                code, refused = self.run_cli("gauntlet-orchestration-adopt", str(root), "--work-id", "work-x",
                    "--runtime", "codex", "--session-ref", ref)
                self.assertEqual(code, 2, refused)
                self.assertEqual(store.read_snapshot(root).content_sha256, before)
            with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "STYLE-LOAD-UNCONFIRMED"):
                agent_orchestration.require_presentation_work_ready({})

    def test_preflight_requires_and_verifies_current_session_presentation(self):
        temporary, root = self.fixture()
        with temporary, orchestration_fixture.offline_leader(grill_workspace), mock.patch.object(
                grill_workspace, "dependency_report", return_value={"verdict": "OK"}):
            code, refused = self.run_cli("preflight", str(root), "--runtime", "codex", "--skip-backlog")
            self.assertEqual((code, refused["code"]), (2, "LEADER-AUTHORITY-UNPROVEN"))
            self.assertFalse(refused["presentation"]["work_ready"])
            self.assertEqual(refused["presentation"]["trust"], "undetermined")
            self.assertFalse(store.store_exists(root))
            with mock.patch.object(grill_workspace, "_leader_boundary", side_effect=lambda *args:
                    orchestration_fixture.boundary(grill_workspace, *args, loaded=False)[0]):
                code, pending = self.run_cli("preflight", str(root), "--runtime", "codex", "--skip-backlog",
                                             "--session-ref", orchestration_fixture.SESSION)
                self.assertEqual((code, pending["code"]), (2, "STYLE-LOAD-UNCONFIRMED"))
                self.assertEqual(pending["presentation"]["load_request"]["scope"]["work_id"], None)
            with mock.patch.object(grill_workspace, "_leader_boundary", side_effect=lambda *args:
                    orchestration_fixture.boundary(grill_workspace, *args)[0]):
                code, ready = self.run_cli("preflight", str(root), "--runtime", "codex", "--skip-backlog",
                                           "--session-ref", orchestration_fixture.SESSION)
                self.assertEqual((code, ready["verdict"], ready["presentation"]["work_ready"]), (0, "OK", True))

    def test_every_work_entry_reobserves_authority_and_requires_presentation(self):
        temporary, root = self.fixture()
        core = grill_workspace.grill_core_module("agent_runtime")
        with temporary, orchestration_fixture.offline_leader(grill_workspace):
            code, created = self.run_cli("init", str(root), "--work-id", "work-x", "--type", "feature",
                "--slug", "x", "--runtime", "codex", "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, created)
            item = store.read_snapshot(root).document["agent_orchestration"]["work_items"]["work-x"]
            context_id = item["current_context_id"]
            context = item["contexts"][context_id]
            commands = [
                ("gauntlet-run",), ("gauntlet-resume", "--run-id", "r"),
                ("gauntlet-prepare-worker", "--run-id", "r", "--worker-id", "w", "--scope", "x"),
                ("gauntlet-wave-declare", "--run-id", "r", "--dag", "d", "--node-id", "n"),
                ("gauntlet-worker-declare", "--run-id", "r", "--wave-id", "w", "--dag", "d", "--node-id", "n", "--tier", "small", "--files", "x"),
                ("gauntlet-remediate", "--run-id", "r", "--worker-id", "w", "--reason", "stall"),
                ("gauntlet-converge", "--run-id", "r", "--dag", "d", "--wave-id", "w"),
                ("gauntlet-progress-record", "--run-id", "r", "--worker-id", "w"),
                ("gauntlet-worker-terminal", "--run-id", "r", "--worker-id", "w", "--outcome", "completed"),
                ("gauntlet-run-abandon", "--run-id", "r", "--attestation", "a"),
                ("gauntlet-step-enter", "--context-id", context_id, "--epoch", "1", "--step", "implement-parallel"),
                ("gauntlet-activity", "--context-id", context_id, "--epoch", "1", "--activity-id", "a", "--scope", "interview", "--kind", "author", "--phase", "prepare", "--input-manifest", "m"),
                ("attest", "--step", "specify", "--artifact", "a", "--out", "o"),
                ("checkpoint", "--step", "specify", "--state", "in-progress"),
                ("partition-emit", "--feature", "f", "--apply"),
                ("gauntlet-tasks-reconcile", "--dag", "d", "--apply"),
                ("task-files-migrate", "--feature", "f", "--proposal", "p"),
                ("phase-turn",),
            ]
            def invoke(command):
                return self.run_cli(command[0], str(root), "--work-id", "work-x", "--session-ref",
                                    orchestration_fixture.SESSION, *command[1:])
            def remove_presentation(document):
                document["agent_orchestration"]["work_items"]["work-x"]["contexts"][context_id].pop("presentation")
                return document
            store.transact(root, remove_presentation)
            with mock.patch.object(grill_workspace, "_leader_boundary", side_effect=AssertionError("missing presentation reached adapter")):
                for command in commands:
                    with self.subTest(command=command[0], case="absent"):
                        self.assertEqual(invoke(command)[1]["code"], "STYLE-LOAD-UNCONFIRMED")
            # T005/FR-006: exercised on a disposable, freshly-adopted work item
            # (created here, before _session_readiness is mocked below, since
            # init still needs full presentation) so the shared "work-x" context
            # this test keeps reusing below stays ACTIVE -- gauntlet-prepare-switch
            # commits a real QUIESCING transition (checkpoint, operation,
            # worktree_identity) once it succeeds, and the Store's history is
            # append-only, so that would not be safely reversible in place.
            code, seeded = self.run_cli("init", str(root), "--work-id", "work-quiescing-check", "--type", "feature",
                "--slug", "work-quiescing-check", "--runtime", "codex", "--session-ref", orchestration_fixture.SESSION,
                "--skip-backlog")
            self.assertEqual(code, 0, seeded)
            quiescing_context_id = store.read_snapshot(root).document["agent_orchestration"]["work_items"][
                "work-quiescing-check"]["current_context_id"]
            with mock.patch.object(grill_workspace, "_session_readiness", side_effect=AssertionError("cleanup requires style")):
                code, cleaned = invoke(("gauntlet-cleanup", "--context-id", context_id, "--epoch", "1"))
                self.assertEqual((code, cleaned["verdict"]), (0, "CLEANED"))
                # A fresh work item has no committed checkpoint yet (checkpoint_head
                # is None), so this no longer refuses with CONTINUITY-CHECKPOINT-MISSING
                # -- it succeeds and projects an initial checkpoint from the current
                # state instead. The refusal still applies to a *declared but
                # unknown* checkpoint_head (a string that doesn't resolve inside
                # checkpoints); that branch is covered on its own in
                # test_prepare_switch_refuses_declared_but_unknown_checkpoint, since
                # the Store itself refuses to persist a document shaped that way
                # through any legitimate write (see p02-a's T005 notes).
                code, prepared = self.run_cli("gauntlet-prepare-switch", str(root), "--work-id", "work-quiescing-check",
                    "--session-ref", orchestration_fixture.SESSION, "--context-id", quiescing_context_id,
                    "--epoch", "1", "--to-runtime", "claude")
                self.assertEqual((code, prepared.get("verdict")), (0, "QUIESCING"), prepared)
                # T021/FR-006: the verdict alone proves nothing -- read the
                # snapshot back and require the synthesized resume point to be
                # committed as the head, in the current checkpoint schema, with
                # no predecessor and both digests taken from their real sources.
                seeded_item = store.read_snapshot(root).document["agent_orchestration"][
                    "work_items"]["work-quiescing-check"]
                head = seeded_item["checkpoint_head"]
                self.assertIsInstance(head, str)
                initial = seeded_item["checkpoints"][head]
                self.assertEqual(initial["schema"], agent_orchestration.CHECKPOINT_SCHEMA_V2)
                self.assertEqual((initial["checkpoint_id"], initial["context_id"]), (head, quiescing_context_id))
                self.assertIsNone(initial["previous_checkpoint_id"])
                self.assertEqual(initial["context_inputs_sha256"],
                                 seeded_item["contexts"][quiescing_context_id]["inputs_sha256"])
                self.assertEqual(initial["origin_metadata_sha256"], seeded_item["origin"]["metadata_sha256"])
                # T033/FR-011: the *projected development state*, which nothing
                # else asserts. The store contract dropped the equivalent
                # assertion when T029 stopped importing the CLI emitter, and its
                # comment claims this case exercises it -- it did not: schema,
                # identifiers and the two digests say nothing about what the
                # emitter projected. And validate_block accepts a dict OR a list
                # in development_sequence, so an emitter regressed to the v1 map
                # would pass the whole suite. Read the live state back and
                # require the checkpoint to carry it, in list form.
                _, live_state = grill_workspace.read_development_state(
                    root, grill_workspace.resolve_development_item(root, "work-quiescing-check"),
                    "work-quiescing-check")
                development = live_state["development"]
                self.assertIsInstance(initial["development_sequence"], list)
                self.assertTrue(initial["development_sequence"])
                self.assertEqual(initial["development_sequence"], development["sequence"])
                self.assertEqual(initial["current_step"], development.get("current_step"))
                self.assertEqual(initial["accepted_outputs"], development.get("attested_outputs", {}))
                self.assertEqual(initial["accepted_executions"], development.get("attested_executions", {}))
            # -- T037/R4/FR-011: the SECOND emitter of the projected
            # development state. `checkpoint_command` builds the same block
            # from the same line, and nothing observed it: regressing only
            # that emitter back to the v1 map (a dict) left all three
            # validators green, because validate_block accepts a dict OR a
            # list in development_sequence. The assertions above are replicated
            # here against the checkpoint this verb commits, read back from the
            # store and compared to the live state -- never to literals. --
            code, confirm_seed = self.run_cli("init", str(root), "--work-id", "work-confirm-projection",
                "--type", "feature", "--slug", "work-confirm-projection", "--runtime", "codex",
                "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, confirm_seed)
            code, updated = self.run_cli("checkpoint", str(root), "--work-id", "work-confirm-projection",
                "--step", "specify", "--state", "in-progress", "--operation-id", "op-confirm-projection",
                "--session-ref", orchestration_fixture.SESSION)
            self.assertEqual((code, updated.get("verdict")), (0, "UPDATED"), updated)
            confirm_item = store.read_snapshot(root).document["agent_orchestration"][
                "work_items"]["work-confirm-projection"]
            confirmed = confirm_item["checkpoints"][confirm_item["checkpoint_head"]]
            self.assertEqual(confirmed["checkpoint_id"], updated["checkpoint_id"])
            self.assertEqual(confirmed["schema"], agent_orchestration.CHECKPOINT_SCHEMA_V2)
            _, confirm_state = grill_workspace.read_development_state(
                root, grill_workspace.resolve_development_item(root, "work-confirm-projection"),
                "work-confirm-projection")
            confirm_development = confirm_state["development"]
            self.assertIsInstance(confirmed["development_sequence"], list)
            self.assertTrue(confirmed["development_sequence"])
            self.assertEqual(confirmed["development_sequence"], confirm_development["sequence"])
            self.assertEqual(confirmed["current_step"], confirm_development.get("current_step"))
            self.assertEqual(confirmed["step_states"], confirm_development.get("steps", {}))
            self.assertEqual(confirmed["accepted_outputs"], confirm_development.get("attested_outputs", {}))
            self.assertEqual(confirmed["accepted_executions"], confirm_development.get("attested_executions", {}))

            def restore(document):
                document["agent_orchestration"]["work_items"]["work-x"]["contexts"][context_id] = copy.deepcopy(context)
                return document
            store.transact(root, restore)
            before = store.read_snapshot(root).content_sha256
            empty_context = list(commands[10])
            empty_context[2] = ""
            self.assertEqual(invoke(empty_context)[1]["code"], "LEADER-AUTHORITY-UNPROVEN")
            with mock.patch.object(grill_workspace, "_leader_boundary", side_effect=core.RuntimeError("LEADER-AUTHORITY-UNPROVEN")) as probe:
                for command in commands:
                    with self.subTest(command=command[0], case="revoked"):
                        self.assertEqual(invoke(command)[1]["code"], "LEADER-AUTHORITY-UNPROVEN")
                self.assertEqual(probe.call_count, len(commands))
                self.assertEqual(invoke(("gauntlet-cleanup", "--context-id", context_id, "--epoch", "1"))[1]["code"], "LEADER-AUTHORITY-UNPROVEN")
                self.assertEqual(invoke(("gauntlet-prepare-switch", "--context-id", context_id, "--epoch", "1", "--to-runtime", "claude"))[1]["code"], "LEADER-AUTHORITY-UNPROVEN")
            for mutation in ("dispatch", "incarnation", "config"):
                adapter, show, transcript = orchestration_fixture.boundary(grill_workspace, root, "codex", orchestration_fixture.SESSION, "work-x")
                if mutation == "dispatch":
                    show["result"]["dispatch"]["capabilityRevokedAt"] = "revoked"
                elif mutation == "incarnation":
                    show["result"]["terminal"]["incarnationId"] = "new-incarnation"
                else:
                    transcript["result"]["sourceIdentity"] = "current-config-changed"
                    policy_raw = (grill_workspace.ASSETS / "agent-orchestration.v1.json").read_bytes()
                    _, pending = core.project_leader_presentation(adapter, policy=json.loads(policy_raw),
                        policy_sha256=grill_workspace.hash_bytes(policy_raw),
                        gwd_skill_sha256=grill_workspace.hash_bytes((grill_workspace.ASSETS.parent / "SKILL.md").read_bytes()),
                        runtime="codex", scope={"kind": "gwd", "root": str(root), "work_id": "work-x"})
                    transcript["result"]["transcript"]["messages"][1]["blocks"][0]["output"] = json.dumps(
                        {"verdict": "BLOCKED", "code": "STYLE-LOAD-UNCONFIRMED", "presentation": pending})
                with self.subTest(mutation=mutation), mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter):
                    self.assertEqual(invoke(commands[0])[1]["code"], "STYLE-SCOPE-CONFLICT" if mutation == "config" else "LEADER-AUTHORITY-UNPROVEN")
                    self.assertEqual(invoke(commands[10])[0], 2)
            self.assertEqual(store.read_snapshot(root).content_sha256, before)

    def test_native_exec_result_variable_wrapper(self):
        core = grill_workspace.grill_core_module("agent_runtime")
        literal = '{cmd:"/usr/bin/true",workdir:"/tmp",yield_time_ms:30000,max_output_tokens:12000}'
        wrapper = "const r = await tools.exec_command(" + literal + "); text(JSON.stringify(r));"
        call = {"type": "tool-call", "name": "exec", "input": wrapper}
        self.assertEqual(core._tool_command(call), ["/usr/bin/true"])
        # No extra statement/call, output mutation, expression, ambiguous key,
        # relative cwd, or shell interpretation earns evidence.
        for altered in (
            wrapper + " text('forged');", wrapper * 2,
            wrapper.replace("stringify(r)", "stringify({...r,output:'forged'})"),
            wrapper.replace("stringify(r)", "stringify(other)"),
            wrapper.replace("; text", "; r.output = 'forged'; text"),
            wrapper.replace('cmd:"/usr/bin/true"', 'cmd:process.env.COMMAND'),
            wrapper.replace('cmd:"/usr/bin/true"', 'cmd:"/usr/bin/true", "cmd":"/usr/bin/false"'),
            wrapper.replace('workdir:"/tmp"', 'workdir:"relative"'),
            wrapper.replace('workdir:"/tmp"', 'workdir:null'),
            wrapper.replace('cmd:"/usr/bin/true"', 'cmd:`/usr/bin/true`'),
            wrapper.replace('cmd:"/usr/bin/true"', 'cmd:"/usr/bin/true", ...options'),
            wrapper.replace('cmd:"/usr/bin/true"', 'cmd:"/usr/bin/true", env:{X:"x"}'),
            wrapper.replace('cmd:"/usr/bin/true"', 'cmd:"/usr/bin/true ; printf forged"'),
            wrapper.replace('cmd:"/usr/bin/true"', 'cmd:"/usr/bin/true $(true)"'),
        ):
            with self.subTest(input=altered):
                self.assertEqual(core._tool_command({**call, "input": altered}), [])
        quoted = wrapper.replace('/usr/bin/true', "/usr/bin/echo 'cmd: value'")
        self.assertEqual(core._tool_command({**call, "input": quoted}), ["/usr/bin/echo", "cmd: value"])
        temp, root = self.fixture()
        with temp, orchestration_fixture.offline_leader(grill_workspace):
            adapter, _, source = orchestration_fixture.boundary(
                grill_workspace, root, "codex", orchestration_fixture.SESSION, None)
            messages = source["result"]["transcript"]["messages"]
            request = json.loads(messages[1]["blocks"][0]["output"])["presentation"]["load_request"]
            for index in (0, 2):
                command = messages[index]["blocks"][0]["input"]["cmd"]
                literal = '{cmd:' + json.dumps(command) + ',workdir:' + json.dumps(str(root)) + ',yield_time_ms:30000,max_output_tokens:12000}'
                messages[index]["blocks"][0] = {**call, "input":
                    "const r = await tools.exec_command(" + literal + "); text(JSON.stringify(r));"}
                result = messages[index + 1]["blocks"][0]
                result["output"] = "Script completed\nWall time 0.1 seconds\nOutput:\n" + json.dumps(
                    {"exit_code": 2 if index == 0 else 0, "output": result["output"]})
            observed = adapter.observe()
            self.assertIsNotNone(core._full_read(observed, {"messages": messages}, request))
            for index in (1, 3):
                output = messages[index]["blocks"][0]["output"]
                for altered in (output[:1200] + "\n… (truncated)", output.replace('"exit_code":', '"exit_code":1,"exit_code":'),
                                output.replace('"output":', '"session_id":123,"output":')):
                    messages[index]["blocks"][0]["output"] = altered
                    self.assertIsNone(core._full_read(observed, {"messages": messages}, request))
                messages[index]["blocks"][0]["output"] = output

    def test_exact_native_commands_and_envelope(self):
        core = grill_workspace.grill_core_module("agent_runtime")
        # Literal Orca capture, ctx_28bc43fcfd6c / ctco_01a0a1ab-0180-73e3-af98-5ae259c41421.
        native = {"type": "tool-call", "name": "exec",
                  "input": 'text(await tools.exec_command({"cmd":"/usr/bin/true","max_output_tokens":1000}));\n'}
        output = ('Script completed\nWall time 0.1 seconds\nOutput:\n'
                  '{"chunk_id":"c6c076","wall_time_seconds":0.000003266,"exit_code":0,"original_token_count":0,"output":""}')
        transcript = {"messages": [
            {"role": "assistant", "blocks": [native]},
            {"id": "ctco_01a0a1ab-0180-73e3-af98-5ae259c41421", "role": "tool",
             "blocks": [{"type": "tool-result", "output": output}]}]}
        self.assertEqual(list(core._tool_results(transcript)), [(native, transcript["messages"][1]["id"], "")])
        self.assertEqual(core._tool_command(native), ["/usr/bin/true"])
        for altered in (native["input"] + "text('forged');", native["input"] * 2,
                        native["input"].replace("text(await", "text(String(await"),
                        native["input"].replace('"max_output_tokens":1000', '"command":"/usr/bin/false"')):
            self.assertEqual(core._tool_command({**native, "input": altered}), [])
        temporary, root = self.fixture()
        with temporary, orchestration_fixture.offline_leader(grill_workspace):
            for runtime in ("codex", "claude"):
                adapter, _, source = orchestration_fixture.boundary(grill_workspace, root, runtime, orchestration_fixture.SESSION, None)
                observed = adapter.observe()
                messages = source["result"]["transcript"]["messages"]
                original = copy.deepcopy(messages)
                request = json.loads(messages[1]["blocks"][0]["output"])["presentation"]["load_request"]
                self.assertIsNotNone(core._full_read(observed, {"messages": messages}, request))
                compaction = [{"id": "compact", "role": "system", "blocks": [{"type": "compaction"}]}]
                self.assertIsNone(core._full_read(observed, {"messages": messages + compaction}, request))
                self.assertIsNotNone(core._full_read(observed, {"messages": messages + compaction + messages}, request))
                key = "command" if runtime == "claude" else "cmd"
                for index in (0, 2):
                    command = original[index]["blocks"][0]["input"][key]
                    tokens = shlex.split(command)
                    bad = [shlex.join(["/tmp/caller/python3" if index == 0 else "/tmp/caller/cat", *tokens[1:]]),
                           command + " ; printf forged-result", command + " > /tmp/output", command + " | cat",
                           command + " && true", command + " # comment", command + " extra", command + " $(true)",
                           command + " `true`", command + "\ntrue", "sh -c " + shlex.quote(command)]
                    for altered in bad:
                        messages[:] = copy.deepcopy(original)
                        messages[index]["blocks"][0]["input"][key] = altered
                        with self.subTest(runtime=runtime, index=index, command=altered):
                            self.assertIsNone(core._full_read(observed, {"messages": messages}, request))
                messages[:] = copy.deepcopy(original)
                for index in (0, 2):
                    command = messages[index]["blocks"][0]["input"][key]
                    messages[index]["blocks"][0] = {"type": "tool-call", "name": "exec",
                        "input": "text(await tools.exec_command(" + json.dumps({"cmd": command}) + "));\n"}
                    raw = messages[index + 1]["blocks"][0]["output"]
                    messages[index + 1]["blocks"][0]["output"] = "Script completed\nWall time 0.1 seconds\nOutput:\n" + json.dumps(
                        {"exit_code": 2 if index == 0 else 0, "output": raw, "original_token_count": 100})
                self.assertIsNotNone(core._full_read(observed, {"messages": messages}, request))
                transport = copy.deepcopy(messages)
                transport[1]["blocks"][0]["isError"] = True
                transport[3]["blocks"][0]["output"] = transport[3]["blocks"][0]["output"].rstrip("\n")
                self.assertIsNotNone(core._full_read(observed, {"messages": transport}, request))
                envelope = copy.deepcopy(messages)
                for index in (0, 2):
                    # Reject duplicates before json decoding discards the first value.
                    for duplicate in ('"cmd":"/usr/bin/false",', '"max_output_tokens":1,"max_output_tokens":2,'):
                        messages[:] = copy.deepcopy(envelope)
                        call = messages[index]["blocks"][0]
                        call["input"] = call["input"].replace("{", "{" + duplicate, 1)
                        self.assertIsNone(core._full_read(observed, {"messages": messages}, request))
                        with mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter), \
                             self.assertRaisesRegex(grill_workspace.CliFailure, "STYLE-LOAD-UNCONFIRMED"):
                            grill_workspace._session_readiness(root, runtime, orchestration_fixture.SESSION, work_id=None)
                    for duplicate in ('"exit_code":1,', '"output":"forged",', '"session_id":1,"session_id":null,'):
                        messages[:] = copy.deepcopy(envelope)
                        result = messages[index + 1]["blocks"][0]
                        result["output"] = result["output"].replace("{", "{" + duplicate, 1)
                        self.assertIsNone(core._full_read(observed, {"messages": messages}, request))
                    for altered in ("/tmp/caller/" + ("python3" if index == 0 else "cat"),
                                    shlex.join([sys.executable, "-c", "print('forged')"]),
                                    original[index]["blocks"][0]["input"][key] + " ; printf forged"):
                        messages[:] = copy.deepcopy(envelope)
                        messages[index]["blocks"][0]["input"] = "text(await tools.exec_command(" + json.dumps({"cmd": altered}) + "));\n"
                        self.assertIsNone(core._full_read(observed, {"messages": messages}, request))
                messages[:] = copy.deepcopy(envelope)
                messages[0]["blocks"][0]["input"] += "text('forged');"
                self.assertIsNone(core._full_read(observed, {"messages": messages}, request))
            listing = json.dumps({"installed": [{"pluginId": core.PRESENTATION_COMPONENT,
                "enabled": True, "version": "0.3.0", "installPath": "/installed/adhd"}]})
            with mock.patch.object(shutil, "which", return_value="/native/codex"):
                for command, expected in (("/native/codex plugin list --json", True),
                        ("codex plugin list --json", False), ("/tmp/caller/codex plugin list --json", False),
                        ("/native/codex plugin list --json ; printf forged-result", False),
                        ("/native/codex plugin list --json > /tmp/output", False),
                        ("/native/codex plugin list --json extra", False),
                        ("/native/codex plugin list --json $(true)", False)):
                    transcript = {"messages": orchestration_fixture.tool_pair("codex", command, listing, "listing")}
                    axes = core._orca_presentation_axes({"provider": "codex", "source_ref": "orca:ctx-fixture"}, transcript)
                    self.assertEqual(bool(axes["installation"]), expected, command)
                    self.assertEqual((axes["trust"], axes["enablement"]), ({}, {}))
                with mock.patch.object(core, "_runtime_config_axes", return_value={
                    "configuration": {"state": "observed"},
                    "enablement": {"state": "enabled"},
                    "trust": {"state": "ready"},
                }):
                    axes = core._orca_presentation_axes(
                        {"provider": "codex", "source_ref": "orca:ctx-fixture"},
                        {"messages": orchestration_fixture.tool_pair("codex", "/native/codex plugin list --json", listing, "listing")},
                    )
                    self.assertEqual(axes["configuration"]["state"], "observed")
                    self.assertEqual(axes["enablement"]["state"], "enabled")
                    self.assertEqual(axes["trust"]["state"], "ready")

    def test_codex_install_path_composed_from_cache_when_installpath_absent(self):
        # Fixture is the real 0.154.0 `codex plugin list --json` shape: no
        # installPath, only marketplaceName/name/version (work item
        # fix-codex-install-path, FR-001..FR-009).
        core = grill_workspace.grill_core_module("agent_runtime")
        listing = (Path(__file__).parent / "fixtures/orchestration/codex-plugin-list-0.154.0.json").read_text()
        approved_raw = orchestration_fixture.REFERENCE.read_bytes()
        divergent_raw = b"---\nname: offline-presentation-fixture\n---\n# Divergent\n\nNot the approved bytes.\n"
        policy = {"presentation": {"schema": core.PRESENTATION_SCHEMA, "component": core.PRESENTATION_COMPONENT,
            "loader": core.PRESENTATION_LOADER,
            "approved": [{"version": "0.3.0", "skill_sha256": "sha256:" + hashlib.sha256(approved_raw).hexdigest()}]}}
        scope = {"kind": "gwd", "root": "fixture", "work_id": "work-x"}
        observed = {"provider": "codex", "source_ref": "orca:ctx-fixture"}

        def seed_cache(home, marketplace_name, name, version, raw):
            skill_dir = Path(home) / "plugins" / "cache" / marketplace_name / name / version / "skills" / "i-have-adhd"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_bytes(raw)
            return skill_dir.parent.parent

        def axes_for(home, payload):
            transcript = {"messages": orchestration_fixture.tool_pair(
                "codex", "/native/codex plugin list --json", json.dumps(payload), "listing")}
            with mock.patch.dict(os.environ, {"CODEX_HOME": home}):
                return core._orca_presentation_axes(observed, transcript)

        with mock.patch.object(shutil, "which", return_value="/native/codex"):
            listing_payload = json.loads(listing)
            with tempfile.TemporaryDirectory() as home:
                install_root = seed_cache(home, "i-have-adhd", "i-have-adhd", "0.3.0", approved_raw)

                # US1-S1: real listing + cache copy present -> installation present,
                # skill_ref rooted under the temporary CODEX_HOME.
                first = axes_for(home, listing_payload)
                self.assertEqual(first["installation"]["status"], "present")
                self.assertEqual(first["installation"]["version"], "0.3.0")
                self.assertEqual(first["installation"]["install_root"], str(install_root))
                self.assertEqual(first["installation"]["skill_ref"], str(install_root / "skills/i-have-adhd/SKILL.md"))
                self.assertTrue(first["installation"]["skill_ref"].startswith(home))

                # US1-S2: repeating the same observation yields an identical result.
                second = axes_for(home, listing_payload)
                self.assertEqual(first, second)

                # US2-S1: installed false -> empty installation.
                not_installed = copy.deepcopy(listing_payload)
                not_installed["installed"][0]["installed"] = False
                self.assertEqual(axes_for(home, not_installed)["installation"], {})

                # US2-S4 / FR-009: each identification field, absent or unsafe -> empty.
                for field in ("marketplaceName", "name", "version"):
                    absent = copy.deepcopy(listing_payload)
                    del absent["installed"][0][field]
                    self.assertEqual(axes_for(home, absent)["installation"], {}, (field, "absent"))
                    for value in ("", ".", "..", "seg/ment", "seg\\ment", "D:", "C:"):
                        mutated = copy.deepcopy(listing_payload)
                        mutated["installed"][0][field] = value
                        self.assertEqual(axes_for(home, mutated)["installation"], {}, (field, value))

                # FR-002/FR-009: a non-string identification field (int) and a null
                # field both fail closed to empty, never a TypeError from PureWindowsPath.
                wrong_types = copy.deepcopy(listing_payload)
                wrong_types["installed"][0]["version"] = 1
                wrong_types["installed"][0]["marketplaceName"] = None
                self.assertEqual(axes_for(home, wrong_types)["installation"], {})

                # I2/FR-009: a literal "D:" segment must be rejected as a value,
                # even when a directory literally named "D:" exists on disk (POSIX
                # allows that literal name; the join alone would not fail there,
                # so the filter itself -- not a failed lookup -- must reject it).
                # The seed itself only runs off-Windows: "D:" is a drive anchor
                # there, so Path(home) / "plugins" / "cache" / "D:" reanchors to
                # a drive-relative path outside the temp dir instead of nesting.
                # The rejection assertion still runs on every OS unconditionally,
                # since the filter must reject the value before touching disk.
                with tempfile.TemporaryDirectory() as drive_home:
                    if os.name != "nt":
                        seed_cache(drive_home, "D:", "i-have-adhd", "0.3.0", approved_raw)
                    drive_payload = copy.deepcopy(listing_payload)
                    drive_payload["installed"][0]["marketplaceName"] = "D:"
                    self.assertEqual(axes_for(drive_home, drive_payload)["installation"], {})

                # FR-004: installPath present but null never triggers composition either.
                null_install_path = copy.deepcopy(listing_payload)
                null_install_path["installed"][0]["installPath"] = None
                self.assertEqual(axes_for(home, null_install_path)["installation"], {})

                # US2-S1 variant: the "installed" flag key itself missing -> empty.
                no_installed_key = copy.deepcopy(listing_payload)
                del no_installed_key["installed"][0]["installed"]
                self.assertEqual(axes_for(home, no_installed_key)["installation"], {})

                # FR-004: a relative installPath never falls back to the composed cache path.
                relative = copy.deepcopy(listing_payload)
                relative["installed"][0]["installPath"] = "relative/adhd"
                self.assertEqual(axes_for(home, relative)["installation"], {})

            # I1: Path.home() raising RuntimeError (no CODEX_HOME, no resolvable
            # home) fails closed to empty installation, never an uncaught exception.
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("CODEX_HOME", None)
                with mock.patch.object(Path, "home", side_effect=RuntimeError("no home")):
                    transcript = {"messages": orchestration_fixture.tool_pair(
                        "codex", "/native/codex plugin list --json", listing, "listing")}
                    self.assertEqual(core._orca_presentation_axes(observed, transcript)["installation"], {})

            # I1: a PermissionError from Path.is_dir on an otherwise valid, seeded
            # cache also fails closed to empty, never an uncaught exception.
            with tempfile.TemporaryDirectory() as perm_home:
                seed_cache(perm_home, "i-have-adhd", "i-have-adhd", "0.3.0", approved_raw)
                with mock.patch.object(Path, "is_dir", side_effect=PermissionError("denied")):
                    self.assertEqual(axes_for(perm_home, listing_payload)["installation"], {})

            # US2-S2: cache root absent (fresh CODEX_HOME) -> empty installation.
            with tempfile.TemporaryDirectory() as empty_home:
                self.assertEqual(axes_for(empty_home, listing_payload)["installation"], {})

            # US2-S3 (U2): cache copy diverges from the approved SKILL.md bytes ->
            # full presentation evaluation reports STYLE-CONTENT-INCOMPATIBLE.
            with tempfile.TemporaryDirectory() as divergent_home:
                seed_cache(divergent_home, "i-have-adhd", "i-have-adhd", "0.3.0", divergent_raw)
                axes = axes_for(divergent_home, listing_payload)
                self.assertEqual(axes["installation"]["status"], "present")
                state = presentation_state(policy=policy, policy_sha256="a" * 64, gwd_skill_sha256="b" * 64,
                    runtime="codex", session_identity="session-1", config_fingerprint="config-1", scope=scope,
                    installation=axes["installation"], enablement={}, trust={})
                self.assertEqual(state["compatibility"], "incompatible")
                self.assertIn("STYLE-CONTENT-INCOMPATIBLE", [entry["code"] for entry in state["diagnostics"]])

    def test_presentation_fingerprint_ignores_repeated_listing_event_identity(self):
        core = grill_workspace.grill_core_module("agent_runtime")
        axes = {
            "configuration": {"state": "observed", "source_sha256": "a" * 64},
            "installation": {"status": "present", "version": "0.3.0"},
            "plugin_listing": {"source_ref": "orca:ctx:event-1", "source_sha256": "b" * 64},
        }
        first = core._presentation_config_fingerprint("source-1", axes)
        axes["plugin_listing"]["source_ref"] = "orca:ctx:event-2"
        self.assertEqual(core._presentation_config_fingerprint("source-1", axes), first)
        axes["installation"]["version"] = "0.4.0"
        self.assertNotEqual(core._presentation_config_fingerprint("source-1", axes), first)

        # US3: a Claude listing with an absolute installPath keeps the current
        # behavior (present, install_root == installPath), no Codex cache lookup.
        with mock.patch.object(shutil, "which", return_value="/native/claude"):
            claude_listing = json.dumps({"installed": [{"pluginId": core.PRESENTATION_COMPONENT,
                "version": "0.3.0", "installPath": "/abs/claude/adhd"}]})
            transcript = {"messages": orchestration_fixture.tool_pair(
                "claude", "/native/claude plugin list --json", claude_listing, "listing")}
            axes = core._orca_presentation_axes({"provider": "claude", "source_ref": "orca:ctx-fixture"}, transcript)
        self.assertEqual(axes["installation"], {"status": "present", "version": "0.3.0",
            "install_root": "/abs/claude/adhd", "skill_ref": "/abs/claude/adhd/skills/i-have-adhd/SKILL.md"})

    def ready_presentation(self, runtime="codex", scope=None):
        return {
            "schema": "grill-gwd-presentation/v1", "component": "i-have-adhd@i-have-adhd",
            "minimum_version": "0.3.0", "loader": "gwd-reference/v1", "runtime": runtime,
            "session_identity": "observed-session", "config_fingerprint": "config-1",
            "scope": scope or {"kind": "gwd", "root": "fixture", "work_id": "work-x"},
            "policy_sha256": "a" * 64, "gwd_skill_sha256": "b" * 64,
            "installation": {"status": "present"}, "compatibility": "approved",
            "enablement": "enabled", "trust": "ready", "loading": "loaded",
            "behavior": "not_tested", "application": "active", "suspension": None,
            "evidence": {}, "load_request": None, "use_ready": True, "work_ready": True,
            "functional_verified": False, "diagnostics": [],
        }

    def readiness(self, runtime="codex", scope=None):
        return {"ref": "session-1", "sha256": "f" * 64,
                "incarnation": "inc-1", "presentation": self.ready_presentation(runtime, scope)}

    def presentation_fixture(self):
        temporary = tempfile.TemporaryDirectory()
        reference = Path(temporary.name) / "SKILL.md"
        raw = b"---\nname: fixture\n---\n# Fixture\n\nRule one.\n"
        reference.write_bytes(raw)
        policy = {
            "presentation": {
                "schema": "grill-gwd-presentation/v1", "component": "i-have-adhd@i-have-adhd",
                "minimum_version": "0.3.0", "loader": "gwd-reference/v1",
                "approved": [{"version": "0.3.0", "skill_sha256": "sha256:" + __import__("hashlib").sha256(raw).hexdigest()}],
            }
        }
        scope = {"kind": "gwd", "root": "fixture", "invocation_ref": "gwd-entry"}
        kwargs = {"policy": policy, "policy_sha256": "a" * 64, "gwd_skill_sha256": "b" * 64,
                  "runtime": "codex", "session_identity": "session-1", "config_fingerprint": "config-1",
                  "scope": scope, "installation": {"status": "present", "version": "0.3.0",
                  "skill_ref": str(reference), "marketplace": "i-have-adhd", "install_root": str(reference.parent)},
                  "enablement": {"state": "enabled", "source_ref": "plugin-list", "source_sha256": "c" * 64},
                  "trust": {"state": "ready", "source_ref": "startup", "source_sha256": "d" * 64}}
        return temporary, reference, kwargs

    def test_presentation_bootstrap(self):
        temporary, reference, kwargs = self.presentation_fixture()
        with temporary:
            pending = presentation_state(**kwargs)
            self.assertFalse(pending["use_ready"])
            self.assertFalse(pending["work_ready"])
            self.assertEqual(pending["loading"], "unconfirmed")
            request = pending["load_request"]
            self.assertEqual(request["skill_ref"], str(reference))
            loaded = presentation_state(**kwargs, loading={"load_request": request, "evidence_kind": "full_read", "event_ref": "tool-read-1",
                "event_sha256": "e" * 64, "session_identity": "session-1", "config_fingerprint": "config-1",
                "scope": kwargs["scope"], "skill_sha256": request["skill_sha256"], "body_sha256": request["body_sha256"]})
            self.assertEqual((loaded["loading"], loaded["use_ready"], loaded["work_ready"],
                              loaded["behavior"], loaded["functional_verified"]),
                             ("loaded", True, True, "not_tested", False))
            for changed in ({"session_identity": "other"}, {"config_fingerprint": "other"},
                            {"evidence_kind": "exit_0"}, {"scope": {"kind": "gwd"}}):
                invalid = {"load_request": request, "evidence_kind": "full_read", "event_ref": "tool-read-1", "event_sha256": "e" * 64,
                           "session_identity": "session-1", "config_fingerprint": "config-1", "scope": kwargs["scope"],
                           "skill_sha256": request["skill_sha256"], "body_sha256": request["body_sha256"], **changed}
                self.assertFalse(presentation_state(**kwargs, loading=invalid)["use_ready"])
            reference.write_bytes(b"---\nname: fixture\n---\ntruncated")
            self.assertEqual(presentation_state(**kwargs)["compatibility"], "incompatible")

    def test_presentation_context(self):
        temporary, _reference, kwargs = self.presentation_fixture()
        with temporary:
            pending = presentation_state(**kwargs)
            request = pending["load_request"]
            suspended = presentation_state(**kwargs, application="suspended_by_user", loading={"stale": True},
                suspension={"command": "stop adhd mode", "source_ref": "human-1", "source_sha256": "f" * 64,
                            "session_identity": "session-1", "config_fingerprint": "config-1", "scope": kwargs["scope"]})
            self.assertEqual((suspended["application"], suspended["loading"], suspended["work_ready"],
                              suspended["use_ready"], suspended["functional_verified"], suspended["load_request"]),
                             ("suspended_by_user", "stale", True, False, False, None))
            invalid = presentation_state(**kwargs, application="suspended_by_user", loading={"stale": True},
                suspension={"command": "stop adhd mode", "source_ref": "human-1", "source_sha256": "f" * 64,
                            "session_identity": "other", "config_fingerprint": "config-1", "scope": kwargs["scope"]})
            self.assertFalse(invalid["work_ready"])
            active = presentation_state(**kwargs, loading={"load_request": request, "evidence_kind": "full_read", "event_ref": "read-1",
                "event_sha256": "e" * 64, "session_identity": "session-1", "config_fingerprint": "config-1",
                "scope": kwargs["scope"], "skill_sha256": request["skill_sha256"], "body_sha256": request["body_sha256"]})
            self.assertTrue(active["use_ready"])

    def test_presentation_scope_preservation(self):
        temporary, _reference, kwargs = self.presentation_fixture()
        with temporary:
            pending = presentation_state(**kwargs)
            request = pending["load_request"]
            presentation = presentation_state(**kwargs, loading={"load_request": request, "evidence_kind": "full_read", "event_ref": "read-1",
                "event_sha256": "e" * 64, "session_identity": "session-1", "config_fingerprint": "config-1",
                "scope": kwargs["scope"], "skill_sha256": request["skill_sha256"], "body_sha256": request["body_sha256"]})
            context = {"context_id": "ctx-1", "epoch": 1, "presentation": presentation}
            invocation = agent_orchestration.invocation_context(policy={"activity_matrix": {"plan": {"required": []}}},
                policy_sha256="a" * 64, context=context, step_id="plan", canonical_entrypoint={"kind": "canonical"},
                supplement={"path": "supplement", "sha256": "b" * 64}, task_template={"path": "template", "sha256": "c" * 64})
            self.assertEqual(invocation["presentation"], presentation)
            self.assertEqual(presentation["scope"]["kind"], "gwd")

    def test_cleanup_lifecycle(self):
        run = {
            "admission": {"activation_sha256": "a" * 64, "work_item_sha256": "b" * 64,
                          "workflow_sha256": "c" * 64, "config_sha256": "d" * 64,
                          "base_commit": "e" * 40},
            "state": "COMPLETE",
            "workers": {"T006": {"state": "CLEANED", "node_id": "T006", "remediates": None,
                                    "workspace": {"converged": True}}},
        }
        self.assertTrue(gauntlet_runs._node_ready(run, "T006"))
        self.assertTrue(gauntlet_runs._converged_lineage_head(run, "T006"))
        with mock.patch.object(gauntlet_runs, "_require_base_commit"), mock.patch.object(
            gauntlet_runs, "_read_runs", return_value={"run-cleanup": run}
        ):
            self.assertIs(gauntlet_runs._run_for_worker(
                ".", "work", "run-cleanup", run["admission"], purpose="cleanup"
            ), run)

    def test_cleanup_public_selectors_preserve_unproven_sessions(self):
        temporary, root = self.fixture()
        with temporary:
            activity, _, _, observed, _, _ = self.accepted_specialist("author-cleanup")
            resource_id, resource = agent_orchestration.session_resource(
                activity, observed, collected_at="2026-01-01T00:00:00Z")
            context = {"context_id": "ctx-1", "epoch": 1, "state": "ACTIVE", "scheduler_runs": {},
                       "leader": {"state": "ACTIVE", "session_ref": "session-1"}}
            item = {"current_context_id": "ctx-1", "contexts": {"ctx-1": context},
                    "activities": {"author-cleanup": activity}, "resources": {resource_id: resource}}
            snapshot = SimpleNamespace(document={"agent_orchestration": {"work_items": {"wx": item}}})
            args = ("gauntlet-cleanup", str(root), "--work-id", "wx", "--context-id", "ctx-1",
                    "--epoch", "1", "--session-ref", "session-1")
            with mock.patch.object(grill_workspace.grill_core_module("gauntlet_runs").store, "read_snapshot", return_value=snapshot), \
                 mock.patch.object(grill_workspace.grill_core_module("gauntlet_runs"), "cleanup_worker") as cleanup:
                for selector in ((), ("--activity-id", "author-cleanup")):
                    code, payload = self.run_cli(*args, *selector)
                    self.assertEqual((code, payload["verdict"]), (2, "UNKNOWN"), payload)
                    self.assertEqual(payload["resources"][0]["code"], "SESSION-CLOSE-UNPROVEN")
                for selector, expected in (
                        (("--activity-id", "missing"), "RESOURCE-IDENTITY-DIVERGENT"),
                        (("--activity-id", "author-cleanup", "--run-id", "run-1"), "INVALID-ARGUMENTS"),
                        (("--worker-id", "worker-1"), "INVALID-ARGUMENTS"),
                        (("--epoch", "2"), "LEADER-AUTHORITY-UNPROVEN")):
                    code, payload = self.run_cli(*args, *selector)
                    self.assertEqual((code, payload["code"]), (2, expected))
                cleanup.assert_not_called()
                resource.update(state="CLOSED", result_acceptance_ref=activity["acceptance_ref"])
                self.assertEqual(self.run_cli(*args, "--activity-id", "author-cleanup")[0], 0)
                runs = grill_workspace.grill_core_module("gauntlet_runs")
                cleanup.side_effect = [{"verdict": "PRESERVED", "worker_id": "w1"},
                                       {"verdict": "CLEANED", "worker_id": "w2"}]
                with mock.patch.object(grill_workspace, "gauntlet_run_admission", return_value=(root, runs, {}, {})), \
                     mock.patch.object(runs, "_run_for_worker", return_value={"workers": {"w1": {}, "w2": {}}}):
                    code, payload = self.run_cli(*args, "--run-id", "run-1")
                    self.assertEqual((code, payload["verdict"], len(payload["resources"])), (2, "PRESERVED", 2))
                    self.assertEqual(cleanup.call_count, 2)

    def test_cleanup_candidate_guard_and_resources_retained_elsewhere(self):
        """T032/T031/FR-010/FR-011: the `candidates` guard of gauntlet-cleanup,
        both sides, plus the successor case it used to deadlock.

        R3-4 verified by execution that replacing the guard with `pass` left the
        whole suite green: the only RESOURCE-IDENTITY-DIVERGENT exercised today
        goes through --activity-id and is refused much earlier, by the activity
        ownership check, so it never reaches the counter. Both sides matter --
        without the zero-candidate case the guard could be widened back to
        `selected and not results` without failing anything.

        The third case is R3-3: a resource pinned by a *superseded* predecessor
        is not a candidate of this selection at all. Counting it made the
        successor's own cleanup refuse forever (T026 leaves no verb to reconcile
        it). It must be reported in `retained` and drop the verdict, never
        refuse the operation.
        """
        temporary, root = self.fixture()

        def resource(origin, activity_id, state="REGISTERED"):
            return {"kind": "session", "activity_id": activity_id, "origin_context_id": origin,
                    "identity": {"handle": "term-1"}, "state": state, "result_acceptance_ref": None}

        def payload_for(resources, *selector, activities=None):
            context = {"context_id": "ctx-1", "epoch": 1, "state": "ACTIVE", "scheduler_runs": {},
                       "leader": {"state": "ACTIVE", "session_ref": "session-1"}}
            item = {"current_context_id": "ctx-1", "contexts": {"ctx-1": context},
                    "activities": activities or {}, "resources": resources}
            snapshot = SimpleNamespace(document={"agent_orchestration": {"work_items": {"wx": item}}})
            with mock.patch.object(grill_workspace.grill_core_module("gauntlet_runs").store,
                                   "read_snapshot", return_value=snapshot):
                return self.run_cli("gauntlet-cleanup", str(root), "--work-id", "wx", "--context-id", "ctx-1",
                                    "--epoch", "1", "--session-ref", "session-1", *selector)

        with temporary:
            # (1) Candidates exist and the selection reaches none of them: this
            # context owns the resource, so it is counted, but it carries no
            # activity_id and the filter skips it. Falling through to CLEANED
            # would tell the caller a resource still open in the store had been
            # closed.
            code, refused = payload_for({"resource-orphan": resource("ctx-1", None)})
            self.assertEqual((code, refused.get("code")), (2, "RESOURCE-IDENTITY-DIVERGENT"), refused)
            # (2) No candidate at all: cleaning a context that owns nothing is a
            # legitimate no-op, and the verdict stays a success.
            code, empty = payload_for({})
            self.assertEqual((code, empty["verdict"], empty["resources"], empty["retained"]), (0, "CLEANED", [], []))
            # (3) R3-3: the successor of a takeover owns nothing; the open
            # resource belongs to the SUPERSEDED predecessor and can never be
            # closed from here. It is reported, not counted -- so no refusal --
            # and the verdict stops being CLEANED.
            code, retained = payload_for({"resource-predecessor": resource("ctx-old", "activity-1")})
            self.assertEqual((code, retained["verdict"]), (2, "PRESERVED"), retained)
            self.assertNotIn("code", retained)
            self.assertEqual(retained["resources"], [])
            self.assertEqual(retained["retained"], [{"resource_id": "resource-predecessor", "kind": "session",
                                                     "state": "REGISTERED", "origin_context_id": "ctx-old",
                                                     "code": "RESOURCE-RETAINED-ELSEWHERE"}])
            # A predecessor resource already CLOSED is nothing to report, so it
            # must not drag the verdict down either.
            code, settled = payload_for({"resource-predecessor": resource("ctx-old", "activity-1", state="CLOSED")})
            self.assertEqual((code, settled["verdict"], settled["retained"]), (0, "CLEANED", []), settled)
            # (4) R4-1/T034: the same report, now scoped to the selector. A
            # cleanup aimed at ONE activity must not be dragged down by a
            # predecessor resource belonging to another activity -- that
            # selection was never meant to reach it, and the downgrade would be
            # permanent (T026 leaves no verb to reconcile a predecessor's
            # resource). Verified by reversion: collecting before the selector
            # discrimination turns this into PRESERVED/exit 2.
            mine = {"activity-mine": {"context_id": "ctx-1"}}
            owned = resource("ctx-1", "activity-mine", state="CLOSED")
            owned["result_acceptance_ref"] = "receipts/acceptance"
            code, scoped = payload_for(
                {"resource-mine": owned, "resource-predecessor": resource("ctx-old", "activity-other")},
                "--activity-id", "activity-mine", activities=mine)
            self.assertEqual((code, scoped["verdict"], scoped["retained"]), (0, "CLEANED", []), scoped)
            self.assertEqual([entry["resource_id"] for entry in scoped["resources"]], ["resource-mine"])
            # (5) and the scoping is a filter, not a mute: a predecessor
            # resource the selection DOES reach is still reported, and still
            # drops the verdict.
            code, in_scope = payload_for(
                {"resource-mine": owned, "resource-predecessor": resource("ctx-old", "activity-mine")},
                "--activity-id", "activity-mine", activities=mine)
            self.assertEqual((code, in_scope["verdict"]), (2, "PRESERVED"), in_scope)
            self.assertEqual([entry["resource_id"] for entry in in_scope["retained"]], ["resource-predecessor"])

    def test_failed_or_unproven_cleaned_worker_never_unblocks_dependency(self):
        for state, converged in (("FAILED", True), ("CLEANED", False)):
            with self.subTest(state=state, converged=converged):
                run = {"workers": {"T006": {"state": state, "node_id": "T006", "remediates": None,
                                                "workspace": {"converged": converged}}}}
                self.assertFalse(gauntlet_runs._node_ready(run, "T006"))
                self.assertFalse(gauntlet_runs._converged_lineage_head(run, "T006"))

    def test_resource_cleanup_requires_current_facts(self):
        resource = {"kind": "branch", "result_acceptance_ref": "receipt"}
        reasons = agent_orchestration.cleanup_reasons(resource, {
            "session": "closed", "identity": True, "integrated": True,
            "clean": True, "ignored": False, "exclusive_evidence": False,
            "branch_in_use": False, "ref_matches": True,
        })
        self.assertEqual(reasons, ())
        self.assertIn("REF_CHANGED", agent_orchestration.cleanup_reasons(resource, {
            "session": "closed", "identity": True, "integrated": True,
            "clean": True, "ref_matches": False,
        }))

    def run_cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = grill_workspace.main(list(argv))
        return code, json.loads(output.getvalue())

    def fixture(self):
        temp = tempfile.TemporaryDirectory(); root = Path(temp.name).resolve()
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
                 mock.patch.object(dependencies.Toolchain, "run", sentinel_probe), \
                 orchestration_fixture.offline_leader(grill_workspace):
                self.assertEqual(self.run_cli("init", str(root), "--type", "feature", "--slug", "x", "--work-id", "work-x", "--runtime", "codex", "--skip-backlog")[0], 2)
                self.assertFalse((root / ".grill").exists())
                code, init = self.run_cli("init", str(root), "--type", "feature", "--slug", "x", "--work-id", "work-x", "--runtime", "codex", "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
                self.assertEqual(code, 0); self.assertEqual(init["orchestration"], "INITIALIZED")
                before = store.read_snapshot(root).content_sha256
                args = ("gauntlet-orchestration-adopt", str(root), "--work-id", "work-x", "--runtime", "codex", "--session-ref", orchestration_fixture.SESSION, "--scope-file", "src/a.py")
                code, preview = self.run_cli(*args); self.assertEqual(code, 0); self.assertEqual(preview["verdict"], "PREVIEW")
                self.assertEqual(store.read_snapshot(root).content_sha256, before)
                self.assertEqual(self.run_cli(*args, "--apply")[0], 2)
                code, adopted = self.run_cli(*args, "--apply", "--expected-sha256", preview["expected_sha256"])
                self.assertEqual(code, 0); self.assertEqual(adopted["verdict"], "ORCHESTRATION-ADOPTED")
                self.assertEqual(self.run_cli(*args, "--apply", "--expected-sha256", preview["expected_sha256"])[1]["verdict"], "REUSED")
                document = store.read_snapshot(root).document
                context = document["agent_orchestration"]["work_items"]["work-x"]["contexts"][adopted["context_id"]]
                self.assertIsNone(context["activation"]); self.assertIsNone(context["campaign"]); self.assertEqual(context["scheduler_runs"], {})
                code, entered = self.run_cli(
                    "gauntlet-step-enter", str(root), "--work-id", "work-x", "--context-id", adopted["context_id"],
                    "--epoch", "1", "--session-ref", orchestration_fixture.SESSION, "--step", "implement-parallel")
                self.assertEqual(code, 0)
                changed_origin = {**preview["origin"], "state_sha256": "f" * 64}
                with mock.patch.object(grill_workspace, "_orchestration_origin", return_value=changed_origin):
                    code, refresh = self.run_cli(*args)
                    self.assertEqual(code, 0, refresh)
                    code, refreshed = self.run_cli(*args, "--apply", "--expected-sha256", refresh["expected_sha256"])
                    self.assertEqual((code, refreshed["context_id"]), (0, adopted["context_id"]))
                invocation = entered["invocation_context"]
                self.assertEqual(invocation["canonical_entrypoint"]["entrypoint"], "grill-with-docs:grill-implement-parallel")
                for key, path in (("supplement", "references/agent-orchestration.md"),
                                  ("task_template", "assets/task-files.v1.template.md")):
                    body = (SCRIPTS.parent / path).read_bytes()
                    self.assertEqual(invocation[key], {
                        "path": f"plugin/skills/grill-with-docs/{path}",
                        "sha256": __import__("hashlib").sha256(body).hexdigest(),
                    })
                checkpoint_args = ("checkpoint", str(root), "--work-id", "work-x", "--step", "specify", "--state", "in-progress", "--operation-id", "checkpoint-1", "--session-ref", orchestration_fixture.SESSION)
                code, checkpoint = self.run_cli(*checkpoint_args)
                self.assertEqual((code, checkpoint["code"]), (2, "ACTIVITY-REQUIRED"))
                stale = self.run_cli(*args, "--scope-file", "src/b.py", "--apply", "--expected-sha256", preview["expected_sha256"])
                self.assertEqual(stale[0], 2)
            self.assertTrue(probes); self.assertTrue(commands)
            self.assertTrue(all(argv[0].startswith("/offline/") for argv in commands))

    def test_bootstrap_reuse_waits_for_the_journal_snapshot_commit(self):
        temp, root = self.fixture()
        with temp:
            store.bootstrap(root)
            writing, waiting, release = threading.Event(), threading.Event(), threading.Event()
            write, lock = store._write_document, store.orchestrator_lock
            def paused_write(*args):
                writing.set()
                self.assertTrue(release.wait(5))
                return write(*args)
            @contextlib.contextmanager
            def observed_lock(*args, **kwargs):
                if writing.is_set():
                    waiting.set()
                with lock(*args, **kwargs) as held:
                    yield held
            with mock.patch.object(store, "_write_document", side_effect=paused_write), \
                    mock.patch.object(store, "orchestrator_lock", side_effect=observed_lock), \
                    concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                writer = pool.submit(store.transact, root, lambda document: document)
                self.assertTrue(writing.wait(5))
                reuse = pool.submit(store.bootstrap, root)
                try:
                    self.assertTrue(waiting.wait(3), "bootstrap read the intermediate journal without waiting")
                    self.assertFalse(reuse.done())
                finally:
                    release.set()
                writer.result(timeout=5)
                self.assertEqual(reuse.result(timeout=5)["verdict"], "REUSED")

    def test_adopted_direct_effect_requires_the_current_context_proof(self):
        temp, root = self.fixture()
        with temp:
            store.bootstrap(root)
            origin = {"state_sha256": "1" * 64, "metadata_sha256": "2" * 64, "activation": None,
                      "campaign": None, "lifecycle": "ACTIVE", "worktree": {"root": str(root), "branch": "main"}}
            contract = grill_workspace.grill_core_module("agent_orchestration")
            readiness = self.readiness()
            inputs = contract.adoption_inputs(
                work_id="work-x", runtime="codex", session_ref="session-1",
                session_observation={key: readiness[key] for key in ("ref", "sha256", "incarnation")},
                presentation=readiness["presentation"], scope_files=[], origin=origin)
            item = contract.new_work_item(inputs, policy_ref="policy/v1", policy_sha256="a" * 64,
                                          adopted_at="2026-01-01T00:00:00Z", context_id="ctx-1")
            store.transact(root, lambda document: {**document, "agent_orchestration": {"schema": contract.SCHEMA, "work_items": {"work-x": item}}})
            with self.assertRaises(store.StoreError):
                store.require_orchestration_authority(root, "work-x", purpose="prepare")
            with store.orchestration_authority(root, "work-x", context_id="ctx-1", epoch=1, session_ref="session-1"):
                with self.assertRaises(store.StoreError):
                    store.require_orchestration_authority(root, "work-x", purpose="prepare")
            with store.orchestration_authority(root, "work-x", context_id="ctx-1", epoch=1, session_ref="session-1",
                                               observed_context=item["contexts"]["ctx-1"]):
                store.require_orchestration_authority(root, "work-x", purpose="prepare")
                def change_config(document):
                    document["agent_orchestration"]["work_items"]["work-x"]["contexts"]["ctx-1"]["presentation"]["config_fingerprint"] = "new-config"
                    return document
                store.transact(root, change_config)
                with self.assertRaisesRegex(store.StoreError, "entry observation changed"):
                    store.require_orchestration_authority(root, "work-x", purpose="prepare")
                with self.assertRaisesRegex(store.StoreError, "entry observation changed"):
                    store.transact(root, lambda document: document)

    def test_runtime_continuity(self):
        """A switch preserves logical work and refuses activity inferred from silence."""
        policy = json.loads((SCRIPTS.parent / "assets/agent-orchestration.v1.json").read_text(encoding="utf-8"))
        for runtime, expected in (("codex", "Sol"), ("claude", "Opus")):
            with self.subTest(runtime=runtime):
                self.assertEqual(agent_orchestration.coordinator_recommendation(policy, runtime), expected)
                response = grill_workspace._with_coordinator_response({"active_model": None}, runtime)
                self.assertEqual(response, {"active_model": None, "coordinator_recommendation": expected,
                                            "active_model_changed": False})
        self.assertEqual(agent_orchestration.specialist_pair("codex", "author"), ("gpt-6-astra", "xhigh"))
        self.assertEqual(agent_orchestration.specialist_pair("claude", "reviewer"), ("fable", "high"))
        old = {"project_id": "sha256:" + "1" * 64, "run_id": "leader-work-x", "runtime": "codex",
               "adapter": "codex", "registry_sha256": "sha256:" + "2" * 64,
               "recovery_generation_id": "rg-" + "3" * 64, "plan_revision": 7}
        successor = agent_orchestration.successor_campaign(old, runtime="claude", adapter="claude",
            registry_sha256=old["registry_sha256"], bridge_seed={"checkpoint": "cp-1", "context": "ctx-1"})
        bridge = agent_orchestration.campaign_bridge(old, successor,
            accepted_outputs={"specify": {"receipt_ref": "r", "output_sha256": "sha256:" + "4" * 64}},
            worktree_identity={"project_id": old["project_id"], "work_id": "work-x", "phase": "specify",
                                "du": "work-item", "git_common_dir": "/repo/.git", "real_path": "/repo",
                                "branch": "main"})
        self.assertEqual((successor["project_id"], successor["run_id"], successor["plan_revision"]),
                         (old["project_id"], old["run_id"], old["plan_revision"]))
        self.assertNotEqual(successor["recovery_generation_id"], old["recovery_generation_id"])
        self.assertEqual(bridge["from_campaign"], old)
        item = {"operations": {"switch-1": {"intended_after": {"campaign_bridge": bridge}}}}
        context = {"campaign": successor, "continuity_ref": "switch-1"}
        state = {"development": {"attestation_campaign": copy.deepcopy(old)}}
        self.assertEqual(grill_workspace._checkpoint_campaign(item, context, state, "work-x"), successor)
        self.assertEqual(state["development"]["attestation_campaign"], successor)
        final = agent_orchestration.successor_campaign(successor, runtime="codex", adapter="codex",
            registry_sha256=successor["registry_sha256"], bridge_seed={"checkpoint": "cp-2", "context": "ctx-2"})
        second_bridge = agent_orchestration.campaign_bridge(successor, final,
            accepted_outputs={}, worktree_identity={})
        multi_item = {"operations": {
            "switch-1": {"intended_after": {"campaign_bridge": bridge}},
            "switch-2": {"intended_after": {"campaign_bridge": second_bridge}},
        }, "contexts": {
            "ctx-2": {"campaign": successor, "continuity_ref": "switch-1"},
        }}
        multi_context = {"campaign": final, "continuity_ref": "switch-2", "predecessor_context_id": "ctx-2"}
        multi_state = {"development": {"attestation_campaign": copy.deepcopy(old)}}
        self.assertEqual(grill_workspace._checkpoint_campaign(multi_item, multi_context, multi_state, "work-x"), final)
        self.assertEqual(multi_state["development"]["attestation_campaign"], final)
        broken = copy.deepcopy(item)
        broken["operations"]["switch-1"]["intended_after"]["campaign_bridge"]["from_campaign"] = successor
        with self.assertRaisesRegex(grill_workspace.CliFailure, "CHECKPOINT-CAMPAIGN-DIVERGENT"):
            grill_workspace._checkpoint_campaign(broken, context,
                {"development": {"attestation_campaign": old}}, "work-x")
        bad = copy.deepcopy(successor); bad["plan_revision"] += 1
        with self.assertRaises(agent_orchestration.OrchestrationError):
            agent_orchestration.campaign_bridge(old, bad, accepted_outputs={}, worktree_identity={})
        active, unknown = grill_workspace._continuity_quiescence(
            {"work_items": {"work-x": {"gauntlet": {"runs": {"run-1": {"workers": {
                "w": {"state": "PREPARED", "lease": {"expires_at": "2000-01-01T00:00:00Z"}}}}}}}}},
            {"activities": {}, "resources": {}}, "work-x")
        self.assertEqual(active, ["worker:run-1:w"]); self.assertEqual(unknown, [])
        active, unknown = grill_workspace._continuity_quiescence(
            {"work_items": {"work-x": {"gauntlet": {"runs": {"run-1": {"workers": {"w": {"state": "ORPHANED"}}}}}}}},
            {"activities": {}, "resources": {}}, "work-x")
        self.assertEqual(active, []); self.assertEqual(unknown, ["worker:run-1:w"])

        physical = {"provider": "codex", "adapter": "orca", "host": "local", "runtime_instance": "runtime-1",
                    "handle": "term-1", "incarnation": "inc-1", "dispatch_incarnation": "process-1",
                    "worktree_id": "worktree-1"}
        transferred = {"activities": {
            "review-1": {"state": "DISPATCHED", "session_resource_id": "session-1", "context_id": "ctx-1",
                         "activity_type": "reviewer", "step_id": "checklist", "author_activity_ids": ["author-1"]},
            "review-2": {"state": "ACCEPTED", "session_resource_id": "session-2", "context_id": "ctx-1",
                         "activity_type": "reviewer", "step_id": "checklist", "author_activity_ids": ["author-1"],
                         "acceptance_ref": "results/review-2.md"},
        }, "resources": {
            "session-1": {"kind": "session", "state": "REGISTERED", "activity_id": "review-1",
                          "identity": {**physical, "owner_dispatch": "ctx-old", "task_id": "task-old"},
                          "creation_observation": {"collected_at": "2026-01-01T00:00:00Z"}},
            "session-2": {"kind": "session", "state": "CLOSED", "activity_id": "review-2",
                          "identity": {**physical, "owner_dispatch": "ctx-new", "task_id": "task-new"},
                          "creation_observation": {"collected_at": "2026-01-01T00:01:00Z"},
                          "result_acceptance_ref": "results/review-2.md", "last_observation": "orca:ctx-new:closed",
                          "evidence_manifest": {"receipts": [
                              {"ref": "orca:ctx-new:closed", "sha256": "a" * 64}]}}
        }}
        self.assertEqual(grill_workspace._transferred_activity_sessions(transferred), {
            "review-1": ("session-1", "review-2", {"ref": "orca:ctx-new:closed", "sha256": "a" * 64})})
        transferred["activities"]["review-3"] = copy.deepcopy(transferred["activities"]["review-2"])
        transferred["activities"]["review-3"]["session_resource_id"] = "session-3"
        transferred["resources"]["session-3"] = copy.deepcopy(transferred["resources"]["session-2"])
        transferred["resources"]["session-3"]["activity_id"] = "review-3"
        transferred["resources"]["session-3"]["identity"]["owner_dispatch"] = "ctx-third"
        self.assertEqual(grill_workspace._transferred_activity_sessions(transferred), {})

    def test_prepare_switch_recovers_an_exact_released_source(self):
        import validate_orchestrator_store_contract as seed
        core = grill_workspace.grill_core_module("agent_runtime")
        temporary, root = self.fixture()
        with temporary, orchestration_fixture.offline_leader(grill_workspace):
            code, payload = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                "--work-id", "work-x", "--runtime", "codex", "--session-ref",
                orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, payload)
            snapshot = store.read_snapshot(root)
            item = snapshot.document["agent_orchestration"]["work_items"]["work-x"]
            context_id = item["current_context_id"]
            checkpoint = seed.ORCHESTRATION_CHECKPOINT()
            checkpoint["context_id"] = context_id
            checkpoint["checkpoint_sha256"] = store.jcs_sha256(
                {key: value for key, value in checkpoint.items() if key != "checkpoint_sha256"})
            def add_checkpoint(document):
                target = document["agent_orchestration"]["work_items"]["work-x"]
                target["checkpoints"] = {"checkpoint-1": copy.deepcopy(checkpoint)}
                target["checkpoint_head"] = "checkpoint-1"
                return document
            store.transact(root, add_checkpoint)
            adapter, show, _ = orchestration_fixture.boundary(
                grill_workspace, root, "codex", orchestration_fixture.SESSION, "work-x")
            result = show["result"]
            for launch in (result["worker"]["startOptions"]["launch"]["requested"],
                           result["worker"]["startOptions"]["launch"]["effective"]):
                launch.update(model="gpt-6-astra", effort="xhigh")
            manifest = {"files": [], "required_activity_ids": [], "author_activity_ids": [],
                        "task_binding": None, "human_authorization": None}
            activity = agent_orchestration.new_activity(activity_id="orphan-author", context_id=context_id,
                step_id="specify", activity_scope="cycle", activity_type="author", attempt=1,
                input_manifest=manifest, policy_sha256=item["policy_sha256"], write_files=[])
            activity = agent_orchestration.prepare_activity(activity, item["contexts"][context_id])
            observed = adapter.observe()
            observed["resolved_model_id"] = "gpt-6-astra"
            activity = agent_orchestration.record_verified_activity(activity, observed)
            resource_id, resource = agent_orchestration.session_resource(
                activity, observed, collected_at="2026-01-01T00:00:00Z")
            activity, _ = agent_orchestration.dispatch_activity(activity, item["contexts"][context_id])
            activity = agent_orchestration.record_activity_result(activity, result_ref="results/orphan.md",
                result_sha256="b" * 64, output_manifest={"files": [],
                    "return_ref": {"ref": "results/orphan.md", "sha256": "b" * 64}, "effect_ref": None})
            resource["state"] = "CLOSE_PENDING"
            def add_pending_activity(document):
                target = document["agent_orchestration"]["work_items"]["work-x"]
                target["activities"][activity["activity_id"]] = copy.deepcopy(activity)
                target["resources"][resource_id] = copy.deepcopy(resource)
                return document
            store.transact(root, add_pending_activity)
            result["dispatch"].update(status="completed", capabilityRevokedAt="2026-01-01T00:00:00Z",
                                      completedAt="2026-01-01T00:00:00Z")
            result["worker"].update(state="succeeded", stage="settled")
            result["terminal"].update(connected=False, writable=False)
            result["terminalResource"].update(ownershipState="released", releaseState="released",
                originDispatchId="ctx-fixture", releaseCompletedAt="2026-01-01T00:00:01Z",
                releaseError=None, archive={"source": "transcript", "status": "captured"})
            result["projection"].update(outcome="succeeded",
                workspace={"id": "worktree-fixture"},
                liveness={"verdict": "exited", "source": "resource_release"},
                resource={"state": "released", "releaseState": "released", "terminalState": "released",
                          "ownerDispatchId": "ctx-fixture"})
            result["observation"]["status"] = "exited"
            result["terminalResource"]["archive"]["status"] = "missing"
            with self.assertRaisesRegex(core.RuntimeError, "LEADER-RELEASE-UNPROVEN"):
                adapter.observe_released()
            result["dispatch"].update(status="failed", lastFailure="stopped")
            result["worker"].update(state="stopped", stage="process_stopped")
            result["projection"]["outcome"] = "failed"
            result["terminalResource"]["archive"] = {"source": None, "status": "unavailable"}
            with self.assertRaisesRegex(core.RuntimeError, "LEADER-RELEASE-UNPROVEN"):
                adapter.observe_released()
            fenced = adapter.observe_released(allow_unarchived_stopped=True)
            self.assertEqual((fenced["outcome"], fenced["release_proof"]), ("failed", "resource-fence"))
            with mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter):
                recovered = grill_workspace._require_released_leader(
                    root, "work-x", item["contexts"][context_id], orchestration_fixture.SESSION)
            self.assertEqual(recovered["release_proof"], "resource-fence")
            result["terminalResource"]["archive"]["status"] = "captured"
            result["terminalResource"]["archive"]["source"] = "transcript"
            result["dispatch"]["status"] = "failed"
            result["worker"]["state"] = result["projection"]["outcome"] = "failed"
            result["worker"]["stage"] = "settled"
            self.assertEqual(adapter.observe_released()["outcome"], "failed")
            result["dispatch"]["status"] = "completed"
            result["worker"]["state"] = result["projection"]["outcome"] = "succeeded"
            argv = ("gauntlet-prepare-switch", str(root), "--work-id", "work-x", "--context-id", context_id,
                    "--epoch", "1", "--session-ref", orchestration_fixture.SESSION,
                    "--to-runtime", "claude", "--released-source")
            with mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter):
                code, quiescing = self.run_cli(*argv)
                self.assertEqual((code, quiescing["verdict"]), (0, "QUIESCING"), quiescing)
                code, prepared = self.run_cli(*argv)
            self.assertEqual((code, prepared["verdict"]), (0, "SWITCH-PREPARED"), prepared)
            saved = store.read_snapshot(root).document["agent_orchestration"]["work_items"]["work-x"]
            self.assertEqual(saved["contexts"][context_id]["state"], "RELEASED")
            self.assertEqual(saved["contexts"][context_id]["leader"]["state"], "RELEASED")
            operation = saved["operations"][prepared["operation_id"]]
            self.assertEqual((operation["state"], operation["observation_ref"]),
                             ("APPLIED", orchestration_fixture.SESSION))
            self.assertEqual(saved["activities"]["orphan-author"]["state"], "ACCEPTED")
            self.assertEqual(saved["resources"][resource_id]["state"], "CLOSED")
            self.assertEqual(grill_workspace._continuity_quiescence(
                store.read_snapshot(root).document, saved, "work-x"), ([], []))

    def test_released_leader_accepts_an_exact_finalized_ownership_transfer(self):
        core = grill_workspace.grill_core_module("agent_runtime")
        temporary, root = self.fixture()
        with temporary, orchestration_fixture.offline_leader(grill_workspace):
            adapter, show, transcript = orchestration_fixture.boundary(
                grill_workspace, root, "codex", orchestration_fixture.SESSION, "work-x")
            result = show["result"]
            result["dispatch"].update(runId="run-1", status="completed",
                                      capabilityRevokedAt="2026-01-01T00:00:00Z",
                                      completedAt="2026-01-01T00:00:00Z")
            result["worker"].update(state="succeeded", stage="settled")
            result["terminal"].update(connected=False, writable=False)
            result["projection"].update(outcome="succeeded", workspace={"id": "worktree-fixture"},
                                        liveness={"verdict": "unverifiable", "reason": "missing_status"},
                                        resource={"state": "absent", "reason": "not_materialized"})
            result["observation"].update(status="exited")
            result["terminalResource"] = None
            released_resource = {
                "ownershipState": "released", "releaseState": "released",
                "originDispatchId": "ctx-fixture", "ownerDispatchId": "ctx-next",
                "terminalHandle": "term-fixture", "worktreeId": "worktree-fixture",
                "endpointId": "runtime-fixture", "endpointIncarnation": "pty-fixture:inc-fixture",
                "releaseCompletedAt": "2026-01-01T00:00:01Z", "releaseError": None,
                "archive": {"source": "transcript", "status": "captured"},
            }
            fleet = {"ok": True, "result": {"workers": [{
                "dispatchId": "ctx-next", "agentTerminalHandle": "term-fixture",
                "workerState": "failed", "dispatchStatus": "failed", "terminalState": "released",
                "resource": released_resource,
                "projection": {"liveness": {"verdict": "exited", "source": "resource_release"},
                               "resource": {"state": "released"}},
            }], "page": {"hasMore": False}}}
            adapter.read = lambda argv: orchestration_fixture.pack(
                show if argv[1] == "worker-show" else fleet if argv[1] == "worker-list" else transcript)
            with self.assertRaisesRegex(core.RuntimeError, "terminal resource"):
                adapter.observe_released()
            recovered = adapter.observe_released(allow_unarchived_stopped=True)
            self.assertEqual((recovered["outcome"], recovered["release_proof"]),
                             ("succeeded", "ownership-transfer"))
            released_resource["archive"]["status"] = "missing"
            with self.assertRaisesRegex(core.RuntimeError, "LEADER-RELEASE-UNPROVEN"):
                adapter.observe_released(allow_unarchived_stopped=True)

    def test_public_continuity_resume_observes_destination_before_commit(self):
        import validate_orchestrator_store_contract as seed
        store = grill_workspace.grill_core_module("store")
        core = grill_workspace.grill_core_module("agent_runtime")
        for source_runtime, runtime in (("codex", "claude"), ("claude", "codex")):
            temporary, root = self.fixture()
            with temporary, self.subTest(runtime=runtime), orchestration_fixture.offline_leader(grill_workspace):
                with mock.patch.object(grill_workspace, "_initialize_orchestration", return_value={}):
                    code, payload = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                        "--work-id", "work-x", "--runtime", source_runtime,
                        "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
                self.assertEqual(code, 0, payload)
                state = grill_workspace.read_development_state(root,
                    grill_workspace.resolve_development_item(root, "work-x"), "work-x")[1]
                identity = grill_workspace._continuity_identity(root, "work-x", state)
                context = seed.ORCHESTRATION_CONTEXT(state="RELEASED", leader_state="RELEASED")
                context.update(runtime=source_runtime, adapter=source_runtime, worktree_identity=identity)
                checkpoint = seed.ORCHESTRATION_CHECKPOINT()
                checkpoint.update(worktree_identity=identity, accepted_outputs={"specify": {"output_sha256": "a" * 64}})
                checkpoint["checkpoint_sha256"] = store.jcs_sha256({k: v for k, v in checkpoint.items() if k != "checkpoint_sha256"})
                operation = seed.ORCHESTRATION_OPERATION()
                operation.update(kind="continuity-switch", state="APPLIED", expected_before={"checkpoint_id": "checkpoint-1"},
                                 intended_after={"to_runtime": runtime, "campaign_bridge": None})
                item = seed.ORCHESTRATION_ITEM({"ctx-1": context}, {"op-1": operation})
                item["policy_ref"] = "assets/agent-orchestration.v1.json"
                item["policy_sha256"] = context["policy_sha256"] = grill_workspace.hash_bytes(
                    (grill_workspace.ASSETS / "agent-orchestration.v1.json").read_bytes())
                item.update(checkpoints={"checkpoint-1": checkpoint}, checkpoint_head="checkpoint-1")
                store.bootstrap(root)
                store.transact(root, lambda doc: {**doc, "agent_orchestration": {
                    "schema": "grill-agent-orchestration/v1", "work_items": {"work-x": item}}})
                session = "orca:ctx-destination"
                argv = ("gauntlet-resume", str(root), "--work-id", "work-x", "--checkpoint", "checkpoint-1",
                        "--runtime", runtime, "--session-ref", session)
                adapter, show, transcript = orchestration_fixture.boundary(grill_workspace, root, runtime, session, "work-x")
                request_call = transcript["result"]["transcript"]["messages"][0]["blocks"][0]
                request_call["input"] = {"command" if runtime == "claude" else "cmd": shlex.join(
                    [sys.executable, "-B", str(SCRIPTS / "grill_workspace.py"), *argv])}
                def durable():
                    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
                before = durable()
                with mock.patch.object(grill_workspace, "_continuity_effective_activation",
                        return_value={"runtime": {"id": runtime, "adapter": runtime}}), \
                     mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter) as observe:
                    code, preview = self.run_cli(*argv)
                    self.assertEqual(code, 0, preview)
                    self.assertEqual(durable(), before)
                    for container, key, value, expected in (
                        (show["result"]["terminal"], "handle", "wrong-terminal", "LEADER-AUTHORITY-UNPROVEN"),
                        (show["result"]["terminal"], "agentIdentity", source_runtime, "LEADER-AUTHORITY-UNPROVEN"),
                        (show["result"]["terminal"], "worktreePath", "/other", "LEADER-AUTHORITY-UNPROVEN"),
                        (show["result"]["dispatch"], "capabilityRevokedAt", "revoked", "LEADER-AUTHORITY-UNPROVEN"),
                        (transcript["result"], "contentComplete", False, "LEADER-TRANSCRIPT-UNPROVEN"),
                        (transcript["result"]["transcript"]["messages"][3]["blocks"][0], "output", "",
                         "STYLE-LOAD-UNCONFIRMED"),
                        (request_call, "input", {"command" if runtime == "claude" else "cmd": shlex.join(
                            [sys.executable, "-B", str(SCRIPTS / "grill_workspace.py"), *argv, "--run-id", "r"])},
                         "STYLE-LOAD-UNCONFIRMED"),
                    ):
                        original = container[key]
                        container[key] = value
                        for tail in ((), ("--apply", "--expected-sha256", preview["expected_sha256"])):
                            code, blocked = self.run_cli(*argv, *tail)
                            self.assertEqual((code, blocked.get("code")), (2, expected), blocked)
                            self.assertEqual(durable(), before)
                        container[key] = original
                    with mock.patch.object(adapter, "read", side_effect=core.RuntimeError("LEADER-ADAPTER-UNAVAILABLE")):
                        code, blocked = self.run_cli(*argv, "--apply", "--expected-sha256", preview["expected_sha256"])
                    self.assertEqual((code, blocked.get("code")), (2, "LEADER-ADAPTER-UNAVAILABLE"), blocked)
                    self.assertEqual(durable(), before)
                    with mock.patch.object(adapter, "session_ref", "arbitrary-caller-session"):
                        code, blocked = self.run_cli(*argv, "--apply", "--expected-sha256", preview["expected_sha256"])
                    self.assertEqual((code, blocked.get("code")), (2, "LEADER-ADAPTER-UNSUPPORTED"), blocked)
                    self.assertEqual(durable(), before)
                    # Another valid native task changes the observed identity; the old preview cannot authorize it.
                    for container in (show["result"]["dispatch"], show["result"]["projection"]):
                        container["taskId"] = "task-successor"
                    request_result = transcript["result"]["transcript"]["messages"][1]["blocks"][0]
                    original_result = request_result["output"]
                    request = json.loads(original_result)
                    request["presentation"]["load_request"]["session_identity"] = core.leader_session_identity(adapter.observe())
                    request_result["output"] = json.dumps(request)
                    code, blocked = self.run_cli(*argv, "--apply", "--expected-sha256", preview["expected_sha256"])
                    self.assertEqual((code, blocked.get("code")), (2, "ORCHESTRATION-POLICY-STALE"), blocked)
                    self.assertEqual(durable(), before)
                    for container in (show["result"]["dispatch"], show["result"]["projection"]):
                        container["taskId"] = "task-fixture"
                    request_result["output"] = original_result
                    # A Store update after observation must fail CAS before promotion.
                    real_transact = store.transact
                    concurrent = None
                    def race(write_root, mutate):
                        nonlocal concurrent
                        real_transact(write_root, lambda document: document)
                        concurrent = durable()
                        return real_transact(write_root, mutate)
                    with mock.patch.object(store, "transact", side_effect=race):
                        code, blocked = self.run_cli(*argv, "--apply", "--expected-sha256", preview["expected_sha256"])
                    self.assertEqual((code, blocked.get("code")), (2, "CONTINUITY-CAS-CONFLICT"), blocked)
                    self.assertEqual(durable(), concurrent)
                    code, preview = self.run_cli(*argv)
                    self.assertEqual(code, 0, preview)
                    code, resumed = self.run_cli(*argv, "--apply", "--expected-sha256", preview["expected_sha256"])
                    self.assertEqual((code, resumed.get("verdict")), (0, "RESUMED"), resumed)
                    self.assertGreater(observe.call_count, 2)
                    saved = store.read_snapshot(root).document["agent_orchestration"]["work_items"]["work-x"]
                    destination = saved["contexts"][saved["current_context_id"]]
                    observed = adapter.observe()
                    self.assertEqual(saved["contexts"]["ctx-1"]["state"], "SUPERSEDED")
                    self.assertEqual(destination["leader"]["incarnation"], observed["incarnation"])
                    self.assertEqual(destination["leader"]["observation_ref"], session)
                    self.assertEqual(destination["leader"]["observation_sha256"], observed["source_sha256"])
                    self.assertEqual(destination["presentation"], preview["presentation"])
                    self.assertEqual(resumed["presentation"], destination["presentation"])
                    self.assertEqual(saved["checkpoints"]["checkpoint-1"], checkpoint)
                    code, entered = self.run_cli("gauntlet-step-enter", str(root), "--work-id", "work-x",
                        "--context-id", destination["context_id"], "--epoch", "2", "--session-ref", session,
                        "--step", "implement-parallel")
                    self.assertEqual(code, 0, entered)

    def test_continuity_siblings_judge_only_the_structural_tuple(self):
        """T035/R4-3/FR-001/FR-005: `gauntlet-prepare-switch` and
        `gauntlet-resume` judge the sealed stamp on the same structural tuple
        the takeover moved to, not on the whole identity.

        Both sides matter, and neither had a test. `phase` moves with every
        cycle step and `branch` by routine human action, only a successful
        takeover ever rewrites a stamp, and the takeover stamps the phase of
        that instant -- so while the siblings compared every field, the first
        step turn after a takeover made them refuse forever. The block was not
        removed by Phase 9, only deferred. The refusal side is asserted too:
        widening the tuple back out is not the same as deleting the check.
        """
        temp, root = self.fixture()
        with temp, orchestration_fixture.offline_leader(grill_workspace):
            code, created = self.run_cli("init", str(root), "--work-id", "work-sibling", "--type", "feature",
                "--slug", "work-sibling", "--runtime", "codex",
                "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, created)
            seeded = store.read_snapshot(root).document["agent_orchestration"]["work_items"]["work-sibling"]
            sibling_context_id = seeded["current_context_id"]
            switch = ("gauntlet-prepare-switch", str(root), "--work-id", "work-sibling", "--session-ref",
                      orchestration_fixture.SESSION, "--context-id", sibling_context_id, "--epoch", "1",
                      "--to-runtime", "claude")
            code, quiescing = self.run_cli(*switch)
            self.assertEqual((code, quiescing.get("verdict")), (0, "QUIESCING"), quiescing)
            sealed = copy.deepcopy(store.read_snapshot(root).document["agent_orchestration"][
                "work_items"]["work-sibling"]["contexts"][sibling_context_id]["worktree_identity"])
            original_branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                                             check=True, capture_output=True, text=True).stdout.strip()
            # R5-2: teardown, not a protected block. The restoration tolerates
            # failure so it never masks the real assertion (T038), and as a
            # `finally` that meant the cases *after* it could silently derive
            # identity from the test branch. Registered as cleanup it always
            # runs, at the end of the case, with no uncovered window.
            self.addCleanup(subprocess.run, ["git", "-C", str(root), "checkout", "-q", original_branch],
                            check=False)
            subprocess.run(["git", "-C", str(root), "checkout", "-q", "-b", "a-branch-nobody-was-on"], check=True)
            state_path = root / ".grill" / "work-items" / "work-sibling" / "state.json"
            aged = json.loads(state_path.read_text(encoding="utf-8"))
            aged["active_phase"] = "a-later-step"
            state_path.write_text(json.dumps(aged), encoding="utf-8")
            self.assertNotEqual((sealed["phase"], sealed["branch"]),
                                ("a-later-step", "a-branch-nobody-was-on"))
            # The identity check runs before the idempotent reuse of the
            # switch operation, so reaching that verdict at all is the
            # proof: with phase and branch still inside the tuple this is
            # CONTINUITY-STATE-DIVERGENCE, exit 2.
            code, again = self.run_cli(*switch)
            self.assertEqual((code, again.get("verdict")), (0, "SWITCH-PREPARED"), again)
            # The cases below need the original branch back, so the case
            # restores it explicitly and demands success -- no assertion is in
            # flight here, so `check=True` masks nothing. The cleanup above
            # stays as the net for the paths that never reach this line.
            subprocess.run(["git", "-C", str(root), "checkout", "-q", original_branch], check=True)
            # The refusal side: narrowing the tuple is not deleting the check.
            # The sealed stamp is immutable in the Store, so the divergence is
            # produced where production produces it -- on the *live* side, the
            # tree answering from somewhere else.
            real_identity = grill_workspace._continuity_identity

            def moved_tree(*args, **kwargs):
                identity = real_identity(*args, **kwargs)
                return {**identity, "real_path": identity["real_path"] + "-a-tree-that-is-not-this-one"}

            # A fresh item, because the item above already committed its
            # switch: its context is RELEASED and would refuse on authority,
            # well before the identity is ever compared.
            code, created = self.run_cli("init", str(root), "--work-id", "work-sibling-moved", "--type", "feature",
                "--slug", "work-sibling-moved", "--runtime", "codex",
                "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, created)
            moved_context_id = store.read_snapshot(root).document["agent_orchestration"][
                "work_items"]["work-sibling-moved"]["current_context_id"]
            moved_switch = ("gauntlet-prepare-switch", str(root), "--work-id", "work-sibling-moved",
                            "--session-ref", orchestration_fixture.SESSION, "--context-id", moved_context_id,
                            "--epoch", "1", "--to-runtime", "claude")
            code, stamped = self.run_cli(*moved_switch)
            self.assertEqual((code, stamped.get("verdict")), (0, "QUIESCING"), stamped)
            before = store.read_snapshot(root).content_sha256
            with mock.patch.object(grill_workspace, "_continuity_identity", side_effect=moved_tree):
                code, blocked = self.run_cli(*moved_switch)
            self.assertEqual((code, blocked.get("code")), (2, "CONTINUITY-STATE-DIVERGENCE"), blocked)
            self.assertEqual(store.read_snapshot(root).content_sha256, before)

    def test_continuity_resume_judges_only_the_structural_tuple(self):
        """T035, the resume half: the same tuple, on the seeded RELEASED
        fixture the public resume contract already uses. A stamp carrying a
        stale `phase` and `branch` must still resume; one structural field
        moved must refuse CONTINUITY-STATE-DIVERGENCE and write nothing."""
        import validate_orchestrator_store_contract as seed
        store_module = grill_workspace.grill_core_module("store")
        runtime, session = "claude", "orca:ctx-destination"
        for label, drift in (("stale-phase-and-branch", {"phase": "a-later-step",
                                                         "branch": "a-branch-nobody-was-on"}),
                             ("structural", {"real_path": "/a-tree-that-is-not-this-one"})):
            temporary, root = self.fixture()
            with temporary, self.subTest(case=label), orchestration_fixture.offline_leader(grill_workspace):
                with mock.patch.object(grill_workspace, "_initialize_orchestration", return_value={}):
                    code, payload = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                        "--work-id", "work-x", "--runtime", "codex",
                        "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
                self.assertEqual(code, 0, payload)
                state = grill_workspace.read_development_state(root,
                    grill_workspace.resolve_development_item(root, "work-x"), "work-x")[1]
                live = grill_workspace._continuity_identity(root, "work-x", state)
                sealed = {**live, **drift}
                self.assertNotEqual(sealed, live)
                context = seed.ORCHESTRATION_CONTEXT(state="RELEASED", leader_state="RELEASED")
                context.update(runtime="codex", adapter="codex", worktree_identity=sealed)
                checkpoint = seed.ORCHESTRATION_CHECKPOINT()
                checkpoint.update(worktree_identity=sealed, accepted_outputs={"specify": {"output_sha256": "a" * 64}})
                checkpoint["checkpoint_sha256"] = store_module.jcs_sha256(
                    {k: v for k, v in checkpoint.items() if k != "checkpoint_sha256"})
                operation = seed.ORCHESTRATION_OPERATION()
                operation.update(kind="continuity-switch", state="APPLIED",
                                 expected_before={"checkpoint_id": "checkpoint-1"},
                                 intended_after={"to_runtime": runtime, "campaign_bridge": None})
                item = seed.ORCHESTRATION_ITEM({"ctx-1": context}, {"op-1": operation})
                item["policy_ref"] = "assets/agent-orchestration.v1.json"
                item["policy_sha256"] = context["policy_sha256"] = grill_workspace.hash_bytes(
                    (grill_workspace.ASSETS / "agent-orchestration.v1.json").read_bytes())
                item.update(checkpoints={"checkpoint-1": checkpoint}, checkpoint_head="checkpoint-1")
                store_module.bootstrap(root)
                store_module.transact(root, lambda doc: {**doc, "agent_orchestration": {
                    "schema": "grill-agent-orchestration/v1", "work_items": {"work-x": item}}})
                argv = ("gauntlet-resume", str(root), "--work-id", "work-x", "--checkpoint", "checkpoint-1",
                        "--runtime", runtime, "--session-ref", session)
                before = store_module.read_snapshot(root).content_sha256
                if label == "structural":
                    # The identity check runs before any leader observation, so
                    # this refusal needs no boundary at all.
                    code, blocked = self.run_cli(*argv)
                    self.assertEqual((code, blocked.get("code")), (2, "CONTINUITY-STATE-DIVERGENCE"), blocked)
                    self.assertEqual(store_module.read_snapshot(root).content_sha256, before)
                    continue
                adapter, _show, transcript = orchestration_fixture.boundary(
                    grill_workspace, root, runtime, session, "work-x")
                transcript["result"]["transcript"]["messages"][0]["blocks"][0]["input"] = {
                    "command": shlex.join([sys.executable, "-B", str(SCRIPTS / "grill_workspace.py"), *argv])}
                with mock.patch.object(grill_workspace, "_continuity_effective_activation",
                        return_value={"runtime": {"id": runtime, "adapter": runtime}}), \
                     mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter):
                    code, preview = self.run_cli(*argv)
                self.assertEqual((code, preview.get("verdict")), (0, "PREVIEW"), preview)
                self.assertEqual(store_module.read_snapshot(root).content_sha256, before)

    def test_continuity_resume_compares_the_bound_execution_branch(self):
        """R5-1/T040, the resume half: `branch` left the structural tuple
        (T035) because it moves in normal life and no verb re-stamps it, and
        the compensating control -- the execution branch the work item binds --
        was never read here. So a work item already bound to one branch resumed
        from any other. The binding is the SSOT that does survive a switch:
        when it exists, the live branch must equal it; when it does not, the
        resume stays as permissive as T035 made it.

        Verified by reversion: deleting the comparison makes the bound-elsewhere
        half return PREVIEW/exit 0 -- the resume proceeding on a branch the work
        item is not bound to, not merely a different refusal code (T046).
        """
        import validate_orchestrator_store_contract as seed
        store_module = grill_workspace.grill_core_module("store")
        runtime, session = "claude", "orca:ctx-destination"
        for label, bound in (("bound-elsewhere", "a-branch-nobody-was-on"), ("bound-here", None)):
            temporary, root = self.fixture()
            with temporary, self.subTest(case=label), orchestration_fixture.offline_leader(grill_workspace):
                with mock.patch.object(grill_workspace, "_initialize_orchestration", return_value={}):
                    code, payload = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                        "--work-id", "work-x", "--runtime", "codex",
                        "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
                self.assertEqual(code, 0, payload)
                state_path = root / ".grill" / "work-items" / "work-x" / "state.json"
                live_branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                                             check=True, capture_output=True, text=True).stdout.strip()
                stored = json.loads(state_path.read_text(encoding="utf-8"))
                stored["development"]["execution_branch"] = bound or live_branch
                state_path.write_text(json.dumps(stored), encoding="utf-8")
                if bound is not None:
                    # T063: fixture sanity, not coverage -- `bound` is the fixed
                    # literal below ("a-branch-nobody-was-on"), never derived
                    # from `live_branch`, so this only guards against the
                    # fixture's init branch colliding with the literal. The
                    # real assertion is the readback further down.
                    self.assertNotEqual(bound, live_branch)
                state = grill_workspace.read_development_state(root,
                    grill_workspace.resolve_development_item(root, "work-x"), "work-x")[1]
                # The stamp itself is untouched: only the binding disagrees, so
                # a failure here can only come from the new comparison.
                sealed = grill_workspace._continuity_identity(root, "work-x", state)
                context = seed.ORCHESTRATION_CONTEXT(state="RELEASED", leader_state="RELEASED")
                context.update(runtime="codex", adapter="codex", worktree_identity=sealed)
                checkpoint = seed.ORCHESTRATION_CHECKPOINT()
                checkpoint.update(worktree_identity=sealed, accepted_outputs={"specify": {"output_sha256": "a" * 64}})
                checkpoint["checkpoint_sha256"] = store_module.jcs_sha256(
                    {k: v for k, v in checkpoint.items() if k != "checkpoint_sha256"})
                operation = seed.ORCHESTRATION_OPERATION()
                operation.update(kind="continuity-switch", state="APPLIED",
                                 expected_before={"checkpoint_id": "checkpoint-1"},
                                 intended_after={"to_runtime": runtime, "campaign_bridge": None})
                item = seed.ORCHESTRATION_ITEM({"ctx-1": context}, {"op-1": operation})
                item["policy_ref"] = "assets/agent-orchestration.v1.json"
                item["policy_sha256"] = context["policy_sha256"] = grill_workspace.hash_bytes(
                    (grill_workspace.ASSETS / "agent-orchestration.v1.json").read_bytes())
                item.update(checkpoints={"checkpoint-1": checkpoint}, checkpoint_head="checkpoint-1")
                store_module.bootstrap(root)
                store_module.transact(root, lambda doc: {**doc, "agent_orchestration": {
                    "schema": "grill-agent-orchestration/v1", "work_items": {"work-x": item}}})
                argv = ("gauntlet-resume", str(root), "--work-id", "work-x", "--checkpoint", "checkpoint-1",
                        "--runtime", runtime, "--session-ref", session)
                before = store_module.read_snapshot(root).content_sha256
                # R6-3/T046: both halves get the SAME boundary substitutes. The
                # divergent half used to run without them, so it stopped short
                # on the missing activation and the reversion only changed which
                # refusal code came out first -- exit code and write barrier read
                # identically with and without the comparison. Installed here,
                # the reversion degrades this half to PREVIEW/exit 0, which is
                # what "the resume proceeds on a foreign branch" actually means.
                adapter, _show, transcript = orchestration_fixture.boundary(
                    grill_workspace, root, runtime, session, "work-x")
                transcript["result"]["transcript"]["messages"][0]["blocks"][0]["input"] = {
                    "command": shlex.join([sys.executable, "-B", str(SCRIPTS / "grill_workspace.py"), *argv])}
                with mock.patch.object(grill_workspace, "_continuity_effective_activation",
                        return_value={"runtime": {"id": runtime, "adapter": runtime}}), \
                     mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter):
                    code, payload = self.run_cli(*argv)
                if bound is not None:
                    self.assertEqual((code, payload.get("code")), (2, "CONTINUITY-STATE-DIVERGENCE"), payload)
                    self.assertIn(bound, payload.get("error", ""))
                else:
                    self.assertEqual((code, payload.get("verdict")), (0, "PREVIEW"), payload)
                self.assertEqual(store_module.read_snapshot(root).content_sha256, before)

    def test_continuity_resume_refuses_a_malformed_development_block(self):
        """T055/T060: `_continuity_identity` validates `development`'s own
        shape unconditionally, before any continuity verb reads
        `execution_branch` -- DEVELOPMENT-SCHEMA when the block is present
        but not a mapping. The step-confirmation and phase-turn commands
        raise the same named code for the identical shape, but only on
        their own local `state.json` read; this guard is reachable through
        `continuity-resume` too, and had no case proving it there.
        `_continuity_refuse_branch_contradiction` carries the same-named
        guard, but it is defense in depth today: no CLI path reaches it,
        because `_continuity_identity` runs first in all three verbs and
        already refuses this shape.

        Verified by reversion: removing the guard from `_continuity_identity`
        does not let this case proceed -- measured result is
        (2, "UNEXPECTED-FAILURE") with an AttributeError, because nothing
        downstream still names DEVELOPMENT-SCHEMA for this shape.
        """
        import validate_orchestrator_store_contract as seed
        store_module = grill_workspace.grill_core_module("store")
        runtime, session = "claude", "orca:ctx-destination"
        temporary, root = self.fixture()
        with temporary, orchestration_fixture.offline_leader(grill_workspace):
            with mock.patch.object(grill_workspace, "_initialize_orchestration", return_value={}):
                code, payload = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                    "--work-id", "work-x", "--runtime", "codex",
                    "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, payload)
            state_path = root / ".grill" / "work-items" / "work-x" / "state.json"
            state = grill_workspace.read_development_state(root,
                grill_workspace.resolve_development_item(root, "work-x"), "work-x")[1]
            sealed = grill_workspace._continuity_identity(root, "work-x", state)
            context = seed.ORCHESTRATION_CONTEXT(state="RELEASED", leader_state="RELEASED")
            context.update(runtime="codex", adapter="codex", worktree_identity=sealed)
            checkpoint = seed.ORCHESTRATION_CHECKPOINT()
            checkpoint.update(worktree_identity=sealed, accepted_outputs={"specify": {"output_sha256": "a" * 64}})
            checkpoint["checkpoint_sha256"] = store_module.jcs_sha256(
                {k: v for k, v in checkpoint.items() if k != "checkpoint_sha256"})
            operation = seed.ORCHESTRATION_OPERATION()
            operation.update(kind="continuity-switch", state="APPLIED",
                             expected_before={"checkpoint_id": "checkpoint-1"},
                             intended_after={"to_runtime": runtime, "campaign_bridge": None})
            item = seed.ORCHESTRATION_ITEM({"ctx-1": context}, {"op-1": operation})
            item["policy_ref"] = "assets/agent-orchestration.v1.json"
            item["policy_sha256"] = context["policy_sha256"] = grill_workspace.hash_bytes(
                (grill_workspace.ASSETS / "agent-orchestration.v1.json").read_bytes())
            item.update(checkpoints={"checkpoint-1": checkpoint}, checkpoint_head="checkpoint-1")
            store_module.bootstrap(root)
            store_module.transact(root, lambda doc: {**doc, "agent_orchestration": {
                "schema": "grill-agent-orchestration/v1", "work_items": {"work-x": item}}})
            stored = json.loads(state_path.read_text(encoding="utf-8"))
            stored["active_phase"] = None
            stored["development"] = "not-a-mapping"
            state_path.write_text(json.dumps(stored), encoding="utf-8")
            argv = ("gauntlet-resume", str(root), "--work-id", "work-x", "--checkpoint", "checkpoint-1",
                    "--runtime", runtime, "--session-ref", session)
            before = store_module.read_snapshot(root).content_sha256
            adapter, _show, transcript = orchestration_fixture.boundary(
                grill_workspace, root, runtime, session, "work-x")
            transcript["result"]["transcript"]["messages"][0]["blocks"][0]["input"] = {
                "command": shlex.join([sys.executable, "-B", str(SCRIPTS / "grill_workspace.py"), *argv])}
            with mock.patch.object(grill_workspace, "_continuity_effective_activation",
                    return_value={"runtime": {"id": runtime, "adapter": runtime}}), \
                 mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter):
                code, blocked = self.run_cli(*argv)
            self.assertEqual((code, blocked.get("code")), (2, "DEVELOPMENT-SCHEMA"), blocked)
            self.assertEqual(store_module.read_snapshot(root).content_sha256, before)

    def test_continuity_refuse_branch_contradiction_guards_malformed_development_directly(self):
        """T061: `_continuity_refuse_branch_contradiction`'s own DEVELOPMENT-SCHEMA
        guard (T047) is defense in depth today -- `_continuity_identity` (T055)
        already refuses the same shape first, in all three continuity verbs, so
        no CLI path reaches this one (see T059/T060). It still needs its own
        coverage: nothing else in this file calls the function directly, and
        swapping its guard for silent continuation leaves the whole suite green.

        Verified by mutation: replacing the `raise` with `pass` makes this case
        fail -- the call returns `None` instead of refusing.

        T068: `_continuity_identity_matches`'s own fail-closed branch (a
        present-but-non-mapping stamp never matches) has no direct case
        either -- inverting it makes a non-mapping stamp match in all three
        comparators (prepare-switch, resume, takeover). Verified by mutation:
        flipping that `return False` to `return True` makes this line fail.
        """
        with self.assertRaises(grill_workspace.CliFailure) as blocked:
            grill_workspace._continuity_refuse_branch_contradiction(
                {"development": "not-a-mapping"}, {}, "work-x")
        self.assertEqual(blocked.exception.code, "DEVELOPMENT-SCHEMA")
        self.assertFalse(grill_workspace._continuity_identity_matches("not-a-mapping", {}))

    def test_prepare_switch_and_takeover_compare_the_bound_execution_branch(self):
        """T067/R10: the sixth review round (R6-T045) made
        `_continuity_refuse_branch_contradiction` the single point every
        continuity verb calls so a sealed/live execution-branch contradiction
        is named *before* anything mutates -- prepare-switch creates the
        operation and releases the leader, and takeover re-stamps the
        identity, before either one is done checking. Neither call site
        (grill_workspace.py, `gauntlet_prepare_switch_command` and
        `gauntlet_context_takeover_command`) had a case: swapping either call
        for `pass` leaves the whole 51-test suite green.

        Each half seeds `development.execution_branch` (the work item's own
        sealed SSOT) to a branch that is not the live one and requires the
        named refusal, with the store digest unchanged -- proving the
        refusal happens before any write, which is the entire point of the
        finding.

        Verified by mutation: commenting out either
        `_continuity_refuse_branch_contradiction(...)` call (prepare-switch
        or takeover) makes its half proceed to SWITCH-PREPARED/QUIESCING or
        TAKEOVER-APPLIED instead of refusing, and the store digest changes.
        """
        bound = "a-branch-nobody-was-on"
        temp, root = self.fixture()
        with temp, orchestration_fixture.offline_leader(grill_workspace):
            live_branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                                         check=True, capture_output=True, text=True).stdout.strip()
            self.assertNotEqual(bound, live_branch)

            def bind_to(work_id):
                state_path = root / ".grill" / "work-items" / work_id / "state.json"
                stored = json.loads(state_path.read_text(encoding="utf-8"))
                stored["development"]["execution_branch"] = bound
                state_path.write_text(json.dumps(stored), encoding="utf-8")

            # -- prepare-switch half. --
            code, created = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                "--work-id", "work-switch", "--runtime", "codex",
                "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, created)
            switch_context_id = store.read_snapshot(root).document["agent_orchestration"][
                "work_items"]["work-switch"]["current_context_id"]
            bind_to("work-switch")
            before = store.read_snapshot(root).content_sha256
            code, blocked = self.run_cli("gauntlet-prepare-switch", str(root), "--work-id", "work-switch",
                "--session-ref", orchestration_fixture.SESSION, "--context-id", switch_context_id,
                "--epoch", "1", "--to-runtime", "claude")
            self.assertEqual((code, blocked.get("code")), (2, "CONTINUITY-STATE-DIVERGENCE"), blocked)
            self.assertIn(bound, blocked.get("error", ""))
            self.assertEqual(store.read_snapshot(root).content_sha256, before)

            # -- takeover half. --
            code, created = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                "--work-id", "work-takeover", "--runtime", "codex",
                "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, created)
            bind_to("work-takeover")
            before = store.read_snapshot(root).content_sha256
            old_dispatch = orchestration_fixture.SESSION.removeprefix("orca:")
            raw = takeover_show(old_dispatch, status="completed")
            real_run = subprocess.run
            def guarded(cmd, **kwargs):
                if isinstance(cmd, list) and "worker-show" in cmd:
                    return subprocess.CompletedProcess(cmd, 0, stdout=raw)
                return real_run(cmd, **kwargs)
            with mock.patch.dict(os.environ, {"ORCA_TERMINAL_HANDLE": "term-fixture"}), \
                 mock.patch.object(subprocess, "run", side_effect=guarded):
                code, blocked = self.run_cli("gauntlet-context-takeover", str(root), "--work-id", "work-takeover",
                    "--session-ref", "orca:ctx-new-takeover")
            self.assertEqual((code, blocked.get("code")), (2, "CONTINUITY-STATE-DIVERGENCE"), blocked)
            self.assertIn(bound, blocked.get("error", ""))
            self.assertEqual(store.read_snapshot(root).content_sha256, before)

    def test_continuity_resume_tolerates_an_absent_development_block(self):
        """T062: `_continuity_identity`'s DEVELOPMENT-SCHEMA guard only fires
        when `development` is present and the wrong type -- `development is
        not None and not isinstance(development, dict)`. Absence is a
        legitimate state, not a hypothesis: it is the terminal-milestone
        shape `audit_decisions.py` requires (`active_phase` null), and the
        `is not None` half of the clause is what lets a work item in that
        shape resume at all. Untested until now: tightening the clause to
        `not isinstance(development, dict)`, which refuses absence too,
        leaves the whole suite green.

        Verified by mutation: that tightened clause makes this case refuse
        DEVELOPMENT-SCHEMA/exit 2 instead of proceeding.
        """
        import validate_orchestrator_store_contract as seed
        store_module = grill_workspace.grill_core_module("store")
        runtime, session = "claude", "orca:ctx-destination"
        temporary, root = self.fixture()
        with temporary, orchestration_fixture.offline_leader(grill_workspace):
            with mock.patch.object(grill_workspace, "_initialize_orchestration", return_value={}):
                code, payload = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                    "--work-id", "work-x", "--runtime", "codex",
                    "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, payload)
            state_path = root / ".grill" / "work-items" / "work-x" / "state.json"
            state = grill_workspace.read_development_state(root,
                grill_workspace.resolve_development_item(root, "work-x"), "work-x")[1]
            sealed = grill_workspace._continuity_identity(root, "work-x", state)
            context = seed.ORCHESTRATION_CONTEXT(state="RELEASED", leader_state="RELEASED")
            context.update(runtime="codex", adapter="codex", worktree_identity=sealed)
            checkpoint = seed.ORCHESTRATION_CHECKPOINT()
            checkpoint.update(worktree_identity=sealed, accepted_outputs={"specify": {"output_sha256": "a" * 64}})
            checkpoint["checkpoint_sha256"] = store_module.jcs_sha256(
                {k: v for k, v in checkpoint.items() if k != "checkpoint_sha256"})
            operation = seed.ORCHESTRATION_OPERATION()
            operation.update(kind="continuity-switch", state="APPLIED",
                             expected_before={"checkpoint_id": "checkpoint-1"},
                             intended_after={"to_runtime": runtime, "campaign_bridge": None})
            item = seed.ORCHESTRATION_ITEM({"ctx-1": context}, {"op-1": operation})
            item["policy_ref"] = "assets/agent-orchestration.v1.json"
            item["policy_sha256"] = context["policy_sha256"] = grill_workspace.hash_bytes(
                (grill_workspace.ASSETS / "agent-orchestration.v1.json").read_bytes())
            item.update(checkpoints={"checkpoint-1": checkpoint}, checkpoint_head="checkpoint-1")
            store_module.bootstrap(root)
            store_module.transact(root, lambda doc: {**doc, "agent_orchestration": {
                "schema": "grill-agent-orchestration/v1", "work_items": {"work-x": item}}})
            stored = json.loads(state_path.read_text(encoding="utf-8"))
            stored["active_phase"] = None
            del stored["development"]
            state_path.write_text(json.dumps(stored), encoding="utf-8")
            argv = ("gauntlet-resume", str(root), "--work-id", "work-x", "--checkpoint", "checkpoint-1",
                    "--runtime", runtime, "--session-ref", session)
            before = store_module.read_snapshot(root).content_sha256
            adapter, _show, transcript = orchestration_fixture.boundary(
                grill_workspace, root, runtime, session, "work-x")
            transcript["result"]["transcript"]["messages"][0]["blocks"][0]["input"] = {
                "command": shlex.join([sys.executable, "-B", str(SCRIPTS / "grill_workspace.py"), *argv])}
            with mock.patch.object(grill_workspace, "_continuity_effective_activation",
                    return_value={"runtime": {"id": runtime, "adapter": runtime}}), \
                 mock.patch.object(grill_workspace, "_leader_boundary", return_value=adapter):
                code, preview = self.run_cli(*argv)
            self.assertEqual((code, preview.get("verdict")), (0, "PREVIEW"), preview)
            self.assertEqual(store_module.read_snapshot(root).content_sha256, before)

    def _graft_succession(self, root, work_id, branch):
        """Leave behind the shape a takeover/resume produces: a successor
        context, descending from the current one, whose worktree identity is
        stamped on `branch`. The real verbs derive that stamp live and validate
        the structural identity in the act, so the stamp is the only evidence
        of which tree the context ran on -- and the Store forbids rewriting a
        context in place, which is why the succession is grafted as a new one.
        """
        import validate_orchestrator_store_contract as seed
        store_module = grill_workspace.grill_core_module("store")
        state = grill_workspace.read_development_state(
            root, grill_workspace.resolve_development_item(root, work_id), work_id)[1]
        sealed = {**grill_workspace._continuity_identity(root, work_id, state), "branch": branch}

        def apply(document):
            document = copy.deepcopy(document)
            item = document["agent_orchestration"]["work_items"][work_id]
            prior_id = item["current_context_id"]
            prior = item["contexts"][prior_id]
            epoch = prior["epoch"] + 1
            operation = seed.ORCHESTRATION_OPERATION("op-continuity", "ctx-successor")
            operation.update(kind="continuity-switch", state="APPLIED", fence=epoch,
                             intended_after={"campaign_bridge": None})
            item["contexts"][prior_id] = {**prior, "state": "SUPERSEDED",
                                          "leader": {**prior["leader"], "state": "RELEASING"}}
            item["contexts"]["ctx-successor"] = {
                **copy.deepcopy(prior), "context_id": "ctx-successor", "epoch": epoch,
                "predecessor_context_id": prior_id, "continuity_ref": "op-continuity",
                "worktree_identity": sealed,
                "leader": {**prior["leader"], "owner_id": "ctx-successor", "fence": epoch, "epoch": epoch}}
            item["operations"]["op-continuity"] = operation
            item["current_context_id"] = "ctx-successor"
            return document

        store_module.transact(root, apply)

    def _finish_phase(self, state_path, *, unbind):
        """Complete every step of the matrix so `phase-turn` is admissible,
        optionally clearing the binding to reach the turn's own minting branch."""
        state = json.loads(state_path.read_text(encoding="utf-8"))
        development = state["development"]
        development["steps"] = {step: "complete" for step in development["sequence"]}
        development["current_step"] = development["sequence"][-1]
        if unbind:
            development["execution_branch"] = None
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def test_execution_branch_minting_ignores_the_identity_stamp(self):
        """R6-1/T044, T048/T049. This case used to assert EXECUTION-BRANCH-MISMATCH
        whenever the identity stamp contradicted the live branch -- itself a
        narrower descendant of the very defect T048 removed. `_continuity_stamped_branch`
        read a value written once, at context creation, that no verb ever
        re-stamps, while `phase-turn` clears the binding on purpose so the next
        phase's first confirmation can mint a fresh one. Comparing an unrenewed
        stamp against the live branch refused every work item that was ever
        taken over or resumed, on its first confirmation after the very next
        phase turn -- permanently, with no verb to undo it.

        T048 removed the comparison entirely, at both minting sites -- the step
        confirmation and the phase turn, which had no guard of its own before
        R6 added one. The criterion is now just: no bound branch yet, mint the
        live one. What the identity stamp claims -- absent or contradicting,
        the two subcases this case still covers -- no longer matters: there
        is no upstream proof that the live branch is the one the context ran
        on. `branch` was pulled out of the structural tuple in T035, and two
        branches inside the same worktree look identical on
        project/path/git_common_dir alone. Minting just records the current
        branch as the binding; it does not verify one.

        Covers the sequence that motivated the removal end to end: succession,
        then the step confirmation, then the phase turn -- the dead end R6
        found, now open on both minting sites regardless of what the stamp
        says.

        Verified by reversion: restoring either stamp comparison makes the
        "stamp contradicts" subcase refuse EXECUTION-BRANCH-MISMATCH again, at
        whichever site it was restored on.
        """
        for label, stamp in (("no stamp", None),
                              ("stamp contradicts", "a-branch-nobody-was-on")):
            temporary, root = self.fixture()
            with temporary, self.subTest(case=label), orchestration_fixture.offline_leader(grill_workspace):
                code, payload = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                    "--work-id", "work-x", "--runtime", "codex",
                    "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
                self.assertEqual(code, 0, payload)
                state_path = root / ".grill" / "work-items" / "work-x" / "state.json"
                self.assertNotIn("execution_branch",
                                 json.loads(state_path.read_text(encoding="utf-8"))["development"])
                live_branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                                             check=True, capture_output=True, text=True).stdout.strip()
                if stamp is not None:
                    # T063: no subcase loads "live" any more -- the "agreeing"
                    # situation was removed on purpose (only "no stamp" and
                    # "stamp contradicts" remain above), so the selector this
                    # ternary switched on is dead. `stamp` is the value.
                    sealed_value = stamp
                    self._graft_succession(root, "work-x", sealed_value)
                    # Assert the value the graft actually sealed -- not a
                    # value standing in for the subcase's own label -- so a
                    # regression that stops the graft from writing the stamp
                    # is caught here, not just at the mint.
                    document = store.read_snapshot(root).document
                    item = document["agent_orchestration"]["work_items"]["work-x"]
                    context = item["contexts"][item["current_context_id"]]
                    self.assertEqual(context["worktree_identity"]["branch"], sealed_value)
                    # Fixture sanity, not coverage -- `sealed_value` here is
                    # the fixed literal "a-branch-nobody-was-on", never
                    # derived from `live_branch`. The real assertion is the
                    # readback above.
                    self.assertNotEqual(sealed_value, live_branch)

                # The step confirmation, which is where the backfill lives.
                code, payload = self.run_cli("checkpoint", str(root), "--work-id", "work-x",
                    "--step", "specify", "--state", "in-progress", "--operation-id", "op-specify",
                    "--session-ref", orchestration_fixture.SESSION)
                self.assertEqual(code, 0, payload)
                self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))[
                    "development"]["execution_branch"], live_branch)

                # The phase turn mints the binding through its own branch, the
                # one R6 found without any guard at all.
                self._finish_phase(state_path, unbind=True)
                code, payload = self.run_cli("phase-turn", str(root), "--work-id", "work-x",
                    "--reason", "abrindo a fase seguinte", "--session-ref", orchestration_fixture.SESSION)
                self.assertEqual((code, payload.get("verdict")), (0, "TURNED"), payload)
                turned = json.loads(state_path.read_text(encoding="utf-8"))["development"]
                self.assertIsNone(turned["execution_branch"])
                self.assertEqual(turned["audit"][-1]["previous_execution_branch"], live_branch)

    def test_a_succeeded_work_item_still_binds_a_branch_after_the_phase_turn(self):
        """R6-1/T044, the dead end itself, as one uninterrupted sequence:
        succession, then phase turn, then step confirmation. `phase-turn` clears
        `development["execution_branch"]` deliberately, so the next phase binds
        its own branch, and the only other writer is the mint. Under the old
        monotonic criterion the successor context could never mint again, so the
        first turn after ANY takeover or resume blocked the work item forever --
        an availability defect no verb could undo.

        Verified by reversion: restoring the "has a predecessor" criterion makes
        the final confirmation refuse EXECUTION-BRANCH-UNSET.
        """
        temporary, root = self.fixture()
        with temporary, orchestration_fixture.offline_leader(grill_workspace):
            code, payload = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                "--work-id", "work-x", "--runtime", "codex",
                "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, payload)
            state_path = root / ".grill" / "work-items" / "work-x" / "state.json"
            live_branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                                         check=True, capture_output=True, text=True).stdout.strip()
            code, payload = self.run_cli("checkpoint", str(root), "--work-id", "work-x",
                "--step", "specify", "--state", "in-progress", "--operation-id", "op-first",
                "--session-ref", orchestration_fixture.SESSION)
            self.assertEqual(code, 0, payload)
            self._graft_succession(root, "work-x", live_branch)
            self._finish_phase(state_path, unbind=False)
            code, payload = self.run_cli("phase-turn", str(root), "--work-id", "work-x",
                "--reason", "fase entregue", "--session-ref", orchestration_fixture.SESSION)
            self.assertEqual((code, payload.get("verdict")), (0, "TURNED"), payload)
            self.assertIsNone(json.loads(state_path.read_text(encoding="utf-8"))[
                "development"]["execution_branch"])
            code, payload = self.run_cli("checkpoint", str(root), "--work-id", "work-x",
                "--step", "specify", "--state", "in-progress", "--operation-id", "op-next-phase",
                "--session-ref", orchestration_fixture.SESSION)
            self.assertEqual(code, 0, payload)
            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))[
                "development"]["execution_branch"], live_branch)

    def test_block_refuses_a_resource_whose_activity_lives_in_another_context(self):
        """o1/T043: every producer pins a resource to the context of its own
        activity (`new_specialist_resource`) and no verb moves an activity
        between contexts (`prepare_activity` fences on it), so the shape the
        cleanup scope reasons about -- a foreign-context resource carrying the
        requested activity -- is one the core never emits. It was only implicit:
        the Store accepted it, which is what made the cleanup case covering
        that branch a test of a document nothing produces. Asserted here, the
        branch becomes defence in depth instead of false confidence.

        Verified by reversion: without the invariant the divergent block
        validates clean.
        """
        import validate_orchestrator_store_contract as seed
        item = seed.ORCHESTRATION_ITEM({"ctx-1": seed.ORCHESTRATION_CONTEXT(),
                                        "ctx-2": seed.ORCHESTRATION_CONTEXT("ctx-2", 2)})
        item["activities"] = {"activity-1": seed.ORCHESTRATION_ACTIVITY()}
        item["resources"] = {"resource-1": seed.ORCHESTRATION_RESOURCE()}
        block = {"schema": agent_orchestration.SCHEMA, "work_items": {"work-x": item}}
        agent_orchestration.validate_block(copy.deepcopy(block))
        divergent = copy.deepcopy(block)
        divergent["work_items"]["work-x"]["resources"]["resource-1"]["origin_context_id"] = "ctx-2"
        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "another context"):
            agent_orchestration.validate_block(divergent)

    def test_prepare_switch_refuses_declared_but_unknown_checkpoint(self):
        """T005: only the "no checkpoint at all yet" branch (checkpoint_head is
        None) was relaxed to synthesize one (FR-006, see
        test_every_work_entry_reobserves_authority_and_requires_presentation).
        A checkpoint_head that IS set but does not resolve inside checkpoints
        still refuses CONTINUITY-CHECKPOINT-MISSING. validate_block already
        refuses to persist a document shaped that way through any real write
        (p02-a's own T005 finding), so this stubs store.read_snapshot for one
        call instead of writing it to disk."""
        temp, root = self.fixture()
        store_module = grill_workspace.grill_core_module("store")
        with temp, orchestration_fixture.offline_leader(grill_workspace):
            code, created = self.run_cli("init", str(root), "--work-id", "work-x", "--type", "feature",
                "--slug", "x", "--runtime", "codex", "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, created)
            real = store_module.read_snapshot(root)
            context_id = real.document["agent_orchestration"]["work_items"]["work-x"]["current_context_id"]
            tampered = copy.deepcopy(real.document)
            tampered["agent_orchestration"]["work_items"]["work-x"]["checkpoint_head"] = "cp-declared-but-unknown"
            stub = store_module.Snapshot(document=tampered, revision=real.revision,
                content_sha256=real.content_sha256, project_id=real.project_id, path=real.path)
            with mock.patch.object(store_module, "read_snapshot", return_value=stub):
                code, blocked = self.run_cli("gauntlet-prepare-switch", str(root), "--work-id", "work-x",
                    "--context-id", context_id, "--epoch", "1", "--session-ref", orchestration_fixture.SESSION,
                    "--to-runtime", "claude")
                self.assertEqual((code, blocked.get("code")), (2, "CONTINUITY-CHECKPOINT-MISSING"), blocked)

    def test_context_takeover(self):
        """T007: gauntlet-context-takeover accepts a takeover only on a proven
        terminal observation of the predecessor dispatch, refuses every live or
        inconclusive signal with its own code, preview and apply agree on every
        verdict, preview never writes, a stale hash is refused and an identical
        replay short-circuits without re-observing (contracts/context-takeover.md)."""
        temp, root = self.fixture()
        with temp, orchestration_fixture.offline_leader(grill_workspace):
            old_session = orchestration_fixture.SESSION
            old_dispatch = old_session.removeprefix("orca:")

            def spawn(work_id):
                code, created = self.run_cli("init", str(root), "--work-id", work_id, "--type", "feature",
                    "--slug", work_id, "--runtime", "codex", "--session-ref", old_session, "--skip-backlog")
                self.assertEqual(code, 0, created)
                item = store.read_snapshot(root).document["agent_orchestration"]["work_items"][work_id]
                return item["current_context_id"]

            def takeover(work_id, new_session, *tail):
                return self.run_cli("gauntlet-context-takeover", str(root), "--work-id", work_id,
                                    "--session-ref", new_session, *tail)

            real_run = subprocess.run

            def guarded_run(raw):
                # Only the orca worker-show call _takeover_observation issues is
                # synthetic (or forbidden, when raw is None); every other
                # subprocess call (git, via store.read_snapshot et al.) still
                # runs for real -- it must pass through untouched either way.
                def run(cmd, **kwargs):
                    if isinstance(cmd, list) and "worker-show" in cmd:
                        if raw is None:
                            raise AssertionError("observation must not run here")
                        return subprocess.CompletedProcess(cmd, 0, stdout=raw)
                    return real_run(cmd, **kwargs)
                return mock.patch.object(subprocess, "run", side_effect=run)

            def observing(raw):
                return mock.patch.dict(os.environ, {"ORCA_TERMINAL_HANDLE": "term-fixture"}), guarded_run(raw)

            def assert_refused_and_unwritten(work_id, new_session, code_, raw=None):
                context = observing(raw) if raw is not None else (guarded_run(None),)
                with contextlib.ExitStack() as stack:
                    for manager in context:
                        stack.enter_context(manager)
                    before = store.read_snapshot(root).content_sha256
                    for tail in ((), ("--apply", "--expected-sha256", "0" * 64)):
                        with self.subTest(work_id=work_id, code=code_, apply=bool(tail)):
                            status, blocked = takeover(work_id, new_session, *tail)
                            self.assertEqual((status, blocked.get("code")), (2, code_), blocked)
                    self.assertEqual(store.read_snapshot(root).content_sha256, before)

            # -- three independent, real reasons observe_predecessor_termination
            # calls the predecessor terminal; every one accepts the takeover. --
            terminal = {
                "status": (takeover_show(old_dispatch, status="completed",
                    liveness={"verdict": "live", "source": "agent_status"}), "completed",
                    {"verdict": "live", "source": "agent_status"}),
                "revoked": (takeover_show(old_dispatch, status="dispatched",
                    revoked="2026-01-01T00:00:00Z"), "dispatched", None),
                "exited": (takeover_show(old_dispatch, status="dispatched",
                    liveness={"verdict": "exited", "source": "agent_status"}), "dispatched",
                    {"verdict": "exited", "source": "agent_status"}),
            }
            for label, (raw, expected_status, expected_liveness) in terminal.items():
                work_id = "work-terminal-" + label
                old_context_id = spawn(work_id)
                new_session = "orca:ctx-new-" + label
                env, transport = observing(raw)
                with self.subTest(case=label), env, transport:
                    before = store.read_snapshot(root).content_sha256
                    code, preview = takeover(work_id, new_session)
                    self.assertEqual((code, preview.get("verdict")), (0, "TAKEOVER-PREVIEW"), preview)
                    self.assertEqual(store.read_snapshot(root).content_sha256, before)
                    code, applied = takeover(work_id, new_session, "--apply", "--expected-sha256", preview["expected_sha256"])
                    self.assertEqual((code, applied.get("verdict")), (0, "TAKEOVER-APPLIED"), applied)
                    self.assertEqual(applied["from_context_id"], old_context_id)
                    self.assertEqual(applied["succession"]["reason"], "takeover")
                    # T014/FR-004: dispatch_status and liveness must come from the
                    # same enveloped {"ok": true, "result": {...}} shape the real
                    # transport returns, not a top-level read that always misses.
                    self.assertEqual(applied["succession"]["evidence"]["dispatch_status"], expected_status)
                    self.assertEqual(applied["succession"]["evidence"]["liveness"], expected_liveness)
                    document = store.read_snapshot(root).document["agent_orchestration"]["work_items"][work_id]
                    self.assertEqual(document["contexts"][old_context_id]["state"], "SUPERSEDED")
                    new_context = document["contexts"][applied["context_id"]]
                    self.assertEqual((new_context["state"], new_context["leader"]["session_ref"]), ("ACTIVE", new_session))
                    # T021/T016/FR-001: the successor leader must carry the
                    # *incoming* session's own observation. These three were
                    # installed as None, so every @_gauntlet_authorized command
                    # refused the very session the takeover had just installed.
                    readiness = grill_workspace._session_readiness(root, "codex", new_session, work_id=work_id)
                    leader = new_context["leader"]
                    self.assertEqual([leader["observation_ref"], leader["observation_sha256"], leader["incarnation"]],
                                     [readiness["ref"], readiness["sha256"], readiness["incarnation"]])
                    self.assertTrue(all(leader[key] is not None for key in
                                        ("observation_ref", "observation_sha256", "incarnation")))
                    # FR-004: the presentation now comes from the incoming
                    # session's readiness (mirroring continuity_resume_command),
                    # not from a copy of the predecessor's context.
                    self.assertEqual(new_context["presentation"], readiness["presentation"])
                    self.assertEqual(applied["presentation"], new_context["presentation"])
                    # FR-004: the persisted succession operation carries reason,
                    # destination runtime, proof and instant -- the response is
                    # not the record.
                    operation = document["operations"][new_context["continuity_ref"]]
                    self.assertEqual(operation["kind"], "continuity-switch")
                    self.assertEqual(operation["context_id"], old_context_id)
                    self.assertEqual(operation["subject_ids"], [old_context_id, applied["context_id"]])
                    self.assertEqual({key: operation["intended_after"][key] for key in
                                      ("reason", "to_runtime", "from_session_ref", "to_session_ref", "evidence", "taken_at")},
                                     {"reason": "takeover", "to_runtime": "codex", "from_session_ref": old_session,
                                      "to_session_ref": new_session, "evidence": applied["succession"]["evidence"],
                                      "taken_at": applied["succession"]["taken_at"]})
                    # The case that would have caught T016: an authorized verb
                    # run as the incoming session must be accepted, end to end,
                    # through _require_current_leader.
                    code, entered = self.run_cli("gauntlet-step-enter", str(root), "--work-id", work_id,
                        "--context-id", applied["context_id"], "--epoch", str(applied["epoch"]),
                        "--session-ref", new_session, "--step", "implement-parallel")
                    self.assertEqual(code, 0, entered)
            applied_work_id, applied_session = "work-terminal-status", "orca:ctx-new-status"

            # -- T021/FR-004: worktree identity is inherited, not re-derived. A
            # fresh context has none yet, so the predecessor is first taken
            # through prepare-switch (which stamps it and leaves the context
            # QUIESCING, a state takeover still accepts). --
            inherit_context_id = spawn("work-inherit")
            code, quiescing = self.run_cli("gauntlet-prepare-switch", str(root), "--work-id", "work-inherit",
                "--session-ref", old_session, "--context-id", inherit_context_id, "--epoch", "1",
                "--to-runtime", "claude")
            self.assertEqual((code, quiescing.get("verdict")), (0, "QUIESCING"), quiescing)
            stamped = store.read_snapshot(root).document["agent_orchestration"]["work_items"][
                "work-inherit"]["contexts"][inherit_context_id]["worktree_identity"]
            self.assertTrue(stamped)
            env, transport = observing(takeover_show(old_dispatch, status="completed"))
            with env, transport:
                code, preview = takeover("work-inherit", "orca:ctx-new-inherit")
                self.assertEqual(code, 0, preview)
                code, inherited = takeover("work-inherit", "orca:ctx-new-inherit", "--apply",
                                           "--expected-sha256", preview["expected_sha256"])
            self.assertEqual((code, inherited.get("verdict")), (0, "TAKEOVER-APPLIED"), inherited)
            inherit_item = store.read_snapshot(root).document["agent_orchestration"]["work_items"]["work-inherit"]
            self.assertEqual(inherit_item["contexts"][inherited["context_id"]]["worktree_identity"], stamped)

            # -- R3-1/R3-2/T030: `phase` and `branch` move during the normal
            # life of a context (phase with every cycle step, branch by routine
            # human action once nobody drives the tree), and only a successful
            # takeover rewrites the stamp -- there is no re-stamp verb. While
            # they were inside the compared identity, the takeover refused the
            # very scenario it exists to cure, permanently. They must be
            # re-stamped from the live derived identity instead. --
            restamp_context_id = spawn("work-restamp")
            code, quiescing = self.run_cli("gauntlet-prepare-switch", str(root), "--work-id", "work-restamp",
                "--session-ref", old_session, "--context-id", restamp_context_id, "--epoch", "1",
                "--to-runtime", "claude")
            self.assertEqual((code, quiescing.get("verdict")), (0, "QUIESCING"), quiescing)
            sealed_identity = copy.deepcopy(store.read_snapshot(root).document["agent_orchestration"][
                "work_items"]["work-restamp"]["contexts"][restamp_context_id]["worktree_identity"])
            # The stamp is immutable in the Store, so the *live* tree is what
            # moves -- exactly as it does in production: the cycle advances a
            # step and someone switches branch once the session is dead.
            original_branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                                             check=True, capture_output=True, text=True).stdout.strip()
            # R5-2: teardown, not a protected block. The restoration tolerates
            # failure so it never masks the real assertion (T038), and as a
            # `finally` that meant the cases *after* it could silently derive
            # identity from the test branch. Registered as cleanup it always
            # runs, at the end of the case, with no uncovered window.
            self.addCleanup(subprocess.run, ["git", "-C", str(root), "checkout", "-q", original_branch],
                            check=False)
            subprocess.run(["git", "-C", str(root), "checkout", "-q", "-b", "a-branch-nobody-was-on"], check=True)
            state_path = root / ".grill" / "work-items" / "work-restamp" / "state.json"
            aged = json.loads(state_path.read_text(encoding="utf-8"))
            aged["active_phase"] = "a-later-step"
            state_path.write_text(json.dumps(aged), encoding="utf-8")
            self.assertNotEqual((sealed_identity["phase"], sealed_identity["branch"]),
                                ("a-later-step", "a-branch-nobody-was-on"))
            env, transport = observing(takeover_show(old_dispatch, status="completed"))
            with env, transport:
                code, preview = takeover("work-restamp", "orca:ctx-new-restamp")
                self.assertEqual(code, 0, preview)
                code, restamped = takeover("work-restamp", "orca:ctx-new-restamp", "--apply",
                                           "--expected-sha256", preview["expected_sha256"])
            self.assertEqual((code, restamped.get("verdict")), (0, "TAKEOVER-APPLIED"), restamped)
            restamp_item = store.read_snapshot(root).document["agent_orchestration"]["work_items"]["work-restamp"]
            successor = restamp_item["contexts"][restamped["context_id"]]["worktree_identity"]
            # The successor carries the *live* values, not the predecessor's
            # stale copy; every structural field is preserved untouched.
            self.assertEqual((successor["phase"], successor["branch"]),
                             ("a-later-step", "a-branch-nobody-was-on"))
            self.assertEqual({key: successor[key] for key in
                              ("project_id", "work_id", "du", "git_common_dir", "real_path")},
                             {key: sealed_identity[key] for key in
                              ("project_id", "work_id", "du", "git_common_dir", "real_path")})
            # The cases below need the original branch back, so the case
            # restores it explicitly and demands success -- no assertion is in
            # flight here, so `check=True` masks nothing. The cleanup above
            # stays as the net for the paths that never reach this line.
            subprocess.run(["git", "-C", str(root), "checkout", "-q", original_branch], check=True)
            # -- R4-2/T036: the REFUSAL side of the same guard, which no test
            # exercised at all: `grep -rn TAKEOVER-IDENTITY-DIVERGENT tests/`
            # returned zero, and deleting the whole `raise` -- not relaxing it,
            # deleting it -- left the suite green. The `work-restamp` case above
            # covers only acceptance, and the reversions behind it prove the
            # guard cannot be widened *back*, never that it exists. Here a
            # STRUCTURAL field moves instead of phase and branch: `real_path` is
            # rewritten straight in the sealed stamp (a fixture mutation; no
            # product path rewrites a stamp), so the live tree still answers
            # what it always did and only the sealed claim disagrees. --
            divergent_context_id = spawn("work-divergent")
            code, quiescing = self.run_cli("gauntlet-prepare-switch", str(root), "--work-id", "work-divergent",
                "--session-ref", old_session, "--context-id", divergent_context_id, "--epoch", "1",
                "--to-runtime", "claude")
            self.assertEqual((code, quiescing.get("verdict")), (0, "QUIESCING"), quiescing)

            # worktree_identity is an immutable context field, so the Store
            # refuses to persist the moved stamp through any write (verified:
            # ORCHESTRATOR_INVALID, "context immutable field changed"). The
            # divergence is therefore handed in by stubbing one read, exactly
            # as test_prepare_switch_refuses_declared_but_unknown_checkpoint
            # does; the "nothing was written" check below reads the real file.
            takeover_store = grill_workspace.grill_core_module("store")
            real_snapshot = takeover_store.read_snapshot(root)
            tampered = copy.deepcopy(real_snapshot.document)
            moved_stamp = tampered["agent_orchestration"]["work_items"]["work-divergent"][
                "contexts"][divergent_context_id]["worktree_identity"]
            moved_stamp["real_path"] = moved_stamp["real_path"] + "-a-tree-that-is-not-this-one"
            self.assertNotEqual(moved_stamp["real_path"], str(root.resolve()))
            divergent_stub = takeover_store.Snapshot(document=tampered, revision=real_snapshot.revision,
                content_sha256=real_snapshot.content_sha256, project_id=real_snapshot.project_id,
                path=real_snapshot.path)
            before = store.read_snapshot(root).content_sha256
            env, transport = observing(takeover_show(old_dispatch, status="completed"))
            with env, transport:
                for tail in ((), ("--apply", "--expected-sha256", "0" * 64)):
                    with self.subTest(case="identity-divergent", apply=bool(tail)), \
                         mock.patch.object(takeover_store, "read_snapshot", return_value=divergent_stub):
                        code, blocked = takeover("work-divergent", "orca:ctx-new-divergent", *tail)
                        # R5-3: inside the subTest. Dedented, a failure of the
                        # preview iteration aborted the loop and the apply
                        # subcase never ran at all.
                        self.assertEqual((code, blocked.get("code")), (2, "TAKEOVER-IDENTITY-DIVERGENT"), blocked)
            self.assertEqual(store.read_snapshot(root).content_sha256, before)

            # -- a live dispatch refuses distinctly from an inconclusive one. --
            spawn("work-leader-active")
            assert_refused_and_unwritten("work-leader-active", "orca:ctx-new-active", "TAKEOVER-LEADER-ACTIVE",
                takeover_show(old_dispatch, status="dispatched", liveness={"verdict": "live", "source": "agent_status"}))

            # -- every inconclusive shape of the observation refuses the same way. --
            spawn("work-evidence-absent")
            with mock.patch.dict(os.environ, clear=False):
                os.environ.pop("ORCA_TERMINAL_HANDLE", None)
                assert_refused_and_unwritten("work-evidence-absent", "orca:ctx-new-absent", "TAKEOVER-EVIDENCE-UNPROVEN")
            for label, raw in (
                ("illegible", b"\xff\xfe\x00not-utf8"),
                ("invalid-json", b"not a json document at all"),
                ("uncorrelated", takeover_show("some-other-dispatch", status="dispatched")),
                ("liveness-unverifiable", takeover_show(old_dispatch, status=None, liveness={"verdict": "unverifiable"})),
            ):
                work_id = "work-evidence-" + label
                spawn(work_id)
                assert_refused_and_unwritten(work_id, "orca:ctx-new-" + label, "TAKEOVER-EVIDENCE-UNPROVEN", raw)

            # -- a session_ref the adapter cannot even shape a query out of.
            # A legitimate init always observes the LeaderBoundary form (same
            # regex as observe_predecessor_termination), so this can only be a
            # pre-existing binding -- built directly, like the seeded store
            # fixtures elsewhere in this file, rather than mutating one that
            # went through init (the Store's write-once transition guard
            # refuses a live context's leader identity changing underfoot). --
            import validate_orchestrator_store_contract as seed
            legacy_context = seed.ORCHESTRATION_CONTEXT()
            legacy_context["leader"]["session_ref"] = "orca:legacy-worker-1"
            legacy_item = seed.ORCHESTRATION_ITEM({"ctx-1": legacy_context})
            def add_legacy_item(document):
                document["agent_orchestration"]["work_items"]["work-not-observable"] = legacy_item
                return document
            store.transact(root, add_legacy_item)
            assert_refused_and_unwritten("work-not-observable", "orca:ctx-new-unobservable", "TAKEOVER-NOT-OBSERVABLE")

            # -- specialist activity still in flight refuses even a terminal observation. --
            active_context_id = spawn("work-active")
            active_policy_sha256 = store.read_snapshot(root).document["agent_orchestration"][
                "work_items"]["work-active"]["policy_sha256"]
            activity = seed.ORCHESTRATION_ACTIVITY("activity-live")
            activity.update(context_id=active_context_id, state="BOOTSTRAPPING", policy_sha256=active_policy_sha256)
            def add_activity(document):
                document["agent_orchestration"]["work_items"]["work-active"]["activities"]["activity-live"] = activity
                return document
            store.transact(root, add_activity)
            assert_refused_and_unwritten("work-active", "orca:ctx-new-work", "TAKEOVER-WORK-ACTIVE",
                takeover_show(old_dispatch, status="completed"))

            # -- a reread hash mismatch on --apply refuses without writing. --
            spawn("work-stale")
            env, transport = observing(takeover_show(old_dispatch, status="completed",
                liveness={"verdict": "live", "source": "agent_status"}))
            with env, transport:
                code, preview = takeover("work-stale", "orca:ctx-new-stale")
                self.assertEqual(code, 0, preview)
                before = store.read_snapshot(root).content_sha256
                code, blocked = takeover("work-stale", "orca:ctx-new-stale", "--apply", "--expected-sha256", "0" * 64)
                self.assertEqual((code, blocked.get("code")), (2, "TAKEOVER-INPUTS-STALE"), blocked)
                self.assertEqual(store.read_snapshot(root).content_sha256, before)

            # -- R2-4/T027: the applied takeover projects what stays pinned
            # under the superseded context. The filters are the point: a
            # CLOSED resource and a settled operation must NOT appear, so a
            # projection reverted to {} (or dropped from the payload) fails
            # here instead of passing the whole suite green. --
            projection_context_id = spawn("work-projection")
            projection_policy = store.read_snapshot(root).document["agent_orchestration"][
                "work_items"]["work-projection"]["policy_sha256"]
            # DECLARED is quiescent (_continuity_quiescence), so the resources
            # below get a creation binding without refusing the takeover.
            projection_activity = seed.ORCHESTRATION_ACTIVITY("activity-projection")
            projection_activity.update(context_id=projection_context_id, policy_sha256=projection_policy)
            kept_resource = seed.ORCHESTRATION_RESOURCE("resource-kept")
            kept_resource.update(origin_context_id=projection_context_id, activity_id="activity-projection", state="REGISTERED")
            closed_resource = seed.ORCHESTRATION_RESOURCE("resource-closed")
            closed_resource.update(origin_context_id=projection_context_id, activity_id="activity-projection", state="CLOSED")
            kept_operation = seed.ORCHESTRATION_OPERATION("op-kept", context_id=projection_context_id)
            settled_operation = seed.ORCHESTRATION_OPERATION("op-settled", context_id=projection_context_id,
                                                             result_sha256="f" * 64)
            settled_operation.update(state="CONFIRMED", observation_ref="receipts/op-settled")
            def add_projection(document):
                target = document["agent_orchestration"]["work_items"]["work-projection"]
                target["activities"]["activity-projection"] = copy.deepcopy(projection_activity)
                target["resources"].update({"resource-kept": copy.deepcopy(kept_resource),
                                            "resource-closed": copy.deepcopy(closed_resource)})
                target["operations"].update({"op-kept": copy.deepcopy(kept_operation),
                                             "op-settled": copy.deepcopy(settled_operation)})
                return document
            store.transact(root, add_projection)
            env, transport = observing(takeover_show(old_dispatch, status="completed"))
            with env, transport:
                code, preview = takeover("work-projection", "orca:ctx-new-projection")
                self.assertEqual(code, 0, preview)
                code, projected = takeover("work-projection", "orca:ctx-new-projection", "--apply",
                                           "--expected-sha256", preview["expected_sha256"])
            self.assertEqual((code, projected.get("verdict")), (0, "TAKEOVER-APPLIED"), projected)
            self.assertEqual(projected["preserved_resources"], {"resource-kept": kept_resource})
            self.assertEqual(projected["operations_to_reconcile"], {"op-kept": kept_operation})

            # -- R2-5/T027: the revision guard at the top of mutate. The whole
            # verdict is computed from a snapshot read outside the lock; when
            # the document moved between that read and the commit, the
            # takeover refuses instead of committing over the newer state.
            # Same seam the resume sibling's CONTINUITY-CAS-CONFLICT uses. --
            store_module = grill_workspace.grill_core_module("store")
            spawn("work-cas")
            env, transport = observing(takeover_show(old_dispatch, status="completed"))
            with env, transport:
                code, preview = takeover("work-cas", "orca:ctx-new-cas")
                self.assertEqual(code, 0, preview)
                before = store.read_snapshot(root).content_sha256
                real = store_module.read_snapshot(root)
                stale = store_module.Snapshot(document=real.document, revision=real.revision - 1,
                    content_sha256=real.content_sha256, project_id=real.project_id, path=real.path)
                with mock.patch.object(store_module, "read_snapshot", return_value=stale):
                    code, blocked = takeover("work-cas", "orca:ctx-new-cas", "--apply",
                                             "--expected-sha256", preview["expected_sha256"])
                self.assertEqual((code, blocked.get("code")), (2, "TAKEOVER-CAS-CONFLICT"), blocked)
            self.assertEqual(store.read_snapshot(root).content_sha256, before)

            # -- an identical, already-applied request short-circuits: no re-observation. --
            before = store.read_snapshot(root).content_sha256
            with guarded_run(None):
                for tail in ((), ("--apply", "--expected-sha256", "0" * 64)):
                    code, reused = takeover(applied_work_id, applied_session, *tail)
                    self.assertEqual((code, reused.get("verdict")), (0, "TAKEOVER-REUSED"), reused)
            self.assertEqual(store.read_snapshot(root).content_sha256, before)

    def test_orchestration_adopt_preview_matches_apply_when_context_fenced(self):
        """T006/T007: a preview against a work item already bound to another
        observed leader refuses CONTEXT-FENCED exactly like --apply would, and
        writes nothing either way (contracts/context-takeover.md parity note)."""
        temp, root = self.fixture()
        with temp, orchestration_fixture.offline_leader(grill_workspace):
            code, created = self.run_cli("init", str(root), "--type", "feature", "--slug", "x", "--work-id", "work-x",
                "--runtime", "codex", "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, created)
            args = ("gauntlet-orchestration-adopt", str(root), "--work-id", "work-x", "--runtime", "codex",
                    "--session-ref", orchestration_fixture.SESSION, "--scope-file", "src/a.py")
            code, preview = self.run_cli(*args)
            self.assertEqual(code, 0, preview)
            code, adopted = self.run_cli(*args, "--apply", "--expected-sha256", preview["expected_sha256"])
            self.assertEqual((code, adopted.get("verdict")), (0, "ORCHESTRATION-ADOPTED"), adopted)
            before = store.read_snapshot(root).content_sha256
            other = ("gauntlet-orchestration-adopt", str(root), "--work-id", "work-x", "--runtime", "codex",
                     "--session-ref", "orca:ctx-other-leader", "--scope-file", "src/a.py")
            for tail in ((), ("--apply", "--expected-sha256", "0" * 64)):
                code, fenced = self.run_cli(*other, *tail)
                self.assertEqual((code, fenced.get("code")), (2, "CONTEXT-FENCED"), fenced)
            self.assertEqual(store.read_snapshot(root).content_sha256, before)

    def test_orchestration_adopt_preview_matches_apply_when_origin_changed(self):
        """T066/FR-011: `_adoption_conflict` (grill_workspace.py) mirrors the
        apply closure's origin-changed branch so the preview raises the same
        refusal the apply would -- but the only existing preview/apply parity
        case (test_orchestration_adopt_preview_matches_apply_when_context_fenced,
        above) covers CONTEXT-FENCED only. The origin-changed invariant this
        delivery built was proven only by eyeballing the two branches stay in
        lockstep, never by a test: that is exactly what let a main-branch
        merge loosen `_adoption_conflict` without either the preview or the
        suite noticing, and the suite only caught it because a case coming
        from main happened to exercise this path (converge round 21).

        Both sides of the branch: origin changed together with a changed
        scope (or no current context) refuses identically on preview and
        apply; origin changed with the scope unchanged and a current context
        accepts on both, with the very same context_id.

        Verified by mutation: deleting the origin-changed `raise` in
        `_adoption_conflict` (grill_workspace.py ~1772) makes the "both
        refuse" half fail -- preview returns PREVIEW/exit 0 where apply still
        refuses ORCHESTRATION-POLICY-STALE.
        """
        temp, root = self.fixture()
        with temp, orchestration_fixture.offline_leader(grill_workspace):
            code, created = self.run_cli("init", str(root), "--type", "feature", "--slug", "x", "--work-id", "work-x",
                "--runtime", "codex", "--session-ref", orchestration_fixture.SESSION, "--skip-backlog")
            self.assertEqual(code, 0, created)
            args = ("gauntlet-orchestration-adopt", str(root), "--work-id", "work-x", "--runtime", "codex",
                    "--session-ref", orchestration_fixture.SESSION, "--scope-file", "src/a.py")
            code, preview = self.run_cli(*args)
            self.assertEqual(code, 0, preview)
            code, adopted = self.run_cli(*args, "--apply", "--expected-sha256", preview["expected_sha256"])
            self.assertEqual((code, adopted.get("verdict")), (0, "ORCHESTRATION-ADOPTED"), adopted)
            changed_origin = {**preview["origin"], "state_sha256": "f" * 64}
            # -- both refuse: origin changed AND scope also changed. --
            before = store.read_snapshot(root).content_sha256
            refused = ("gauntlet-orchestration-adopt", str(root), "--work-id", "work-x", "--runtime", "codex",
                       "--session-ref", orchestration_fixture.SESSION, "--scope-file", "src/b.py")
            with mock.patch.object(grill_workspace, "_orchestration_origin", return_value=changed_origin):
                for tail in ((), ("--apply", "--expected-sha256", "0" * 64)):
                    code, blocked = self.run_cli(*refused, *tail)
                    self.assertEqual((code, blocked.get("code")), (2, "ORCHESTRATION-POLICY-STALE"), blocked)
            self.assertEqual(store.read_snapshot(root).content_sha256, before)
            # -- both accept: origin changed, scope unchanged, current context exists. --
            with mock.patch.object(grill_workspace, "_orchestration_origin", return_value=changed_origin):
                code, refresh = self.run_cli(*args)
                self.assertEqual((code, refresh.get("verdict")), (0, "PREVIEW"), refresh)
                code, refreshed = self.run_cli(*args, "--apply", "--expected-sha256", refresh["expected_sha256"])
            self.assertEqual((code, refreshed.get("verdict"), refreshed.get("context_id")),
                             (0, "ORCHESTRATION-ADOPTED", adopted["context_id"]), refreshed)

    def boundary(self, probe=None, after=None, release=None, adapter="orca", capabilities=None, calls=None):
        probe = probe or native_sources()
        after = after or native_sources(released=True)
        release = release or release_source()
        calls = calls if calls is not None else []
        return RuntimeBoundary(adapter, "orca:worker-show:ctx-1", capabilities or ORCA_CAPABILITIES, lambda: (calls.append("probe") or probe), lambda: (calls.append("observe") or probe), lambda: (calls.append("release") or release), lambda: (calls.append("readback") or after)), calls

    def verified(self):
        boundary, calls = self.boundary()
        return boundary, boundary.verified("gpt-6-astra", "high"), calls

    def accepted_specialist(self, activity_id, *, step="plan", scope="cycle", role="author",
                            author_ids=None, runtime="codex"):
        model, effort = agent_orchestration.specialist_pair(runtime, role)
        launch, show = native_sources(provider=runtime, model=model, effort=effort)
        after = native_sources(released=True, provider=runtime, model=model, effort=effort)
        boundary, _calls = self.boundary(probe=(launch, show), after=after)
        observed = boundary.verified(model, effort)
        manifest = {"files": [], "required_activity_ids": [], "author_activity_ids": author_ids or [],
                    "task_binding": None, "human_authorization": None}
        activity = agent_orchestration.new_activity(
            activity_id=activity_id, context_id="ctx-1", step_id=None if scope == "interview" else step,
            activity_scope=scope, activity_type=role, attempt=1, input_manifest=manifest,
            policy_sha256="a" * 64, write_files=[],
        )
        context = {"context_id": "ctx-1", "runtime": runtime, "leader": {"fence": 1}}
        activity = agent_orchestration.prepare_activity(activity, context)
        bootstrap = agent_orchestration.bootstrap_request(activity)
        activity = agent_orchestration.record_verified_activity(activity, observed)
        activity, payload = agent_orchestration.dispatch_activity(activity, context)
        result = {"ref": f"results/{activity_id}.json", "sha256": "b" * 64}
        output = {"files": [], "return_ref": result, "effect_ref": None}
        activity = agent_orchestration.record_activity_result(
            activity, result_ref=result["ref"], result_sha256=result["sha256"], output_manifest=output,
        )
        closed = boundary.close(observed)
        activity = agent_orchestration.accept_activity(
            activity, context=context, observation=closed, acceptance_ref=result["ref"],
        )
        return activity, bootstrap, payload, observed, closed, context

    def accepted_deterministic(self, activity_id, *, step="verify"):
        manifest = {"files": [], "required_activity_ids": [], "author_activity_ids": [],
                    "task_binding": None, "human_authorization": None}
        context = {"context_id": "ctx-1", "runtime": "codex", "leader": {"fence": 1}}
        activity = agent_orchestration.new_activity(
            activity_id=activity_id, context_id="ctx-1", step_id=step, activity_scope="cycle",
            activity_type="deterministic_check", attempt=1, input_manifest=manifest,
            policy_sha256="a" * 64, write_files=[],
        )
        activity = agent_orchestration.prepare_activity(activity, context)
        activity = agent_orchestration.record_verified_activity(activity)
        activity, payload = agent_orchestration.dispatch_activity(activity, context)
        result = {"ref": f"results/{activity_id}.json", "sha256": "b" * 64}
        output = {"files": [], "return_ref": result, "effect_ref": None}
        activity = agent_orchestration.record_activity_result(
            activity, result_ref=result["ref"], result_sha256=result["sha256"], output_manifest=output,
        )
        return agent_orchestration.accept_activity(
            activity, context=context, observation=None, acceptance_ref=result["ref"]), payload

    def test_accept_resumes_a_recorded_result_after_the_worker_is_released(self):
        temporary, root = self.fixture()
        with temporary, orchestration_fixture.offline_leader(grill_workspace):
            code, created = self.run_cli("init", str(root), "--work-id", "work-x", "--type", "feature",
                "--slug", "x", "--runtime", "codex", "--session-ref", orchestration_fixture.SESSION,
                "--skip-backlog")
            self.assertEqual(code, 0, created)
            snapshot = store.read_snapshot(root)
            item = snapshot.document["agent_orchestration"]["work_items"]["work-x"]
            context_id = item["current_context_id"]
            context = item["contexts"][context_id]
            manifest = {"files": [], "required_activity_ids": [], "author_activity_ids": [],
                        "task_binding": None, "human_authorization": None}
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (root / "result.md").write_text("done\n", encoding="utf-8")
            model, effort = agent_orchestration.specialist_pair("codex", "author")
            launch, show = native_sources(model=model, effort=effort)
            boundary, _calls = self.boundary(probe=(launch, show), after=native_sources(
                released=True, model=model, effort=effort))
            observed = boundary.verified(model, effort)
            activity = agent_orchestration.new_activity(activity_id="author-resume", context_id=context_id,
                step_id="checklist", activity_scope="cycle", activity_type="author", attempt=1,
                input_manifest=manifest, policy_sha256=item["policy_sha256"], write_files=[])
            activity = agent_orchestration.prepare_activity(activity, context)
            activity = agent_orchestration.record_verified_activity(activity, observed)
            resource_id, resource = agent_orchestration.session_resource(
                activity, observed, collected_at="2026-01-01T00:00:00Z")
            activity, _payload = agent_orchestration.dispatch_activity(activity, context)
            def add_activity(document):
                target = document["agent_orchestration"]["work_items"]["work-x"]
                target["activities"][activity["activity_id"]] = copy.deepcopy(activity)
                target["resources"][resource_id] = copy.deepcopy(resource)
                return document
            store.transact(root, add_activity)
            argv = ("gauntlet-activity", str(root), "--work-id", "work-x", "--context-id", context_id,
                    "--epoch", "1", "--session-ref", orchestration_fixture.SESSION,
                    "--activity-id", "author-resume", "--step", "checklist", "--scope", "cycle",
                    "--kind", "author", "--phase", "accept", "--input-manifest", "manifest.json",
                    "--result", "result.md")
            code, recorded = self.run_cli(*argv)
            self.assertEqual((code, recorded["verdict"]), (0, "RESULT-RECORDED"), recorded)
            closed = boundary.close(observed)
            (root / "closed.json").write_text(json.dumps(closed), encoding="utf-8")
            code, accepted = self.run_cli(*argv, "--observation", "closed.json")
            self.assertEqual((code, accepted["verdict"]), (0, "ACCEPTED"), accepted)
            saved = store.read_snapshot(root).document["agent_orchestration"]["work_items"]["work-x"]
            self.assertEqual(saved["activities"]["author-resume"]["state"], "ACCEPTED")
            self.assertEqual(saved["resources"][resource_id]["state"], "CLOSED")

    def test_specialist_admission(self):
        activity, bootstrap, payload, observed, closed, context = self.accepted_specialist("author-plan")
        self.assertEqual((activity["state"], activity["effective_model"], activity["effective_effort"]),
                         ("ACCEPTED", "gpt-6-astra", "xhigh"))
        self.assertEqual(bootstrap["transport"], "bootstrap")
        self.assertNotIn("input_manifest", bootstrap)
        self.assertNotIn("write_files", bootstrap)
        self.assertEqual((payload["activity_id"], payload["context_id"], payload["fence"]),
                         ("author-plan", "ctx-1", 1))
        self.assertEqual(payload["input_sha256"], activity["input_sha256"])

        wrong_effort = copy.deepcopy(closed); wrong_effort["effective_effort"] = "high"
        recorded = copy.deepcopy(activity); recorded["state"] = "RESULT_RECORDED"
        recorded["released_at"] = None; recorded["accepted_by_context"] = None
        recorded["acceptance_ref"] = None; recorded["review_verdict"] = None
        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "SPECIALIST-EFFORT-DIVERGENT"):
            agent_orchestration.accept_activity(recorded, context=context, observation=wrong_effort,
                                                acceptance_ref="results/author-plan.json")

        unclosed = copy.deepcopy(observed)
        provisional = copy.deepcopy(recorded)
        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "SESSION-CLOSE-UNPROVEN"):
            agent_orchestration.accept_activity(provisional, context=context, observation=unclosed,
                                                acceptance_ref="results/author-plan.json")

        malformed = copy.deepcopy(activity); malformed["state"] = "BOOTSTRAPPING"
        malformed["requested_effort"] = "high"
        malformed["effective_model"] = malformed["effective_effort"] = malformed["resolved_model_id"] = None
        malformed["session_resource_id"] = malformed["launch_observation_ref"] = None
        malformed["payload_sha256"] = malformed["result_ref"] = malformed["result_sha256"] = None
        malformed["output_manifest"] = malformed["released_at"] = None
        malformed["accepted_by_context"] = malformed["acceptance_ref"] = malformed["review_verdict"] = None
        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "SPECIALIST-CAPABILITY-UNPROVEN"):
            agent_orchestration.record_verified_activity(malformed, observed)

        author, _bootstrap, _payload, author_observed, _closed, _context = self.accepted_specialist("author-source")
        reviewer, _bootstrap, _payload, reviewer_observed, reviewer_closed, _context = self.accepted_specialist(
            "reviewer-source", role="reviewer", author_ids=["author-source"])
        _resource_id, author_resource = agent_orchestration.session_resource(
            author, author_observed, collected_at="2026-01-01T00:00:00Z")
        item = {"author-source": author, "reviewer-source": reviewer}
        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "REVIEWER-NOT-INDEPENDENT"):
            agent_orchestration.require_reviewer_independence(
                reviewer, reviewer_observed, activities=item, resources={author["session_resource_id"]: author_resource})

        independent = copy.deepcopy(reviewer_observed)
        independent.update({"handle": "term-review", "incarnation": "inc-review",
                            "dispatch_incarnation": "dispatch-inc-review", "owner_dispatch": "ctx-review",
                            "task_id": "task-review", "worktree_id": "worktree-review"})
        agent_orchestration.require_reviewer_independence(
            reviewer, independent, activities=item, resources={author["session_resource_id"]: author_resource})

        omitted = copy.deepcopy(reviewer); omitted["author_activity_ids"] = []
        omitted["input_manifest"]["author_activity_ids"] = []
        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "REVIEWER-NOT-INDEPENDENT"):
            agent_orchestration.require_reviewer_independence(
                omitted, independent, activities=item, resources={author["session_resource_id"]: author_resource})

        second_author, *_ = self.accepted_specialist("author-second")
        composite = copy.deepcopy(reviewer)
        composite["input_manifest"]["required_activity_ids"] = ["author-source", "author-second"]
        composite_item = {**item, "author-second": second_author}
        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "REVIEWER-NOT-INDEPENDENT"):
            agent_orchestration.require_reviewer_independence(
                composite, independent, activities=composite_item,
                resources={author["session_resource_id"]: author_resource})

        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "reviewer writes files"):
            agent_orchestration.new_activity(
                activity_id="reviewer-write", context_id="ctx-1", step_id="plan", activity_scope="cycle",
                activity_type="reviewer", attempt=1,
                input_manifest={"files": [], "required_activity_ids": [], "author_activity_ids": [],
                                "task_binding": None, "human_authorization": None},
                policy_sha256="a" * 64, write_files=["review.md"])

        recorded_review = copy.deepcopy(reviewer)
        recorded_review.update({"state": "RESULT_RECORDED", "released_at": None,
                                "accepted_by_context": None, "acceptance_ref": None, "review_verdict": None})
        stale = agent_orchestration.accept_activity(
            recorded_review, context=context, observation=reviewer_closed,
            acceptance_ref="results/reviewer-source.json", current_input_sha256="c" * 64)
        self.assertEqual(stale["review_verdict"], "STALE")

    def test_activity_coverage(self):
        policy = json.loads((SCRIPTS.parent / "assets/agent-orchestration.v1.json").read_text(encoding="utf-8"))
        author, _bootstrap, _payload, _observed, _closed, _context = self.accepted_specialist("author-plan")
        reviewer, *_ = self.accepted_specialist("reviewer-plan", role="reviewer", author_ids=["author-plan"])
        item = {"activities": {"author-plan": author, "reviewer-plan": reviewer}}
        missing = agent_orchestration.activity_coverage(item, policy, context_id="ctx-1", step_id="tasks")
        self.assertEqual(missing["missing"], ["author", "reviewer"])
        with self.assertRaises(attestation.AttestationError):
            attestation.require_activity_coverage(missing, step_id="tasks")

        author_tasks, *_ = self.accepted_specialist("author-tasks", step="tasks")
        reviewer_tasks, *_ = self.accepted_specialist("reviewer-tasks", step="tasks", role="reviewer", author_ids=["author-tasks"])
        author_specify, *_ = self.accepted_specialist("author-specify", step="specify")
        reviewer_specify, *_ = self.accepted_specialist("reviewer-specify", step="specify", role="reviewer", author_ids=["author-specify"])
        interview_author, *_ = self.accepted_specialist("author-interview", scope="interview")
        interview_reviewer, *_ = self.accepted_specialist("reviewer-interview", scope="interview", role="reviewer", author_ids=["author-interview"])
        item["activities"].update({
            "author-tasks": author_tasks, "reviewer-tasks": reviewer_tasks,
            "author-specify": author_specify, "reviewer-specify": reviewer_specify,
            "author-interview": interview_author, "reviewer-interview": interview_reviewer,
        })
        for kwargs in (
            {"step_id": "plan", "frontend": True}, {"step_id": "tasks"},
            {"step_id": "specify", "new_how": True},
            {"step_id": None, "activity_scope": "interview"},
        ):
            coverage = agent_orchestration.require_activity_coverage(item, policy, context_id="ctx-1", **kwargs)
            self.assertEqual(coverage["missing"], [])

        invocation = agent_orchestration.invocation_context(
            policy=policy, policy_sha256="c" * 64,
            context={"context_id": "ctx-1", "epoch": 1, "presentation": self.ready_presentation()},
            step_id="plan", canonical_entrypoint={"kind": "canonical"},
            supplement={"path": "supplement", "sha256": "d" * 64},
            task_template={"path": "template", "sha256": "e" * 64}, frontend=True,
        )
        self.assertEqual(invocation["limitation"], "context-delivery-is-not-skill-invocation")

        deterministic, deterministic_payload = self.accepted_deterministic("verify-gates")
        self.assertEqual((deterministic["runtime"], deterministic["requested_model"],
                          deterministic["requested_effort"], deterministic["review_verdict"]),
                         (None, None, None, "APPROVED"))
        self.assertIsNone(deterministic_payload["runtime"])
        review_only = agent_orchestration.activity_coverage(
            {"activities": {"verify-gates": deterministic}}, policy,
            context_id="ctx-1", step_id="review")
        self.assertEqual(review_only["missing"], ["reviewer"])

        matrix_item = {"activities": {}}
        matrix_cases = (
            ("specify", True), ("plan", False), ("checklist", False), ("tasks", False),
            ("analyze", True), ("partition", False), ("implement-parallel", True),
            ("converge", True), ("verify", True), ("review", False), ("ship", True),
        )
        for step_id, new_how in matrix_cases:
            roles = agent_orchestration.activity_requirements(
                policy, step_id=step_id, activity_scope="cycle", new_how=new_how)
            author_id = f"matrix-author-{step_id}"
            if "author" in roles or "reviewer" in roles:
                source_author, *_ = self.accepted_specialist(author_id, step=step_id)
                matrix_item["activities"][author_id] = source_author
            if "reviewer" in roles:
                reviewer_id = f"matrix-reviewer-{step_id}"
                source_reviewer, *_ = self.accepted_specialist(
                    reviewer_id, step=step_id, role="reviewer", author_ids=[author_id])
                matrix_item["activities"][reviewer_id] = source_reviewer
            coverage = agent_orchestration.require_activity_coverage(
                matrix_item, policy, context_id="ctx-1", step_id=step_id, new_how=new_how)
            self.assertEqual(coverage["missing"], [], step_id)

        changes_required = copy.deepcopy(reviewer_tasks); changes_required["review_verdict"] = "CHANGES_REQUIRED"
        stale = copy.deepcopy(reviewer_tasks); stale["review_verdict"] = "STALE"
        for verdict, review in (("CHANGES_REQUIRED", changes_required), ("STALE", stale)):
            coverage = agent_orchestration.activity_coverage(
                {"activities": {"author-tasks": author_tasks, "reviewer-tasks": review}}, policy,
                context_id="ctx-1", step_id="tasks")
            self.assertEqual(coverage["missing"], ["reviewer"])
            self.assertEqual(coverage[verdict.lower()], ["reviewer-tasks"])
            with self.assertRaises(attestation.AttestationError):
                attestation.require_activity_coverage(coverage, step_id="tasks")

    def test_native_bytes_prove_effective_pair_and_full_identity(self):
        boundary, observed, calls = self.verified()
        self.assertEqual(calls, ["probe", "observe"])
        self.assertEqual(observed["effective_model"], "gpt-6-astra")
        self.assertEqual(observed["effective_effort"], "high")
        self.assertEqual(observed["incarnation"], "inc-1")
        self.assertEqual(observed["dispatch_incarnation"], "dispatch-inc-1")
        self.assertEqual(observed["task_id"], "task-1")
        self.assertEqual(observed["worktree_id"], "worktree-1")

    def test_failed_released_dispatch_is_closed(self):
        launch, show = native_sources(released=True)
        failed = json.loads(show)
        failed["result"]["dispatch"]["status"] = "failed"
        failed["result"]["worker"]["state"] = "failed"
        observed = grill_workspace.grill_core_module("agent_runtime")._orca_observation(
            "orca:worker-show:ctx-1", launch, pack(failed))
        self.assertEqual((observed["close"], observed["activity"]), ("closed", "exited"))

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

    def test_task_phase_barriers_and_migration_are_hash_fenced(self):
        semantic, dag_hash = "a" * 64, "b" * 64
        tasks = [{"task_id": "T001", "phase": 1}, {"task_id": "T002", "phase": 2}]
        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "TASK-PHASE-PENDING"):
            agent_orchestration.require_task_phase_barrier(
                tasks, {}, target_phase=2, tasks_semantic_sha256=semantic, dag_content_sha256=dag_hash)
        accepted = {"T001": {"state": "ACCEPTED", "task_binding": {
            "task_id": "T001", "phase": "1", "tasks_semantic_sha256": semantic,
            "dag_content_sha256": dag_hash,
        }}}
        agent_orchestration.require_task_phase_barrier(
            tasks, accepted, target_phase=2, tasks_semantic_sha256=semantic, dag_content_sha256=dag_hash)
        guard = gauntlet_runs.task_phase_barrier(
            {"schema": gauntlet_runs.DAG_V2_SCHEMA, "tasks_semantic_sha256": semantic,
             "accepted_tasks": accepted},
            {"schema": "grill-partition-report/v2", "phases": [{"phase": 1, "task_ids": ["T001"]}]},
            target_phase=2, dag_content_sha256=dag_hash)
        self.assertEqual(guard["pending"], [])
        external = gauntlet_runs.task_phase_barrier(
            {"schema": gauntlet_runs.DAG_V2_SCHEMA, "tasks_semantic_sha256": semantic,
             "accepted_tasks": {}},
            {"schema": "grill-partition-report/v2", "phases": [{"phase": 1, "task_ids": ["T001"]}]},
            target_phase=2, dag_content_sha256=dag_hash, accepted_tasks=accepted)
        self.assertEqual(external["pending"], [])
        current = "- [X] T001 old\n"
        proposal = "<!-- grill-task-files:v1 -->\n- [X] T001 old\n"
        preview = agent_orchestration.task_files_migration_preview(
            current, proposal, expected_sha256=__import__("hashlib").sha256(current.encode()).hexdigest(),
            accepted_task_ids=["T001"])
        self.assertEqual(preview["preserved_task_ids"], ["T001"])
        with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "TASKS-SOURCE-STALE"):
            agent_orchestration.task_files_migration_preview(current, proposal, expected_sha256="0" * 64)

        # Every mutable scheduler entrance must reject an unfinished prior
        # phase before its own core can see the request. The CLI boundary uses
        # its admission seam, so this regression creates no live run or worker.
        record = {
            "workflow": {"version": "v4"},
            "tier_policy": {"minimum_by_step": {"implement-parallel": "medium"},
                            "supplemental": {"markdown-maintenance": "small"}},
            "limits": {"max_workers": 1, "stall_minutes": 15},
            "runtime": {"id": "codex"},
        }
        boundaries = (
            (grill_workspace.gauntlet_wave_declare_command.__wrapped__, "declare_wave",
             SimpleNamespace(root=".", work_id="work", run_id="run", dag="dag.json", node_id=["p02-a"])),
            (grill_workspace.gauntlet_worker_declare_command.__wrapped__, "declare_worker",
             SimpleNamespace(root=".", work_id="work", run_id="run", wave_id="wave-0001", node_id="p02-a",
                             tier="medium", files=["src/a.py"], dag="dag.json")),
            (grill_workspace.gauntlet_prepare_worker_command.__wrapped__, "prepare_worker",
             SimpleNamespace(root=".", work_id="work", run_id="run", worker_id="p02-a", scope=["src/a.py"])),
            (grill_workspace.gauntlet_remediate_command.__wrapped__, "remediate_node",
             SimpleNamespace(root=".", work_id="work", run_id="run", worker_id="p02-a", reason="stall")),
        )
        for command, core_action, args in boundaries:
            with self.subTest(boundary=core_action), \
                 mock.patch.object(grill_workspace, "gauntlet_run_admission",
                                   return_value=(Path("."), gauntlet_runs, {}, record)), \
                 mock.patch.object(grill_workspace, "_scheduler_accepted_tasks", return_value={}), \
                 mock.patch.object(gauntlet_runs, "task_phase_barrier",
                                   side_effect=gauntlet_runs.GauntletRunError("TASK-PHASE-PENDING", "T001")) as guard, \
                 mock.patch.object(gauntlet_runs, core_action,
                                   side_effect=AssertionError(f"{core_action} bypassed task phase barrier")):
                with self.assertRaises(grill_workspace.CliFailure) as blocked:
                    command(args)
                self.assertEqual(blocked.exception.code, "TASK-PHASE-PENDING")
                guard.assert_called_once()

    def test_visual_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            html = b"<!doctype html><html><body>preview</body></html>"
            png = b"\x89PNG\r\n\x1a\nminimal"
            (root / "design.html").write_bytes(html)
            (root / "wide.png").write_bytes(png)
            digest = lambda raw: __import__("hashlib").sha256(raw).hexdigest()
            files = [
                {"path": "design.html", "media_type": "text/html", "sha256": digest(html), "size": len(html)},
                {"path": "wide.png", "media_type": "image/png", "sha256": digest(png), "size": len(png)},
            ]
            author = {"state": "ACCEPTED", "activity_type": "author", "context_id": "ctx", "step_id": "plan",
                      "runtime": "codex", "requested_model": "gpt-6-astra", "requested_effort": "xhigh",
                      "effective_model": "gpt-6-astra", "effective_effort": "xhigh", "resolved_model_id": "gpt-6-astra",
                      "session_resource_id": "author-session", "output_manifest": {"files": files}, "acceptance_ref": "author-receipt"}
            reviewer = {"state": "ACCEPTED", "activity_type": "reviewer", "context_id": "ctx", "step_id": "plan",
                        "runtime": "codex", "requested_model": "gpt-6-astra", "requested_effort": "high",
                        "effective_model": "gpt-6-astra", "effective_effort": "high", "resolved_model_id": "gpt-6-astra",
                        "session_resource_id": "reviewer-session", "input_manifest": {"files": files},
                        "author_activity_ids": ["design-author"], "review_verdict": "APPROVED", "acceptance_ref": "review-receipt"}
            manifest = {
                "schema": "grill-design-preview/v1", "feature": "030-agent-orchestration", "phase": "plan", "du": "DU-001",
                "classification": {source: {"development_type": "frontend", "visual_surface": True}
                                   for source in ("handoff", "du", "plan_context")},
                "input_sha256": "a" * 64,
                "impeccable": {"schema": "grill-impeccable-observation/v1", "capability": "impeccable",
                               "skill_path": "/observed/impeccable/SKILL.md", "version": "1.0.0", "skill_sha256": "b" * 64,
                               "entrypoint": "$impeccable", "invocation_ref": "session-call-1", "invocation_sha256": "c" * 64},
                "author_activity_id": "design-author", "review_activity_id": "design-review",
                "files": files, "entrypoint": "design.html", "captures": [{"viewport": "1280x800", "state": "default", "path": "wide.png"}],
            }
            preview = agent_orchestration.inspect_visual_preview(
                manifest, preview_sha256=digest(pack(manifest)), context_id="ctx",
                activities={"design-author": author, "design-review": reviewer},
                read_file=lambda path: (root / path).read_bytes())
            self.assertEqual(preview["state"], "REVIEWED")
            self.assertEqual(agent_orchestration.visual_gate_state({}, preview, decision=None), "PENDING_APPROVAL")
            decision = {"preview_sha256": preview["preview_sha256"], "review_ref": preview["review_ref"], "decision": "approved"}
            self.assertEqual(agent_orchestration.visual_gate_state({}, preview, decision=decision), "APPROVED")
            brief = copy.deepcopy(manifest); brief["files"][0]["sha256"] = digest(b"brief")
            (root / "design.html").write_bytes(b"brief")
            with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "PREVIEW-STALE"):
                agent_orchestration.inspect_visual_preview(brief, preview_sha256=digest(pack(brief)), context_id="ctx",
                    activities={"design-author": author, "design-review": reviewer}, read_file=lambda path: (root / path).read_bytes())
            (root / "design.html").write_bytes(html)
            missing_capture = copy.deepcopy(manifest); missing_capture["captures"] = []
            with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "PREVIEW-NOT-VISUAL"):
                agent_orchestration.inspect_visual_preview(missing_capture, preview_sha256=digest(pack(missing_capture)), context_id="ctx",
                    activities={"design-author": author, "design-review": reviewer}, read_file=lambda path: (root / path).read_bytes())
            invalid_reviewer = copy.deepcopy(reviewer); invalid_reviewer["session_resource_id"] = "author-session"
            with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "REVIEWER-NOT-INDEPENDENT"):
                agent_orchestration.inspect_visual_preview(manifest, preview_sha256=digest(pack(manifest)), context_id="ctx",
                    activities={"design-author": author, "design-review": invalid_reviewer}, read_file=lambda path: (root / path).read_bytes())
            contradictory = copy.deepcopy(manifest); contradictory["classification"]["du"] = {"development_type": "platform-devops", "visual_surface": False}
            with self.assertRaisesRegex(agent_orchestration.OrchestrationError, "FRONTEND-CLASSIFICATION-DIVERGENT"):
                agent_orchestration.inspect_visual_preview(contradictory, preview_sha256=digest(pack(contradictory)), context_id="ctx",
                    activities={"design-author": author, "design-review": reviewer}, read_file=lambda path: (root / path).read_bytes())
            not_applicable = copy.deepcopy(manifest)
            not_applicable["classification"] = {source: {"development_type": "platform-devops", "visual_surface": False}
                                                for source in ("handoff", "du", "plan_context")}
            not_applicable.update({"impeccable": None, "author_activity_id": None, "review_activity_id": None,
                                   "files": [], "entrypoint": None, "captures": []})
            status = agent_orchestration.inspect_visual_preview(not_applicable, preview_sha256=digest(pack(not_applicable)),
                context_id="ctx", activities={}, read_file=lambda _path: b"")
            self.assertEqual((status["state"], agent_orchestration.visual_gate_state({}, status, decision=None)),
                             ("NOT_APPLICABLE", "NOT_APPLICABLE"))


if __name__ == "__main__":
    unittest.main()
