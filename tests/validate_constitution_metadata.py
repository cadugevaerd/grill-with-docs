#!/usr/bin/env python3
"""Contract for the Constitution metadata reader of `audit_decisions.py`.

A Constitution reaches the auditor in one of three real shapes, and all three are
legitimate: the managed Grill template writes `- key: value` bullets, older
projects write bare `key: value` lines, and `speckit-constitution` writes a bold
footer (`**Version**: X | **Ratified**: Y | **Last Amended**: Z`) plus a
`## Governance` section of prose.  `ensure_managed_constitution` preserves a
preexisting Constitution byte for byte, so the auditor has to read what the
ecosystem actually produces instead of the one shape it used to know.

Fixtures here are derived from the shipped artefacts -- the Grill asset template
and the upstream Spec Kit template -- never hand-written from the parser, which
is how the previous shape went unnoticed.  Runs with no network and no external
CLI: the auditor only reads files below a temporary project root.
"""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "plugin/skills/grill-with-docs/scripts/audit_decisions.py"
ASSET = REPO / "plugin/skills/grill-with-docs/assets/GRILL-CONSTITUTION.template.md"
SPEC_KIT = REPO / "tests/fixtures/constitutions/spec-kit-filled.md"
PROJECT = REPO / "tests/fixtures/go-project"


def load() -> object:
    spec = importlib.util.spec_from_file_location("audit_decisions", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def managed_constitution() -> str:
    """The Grill template as `ensure_managed_constitution` writes it to disk."""
    return ASSET.read_text(encoding="utf-8").replace("{{RATIFIED}}", "2026-08-11").replace(
        "{{LAST_AMENDED}}", "2026-08-14"
    )


class ConstitutionMetadata(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        shutil.copytree(PROJECT, self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def audit(self, constitution: str) -> list[str]:
        """Run the real CLI over a project carrying `constitution`."""
        path = self.root / ".specify/memory/constitution.md"
        path.write_text(constitution, encoding="utf-8")
        state_path = self.root / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["constitution"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        process = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(process.stdout)
        return sorted(item for item in payload.get("findings", []) if item.startswith("constitution:"))

    # --- the three real shapes ---------------------------------------------

    def test_managed_grill_template_audits_clean(self) -> None:
        """The bullet shape the plugin itself writes had no coverage through audit."""
        self.assertEqual(self.audit(managed_constitution()), [])

    def test_spec_kit_constitution_audits_clean(self) -> None:
        self.assertEqual(self.audit(SPEC_KIT.read_text(encoding="utf-8")), [])

    def test_legacy_top_level_fields_audit_clean(self) -> None:
        text = "version: 1.0.0\nratified: 2026-01-01\nlast-amended: 2026-01-01\ngovernance: Architecture Council\n"
        self.assertEqual(self.audit(text), [])

    # --- fail-closed is preserved ------------------------------------------

    def test_constitution_without_metadata_still_fails_closed(self) -> None:
        text = "# Acme Constitution\n\n## Core Principles\n\n### I. Evidence First\nClaims carry evidence.\n"
        self.assertEqual(
            self.audit(text),
            [
                "constitution: governance vazio",
                "constitution: last-amended ISO inválido",
                "constitution: ratified ISO inválido",
                "constitution: version SemVer inválida",
            ],
        )

    def test_footer_version_must_be_semver(self) -> None:
        text = SPEC_KIT.read_text(encoding="utf-8").replace("**Version**: 1.2.0", "**Version**: 1.2")
        self.assertEqual(self.audit(text), ["constitution: version SemVer inválida"])

    def test_footer_ratified_must_be_iso(self) -> None:
        text = SPEC_KIT.read_text(encoding="utf-8").replace("**Ratified**: 2026-07-30", "**Ratified**: someday")
        self.assertEqual(self.audit(text), ["constitution: ratified ISO inválido"])

    def test_governance_heading_without_prose_is_empty(self) -> None:
        text = (
            "# Acme Constitution\n\n## Core Principles\n\n### I. Evidence First\nClaims carry evidence.\n\n"
            "## Governance\n\n"
            "**Version**: 1.2.0 | **Ratified**: 2026-07-30 | **Last Amended**: 2026-08-11\n"
        )
        self.assertEqual(self.audit(text), ["constitution: governance vazio"])

    def test_commented_example_footer_supplies_no_values(self) -> None:
        """The upstream template ships a commented example footer; it is not data."""
        text = (
            "# Acme Constitution\n\n## Core Principles\n\n### I. Evidence First\nClaims carry evidence.\n\n"
            "## Governance\nAmendments require review.\n\n"
            "<!-- Example: **Version**: 2.1.1 | **Ratified**: 2025-06-13 | **Last Amended**: 2025-07-16 -->\n"
        )
        self.assertEqual(
            self.audit(text),
            [
                "constitution: last-amended ISO inválido",
                "constitution: ratified ISO inválido",
                "constitution: version SemVer inválida",
            ],
        )

    # --- the reader itself --------------------------------------------------

    def test_footer_pairs_are_split_on_the_pipe(self) -> None:
        values = self.module.constitution_metadata(
            "**Version**: 1.2.0 | **Ratified**: 2026-07-30 | **Last Amended**: 2026-08-11\n"
        )
        self.assertEqual(values["version"], "1.2.0")
        self.assertEqual(values["ratified"], "2026-07-30")
        self.assertEqual(values["last-amended"], "2026-08-11")

    def test_declared_fields_win_over_the_footer(self) -> None:
        values = self.module.constitution_metadata(
            "- version: 3.0.0\n\n**Version**: 1.2.0 | **Ratified**: 2026-07-30 | **Last Amended**: 2026-08-11\n"
        )
        self.assertEqual(values["version"], "3.0.0")
        self.assertEqual(values["ratified"], "2026-07-30")

    def test_governance_accepts_a_portuguese_heading(self) -> None:
        values = self.module.constitution_metadata("## Governança\nAlterações exigem revisão.\n")
        self.assertEqual(values["governance"], "Alterações exigem revisão.")

    def test_governance_body_stops_at_the_next_heading(self) -> None:
        values = self.module.constitution_metadata(
            "## Governance\nAmendments require review.\n\n## Annex\nUnrelated prose.\n"
        )
        self.assertEqual(values["governance"], "Amendments require review.")

    def test_unbolded_prose_is_not_read_as_a_footer(self) -> None:
        values = self.module.constitution_metadata("Ratified: whenever the council decides.\n")
        self.assertEqual(values.get("ratified", ""), "")

    def test_section_body_excludes_the_footer_line(self) -> None:
        body = self.module.section_body(
            "## Governance\nAmendments require review.\n\n**Version**: 1.2.0 | **Ratified**: 2026-07-30\n",
            self.module.GOVERNANCE_NAMES,
        )
        self.assertEqual(body, "Amendments require review.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
