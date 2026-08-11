#!/usr/bin/env python3
"""Executable contract for pointing marketplace entries at a published release.

Runs with no network, no credentials and no marketplace checkout, because it is
collected by ``tests/run_validators.py`` on every supported OS and Python version.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SCRIPT = TESTS / "publish_to_marketplace.py"
SHA = "45f6b988bf8f279756a62cfac22300426108626b"
OTHER_SHA = "c6a9b0708f737dd9f13a3ca98c3b5fa2a00c4cbf"


def load() -> object:
    spec = importlib.util.spec_from_file_location("publish_to_marketplace_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load()
RELEASE = MODULE.parse_release("2.5.0", "v2.5.0", SHA)

# Fixtures reproduzindo a forma real dos dois índices, incluindo uma entrada
# vizinha compactada à mão — é ela que denuncia reformatação indevida.
CLAUDE_INDEX = """{
  "name": "claude-skills",
  "owner": {
    "name": "Carlos Araujo"
  },
  "plugins": [
    {
      "name": "grill-with-docs",
      "description": "texto curado que nao pode ser sobrescrito",
      "source": {
        "source": "git-subdir",
        "url": "https://github.com/cadugevaerd/grill-with-docs.git",
        "path": "plugin",
        "ref": "v2.4.1",
        "sha": "%s"
      },
      "version": "2.4.1",
      "author": {
        "name": "Carlos Araujo"
      },
      "category": "development",
      "tags": ["architecture", "adr"]
    },
    {
      "name": "vizinho-compacto",
      "source": "./plugins/vizinho-compacto",
      "author": {"name": "Carlos Araujo"},
      "tags": ["quality", "security"]
    }
  ]
}
""" % OTHER_SHA

CODEX_INDEX = """{
  "name": "codex-skills",
  "interface": {
    "displayName": "Codex Skills"
  },
  "plugins": [
    {
      "name": "backlog",
      "source": {
        "source": "local",
        "path": "./plugins/backlog"
      },
      "description": "vizinho",
      "version": "2.4.2",
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
"""


class ReleaseParsing(unittest.TestCase):
    def test_valid_release_parses(self) -> None:
        self.assertEqual(MODULE.parse_release("2.5.0", "v2.5.0", SHA.upper()).sha, SHA)

    def test_ref_must_match_the_version(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.parse_release("2.5.0", "v2.4.1", SHA)

    def test_malformed_version_or_sha_raise(self) -> None:
        for version, ref, sha in (("2.5", "v2.5", SHA), ("2.5.0", "v2.5.0", "abc"),
                                  ("", "v", SHA), ("2.5.0", "2.5.0", SHA)):
            with self.assertRaises(ValueError):
                MODULE.parse_release(version, ref, sha)


class PlanEntry(unittest.TestCase):
    def test_existing_entry_is_updated_in_place(self) -> None:
        plan = MODULE.plan_entry(json.loads(CLAUDE_INDEX), "claude", RELEASE, {})
        self.assertEqual(plan.status, "UPDATED")
        self.assertEqual(plan.entry["version"], "2.5.0")
        self.assertEqual(plan.entry["source"]["ref"], "v2.5.0")
        self.assertEqual(plan.entry["source"]["sha"], SHA)

    def test_curated_fields_survive_the_update(self) -> None:
        plan = MODULE.plan_entry(json.loads(CLAUDE_INDEX), "claude", RELEASE, {"description": "OUTRO"})
        self.assertEqual(plan.entry["description"], "texto curado que nao pode ser sobrescrito")
        self.assertEqual(plan.entry["tags"], ["architecture", "adr"])

    def test_absent_entry_is_created_with_the_codex_schema(self) -> None:
        meta = {"description": "descricao canonica", "category": "Development"}
        plan = MODULE.plan_entry(json.loads(CODEX_INDEX), "codex", RELEASE, meta)
        self.assertEqual(plan.status, "CREATED")
        self.assertEqual(plan.entry["source"]["source"], "git-subdir")
        self.assertEqual(set(plan.entry["source"]), {"source", "url", "path", "ref", "sha"})
        self.assertEqual(plan.entry["policy"], {"installation": "AVAILABLE", "authentication": "ON_INSTALL"})
        self.assertEqual(plan.entry["description"], "descricao canonica")

    def test_already_published_release_is_unchanged(self) -> None:
        applied = MODULE.plan_entry(json.loads(CLAUDE_INDEX), "claude", RELEASE, {}).index
        self.assertEqual(MODULE.plan_entry(applied, "claude", RELEASE, {}).status, "UNCHANGED")

    def test_vendored_entry_is_refused_instead_of_converted(self) -> None:
        index = json.loads(CODEX_INDEX)
        index["plugins"].append({"name": "grill-with-docs", "source": {"source": "local", "path": "./x"}})
        with self.assertRaises(MODULE.TargetInvalid):
            MODULE.plan_entry(index, "codex", RELEASE, {})

    def test_index_without_a_plugins_list_is_refused(self) -> None:
        for broken in ({"plugins": {}}, {"plugins": "x"}, {}):
            with self.assertRaises(MODULE.TargetInvalid):
                MODULE.plan_entry(broken, "claude", RELEASE, {})


class Splice(unittest.TestCase):
    """A publicação precisa produzir um diff que um humano consiga revisar."""

    def neighbours(self, text: str) -> dict:
        return {p["name"]: p for p in json.loads(text)["plugins"] if p["name"] != "grill-with-docs"}

    def test_update_touches_only_this_entry(self) -> None:
        plan = MODULE.plan_entry(json.loads(CLAUDE_INDEX), "claude", RELEASE, {})
        result = MODULE.splice(CLAUDE_INDEX, plan, json.loads(CLAUDE_INDEX))
        self.assertEqual(self.neighbours(result), self.neighbours(CLAUDE_INDEX))
        self.assertIn('"author": {"name": "Carlos Araujo"}', result)  # vizinho compacto intacto
        self.assertNotIn(OTHER_SHA, result)
        self.assertIn(SHA, result)

    def test_update_changes_only_three_lines(self) -> None:
        plan = MODULE.plan_entry(json.loads(CLAUDE_INDEX), "claude", RELEASE, {})
        result = MODULE.splice(CLAUDE_INDEX, plan, json.loads(CLAUDE_INDEX))
        differing = [(a, b) for a, b in zip(CLAUDE_INDEX.splitlines(), result.splitlines()) if a != b]
        self.assertEqual(len(differing), 3)

    def test_creation_appends_valid_json_after_the_last_sibling(self) -> None:
        previous = json.loads(CODEX_INDEX)
        plan = MODULE.plan_entry(previous, "codex", RELEASE, {"description": "d", "category": "Development"})
        result = MODULE.splice(CODEX_INDEX, plan, previous)
        parsed = json.loads(result)
        self.assertEqual([p["name"] for p in parsed["plugins"]], ["backlog", "grill-with-docs"])
        self.assertEqual(self.neighbours(result), self.neighbours(CODEX_INDEX))
        self.assertEqual(list(parsed), list(previous))

    def test_creation_does_not_nest_inside_a_sibling_policy_object(self) -> None:
        """Regressão: ancorar no último `}` do arquivo acerta o fecho de `policy`."""
        previous = json.loads(CODEX_INDEX)
        plan = MODULE.plan_entry(previous, "codex", RELEASE, {})
        parsed = json.loads(MODULE.splice(CODEX_INDEX, plan, previous))
        self.assertNotIn("grill-with-docs", json.dumps(parsed["plugins"][0]))

    def test_object_span_ignores_braces_inside_strings(self) -> None:
        text = '[{"name": "a", "d": "chave } falsa"}, {"name": "b"}]'
        start, end = MODULE.locate(text, "a")
        self.assertEqual(json.loads(text[start:end])["d"], "chave } falsa")

    def test_indent_is_detected_from_the_file(self) -> None:
        self.assertEqual(MODULE.detect_indent(CLAUDE_INDEX), 2)
        self.assertEqual(MODULE.detect_indent('{\n    "a": 1\n}'), 4)


class CommandLine(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        index = self.root / MODULE.TARGETS["claude"]["index"]
        index.parent.mkdir(parents=True)
        index.write_text(CLAUDE_INDEX, encoding="utf-8")
        self.index = index

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *extra: str) -> tuple[int, str]:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = MODULE.main(["--target", "claude", "--checkout", str(self.root),
                                "--version", "2.5.0", "--ref", "v2.5.0", "--sha", SHA, *extra])
        return code, stream.getvalue()

    def test_preview_writes_nothing(self) -> None:
        before = self.index.read_text(encoding="utf-8")
        code, output = self.run_cli("--json")
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual((payload["verdict"], payload["entry"]), ("PREVIEW", "UPDATED"))
        self.assertEqual(self.index.read_text(encoding="utf-8"), before)

    def test_apply_writes_and_is_idempotent(self) -> None:
        self.assertEqual(self.run_cli("--apply", "--json")[0], 0)
        after = self.index.read_text(encoding="utf-8")
        code, output = self.run_cli("--apply", "--json")
        self.assertEqual(json.loads(output)["entry"], "UNCHANGED")
        self.assertEqual(self.index.read_text(encoding="utf-8"), after)
        self.assertEqual(code, 0)

    def test_missing_index_exits_one(self) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = MODULE.main(["--target", "codex", "--checkout", str(self.root),
                                "--version", "2.5.0", "--ref", "v2.5.0", "--sha", SHA, "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stream.getvalue())["verdict"], "BLOCKED")

    def test_nonexistent_checkout_exits_two(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            code = MODULE.main(["--target", "claude", "--checkout", str(self.root / "nao-existe"),
                                "--version", "2.5.0", "--ref", "v2.5.0", "--sha", SHA])
        self.assertEqual(code, 2)

    def test_malformed_release_exits_two(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            code = MODULE.main(["--target", "claude", "--checkout", str(self.root),
                                "--version", "2.5", "--ref", "v2.5", "--sha", SHA])
        self.assertEqual(code, 2)

    def test_unknown_target_is_rejected_by_the_parser(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            MODULE.main(["--target", "outro", "--checkout", str(self.root),
                         "--version", "2.5.0", "--ref", "v2.5.0", "--sha", SHA])
        self.assertEqual(raised.exception.code, 2)


class Collection(unittest.TestCase):
    def test_the_publisher_is_not_collected_as_a_validator(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertNotIn(SCRIPT, list(TESTS.glob("validate_*.py")))

    def test_only_declared_targets_exist(self) -> None:
        self.assertEqual(sorted(MODULE.TARGETS), ["claude", "codex"])
        for target in MODULE.TARGETS.values():
            self.assertTrue(target["repo"].startswith("cadugevaerd/"))


if __name__ == "__main__":
    unittest.main(verbosity=1, argv=[sys.argv[0], *sys.argv[1:]])
