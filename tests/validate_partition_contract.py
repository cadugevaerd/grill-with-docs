#!/usr/bin/env python3
"""Public contract for the ``partition`` step's deterministic core.

Fixtures are inline ``tasks.md`` bodies plus the repository's own fifteen real
``specs/*/tasks.md`` as a corpus. No network, no Git, no subprocess: the module
under test is pure text in, documents out.

The corpus cases matter more than the synthetic ones here. The first design of
this step passed every hand-written fixture and still collapsed to a single
node on fourteen of those fifteen real files, because the fixtures had been
written from the algorithm rather than from real tool output. Every emitted DAG
is therefore re-validated through the *production* validators in
``gauntlet_runs`` rather than through a local re-implementation of them.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "plugin/skills/grill-with-docs/scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from grill_core import gauntlet_runs  # noqa: E402
from grill_core import partition as P  # noqa: E402

MEDIUM_FLOOR = "medium"
MARKDOWN_FLOOR = "small"


def tasks_md(*lines: str) -> str:
    return "\n".join(lines) + "\n"


THREE_WAY = tasks_md(
    "# Tasks: Demo",
    "",
    "## Phase 1: Setup",
    "",
    "- [ ] T001 [P] Add `src/alpha.py` behaviour.",
    "- [ ] T002 [P] Add `src/beta.py` behaviour.",
    "- [ ] T003 Add `src/gamma.py` behaviour.",
    "",
    "## Phase 2: Core",
    "",
    "- [ ] T004 Extend `src/alpha.py` again.",
    "- [ ] T005 Extend `src/delta.py`.",
)

CHAINED = tasks_md(
    "## Phase 1: Setup",
    "",
    "- [ ] T001 Touch `src/only.py`.",
    "- [ ] T002 [P] Touch `src/only.py` too.",
    "- [ ] T003 Touch `src/only.py` as well.",
)

WITH_UNMAPPED = tasks_md(
    "## Phase 1: Setup",
    "",
    "- [ ] T001 Edit `src/alpha.py`.",
    "- [ ] T002 Decide the naming convention with the team.",
    "- [ ] T003 Write the release note.",
)


class Parsing(unittest.TestCase):
    def test_task_id_phase_and_markers_are_read(self) -> None:
        parsed = P.parse_tasks(THREE_WAY)
        self.assertEqual([t.id for t in parsed], ["T001", "T002", "T003", "T004", "T005"])
        self.assertEqual([t.phase for t in parsed], [1, 1, 1, 2, 2])
        self.assertEqual([t.parallel for t in parsed], [True, True, False, False, False])

    def test_phase_title_is_captured(self) -> None:
        parsed = P.parse_tasks(THREE_WAY)
        self.assertEqual(parsed[0].phase_title, "Setup")
        self.assertEqual(parsed[-1].phase_title, "Core")

    def test_story_markers_are_kept_and_p_is_not_one(self) -> None:
        parsed = P.parse_tasks(tasks_md("## Phase 1: X", "- [ ] T001 [P] [US2] Edit `a/b.py`."))
        self.assertEqual(parsed[0].stories, ("US2",))
        self.assertTrue(parsed[0].parallel)

    def test_completed_tasks_are_parsed_too(self) -> None:
        """A resumed cycle still has to partition the whole file."""
        parsed = P.parse_tasks(tasks_md("## Phase 1: X", "- [x] T001 Edit `a/b.py`."))
        self.assertEqual(len(parsed), 1)

    def test_backticked_and_bare_paths_are_both_extracted(self) -> None:
        self.assertEqual(P.extract_files("Edit `a/b.py` and c/d.py now."), ("a/b.py", "c/d.py"))

    def test_line_suffixes_are_stripped(self) -> None:
        self.assertEqual(P.extract_files("Fix `a/b.py:927-928`."), ("a/b.py",))

    def test_a_bare_filename_is_not_a_path(self) -> None:
        """Guessing the directory of `store.py` is exactly the inference refused."""
        self.assertEqual(P.extract_files("Fix `store.py:927`."), ())

    def test_urls_are_not_paths(self) -> None:
        self.assertEqual(P.extract_files("See https://example.com/a/b."), ())

    def test_escaping_paths_are_rejected(self) -> None:
        self.assertEqual(P.extract_files("Edit `../outside/x.py` and `/etc/passwd`."), ())

    def test_paths_are_sorted_and_deduplicated(self) -> None:
        self.assertEqual(P.extract_files("`b/x.py` `a/y.py` `b/x.py`"), ("a/y.py", "b/x.py"))


class Structure(unittest.TestCase):
    def build(self, text: str, groups: int = 3):
        return P.partition(text, feature="demo", sidecar_dir="specs/demo/implement", groups=groups)

    def test_every_task_lands_in_exactly_one_node(self) -> None:
        _, report = self.build(THREE_WAY)
        seen = [tid for node in report["nodes"] for tid in node["task_ids"]]
        self.assertEqual(sorted(seen), ["T001", "T002", "T003", "T004", "T005"])
        self.assertEqual(len(seen), len(set(seen)))

    def test_parallel_nodes_of_a_phase_have_pairwise_disjoint_files(self) -> None:
        dag, report = self.build(THREE_WAY)
        files = {node["id"]: set(node["files"]) for node in dag["nodes"]}
        by_phase: dict[int, list[str]] = {}
        for node in report["nodes"]:
            if node["parallel"]:
                by_phase.setdefault(node["phase"], []).append(node["id"])
        for phase, ids in by_phase.items():
            for left in range(len(ids)):
                for right in range(left + 1, len(ids)):
                    with self.subTest(phase=phase, pair=(ids[left], ids[right])):
                        self.assertEqual(files[ids[left]] & files[ids[right]], set())

    def test_a_phase_depends_on_every_node_of_the_previous_phase(self) -> None:
        dag, report = self.build(THREE_WAY)
        first = sorted(n["id"] for n in report["nodes"] if n["phase"] == 1)
        for node in dag["nodes"]:
            if node["id"].startswith("p02"):
                with self.subTest(node=node["id"]):
                    self.assertEqual(node["depends_on"], first)

    def test_the_first_phase_depends_on_nothing(self) -> None:
        dag, _ = self.build(THREE_WAY)
        for node in dag["nodes"]:
            if node["id"].startswith("p01"):
                self.assertEqual(node["depends_on"], [])

    def test_each_node_carries_its_own_sidecar(self) -> None:
        dag, _ = self.build(THREE_WAY)
        for node in dag["nodes"]:
            with self.subTest(node=node["id"]):
                self.assertIn(f"specs/demo/implement/{node['id']}.tasks.json", node["files"])

    def test_node_ids_never_use_the_reserved_remediation_suffix(self) -> None:
        dag, _ = self.build(THREE_WAY)
        for node in dag["nodes"]:
            with self.subTest(node=node["id"]):
                self.assertIsNone(gauntlet_runs.store.WORKER_REMEDIATION_SUFFIX_RE.fullmatch(node["id"]))


class Degradation(unittest.TestCase):
    def build(self, text: str, groups: int = 3):
        return P.partition(text, feature="demo", sidecar_dir="specs/demo/implement", groups=groups)

    def test_a_single_conflict_group_yields_one_node_not_three_fake_ones(self) -> None:
        dag, report = self.build(CHAINED)
        self.assertEqual(report["phases"][0]["achieved_groups"], 1)
        self.assertEqual(report["verdict"], P.VERDICT_DEGRADED)
        self.assertIn(P.REASON_CONFLICT_GROUPS, report["phases"][0]["reasons"])
        self.assertEqual(len([n for n in dag["nodes"] if n["parallel"]]), 1)

    def test_a_conflict_group_is_never_split_across_bins(self) -> None:
        _, report = self.build(CHAINED)
        owning = [node for node in report["nodes"] if "T001" in node["task_ids"]]
        self.assertEqual(len(owning), 1)
        self.assertEqual(sorted(owning[0]["task_ids"]), ["T001", "T002", "T003"])

    def test_max_workers_never_exceeds_the_widest_phase(self) -> None:
        dag, report = self.build(CHAINED)
        self.assertEqual(dag["max_workers"], 1)
        self.assertEqual(dag["max_workers"], report["max_workers"])

    def test_max_workers_never_exceeds_the_requested_width(self) -> None:
        dag, _ = self.build(THREE_WAY, groups=2)
        self.assertLessEqual(dag["max_workers"], 2)

    def test_unmapped_tasks_get_a_solo_node_rather_than_a_guess(self) -> None:
        dag, report = self.build(WITH_UNMAPPED)
        serial = [node for node in report["nodes"] if not node["parallel"]]
        self.assertEqual(len(serial), 1)
        self.assertEqual(sorted(serial[0]["task_ids"]), ["T002", "T003"])
        self.assertEqual(serial[0]["scope"], "FEATURE_WIDE")
        node = next(n for n in dag["nodes"] if n["id"] == serial[0]["id"])
        self.assertFalse(node["parallel"])

    def test_the_solo_node_declares_the_whole_feature_scope(self) -> None:
        dag, _ = self.build(WITH_UNMAPPED)
        serial = next(n for n in dag["nodes"] if n["id"].endswith("-serial"))
        self.assertIn("src/alpha.py", serial["files"])

    def test_the_solo_node_runs_after_the_parallel_bins_of_its_phase(self) -> None:
        dag, _ = self.build(WITH_UNMAPPED)
        serial = next(n for n in dag["nodes"] if n["id"].endswith("-serial"))
        self.assertEqual(serial["depends_on"], ["p01-a"])

    def test_unmapped_tasks_are_named_in_the_report(self) -> None:
        _, report = self.build(WITH_UNMAPPED)
        self.assertEqual(report["unmapped_task_ids"], ["T002", "T003"])
        self.assertIn(P.REASON_UNMAPPED, report["phases"][0]["reasons"])

    def test_a_clean_three_way_split_reports_complete(self) -> None:
        text = tasks_md(
            "## Phase 1: Setup",
            "- [ ] T001 Edit `src/a.py`.",
            "- [ ] T002 Edit `src/b.py`.",
            "- [ ] T003 Edit `src/c.py`.",
        )
        _, report = self.build(text)
        self.assertEqual(report["verdict"], P.VERDICT_COMPLETE)
        self.assertEqual(report["phases"][0]["achieved_groups"], 3)


class Refusals(unittest.TestCase):
    def build(self, text: str, groups: int = 3):
        return P.partition(text, feature="demo", sidecar_dir="specs/demo/implement", groups=groups)

    def test_a_tasks_file_with_no_tasks_is_refused(self) -> None:
        with self.assertRaises(P.PartitionError) as caught:
            self.build(tasks_md("# Tasks: Demo", "", "Nothing here."))
        self.assertEqual(caught.exception.code, "PARTITION-NO-TASKS")

    def test_a_feature_naming_no_path_at_all_is_refused(self) -> None:
        with self.assertRaises(P.PartitionError) as caught:
            self.build(tasks_md("## Phase 1: X", "- [ ] T001 Think hard about naming."))
        self.assertEqual(caught.exception.code, "PARTITION-UNSCOPED-FEATURE")

    def test_a_feature_that_is_all_coordinator_evidence_is_refused(self) -> None:
        with self.assertRaises(P.PartitionError) as caught:
            self.build(tasks_md("## Phase 1: X", "- [ ] T001 Write `.specify/reports/x.md`."))
        self.assertEqual(caught.exception.code, "PARTITION-COORDINATOR-ONLY")

    def test_a_width_below_one_is_refused(self) -> None:
        with self.assertRaises(P.PartitionError) as caught:
            self.build(THREE_WAY, groups=0)
        self.assertEqual(caught.exception.code, "PARTITION-INVALID-WIDTH")


class EvidenceBoundary(unittest.TestCase):
    """Tasks writing coordinator evidence are withheld from every wave.

    ADR-0010 makes the coordinator the single Evidence Boundary, so a task that
    writes `.grill/` or `.specify/reports/` is the leader's own work. Refusing
    the whole feature over it would block three of this repository's own
    fourteen partitionable specs; letting a worker run it would let a worker
    forge its proof. Neither is acceptable, so it is handed back by name.
    """

    def build(self, text: str):
        return P.partition(text, feature="demo", sidecar_dir="specs/demo/implement")

    EVIDENCE = tasks_md(
        "## Phase 1: X",
        "- [ ] T001 Edit `src/alpha.py`.",
        "- [ ] T002 Record `.specify/reports/verify-review-ship/verify.md`.",
        "- [ ] T003 Append `.grill/work-items/x/ROUND-LOG.jsonl`.",
    )

    def test_evidence_tasks_are_named_back_to_the_leader(self) -> None:
        _, report = self.build(self.EVIDENCE)
        self.assertEqual(report["deferred_to_leader"], ["T002", "T003"])

    def test_evidence_tasks_reach_no_node(self) -> None:
        _, report = self.build(self.EVIDENCE)
        placed = {tid for node in report["nodes"] for tid in node["task_ids"]}
        self.assertEqual(placed, {"T001"})

    def test_no_emitted_node_declares_forbidden_evidence(self) -> None:
        dag, _ = self.build(self.EVIDENCE)
        nodes = gauntlet_runs._validate_dag_structure(dag)
        gauntlet_runs._validate_dag_scope(nodes)

    def test_deferring_marks_the_partition_degraded(self) -> None:
        _, report = self.build(self.EVIDENCE)
        self.assertEqual(report["verdict"], P.VERDICT_DEGRADED)
        self.assertIn(P.REASON_EVIDENCE, report["phases"][0]["reasons"])

    def test_the_task_count_still_reports_the_whole_file(self) -> None:
        """Deferred work stays visible: 3 tasks, 1 dispatchable."""
        _, report = self.build(self.EVIDENCE)
        self.assertEqual(report["tasks"], 3)
        self.assertEqual(report["dispatchable_tasks"], 1)

    def test_the_real_corpus_defers_rather_than_blocking(self) -> None:
        """011, 012 and 013 name coordinator evidence and must still partition."""
        for feature in ("011-gauntlet-loop", "012-durable-run-state", "013-scheduler-waves"):
            path = REPO / "specs" / feature / "tasks.md"
            with self.subTest(feature=feature):
                _, report = P.partition(
                    path.read_text(encoding="utf-8"),
                    feature=feature,
                    sidecar_dir=f"specs/{feature}/implement",
                )
                self.assertTrue(report["deferred_to_leader"])


class Determinism(unittest.TestCase):
    def test_the_same_input_produces_byte_identical_documents(self) -> None:
        """A run pins dag_content_sha256; drift here would make that pin noise."""
        for path in sorted(glob.glob(str(REPO / "specs/*/tasks.md"))):
            feature = os.path.basename(os.path.dirname(path))
            text = Path(path).read_text(encoding="utf-8")
            try:
                first = P.partition(text, feature=feature, sidecar_dir=f"specs/{feature}/implement")
                second = P.partition(text, feature=feature, sidecar_dir=f"specs/{feature}/implement")
            except P.PartitionError:
                continue
            with self.subTest(feature=feature):
                self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_the_p_marker_does_not_change_the_grouping(self) -> None:
        """[P] is recorded for diagnostics; disjointness is what packs bins."""
        marked = tasks_md("## Phase 1: X", "- [ ] T001 [P] Edit `a/b.py`.", "- [ ] T002 [P] Edit `c/d.py`.")
        plain = tasks_md("## Phase 1: X", "- [ ] T001 Edit `a/b.py`.", "- [ ] T002 Edit `c/d.py`.")
        left, _ = P.partition(marked, feature="d", sidecar_dir="specs/d/implement")
        right, _ = P.partition(plain, feature="d", sidecar_dir="specs/d/implement")
        self.assertEqual(left, right)


class RealCorpus(unittest.TestCase):
    """Every real tasks.md in this repository, through the production validators."""

    def corpus(self):
        for path in sorted(glob.glob(str(REPO / "specs/*/tasks.md"))):
            feature = os.path.basename(os.path.dirname(path))
            text = Path(path).read_text(encoding="utf-8")
            try:
                dag, report = P.partition(text, feature=feature, sidecar_dir=f"specs/{feature}/implement")
            except P.PartitionError:
                continue
            yield feature, dag, report

    def test_the_corpus_is_not_empty(self) -> None:
        self.assertGreaterEqual(len(list(self.corpus())), 10)

    def test_every_emitted_dag_passes_the_production_structure_validator(self) -> None:
        for feature, dag, _ in self.corpus():
            with self.subTest(feature=feature):
                gauntlet_runs._validate_dag_structure(dag)

    def test_every_emitted_dag_passes_the_production_scope_validator(self) -> None:
        for feature, dag, _ in self.corpus():
            with self.subTest(feature=feature):
                nodes = gauntlet_runs._validate_dag_structure(dag)
                gauntlet_runs._validate_dag_scope(nodes)

    def test_every_emitted_node_satisfies_the_medium_tier_floor(self) -> None:
        for feature, dag, _ in self.corpus():
            with self.subTest(feature=feature):
                nodes = gauntlet_runs._validate_dag_structure(dag)
                gauntlet_runs._validate_dag_tiers(
                    nodes, agent_execute_floor=MEDIUM_FLOOR, markdown_floor=MARKDOWN_FLOOR
                )

    def test_the_corpus_actually_parallelises(self) -> None:
        """The regression this whole redesign exists for: no all-serial output."""
        widths = [dag["max_workers"] for _, dag, _ in self.corpus()]
        self.assertGreaterEqual(sum(1 for w in widths if w >= 2), len(widths) - 2)

    def test_no_task_is_lost_anywhere_in_the_corpus(self) -> None:
        """Every task is either dispatched to a node or named back to the leader."""
        for feature, _, report in self.corpus():
            with self.subTest(feature=feature):
                placed = [tid for node in report["nodes"] for tid in node["task_ids"]]
                self.assertEqual(len(placed), report["dispatchable_tasks"])
                self.assertEqual(len(set(placed)), len(placed))
                accounted = set(placed) | set(report["deferred_to_leader"])
                self.assertEqual(len(accounted), report["tasks"])

    def test_parallel_siblings_never_share_a_file_anywhere_in_the_corpus(self) -> None:
        for feature, dag, report in self.corpus():
            files = {node["id"]: set(node["files"]) for node in dag["nodes"]}
            by_phase: dict[int, list[str]] = {}
            for node in report["nodes"]:
                if node["parallel"]:
                    by_phase.setdefault(node["phase"], []).append(node["id"])
            for phase, ids in by_phase.items():
                for left in range(len(ids)):
                    for right in range(left + 1, len(ids)):
                        with self.subTest(feature=feature, phase=phase):
                            self.assertEqual(files[ids[left]] & files[ids[right]], set())


if __name__ == "__main__":
    unittest.main(verbosity=0)
