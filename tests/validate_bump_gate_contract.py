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
import os
import subprocess
import sys
import tempfile
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


class GitLayer(unittest.TestCase):
    """A camada de git é exercitada capturando o argv, sem repositório."""

    def setUp(self) -> None:
        self.original = MODULE.git
        self.calls: list[list[str]] = []

    def tearDown(self) -> None:
        MODULE.git = self.original

    def capture(self, output: str = "") -> None:
        def fake(argv):
            self.calls.append(list(argv))
            return output

        MODULE.git = fake

    def test_diff_disables_rename_detection(self) -> None:
        """Regressão: com rename detection, mover um arquivo para fora de plugin/
        reportaria só o destino, e a remoção de conteúdo do bundle passaria como
        se nada no bundle tivesse mudado."""
        self.capture()
        MODULE.changed_paths("base", "head")
        self.assertEqual(len(self.calls), 1)
        self.assertIn("--no-renames", self.calls[0])

    def test_diff_uses_the_merge_base_not_the_tip(self) -> None:
        self.capture()
        MODULE.changed_paths("base", "head")
        self.assertIn("base...head", self.calls[0])
        self.assertNotIn("base..head", self.calls[0])

    def test_a_move_out_of_the_bundle_requires_a_bump(self) -> None:
        """O par que o --no-renames produz: origem sob plugin/, destino fora."""
        paths = ["docs-attribution.md", "plugin/skills/grill-with-docs/references/upstream-attribution.md"]
        self.assertTrue(MODULE.touches_plugin(paths))
        self.assertEqual(MODULE.decide(paths, "2.5.0", "2.5.0").code, "MISSING-BUMP")


