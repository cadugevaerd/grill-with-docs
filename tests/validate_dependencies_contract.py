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

    def test_extensions_are_missing_without_specify_and_never_probe_it(self) -> None:
        tools = StubToolchain()
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        self.assertEqual(self.report(reports, "ext:git")["status"], "missing")
        self.assertNotIn(["extension", "list"], [call[1:] for call in tools.calls])

    def test_extension_list_is_read_once_and_empty_state_is_not_a_match(self) -> None:
        tools = StubToolchain(
            binaries={"specify": "/stub/specify"},
            outputs={
                ("/stub/specify", "--version"): (0, "specify 0.15.1"),
                ("/stub/specify", "extension", "list"): (0, "No extensions installed. add git"),
            },
        )
        reports = MODULE.detect(self.root, MODULE.load_manifest(), tools)
        self.assertEqual(self.report(reports, "ext:git")["status"], "missing")
        self.assertEqual(sum(1 for call in tools.calls if call[1:] == ["extension", "list"]), 1)

    def test_installed_extension_is_detected(self) -> None:
        tools = StubToolchain(
            binaries={"specify": "/stub/specify"},
            outputs={
                ("/stub/specify", "--version"): (0, "specify 0.15.1"),
                ("/stub/specify", "extension", "list"): (0, "git (v1.0.0)\nverify-review-ship (v0.4.2)\n"),
            },
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


if __name__ == "__main__":
    unittest.main(verbosity=1, argv=[sys.argv[0], *sys.argv[1:]])
