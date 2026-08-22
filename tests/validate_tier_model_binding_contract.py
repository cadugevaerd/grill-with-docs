#!/usr/bin/env python3
"""Public contract for the tier -> model binding (ADR-0001, ADR-0013).

The point of this file is that "workers must not use a frontier model" stops
being prose. Every assertion below is about a *policy invariant* rather than a
model string, with two deliberate exceptions: the shipped asset's own model ids
are pinned, because a silent edit there changes which model runs real work and
must show up as a failing test rather than as a quieter invoice.

No network, no subprocess: the module reads one asset and answers questions.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin/skills/grill-with-docs"
SCRIPTS = SKILL / "scripts"
ASSET = SKILL / "assets/workflow-tier-models.json"
AGENTS = REPO / "plugin/agents"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from grill_core import tier_models as T  # noqa: E402
from grill_core import workflow_versions as wv  # noqa: E402

TIERS = ("small", "medium", "large")
#: Pinned on purpose -- see module docstring.
EXPECTED_MODELS = {
    "claude": {"small": "haiku", "medium": "sonnet", "large": "opus"},
    "codex": {"small": "gpt-5.6-luna", "medium": "gpt-5.6-terra", "large": "gpt-5.6-sol"},
}
FRONTMATTER_MODEL_RE = re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE)


class Shape(unittest.TestCase):
    def setUp(self) -> None:
        self.binding = T.load_binding()

    def test_the_shipped_asset_loads(self) -> None:
        self.assertEqual(self.binding["schema"], T.SCHEMA)

    def test_the_binding_declares_the_v4_workflow(self) -> None:
        self.assertEqual(self.binding["workflow_version"], "v4")

    def test_tier_order_matches_the_core_tier_vocabulary(self) -> None:
        self.assertEqual(tuple(self.binding["tier_order"]), TIERS)

    def test_every_resolved_runtime_covers_every_tier(self) -> None:
        for name in T.resolved_runtimes(self.binding):
            with self.subTest(runtime=name):
                self.assertEqual(set(self.binding["runtimes"][name]["tiers"]), set(TIERS))

    def test_claude_and_codex_are_both_resolved(self) -> None:
        self.assertEqual(T.resolved_runtimes(self.binding), ("claude", "codex"))

    def test_an_unresolved_runtime_declares_why(self) -> None:
        hermes = self.binding["runtimes"]["hermes"]
        self.assertFalse(hermes["resolved"])
        self.assertEqual(hermes["unresolved_reason"], "RUNTIME_ENTRYPOINT_UNPROVEN")

    def test_the_shipped_model_ids_are_pinned(self) -> None:
        for runtime, tiers in EXPECTED_MODELS.items():
            for tier, model in tiers.items():
                with self.subTest(runtime=runtime, tier=tier):
                    self.assertEqual(self.binding["runtimes"][runtime]["tiers"][tier]["model"], model)

    def test_no_placeholder_survives_in_a_resolved_runtime(self) -> None:
        for name in T.resolved_runtimes(self.binding):
            for tier, entry in self.binding["runtimes"][name]["tiers"].items():
                with self.subTest(runtime=name, tier=tier):
                    self.assertFalse(entry["model"].startswith("__"))

    def test_every_resolved_runtime_documents_how_a_model_is_selected(self) -> None:
        for name in T.resolved_runtimes(self.binding):
            with self.subTest(runtime=name):
                self.assertTrue(self.binding["runtimes"][name]["selection"].strip())


class Policy(unittest.TestCase):
    """Invariants, not strings. These must hold for any future runtime."""

    def setUp(self) -> None:
        self.binding = T.load_binding()

    def test_only_the_largest_tier_is_ever_frontier(self) -> None:
        for name in T.resolved_runtimes(self.binding):
            tiers = self.binding["runtimes"][name]["tiers"]
            for tier in ("small", "medium"):
                with self.subTest(runtime=name, tier=tier):
                    self.assertFalse(tiers[tier]["frontier"])

    def test_a_worker_may_never_resolve_a_frontier_model(self) -> None:
        for name in T.resolved_runtimes(self.binding):
            with self.subTest(runtime=name):
                with self.assertRaises(T.TierModelError) as caught:
                    T.resolve_model(name, "large", actor_class="worker", binding=self.binding)
                self.assertEqual(caught.exception.code, "FRONTIER-MODEL-FORBIDDEN")

    def test_a_leader_may_resolve_a_frontier_model(self) -> None:
        for name in T.resolved_runtimes(self.binding):
            with self.subTest(runtime=name):
                resolved = T.resolve_model(name, "large", actor_class="leader", binding=self.binding)
                self.assertTrue(resolved["frontier"])

    def test_the_executor_step_floor_resolves_for_a_worker_in_every_runtime(self) -> None:
        """The v4 executor floor has to be dispatchable, or no worker ever runs."""
        floor = wv.TIER_POLICY_V4[wv.EXECUTOR_STEP_BY_VERSION["v4"]]
        for name in T.resolved_runtimes(self.binding):
            with self.subTest(runtime=name):
                resolved = T.resolve_model(name, floor, actor_class="worker", binding=self.binding)
                self.assertFalse(resolved["frontier"])

    def test_resolution_reports_the_runtime_adapter(self) -> None:
        resolved = T.resolve_model("claude", "medium", actor_class="worker", binding=self.binding)
        self.assertEqual(resolved["adapter"], "claude-code-skill/v1")

    def test_worker_class_forbids_frontier_and_leader_class_allows_it(self) -> None:
        actors = self.binding["actor_classes"]
        self.assertFalse(actors["worker"]["frontier_allowed"])
        self.assertTrue(actors["leader"]["frontier_allowed"])


class Refusals(unittest.TestCase):
    def setUp(self) -> None:
        self.binding = T.load_binding()

    def test_an_undeclared_runtime_is_refused(self) -> None:
        with self.assertRaises(T.TierModelError) as caught:
            T.resolve_model("nope", "medium", actor_class="worker", binding=self.binding)
        self.assertEqual(caught.exception.code, "UNKNOWN-RUNTIME")

    def test_an_unresolved_runtime_is_refused_rather_than_defaulted(self) -> None:
        with self.assertRaises(T.TierModelError) as caught:
            T.resolve_model("hermes", "medium", actor_class="worker", binding=self.binding)
        self.assertEqual(caught.exception.code, "RUNTIME-UNRESOLVED")

    def test_an_undeclared_tier_is_refused(self) -> None:
        with self.assertRaises(T.TierModelError) as caught:
            T.resolve_model("claude", "enormous", actor_class="worker", binding=self.binding)
        self.assertEqual(caught.exception.code, "UNKNOWN-TIER")

    def test_an_undeclared_actor_class_is_refused(self) -> None:
        with self.assertRaises(T.TierModelError) as caught:
            T.resolve_model("claude", "medium", actor_class="tourist", binding=self.binding)
        self.assertEqual(caught.exception.code, "UNKNOWN-ACTOR-CLASS")

    def write(self, document) -> Path:
        import tempfile
        handle = Path(tempfile.mkdtemp()) / "binding.json"
        handle.write_text(json.dumps(document), encoding="utf-8")
        return handle

    def test_an_unknown_top_level_key_is_malformed(self) -> None:
        document = json.loads(ASSET.read_text(encoding="utf-8"))
        document["surprise"] = 1
        with self.assertRaises(T.TierModelError) as caught:
            T.load_binding(self.write(document))
        self.assertEqual(caught.exception.code, "BINDING-MALFORMED")

    def test_a_runtime_missing_a_tier_is_malformed(self) -> None:
        document = json.loads(ASSET.read_text(encoding="utf-8"))
        del document["runtimes"]["claude"]["tiers"]["small"]
        with self.assertRaises(T.TierModelError) as caught:
            T.load_binding(self.write(document))
        self.assertEqual(caught.exception.code, "BINDING-MALFORMED")

    def test_a_surviving_placeholder_is_refused_not_defaulted(self) -> None:
        document = json.loads(ASSET.read_text(encoding="utf-8"))
        document["runtimes"]["codex"]["tiers"]["medium"]["model"] = "__CODEX_MEDIUM__"
        with self.assertRaises(T.TierModelError) as caught:
            T.load_binding(self.write(document))
        self.assertEqual(caught.exception.code, "TIER-MODEL-UNRESOLVED")

    def test_a_missing_asset_is_refused(self) -> None:
        with self.assertRaises(T.TierModelError) as caught:
            T.load_binding(Path("/nonexistent/binding.json"))
        self.assertEqual(caught.exception.code, "BINDING-UNAVAILABLE")


class ShippedAgents(unittest.TestCase):
    """The dispatch surface must agree with the binding, or the binding is decoration."""

    def worker_agents(self):
        return sorted(AGENTS.glob("gauntlet-worker-*.md"))

    def test_at_least_one_worker_agent_ships(self) -> None:
        self.assertTrue(self.worker_agents())

    def test_each_worker_agent_pins_the_model_its_tier_binds_to(self) -> None:
        binding = T.load_binding()
        for path in self.worker_agents():
            tier = path.stem.rsplit("-", 1)[-1]
            with self.subTest(agent=path.name):
                declared = FRONTMATTER_MODEL_RE.search(path.read_text(encoding="utf-8"))
                self.assertIsNotNone(declared, "worker agent declares no model")
                expected = T.resolve_model("claude", tier, actor_class="worker", binding=binding)
                self.assertEqual(declared.group(1), expected["model"])

    def test_no_worker_agent_declares_a_frontier_tier(self) -> None:
        binding = T.load_binding()
        for path in self.worker_agents():
            tier = path.stem.rsplit("-", 1)[-1]
            with self.subTest(agent=path.name):
                self.assertFalse(binding["runtimes"]["claude"]["tiers"][tier]["frontier"])


class Provenance(unittest.TestCase):
    MANIFEST = SKILL / "assets/grill-local-skills.manifest.json"

    def test_the_manifest_lists_every_authored_file_with_its_real_digest(self) -> None:
        document = json.loads(self.MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(document["integration"], "grill-with-docs")
        for relative, digest in document["files"].items():
            with self.subTest(path=relative):
                actual = hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
                self.assertEqual(actual, digest)

    def test_the_manifest_covers_both_authored_skills_and_the_worker_agent(self) -> None:
        document = json.loads(self.MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(sorted(document["files"]), [
            "plugin/agents/gauntlet-worker-medium.md",
            "plugin/skills/grill-implement-parallel/SKILL.md",
            "plugin/skills/grill-partition/SKILL.md",
        ])

    def test_binding_sha256_is_taken_over_the_literal_bytes(self) -> None:
        expected = "sha256:" + hashlib.sha256(ASSET.read_bytes()).hexdigest()
        self.assertEqual(T.binding_sha256(), expected)


if __name__ == "__main__":
    unittest.main(verbosity=0)