class RealGit(unittest.TestCase):
    """Exercita o binário git de verdade.

    Os demais testes substituem a camada de git, então uma mudança de flag que
    quebrasse o comportamento real passaria por eles: a asserção sobre argv
    continuaria valendo. Este teste fecha essa lacuna — foi exatamente por ela
    que o bypass de rename chegou a existir com a suíte verde.
    """

    def setUp(self) -> None:
        # Git owns this tree and keeps working in it: background maintenance can
        # write into .git/objects while the directory is being removed, and the
        # teardown then dies with "Directory not empty" for a reason that has
        # nothing to do with the assertion. Third instance of the SGD-12 family.
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name)
        self.previous = os.getcwd()
        self.git("init", "-q", "-b", "main", ".")
        self.git("config", "user.email", "gate@example.invalid")
        self.git("config", "user.name", "bump gate tests")
        self.write(MANIFEST_FILE, '{"name": "p", "version": "2.5.0"}\n')
        self.write(PLUGIN_FILE, "conteúdo distribuído\n")
        self.write("tests/algum_teste.py", "# fora do bundle\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()
        os.chdir(self.root)

    def tearDown(self) -> None:
        os.chdir(self.previous)
        self.temporary.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True,
                              text=True, check=True).stdout

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit_all(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def verdict(self):
        return MODULE.decide(MODULE.changed_paths(self.base, "HEAD"),
                             MODULE.read_version(self.base), MODULE.read_version("HEAD"))

    def test_move_out_of_the_bundle_is_caught_against_real_git(self) -> None:
        """Regressão do bypass: sem --no-renames o git reportaria só o destino."""
        self.git("mv", PLUGIN_FILE, "docs_movido.md")
        self.commit_all("move para fora do bundle")
        paths = MODULE.changed_paths(self.base, "HEAD")
        self.assertIn(PLUGIN_FILE, paths)
        self.assertEqual(self.verdict().code, "MISSING-BUMP")

    def test_plain_deletion_is_caught_against_real_git(self) -> None:
        self.git("rm", "-q", PLUGIN_FILE)
        self.commit_all("remove do bundle")
        self.assertEqual(self.verdict().code, "MISSING-BUMP")

    def test_change_outside_the_bundle_passes_against_real_git(self) -> None:
        self.write("tests/algum_teste.py", "# alterado\n")
        self.commit_all("muda fora do bundle")
        self.assertEqual(self.verdict().code, "NO-PLUGIN-CHANGE")

    def test_bundle_change_with_bump_passes_against_real_git(self) -> None:
        self.write(PLUGIN_FILE, "conteúdo alterado\n")
        self.write(MANIFEST_FILE, '{"name": "p", "version": "2.6.0"}\n')
        self.commit_all("muda o bundle com bump")
        self.assertEqual(self.verdict().code, "BUMPED")

    def test_cli_exits_one_against_real_git_when_the_bump_is_missing(self) -> None:
        self.write(PLUGIN_FILE, "conteúdo alterado\n")
        self.commit_all("muda o bundle sem bump")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = MODULE.main(["--base-ref", self.base, "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stream.getvalue())["code"], "MISSING-BUMP")

    def test_unreachable_base_fails_closed_against_real_git(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = MODULE.main(["--base-ref", "0" * 40, "--json"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stream.getvalue())["code"], "VERSION-UNREADABLE")


class WorkflowWiring(unittest.TestCase):
    """O gate só bloqueia se reportar sempre — e só reporta se escapar do filtro.

    A migração tirou o job de um workflow e o pôs em outro. Errar o arquivo novo
    deixaria o repositório sem gate nenhum, sem sintoma nenhum, até alguém
    integrar conteúdo distribuído sem subir a versão.
    """

    ROOT = TESTS.parent
    GATE = ROOT / ".github/workflows/bump-gate.yml"
    CI = ROOT / ".github/workflows/ci.yml"
    PUBLISH = ROOT / ".github/workflows/publish.yml"
    CONSTITUTION = ROOT / ".specify/memory/constitution.md"

    def load_yaml(self, path: Path) -> dict:
        try:
            import yaml
        except ImportError:  # pragma: no cover - a matriz de CI não instala pyyaml
            self.skipTest("pyyaml indisponível")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def triggers(self, document: dict) -> dict:
        # PyYAML lê o `on:` do GitHub Actions como o booleano True.
        return document[True] if True in document else document["on"]

    def test_the_gate_lives_in_its_own_workflow(self) -> None:
        self.assertTrue(self.GATE.is_file(), self.GATE)

    def test_the_gate_has_no_path_filter(self) -> None:
        triggers = self.triggers(self.load_yaml(self.GATE))
        self.assertIn("pull_request", triggers)
        pull_request = triggers["pull_request"] or {}
        self.assertNotIn("paths", pull_request)
        self.assertNotIn("paths-ignore", pull_request)

    def test_the_gate_keeps_full_history_and_the_payload_base(self) -> None:
        document = self.load_yaml(self.GATE)
        job = next(iter(document["jobs"].values()))
        checkout = next(s for s in job["steps"] if "checkout" in str(s.get("uses", "")))
        self.assertEqual(checkout["with"]["fetch-depth"], 0)
        enforce = next(s for s in job["steps"] if "check_version_bump.py" in str(s.get("run", "")))
        self.assertEqual(enforce["env"]["BASE_SHA"], "${{ github.event.pull_request.base.sha }}")
        self.assertNotIn("github.base_ref", str(enforce))

    def test_publish_rechecks_a_main_push_before_creating_an_immutable_tag(self) -> None:
        document = self.load_yaml(self.PUBLISH)
        release = document["jobs"]["release"]
        checkout = next(step for step in release["steps"] if "checkout" in str(step.get("uses", "")))
        self.assertEqual(checkout["with"]["fetch-depth"], 0)
        enforce_index, enforce = next(
            (index, step)
            for index, step in enumerate(release["steps"])
            if "check_version_bump.py" in str(step.get("run", ""))
        )
        tag_index = next(
            index for index, step in enumerate(release["steps"])
            if step.get("name") == "Criar a tag, recusando remarcação"
        )
        self.assertLess(enforce_index, tag_index)
        self.assertEqual(enforce["if"], "${{ github.event_name == 'push' }}")
        self.assertEqual(enforce["env"]["BASE_SHA"], "${{ github.event.before }}")
        self.assertEqual(enforce["env"]["HEAD_SHA"], "${{ github.sha }}")
        self.assertIn('--base-ref "$BASE_SHA" --head-ref "$HEAD_SHA"', enforce["run"])

    def test_constitution_requires_a_semver_bump_for_distributed_changes(self) -> None:
        text = self.CONSTITUTION.read_text(encoding="utf-8")
        self.assertIn("- version: 1.1.0", text)
        self.assertIn("### Bump obrigatório do plugin", text)
        self.assertIn("`plugin/**` MUST incrementar a versão SemVer", text)
        self.assertIn("antes da tag de publicação", text)

    def test_the_matrix_workflow_no_longer_owns_the_gate(self) -> None:
        document = self.load_yaml(self.CI)
        self.assertNotIn("bump-gate", document["jobs"])
        self.assertNotIn("check_version_bump", self.CI.read_text(encoding="utf-8"))

    def test_the_matrix_keeps_its_path_filter_and_its_dedup_guard(self) -> None:
        document = self.load_yaml(self.CI)
        triggers = self.triggers(document)
        self.assertIn("paths", triggers["pull_request"])
        contract = document["jobs"]["contract"]
        self.assertIn("Merge pull request", contract["if"])

    def test_no_job_reports_success_without_running_the_gate(self) -> None:
        """Um shim que aprova quando o gate foi pulado torna aprovado
        indistinguível de não-executado."""
        for path in (self.GATE, self.CI):
            document = self.load_yaml(path)
            for name, job in document["jobs"].items():
                steps = job.get("steps", [])
                self.assertTrue(steps, (path.name, name))
                for step in steps:
                    self.assertNotIn("exit 0", str(step.get("run", "")))

    def test_both_workflows_have_valid_shell(self) -> None:
        for path in (self.GATE, self.CI):
            document = self.load_yaml(path)
            for job in document["jobs"].values():
                for step in job.get("steps", []):
                    script = step.get("run")
                    if not script:
                        continue
                    checked = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
                    self.assertEqual(checked.returncode, 0, (path.name, step.get("name"), checked.stderr))


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
