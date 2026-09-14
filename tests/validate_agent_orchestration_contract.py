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


class AgentOrchestrationContract(unittest.TestCase):
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
            loaded = presentation_state(**kwargs, loading={"evidence_kind": "full_read", "event_ref": "tool-read-1",
                "event_sha256": "e" * 64, "session_identity": "session-1", "config_fingerprint": "config-1",
                "scope": kwargs["scope"], "skill_sha256": request["skill_sha256"], "body_sha256": request["body_sha256"]})
            self.assertEqual((loaded["loading"], loaded["use_ready"], loaded["work_ready"],
                              loaded["behavior"], loaded["functional_verified"]),
                             ("loaded", True, True, "not_tested", False))
            for changed in ({"session_identity": "other"}, {"config_fingerprint": "other"},
                            {"evidence_kind": "exit_0"}, {"scope": {"kind": "gwd"}}):
                invalid = {"evidence_kind": "full_read", "event_ref": "tool-read-1", "event_sha256": "e" * 64,
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
            active = presentation_state(**kwargs, loading={"evidence_kind": "full_read", "event_ref": "read-1",
                "event_sha256": "e" * 64, "session_identity": "session-1", "config_fingerprint": "config-1",
                "scope": kwargs["scope"], "skill_sha256": request["skill_sha256"], "body_sha256": request["body_sha256"]})
            self.assertTrue(active["use_ready"])

    def test_presentation_scope_preservation(self):
        temporary, _reference, kwargs = self.presentation_fixture()
        with temporary:
            pending = presentation_state(**kwargs)
            request = pending["load_request"]
            presentation = presentation_state(**kwargs, loading={"evidence_kind": "full_read", "event_ref": "read-1",
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
                code, entered = self.run_cli(
                    "gauntlet-step-enter", str(root), "--work-id", "work-x", "--context-id", adopted["context_id"],
                    "--epoch", "1", "--session-ref", "observed-session", "--step", "implement-parallel")
                self.assertEqual(code, 0)
                invocation = entered["invocation_context"]
                self.assertEqual(invocation["canonical_entrypoint"]["entrypoint"], "grill-with-docs:grill-implement-parallel")
                for key, path in (("supplement", "references/agent-orchestration.md"),
                                  ("task_template", "assets/task-files.v1.template.md")):
                    body = (SCRIPTS.parent / path).read_bytes()
                    self.assertEqual(invocation[key], {
                        "path": f"plugin/skills/grill-with-docs/{path}",
                        "sha256": __import__("hashlib").sha256(body).hexdigest(),
                    })
                checkpoint_args = ("checkpoint", str(root), "--work-id", "work-x", "--step", "specify", "--state", "in-progress", "--operation-id", "checkpoint-1", "--session-ref", "observed-session")
                code, checkpoint = self.run_cli(*checkpoint_args)
                self.assertEqual((code, checkpoint["code"]), (2, "ACTIVITY-REQUIRED"))
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
            policy=policy, policy_sha256="c" * 64, context={"context_id": "ctx-1", "epoch": 1},
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
