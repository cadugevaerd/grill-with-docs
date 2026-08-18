#!/usr/bin/env python3
"""Contract for `grill_workspace.py triage` and `grill_core/triage.py`.

Runs with no network, no `specify`, no `node` and no `backlogctl`: triage is a
pre-cycle command that reads two files below the repository root and writes one
record, so the whole surface is exercisable from a temporary git repository.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"
SCRIPT = PLUGIN / "skills/grill-with-docs/scripts/grill_workspace.py"
TRIAGE = PLUGIN / "skills/grill-with-docs/scripts/grill_core/triage.py"


def symlink_supported() -> bool:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as raw:
        try:
            os.symlink(raw, str(Path(raw) / "probe"))
        except (OSError, NotImplementedError):
            return False
    return True


SYMLINK_SUPPORTED = symlink_supported()


def load() -> object:
    spec = importlib.util.spec_from_file_location("triage_under_test", TRIAGE)
    module = importlib.util.module_from_spec(spec)
    # Registered before exec because @dataclass resolves annotations through
    # sys.modules[cls.__module__]; the production loader does the same.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load()

PROVEN_REPORT = """# Relatório de debug

## Status
Causa raiz comprovada.

## Sintoma reproduzido
- Comando/cenário: `python -m pytest tests/test_config.py -q`
- Resultado observado: exit code 1 ao carregar configuração inválida.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| Exceção antes da validação | `stderr` do teste | A falha ocorre durante a leitura. |

## Caminho de investigação/Hipóteses eliminadas
1. Reprodução capturada → falha determinística.

## Causa raiz
A configuração inválida é consumida antes da validação obrigatória.

## Cadeia causal
Configuração inválida → leitura sem validação → exceção → falha do teste.

## Arquivos envolvidos
- `src/config.py`: lê a configuração antes de validá-la.

