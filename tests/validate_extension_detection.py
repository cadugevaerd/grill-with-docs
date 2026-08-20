#!/usr/bin/env python3
"""Executable contract for extension detection.

The preflight answers one question about each extension the workflow requires:
is it usable? It used to answer by tokenising the terminal output of
``specify extension list``, which failed twice over — the ANSI escape on the
slug line yielded ``2mgit`` instead of ``git``, and the whole-output scan let a
word inside a description line pass for an identifier.

The fixtures here deliberately carry the escapes and the decoy descriptions the
old suite lacked. A fixture cleaner than reality validates the parser instead of
exercising it, which is precisely how the defect survived 1066 tests.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"
SCRIPT = PLUGIN / "skills/grill-with-docs/scripts/ensure_dependencies.py"

REGISTRY_PATH = ".specify/extensions/.registry"
REQUIRED = ("git", "agent-assign", "bugfix", "verify-review-ship")


def load() -> object:
    spec = importlib.util.spec_from_file_location("ensure_dependencies_extension_detection", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load()


class RefusingToolchain(MODULE.Toolchain):
    """Fails the test if extension detection ever spawns a child process."""

    def __init__(self, *, binaries=None, outputs=None):
        super().__init__({"HOME": "/nonexistent-home"})
        self.binaries = binaries if binaries is not None else {"specify": "/stub/specify"}
        self.outputs = outputs or {("/stub/specify", "--version"): (0, "specify 0.15.1")}
        self.calls: list[list[str]] = []

    def which(self, command):
        return self.binaries.get(command)

    def run(self, argv, *, cwd=None, timeout=None):
        self.calls.append(list(argv))
        return self.outputs.get(tuple(argv), (0, ""))

    def backlog_installer(self):
        return "/stub/ensure-backlogctl.js"

    @property
    def extension_calls(self) -> list[list[str]]:
        return [call for call in self.calls if "extension" in call]


def entry(version: str = "1.0.0", *, enabled: bool = True, **extra) -> dict:
    payload = {"version": version, "enabled": enabled, "source": "local", "priority": 10}
    payload.update(extra)
    return payload


def registry(extensions: dict, *, schema_version: str = "1.0") -> dict:
    return {"schema_version": schema_version, "extensions": extensions}


def all_required(**overrides) -> dict:
    extensions = {slug: entry() for slug in REQUIRED}
    extensions.update(overrides)
    return registry(extensions)


class DetectionCase(unittest.TestCase):
    """Builds a root whose only interesting content is the extension registry."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / ".specify/extensions").mkdir(parents=True)
        self.addCleanup(self.temporary.cleanup)

    def write_registry(self, payload) -> None:
        target = self.root / REGISTRY_PATH
        text = payload if isinstance(payload, str) else json.dumps(payload)
        target.write_text(text, encoding="utf-8")

    def reports(self, tools=None) -> list[dict]:
        tools = tools or RefusingToolchain()
        self.tools = tools
        return MODULE.detect(self.root, MODULE.load_manifest(), tools)

    def report(self, reports: list[dict], identifier: str) -> dict:
        for item in reports:
            if item["id"] == identifier:
                return item
        raise AssertionError(f"missing report for {identifier}")

    def extension_reports(self, reports: list[dict]) -> list[dict]:
        return [item for item in reports if item["kind"] == "specify-extension"]


