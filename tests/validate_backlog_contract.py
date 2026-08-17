#!/usr/bin/env python3
"""Executable contract for the preview-first bridge to the external backlog."""
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

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"
SCRIPT = PLUGIN / "skills/grill-with-docs/scripts/backlog_bridge.py"
CLI = "/stub/backlogctl"
DB = "/stub/backlog.db"


def load() -> object:
    spec = importlib.util.spec_from_file_location("backlog_bridge_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load()


def envelope(data, *, operation="op", changed=False) -> str:
    return json.dumps({
        "result": "ok", "operation": operation, "contract_version": "2",
        "changed": changed, "data": data, "warnings": [], "next_action": "",
    })


class StubToolchain:
    """Records every backlogctl invocation and answers from a scripted table."""

    def __init__(self, answers=None):
        self.environ: dict[str, str] = {}
        self.answers = answers or {}
        self.calls: list[list[str]] = []

    def key(self, argv):
        return tuple(part for part in argv if not part.startswith("/stub"))

    def run(self, argv, *, cwd=None, timeout=None):
        self.calls.append(list(argv))
        for prefix, answer in self.answers.items():
            if tuple(argv[2:2 + len(prefix)]) == prefix:
                return answer
        return 0, envelope([])

    def mutations(self):
        return [call for call in self.calls if call[2] in {"store", "create", "bind"} or call[2:4] in (["backlog", "create"], ["backlog", "bind"], ["item", "add"])]


class Envelope(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = StubToolchain()

    def test_domain_error_and_wrong_contract_version_both_fail_closed(self) -> None:
        for answer in (
            (1, json.dumps({"result": "error", "error": "nope"})),
            (0, json.dumps({"result": "ok", "contract_version": "1", "data": []})),
            (0, "not json at all"),
        ):
            tools = StubToolchain({("backlog", "list"): answer})
            with self.assertRaises(MODULE.BacklogUnavailable):
                MODULE.call(CLI, tools, DB, ["backlog", "list"])

    def test_json_flag_precedes_the_family_and_db_is_always_passed(self) -> None:
        MODULE.call(CLI, self.tools, DB, ["backlog", "list"])
        self.assertEqual(self.tools.calls[0][:3], [CLI, "--json", "backlog"])
        self.assertEqual(self.tools.calls[0][-2:], ["--db", DB])


class Identity(unittest.TestCase):
    def test_code_is_derived_from_the_repository_name(self) -> None:
        self.assertEqual(MODULE.derive_identity(Path("/x/grill-with-docs"), set())[0], "GWD")
        self.assertEqual(MODULE.derive_identity(Path("/x/timbro"), set())[0], "TXX")

    def test_collision_produces_a_free_code(self) -> None:
        code, _ = MODULE.derive_identity(Path("/x/grill-with-docs"), {"GWD"})
        self.assertNotEqual(code, "GWD")
        self.assertEqual(len(code), 3)


class Resolution(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def tools_with(self, backlogs):
        return StubToolchain({("backlog", "list"): (0, envelope(backlogs))})

    def test_bound_path_match_wins(self) -> None:
        tools = self.tools_with([{"code": "AAA", "name": "other", "bound_path": str(self.root)}])
        resolution = MODULE.resolve_backlog(self.root, CLI, tools, DB)
        self.assertEqual(resolution["status"], "BOUND")
        self.assertEqual(resolution["code"], "AAA")

    def test_unbound_backlog_with_the_repository_name_only_needs_binding(self) -> None:
        tools = self.tools_with([{"code": "BBB", "name": self.root.name, "bound_path": ""}])
        self.assertEqual(MODULE.resolve_backlog(self.root, CLI, tools, DB)["status"], "NEEDS-BIND")

    def test_nothing_matching_needs_creation(self) -> None:
        tools = self.tools_with([{"code": "CCC", "name": "unrelated", "bound_path": "/elsewhere"}])
        self.assertEqual(MODULE.resolve_backlog(self.root, CLI, tools, DB)["status"], "NEEDS-CREATE")

    def test_requested_code_wins_over_the_derived_one(self) -> None:
        tools = self.tools_with([{"code": "SGD", "name": "inherited-name", "bound_path": ""}])
        resolution = MODULE.resolve_backlog(self.root, CLI, tools, DB, "SGD")
        self.assertEqual(resolution["status"], "NEEDS-BIND")
        self.assertEqual(resolution["code"], "SGD")
        self.assertEqual(resolution["name"], "inherited-name")

    def test_requested_code_that_does_not_exist_is_created(self) -> None:
        tools = self.tools_with([])
        resolution = MODULE.resolve_backlog(self.root, CLI, tools, DB, "NEW")
        self.assertEqual(resolution["status"], "NEEDS-CREATE")
        self.assertEqual(resolution["code"], "NEW")

    def test_requested_code_already_bound_elsewhere_fails_closed(self) -> None:
        tools = self.tools_with([{"code": "SGD", "name": "n", "bound_path": "/other/repo"}])
        with self.assertRaises(MODULE.BacklogUnavailable):
            MODULE.resolve_backlog(self.root, CLI, tools, DB, "SGD")

    def test_repository_bound_to_another_code_is_never_silently_rebound(self) -> None:
        tools = self.tools_with([{"code": "AAA", "name": "n", "bound_path": str(self.root)}])
        with self.assertRaises(MODULE.BacklogUnavailable):
            MODULE.resolve_backlog(self.root, CLI, tools, DB, "SGD")


class BindLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.original = MODULE.resolve_cli

    def tearDown(self) -> None:
        MODULE.resolve_cli = self.original
        self.temporary.cleanup()

    def inject(self, tools):
        MODULE.resolve_cli = lambda given=None: (CLI, tools)

    def test_preview_is_read_only(self) -> None:
        tools = StubToolchain({("backlog", "list"): (0, envelope([]))})
        self.inject(tools)
        payload = MODULE.ensure_bind(self.root, apply=False, db=DB)
        self.assertEqual(payload["verdict"], "PREVIEW")
        self.assertFalse(payload["changed"])
        self.assertEqual(tools.mutations(), [])

    def test_already_bound_is_ok_and_still_read_only(self) -> None:
        tools = StubToolchain({("backlog", "list"): (0, envelope([{"code": "AAA", "name": "n", "bound_path": str(self.root)}]))})
        self.inject(tools)
        payload = MODULE.ensure_bind(self.root, apply=True, db=DB)
        self.assertEqual(payload["verdict"], "OK")
        self.assertFalse(payload["changed"])
        self.assertEqual(tools.mutations(), [])

    def test_apply_creates_then_binds(self) -> None:
        tools = StubToolchain({("backlog", "list"): (0, envelope([]))})
        self.inject(tools)
        MODULE.ensure_bind(self.root, apply=True, db=DB)
        families = [call[2:4] for call in tools.calls]
        self.assertIn(["backlog", "create"], families)
        self.assertIn(["backlog", "bind"], families)
        self.assertLess(families.index(["backlog", "create"]), families.index(["backlog", "bind"]))

    def test_unresolvable_cli_is_reported_not_raised_by_the_entry_point(self) -> None:
        def refuse(given=None):
            raise MODULE.BacklogUnavailable("backlogctl not installed")

        MODULE.resolve_cli = refuse
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            self.assertEqual(MODULE.main([str(self.root)]), 2)
        self.assertEqual(json.loads(captured.getvalue())["code"], "BACKLOG-UNAVAILABLE")


class DeferredParsing(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, text):
        path = self.root / "DECISION-BACKLOG.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_only_open_blocks_are_mirrored(self) -> None:
        path = self.write(
            "# DECISION-BACKLOG\n\n"
            "## BL-0001 — Limite por cliente\n- state: open\n- motivo: pendente\n\n"
            "## BL-0002 — Ja resolvida\n- state: resolved\n- motivo: fechada\n"
        )
        entries = MODULE.parse_deferred(path)
        self.assertEqual([entry["id"] for entry in entries], ["BL-0001"])
        self.assertEqual(entries[0]["motivo"], "pendente")

    def test_absent_or_empty_backlog_yields_nothing(self) -> None:
        self.assertEqual(MODULE.parse_deferred(self.root / "missing.md"), [])
        self.assertEqual(MODULE.parse_deferred(self.write("# DECISION-BACKLOG\n")), [])


class ItemSync(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.item = self.root / "item"
        self.item.mkdir()
        (self.item / "DECISION-BACKLOG.md").write_text(
            "# DECISION-BACKLOG\n\n## BL-0001 — Limite por cliente\n- state: open\n- criticality: high\n",
            encoding="utf-8",
        )
        self.original = MODULE.resolve_cli

    def tearDown(self) -> None:
        MODULE.resolve_cli = self.original
        self.temporary.cleanup()

    def inject(self, tools):
        MODULE.resolve_cli = lambda given=None: (CLI, tools)

    def bound(self, items):
        return StubToolchain({
            ("backlog", "list"): (0, envelope([{"code": "AAA", "name": "n", "bound_path": str(self.root)}])),
            ("item", "list"): (0, envelope(items)),
        })

    def test_unbound_backlog_blocks_the_sync(self) -> None:
        tools = StubToolchain({("backlog", "list"): (0, envelope([]))})
        self.inject(tools)
        payload = MODULE.sync_items(self.root, self.item, "work-a", apply=False, db=DB)
        self.assertEqual(payload["verdict"], "BLOCKED")
        self.assertEqual(payload["code"], "BACKLOG-NOT-BOUND")

    def test_preview_proposes_without_mutating(self) -> None:
        tools = self.bound([])
        self.inject(tools)
        payload = MODULE.sync_items(self.root, self.item, "work-a", apply=False, db=DB)
        self.assertEqual(payload["verdict"], "PREVIEW")
        self.assertFalse(payload["changed"])
        self.assertEqual([item["status"] for item in payload["items"]], ["PROPOSED"])
        self.assertEqual(tools.mutations(), [])

    def test_apply_adds_the_item_with_valid_category_and_criticality(self) -> None:
        tools = self.bound([])
        self.inject(tools)
        payload = MODULE.sync_items(self.root, self.item, "work-a", apply=True, db=DB)
        self.assertEqual(payload["verdict"], "APPLIED")
        argv = next(call for call in tools.calls if call[2:4] == ["item", "add"])
        self.assertEqual(argv[argv.index("--category") + 1], MODULE.CATEGORY)
        self.assertIn(argv[argv.index("--criticality") + 1], MODULE.CRITICALITY)
        self.assertTrue(argv[argv.index("--title") + 1].startswith("BL-0001 — "))

    def test_marker_makes_the_mirror_idempotent(self) -> None:
        description = f"x\n\n---\n{MODULE.WORK_ID_MARKER}: work-a\n{MODULE.BL_MARKER}: BL-0001\n"
        tools = self.bound([{"id": "AAA-1", "description": description}])
        self.inject(tools)
        payload = MODULE.sync_items(self.root, self.item, "work-a", apply=True, db=DB)
        self.assertEqual([item["status"] for item in payload["items"]], ["REUSED"])
        self.assertFalse(payload["changed"])
        self.assertEqual(tools.mutations(), [])

    def test_the_same_bl_in_another_work_item_is_not_deduplicated(self) -> None:
        description = f"x\n\n---\n{MODULE.WORK_ID_MARKER}: work-b\n{MODULE.BL_MARKER}: BL-0001\n"
        tools = self.bound([{"id": "AAA-1", "description": description}])
        self.inject(tools)
        payload = MODULE.sync_items(self.root, self.item, "work-a", apply=False, db=DB)
        self.assertEqual([item["status"] for item in payload["items"]], ["PROPOSED"])


class StateMap(unittest.TestCase):
    """T003 — the mapping is fixed by ADR-0003 and by the measured FSM."""

    def test_every_decision_state_maps_to_a_reachable_item_state(self) -> None:
        self.assertEqual(MODULE.STATE_TARGET,
                         {"open": "in_progress", "resolved": "done", "superseded": "cancelled"})

    def test_the_bridge_never_targets_open_or_merged(self) -> None:
        self.assertNotIn("open", set(MODULE.STATE_TARGET.values()))
        self.assertNotIn("merged", set(MODULE.STATE_TARGET.values()))

    def test_open_to_done_is_not_a_legal_transition(self) -> None:
        # The naive map resolved->done from a freshly created open item is
        # exactly what the measured FSM refuses; this is why items are born
        # in_progress.
        self.assertNotIn("done", MODULE.LEGAL_TRANSITIONS["open"])

    def test_every_target_is_reachable_from_the_birth_state(self) -> None:
        for target in MODULE.STATE_TARGET.values():
            self.assertIn(target, MODULE.LEGAL_TRANSITIONS["in_progress"], target)


class DeferredParsing(unittest.TestCase):
    """T008 — state is carried out, never used to filter."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "DECISION-BACKLOG.md"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, body: str) -> Path:
        self.path.write_text(body, encoding="utf-8")
        return self.path

    def test_terminal_decisions_are_returned_with_their_state(self) -> None:
        entries = MODULE.parse_deferred(self.write(
            "# DECISION-BACKLOG\n\n"
            "## BL-0001 — Aberta\n- state: open\n\n"
            "## BL-0002 — Resolvida\n- state: resolved\n\n"
            "## BL-0003 — Substituida\n- state: superseded\n"
        ))
        self.assertEqual([(e["id"], e["state"]) for e in entries],
                         [("BL-0001", "open"), ("BL-0002", "resolved"), ("BL-0003", "superseded")])

    def test_a_closed_milestone_still_has_something_to_mirror(self) -> None:
        # The defect this phase exists to fix: every decision resolved means
        # the old filter returned nothing exactly when the work was shippable.
        entries = MODULE.parse_deferred(self.write(
            "# DECISION-BACKLOG\n\n## BL-0001 — A\n- state: resolved\n\n## BL-0002 — B\n- state: resolved\n"
        ))
        self.assertEqual(len(entries), 2)

    def test_a_missing_file_is_not_an_error(self) -> None:
        self.assertEqual(MODULE.parse_deferred(self.path.with_name("absent.md")), [])


class Reconciliation(unittest.TestCase):
    """T009, T012-T015, T024-T026 — creation state, dedup and state repair."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.item = self.root / "item"
        self.item.mkdir()
        self.original = MODULE.resolve_cli

    def tearDown(self) -> None:
        MODULE.resolve_cli = self.original
        self.temporary.cleanup()

    def backlog(self, body: str) -> None:
        (self.item / "DECISION-BACKLOG.md").write_text(body, encoding="utf-8")

    def bound(self, items):
        tools = StubToolchain({
            ("backlog", "list"): (0, envelope([{"code": "AAA", "name": "n", "bound_path": str(self.root)}])),
            ("item", "list"): (0, envelope(items)),
        })
        MODULE.resolve_cli = lambda given=None: (CLI, tools)
        return tools

    def linked(self, work_id, bl_id, **extra):
        description = f"x\n\n---\n{MODULE.WORK_ID_MARKER}: {work_id}\n{MODULE.BL_MARKER}: {bl_id}\n"
        return {"id": "AAA-1", "description": description, **extra}

    def sync(self, tools, *, apply=False, work_id="work-a"):
        return MODULE.sync_items(self.root, self.item, work_id, apply=apply, db=DB)

    def status_of(self, argv):
        return argv[argv.index("--status") + 1]

    def test_a_resolved_decision_is_created_already_done(self) -> None:
        self.backlog("## BL-0001 — R\n- state: resolved\n")
        tools = self.bound([])
        self.sync(tools, apply=True)
        argv = next(call for call in tools.calls if call[2:4] == ["item", "add"])
        self.assertEqual(self.status_of(argv), "done")

    def test_a_superseded_decision_is_created_already_cancelled(self) -> None:
        self.backlog("## BL-0001 — S\n- state: superseded\n")
        tools = self.bound([])
        self.sync(tools, apply=True)
        argv = next(call for call in tools.calls if call[2:4] == ["item", "add"])
        self.assertEqual(self.status_of(argv), "cancelled")

    def test_an_open_decision_is_born_in_progress(self) -> None:
        self.backlog("## BL-0001 — O\n- state: open\n")
        tools = self.bound([])
        self.sync(tools, apply=True)
        argv = next(call for call in tools.calls if call[2:4] == ["item", "add"])
        self.assertEqual(self.status_of(argv), "in_progress")

    def test_a_second_apply_creates_nothing(self) -> None:
        self.backlog("## BL-0001 — O\n- state: open\n")
        tools = self.bound([self.linked("work-a", "BL-0001", status="in_progress")])
        payload = self.sync(tools, apply=True)
        self.assertEqual([entry["status"] for entry in payload["items"]], ["REUSED"])
        self.assertFalse(payload["changed"])
        self.assertEqual(tools.mutations(), [])

    def test_a_diverged_item_is_transitioned(self) -> None:
        self.backlog("## BL-0001 — R\n- state: resolved\n")
        tools = self.bound([self.linked("work-a", "BL-0001", status="in_progress")])
        payload = self.sync(tools, apply=True)
        self.assertEqual([entry["status"] for entry in payload["items"]], ["TRANSITIONED"])
        argv = next(call for call in tools.calls if call[2:4] == ["item", "transition"])
        self.assertEqual(self.status_of(argv), "done")
        self.assertEqual(argv[argv.index("--id") + 1], "AAA-1")

    def test_an_unreachable_target_is_refused_without_emitting_anything(self) -> None:
        # Real case observed in this repository: SGD-3 sits at open while its
        # decision is resolved, and open -> done has no legal path.
        self.backlog("## BL-0001 — R\n- state: resolved\n")
        tools = self.bound([self.linked("work-a", "BL-0001", status="open")])
        payload = self.sync(tools, apply=True)
        self.assertEqual([entry["status"] for entry in payload["items"]], ["TRANSITION-REFUSED"])
        self.assertFalse(payload["changed"])
        self.assertEqual([call for call in tools.calls if call[2:4] == ["item", "transition"]], [])

    def test_the_refusal_never_reaches_for_reconcile_status(self) -> None:
        self.backlog("## BL-0001 — R\n- state: resolved\n")
        tools = self.bound([self.linked("work-a", "BL-0001", status="open")])
        self.sync(tools, apply=True)
        self.assertEqual([call for call in tools.calls if "reconcile-status" in call], [])

    def test_an_item_without_a_reported_status_is_left_alone(self) -> None:
        self.backlog("## BL-0001 — R\n- state: resolved\n")
        tools = self.bound([self.linked("work-a", "BL-0001")])
        payload = self.sync(tools, apply=True)
        self.assertEqual([entry["status"] for entry in payload["items"]], ["REUSED"])
        self.assertEqual(tools.mutations(), [])

    def test_the_same_local_id_in_another_work_item_gets_its_own_item(self) -> None:
        self.backlog("## BL-0001 — O\n- state: open\n")
        tools = self.bound([self.linked("work-b", "BL-0001", status="in_progress")])
        payload = self.sync(tools, apply=False)
        self.assertEqual([entry["status"] for entry in payload["items"]], ["PROPOSED"])

    def test_preview_never_mutates_even_when_work_is_pending(self) -> None:
        self.backlog("## BL-0001 — O\n- state: open\n\n## BL-0002 — R\n- state: resolved\n")
        tools = self.bound([self.linked("work-a", "BL-0002", status="in_progress")])
        payload = self.sync(tools, apply=False)
        self.assertEqual(payload["verdict"], "PREVIEW")
        self.assertFalse(payload["changed"])
        self.assertEqual(tools.mutations(), [])
        self.assertEqual([entry["status"] for entry in payload["items"]], ["PROPOSED", "PROPOSED"])

    def test_an_interrupted_apply_converges_on_the_next_run(self) -> None:
        # First run created BL-0001 and died before BL-0002; the second run
        # must finish the job without duplicating what already landed.
        self.backlog("## BL-0001 — A\n- state: open\n\n## BL-0002 — B\n- state: open\n")
        tools = self.bound([self.linked("work-a", "BL-0001", status="in_progress")])
        payload = self.sync(tools, apply=True)
        self.assertEqual([entry["status"] for entry in payload["items"]], ["REUSED", "APPLIED"])
        added = [call for call in tools.calls if call[2:4] == ["item", "add"]]
        self.assertEqual(len(added), 1)
        self.assertTrue(added[0][added[0].index("--title") + 1].startswith("BL-0002 — "))

    def test_every_entry_reports_source_state_and_target(self) -> None:
        self.backlog("## BL-0001 — S\n- state: superseded\n")
        payload = self.sync(self.bound([]), apply=False)
        entry = payload["items"][0]
        self.assertEqual((entry["state"], entry["target"]), ("superseded", "cancelled"))

    def test_a_decision_without_a_declared_state_is_treated_as_open(self) -> None:
        self.backlog("## BL-0001 — Sem estado\n- owner: alguem\n")
        payload = self.sync(self.bound([]), apply=False)
        self.assertEqual(payload["items"][0]["target"], "in_progress")

    def test_nothing_to_mirror_means_nothing_to_do(self) -> None:
        self.backlog("# DECISION-BACKLOG\n\nSem decisoes.\n")
        tools = self.bound([])
        payload = self.sync(tools, apply=True)
        self.assertEqual(payload["items"], [])
        self.assertFalse(payload["changed"])
        self.assertEqual(tools.mutations(), [])

    def test_an_unbound_repository_refuses_before_touching_anything(self) -> None:
        self.backlog("## BL-0001 — O\n- state: open\n")
        tools = StubToolchain({("backlog", "list"): (0, envelope([]))})
        MODULE.resolve_cli = lambda given=None: (CLI, tools)
        payload = self.sync(tools, apply=True)
        self.assertEqual(payload["code"], "BACKLOG-NOT-BOUND")
        self.assertEqual(tools.mutations(), [])

    def test_a_store_answering_outside_the_contract_fails_closed(self) -> None:
        self.backlog("## BL-0001 — O\n- state: open\n")
        tools = StubToolchain({("backlog", "list"): (1, json.dumps({"result": "error", "error": "nope"}))})
        MODULE.resolve_cli = lambda given=None: (CLI, tools)
        with self.assertRaises(MODULE.BacklogUnavailable):
            self.sync(tools, apply=True)
        self.assertEqual(tools.mutations(), [])


WORKSPACE = PLUGIN / "skills/grill-with-docs/scripts/grill_workspace.py"
WORKFLOW_TEMPLATE = PLUGIN / "skills/grill-with-docs/assets/WORKFLOW.template.md"


def load_workspace():
    name = "grill_workspace_backlog_contract"
    spec = importlib.util.spec_from_file_location(name, WORKSPACE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def workspace(*args: object) -> tuple[int, dict]:
    process = subprocess.run(
        [sys.executable, str(WORKSPACE), *(str(arg) for arg in args)],
        text=True, capture_output=True, check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GRILL_SKIP_DEPENDENCIES": "1"},
    )
    lines = process.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError(f"expected one JSON line, got {process.stdout!r} / {process.stderr!r}")
    return process.returncode, json.loads(lines[0])


class SyncGate(unittest.TestCase):
    """T004, T005, T007 — the subcommand gates identity, not artifact hashes."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        git(self.root, "config", "user.email", "tests@example.invalid")
        git(self.root, "config", "user.name", "Contract Tests")
        (self.root / "WORKFLOW.md").write_bytes(WORKFLOW_TEMPLATE.read_bytes())
        git(self.root, "add", "WORKFLOW.md")
        git(self.root, "commit", "-q", "-m", "initial workflow")
        code, payload = workspace("init", self.root, "--type", "feature", "--slug", "alpha",
                                  "--work-id", "work-a", "--skip-backlog")
        self.assertEqual(code, 0, payload)
        self.item = self.root / ".grill" / "work-items" / "work-a"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_decision(self) -> None:
        (self.item / "DECISION-BACKLOG.md").write_text(
            "# DECISION-BACKLOG\n\n## BL-0001 — Uma decisao adiada\n- state: open\n", encoding="utf-8")

    def sync(self):
        return workspace("backlog-sync", self.root, "--work-id", "work-a")

    def test_a_written_decision_no_longer_refuses_the_bundle(self) -> None:
        # The defect: initial_artifacts pins the templates written by init, so
        # recording a decision — the only reason to run this command — used to
        # invalidate its own precondition.
        self.write_decision()
        _, payload = self.sync()
        self.assertNotEqual(payload.get("code"), "BUNDLE-INTEGRITY")

    def test_an_untouched_bundle_is_still_accepted(self) -> None:
        _, payload = self.sync()
        self.assertNotEqual(payload.get("code"), "BUNDLE-INTEGRITY")

    def test_a_tampered_immutable_block_is_still_refused(self) -> None:
        self.write_decision()
        metadata = json.loads((self.item / "WORK-ITEM.json").read_text(encoding="utf-8"))
        metadata["immutable"]["slug"] = "tampered"
        (self.item / "WORK-ITEM.json").write_text(json.dumps(metadata), encoding="utf-8")
        code, payload = self.sync()
        self.assertNotEqual(code, 0)
        self.assertEqual(payload.get("code"), "IMMUTABLE-TAMPERED")

    def test_the_artifact_gate_itself_still_refuses_a_drifted_bundle(self) -> None:
        # Relaxing the gate for this one command must not weaken the gate.
        # Exercised directly because other commands reach their own checks
        # first, which would make an end-to-end assertion test the wrong thing.
        self.write_decision()
        module = load_workspace()
        bundle = module.read_local_bundle(self.root, self.item)
        with self.assertRaises(module.CliFailure) as raised:
            module.validate_bundle_integrity(bundle)
        self.assertEqual(raised.exception.code, "BUNDLE-INTEGRITY")

    def test_the_gate_is_still_wired_into_the_commands_that_need_it(self) -> None:
        source = WORKSPACE.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("validate_bundle_integrity(bundle)"), 3)
        self.assertNotIn("validate_bundle_integrity", source.split("def backlog_sync_command")[1].split("\ndef ")[0])


if __name__ == "__main__":
    unittest.main(verbosity=1, argv=[sys.argv[0], *sys.argv[1:]])
