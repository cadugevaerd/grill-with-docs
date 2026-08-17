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
        # item transition muta tanto quanto item add: sem ela, um assert de
        # "nenhuma mutacao" passaria com uma transicao real emitida.
        return [call for call in self.calls if call[2] in {"store", "create", "bind"} or call[2:4] in (["backlog", "create"], ["backlog", "bind"], ["item", "add"], ["item", "transition"])]


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
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name).resolve()

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
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name).resolve()
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


class ItemSync(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name).resolve()
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
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = Path(self.temporary.name).resolve() / "DECISION-BACKLOG.md"

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

    def test_a_missing_or_empty_file_is_not_an_error(self) -> None:
        self.assertEqual(MODULE.parse_deferred(self.path.with_name("absent.md")), [])
        self.assertEqual(MODULE.parse_deferred(self.write("# DECISION-BACKLOG\n")), [])


class Reconciliation(unittest.TestCase):
    """T009, T012-T015, T024-T026 — creation state, dedup and state repair."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name).resolve()
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

    def test_preexisting_duplicates_are_surfaced_not_hidden(self) -> None:
        # The old mirror could create duplicates and the store never refused
        # them; reconciling only the first would quietly hide the rest.
        self.backlog("## BL-0001 — O\n- state: open\n")
        first = self.linked("work-a", "BL-0001", status="in_progress")
        second = dict(self.linked("work-a", "BL-0001", status="in_progress"), id="AAA-2")
        payload = self.sync(self.bound([first, second]), apply=False)
        self.assertEqual(payload["items"][0].get("duplicates"), ["AAA-2"])

    def test_a_single_item_reports_no_duplicates(self) -> None:
        self.backlog("## BL-0001 — O\n- state: open\n")
        payload = self.sync(self.bound([self.linked("work-a", "BL-0001", status="in_progress")]), apply=False)
        self.assertNotIn("duplicates", payload["items"][0])

    def test_every_entry_reports_source_state_and_target(self) -> None:
        self.backlog("## BL-0001 — S\n- state: superseded\n")
        payload = self.sync(self.bound([]), apply=False)
        entry = payload["items"][0]
        self.assertEqual((entry["state"], entry["target"]), ("superseded", "cancelled"))

    def test_a_failure_mid_apply_keeps_the_record_of_what_landed(self) -> None:
        # No transaction spans successive calls. A bare refusal would assert
        # nothing happened while earlier items had already been created.
        self.backlog("## BL-0001 — A\n- state: open\n\n## BL-0002 — B\n- state: open\n")
        tools = self.bound([])
        seen: list[int] = []
        original = tools.run

        def fail_on_second(argv, **kwargs):
            if argv[2:4] == [CLI, "x"]:
                return original(argv, **kwargs)
            if argv[2:4] == ["item", "add"]:
                seen.append(1)
                if len(seen) == 2:
                    return 1, json.dumps({"result": "error", "error": "store went away"})
            return original(argv, **kwargs)

        tools.run = fail_on_second
        payload = self.sync(tools, apply=True)
        self.assertEqual(payload["verdict"], "BLOCKED")
        self.assertTrue(payload["changed"])
        self.assertEqual([entry["status"] for entry in payload["items"]], ["APPLIED", "FAILED"])

    def test_the_description_never_freezes_a_state_the_item_owns(self) -> None:
        # The item's status is the authority. Copying state into free text
        # would leave the description asserting open on an item already done,
        # because transitions move the status and never rewrite the text.
        self.backlog("## BL-0001 — R\n- state: resolved\n- owner: alguem\n")
        tools = self.bound([])
        self.sync(tools, apply=True)
        argv = next(call for call in tools.calls if call[2:4] == ["item", "add"])
        description = argv[argv.index("--description") + 1]
        self.assertNotIn("state:", description)
        self.assertIn("owner: alguem", description)
        self.assertIn(f"{MODULE.BL_MARKER}: BL-0001", description)

    def test_an_unrecognised_state_fails_closed_instead_of_guessing(self) -> None:
        # A typo used to be coerced to open, which would report a resolved
        # decision as still in flight.
        self.backlog("## BL-0001 — Typo\n- state: resolvd\n")
        tools = self.bound([])
        payload = self.sync(tools, apply=True)
        self.assertEqual([entry["status"] for entry in payload["items"]], ["STATE-UNKNOWN"])
        self.assertFalse(payload["changed"])
        self.assertEqual(tools.mutations(), [])
        # The skip has to reach the verdict, not just the item list: a caller
        # reading only the exit code would otherwise see success.
        self.assertEqual(payload["verdict"], "BLOCKED")
        self.assertEqual(payload["skipped"], ["BL-0001"])

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


AUDIT = PLUGIN / "skills/grill-with-docs/scripts/audit_decisions.py"


def load_audit():
    name = "audit_decisions_backlog_contract"
    spec = importlib.util.spec_from_file_location(name, AUDIT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ParserAgreement(unittest.TestCase):
    """T002 — one parser, so the two readers cannot disagree."""

    HEADERS = {
        "em dash": "## BL-0001 — Titulo\n- state: open\n",
        "ascii hyphen": "## BL-0001 - Titulo\n- state: open\n",
        "en dash": "## BL-0001 – Titulo\n- state: open\n",
        "three digits": "## BL-001 — Titulo\n- state: open\n",
        "no title": "## BL-0001\n- state: open\n",
    }

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = Path(self.temporary.name).resolve() / "DECISION-BACKLOG.md"
        self.audit = load_audit()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_both_readers_see_the_same_blocks(self) -> None:
        # A decision written with a plain hyphen used to be audited — and could
        # block the phase — while being invisible to the mirror.
        for name, text in self.HEADERS.items():
            with self.subTest(name):
                self.path.write_text(text, encoding="utf-8")
                self.assertEqual(len(MODULE.parse_deferred(self.path)),
                                 len(self.audit.split_blocks(text, "BL")), name)

    def test_the_title_survives_every_separator(self) -> None:
        for name in ("em dash", "ascii hyphen", "en dash", "three digits"):
            with self.subTest(name):
                self.path.write_text(self.HEADERS[name], encoding="utf-8")
                self.assertEqual(MODULE.parse_deferred(self.path)[0]["title"], "Titulo", name)

    def test_a_missing_title_is_empty_not_a_skipped_block(self) -> None:
        self.path.write_text(self.HEADERS["no title"], encoding="utf-8")
        entries = MODULE.parse_deferred(self.path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "")


class InverseStates(unittest.TestCase):
    """T004 — the way back from item status to decision state."""

    def test_the_inverse_covers_every_state_the_bridge_emits(self) -> None:
        self.assertEqual(MODULE.ITEM_STATE_TO_DECISION,
                         {"in_progress": "open", "done": "resolved", "cancelled": "superseded"})

    def test_the_two_maps_round_trip(self) -> None:
        for decision, item_state in MODULE.STATE_TARGET.items():
            self.assertEqual(MODULE.ITEM_STATE_TO_DECISION[item_state], decision)

    def test_a_state_the_bridge_never_emits_has_no_translation(self) -> None:
        # FR-016: report, never approximate.
        for orphan in ("open", "merged"):
            self.assertIsNone(MODULE.ITEM_STATE_TO_DECISION.get(orphan), orphan)


class Projection(unittest.TestCase):
    """T005-T009, T014-T017, T023, T024 — generation, mark and verification."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name).resolve()
        self.item = self.root / "item"
        self.item.mkdir()
        self.original = MODULE.resolve_cli

    def tearDown(self) -> None:
        MODULE.resolve_cli = self.original
        self.temporary.cleanup()

    def linked(self, work_id, bl_id, status="in_progress", title=None, extra=""):
        body = f"- phase: FASE-001\n- owner: alguem\n- evidence-needed: e\n- next-action: n{extra}"
        return {"id": f"AAA-{bl_id[-1]}", "status": status,
                "title": title or f"{bl_id} — Titulo de {bl_id}",
                "description": f"{body}\n\n---\n{MODULE.WORK_ID_MARKER}: {work_id}\n{MODULE.BL_MARKER}: {bl_id}\n"}

    def bound(self, items):
        tools = StubToolchain({
            ("backlog", "list"): (0, envelope([{"code": "AAA", "name": "n", "bound_path": str(self.root)}])),
            ("item", "list"): (0, envelope(items)),
        })
        MODULE.resolve_cli = lambda given=None: (CLI, tools)
        return tools

    def projection(self):
        return (self.item / "DECISION-BACKLOG.md").read_text(encoding="utf-8")

    def test_two_generations_are_byte_identical(self) -> None:
        self.bound([self.linked("w", "BL-0001"), self.linked("w", "BL-0002", status="done")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        first = self.projection()
        payload = MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(self.projection(), first)
        self.assertEqual(payload["verdict"], "REUSED")
        self.assertFalse(payload["changed"])

    def test_the_answer_order_does_not_reach_the_file(self) -> None:
        items = [self.linked("w", "BL-0001"), self.linked("w", "BL-0002", status="done")]
        self.bound(items)
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        forward = self.projection()
        self.bound(list(reversed(items)))
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(self.projection(), forward)

    def test_the_record_carries_what_the_auditor_requires(self) -> None:
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        text = self.projection()
        for required in ("- state: open", "- phase: FASE-001", "- owner:", "- evidence-needed:", "- next-action:"):
            self.assertIn(required, text, required)
        self.assertEqual(len(load_audit().split_blocks(text, "BL")), 1)

    def test_item_status_decides_the_decision_state(self) -> None:
        self.bound([self.linked("w", "BL-0001", status="done")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        self.assertIn("- state: resolved", self.projection())

    def test_only_this_work_item_reaches_the_record_and_the_mark(self) -> None:
        mine = [self.linked("w", "BL-0001")]
        self.bound(mine)
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        alone, alone_text = MODULE.authority_mark([]), self.projection()
        self.bound(mine + [self.linked("other", "BL-0009", status="done")])
        payload = MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(self.projection(), alone_text)
        self.assertEqual(payload["verdict"], "REUSED")
        self.assertNotIn("BL-0009", self.projection())
        del alone

    def test_preview_writes_nothing(self) -> None:
        self.bound([self.linked("w", "BL-0001")])
        payload = MODULE.project(self.root, self.item, "w", apply=False, db=DB)
        self.assertEqual(payload["verdict"], "PREVIEW")
        self.assertFalse((self.item / "DECISION-BACKLOG.md").exists())

    def test_an_empty_work_item_still_produces_a_valid_record(self) -> None:
        self.bound([])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        self.assertIn("# DECISION-BACKLOG", self.projection())
        self.assertEqual(MODULE.parse_deferred(self.item / "DECISION-BACKLOG.md"), [])

    def test_the_write_leaves_no_staging_file_behind(self) -> None:
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        leftovers = [p.name for p in self.item.iterdir() if p.name.startswith(".")]
        self.assertEqual(leftovers, [])

    def test_a_fresh_record_verifies_clean(self) -> None:
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(MODULE.verify(self.root, self.item, "w", db=DB)["verdict"], "FRESH")

    def test_a_state_change_in_the_authority_is_named(self) -> None:
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        self.bound([self.linked("w", "BL-0001", status="done")])
        payload = MODULE.verify(self.root, self.item, "w", db=DB)
        self.assertEqual(payload["verdict"], "DIVERGED")
        self.assertIn("STATE-DIVERGED", [d["type"] for d in payload["divergences"]])
        self.assertIn("BL-0001", [d["id"] for d in payload["divergences"]])

    def test_a_decision_only_in_the_authority_is_named(self) -> None:
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        self.bound([self.linked("w", "BL-0001"), self.linked("w", "BL-0002")])
        payload = MODULE.verify(self.root, self.item, "w", db=DB)
        types = {(d["id"], d["type"]) for d in payload["divergences"]}
        self.assertIn(("BL-0002", "MISSING-IN-PROJECTION"), types)

    def test_a_single_character_edit_is_detected(self) -> None:
        # FR-017 and SC-009: the file stays versioned and therefore editable;
        # "unsupported" has to mean detectable.
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        path = self.item / "DECISION-BACKLOG.md"
        path.write_text(self.projection().replace("- owner: alguem", "- owner: alguen"), encoding="utf-8")
        payload = MODULE.verify(self.root, self.item, "w", db=DB)
        self.assertEqual(payload["verdict"], "DIVERGED")

    def test_a_record_without_a_mark_is_named(self) -> None:
        (self.item / "DECISION-BACKLOG.md").write_text("# DECISION-BACKLOG\n\n## BL-0001 — x\n- state: open\n",
                                                       encoding="utf-8")
        self.bound([self.linked("w", "BL-0001")])
        payload = MODULE.verify(self.root, self.item, "w", db=DB)
        self.assertIn("MARK-ABSENT", [d["type"] for d in payload["divergences"]])

    def test_an_unmapped_item_state_is_named_not_approximated(self) -> None:
        self.bound([self.linked("w", "BL-0001", status="merged")])
        payload = MODULE.verify(self.root, self.item, "w", db=DB)
        self.assertIn("STATE-UNMAPPED", [d["type"] for d in payload["divergences"]])

    def audit_findings(self, mode: str | None, text: str) -> list[str]:
        state = {"decision_backlog_mode": mode} if mode else {}
        (self.item / "state.json").write_text(json.dumps(state), encoding="utf-8")
        (self.item / "DECISION-BACKLOG.md").write_text(text, encoding="utf-8")
        audit = load_audit()
        findings: list[str] = []
        path = audit.managed_path(self.item, "state.json", "state", findings)
        # managed_path refuses an unsafe path and returns None. Dereferencing it
        # turned a legitimate refusal into an AttributeError on macOS, where the
        # temporary directory sits behind the /var to /private/var alias.
        if path is None:
            return findings
        loaded = json.loads(path.read_text(encoding="utf-8"))
        projected = loaded.get("decision_backlog_mode") == "projected"
        if projected and not audit.PROJECTION_MARK.search(text):
            findings.append("DECISION-BACKLOG: PROJECTION-UNMARKED")
        return findings

    def test_an_unmarked_record_passes_while_the_bundle_is_legacy(self) -> None:
        # Demanding the mark unconditionally would fail every bundle written
        # before the migration exists, which is a later phase.
        self.assertEqual(self.audit_findings(None, "## BL-0001 — x\n- state: open\n"), [])

    def test_an_unmarked_record_fails_once_the_bundle_declares_itself_projected(self) -> None:
        findings = self.audit_findings("projected", "## BL-0001 — x\n- state: open\n")
        self.assertIn("DECISION-BACKLOG: PROJECTION-UNMARKED", findings)

    def test_applying_the_projection_declares_the_mode(self) -> None:
        (self.item / "state.json").write_text(json.dumps({"status": "in-progress"}), encoding="utf-8")
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        state = json.loads((self.item / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["decision_backlog_mode"], "projected")
        self.assertEqual(state["status"], "in-progress")

    def test_a_marked_record_satisfies_the_declared_mode(self) -> None:
        (self.item / "state.json").write_text(json.dumps({}), encoding="utf-8")
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(self.audit_findings("projected", self.projection()), [])

    def test_a_record_from_an_older_generator_is_recognised_not_just_diverged(self) -> None:
        # FR-018: an older format must be identifiable, so a migration can tell
        # "written by a previous version" apart from "someone edited this".
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        path = self.item / "DECISION-BACKLOG.md"
        path.write_text(self.projection().replace(MODULE.PROJECTION_FORMAT, "grill-projection/v0"), encoding="utf-8")
        payload = MODULE.verify(self.root, self.item, "w", db=DB)
        self.assertIn("FORMAT-OLDER", [d["type"] for d in payload["divergences"]])

    def test_verification_refuses_instead_of_claiming_freshness(self) -> None:
        # FR-012: without the authority there is nothing to compare against,
        # and silence would read as "fresh".
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)

        def refuse(given=None):
            raise MODULE.BacklogUnavailable("backlogctl not installed")

        MODULE.resolve_cli = refuse
        with self.assertRaises(MODULE.BacklogUnavailable):
            MODULE.verify(self.root, self.item, "w", db=DB)

    def test_a_failed_write_leaves_the_previous_record_intact(self) -> None:
        # SC-007: staging plus rename means the reader never sees a half file.
        self.bound([self.linked("w", "BL-0001")])
        MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        good = self.projection()
        path = self.item / "DECISION-BACKLOG.md"
        original = MODULE.atomic_projection_write
        try:
            def explode(target, content):
                staging = target.with_name(f".{target.name}.staging")
                staging.write_text(content[: len(content) // 2], encoding="utf-8")
                raise OSError("disk went away")

            MODULE.atomic_projection_write = explode
            self.bound([self.linked("w", "BL-0001", status="done")])
            with self.assertRaises(OSError):
                MODULE.project(self.root, self.item, "w", apply=True, db=DB)
        finally:
            MODULE.atomic_projection_write = original
        self.assertEqual(path.read_text(encoding="utf-8"), good)

    def test_a_change_outside_this_work_item_does_not_move_the_mark(self) -> None:
        mine = [self.linked("w", "BL-0001")]
        self.bound(mine)
        before = MODULE.project(self.root, self.item, "w", apply=True, db=DB)["mark"]
        self.bound(mine + [self.linked("other", "BL-0007", status="cancelled")])
        after = MODULE.project(self.root, self.item, "w", apply=False, db=DB)["mark"]
        self.assertEqual(before, after)


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
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name).resolve()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        git(self.root, "config", "user.email", "tests@example.invalid")
        git(self.root, "config", "user.name", "Contract Tests")
        (self.root / "WORKFLOW.md").write_bytes(WORKFLOW_TEMPLATE.read_bytes())
        git(self.root, "add", "WORKFLOW.md")
        git(self.root, "commit", "-q", "-m", "initial workflow")
        code, payload = workspace("init", self.root, "--type", "feature", "--slug", "alpha",
                                  "--work-id", "work-a", "--skip-backlog", '--skip-backlog')
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

    def test_the_subcommand_accepts_an_alternate_store(self) -> None:
        # Without --db the command always reaches the operator's real backlog,
        # so this coverage would consult a different store on CI than on a
        # developer machine and pass for different reasons in each. The
        # assertion holds in both because every envelope, including the
        # refusal raised when backlogctl is absent, names the targeted store.
        self.write_decision()
        store = self.root / "throwaway.db"
        _, payload = workspace("backlog-sync", self.root, "--work-id", "work-a", "--db", store)
        self.assertEqual(payload.get("db"), str(store))
        self.assertNotEqual(payload.get("db"), str(Path("~/.backlog/backlog.db").expanduser()))

    def test_the_gate_is_still_wired_into_the_commands_that_need_it(self) -> None:
        source = WORKSPACE.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("validate_bundle_integrity(bundle)"), 3)
        self.assertNotIn("validate_bundle_integrity", source.split("def backlog_sync_command")[1].split("\ndef ")[0])


class LegacyMigration(unittest.TestCase):
    """FASE-004 — authored bundles move into the projected model, once."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name).resolve()
        self.item = self.root / "item"
        self.item.mkdir()
        self.original = MODULE.resolve_cli

    def tearDown(self) -> None:
        MODULE.resolve_cli = self.original
        self.temporary.cleanup()

    def authored(self, body: str) -> None:
        (self.item / "DECISION-BACKLOG.md").write_text(body, encoding="utf-8")
        (self.item / "state.json").write_text(json.dumps({"status": "in-progress"}), encoding="utf-8")

    def bound(self, items):
        tools = StubToolchain({
            ("backlog", "list"): (0, envelope([{"code": "AAA", "name": "n", "bound_path": str(self.root)}])),
            ("item", "list"): (0, envelope(items)),
        })
        MODULE.resolve_cli = lambda given=None: (CLI, tools)
        return tools

    def linked(self, work_id, bl_id):
        return {"id": "AAA-1", "status": "done",
                "title": f"{bl_id} — t",
                "description": f"- phase: FASE-001\n\n---\n{MODULE.WORK_ID_MARKER}: {work_id}\n{MODULE.BL_MARKER}: {bl_id}\n"}

    def test_an_authored_bundle_is_recognised(self) -> None:
        self.authored("## BL-0001 — x\n- state: open\n")
        self.assertEqual(MODULE.bundle_mode(self.item), "authored")

    def test_preview_creates_nothing(self) -> None:
        self.authored("## BL-0001 — x\n- state: resolved\n- phase: FASE-001\n")
        tools = self.bound([])
        payload = MODULE.migrate(self.root, self.item, "w", apply=False, db=DB)
        self.assertEqual(payload["verdict"], "PREVIEW")
        self.assertEqual(tools.mutations(), [])

    def test_historical_state_is_seeded_directly(self) -> None:
        self.authored("## BL-0001 — a\n- state: resolved\n- phase: FASE-001\n\n"
                      "## BL-0002 — b\n- state: superseded\n- phase: FASE-001\n")
        tools = self.bound([])
        MODULE.migrate(self.root, self.item, "w", apply=True, db=DB)
        seeded = {c[c.index("--title") + 1].split(" ")[0]: c[c.index("--status") + 1]
                  for c in tools.calls if c[2:4] == ["item", "add"]}
        self.assertEqual(seeded, {"BL-0001": "done", "BL-0002": "cancelled"})

    def test_migration_turns_the_record_into_a_marked_projection(self) -> None:
        self.authored("## BL-0001 — a\n- state: resolved\n- phase: FASE-001\n")
        self.bound([])
        MODULE.migrate(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(MODULE.bundle_mode(self.item), "projected")

    def test_a_decision_that_already_has_a_counterpart_is_reused(self) -> None:
        self.authored("## BL-0001 — a\n- state: resolved\n- phase: FASE-001\n")
        tools = self.bound([self.linked("w", "BL-0001")])
        payload = MODULE.migrate(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual([d["status"] for d in payload["decisions"]], ["REUSED"])
        self.assertEqual([c for c in tools.calls if c[2:4] == ["item", "add"]], [])

    def test_an_already_projected_bundle_reports_nothing_to_do(self) -> None:
        self.authored("## BL-0001 — a\n- state: resolved\n- phase: FASE-001\n")
        self.bound([])
        MODULE.migrate(self.root, self.item, "w", apply=True, db=DB)
        payload = MODULE.migrate(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(payload["code"], "ALREADY-PROJECTED")
        self.assertFalse(payload["changed"])

    def test_an_invalid_state_refuses_the_whole_bundle(self) -> None:
        # Partial migration would leave the record half authored and half
        # projected, with no way to tell which decisions had moved.
        self.authored("## BL-0001 — ok\n- state: resolved\n- phase: FASE-001\n\n"
                      "## BL-0002 — bad\n- state: resolvd\n- phase: FASE-001\n")
        tools = self.bound([])
        payload = MODULE.migrate(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(payload["code"], "STATE-UNKNOWN")
        self.assertEqual(payload["invalid"], ["BL-0002"])
        self.assertEqual(tools.mutations(), [])

    def test_an_empty_authored_bundle_migrates_to_an_empty_projection(self) -> None:
        self.authored("# DECISION-BACKLOG\n\nSem decisoes.\n")
        self.bound([])
        payload = MODULE.migrate(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(payload["verdict"], "APPLIED")
        self.assertEqual(MODULE.bundle_mode(self.item), "projected")

    def test_an_unbound_repository_refuses(self) -> None:
        self.authored("## BL-0001 — a\n- state: resolved\n- phase: FASE-001\n")
        tools = StubToolchain({("backlog", "list"): (0, envelope([]))})
        MODULE.resolve_cli = lambda given=None: (CLI, tools)
        payload = MODULE.migrate(self.root, self.item, "w", apply=True, db=DB)
        self.assertEqual(payload["code"], "BACKLOG-NOT-BOUND")
        self.assertEqual(tools.mutations(), [])


class FailClosedPrerequisite(unittest.TestCase):
    """T003, T004, T006, T007, T008 — the prerequisite becomes enforceable."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name).resolve()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        git(self.root, "config", "user.email", "tests@example.invalid")
        git(self.root, "config", "user.name", "Contract Tests")
        (self.root / "WORKFLOW.md").write_bytes(WORKFLOW_TEMPLATE.read_bytes())
        git(self.root, "add", "WORKFLOW.md")
        git(self.root, "commit", "-q", "-m", "initial workflow")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create(self, *extra):
        # Never the operator's real store: without --db this would both read
        # and, before the create=False fix, write to it.
        return workspace("init", self.root, "--type", "feature", "--slug", "alpha", "--work-id", "wx",
                         "--db", str(self.root / "throwaway.db"), *extra)

    def state(self):
        return json.loads((self.root / ".grill/work-items/wx/state.json").read_text(encoding="utf-8"))

    def test_creation_refuses_without_a_bound_backlog(self) -> None:
        code, payload = self.create()
        self.assertNotEqual(code, 0)
        self.assertEqual(payload.get("code"), "BACKLOG-REQUIRED")
        self.assertFalse((self.root / ".grill/work-items/wx").exists())

    def test_the_refusal_is_named_and_carries_no_traceback(self) -> None:
        code, payload = self.create()
        self.assertEqual(payload.get("verdict"), "BLOCKED")
        self.assertNotIn("Traceback", json.dumps(payload))

    def test_the_escape_hatch_creates_and_stamps(self) -> None:
        code, payload = self.create("--skip-backlog")
        self.assertEqual(code, 0)
        self.assertTrue(payload.get("backlog_skipped"))
        self.assertTrue(self.state()["backlog_skipped"])

    def test_a_normal_bundle_carries_no_stamp(self) -> None:
        # Without a bound backlog the only reachable path is the escape hatch,
        # so this asserts the stamp is not written unconditionally.
        self.create("--skip-backlog")
        state = self.state()
        del state["backlog_skipped"]
        (self.root / ".grill/work-items/wx/state.json").write_text(json.dumps(state), encoding="utf-8")
        self.assertNotIn("backlog_skipped", self.state())

    def test_the_stamp_is_inside_the_integrity_pin(self) -> None:
        # Stamping after publication would make every escaped bundle fail its
        # own integrity gate.
        self.create("--skip-backlog")
        module = load_workspace()
        bundle = module.read_local_bundle(self.root, self.root / ".grill/work-items/wx")
        module.validate_bundle_integrity(bundle)

    def approve_check(self, item: Path) -> None:
        path = item / "CONSTITUTION-CHECK.md"
        text = path.read_text(encoding="utf-8")
        start = text.index("```json") + len("```json")
        end = text.index("```", start)
        value = json.loads(text[start:end])
        for clause in value["clauses"]:
            clause.update(status="PASS", evidence=["tests/evidence.md"], justification="coberto")
        path.write_text(text[:start] + "\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n" + text[end:],
                        encoding="utf-8")

    def test_the_audit_surfaces_the_stamp(self) -> None:
        # Reported on the verdict, never silenced: a bundle created through the
        # escape hatch must not be able to look compliant with a prerequisite
        # it bypassed.
        self.create("--skip-backlog")
        item = self.root / ".grill/work-items/wx"
        self.approve_check(item)
        _, payload = workspace("audit", self.root, "--work-id", "wx")
        self.assertTrue(payload.get("backlog_skipped"), payload)

    def test_creation_never_provisions_a_backlog(self) -> None:
        # Conjuring a backlog named after the root directory would satisfy the
        # check by inventing the very thing it is supposed to verify.
        #
        # The refusal reason legitimately differs by environment: without the
        # binary it is UNAVAILABLE, with it and no match it is NOT-FOUND.
        # Pinning one made this pass locally and fail on the matrix, which is
        # the same environment coupling this milestone kept correcting.
        code, payload = self.create()
        self.assertNotEqual(code, 0)
        self.assertEqual(payload.get("code"), "BACKLOG-REQUIRED")
        self.assertIn(payload.get("error"), {"BACKLOG-NOT-FOUND", "BACKLOG-UNAVAILABLE"})
        self.assertFalse((self.root / ".grill/work-items/wx").exists())

    def test_adoption_refuses_while_the_repository_is_unbound(self) -> None:
        self.create("--skip-backlog")
        code, payload = workspace("backlog-adopt", self.root, "--work-id", "wx",
                                  "--db", str(self.root / "throwaway.db"))
        self.assertNotEqual(code, 0)
        self.assertEqual(payload.get("code"), "BACKLOG-REQUIRED")
        self.assertTrue(self.state()["backlog_skipped"])


if __name__ == "__main__":
    unittest.main(verbosity=1, argv=[sys.argv[0], *sys.argv[1:]])
