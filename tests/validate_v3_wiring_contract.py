#!/usr/bin/env python3
"""Contract for peça E (LD-004): wiring the v3 library onto the public CLI.

Scope, exactly as LD-004 hands it to this piece:

1. dual-read v2/v3 in ``grill_workspace.validate_metadata``, delegating a v3
   document's *form* to ``grill_core.work_item_v3`` -- v2 is byte-for-byte
   the pre-existing path, untouched.
2. ``grill_workspace.py migrate-v3`` -- preview-first bundle upgrade, backed
   by ``grill_core.work_item_v3.migrate_bundle``.
3. ``ensure_workflow.py`` recognises the v3 workflow marker alongside v2,
   without touching the v2 ``ESSENTIAL``/``VERSION`` contract.
4. the ``SessionStart``/``SubagentStart`` hook injects ``registry_sha256``
   (LD-001: raw bytes hash) and the literal anti-emulation phrase *before*
   the status projection, because ``render_hook_output`` truncates the tail.
5. an explicit SCREAMING_SNAKE -> SCREAMING-KEBAB translation table for the
   plan-literal v3 codes (LD-002 revisada), applied at the CLI boundary.

This file is the only place authorised to assert on ``grill_workspace.py``'s
and ``ensure_workflow.py``'s *new* surface; it must not encode assumptions
about the internals of grill_core/work_item_v3.py or grill_core/workflow_v3.py
beyond their public, documented functions -- those belong to other pieces.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"
SKILL = PLUGIN / "skills/grill-with-docs"
SCRIPTS = SKILL / "scripts"
WORKSPACE = SCRIPTS / "grill_workspace.py"
ENSURE_WORKFLOW = SCRIPTS / "ensure_workflow.py"
GRILL_CORE = SCRIPTS / "grill_core"
WORKFLOW_TEMPLATE_V2 = SKILL / "assets/WORKFLOW.template.md"
WORKFLOW_TEMPLATE_V3 = SKILL / "assets/WORKFLOW.v3.template.md"
REGISTRY = SKILL / "assets/workflow-step-skills.json"
CHECK_START = "<!-- grill-constitution-check:start -->"
CHECK_END = "<!-- grill-constitution-check:end -->"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


WORKSPACE_MODULE = load_module(WORKSPACE, "v3_wiring_grill_workspace")
ENSURE_WORKFLOW_MODULE = load_module(ENSURE_WORKFLOW, "v3_wiring_ensure_workflow")
WORK_ITEM_V3 = load_module(GRILL_CORE / "work_item_v3.py", "v3_wiring_work_item_v3")
WORKFLOW_V3 = load_module(GRILL_CORE / "workflow_v3.py", "v3_wiring_workflow_v3")
STORE = load_module(GRILL_CORE / "store.py", "v3_wiring_store")
ATTESTATION_FIXTURES = load_module(REPO / "tests/validate_attestation_contract.py", "v3_wiring_attestation_fixtures")


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True).stdout.strip()


def invoke(*args: object) -> tuple[subprocess.CompletedProcess[str], dict]:
    process = subprocess.run(
        [sys.executable, str(WORKSPACE), *(str(a) for a in args)], text=True, capture_output=True, check=False,
    )
    lines = process.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError(f"expected exactly one JSON line, got stdout={process.stdout!r} stderr={process.stderr!r}")
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise AssertionError(process.stdout) from exc
    return process, payload


def invoke_migrate_v3_apply(root: str, work_id: str) -> dict:
    """Top-level (picklable) so multiprocessing.Pool can spawn it as a worker."""
    _, payload = invoke("migrate-v3", root, "--work-id", work_id, "--apply")
    return payload


def hook_run(*args: str, cwd: Path | None = None, input: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(ENSURE_WORKFLOW), *args], cwd=cwd, input=input, text=True, capture_output=True)


def work_item_v3_emitted_codes() -> set[str]:
    """AST-collect every literal error code ``grill_core/work_item_v3.py`` can raise.

    LD-008 item 2: the previous version of this guard was a hand-typed
    ``live_codes`` set under a docstring that CLAIMED it was "pulled from the
    live module lookup, not typed out by hand" -- false, and the exact
    divergence-by-hand-maintenance LD-008 exists to end. This walks the
    module's own AST instead: a code raised via ``blocked(code, ...)`` (code
    is the first positional argument) or directly via
    ``WorkItemError(exit_code, verdict, code, message, ...)`` (code is the
    third positional argument) is collected regardless of how many lines the
    call spans or how the module's vocabulary grows later -- no one has to
    remember to update a second list when a call site changes.

    Scoped to ``work_item_v3.py`` specifically, not every file under
    ``grill_core/``: it is the one module ``grill_workspace.py`` actually
    loads and routes through ``translate_v3_code``/``raise_from_work_item_error``
    at the public CLI boundary today (see ``grill_core_module``'s own
    docstring). ``store.py``/``step_skills.py``/``attestation.py`` mint their
    own vocabularies (lifecycle STATUS values, not error codes -- e.g.
    ``AWAITING_HUMAN``, ``WORKTREE_CREATING``) that never cross this
    boundary and belong to other pieces' contracts, not this one's.
    """
    source = (GRILL_CORE / "work_item_v3.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="work_item_v3.py")
    codes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else None
        if name == "blocked" and node.args:
            argument = node.args[0]
        elif name == "WorkItemError" and len(node.args) >= 3:
            argument = node.args[2]
        else:
            continue
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            codes.add(argument.value)
    return codes


def render_v3_workflow_bytes() -> bytes:
    """The exact bytes ``grill_core.workflow_v3``'s own migration would write.

    Calls the production ``render_v3`` + ``registry_state`` functions
    directly instead of hand-computing the registry hash a second time, so
    this fixture can never drift from the format the real migration
    produces (LD-010 item 2 / the peça-E wiring critic's "cuide da
    divergência de formato"): ``render_v3`` bakes ``registry_state()["sha256"]``
    verbatim, which is ``"sha256:" + hexdigest`` (LD-001,
    ``grill_core.step_skills.registry_sha256``) -- NOT the bare hexdigest a
    prior version of this helper baked in. That bare-hex fixture only
    "passed" while ``_execution_ready``/``resolve_workflow`` did not yet
    check the pin at all (the exact fail-open LD-010 item 2 closes); once
    ``_v3_ready`` started comparing pins for real, a bare-hex fixture would
    read as REGISTRY_PIN_DIVERGENT and silently break every "this v3
    document is READY" test in this file.
    """
    template_text = WORKFLOW_TEMPLATE_V3.read_text(encoding="utf-8")
    registry_sha256_value = WORKFLOW_V3.registry_state()["sha256"]
    rendered = WORKFLOW_V3.render_v3(template_text, registry_sha256_value)
    assert "__REGISTRY_SHA256__" not in rendered
    return rendered.encode("utf-8")


def snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


class WiringHarness(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        git(self.root, "config", "user.email", "wiring@example.invalid")
        git(self.root, "config", "user.name", "Wiring Tests")
        (self.root / "WORKFLOW.md").write_bytes(WORKFLOW_TEMPLATE_V2.read_bytes())
        git(self.root, "add", "WORKFLOW.md")
        git(self.root, "commit", "-q", "-m", "workflow")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _init_item(self, work_id: str = "wa", kind: str = "feature", slug: str = "alpha") -> Path:
        process, payload = invoke("init", self.root, "--type", kind, "--slug", slug, "--work-id", work_id)
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload["status"], "CREATED")
        return self.root / ".grill" / "work-items" / work_id

    def _metadata(self, item: Path) -> dict:
        return json.loads((item / "WORK-ITEM.json").read_text(encoding="utf-8"))

    def _write_metadata(self, item: Path, value: dict) -> None:
        (item / "WORK-ITEM.json").write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def _approve_check(self, item: Path) -> None:
        text = (item / "CONSTITUTION-CHECK.md").read_text(encoding="utf-8")
        block = text.split(CHECK_START, 1)[1].split(CHECK_END, 1)[0]
        import re

        match = re.search(r"```json\s*(\{.*\})\s*```", block, re.DOTALL)
        assert match is not None
        value = json.loads(match.group(1))
        for entry in value["clauses"]:
            entry["status"] = "PASS"
            entry["evidence"] = ["tests/evidence.md"]
            entry["justification"] = "verified against the work-item scope"
        rendered = "# Constitution Check\n\n" + CHECK_START + "\n```json\n" + json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n```\n" + CHECK_END + "\n"
        (item / "CONSTITUTION-CHECK.md").write_text(rendered, encoding="utf-8")


# ---------------------------------------------------------------------------
# Item 1: dual-read v2/v3 in validate_metadata
# ---------------------------------------------------------------------------


class DualReadContract(WiringHarness):
    def test_status_and_audit_survive_v3_migration(self) -> None:
        """The exact §22/Core gate: status/audit must not regress to METADATA-SCHEMA."""
        self._init_item("wa")
        before_status = invoke("status", self.root, "--work-id", "wa")
        before_audit = invoke("audit", self.root, "--work-id", "wa")
        self.assertNotEqual(before_status[1].get("code"), "METADATA-SCHEMA")
        self.assertNotEqual(before_audit[1].get("code"), "METADATA-SCHEMA")

        process, payload = invoke("migrate-v3", self.root, "--work-id", "wa", "--apply")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        metadata = self._metadata(self.root / ".grill/work-items/wa")
        self.assertEqual(metadata["schema"], "grill-work-item/v3")

        after_status = invoke("status", self.root, "--work-id", "wa")
        after_audit = invoke("audit", self.root, "--work-id", "wa")
        self.assertEqual((after_status[0].returncode, after_status[1]["verdict"], after_status[1]["code"]),
                          (before_status[0].returncode, before_status[1]["verdict"], before_status[1]["code"]))
        self.assertEqual((after_audit[0].returncode, after_audit[1]["verdict"], after_audit[1]["code"]),
                          (before_audit[0].returncode, before_audit[1]["verdict"], before_audit[1]["code"]))
        item = after_status[1]["work_items"][0]
        self.assertEqual(item["work_id"], "wa")
        self.assertEqual(item["type"], "feature")

    def test_status_and_audit_survive_v3_migration_with_approved_constitution(self) -> None:
        """Same gate, but with a real GO-shaped audit instead of BLOCKED-CONSTITUTION."""
        item = self._init_item("wb")
        self._approve_check(item)
        before = invoke("audit", self.root, "--work-id", "wb")
        self.assertNotEqual(before[1].get("code"), "METADATA-SCHEMA")
        invoke("migrate-v3", self.root, "--work-id", "wb", "--apply")
        after = invoke("audit", self.root, "--work-id", "wb")
        self.assertEqual((after[0].returncode, after[1]["verdict"], after[1]["code"]),
                          (before[0].returncode, before[1]["verdict"], before[1]["code"]))

    def test_v2_tamper_is_still_rejected_the_same_way(self) -> None:
        """Real attack: rewrite a whole field, leave immutable_sha256 stale (not a byte-slice)."""
        item = self._init_item("wc")
        metadata = self._metadata(item)
        metadata["immutable"]["slug"] = "tampered-whole-field"
        self._write_metadata(item, metadata)
        process, payload = invoke("status", self.root, "--work-id", "wc")
        self.assertEqual((process.returncode, payload["code"]), (2, "IMMUTABLE-TAMPERED"))
        process, payload = invoke("migrate-v3", self.root, "--work-id", "wc")
        self.assertEqual((process.returncode, payload["code"]), (2, "IMMUTABLE-TAMPERED"))

    def test_v3_tamper_after_migration_is_rejected_fail_closed(self) -> None:
        """Real attack on the NEW v3 path: mutate parent_work_id, keep the stale hash."""
        item = self._init_item("wd")
        invoke("migrate-v3", self.root, "--work-id", "wd", "--apply")
        metadata = self._metadata(item)
        metadata["immutable"]["parent_work_id"] = "some-other-work-item"
        self._write_metadata(item, metadata)
        process, payload = invoke("status", self.root, "--work-id", "wd")
        self.assertEqual((process.returncode, payload["code"]), (2, "IMMUTABLE-TAMPERED"))
        process, payload = invoke("audit", self.root, "--work-id", "wd")
        self.assertEqual((process.returncode, payload["code"]), (2, "IMMUTABLE-TAMPERED"))

    def test_unknown_schema_is_still_rejected(self) -> None:
        item = self._init_item("we")
        metadata = self._metadata(item)
        metadata["schema"] = "grill-work-item/v99"
        metadata["immutable"]["schema"] = "grill-work-item/v99"
        metadata["immutable_sha256"] = hashlib.sha256(
            (json.dumps(metadata["immutable"], ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        ).hexdigest()
        self._write_metadata(item, metadata)
        process, payload = invoke("status", self.root, "--work-id", "we")
        self.assertEqual((process.returncode, payload["code"]), (2, "METADATA-SCHEMA"))

    def test_dual_read_function_probe_does_not_trust_unhashed_schema_claim(self) -> None:
        """Calling validate_metadata in-process: a v3 schema claim alone buys nothing."""
        immutable = {"schema": "grill-work-item/v3", "work_id": "x", "parent_work_id": None,
                     "source": None, "worktree_key": "wt-x"}
        metadata = {"schema": "grill-work-item/v3", "immutable": immutable, "immutable_sha256": "sha256:" + "0" * 64}
        with self.assertRaises(WORKSPACE_MODULE.CliFailure) as ctx:
            WORKSPACE_MODULE.validate_metadata(metadata, "x")
        self.assertEqual(ctx.exception.code, "IMMUTABLE-TAMPERED")

    def test_v3_to_v2_downgrade_with_orphaned_fields_fails_closed(self) -> None:
        """Real attack (LD-010 item 4): migrate to v3, then rewrite the bundle
        claiming immutable.schema=v2 again while keeping the v3 fields --
        including a path-escape worktree_key -- and recompute
        immutable_sha256 with this module's own canonicalizer, so the hash is
        self-consistent. The dual-read probe (immutable.schema) is exactly
        the field the attacker controls; migration must be monotonic. Before
        the fix this returned exit 0 / verdict OK from status with the
        escape payload carried along, unvalidated by either schema branch.
        """
        item = self._init_item("wa")
        process, applied = invoke("migrate-v3", self.root, "--work-id", "wa", "--apply")
        self.assertEqual((process.returncode, applied["verdict"]), (0, "APPLIED"))
        metadata = self._metadata(item)
        self.assertEqual(metadata["schema"], "grill-work-item/v3")
        self.assertIn("orchestration", metadata)

        downgraded = dict(metadata)
        immutable = dict(metadata["immutable"])
        immutable["schema"] = "grill-work-item/v2"
        immutable["worktree_key"] = "../../../escape"
        downgraded["schema"] = "grill-work-item/v2"
        downgraded["immutable"] = immutable
        downgraded["immutable_sha256"] = hashlib.sha256(
            (json.dumps(immutable, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        ).hexdigest()
        self._write_metadata(item, downgraded)

        process, payload = invoke("status", self.root, "--work-id", "wa")
        self.assertEqual((process.returncode, payload["verdict"]), (2, "BLOCKED"), payload)
        self.assertEqual(payload["code"], "STATE-DIVERGENCE")

        process, payload = invoke("audit", self.root, "--work-id", "wa")
        self.assertEqual((process.returncode, payload["verdict"]), (2, "BLOCKED"), payload)
        self.assertEqual(payload["code"], "STATE-DIVERGENCE")

        # In-process too, matching test_dual_read_function_probe_...'s style:
        # the escaped worktree_key never becomes a trusted, validated field.
        with self.assertRaises(WORKSPACE_MODULE.CliFailure) as ctx:
            WORKSPACE_MODULE.validate_metadata(downgraded, "wa")
        self.assertEqual(ctx.exception.code, "STATE-DIVERGENCE")


# ---------------------------------------------------------------------------
# Item 2: migrate-v3 subcommand
# ---------------------------------------------------------------------------


class MigrateV3CommandContract(WiringHarness):
    def test_preview_writes_nothing(self) -> None:
        item = self._init_item("wa")
        before = snapshot(item)
        process, payload = invoke("migrate-v3", self.root, "--work-id", "wa")
        self.assertEqual((process.returncode, payload["verdict"], payload["from_schema"], payload["to_schema"]),
                          (0, "PREVIEW", "grill-work-item/v2", "grill-work-item/v3"))
        self.assertEqual(payload["writes"], [])
        self.assertEqual(snapshot(item), before)
        self.assertFalse((item / ".migrate.lock").exists())

    def test_apply_then_idempotent_reuse(self) -> None:
        item = self._init_item("wa")
        process, applied = invoke("migrate-v3", self.root, "--work-id", "wa", "--apply")
        self.assertEqual((process.returncode, applied["verdict"], applied["writes"]), (0, "APPLIED", ["WORK-ITEM.json"]))
        metadata = self._metadata(item)
        self.assertEqual(metadata["schema"], "grill-work-item/v3")
        WORK_ITEM_V3.validate_metadata(metadata, "wa")  # raises on any structural defect

        process, reused = invoke("migrate-v3", self.root, "--work-id", "wa", "--apply")
        self.assertEqual((process.returncode, reused["verdict"], reused["writes"]), (0, "REUSED", []))
        self.assertEqual(self._metadata(item), metadata)
        # work_item_v3's own lock lives under <git-common-dir>/grill/locks/,
        # never inside the versioned bundle -- ask its own function where
        # that is instead of guessing a path, and confirm it self-cleaned.
        self.assertFalse(WORK_ITEM_V3.lock_path(item, "wa").exists())

    def test_missing_work_item_is_no_go(self) -> None:
        process, payload = invoke("migrate-v3", self.root, "--work-id", "does-not-exist", "--apply")
        self.assertEqual((process.returncode, payload["code"]), (1, "WORK-ITEM-MISSING"))

    def test_invalid_work_id_is_blocked(self) -> None:
        process, payload = invoke("migrate-v3", self.root, "--work-id", "bad/id", "--apply")
        self.assertEqual((process.returncode, payload["code"]), (2, "INVALID-WORK-ID"))

    def test_concurrent_apply_yields_exactly_one_valid_v3_document(self) -> None:
        """Real race: N processes call --apply on the same freshly-init'd bundle."""
        item = self._init_item("wa")
        before_files = {p.relative_to(item).as_posix() for p in item.rglob("*") if p.is_file()}
        with multiprocessing.Pool(6) as pool:
            results = pool.starmap(invoke_migrate_v3_apply, [(str(self.root), "wa")] * 6)
        for payload in results:
            self.assertIn(payload.get("verdict"), {"APPLIED", "REUSED"}, payload)
        metadata = self._metadata(item)
        self.assertEqual(metadata["schema"], "grill-work-item/v3")
        WORK_ITEM_V3.validate_metadata(metadata, "wa")
        # No lock artifact leaked into the versioned bundle: it would silently
        # change bundle_fingerprint() and every BUNDLE-INTEGRITY check. The
        # lock lives at work_item_v3's own lock_path (outside the bundle);
        # confirm it self-cleaned and that no other file appeared alongside
        # the migrated WORK-ITEM.json.
        self.assertFalse(WORK_ITEM_V3.lock_path(item, "wa").exists())
        after_files = {p.relative_to(item).as_posix() for p in item.rglob("*") if p.is_file()}
        self.assertEqual(after_files, before_files)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink creation is unavailable")
    def test_ancestor_symlink_never_redirects_migrate_v3_outside_the_project(self) -> None:
        """A final-component check is insufficient: `.grill/work-items` itself
        must never be followed to a bundle outside the Git root.
        """
        item = self._init_item("wa")
        outside = self.root.parent / f"outside-work-items-{self.root.name}"
        outside.mkdir()
        relocated = outside / "work-items"
        shutil.move(str(self.root / ".grill" / "work-items"), relocated)
        (self.root / ".grill" / "work-items").symlink_to(relocated, target_is_directory=True)
        before = (relocated / "wa" / "WORK-ITEM.json").read_bytes()

        process, payload = invoke("migrate-v3", self.root, "--work-id", "wa", "--apply")

        self.assertEqual((process.returncode, payload["code"]), (2, "WORK-ITEM-SYMLINK"))
        self.assertEqual((relocated / "wa" / "WORK-ITEM.json").read_bytes(), before)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink creation is unavailable")
    def test_waiting_migration_cannot_be_redirected_after_initial_validation(self) -> None:
        """Reproduce the validation-to-lock race against an outside bundle.

        ``migrate-v3`` resolves the normal bundle, then waits on its public
        lock.  While it waits, replacing ``work-items`` with an outside
        symlink must result in a named block; the external document may not be
        migrated.  The production command opens the bundle through pinned
        no-follow directory descriptors only after acquiring that lock.
        """
        self._init_item("wa")
        work_items = self.root / ".grill" / "work-items"
        outside = self.root.parent / f"race-outside-{self.root.name}"
        outside.mkdir()
        relocated = outside / "work-items"
        lock = self.root / ".grill" / "locks" / "wa.lock"
        lock.mkdir()
        process = subprocess.Popen(
            [sys.executable, str(WORKSPACE), "migrate-v3", str(self.root), "--work-id", "wa", "--apply"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            time.sleep(0.12)
            self.assertIsNone(process.poll(), "migration unexpectedly completed before the lock race")
            shutil.move(str(work_items), relocated)
            work_items.symlink_to(relocated, target_is_directory=True)
            before = (relocated / "wa" / "WORK-ITEM.json").read_bytes()
        finally:
            shutil.rmtree(lock, ignore_errors=True)
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(stderr, "")
        self.assertEqual(len(stdout.splitlines()), 1, stdout)
        payload = json.loads(stdout)
        self.assertEqual((process.returncode, payload["code"]), (2, "WORK-ITEM-SYMLINK"))
        self.assertEqual((relocated / "wa" / "WORK-ITEM.json").read_bytes(), before)

    def test_production_reader_probe_sees_this_wiring_as_v3_ready(self) -> None:
        """work_item_v3.migrate_bundle(apply=True) fail-closes on V3_READERS_NOT_WIRED
        until grill_workspace.validate_metadata actually accepts v3 -- this
        wiring is exactly what flips that functional probe, with no version
        string to keep in sync on either side.
        """
        self.assertTrue(WORK_ITEM_V3.production_reader_accepts_v3())

    def test_require_v3_error_crosses_the_cli_boundary_translated(self) -> None:
        """require_v3() raises the real WORK_ITEM_V3_REQUIRED (SNAKE, this module's
        own v3-only vocabulary per its docstring); raise_from_work_item_error
        is what turns it into the live KEBAB code at the CLI boundary, and
        `grill_workspace.py migrate-v3` is the real, callable, zero
        INVALID-ARGUMENTS command it is asking a caller to run.
        """
        item = self._init_item("wa")
        metadata = self._metadata(item)
        with self.assertRaises(WORK_ITEM_V3.WorkItemError) as ctx:
            WORK_ITEM_V3.require_v3(metadata, "some-v3-only-operation", "wa")
        self.assertEqual(ctx.exception.code, "WORK_ITEM_V3_REQUIRED")
        # This wiring is why the probe now says v3 readers are wired: the
        # migration_note it hands back reflects that, live.
        self.assertTrue(ctx.exception.details.get("v3_readers_wired"))

        with self.assertRaises(WORKSPACE_MODULE.CliFailure) as cli_ctx:
            WORKSPACE_MODULE.raise_from_work_item_error(ctx.exception)
        self.assertEqual(cli_ctx.exception.code, "WORK-ITEM-V3-REQUIRED")
        self.assertEqual(cli_ctx.exception.payload()["work_id"], "wa")

        process, payload = invoke("migrate-v3", self.root, "--work-id", "wa", "--apply")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))


# ---------------------------------------------------------------------------
# LD-010 item 3 / §5.7, 22 Core: exactly one JSON document on stdout even when
# grill_core_module()'s loader hits a syntactically broken or unloadable
# grill_core/*.py sibling.
# ---------------------------------------------------------------------------


class ImportFailureContract(WiringHarness):
    def _broken_scripts_copy(self, scratch: Path) -> Path:
        """A disposable copy of scripts/ with grill_core/work_item_v3.py
        corrupted -- never the live plugin tree. Returns the copy's
        grill_workspace.py path; every loader in this codebase resolves
        siblings relative to ``__file__``, so invoking the copy exercises the
        exact same code with only that one file different.
        """
        copy_root = scratch / "scripts"
        shutil.copytree(SCRIPTS, copy_root)
        (copy_root / "grill_core" / "work_item_v3.py").write_text("def broken(:\n", encoding="utf-8")
        return copy_root / "grill_workspace.py"

    def _run_broken(self, workspace: Path, *args: object) -> tuple[subprocess.CompletedProcess[str], dict]:
        process = subprocess.run(
            [sys.executable, str(workspace), *(str(a) for a in args)], text=True, capture_output=True, check=False,
        )
        lines = process.stdout.splitlines()
        self.assertEqual(len(lines), 1, f"stdout={process.stdout!r} stderr={process.stderr!r}")
        return process, json.loads(lines[0])

    def test_broken_grill_core_yields_one_json_for_migrate_v3(self) -> None:
        self._init_item("wa")
        with tempfile.TemporaryDirectory() as scratch:
            broken_workspace = self._broken_scripts_copy(Path(scratch))
            process, payload = self._run_broken(broken_workspace, "migrate-v3", self.root, "--work-id", "wa", "--apply")
        self.assertEqual(process.returncode, 2, payload)
        self.assertEqual(payload["code"], "GRILL-CORE-UNAVAILABLE")
        self.assertIn(payload.get("error"), {"SyntaxError", "ImportError"})

    def test_broken_grill_core_yields_one_json_for_audit_on_a_v3_bundle(self) -> None:
        """audit only reaches grill_core_module() when the bundle is already v3
        (the dual-read probe routes on immutable.schema), so migrate it for
        real first with the live, working wiring.
        """
        self._init_item("wa")
        process, applied = invoke("migrate-v3", self.root, "--work-id", "wa", "--apply")
        self.assertEqual((process.returncode, applied["verdict"]), (0, "APPLIED"))
        with tempfile.TemporaryDirectory() as scratch:
            broken_workspace = self._broken_scripts_copy(Path(scratch))
            process, payload = self._run_broken(broken_workspace, "audit", self.root, "--work-id", "wa")
        self.assertEqual(process.returncode, 2, payload)
        self.assertEqual(payload["code"], "GRILL-CORE-UNAVAILABLE")

    def test_runtime_error_loading_grill_core_is_also_structured(self) -> None:
        """A module-load failure is not limited to syntax/import errors; the
        public CLI must not leak a traceback or the NO-GO exit code for an
        arbitrary exception raised while loading an optional core capability.
        """
        self._init_item("wa")
        with tempfile.TemporaryDirectory() as scratch:
            copy_root = Path(scratch) / "scripts"
            shutil.copytree(SCRIPTS, copy_root)
            (copy_root / "grill_core" / "work_item_v3.py").write_text(
                "raise RuntimeError('loader boom')\n", encoding="utf-8"
            )
            process, payload = self._run_broken(
                copy_root / "grill_workspace.py", "migrate-v3", self.root, "--work-id", "wa", "--apply"
            )
        self.assertEqual(process.returncode, 2, payload)
        self.assertEqual(payload["code"], "GRILL-CORE-UNAVAILABLE")
        self.assertNotIn("Traceback", process.stderr)

    def test_system_exit_and_stdout_noise_loading_grill_core_stay_one_json(self) -> None:
        self._init_item("wa")
        for source in ("raise SystemExit(7)\n", "print('IMPORT-NOISE'); raise RuntimeError('loader boom')\n"):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as scratch:
                copy_root = Path(scratch) / "scripts"
                shutil.copytree(SCRIPTS, copy_root)
                (copy_root / "grill_core" / "work_item_v3.py").write_text(source, encoding="utf-8")
                process, payload = self._run_broken(
                    copy_root / "grill_workspace.py", "migrate-v3", self.root, "--work-id", "wa", "--apply"
                )
            self.assertEqual(process.returncode, 2, payload)
            self.assertEqual(payload["code"], "GRILL-CORE-UNAVAILABLE")


class LazyCoreFailureContract(WiringHarness):
    """Nested core loads are also public JSON boundaries, not just the first one."""

    def _copied_skill(self, scratch: Path) -> Path:
        copied = scratch / "grill-with-docs"
        shutil.copytree(SKILL, copied)
        return copied

    def test_v3_checkpoint_late_step_skills_runtime_error_is_one_blocked_json(self) -> None:
        self._init_item("wa")
        (self.root / "WORKFLOW.md").write_bytes(render_v3_workflow_bytes())
        process, payload = invoke(
            "checkpoint", self.root, "--work-id", "wa", "--step", "specify", "--state", "in-progress", "--reason", "start"
        )
        self.assertEqual((process.returncode, payload["verdict"]), (0, "UPDATED"))
        (self.root / "evidence.md").write_text("evidence\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as scratch:
            copied = self._copied_skill(Path(scratch))
            (copied / "scripts/grill_core/step_skills.py").write_text(
                "print('IMPORT-NOISE'); raise RuntimeError('late loader boom')\n", encoding="utf-8"
            )
            process = subprocess.run(
                [sys.executable, str(copied / "scripts/grill_workspace.py"), "checkpoint", str(self.root),
                 "--work-id", "wa", "--step", "specify", "--state", "complete", "--evidence", "evidence.md", "--reason", "done"],
                text=True, capture_output=True, check=False,
            )
        self.assertEqual(len(process.stdout.splitlines()), 1, process.stdout)
        payload = json.loads(process.stdout)
        self.assertEqual((process.returncode, payload["code"]), (2, "FILESYSTEM"))
        self.assertNotIn("IMPORT-NOISE", process.stdout)
        self.assertNotIn("Traceback", process.stderr)

    def test_hook_hides_system_exit_and_stdout_from_workflow_v3_loader(self) -> None:
        (self.root / "WORKFLOW.md").write_bytes(render_v3_workflow_bytes())
        with tempfile.TemporaryDirectory() as scratch:
            copied = self._copied_skill(Path(scratch))
            (copied / "scripts/grill_core/workflow_v3.py").write_text(
                "print('IMPORT-NOISE'); raise SystemExit(7)\n", encoding="utf-8"
            )
            process = subprocess.run(
                [sys.executable, str(copied / "scripts/ensure_workflow.py"), "--hook"], cwd=self.root,
                input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.root)}),
                text=True, capture_output=True, check=False,
            )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(len(process.stdout.splitlines()), 1, process.stdout)
        payload = json.loads(process.stdout)
        self.assertIn("incompatível", payload["hookSpecificOutput"]["additionalContext"])
        self.assertNotIn("IMPORT-NOISE", process.stdout)
        self.assertNotIn("Traceback", process.stderr)