## Limitações/incertezas
- Nenhuma para o sintoma reproduzido.
"""

UNPROVEN_REPORT = PROVEN_REPORT.replace(
    "## Status\nCausa raiz comprovada.",
    "## Status\nCausa raiz não comprovada ainda.",
)
ENV_BLOCKED_REPORT = PROVEN_REPORT.replace(
    "## Status\nCausa raiz comprovada.",
    "## Status\nBloqueado por ambiente.",
)


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def invoke(*args: object) -> tuple[subprocess.CompletedProcess[str], dict]:
    process = subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    lines = process.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError(
            f"expected one JSON line, got stdout={process.stdout!r} stderr={process.stderr!r}"
        )
    return process, json.loads(lines[0])


def snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    result: dict[str, tuple[bytes, int]] = {}
    for path in sorted(root.rglob("*")):
        if ".git" in path.relative_to(root).parts or not path.is_file():
            continue
        result[str(path.relative_to(root))] = (path.read_bytes(), path.stat().st_mtime_ns)
    return result


class TriageContract(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name)
        git(self.root.parent, "init", "-q", "-b", "main", str(self.root))
        git(self.root, "config", "user.email", "tests@example.invalid")
        git(self.root, "config", "user.name", "Contract Tests")
        (self.root / "docs/debug").mkdir(parents=True)
        (self.root / "specs/003-x").mkdir(parents=True)
        self.write("docs/debug/R.md", PROVEN_REPORT)
        self.write("docs/debug/UNPROVEN.md", UNPROVEN_REPORT)
        self.write("docs/debug/ENVBLOCKED.md", ENV_BLOCKED_REPORT)
        self.write("specs/003-x/spec.md", "# spec\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "initial")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def bugfix(self, *extra: object) -> tuple[subprocess.CompletedProcess[str], dict]:
        return invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md",
            "--route", "bugfix",
            "--severity", "high",
            "--spec-ref", "specs/003-x/spec.md",
            *extra,
        )

    def records(self) -> list[Path]:
        return sorted((self.root / ".grill/triage").glob("*.json"))

    def assert_untouched(self, before: dict[str, tuple[bytes, int]]) -> None:
        self.assertEqual(snapshot(self.root), before)

    # ---------------------------------------------------------------- happy path

    def test_bugfix_route_records_a_sealed_document(self) -> None:
        process, payload = self.bugfix("--apply")
        self.assertEqual(process.returncode, 0)
        self.assertEqual(payload["verdict"], "TRIAGE-RECORDED")
        self.assertEqual(payload["schema"], "grill-triage/v1")
        self.assertEqual(payload["route"], "bugfix")
        self.assertEqual(payload["report_status"], "causa raiz comprovada")
        self.assertTrue(payload["written"])
        self.assertTrue(payload["triage_id"].startswith("tri-"))
        self.assertEqual(process.stderr, "")

        records = self.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, f"{payload['triage_id']}.json")
        stored = json.loads(records[0].read_text(encoding="utf-8"))
        self.assertEqual(stored, payload["record"])
        MODULE.verify_seal(stored)

    def test_record_fingerprints_the_bytes_of_report_and_spec(self) -> None:
        _, payload = self.bugfix("--apply")
        record = payload["record"]
        self.assertEqual(record["report"]["path"], "docs/debug/R.md")
        self.assertEqual(
            record["report"]["sha256"],
            MODULE.hash_bytes((self.root / "docs/debug/R.md").read_bytes()),
        )
        self.assertEqual(
            record["spec_ref"]["sha256"],
            MODULE.hash_bytes((self.root / "specs/003-x/spec.md").read_bytes()),
        )
        head = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        self.assertEqual(record["recorded_at_commit"], head)

    def test_preview_is_the_default_and_writes_nothing(self) -> None:
        before = snapshot(self.root)
        process, payload = self.bugfix()
        self.assertEqual(process.returncode, 0)
        self.assertEqual(payload["verdict"], "TRIAGE-PREVIEW")
        self.assertFalse(payload["written"])
        self.assertIn("record", payload)
        self.assertFalse((self.root / ".grill").exists())
        self.assert_untouched(before)

    def test_reapplying_the_same_decision_is_reused(self) -> None:
        _, first = self.bugfix("--apply")
        before = snapshot(self.root)
        process, second = self.bugfix("--triage-id", first["triage_id"], "--apply")
        self.assertEqual(process.returncode, 0)
        self.assertEqual(second["verdict"], "REUSED")
        self.assertFalse(second["written"])
        self.assertEqual(second["record"], first["record"])
        self.assert_untouched(before)

    def test_explicit_triage_id_is_honoured(self) -> None:
        _, payload = self.bugfix("--triage-id", "tri-incidente-042", "--apply")
        self.assertEqual(payload["triage_id"], "tri-incidente-042")
        self.assertTrue((self.root / ".grill/triage/tri-incidente-042.json").exists())

    def test_hotfix_route_records_scope_and_rollback(self) -> None:
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md",
            "--route", "hotfix",
            "--severity", "critical",
            "--production-impact",
            "--scope", "src/config.py,tests/test_config.py",
            "--rollback", "git revert do commit de correção",
            "--apply",
        )
        self.assertEqual(process.returncode, 0)
        self.assertEqual(payload["verdict"], "TRIAGE-RECORDED")
        self.assertEqual(
            payload["record"]["scope"]["paths"], ["src/config.py", "tests/test_config.py"]
        )
        self.assertTrue(payload["record"]["production_impact"])
        self.assertIsNone(payload["record"]["spec_ref"])

    def test_feature_route_needs_no_evidence(self) -> None:
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "feature", "--severity", "medium", "--apply",
        )
        self.assertEqual(process.returncode, 0)
        self.assertEqual(payload["route"], "feature")
        self.assertIsNone(payload["record"]["spec_ref"])
        self.assertEqual(payload["record"]["scope"]["paths"], [])

    # ------------------------------------------------------- the root-cause gate

    def test_unproven_root_cause_opens_no_route(self) -> None:
        before = snapshot(self.root)
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/UNPROVEN.md",
            "--route", "bugfix", "--severity", "high",
            "--spec-ref", "specs/003-x/spec.md", "--apply",
        )
        self.assertEqual(process.returncode, 1)
        self.assertEqual(payload["verdict"], "NO-GO")
        self.assertEqual(payload["code"], "ROOT-CAUSE-UNPROVEN")
        self.assertEqual(payload["report_status"], "causa raiz não comprovada ainda")
        self.assert_untouched(before)

    def test_environment_blocked_report_opens_no_route(self) -> None:
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/ENVBLOCKED.md",
            "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(process.returncode, 1)
        self.assertEqual(payload["code"], "ROOT-CAUSE-UNPROVEN")
        self.assertEqual(payload["report_status"], "bloqueado por ambiente")

    def test_a_proven_header_cannot_override_an_unproven_root_cause_section(self) -> None:
        contradictory = PROVEN_REPORT.replace(
            "A configuração inválida é consumida antes da validação obrigatória.",
            "Causa raiz não comprovada ainda.",
        )
        self.write("docs/debug/CONTRADICTORY.md", contradictory)
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/CONTRADICTORY.md",
            "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(process.returncode, 1)
        self.assertEqual(payload["code"], "ROOT-CAUSE-UNPROVEN")

    # --------------------------------------------------------- report validation

    def test_markdown_that_is_not_a_debug_report_is_refused(self) -> None:
        self.write("docs/debug/OTHER.md", "# Notas\n\n## Status\nCausa raiz comprovada.\n")
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/OTHER.md",
            "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(process.returncode, 2)
        self.assertEqual(payload["code"], "TRIAGE-REPORT-INVALID")
        self.assertEqual(payload["expected_heading"], "# Relatório de debug")

    def test_missing_section_is_named_so_the_operator_is_not_hunting(self) -> None:
        without = PROVEN_REPORT.replace(
            "## Cadeia causal\nConfiguração inválida → leitura sem validação → exceção → falha do teste.\n",
            "",
        )
        self.write("docs/debug/PARTIAL.md", without)
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/PARTIAL.md",
            "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(process.returncode, 2)
        self.assertEqual(payload["code"], "TRIAGE-REPORT-INCOMPLETE")
        self.assertEqual(payload["missing_sections"], ["Cadeia causal"])

    def test_empty_required_section_counts_as_missing(self) -> None:
        emptied = PROVEN_REPORT.replace(
            "A configuração inválida é consumida antes da validação obrigatória.", ""
        )
        self.write("docs/debug/EMPTY.md", emptied)
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/EMPTY.md",
            "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(payload["code"], "TRIAGE-REPORT-INCOMPLETE")
        self.assertEqual(payload["missing_sections"], ["Causa raiz"])

    def test_unknown_status_phrase_is_refused_rather_than_guessed(self) -> None:
        vague = PROVEN_REPORT.replace("Causa raiz comprovada.", "Parece resolvido.")
        self.write("docs/debug/VAGUE.md", vague)
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/VAGUE.md",
            "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(payload["code"], "TRIAGE-REPORT-INVALID")
        self.assertIn("causa raiz comprovada", payload["accepted_statuses"])

    def test_invalid_utf8_report_is_named_without_a_traceback(self) -> None:
        (self.root / "docs/debug/BINARY.md").write_bytes(b"# Relat\xffrio de debug\n")
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/BINARY.md",
            "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(process.returncode, 2)
        self.assertEqual(payload["code"], "TRIAGE-REPORT-INVALID")
        self.assertNotIn("Traceback", process.stderr)

    def test_missing_report_file_is_named(self) -> None:
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/ABSENT.md",
            "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(payload["code"], "EVIDENCE-MISSING")

    # ------------------------------------------------------ the routing evidence

    def test_bugfix_without_spec_ref_is_refused(self) -> None:
        before = snapshot(self.root)
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "bugfix", "--severity", "high", "--apply",
        )
        self.assertEqual(process.returncode, 1)
        self.assertEqual(payload["code"], "ROUTE-EVIDENCE-MISSING")
        self.assertEqual(payload["missing_evidence"], ["spec_ref"])
        self.assert_untouched(before)

    def test_bugfix_with_scope_or_rollback_is_a_conflict(self) -> None:
        _, payload = self.bugfix("--rollback", "git revert", "--apply")
        self.assertEqual(payload["code"], "ROUTE-EVIDENCE-CONFLICT")
        self.assertEqual(payload["forbidden_evidence"], ["rollback"])

    def test_hotfix_missing_every_required_field_lists_all_of_them(self) -> None:
        process, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "hotfix", "--severity", "low", "--apply",
        )
        self.assertEqual(process.returncode, 1)
        self.assertEqual(payload["code"], "ROUTE-EVIDENCE-MISSING")
        self.assertEqual(
            payload["missing_evidence"],
            ["production_impact", "rollback", "scope", "severity=critical"],
        )

    def test_hotfix_below_critical_severity_is_refused(self) -> None:
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "hotfix", "--severity", "high",
            "--production-impact", "--scope", "src/config.py", "--rollback", "git revert", "--apply",
        )
        self.assertEqual(payload["code"], "ROUTE-EVIDENCE-MISSING")
        self.assertEqual(payload["missing_evidence"], ["severity=critical"])

    def test_hotfix_with_spec_ref_is_a_conflict(self) -> None:
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "hotfix", "--severity", "critical",
            "--production-impact", "--scope", "src/config.py", "--rollback", "git revert",
            "--spec-ref", "specs/003-x/spec.md", "--apply",
        )
        self.assertEqual(payload["code"], "ROUTE-EVIDENCE-CONFLICT")
        self.assertEqual(payload["forbidden_evidence"], ["spec_ref"])

    def test_feature_with_spec_ref_is_a_conflict(self) -> None:
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "feature", "--severity", "low",
            "--spec-ref", "specs/003-x/spec.md", "--apply",
        )
        self.assertEqual(payload["code"], "ROUTE-EVIDENCE-CONFLICT")

    def test_unknown_route_and_severity_are_named_with_what_is_accepted(self) -> None:
        _, route = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "refactor", "--severity", "high", "--apply",
        )
        self.assertEqual(route["code"], "INVALID-ROUTE")
        self.assertEqual(sorted(route["accepted_routes"]), ["bugfix", "feature", "hotfix", "module"])
        _, severity = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "feature", "--severity", "urgent", "--apply",
        )
        self.assertEqual(severity["code"], "INVALID-SEVERITY")

    def test_spec_ref_that_does_not_resolve_is_named_as_such(self) -> None:
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "bugfix", "--severity", "high",
            "--spec-ref", "specs/003-x/absent.md", "--apply",
        )
        self.assertEqual(payload["code"], "SPEC-REF-NOT-FOUND")

    def test_directory_as_spec_ref_is_named_as_such(self) -> None:
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "bugfix", "--severity", "high",
            "--spec-ref", "specs/003-x", "--apply",
        )
        self.assertEqual(payload["code"], "SPEC-REF-NOT-FOUND")

    def test_scope_with_traversal_is_not_closed(self) -> None:
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "hotfix", "--severity", "critical",
            "--production-impact", "--scope", "../fuga", "--rollback", "git revert", "--apply",
        )
        self.assertEqual(payload["verdict"], "NO-GO")
        self.assertEqual(payload["code"], "SCOPE-NOT-CLOSED")

    def test_triage_id_outside_the_namespace_is_refused(self) -> None:
        _, payload = self.bugfix("--triage-id", "incidente-042", "--apply")
        self.assertEqual(payload["code"], "INVALID-TRIAGE-ID")

    # ------------------------------------------------------------ seal integrity

    def test_edited_record_is_detected_as_tampered(self) -> None:
        _, payload = self.bugfix("--apply")
        record = self.records()[0]
        stored = json.loads(record.read_text(encoding="utf-8"))
        stored["route"] = "hotfix"
        record.write_text(json.dumps(stored), encoding="utf-8")
        process, second = self.bugfix("--triage-id", payload["triage_id"], "--apply")
        self.assertEqual(process.returncode, 2)
        self.assertEqual(second["code"], "TRIAGE-TAMPERED")

    def test_same_id_with_a_different_decision_diverges(self) -> None:
        _, payload = self.bugfix("--apply")
        process, second = invoke(
            "triage", self.root,
            "--report", "docs/debug/R.md", "--route", "feature", "--severity", "low",
            "--triage-id", payload["triage_id"], "--apply",
        )
        self.assertEqual(process.returncode, 2)
        self.assertEqual(second["code"], "TRIAGE-IDENTITY-DIVERGENCE")

    def test_seal_covers_every_field_but_itself(self) -> None:
        record = MODULE.seal(
            MODULE.build_record(
                triage_id="tri-abc", route="feature", severity="low", production_impact=False,
                report={"path": "r.md", "sha256": "0" * 64}, spec_ref=None, scope=[],
                rollback=None, recorded_at_commit=None,
            )
        )
        self.assertEqual(MODULE.verify_seal(record), {k: v for k, v in record.items() if k != "triage_sha256"})
        for key in ("route", "severity", "production_impact", "scope", "recorded_at_commit"):
            mutated = {**record, key: "tampered"}
            with self.assertRaises(MODULE.TriageError) as raised:
                MODULE.verify_seal(mutated)
            self.assertEqual(raised.exception.code, "TRIAGE_TAMPERED")
        with self.assertRaises(MODULE.TriageError):
            MODULE.verify_seal({k: v for k, v in record.items() if k != "triage_sha256"})

    # ------------------------------------------------------------ path boundary

    def test_report_outside_the_root_escapes(self) -> None:
        _, payload = invoke(
            "triage", self.root,
            "--report", "../outside.md", "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(payload["code"], "PATH-ESCAPE")

    def test_absolute_report_path_escapes(self) -> None:
        _, payload = invoke(
            "triage", self.root,
            "--report", "/etc/hostname", "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(payload["code"], "PATH-ESCAPE")

    @unittest.skipUnless(SYMLINK_SUPPORTED, "symlinks unsupported on this platform")
    def test_symlinked_report_is_rejected(self) -> None:
        os.symlink(str(self.root / "docs/debug/R.md"), str(self.root / "docs/debug/LINK.md"))
        _, payload = invoke(
            "triage", self.root,
            "--report", "docs/debug/LINK.md", "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(payload["code"], "SYMLINK-REJECTED")

    def test_root_must_be_the_git_top_level(self) -> None:
        _, payload = invoke(
            "triage", self.root / "docs",
            "--report", "debug/R.md", "--route", "feature", "--severity", "low", "--apply",
        )
        self.assertEqual(payload["code"], "INVALID-ROOT")

    # ------------------------------------------------------------ global surface

    def test_triage_never_touches_the_global_projection(self) -> None:
        managed = self.root / ".grill/global"
        managed.mkdir(parents=True)
        (managed / "ROADMAP.md").write_text("# Global ROADMAP\n", encoding="utf-8")
        before = snapshot(managed)
        self.bugfix("--apply")
        self.assertEqual(snapshot(managed), before)

    def test_module_is_stdlib_only_and_offline(self) -> None:
        source = TRIAGE.read_text(encoding="utf-8")
        for forbidden in ("import requests", "urllib", "http.client", "socket", "subprocess", "os.system"):
            # Asserted without dumping the whole module into the failure text:
            # this file is read in full, so assertNotIn would print all of it.
            self.assertFalse(forbidden in source, f"triage.py must not reference {forbidden}")
        self.assertFalse("import grill_workspace" in source, "triage.py must not import the CLI")


if __name__ == "__main__":
    unittest.main()
