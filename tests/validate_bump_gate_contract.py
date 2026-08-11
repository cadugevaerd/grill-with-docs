#!/usr/bin/env python3
"""Executable contract for the plugin version bump gate.

Runs with no git repository and no pull request context, because it is collected by
``tests/run_validators.py`` on every supported OS and Python version.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SCRIPT = TESTS / "check_version_bump.py"


def load() -> object:
    spec = importlib.util.spec_from_file_location("check_version_bump_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load()

PLUGIN_FILE = "plugin/skills/grill-with-docs/SKILL.md"
MANIFEST_FILE = "plugin/.claude-plugin/plugin.json"
OUTSIDE = ["tests/validate_distribution.py", "README.md", ".github/workflows/ci.yml"]


class Collection(unittest.TestCase):
    def test_the_checker_is_not_collected_as_a_validator(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertNotIn(SCRIPT, list(TESTS.glob("validate_*.py")))


class VersionParsing(unittest.TestCase):
    def test_only_three_integer_components_parse(self) -> None:
        self.assertEqual(MODULE.parse_version("2.5.0"), (2, 5, 0))
        self.assertEqual(MODULE.parse_version("0.0.0"), (0, 0, 0))
        self.assertEqual(MODULE.parse_version("10.20.30"), (10, 20, 30))

    def test_malformed_and_absent_versions_raise(self) -> None:
        for text in ("2.5", "v2.5.0", "2.5.0-rc1", "2.5.0.1", "", " 2.5.0", "2.5.0 ", None, 250):
            with self.assertRaises(ValueError):
                MODULE.parse_version(text)

    def test_comparison_is_by_integer_tuple_not_by_string(self) -> None:
        self.assertGreater(MODULE.parse_version("2.10.0"), MODULE.parse_version("2.9.0"))
        self.assertLess("2.10.0", "2.9.0")  # a comparação textual erraria


class ChangeSet(unittest.TestCase):
    def test_any_path_under_plugin_counts(self) -> None:
        self.assertTrue(MODULE.touches_plugin([PLUGIN_FILE]))
        self.assertTrue(MODULE.touches_plugin([*OUTSIDE, MANIFEST_FILE]))
        self.assertTrue(MODULE.touches_plugin(["plugin/hooks/hooks.json"]))

    def test_paths_outside_the_bundle_do_not_count(self) -> None:
        self.assertFalse(MODULE.touches_plugin(OUTSIDE))
        self.assertFalse(MODULE.touches_plugin([]))
        self.assertFalse(MODULE.touches_plugin(["docs/plugin/notes.md", "plugin-notes.md"]))


class HandoffScenarios(unittest.TestCase):
    """CEN-1 a CEN-4 de checklists/acceptance.md."""

    def test_cen1_change_outside_the_bundle_needs_no_bump(self) -> None:
        result = MODULE.decide(OUTSIDE, "2.5.0", "2.5.0")
        self.assertEqual((result.verdict, result.code), ("PASS", "NO-PLUGIN-CHANGE"))
        self.assertEqual(MODULE.exit_code(result), 0)

    def test_cen2_bundle_change_without_bump_fails(self) -> None:
        result = MODULE.decide([PLUGIN_FILE, *OUTSIDE], "2.5.0", "2.5.0")
        self.assertEqual((result.verdict, result.code), ("FAIL", "MISSING-BUMP"))
        self.assertEqual(MODULE.exit_code(result), 1)

    def test_cen3_bundle_change_with_bump_passes(self) -> None:
        result = MODULE.decide([PLUGIN_FILE], "2.5.0", "2.6.0")
        self.assertEqual((result.verdict, result.code), ("PASS", "BUMPED"))
        self.assertEqual(MODULE.exit_code(result), 0)

    def test_cen4_bundle_change_with_lowered_version_fails(self) -> None:
        result = MODULE.decide([PLUGIN_FILE], "2.5.0", "2.4.9")
        self.assertEqual((result.verdict, result.code), ("FAIL", "VERSION-REGRESSION"))
        self.assertEqual(MODULE.exit_code(result), 1)


class FailureMessage(unittest.TestCase):
    def test_every_failure_names_both_versions_and_the_requirement(self) -> None:
        for base, head in (("2.5.0", "2.5.0"), ("2.5.0", "2.4.0")):
            result = MODULE.decide([PLUGIN_FILE], base, head)
            self.assertEqual(result.verdict, "FAIL")
            self.assertEqual((result.base_version, result.head_version), (base, head))
            self.assertIn(base, result.message)
            self.assertIn(head, result.message)
            self.assertIn("precisa aumentar", result.message)

    def test_unreadable_version_still_states_the_requirement(self) -> None:
        result = MODULE.decide([PLUGIN_FILE], None, "2.5")
        self.assertIn("2.5", result.message)
        self.assertIn("ausente", result.message)
        self.assertIn("precisa aumentar", result.message)


class UnreadableVersion(unittest.TestCase):
    def test_absent_version_on_either_side_fails_with_exit_two(self) -> None:
        for base, head in ((None, "2.6.0"), ("2.5.0", None), (None, None)):
            result = MODULE.decide([PLUGIN_FILE], base, head)
            self.assertEqual((result.verdict, result.code), ("FAIL", "VERSION-UNREADABLE"))
            self.assertEqual(MODULE.exit_code(result), 2)

    def test_malformed_version_fails_with_exit_two(self) -> None:
        for base, head in (("2.5", "2.6.0"), ("2.5.0", "v2.6.0"), ("2.5.0", "2.6.0-rc1")):
            result = MODULE.decide([PLUGIN_FILE], base, head)
            self.assertEqual((result.verdict, result.code), ("FAIL", "VERSION-UNREADABLE"))
            self.assertEqual(MODULE.exit_code(result), 2)

    def test_unreadable_version_outside_the_bundle_is_not_a_failure(self) -> None:
        result = MODULE.decide(OUTSIDE, None, None)
        self.assertEqual((result.verdict, result.code), ("PASS", "NO-PLUGIN-CHANGE"))


class Boundaries(unittest.TestCase):
    def test_deleting_a_bundle_file_requires_a_bump(self) -> None:
        # git diff --name-only lista a remoção como um caminho, igual a uma edição.
        result = MODULE.decide(["plugin/skills/grill-with-docs/references/removed.md"], "2.5.0", "2.5.0")
        self.assertEqual(result.code, "MISSING-BUMP")

    def test_change_only_under_tests_requires_no_bump(self) -> None:
        result = MODULE.decide(["tests/validate_bump_gate_contract.py", "tests/run_validators.py"], "2.5.0", "2.5.0")
        self.assertEqual((result.verdict, result.code), ("PASS", "NO-PLUGIN-CHANGE"))

    def test_the_version_itself_as_the_only_bundle_change_is_a_bump(self) -> None:
        result = MODULE.decide([MANIFEST_FILE], "2.5.0", "2.5.1")
        self.assertEqual((result.verdict, result.code), ("PASS", "BUMPED"))
        self.assertEqual(MODULE.exit_code(result), 0)

    def test_patch_minor_and_major_increases_all_count(self) -> None:
        for head in ("2.5.1", "2.6.0", "3.0.0", "2.10.0"):
            self.assertEqual(MODULE.decide([PLUGIN_FILE], "2.9.0" if head == "2.10.0" else "2.5.0", head).code, "BUMPED")

    def test_the_pure_layer_never_shells_out(self) -> None:
        def forbidden(*args, **kwargs):
            raise AssertionError("a camada pura não pode chamar git")

        original = MODULE.subprocess.run
        MODULE.subprocess.run = forbidden
        try:
            MODULE.decide([PLUGIN_FILE], "2.5.0", "2.5.0")
            MODULE.touches_plugin([PLUGIN_FILE])
            MODULE.parse_version("2.5.0")
        finally:
            MODULE.subprocess.run = original


class CommandLine(unittest.TestCase):
    """A CLI é exercitada com a camada de git substituída, para rodar sem repositório."""

    def setUp(self) -> None:
        self.original = (MODULE.changed_paths, MODULE.read_version)

    def tearDown(self) -> None:
        MODULE.changed_paths, MODULE.read_version = self.original

    def run_cli(self, argv, paths, versions):
        MODULE.changed_paths = lambda base, head: list(paths)
        MODULE.read_version = lambda rev: versions[rev]
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = MODULE.main(argv)
        return code, stream.getvalue()

    def test_json_mode_emits_exactly_one_line_and_exit_one_on_missing_bump(self) -> None:
        code, output = self.run_cli(
            ["--base-ref", "origin/main", "--json"],
            [PLUGIN_FILE],
            {"origin/main": "2.5.0", "HEAD": "2.5.0"},
        )
        lines = output.strip().splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["verdict"], "FAIL")
        self.assertEqual(payload["code"], "MISSING-BUMP")
        self.assertEqual(payload["base_version"], "2.5.0")
        self.assertEqual(payload["head_version"], "2.5.0")
        self.assertIn("precisa aumentar", payload["message"])
        self.assertEqual(code, 1)

    def test_text_mode_passes_with_zero_when_the_bundle_is_untouched(self) -> None:
        code, output = self.run_cli(
            ["--base-ref", "origin/main", "--head-ref", "feature"],
            OUTSIDE,
            {"origin/main": "2.5.0", "feature": "2.5.0"},
        )
        self.assertEqual(code, 0)
        self.assertIn("NO-PLUGIN-CHANGE", output)

    def test_regression_exits_one_and_unreadable_exits_two(self) -> None:
        code, _ = self.run_cli(
            ["--base-ref", "main"], [PLUGIN_FILE], {"main": "2.5.0", "HEAD": "2.4.0"})
        self.assertEqual(code, 1)
        code, output = self.run_cli(
            ["--base-ref", "main", "--json"], [PLUGIN_FILE], {"main": "2.5.0", "HEAD": None})
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["code"], "VERSION-UNREADABLE")

    def test_an_unusable_base_ref_is_a_failure_not_a_pass(self) -> None:
        def broken(base, head):
            raise MODULE.GitError("unknown revision")

        MODULE.changed_paths = broken
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = MODULE.main(["--base-ref", "deadbeef", "--json"])
        payload = json.loads(stream.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(payload["verdict"], "FAIL")
        self.assertEqual(payload["code"], "VERSION-UNREADABLE")

    def test_a_missing_base_ref_argument_is_a_usage_error(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                MODULE.main([])
        self.assertEqual(raised.exception.code, 2)

    def test_no_flag_can_approve_a_bundle_change_without_a_bump(self) -> None:
        # Fail-closed: nenhum código de saída significa "não verificado".
        self.assertEqual(set(MODULE.EXIT_CODES.values()), {0, 1, 2})
        self.assertEqual(
            {code for code, status in MODULE.EXIT_CODES.items() if status == 0},
            {"NO-PLUGIN-CHANGE", "BUMPED"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=1, argv=[sys.argv[0], *sys.argv[1:]])
