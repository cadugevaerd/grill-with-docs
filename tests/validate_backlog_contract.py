#!/usr/bin/env python3
"""Executable contract for the preview-first bridge to the external backlog."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
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


if __name__ == "__main__":
    unittest.main(verbosity=1, argv=[sys.argv[0], *sys.argv[1:]])
