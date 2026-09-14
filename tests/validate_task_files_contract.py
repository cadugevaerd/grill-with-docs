#!/usr/bin/env python3
"""Offline checks for migration's specialist and public authority boundary."""
import copy
import contextlib
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugin/skills/grill-with-docs/scripts"))
import grill_workspace
from grill_core import agent_orchestration as contract
import validate_agent_orchestration_contract as fixtures


class TaskFilesContract(unittest.TestCase):
    def evidence(self):
        fixture = fixtures.AgentOrchestrationContract()
        proposal = {"path": "specs/030-demo/proposal.md", "sha256": hashlib.sha256(b"proposal").hexdigest(),
                    "size": 8, "media_type": "text/markdown"}
        activities, resources = {}, {}
        for role in ("author", "reviewer"):
            activity, _, _, observed, _, _ = fixture.accepted_specialist(
                role, role=role, step="tasks", author_ids=["author"] if role == "reviewer" else [])
            observed = copy.deepcopy(observed)
            observed.update(handle="term-" + role, incarnation="inc-" + role)
            resource_id, resource = contract.session_resource(activity, observed, collected_at="2026-01-01T00:00:00Z")
            if role == "author":
                activity["write_files"] = [proposal["path"]]
                activity["output_manifest"]["files"] = [proposal]
            else:
                activity["input_manifest"]["files"] = [proposal]
            activities[role], resources[resource_id] = activity, resource
        return {"activities": activities, "resources": resources, "policy_sha256": "a" * 64}, proposal

    def test_migration_requires_current_specialists_and_independent_review(self):
        item, proposal = self.evidence()
        def verify(candidate):
            return contract.require_task_files_review(candidate, context_id="ctx-1", author_id="author",
                                                       reviewer_id="reviewer", proposal=proposal)
        verify(item)
        cases = (
            ("author", "state", "RESULT_RECORDED", "ACTIVITY-REQUIRED"),
            ("author", "context_id", "ctx-old", "ACTIVITY-REQUIRED"),
            ("author", "effective_effort", "high", "SPECIALIST-CAPABILITY-UNPROVEN"),
            ("reviewer", "review_verdict", "CHANGES_REQUIRED", "ACTIVITY-REQUIRED"),
            ("reviewer", "author_activity_ids", [], "REVIEWER-NOT-INDEPENDENT"),
        )
        for role, key, value, code in cases:
            candidate = copy.deepcopy(item)
            candidate["activities"][role][key] = value
            with self.subTest(role=role, key=key), self.assertRaisesRegex(contract.OrchestrationError, code):
                verify(candidate)
        for role, field in (("author", "output_manifest"), ("reviewer", "input_manifest")):
            candidate = copy.deepcopy(item)
            candidate["activities"][role][field]["files"][0]["sha256"] = "0" * 64
            with self.assertRaisesRegex(contract.OrchestrationError, "TASKS-SOURCE-STALE"):
                verify(candidate)
        candidate = copy.deepcopy(item)
        author_resource = candidate["resources"][candidate["activities"]["author"]["session_resource_id"]]
        reviewer_resource = candidate["resources"][candidate["activities"]["reviewer"]["session_resource_id"]]
        reviewer_resource["identity"] = copy.deepcopy(author_resource["identity"])
        with self.assertRaisesRegex(contract.OrchestrationError, "REVIEWER-NOT-INDEPENDENT"):
            verify(candidate)

    def test_public_migration_selectors(self):
        args = grill_workspace.build_parser().parse_args([
            "task-files-migrate", ".", "--work-id", "wx", "--feature", "030-demo",
            "--proposal", "specs/030-demo/proposal.md", "--context-id", "ctx-1", "--epoch", "1",
            "--session-ref", "session-1", "--author-activity", "author", "--review-activity", "reviewer"])
        self.assertEqual((args.context_id, args.epoch, args.session_ref, args.author_activity, args.review_activity),
                         ("ctx-1", 1, "session-1", "author", "reviewer"))

    def test_migration_preview_apply_rechecks_authority_and_bytes(self):
        temporary, root = fixtures.AgentOrchestrationContract().fixture()
        with temporary:
            directory = root / "specs/030-demo"
            directory.mkdir(parents=True)
            current = directory / "tasks.md"
            current.write_text("## Phase 1: Test\n\n- [ ] T001 Check\n")
            proposal = directory / "proposal.md"
            proposal.write_text('<!-- grill-task-files:v1 -->\n## Phase 1: Test\n\n- [ ] T001 Check\n  Files: []\n')
            item, file = self.evidence()
            file.update(sha256=hashlib.sha256(proposal.read_bytes()).hexdigest(), size=len(proposal.read_bytes()))
            item["activities"]["author"]["output_manifest"]["files"] = [file]
            item["activities"]["reviewer"]["input_manifest"]["files"] = [file]
            for activity in item["activities"].values():
                result = root / activity["result_ref"]
                result.parent.mkdir(exist_ok=True)
                result.write_bytes(b"accepted result")
                activity["result_sha256"] = hashlib.sha256(result.read_bytes()).hexdigest()
            context = {"context_id": "ctx-1", "epoch": 1, "state": "ACTIVE",
                       "leader": {"state": "ACTIVE", "session_ref": "session-1"}}
            item.update(current_context_id="ctx-1", contexts={"ctx-1": context}, operations={})
            document = {"agent_orchestration": {"work_items": {"wx": item}}}
            def authority(_root, work_id, context_id, epoch, session_ref):
                try:
                    contract.require_authority(item, context_id, epoch, session_ref)
                except contract.OrchestrationError as exc:
                    raise grill_workspace.CliFailure(2, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
                return fixtures.store, contract, document, item, context
            fixtures.store.bootstrap(root)
            argv = ["task-files-migrate", str(root), "--work-id", "wx", "--feature", "030-demo",
                    "--proposal", file["path"], "--context-id", "ctx-1", "--epoch", "1",
                    "--session-ref", "session-1", "--author-activity", "author", "--review-activity", "reviewer"]
            def cli(*tail):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = grill_workspace.main(argv + list(tail))
                return code, json.loads(out.getvalue())
            with mock.patch.object(grill_workspace, "resolve_gauntlet_subject"), mock.patch.object(
                    grill_workspace, "_activity_policy", side_effect=authority):
                before = current.read_bytes()
                code, preview = cli()
                self.assertEqual(code, 0, preview)
                self.assertEqual(current.read_bytes(), before)
                self.assertEqual(cli("--apply", "--expected-sha256", "0" * 64)[1]["code"], "TASKS-SOURCE-STALE")
                context["epoch"] = 2
                self.assertEqual(cli("--apply", "--expected-sha256", preview["expected_sha256"])[1]["code"], "LEADER-AUTHORITY-UNPROVEN")
                context["epoch"] = 1
                self.assertEqual(current.read_bytes(), before)
                code, applied = cli("--apply", "--expected-sha256", preview["expected_sha256"])
                self.assertEqual((code, applied.get("verdict")), (0, "APPLIED"), applied)
                self.assertEqual(current.read_bytes(), proposal.read_bytes())


if __name__ == "__main__":
    unittest.main()