# ---------------------------------------------------------------------------
# v3 checkpoint execution boundary: ordinary evidence is not a receipt.
# ---------------------------------------------------------------------------


class CheckpointAttestationWiringContract(WiringHarness):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "WORKFLOW.md").write_bytes(render_v3_workflow_bytes())

    def _start_specify(self) -> None:
        process, payload = invoke(
            "checkpoint", self.root, "--work-id", "wa", "--step", "specify", "--state", "in-progress", "--reason", "start"
        )
        self.assertEqual((process.returncode, payload["verdict"]), (0, "UPDATED"))

    def _receipt(self) -> Path:
        project_id = STORE.project_identity(self.root)["project_id"]
        chain = ATTESTATION_FIXTURES.build_chain(
            step_id="specify", project_id=project_id, work_item_id="wa", run_id="run-checkpoint"
        )
        bundle = {
            "schema": "checkpoint-attestation/v1",
            "resolution": chain["resolution"], "dispatch_intent": chain["dispatch_intent"],
            "invocation_started": chain["invocation_started"], "invocation_terminal": chain["invocation_terminal"],
            "step_output": chain["step_output"], "catalog": ATTESTATION_FIXTURES.catalog(),
        }
        path = self.root / "receipts" / "specify.json"
        path.parent.mkdir()
        path.write_text(json.dumps(bundle, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return path

    def test_v3_checkpoint_rejects_arbitrary_evidence_without_attestation(self) -> None:
        self._init_item("wa")
        self._start_specify()
        evidence = self.root / "evidence.md"
        evidence.write_text("green but unattested\n", encoding="utf-8")
        process, payload = invoke(
            "checkpoint", self.root, "--work-id", "wa", "--step", "specify", "--state", "complete",
            "--evidence", "evidence.md", "--reason", "done",
        )
        self.assertEqual((process.returncode, payload["code"]), (2, "ATTESTATION-REQUIRED"))
        state = json.loads((self.root / ".grill/work-items/wa/state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["development"]["steps"]["specify"], "in-progress")

    def test_v3_checkpoint_accepts_a_cooperative_structural_chain(self) -> None:
        """The coordinator/subagent supplies a correlated receipt for the run.

        This is a cooperative workflow contract, not cryptographic proof of
        provenance.  The public boundary still rejects missing, malformed,
        replayed, stale, diverged, and non-terminal chains.
        """
        self._init_item("wa")
        self._start_specify()
        evidence = self.root / "evidence.md"
        evidence.write_text("canonical skill completed\n", encoding="utf-8")
        receipt = self._receipt()
        process, payload = invoke(
            "checkpoint", self.root, "--work-id", "wa", "--step", "specify", "--state", "complete",
            "--evidence", "evidence.md", "--attestation", receipt.relative_to(self.root), "--reason", "done",
        )
        self.assertEqual((process.returncode, payload["verdict"]), (0, "UPDATED"))
        state = json.loads((self.root / ".grill/work-items/wa/state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["development"]["steps"]["specify"], "complete")
        self.assertEqual(state["development"]["attestation_campaign"]["run_id"], "run-checkpoint")
        self.assertEqual(state["development"]["attested_outputs"]["specify"]["step_id"], "specify")


# ---------------------------------------------------------------------------
# Item 3: ensure_workflow.py recognises v3 alongside v2
# ---------------------------------------------------------------------------


class EnsureWorkflowV3Contract(WiringHarness):
    V2_ESSENTIAL = (
        "## Loop externo", "## Ciclo externo de execução", "specify", "plan", "checklist", "tasks",
        "analyze", "agent-assign", "agent-execute", "converge", "verify", "review", "ship",
        "PLAN_ONLY_STOP", "Spec Kit >=0.11.2", "A–E", "no PR", "hotfix-fast", "HOTFIX-GO",
    )

    def _v3_workflow_bytes(self) -> bytes:
        return render_v3_workflow_bytes()

    def test_v2_essential_tuple_and_version_are_frozen(self) -> None:
        """Guards the literal LD-004 invariant: this round must not touch either."""
        self.assertEqual(ENSURE_WORKFLOW_MODULE.VERSION, "v2")
        self.assertEqual(ENSURE_WORKFLOW_MODULE.MARKER, "grill-with-docs-workflow:v2")
        self.assertEqual(ENSURE_WORKFLOW_MODULE.ESSENTIAL, self.V2_ESSENTIAL)

    def test_v2_workflow_is_byte_intact_and_ensure_reports_v2(self) -> None:
        before = (self.root / "WORKFLOW.md").read_bytes()
        result = hook_run("--ensure", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "REUSED")
        self.assertEqual(payload["version"], "v2")
        self.assertEqual((self.root / "WORKFLOW.md").read_bytes(), before)

    def test_bare_v3_marker_alone_is_still_blocked(self) -> None:
        """Real attack, mirrors the existing v2-analog assertion: a marker is not content."""
        (self.root / "WORKFLOW.md").write_text("<!-- grill-with-docs-workflow:v3 -->\njust the marker, nothing else\n")
        result = hook_run("--ensure", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reason"], "incompatible workflow")

    def test_migrated_v3_workflow_keeps_ensure_and_init_and_preflight_working(self) -> None:
        v3_bytes = self._v3_workflow_bytes()
        (self.root / "WORKFLOW.md").write_bytes(v3_bytes)

        result = hook_run("--ensure", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "REUSED")
        self.assertEqual(payload["version"], "v3")
        # A REUSED v3 document is read-only, never rewritten to v2.
        self.assertEqual((self.root / "WORKFLOW.md").read_bytes(), v3_bytes)

        process, init_payload = invoke("init", self.root, "--type", "feature", "--slug", "beta", "--work-id", "wv3")
        self.assertEqual(process.returncode, 0, (init_payload, process.stderr))
        self.assertEqual(init_payload["workflow"]["status"], "REUSED")
        self.assertEqual((self.root / "WORKFLOW.md").read_bytes(), v3_bytes)

        # preflight's overall verdict/exit code tracks external dependency
        # detection (spec-kit extensions, backlogctl, ...), unrelated to this
        # piece's scope; only its `workflow` sub-payload is this test's
        # concern, and it must not be WORKFLOW-UNAVAILABLE / BLOCKED.
        process, preflight_payload = invoke("preflight", self.root, "--skip-backlog")
        self.assertEqual(preflight_payload["workflow"]["status"], "REUSED")

    def test_v3_compatible_delegates_to_grill_core_workflow_v3(self) -> None:
        v3_text = self._v3_workflow_bytes().decode("utf-8")
        self.assertTrue(ENSURE_WORKFLOW_MODULE.compatible_v3(v3_text))
        self.assertEqual(ENSURE_WORKFLOW_MODULE.compatible_v3(v3_text), WORKFLOW_V3.compatible_v3(v3_text))
        self.assertFalse(ENSURE_WORKFLOW_MODULE.compatible_v3("grill-with-docs-workflow:v3 nothing else"))


# ---------------------------------------------------------------------------
# LD-010 item 2: the v3 registry-pin gate closes the fail-open this round
# opened -- a document that declares the v3 marker AND the whole ESSENTIAL
# frontier, but whose pinned registry_sha256 does not match the live
# registry bytes, must never be treated as READY by --ensure, init or the
# hook. Both attacks come straight from the wiring critic's verdict: the
# unrendered placeholder and a forged pin each still CONTAIN the substring
# "registry_sha256", so the old substring-only check let them both through.
# ---------------------------------------------------------------------------


class RegistryPinGateContract(WiringHarness):
    def _assert_blocked_everywhere(self, work_id: str) -> None:
        result = hook_run("--ensure", str(self.root))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["reason"], "incompatible workflow")

        process, init_payload = invoke("init", self.root, "--type", "feature", "--slug", "pingate", "--work-id", work_id)
        self.assertEqual(process.returncode, 2, (init_payload, process.stderr))
        self.assertEqual(init_payload["code"], "WORKFLOW-UNAVAILABLE")

        hook_result = hook_run(
            "--hook", cwd=self.root, input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.root)}),
        )
        self.assertEqual(hook_result.returncode, 0)
        self.assertEqual(hook_result.stderr, "")
        context = json.loads(hook_result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("incompatível", context)
        # Never the status projection: this is the exact regression the gate
        # exists to prevent ("nunca a projeção de status").
        self.assertNotIn("Fluxo: specify", context)
        self.assertNotIn("registry_sha256=", context)

    def test_unrendered_registry_placeholder_blocks_ensure_init_and_hook(self) -> None:
        """Real attack: the v3 marker and the whole ESSENTIAL frontier are present
        (the template ships that way), but __REGISTRY_SHA256__ was never
        rendered. The literal placeholder still contains the substring
        "registry_sha256", so a substring-only readiness check used to pass it.
        """
        raw = WORKFLOW_TEMPLATE_V3.read_bytes()
        self.assertIn(b"__REGISTRY_SHA256__", raw)
        (self.root / "WORKFLOW.md").write_bytes(raw)
        self._assert_blocked_everywhere("wpin1")

    def test_forged_registry_pin_blocks_ensure_init_and_hook(self) -> None:
        """Real attack: a fully-rendered v3 document whose pin was then hand-edited
        to an attacker-chosen 64-hex digest that does not match the live registry.
        """
        v3_bytes = render_v3_workflow_bytes()
        live_hash = WORKFLOW_V3.registry_state()["sha256"]
        forged = v3_bytes.replace(live_hash.encode("ascii"), b"sha256:" + b"deadbeef" * 8)
        self.assertNotEqual(forged, v3_bytes)
        (self.root / "WORKFLOW.md").write_bytes(forged)
        self._assert_blocked_everywhere("wpin2")

    def test_correctly_pinned_v3_workflow_is_still_ready(self) -> None:
        """Control: the gate does not false-positive on a correctly rendered document."""
        (self.root / "WORKFLOW.md").write_bytes(render_v3_workflow_bytes())
        result = hook_run("--ensure", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["version"], "v3")


# ---------------------------------------------------------------------------
# Item 4: hook injects registry_sha256 + anti-emulation phrase before status
# ---------------------------------------------------------------------------


class HookRegistryInjectionContract(WiringHarness):
    def test_registry_sha256_matches_across_computation_paths(self) -> None:
        """LD-001: peça C owns the asset+function, peça D consumes -- both must agree."""
        raw = hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
        via_workflow_v3 = WORKFLOW_V3.registry_state()["sha256"]
        self.assertEqual(via_workflow_v3, f"sha256:{raw}")
        prefix = ENSURE_WORKFLOW_MODULE._registry_prefix()
        self.assertIn(f"registry_sha256={raw};", prefix)
        self.assertIn("read, resolve and invoke; do not emulate.", prefix)

    def test_hook_includes_registry_hash_and_anti_emulation_phrase(self) -> None:
        hook_run("--ensure", str(self.root))
        before = snapshot(self.root)
        registry_sha256 = hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
        result = hook_run("--hook", cwd=self.root, input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.root)}))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(f"registry_sha256={registry_sha256};", context)
        self.assertIn("read, resolve and invoke; do not emulate.", context)
        self.assertIn(hashlib.sha256((self.root / "WORKFLOW.md").read_bytes()).hexdigest(), context)
        self.assertIn("agent-assign", context)
        self.assertEqual(snapshot(self.root), before)

    def test_registry_prefix_survives_truncation_the_status_tail_does_not(self) -> None:
        """Real attack: force >2048 bytes and prove truncation eats the TAIL, not the head.

        A status line stuffed with a filler block PLUS a unique sentinel at
        its very end is the strongest version of this attack: if the
        registry prefix were placed after the status projection (the bug
        this ordering exists to prevent), the sentinel would survive and the
        registry hash / phrase would be the first bytes cut instead.
        """
        hook_run("--ensure", str(self.root))
        tail_sentinel = "TAIL-SENTINEL-MUST-BE-CUT"
        huge_status_line = "STATUS-" + ("Q" * 5000) + tail_sentinel
        stdin = io.StringIO(json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.root)}))
        buffer = io.StringIO()
        with mock.patch.object(ENSURE_WORKFLOW_MODULE.sys, "stdin", stdin), \
             mock.patch.object(ENSURE_WORKFLOW_MODULE, "human_status", return_value=huge_status_line), \
             contextlib.redirect_stdout(buffer):
            code = ENSURE_WORKFLOW_MODULE.hook()
        self.assertEqual(code, 0)
        rendered = buffer.getvalue()
        self.assertLessEqual(len(rendered), 2048)
        payload = json.loads(rendered)
        context = payload["hookSpecificOutput"]["additionalContext"]
        registry_sha256 = hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
        self.assertIn(f"registry_sha256={registry_sha256};", context)
        self.assertIn("read, resolve and invoke; do not emulate.", context)
        self.assertIn("[TRUNCATED]", context)
        # The tail -- including the sentinel placed at the very end of the
        # original message -- really was cut, not merely present-but-whole.
        self.assertNotIn(tail_sentinel, context)
        self.assertNotIn("Fluxo: specify", context)

    def test_hook_stays_read_only_on_the_v3_execution_ready_path(self) -> None:
        v3_bytes = render_v3_workflow_bytes()
        (self.root / "WORKFLOW.md").write_bytes(v3_bytes)
        hook_run("--ensure", str(self.root))
        before = snapshot(self.root)
        result = hook_run("--hook", cwd=self.root, input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.root)}))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("registry_sha256=", context)
        self.assertIn("read, resolve and invoke; do not emulate.", context)
        self.assertEqual(snapshot(self.root), before)


