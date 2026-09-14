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


if __name__ == "__main__":
    unittest.main()