class SourceOfTruth(DetectionCase):
    """A. The registry is read; the CLI is never consulted."""

    def test_detection_never_spawns_specify_for_extensions(self) -> None:
        self.write_registry(all_required())
        reports = self.reports()
        self.assertEqual(self.tools.extension_calls, [])
        self.assertEqual(self.report(reports, "ext:git")["status"], "present")

    def test_slug_is_matched_as_a_key_not_as_free_text(self) -> None:
        self.write_registry(all_required())
        self.assertEqual(self.report(self.reports(), "ext:git")["status"], "present")

    def test_slug_inside_a_description_is_not_a_match(self) -> None:
        # A3 — regression for the original false positive: `bugfix` was reported
        # present because the phrase "Structured bugfix workflow" appears in the
        # description of the very extension being described.
        extensions = {slug: entry() for slug in REQUIRED if slug != "bugfix"}
        extensions["git"] = entry(description="Structured bugfix workflow - capture bugs and patch specs")
        self.write_registry(registry(extensions))
        self.assertEqual(self.report(self.reports(), "ext:bugfix")["status"], "missing")

    def test_ansi_wrapped_key_is_not_a_match(self) -> None:
        # A4 — the exact shape the old parser produced: \x1b[2mgit\x1b[0m
        extensions = {slug: entry() for slug in REQUIRED if slug != "git"}
        extensions["\x1b[2mgit\x1b[0m"] = entry()
        self.write_registry(registry(extensions))
        self.assertEqual(self.report(self.reports(), "ext:git")["status"], "missing")


class PerExtensionState(DetectionCase):
    """B. Registered and enabled is present; anything else is not usable."""

    def test_registered_and_enabled_is_present_with_version_and_registry_source(self) -> None:
        self.write_registry(all_required())
        git = self.report(self.reports(), "ext:git")
        self.assertEqual(git["status"], "present")
        self.assertEqual(git["version"], "1.0.0")
        self.assertIn(".registry", git["source"])

    def test_registered_but_disabled_blocks_and_remediation_enables(self) -> None:
        self.write_registry(all_required(git=entry(enabled=False)))
        git = self.report(self.reports(), "ext:git")
        self.assertEqual(git["status"], "missing")
        self.assertIn("desabilitada", git["reason"])
        self.assertIn("extension enable", git["remediation"])
        self.assertNotIn("extension add", git["remediation"])

    def test_absent_slug_reports_absence_and_remediation_installs(self) -> None:
        extensions = {slug: entry() for slug in REQUIRED if slug != "git"}
        self.write_registry(registry(extensions))
        git = self.report(self.reports(), "ext:git")
        self.assertEqual(git["status"], "missing")
        self.assertIn("extension add", git["remediation"])

    def test_malformed_record_is_not_reported_as_disabled(self) -> None:
        # B5 — blocking is right; calling it "disabled" would assert a state
        # that was never observed, which is the very error being fixed.
        extensions = {slug: entry() for slug in REQUIRED}
        extensions["git"] = {"version": "1.0.0"}
        self.write_registry(registry(extensions))
        git = self.report(self.reports(), "ext:git")
        self.assertEqual(git["status"], "missing")
        self.assertNotIn("desabilitada", git["reason"])
        self.assertIn("habilitacao", git["reason"])
        self.assertIn("extension add", git["remediation"])

    def test_missing_version_does_not_invalidate_presence(self) -> None:
        extensions = {slug: entry() for slug in REQUIRED}
        extensions["git"] = {"enabled": True}
        self.write_registry(registry(extensions))
        git = self.report(self.reports(), "ext:git")
        self.assertEqual(git["status"], "present")
        self.assertIsNone(git["version"])


