#!/usr/bin/env python3
"""Focused cleanup lifecycle checks for feature 030."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "plugin/skills/grill-with-docs/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from grill_core import gauntlet_runs
from grill_core import agent_orchestration


class AgentOrchestrationContract(unittest.TestCase):
    def test_cleanup_lifecycle(self) -> None:
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
        with patch.object(gauntlet_runs, "_require_base_commit"), patch.object(
            gauntlet_runs, "_read_runs", return_value={"run-cleanup": run}
        ):
            self.assertIs(gauntlet_runs._run_for_worker(
                ".", "work", "run-cleanup", run["admission"], purpose="cleanup"
            ), run)

    def test_failed_or_unproven_cleaned_worker_never_unblocks_dependency(self) -> None:
        for state, converged in (("FAILED", True), ("CLEANED", False)):
            with self.subTest(state=state, converged=converged):
                run = {"workers": {"T006": {"state": state, "node_id": "T006", "remediates": None,
                                                "workspace": {"converged": converged}}}}
                self.assertFalse(gauntlet_runs._node_ready(run, "T006"))
                self.assertFalse(gauntlet_runs._converged_lineage_head(run, "T006"))

    def test_resource_cleanup_requires_current_facts(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
