#!/usr/bin/env python3
"""Public contract for grill_core/workflow_versions.py, the per-version SSOT.

The module is pure data, so this validator is deliberately about *shape and
independence*, not behaviour. Its job is to catch the two failure modes that
a table of frozen literals actually has:

1. **Silent derivation.** If someone "tidies up" ``SEQUENCE_V4`` into a
   comprehension over ``SEQUENCE_V3`` and ``STEP_RENAMES_V3_TO_V4``, a typo in
   the rename map would rewrite the canonical order instead of failing here.
   The literals below are duplicated on purpose -- same anti-import policy
   ``validate_gauntlet_scheduler_contract.py`` documents for its own
   ``SEQUENCE``.
2. **Partial rename.** The sequence lives in seven byte-identical places in
   the tree; the classic defect is renaming it in six of them. Asserting set
   equality (never ``len(...) == 11``) makes a half-applied rename fail loudly:
   a length check passes happily with eleven wrong keys.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "plugin/skills/grill-with-docs/scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from grill_core import workflow_versions as wv  # noqa: E402

# Frozen copies. Never imported from the module under test -- that would make
# this file agree with any edit by construction.
FROZEN_V3 = (
    "specify", "plan", "checklist", "tasks", "analyze", "agent-assign",
    "agent-execute", "converge", "verify", "review", "ship",
)
FROZEN_V4 = (
    "specify", "plan", "checklist", "tasks", "analyze", "partition",
    "implement-parallel", "converge", "verify", "review", "ship",
)
TIERS = ("small", "medium", "large")


class Sequences(unittest.TestCase):
    def test_v3_sequence_is_frozen(self) -> None:
        self.assertEqual(wv.SEQUENCE_V3, FROZEN_V3)

    def test_v4_sequence_is_frozen(self) -> None:
        self.assertEqual(wv.SEQUENCE_V4, FROZEN_V4)

    def test_both_sequences_have_the_same_length(self) -> None:
        self.assertEqual(len(wv.SEQUENCE_V3), len(wv.SEQUENCE_V4))

    def test_the_two_sequences_are_distinct_objects(self) -> None:
        """A shared object means one version silently rewrites the other."""
        self.assertIsNot(wv.SEQUENCE_V3, wv.SEQUENCE_V4)
        self.assertNotEqual(wv.SEQUENCE_V3, wv.SEQUENCE_V4)

    def test_sequences_are_tuples_so_they_cannot_be_mutated_in_place(self) -> None:
        for version, sequence in wv.SEQUENCE_BY_VERSION.items():
            with self.subTest(version=version):
                self.assertIsInstance(sequence, tuple)

    def test_no_step_id_repeats_within_a_sequence(self) -> None:
        for version, sequence in wv.SEQUENCE_BY_VERSION.items():
            with self.subTest(version=version):
                self.assertEqual(len(set(sequence)), len(sequence))

    def test_sequence_by_version_exposes_the_frozen_tuples(self) -> None:
        self.assertEqual(wv.SEQUENCE_BY_VERSION, {"v3": FROZEN_V3, "v4": FROZEN_V4})


class Renames(unittest.TestCase):
    def test_rename_map_is_exactly_the_difference_between_the_sequences(self) -> None:
        removed = [s for s in FROZEN_V3 if s not in FROZEN_V4]
        added = [s for s in FROZEN_V4 if s not in FROZEN_V3]
        self.assertEqual(sorted(wv.STEP_RENAMES_V3_TO_V4), sorted(removed))
        self.assertEqual(sorted(wv.STEP_RENAMES_V3_TO_V4.values()), sorted(added))

    def test_rename_map_is_a_bijection(self) -> None:
        values = list(wv.STEP_RENAMES_V3_TO_V4.values())
        self.assertEqual(len(set(values)), len(values))

    def test_renaming_v3_positionally_reproduces_v4(self) -> None:
        """Provenance check: the rename is positional, never a reordering."""
        rebuilt = tuple(wv.STEP_RENAMES_V3_TO_V4.get(s, s) for s in FROZEN_V3)
        self.assertEqual(rebuilt, FROZEN_V4)

    def test_unrenamed_steps_keep_their_position(self) -> None:
        for step in FROZEN_V3:
            if step in wv.STEP_RENAMES_V3_TO_V4:
                continue
            with self.subTest(step=step):
                self.assertEqual(FROZEN_V3.index(step), FROZEN_V4.index(step))


class TierPolicies(unittest.TestCase):
    def test_every_policy_covers_exactly_its_own_sequence(self) -> None:
        """Set equality, not len(...) == 11: eleven wrong keys must fail."""
        for version, policy in wv.TIER_POLICY_BY_VERSION.items():
            with self.subTest(version=version):
                self.assertEqual(set(policy), set(wv.SEQUENCE_BY_VERSION[version]))

    def test_every_floor_is_a_known_tier(self) -> None:
        for version, policy in wv.TIER_POLICY_BY_VERSION.items():
            for step, tier in policy.items():
                with self.subTest(version=version, step=step):
                    self.assertIn(tier, TIERS)

    def test_the_two_policies_are_distinct_objects(self) -> None:
        self.assertIsNot(wv.TIER_POLICY_V3, wv.TIER_POLICY_V4)

    def test_unrenamed_steps_keep_their_floor_across_versions(self) -> None:
        """Only the renamed steps may change tier in this migration."""
        for step, tier in wv.TIER_POLICY_V3.items():
            if step in wv.STEP_RENAMES_V3_TO_V4:
                continue
            with self.subTest(step=step):
                self.assertEqual(wv.TIER_POLICY_V4[step], tier)

    def test_the_executor_step_floor_is_never_frontier_tier(self) -> None:
        """Workers dispatched under the executor step must not need `large`."""
        for version, executor in wv.EXECUTOR_STEP_BY_VERSION.items():
            with self.subTest(version=version):
                self.assertNotEqual(wv.TIER_POLICY_BY_VERSION[version][executor], "large")


class ExecutorAndAssets(unittest.TestCase):
    def test_executor_step_belongs_to_its_own_sequence(self) -> None:
        for version, executor in wv.EXECUTOR_STEP_BY_VERSION.items():
            with self.subTest(version=version):
                self.assertIn(executor, wv.SEQUENCE_BY_VERSION[version])

    def test_executor_steps_are_the_renamed_pair(self) -> None:
        self.assertEqual(wv.EXECUTOR_STEP_BY_VERSION["v3"], "agent-execute")
        self.assertEqual(wv.EXECUTOR_STEP_BY_VERSION["v4"], "implement-parallel")

    def test_v3_registry_filename_never_moves(self) -> None:
        """Moving it would break every pinned registry_sha256 in the wild."""
        self.assertEqual(
            wv.REGISTRY_FILENAME_BY_VERSION["v3"], "workflow-step-skills.json"
        )

    def test_each_version_owns_a_distinct_registry_asset(self) -> None:
        names = list(wv.REGISTRY_FILENAME_BY_VERSION.values())
        self.assertEqual(len(set(names)), len(names))

    def test_each_version_owns_a_distinct_trusted_catalog_asset(self) -> None:
        names = list(wv.TRUSTED_CATALOGS_FILENAME_BY_VERSION.values())
        self.assertEqual(len(set(names)), len(names))

    def test_registry_and_trusted_catalog_maps_cover_the_same_versions(self) -> None:
        self.assertEqual(
            set(wv.REGISTRY_FILENAME_BY_VERSION),
            set(wv.TRUSTED_CATALOGS_FILENAME_BY_VERSION),
        )

    def test_template_map_still_covers_v2_even_though_v2_never_executes(self) -> None:
        self.assertEqual(wv.TEMPLATE_FILENAME_BY_VERSION["v2"], "WORKFLOW.template.md")
        self.assertNotIn("v2", wv.EXECUTABLE_VERSIONS)

    def test_every_executable_version_has_a_template_and_a_registry(self) -> None:
        for version in wv.EXECUTABLE_VERSIONS:
            with self.subTest(version=version):
                self.assertIn(version, wv.TEMPLATE_FILENAME_BY_VERSION)
                self.assertIn(version, wv.REGISTRY_FILENAME_BY_VERSION)

    def test_development_schema_is_bumped_only_for_v4(self) -> None:
        self.assertEqual(wv.DEVELOPMENT_SCHEMA_BY_VERSION["v3"], "grill-development/v1")
        self.assertEqual(wv.DEVELOPMENT_SCHEMA_BY_VERSION["v4"], "grill-development/v2")

    def test_all_per_version_maps_agree_on_the_executable_versions(self) -> None:
        for name in (
            "SEQUENCE_BY_VERSION",
            "TIER_POLICY_BY_VERSION",
            "EXECUTOR_STEP_BY_VERSION",
            "REGISTRY_FILENAME_BY_VERSION",
            "DEVELOPMENT_SCHEMA_BY_VERSION",
        ):
            with self.subTest(table=name):
                self.assertEqual(tuple(sorted(getattr(wv, name))), tuple(sorted(wv.EXECUTABLE_VERSIONS)))


class Purity(unittest.TestCase):
    def test_the_module_imports_nothing_but_future_annotations(self) -> None:
        """Pure data: no I/O, no core imports, no load-time dependency graph."""
        source = (SCRIPTS / "grill_core/workflow_versions.py").read_text(encoding="utf-8")
        imports = [
            line.strip()
            for line in source.splitlines()
            if line.startswith(("import ", "from "))
        ]
        self.assertEqual(imports, ["from __future__ import annotations"])


if __name__ == "__main__":
    unittest.main(verbosity=0)
