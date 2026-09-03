#!/usr/bin/env python3
"""Contract tests for the ``goal.md`` document (grill_core.goal_document).

Stdlib only. No network, no ``uv``/``specify``/``node``/``backlogctl`` -- only
``tempfile``, ``subprocess`` (python + git) and the standard library (FR-013,
SC-007).

T024: this module imports ``ESSENTIAL``, ``MARKER`` and ``compatible`` from
``grill_core.goal_document`` -- it never redeclares any of them. The tuple
lives in exactly one place; see ``SingleSourceOfTruth`` below (SC-006).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[1]
PLUGIN = REPO / "plugin"
TESTS = HERE.parent
SKILL = PLUGIN / "skills/grill-with-docs"
SCRIPTS = SKILL / "scripts"
ASSETS = SKILL / "assets"
TEMPLATE = ASSETS / "GOAL.template.md"
GRILL_WORKSPACE = SCRIPTS / "grill_workspace.py"
GOAL_DOCUMENT_MODULE = SCRIPTS / "grill_core/goal_document.py"

# scripts/ on sys.path lets `from grill_core import goal_document` resolve the
# same way ensure_goal.py's own docstring says any embedding caller must
# (module docstring, "true for direct invocation ... and for any caller that
# has put scripts/ on sys.path before importing this module").
sys.path.insert(0, str(SCRIPTS))
from grill_core.goal_document import ESSENTIAL, MARKER, compatible, managed_version  # noqa: E402
import ensure_goal  # noqa: E402


class Template(unittest.TestCase):
    def setUp(self) -> None:
        self.text = TEMPLATE.read_text(encoding="utf-8")

    def test_template_carries_the_marker_on_the_first_line_and_is_compatible(self) -> None:
        # T025: template and tuple agree.
        first_line = self.text.split("\n", 1)[0]
        self.assertIn(MARKER, first_line)
        self.assertTrue(compatible(self.text))


class ManagedVersionFirstLineOnly(unittest.TestCase):
    def test_marker_outside_the_first_line_is_not_managed(self) -> None:
        # T025b (FR-011): a marker loose in the body must not identify the
        # document as managed.
        text = f"# Human doc\n\nSome prose that quotes <!-- {MARKER} --> in passing.\n"
        self.assertIn(MARKER, text)  # sanity: the marker really is present
        self.assertIsNone(managed_version(text))

    def test_marker_on_the_first_line_is_managed(self) -> None:
        text = f"<!-- {MARKER} -->\nbody\n"
        self.assertEqual(managed_version(text), "v1")


class EssentialCoverage(unittest.TestCase):
    def setUp(self) -> None:
        self.template = TEMPLATE.read_text(encoding="utf-8")

    def test_removing_each_essential_item_fails_and_names_it(self) -> None:
        # T026 (FR-012, SC-005): remove each item, one at a time, and require
        # the failure to name the missing item.
        for item in ESSENTIAL:
            with self.subTest(item=item):
                mutated = self.template.replace(item, "")
                self.assertNotEqual(mutated, self.template, f"{item!r} was not present verbatim in the template")
                missing = tuple(candidate for candidate in ESSENTIAL if candidate not in mutated)
                self.assertIn(item, missing, f"removed item {item!r} was not named among the missing items {missing!r}")
                self.assertFalse(compatible(mutated), f"compatible() should reject with {item!r} missing")


class OrderAndExtraContent(unittest.TestCase):
    def test_reordered_essential_items_still_pass(self) -> None:
        # T027 (FR-014): presence, not order.
        reordered = "\n".join(reversed(ESSENTIAL))
        self.assertTrue(compatible(reordered))

    def test_extra_content_still_passes(self) -> None:
        # T027 (FR-014): additional content is not forbidden.
        extra = TEMPLATE.read_text(encoding="utf-8") + "\n## Secao extra adicionada por humano\nmais texto aqui.\n"
        self.assertTrue(compatible(extra))


class EmptyDocument(unittest.TestCase):
    def test_empty_and_whitespace_only_documents_fail(self) -> None:
        # T028 (Edge Case "arquivo vazio").
        self.assertFalse(compatible(""))
        self.assertFalse(compatible("   \n\t \n"))


class GoalRootBase(unittest.TestCase):
    def setUp(self) -> None:
        self.t = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.t.name).resolve()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)

    def tearDown(self) -> None:
        self.t.cleanup()


class DirectoryOccupiesTarget(GoalRootBase):
    def test_directory_at_target_is_blocked_with_a_named_reason_and_untouched(self) -> None:
        # T028b: destination occupied by a directory -> BLOCKED, named
        # reason, directory neither removed nor written into.
        target = self.root / "goal.md"
        target.mkdir()
        (target / "sentinel.txt").write_text("do-not-touch", encoding="utf-8")

        result = ensure_goal.resolve_goal(self.root)

        self.assertEqual(result.status, "BLOCKED")
        self.assertTrue(result.reason)
        self.assertTrue(target.is_dir())
        self.assertEqual((target / "sentinel.txt").read_text(encoding="utf-8"), "do-not-touch")
        self.assertEqual(sorted(p.name for p in target.iterdir()), ["sentinel.txt"])


class CollisionBranch(GoalRootBase):
    def test_os_link_collision_branch_is_a_structural_guarantee_not_a_process_race(self) -> None:
        # T030 (FR-015, SC-003). Two parts:
        #  1. A second resolve_goal() over an already-materialised root
        #     yields REUSED, one intact file, never BLOCKED.
        #  2. atomic_create()'s own FileExistsError branch -- the structural
        #     guarantee os.link gives, not a real inter-process race -- is
        #     exercised directly, by calling it a second time against the
        #     same, already-occupied target.
        first = ensure_goal.resolve_goal(self.root)
        self.assertEqual(first.status, "CREATED")
        target = self.root / "goal.md"
        created_bytes = target.read_bytes()

        created_again = ensure_goal.atomic_create(target, b"attempted-overwrite\n")
        self.assertFalse(created_again)
        self.assertEqual(target.read_bytes(), created_bytes)

        second = ensure_goal.resolve_goal(self.root)
        self.assertEqual(second.status, "REUSED")
        self.assertIsNone(second.reason)
        self.assertEqual(target.read_bytes(), created_bytes)
        self.assertEqual([p.name for p in self.root.iterdir() if p.name != ".git"], ["goal.md"])


class PreservedBranch(GoalRootBase):
    """The three named PRESERVED reasons, each proved byte-intact (FR-003, FR-006, FR-007).

    Review finding I1. The behaviour was observed by hand while building the
    feature, but observation in a scratch directory is not a regression test:
    nothing in the repository would reject a refactor that turned PRESERVED
    back into an overwrite, and `init` would start destroying human work with
    the suite still green. SC-002 is the criterion whose cost of being wrong
    is unrecoverable, so it gets assertions, not a memory of a terminal.
    """

    def preserved(self, body: bytes) -> tuple[object, str, list[str]]:
        target = self.root / "goal.md"
        target.write_bytes(body)
        before = hashlib.sha256(body).hexdigest()

        result = ensure_goal.resolve_goal(self.root)

        after = hashlib.sha256(target.read_bytes()).hexdigest()
        self.assertEqual(before, after, "PRESERVED must leave the bytes untouched")
        entries = sorted(q.name for q in self.root.iterdir() if q.name != ".git")
        # No backup, no copy, no rename: exactly the file that was already there.
        self.assertEqual(entries, ["goal.md"])
        return result, after, entries

    def test_human_document_is_preserved_byte_intact(self) -> None:
        result, _, _ = self.preserved(b"meus objetivos do trimestre\n- crescer\n")
        self.assertEqual(result.status, "PRESERVED")
        self.assertEqual(result.reason, "human document")

    def test_empty_document_is_preserved_not_treated_as_absent(self) -> None:
        # Edge case: existing-but-empty is divergent, so it is preserved.
        # Treating it as absent would reopen the exception FR-002 denies.
        result, _, _ = self.preserved(b"")
        self.assertEqual(result.status, "PRESERVED")
        self.assertEqual((self.root / "goal.md").stat().st_size, 0)

    def test_other_version_marker_is_a_managed_version_mismatch(self) -> None:
        body = "<!-- grill-with-docs-goal:v2 -->\nconteudo de outra versao\n".encode("utf-8")
        result, _, _ = self.preserved(body)
        self.assertEqual(result.status, "PRESERVED")
        self.assertEqual(result.reason, "managed version mismatch")

    def test_v1_marker_failing_the_contract_is_an_incompatible_goal(self) -> None:
        # Correct marker on the first line, but the required parts are gone.
        body = f"<!-- {MARKER} -->\nfaltando tudo\n".encode("utf-8")
        result, _, _ = self.preserved(body)
        self.assertEqual(result.status, "PRESERVED")
        self.assertEqual(result.reason, "incompatible goal")


class BlockedBranch(GoalRootBase):
    """Refusals happen before any write, and never touch what they refuse."""

    def test_symlink_target_is_blocked_and_the_pointee_is_untouched(self) -> None:
        outside = Path(self.t.name).resolve() / "pointee.txt"
        outside.write_bytes(b"segredo\n")
        try:
            (self.root / "goal.md").symlink_to(outside)
        except (OSError, NotImplementedError) as error:  # pragma: no cover
            self.skipTest(f"symlinks unavailable on this platform: {error}")

        result = ensure_goal.resolve_goal(self.root)

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason, "unsafe target")
        # The refusal must not have followed the link and written through it.
        self.assertEqual(outside.read_bytes(), b"segredo\n")

    def test_invalid_utf8_document_is_blocked_and_left_alone(self) -> None:
        # contracts/materialization-cli.md: UnicodeError -> BLOCKED,
        # "invalid UTF-8 goal". Named refusal, never silent progress.
        body = b"\xff\xfe not utf-8 at all\n"
        target = self.root / "goal.md"
        target.write_bytes(body)

        result = ensure_goal.resolve_goal(self.root)

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason, "invalid UTF-8 goal")
        self.assertEqual(target.read_bytes(), body)

    def test_cli_exit_code_is_two_for_a_blocked_root(self) -> None:
        # T013's exit contract, on the refusal side: 2, not 0.
        (self.root / "goal.md").mkdir()
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = ensure_goal.ensure(str(self.root))
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stream.getvalue())["status"], "BLOCKED")


class SingleSourceOfTruth(unittest.TestCase):
    def test_essential_is_declared_in_exactly_one_source_file(self) -> None:
        # T029 (SC-006): textual search over plugin/ and tests/ -- the source
        # tree, not the specs tree (contracts/goal-document.md quotes the
        # tuple in prose; that is a citation, not a declaration).
        needle = "ESSENTIAL" + " = ("  # built at runtime: never appear as one literal substring in this file
        anchor = ESSENTIAL[0]  # the tuple's first item -- unique to this contract's tuple
        hits = []
        for base in (PLUGIN, TESTS):
            for path in sorted(base.rglob("*.py")):
                if ".git" in path.relative_to(base).parts:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if needle in text and anchor in text:
                    hits.append(path)
        self.assertEqual(hits, [GOAL_DOCUMENT_MODULE], hits)


class ExternalToolBoundary(unittest.TestCase):
    def test_this_validator_only_ever_shells_out_to_python_and_git(self) -> None:
        # T031 (FR-013, SC-007): no network, no uv/specify/node/backlogctl.
        source = HERE.read_text(encoding="utf-8")
        calls = re.findall(r"subprocess\.run\(\s*\[([^\]]*)\]", source)
        self.assertTrue(calls)
        allowed = ("sys.executable", "'git'", '"git"')
        for call in calls:
            first_argument = call.strip().split(",", 1)[0].strip()
            self.assertIn(first_argument, allowed, call)


class WorkItemSealBoundary(unittest.TestCase):
    def test_work_item_json_never_carries_a_goal_block(self) -> None:
        # T031b: goal.md is a project-wide, humanly-editable artefact -- it is
        # reported via state.json, never sealed into WORK-ITEM.json identity.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as raw_root:
            root = Path(raw_root).resolve()
            subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
            result = subprocess.run(
                [
                    sys.executable, str(GRILL_WORKSPACE), "init", str(root),
                    "--runtime", "claude",
                    "--type", "feature", "--slug", "goal-seal-check",
                    "--work-id", "goal-seal-check", "--skip-backlog",
                ],
                text=True, capture_output=True,
                env={**os.environ, "GRILL_SKIP_DEPENDENCIES": "1"},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            body = json.loads(result.stdout.splitlines()[0])
            self.assertEqual(body.get("status"), "CREATED", body)

            work_item_path = root / ".grill/work-items/goal-seal-check/WORK-ITEM.json"
            metadata = json.loads(work_item_path.read_text(encoding="utf-8"))
            self.assertNotIn("goal", metadata)
            self.assertNotIn("goal", metadata.get("immutable", {}))

            state = json.loads((root / ".grill/work-items/goal-seal-check/state.json").read_text(encoding="utf-8"))
            self.assertIn("goal", state)


if __name__ == "__main__":
    unittest.main()
