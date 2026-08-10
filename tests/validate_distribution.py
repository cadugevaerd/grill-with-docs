#!/usr/bin/env python3
"""Validate the standalone public distribution contract."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin"
VERSION = "2.4.1"

def load(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)

def main():
    codex = load(PLUGIN / ".codex-plugin/plugin.json")
    claude = load(PLUGIN / ".claude-plugin/plugin.json")
    codex_market = load(ROOT / ".agents/plugins/marketplace.json")
    claude_market = load(ROOT / ".claude-plugin/marketplace.json")
    assert codex["version"] == claude["version"] == VERSION
    assert codex["homepage"] == codex["repository"] == "https://github.com/cadugevaerd/grill-with-docs"
    assert codex_market["name"] == claude_market["name"] == "grill-with-docs"
    assert codex_market["plugins"][0]["source"] == claude_market["plugins"][0]["source"] == "./plugin"
    assert codex_market["plugins"][0]["version"] == claude_market["plugins"][0]["version"] == VERSION
    assert codex_market["plugins"][0]["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert codex_market["plugins"][0]["category"] == "Development"
    assert claude_market["owner"]["name"] == "Carlos Araujo"
    assert not list(PLUGIN.rglob("tests"))
    for path in (PLUGIN / ".codex-plugin/plugin.json", PLUGIN / ".claude-plugin/plugin.json", PLUGIN / "hooks/hooks.json", PLUGIN / "skills/grill-with-docs/SKILL.md", PLUGIN / "skills/grill-with-docs/scripts/grill_workspace.py", PLUGIN / "skills/grill-with-docs/scripts/audit_decisions.py"):
        assert path.is_file(), path
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "codex plugin marketplace add ." in readme and "codex plugin add grill-with-docs@grill-with-docs" in readme
    assert "claude plugin marketplace add cadugevaerd/grill-with-docs" in readme and "claude plugin install grill-with-docs@grill-with-docs" in readme
    print("distribution: OK")

if __name__ == "__main__":
    main()