# ---------------------------------------------------------------------------
# Item 5: SCREAMING_SNAKE -> SCREAMING-KEBAB translation table
# ---------------------------------------------------------------------------


class V3CodeTranslationContract(unittest.TestCase):
    PLAN_LITERAL_CODES = {
        "BLOCKED_CAPABILITY": "BLOCKED-CAPABILITY",
        "STALE_LEASE": "STALE-LEASE",
        "ORCHESTRATOR_INVALID": "ORCHESTRATOR-INVALID",
        "STALE_PLAN": "STALE-PLAN",
        "UNATTESTED_STEP_OUTPUT": "UNATTESTED-STEP-OUTPUT",
        "STALE_SKILL_RESOLUTION": "STALE-SKILL-RESOLUTION",
        "PROJECT_IDENTITY_DIVERGENCE": "PROJECT-IDENTITY-DIVERGENCE",
        "STATE_DIVERGENCE": "STATE-DIVERGENCE",
    }

    def test_all_eight_plan_literal_codes_translate(self) -> None:
        for snake, kebab in self.PLAN_LITERAL_CODES.items():
            with self.subTest(code=snake):
                self.assertEqual(WORKSPACE_MODULE.translate_v3_code(snake), kebab)

    def test_v2_contract_codes_pass_through_unchanged(self) -> None:
        """Reusing the existing v2 code is correct; a hyphenated code is never rewritten."""
        for code in ("METADATA-SCHEMA", "LOCK-CONTENTION", "IMMUTABLE-TAMPERED", "BUNDLE-INTEGRITY",
                     "WORK-ITEM-MISSING", "WORK-ID-DIVERGENCE", "FILESYSTEM"):
            with self.subTest(code=code):
                self.assertEqual(WORKSPACE_MODULE.translate_v3_code(code), code)

    def test_every_work_item_v3_emitted_code_is_routable(self) -> None:
        """LD-008 item 2: a real AST exhaustiveness scan, not a hand-typed set.

        Walks the actual ``grill_core/work_item_v3.py`` source (see
        ``work_item_v3_emitted_codes``) and requires every single code it can
        raise -- the eight plan-literal names, its own v3-only SNAKE
        vocabulary, and every reused v2 KEBAB code -- to be routable through
        ``translate_v3_code`` without leaving a stray underscore. Adding a new
        ``blocked("SOME_NEW_CODE", ...)`` call to that module makes this test
        pick it up automatically; nothing here has to be updated by hand.
        """
        codes = work_item_v3_emitted_codes()
        # Sanity floor: the scan really walked the module and found the
        # SNAKE vocabulary this test exists to guard, not an empty AST.
        self.assertGreaterEqual(len(codes), 9)
        self.assertIn("WORKTREE_PATH_FORBIDDEN", codes)
        for code in sorted(codes):
            with self.subTest(code=code):
                translated = WORKSPACE_MODULE.translate_v3_code(code)
                self.assertNotIn("_", translated)

    def test_unknown_future_snake_code_would_also_be_caught(self) -> None:
        """Attack against a hypothetical AST-scan bypass: a code shaped like the
        module's real vocabulary but not literally present today must still
        translate cleanly through the generic fallback -- proving routability
        does not depend on the exhaustiveness test's fixed snapshot of codes.
        """
        codes = work_item_v3_emitted_codes()
        hypothetical = "BRAND_NEW_V3_ONLY_CONDITION"
        self.assertNotIn(hypothetical, codes)
        self.assertEqual(WORKSPACE_MODULE.translate_v3_code(hypothetical), "BRAND-NEW-V3-ONLY-CONDITION")

    def test_unknown_snake_code_still_translates_mechanically(self) -> None:
        """Beyond the eight AND beyond today's work_item_v3 codes: the fallback is general."""
        self.assertEqual(WORKSPACE_MODULE.translate_v3_code("SOME_OTHER_SNAKE_CODE"), "SOME-OTHER-SNAKE-CODE")

    def test_mixed_hyphen_and_underscore_code_is_left_alone(self) -> None:
        """Real attack against a naive blanket .replace('_','-'): a code that already
        carries a hyphen (the v2 spelling) must never be mechanically mangled
        just because it also happens to contain an underscore.
        """
        mixed = "STALE_LEASE-EXTRA"
        self.assertEqual(WORKSPACE_MODULE.translate_v3_code(mixed), mixed)

    def test_near_miss_translates_whole_string_not_a_table_substring(self) -> None:
        """Attack against a hypothetical `code.replace(table_key, table_value)` bug:
        the wrapping segments must be translated too, not just the embedded
        eight-table name, and nothing from a different table entry leaks in.
        """
        poisoned = "PRE_STALE_LEASE_SUFFIX"
        self.assertEqual(WORKSPACE_MODULE.translate_v3_code(poisoned), "PRE-STALE-LEASE-SUFFIX")

    def test_clifailure_extra_never_clobbers_canonical_payload_fields(self) -> None:
        """Real attack: extra dict tries to overwrite verdict/code/error; canonical wins."""
        failure = WORKSPACE_MODULE.CliFailure(
            2, "BLOCKED", "REAL-CODE", "real message",
            extra={"verdict": "HACKED", "code": "HACKED", "error": "HACKED", "work_id": "kept"},
        )
        payload = failure.payload()
        self.assertEqual(payload["verdict"], "BLOCKED")
        self.assertEqual(payload["code"], "REAL-CODE")
        self.assertEqual(payload["error"], "real message")
        self.assertEqual(payload["work_id"], "kept")

    def test_raise_from_work_item_error_translates_at_the_boundary(self) -> None:
        """Uses the REAL WorkItemError type from grill_core.work_item_v3, not a stand-in."""
        error = WORK_ITEM_V3.WorkItemError(
            exit_code=2, verdict="BLOCKED", code="STALE_LEASE", message="synthetic",
            details={"work_id": "zz"},
        )
        with self.assertRaises(WORKSPACE_MODULE.CliFailure) as ctx:
            WORKSPACE_MODULE.raise_from_work_item_error(error)
        self.assertEqual(ctx.exception.code, "STALE-LEASE")
        self.assertEqual(ctx.exception.exit_code, 2)
        self.assertEqual(ctx.exception.verdict, "BLOCKED")
        self.assertEqual(ctx.exception.payload()["work_id"], "zz")

    def test_raise_from_work_item_error_passes_through_kebab_codes_unrouted(self) -> None:
        error = WORK_ITEM_V3.WorkItemError(
            exit_code=2, verdict="BLOCKED", code="METADATA-SCHEMA", message="synthetic", details={},
        )
        with self.assertRaises(WORKSPACE_MODULE.CliFailure) as ctx:
            WORKSPACE_MODULE.raise_from_work_item_error(error)
        self.assertEqual(ctx.exception.code, "METADATA-SCHEMA")


if __name__ == "__main__":
    unittest.main(verbosity=1)