class UnreadableRegistry(DetectionCase):
    """C. Not observed is not the same proposition as not installed."""

    UNREADABLE = (
        ("absent", None),
        ("invalid-json", "{not json"),
        ("unknown-schema", registry({slug: entry() for slug in REQUIRED}, schema_version="2.0")),
    )

    def prepare(self, payload) -> None:
        if payload is None:
            return
        self.write_registry(payload)

    def test_every_unreadable_shape_yields_undetermined_extensions(self) -> None:
        for label, payload in self.UNREADABLE:
            with self.subTest(label):
                self.setUp()
                self.prepare(payload)
                for item in self.extension_reports(self.reports()):
                    self.assertEqual(item["status"], "undetermined")

    def test_unreadable_shapes_agree_on_the_extension_slice(self) -> None:
        # C2/C3 — "the three shapes converge" is a verifiable claim, and
        # convergence is exactly what gets assumed instead of checked.
        seen = []
        for label, payload in self.UNREADABLE:
            self.setUp()
            self.prepare(payload)
            slice_ = [
                {key: item.get(key) for key in ("id", "status", "remediation", "version")}
                for item in self.extension_reports(self.reports())
            ]
            seen.append(slice_)
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(seen[1], seen[2])

    def test_undetermined_extensions_carry_no_remediation(self) -> None:
        for label, payload in self.UNREADABLE:
            with self.subTest(label):
                self.setUp()
                self.prepare(payload)
                for item in self.extension_reports(self.reports()):
                    self.assertNotIn("remediation", item)

    def test_no_extension_is_called_missing_when_nothing_was_observed(self) -> None:
        for label, payload in self.UNREADABLE:
            with self.subTest(label):
                self.setUp()
                self.prepare(payload)
                statuses = {item["status"] for item in self.extension_reports(self.reports())}
                self.assertNotIn("missing", statuses)

    def test_root_cause_is_named_once_with_its_own_remediation(self) -> None:
        for label, payload in self.UNREADABLE:
            with self.subTest(label):
                self.setUp()
                self.prepare(payload)
                reports = self.reports()
                registry_report = self.report(reports, "spec-kit-extension-registry")
                self.assertEqual(registry_report["status"], "missing")
                self.assertTrue(registry_report["remediation"])
                missing = [item["id"] for item in reports if item["status"] == "missing"]
                self.assertEqual(missing.count("spec-kit-extension-registry"), 1)

    def test_undetermined_blocks_the_verdict(self) -> None:
        tools = RefusingToolchain()
        payload = MODULE.preflight(self.root, tools=tools)
        self.assertEqual(payload["verdict"], "MISSING-DEPENDENCY")
        self.assertIn("spec-kit-extension-registry", payload["missing_required"])

    def test_allow_install_never_installs_over_an_unobserved_state(self) -> None:
        # C8 — the costliest failure mode: mutating the operator's environment
        # on the strength of something that was never observed.
        tools = RefusingToolchain()
        MODULE.preflight(self.root, allow_install=True, tools=tools)
        self.assertEqual([call for call in tools.calls if call[1:3] == ["extension", "add"]], [])


class HealthyEnvironment(DetectionCase):
    """D. The scenario that produced SGD-16 must now pass."""

    def test_all_required_registered_and_enabled_is_ok(self) -> None:
        self.write_registry(all_required())
        tools = RefusingToolchain()
        payload = MODULE.preflight(self.root, tools=tools)
        self.assertEqual([item for item in payload["missing_required"] if item.startswith("ext:")], [])
        self.assertEqual(tools.extension_calls, [])


class ContractShape(DetectionCase):
    """E/F. Schema, manifest ordering, and no parallel parser."""

    def test_schema_identifier_is_unchanged(self) -> None:
        self.assertEqual(MODULE.SCHEMA, "grill-dependencies/v1")

    def test_registry_is_declared_before_the_extensions_that_depend_on_it(self) -> None:
        order = [item["id"] for item in MODULE.load_manifest()["dependencies"]]
        position = order.index("spec-kit-extension-registry")
        for slug in REQUIRED:
            self.assertLess(position, order.index(f"ext:{slug}"))

    def test_every_required_extension_declares_an_enable_command(self) -> None:
        for item in MODULE.load_manifest()["dependencies"]:
            if item["kind"] == "specify-extension":
                self.assertEqual(item["enable"][:3], ["specify", "extension", "enable"])
                self.assertEqual(item["enable"][3], item["extension"])

    def test_the_terminal_output_parser_is_gone(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"extension", "list"', source)
        self.assertNotIn("['extension', 'list']", source)

    def test_module_introduces_no_blanket_exception_handler(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("except Exception", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
