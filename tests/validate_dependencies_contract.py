#!/usr/bin/env python3
"""Executable contract for the delegated dependency preflight."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"
SCRIPT = PLUGIN / "skills/grill-with-docs/scripts/ensure_dependencies.py"
MANIFEST = PLUGIN / "skills/grill-with-docs/assets/dependencies.json"


def load() -> object:
    spec = importlib.util.spec_from_file_location("ensure_dependencies_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load()


class StubToolchain(MODULE.Toolchain):
    """Every external effect replaced by a recording table."""

    def __init__(self, *, binaries=None, outputs=None, environ=None, installer="/stub/ensure-backlogctl.js"):
        super().__init__(environ or {"HOME": "/nonexistent-home"})
        self.binaries = binaries or {}
        self.outputs = outputs or {}
        self.installer = installer
        self.calls: list[list[str]] = []

    def which(self, command):
        return self.binaries.get(command)

    def run(self, argv, *, cwd=None, timeout=None):
        self.calls.append(list(argv))
        return self.outputs.get(tuple(argv), (0, ""))

    def backlog_installer(self):
        return self.installer


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


class DependencyManifest(unittest.TestCase):
    def test_bundled_manifest_is_valid_and_installs_are_argv_lists(self) -> None:
        loaded = MODULE.load_manifest()
        self.assertEqual(loaded["schema"], MODULE.SCHEMA)
        identifiers = [entry["id"] for entry in loaded["dependencies"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for entry in loaded["dependencies"]:
            self.assertIn(entry["kind"], MODULE.KINDS)
            for command in entry.get("install") or []:
                self.assertIsInstance(command, list)
                self.assertTrue(all(isinstance(part, str) for part in command))

    def test_manifest_rejects_schema_duplicate_kind_and_install_shape(self) -> None:
        for mutate in (
            lambda data: data.update(schema="other/v9"),
            lambda data: data.update(dependencies=[]),
            lambda data: data["dependencies"].append(dict(data["dependencies"][0])),
            lambda data: data["dependencies"][0].update(kind="magic"),
            lambda data: data["dependencies"][2].update(install=["not-a-list"]),
        ):
            data = manifest()
            mutate(data)
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "dependencies.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(MODULE.ManifestError):
                    MODULE.load_manifest(path)


class VersionComparison(unittest.TestCase):
    def test_parses_real_tool_banners(self) -> None:
        self.assertEqual(MODULE.parse_version("git version 2.43.0"), (2, 43, 0))
        self.assertEqual(MODULE.parse_version("specify 0.15.1"), (0, 15, 1))
        self.assertEqual(MODULE.parse_version("2.3.0"), (2, 3, 0))
        self.assertIsNone(MODULE.parse_version("no digits here"))

    def test_floor_is_inclusive_and_missing_version_never_passes(self) -> None:
        self.assertTrue(MODULE.meets((0, 11, 2), "0.11.2"))
        self.assertFalse(MODULE.meets((0, 11, 1), "0.11.2"))
        self.assertTrue(MODULE.meets(None, None))
        self.assertFalse(MODULE.meets(None, "1.0.0"))


class Detection(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def report(self, reports, identifier):
        return next(item for item in reports if item["id"] == identifier)

    def test_missing_binary_reports_remediation_and_no_version(self) -> None:
        tools = StubToolchain()
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        specify = self.report(reports, "specify")
        self.assertEqual(specify["status"], "missing")
        self.assertIsNone(specify["version"])
        self.assertIn("uv tool install", specify["remediation"])

    def test_outdated_binary_is_not_present(self) -> None:
        tools = StubToolchain(
            binaries={"specify": "/stub/specify"},
            outputs={("/stub/specify", "--version"): (0, "specify 0.9.0")},
        )
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        self.assertEqual(self.report(reports, "specify")["status"], "outdated")

    def test_env_override_wins_over_path_for_declared_binaries(self) -> None:
        executable = self.root / "backlogctl"
        executable.write_text("#!/bin/sh\n", encoding="utf-8")
        tools = StubToolchain(
            environ={"HOME": str(self.root), "BACKLOGCTL_EXECUTABLE": str(executable)},
            outputs={(str(executable), "version"): (0, "2.4.0")},
        )
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        backlog = self.report(reports, "backlogctl")
        self.assertEqual(backlog["status"], "present")
        self.assertEqual(backlog["source"], str(executable))

    def test_path_dependency_follows_the_repository(self) -> None:
        tools = StubToolchain()
        self.assertEqual(self.report(MODULE.detect(self.root, MODULE.load_manifest(), tools), "spec-kit-scaffold")["status"], "missing")
        scaffold = self.root / ".specify/templates"
        scaffold.mkdir(parents=True)
        (scaffold / "spec-template.md").write_text("x", encoding="utf-8")
        self.assertEqual(self.report(MODULE.detect(self.root, MODULE.load_manifest(), tools), "spec-kit-scaffold")["status"], "present")

    def test_path_dependency_with_contains_requires_the_marker(self) -> None:
        tools = StubToolchain()
        catalogs = self.root / ".specify/extension-catalogs.yml"
        catalogs.parent.mkdir(parents=True)
        catalogs.write_text("catalogs:\n- name: community\n  install_allowed: false\n", encoding="utf-8")
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        self.assertEqual(self.report(reports, "spec-kit-community-catalog")["status"], "missing")
        catalogs.write_text("catalogs:\n- name: community\n  install_allowed: true\n", encoding="utf-8")
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        self.assertEqual(self.report(reports, "spec-kit-community-catalog")["status"], "present")

    def test_trusted_catalog_is_installed_before_the_community_extensions(self) -> None:
        order = [entry["id"] for entry in MODULE.load_manifest()["dependencies"]]
        catalog = order.index("spec-kit-community-catalog")
        for identifier in ("ext:agent-assign", "ext:bugfix", "ext:verify-review-ship"):
            self.assertLess(catalog, order.index(identifier))

    def write_registry(self, extensions, *, schema_version="1.0") -> None:
        target = self.root / MODULE.EXTENSION_REGISTRY
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": schema_version, "extensions": extensions}
        target.write_text(json.dumps(payload), encoding="utf-8")

    def test_extensions_are_undetermined_without_a_registry_and_never_probe_specify(self) -> None:
        tools = StubToolchain()
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        # No registry means nothing was observed. Absence of `specify` is no
        # longer relevant: the source is a file, not a subprocess.
        self.assertEqual(self.report(reports, "ext:git")["status"], "undetermined")
        self.assertNotIn(["extension", "list"], [call[1:] for call in tools.calls])

    def test_empty_registry_is_absence_and_the_cli_is_never_consulted(self) -> None:
        tools = StubToolchain(
            binaries={"specify": "/stub/specify"},
            outputs={("/stub/specify", "--version"): (0, "specify 0.15.1")},
        )
        self.write_registry({})
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        # A readable but empty registry is observed absence, not indetermination.
        self.assertEqual(self.report(reports, "ext:git")["status"], "missing")
        self.assertEqual([call for call in tools.calls if "extension" in call], [])

    def test_installed_extension_is_detected_and_a_decoy_description_is_not(self) -> None:
        tools = StubToolchain(
            binaries={"specify": "/stub/specify"},
            outputs={("/stub/specify", "--version"): (0, "specify 0.15.1")},
        )
        # The old fixture fed clean text — `git (v1.0.0)` — which the terminal
        # never actually emits. That is why the parser passed the suite and
        # failed reality, so the decoy below is the point of this test.
        self.write_registry(
            {
                "git": {"version": "1.0.0", "enabled": True,
                        "description": "Structured bugfix workflow - capture bugs"},
                "verify-review-ship": {"version": "0.4.2", "enabled": True},
            }
        )
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        self.assertEqual(self.report(reports, "ext:git")["status"], "present")
        self.assertEqual(self.report(reports, "ext:verify-review-ship")["status"], "present")
        self.assertEqual(self.report(reports, "ext:bugfix")["status"], "missing")

    def test_unresolvable_installer_placeholder_is_reported_verbatim(self) -> None:
        tools = StubToolchain(installer=None)
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        self.assertIn(MODULE.BACKLOG_INSTALLER, self.report(reports, "backlogctl")["remediation"])


class InstallDelegation(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_preview_never_runs_a_declared_installer(self) -> None:
        tools = StubToolchain()
        payload = MODULE.preflight(self.root, allow_install=False, tools=tools)
        self.assertEqual(payload["verdict"], "MISSING-DEPENDENCY")
        self.assertNotIn("installed", payload)
        declared = {tuple(command) for entry in MODULE.load_manifest()["dependencies"] for command in entry.get("install") or []}
        for call in tools.calls:
            self.assertNotIn(tuple(call), declared)

    def test_install_runs_only_manifest_commands_and_expands_the_placeholder(self) -> None:
        tools = StubToolchain()
        payload = MODULE.preflight(self.root, allow_install=True, tools=tools)
        declared = [command for entry in MODULE.load_manifest()["dependencies"] for command in entry.get("install") or []]
        expanded = {tuple(MODULE.expand(command, tools)) for command in declared}
        installers = [call for call in tools.calls if tuple(call) in expanded]
        self.assertTrue(installers)
        self.assertIn(["node", tools.installer], tools.calls)
        self.assertIn("installed", payload)

    def test_failed_installer_is_reported_and_stops_that_entry(self) -> None:
        tools = StubToolchain(outputs={("node", "/stub/ensure-backlogctl.js"): (1, "boom")})
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        results = MODULE.install(self.root, MODULE.load_manifest(), reports, tools)
        backlog = next(item for item in results if item["id"] == "backlogctl")
        self.assertEqual(backlog["status"], "FAILED")
        self.assertEqual(backlog["commands"][-1]["returncode"], 1)

    def test_unresolvable_placeholder_blocks_that_entry_without_running_anything(self) -> None:
        tools = StubToolchain(installer=None)
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        results = MODULE.install(self.root, MODULE.load_manifest(), reports, tools)
        backlog = next(item for item in results if item["id"] == "backlogctl")
        self.assertEqual(backlog["status"], "BLOCKED")
        self.assertNotIn("node", [call[0] for call in tools.calls])

    def test_entry_without_installer_is_skipped_not_failed(self) -> None:
        tools = StubToolchain()
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        results = MODULE.install(self.root, MODULE.load_manifest(), reports, tools)
        git = next((item for item in results if item["id"] == "git"), None)
        if git is not None:
            self.assertEqual(git["status"], "SKIPPED")

    def test_explicit_skip_is_never_reported_as_ok(self) -> None:
        tools = StubToolchain(environ={"HOME": "/nonexistent-home", MODULE.SKIP_ENV: "1"})
        payload = MODULE.preflight(self.root, allow_install=True, tools=tools)
        self.assertEqual(payload["verdict"], "SKIPPED")
        self.assertEqual(payload["dependencies"], [])
        self.assertEqual(tools.calls, [])


class CommandLine(unittest.TestCase):
    def test_cli_emits_one_json_line_and_maps_the_verdict_to_the_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            process = subprocess.run(
                [sys.executable, str(SCRIPT), temporary],
                capture_output=True, text=True, check=False,
                env={"PATH": "/nonexistent-path", "HOME": temporary, "SystemRoot": "C:\\Windows"},
            )
        lines = process.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["schema"], MODULE.SCHEMA)
        self.assertEqual(payload["verdict"], "MISSING-DEPENDENCY")
        self.assertEqual(process.returncode, 1)


class ShadowedSkills(unittest.TestCase):
    """FASE-006 — a shadowed plugin name stops being silent."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        self.home = Path(self.temporary.name) / "home"
        (self.root / ".claude" / "skills").mkdir(parents=True)
        (self.home / ".claude" / "skills").mkdir(parents=True)
        self.environ = {"HOME": str(self.home)}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def detect(self):
        return MODULE.detect_shadowed_skills(self.root, self.environ)

    def personal(self) -> Path:
        return self.home / ".claude" / "skills" / "grill-with-docs"

    def test_a_clean_environment_raises_no_alarm(self) -> None:
        self.assertEqual(self.detect(), [])

    def test_a_personal_directory_with_a_published_name_is_a_shadow(self) -> None:
        self.personal().mkdir()
        found = self.detect()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["skill"], "grill-with-docs")
        self.assertEqual(found[0]["kind"], "directory")

    def test_a_project_skill_with_a_published_name_is_a_shadow(self) -> None:
        (self.root / ".claude" / "skills" / "grill-with-docs").mkdir()
        self.assertEqual(len(self.detect()), 1)

    def test_a_third_party_name_is_never_reported(self) -> None:
        (self.home / ".claude" / "skills" / "something-else").mkdir()
        self.assertEqual(self.detect(), [])

    def test_a_symlink_shadow_reports_its_target(self) -> None:
        target = self.home / ".agents" / "skills" / "grill-with-docs"
        target.mkdir(parents=True)
        try:
            self.personal().symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        found = [entry for entry in self.detect() if entry["kind"] == "symlink"]
        self.assertEqual(len(found), 1)
        self.assertEqual(Path(found[0]["target"]).name, "grill-with-docs")
        self.assertFalse(found[0]["broken"])

    def test_a_broken_symlink_still_occupies_the_name(self) -> None:
        try:
            self.personal().symlink_to(self.home / "gone", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        found = self.detect()
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["broken"])

    def test_every_shadow_is_reported_not_only_the_first(self) -> None:
        self.personal().mkdir()
        (self.root / ".claude" / "skills" / "grill-with-docs").mkdir()
        self.assertEqual(len(self.detect()), 2)

    def test_a_missing_skills_directory_is_not_an_error(self) -> None:
        MODULE.detect_shadowed_skills(Path(self.temporary.name) / "absent", {"HOME": str(self.home / "absent")})

    def test_removal_takes_the_symlink_and_leaves_the_target(self) -> None:
        target = self.home / ".agents" / "skills" / "grill-with-docs"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("x", encoding="utf-8")
        try:
            self.personal().symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        entry = next(e for e in self.detect() if e["kind"] == "symlink")
        self.assertTrue(MODULE.remove_shadowed_skill(entry)["removed"])
        self.assertFalse(self.personal().is_symlink())
        self.assertTrue((target / "SKILL.md").is_file())

    def test_removal_of_a_directory_shadow_takes_the_whole_directory(self) -> None:
        # Destructive and irreversible: there is no smaller thing to remove when
        # the shadow is a real directory. The contract has to say so plainly.
        self.personal().mkdir()
        (self.personal() / "SKILL.md").write_text("x", encoding="utf-8")
        self.assertTrue(MODULE.remove_shadowed_skill(self.detect()[0])["removed"])
        self.assertEqual(self.detect(), [])

    def test_authorising_an_install_never_removes_a_shadow(self) -> None:
        # allow_install authorises delegated installs and the backlog bind.
        # Deleting a directory outside the repository is a different act, and
        # hiding it behind a flag that does not name it is an implicit waiver.
        self.personal().mkdir()
        (self.personal() / "SKILL.md").write_text("nao apague", encoding="utf-8")
        payload = MODULE.preflight(self.root, allow_install=True, tools=StubToolchain(environ=self.environ),
                                   manifest={"dependencies": []})
        self.assertTrue((self.personal() / "SKILL.md").is_file())
        self.assertEqual([entry.get("removed") for entry in payload["shadowed_skills"]], [None])

    def test_the_dedicated_flag_is_what_removes(self) -> None:
        self.personal().mkdir()
        (self.personal() / "SKILL.md").write_text("x", encoding="utf-8")
        payload = MODULE.preflight(self.root, remove_shadows=True, tools=StubToolchain(environ=self.environ),
                                   manifest={"dependencies": []})
        self.assertEqual([entry["removed"] for entry in payload["shadowed_skills"]], [True])
        self.assertFalse(self.personal().exists())

    def test_a_failed_removal_is_named_and_does_not_raise(self) -> None:
        result = MODULE.remove_shadowed_skill({"skill": "grill-with-docs",
                                               "path": str(self.home / "does-not-exist"), "kind": "directory"})
        self.assertFalse(result["removed"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main(verbosity=1, argv=[sys.argv[0], *sys.argv[1:]])
