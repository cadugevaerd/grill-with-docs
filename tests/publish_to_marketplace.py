#!/usr/bin/env python3
"""Point a marketplace index entry at a published release of this plugin.

The plugin is not vendored into the aggregators: each entry carries a
``git-subdir`` source pinned to a tag and a commit of the canonical repository.
Publishing is therefore a small, reviewable edit to one JSON file per
marketplace — no content is copied anywhere.

Deliberately named outside the ``validate_*.py`` glob of ``tests/run_validators.py``:
it needs a checkout of a target repository, which the portability matrix has no
reason to provide. The decision layer below is pure and is covered there instead.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple

CANONICAL_URL = "https://github.com/cadugevaerd/grill-with-docs.git"
CANONICAL_SUBDIR = "plugin"
PLUGIN_NAME = "grill-with-docs"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SOURCE_KIND = "git-subdir"

TARGETS: dict[str, dict[str, str]] = {
    "claude": {"repo": "cadugevaerd/claude-skills", "index": ".claude-plugin/marketplace.json"},
    "codex": {"repo": "cadugevaerd/codex-skills", "index": ".agents/plugins/marketplace.json"},
}

EXIT_OK = 0
EXIT_TARGET_INVALID = 1
EXIT_USAGE = 2


class Release(NamedTuple):
    version: str
    ref: str
    sha: str


class EntryPlan(NamedTuple):
    status: str  # CREATED | UPDATED | UNCHANGED
    entry: dict[str, Any]
    index: dict[str, Any]


class TargetInvalid(RuntimeError):
    """The checkout does not look like the marketplace it claims to be."""


def parse_release(version: str, ref: str, sha: str) -> Release:
    if not SEMVER_RE.match(version or ""):
        raise ValueError(f"versão inválida: {version!r}")
    if ref != f"v{version}":
        raise ValueError(f"ref deve ser v{version}, recebido {ref!r}")
    if not SHA_RE.match((sha or "").lower()):
        raise ValueError(f"sha deve ter 40 hex, recebido {sha!r}")
    return Release(version, ref, sha.lower())


def source_object(release: Release) -> dict[str, str]:
    return {"source": SOURCE_KIND, "url": CANONICAL_URL, "path": CANONICAL_SUBDIR,
            "ref": release.ref, "sha": release.sha}


def new_entry(target: str, release: Release, meta: dict[str, Any]) -> dict[str, Any]:
    """Build an entry for a marketplace that does not know the plugin yet."""
    entry: dict[str, Any] = {"name": PLUGIN_NAME, "source": source_object(release)}
    if meta.get("description"):
        entry["description"] = meta["description"]
    entry["version"] = release.version
    if target == "codex":
        entry["policy"] = {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
        entry["category"] = meta.get("category", "Development")
    else:
        if meta.get("author"):
            entry["author"] = meta["author"]
        entry["category"] = meta.get("category", "development")
    return entry


def plan_entry(index: dict[str, Any], target: str, release: Release, meta: dict[str, Any]) -> EntryPlan:
    """Decide the resulting entry. Only version and source pin ever change."""
    plugins = index.get("plugins")
    if not isinstance(plugins, list):
        raise TargetInvalid("índice sem lista 'plugins'")
    position = next((i for i, p in enumerate(plugins)
                     if isinstance(p, dict) and p.get("name") == PLUGIN_NAME), None)
    result = json.loads(json.dumps(index))  # cópia profunda, preservando ordem
    if position is None:
        entry = new_entry(target, release, meta)
        result["plugins"] = [*plugins, entry]
        return EntryPlan("CREATED", entry, result)

    current = plugins[position]
    source = current.get("source")
    if not isinstance(source, dict) or source.get("source") != SOURCE_KIND:
        # Converter vendorização em referência mudaria o mecanismo de distribuição
        # sem decisão registrada; recusar é mais seguro que adivinhar.
        raise TargetInvalid(f"entrada existente com source inesperado: {source!r}")

    entry = json.loads(json.dumps(current))
    entry["source"] = {**source, **source_object(release)}
    entry["version"] = release.version
    if entry == current:
        return EntryPlan("UNCHANGED", entry, result)
    result["plugins"][position] = entry
    return EntryPlan("UPDATED", entry, result)


def detect_indent(text: str) -> int:
    for line in text.splitlines():
        stripped = line.lstrip(" ")
        if stripped and stripped != line:
            return len(line) - len(stripped)
    return 2


def read_index(checkout: Path, target: str) -> tuple[dict[str, Any], Path, str]:
    path = checkout / TARGETS[target]["index"]
    if not path.is_file():
        raise TargetInvalid(f"índice ausente: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        index = json.loads(text)
    except json.JSONDecodeError as error:
        raise TargetInvalid(f"índice com JSON inválido: {error}") from error
    if not isinstance(index, dict):
        raise TargetInvalid("índice não é um objeto JSON")
    return index, path, text


def object_span(text: str, start: int) -> tuple[int, int]:
    """Span of the JSON object whose opening brace is at or before ``start``.

    Brace matching is string-aware: a brace inside a string literal, or escaped,
    must not move the depth.
    """
    opening = text.rindex("{", 0, start + 1)
    depth, index, in_string, escaped = 0, opening, False, False
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return opening, index + 1
        index += 1
    raise TargetInvalid("objeto JSON não fechado no índice")


def locate(text: str, name: str) -> tuple[int, int]:
    """Span of the plugin entry with this name, anchored on its ``name`` field."""
    matches = list(re.finditer(r'"name"\s*:\s*"' + re.escape(name) + r'"', text))
    if not matches:
        raise TargetInvalid(f"entrada {name!r} não encontrada no texto do índice")
    return object_span(text, matches[-1].start())


def column_of(text: str, start: int) -> str:
    """Leading whitespace of the line on which an object begins."""
    line_start = text.rfind("\n", 0, start) + 1
    prefix = text[line_start:start]
    return prefix if not prefix.strip() else ""


def string_value_span(text: str, key: str) -> tuple[int, int] | None:
    """Span of a string value for ``key`` at the top level of ``text``'s object.

    Depth matters: a regex would happily patch a same-named key nested inside the
    entry — patching `meta.version` while leaving the real one stale, corrupting
    unrelated data in the process.
    """
    depth, index, in_string, escaped = 0, 0, False, False
    pattern = re.compile(r'"' + re.escape(key) + r'"\s*:\s*"')
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
        elif char == '"':
            if depth == 1:
                match = pattern.match(text, index)
                if match:
                    closing = text.index('"', match.end())
                    return match.end(), closing
            in_string = True
        index += 1
    return None


def replace_at(text: str, key: str, value: str) -> str | None:
    span = string_value_span(text, key)
    if span is None:
        return None
    return text[:span[0]] + value + text[span[1]:]


def object_value_span(text: str, key: str) -> tuple[int, int] | None:
    """Span of an object value for ``key`` at the top level of ``text``'s object."""
    depth, index, in_string, escaped = 0, 0, False, False
    pattern = re.compile(r'"' + re.escape(key) + r'"\s*:\s*\{')
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
        elif char == '"':
            if depth == 1:
                match = pattern.match(text, index)
                if match:
                    return object_span(text, match.end() - 1)
            in_string = True
        index += 1
    return None


def retarget(entry_text: str, entry: dict[str, Any]) -> str | None:
    """Rewrite only the three values that a release changes.

    Re-serialising even our own entry would expand hand-written compact arrays and
    turn a three-line release into a diff nobody reads. Returns ``None`` when the
    expected keys are not where they must be, so the caller can fall back.
    """
    result = replace_at(entry_text, "version", entry["version"])
    if result is None:
        return None
    span = object_value_span(result, "source")
    if span is None:
        return None
    inner = result[span[0]:span[1]]
    for key in ("ref", "sha"):
        patched = replace_at(inner, key, entry["source"][key])
        if patched is None:
            return None
        inner = patched
    return result[:span[0]] + inner + result[span[1]:]


def splice(text: str, plan: EntryPlan, previous: dict[str, Any]) -> str:
    """Replace or insert only this plugin's entry, leaving neighbours byte-identical.

    Re-serialising the whole document would normalise hand-compacted neighbouring
    entries, burying a three-line change in a diff nobody can review.
    """
    rendered = json.dumps(plan.entry, ensure_ascii=False, indent=detect_indent(text))

    if plan.status == "UPDATED":
        start, end = locate(text, PLUGIN_NAME)
        patched = retarget(text[start:end], plan.entry)
        if patched is not None:
            return text[:start] + patched + text[end:]
        # Sem as três chaves no texto, reserializar a entrada é o único caminho
        # correto; custa formatação, mas nunca sai de dentro do próprio span.
        return text[:start] + rendered.replace("\n", "\n" + column_of(text, start)) + text[end:]

    # CREATED: ancorar no último plugin existente e inserir depois dele. Buscar o
    # último "}" do arquivo encontraria o fecho de um objeto aninhado, como policy.
    siblings = previous.get("plugins") or []
    if not siblings:
        raise TargetInvalid("índice sem plugins; não há âncora para inserir")
    start, end = locate(text, siblings[-1].get("name", ""))
    pad = column_of(text, start)
    return text[:end] + ",\n" + pad + rendered.replace("\n", "\n" + pad) + text[end:]


def apply_entry(path: Path, plan: EntryPlan, original: str, previous: dict[str, Any]) -> None:
    path.write_text(splice(original, plan, previous), encoding="utf-8")


def canonical_meta(repo_root: Path, target: str) -> dict[str, Any]:
    name = ".codex-plugin" if target == "codex" else ".claude-plugin"
    path = repo_root / "plugin" / name / "plugin.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return manifest if isinstance(manifest, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aponta a entrada de um marketplace para uma release.")
    parser.add_argument("--target", required=True, choices=sorted(TARGETS))
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    arguments = parser.parse_args(argv)

    checkout = Path(arguments.checkout).expanduser()
    if not checkout.is_dir():
        print(f"checkout inexistente: {checkout}", file=sys.stderr)
        return EXIT_USAGE
    try:
        release = parse_release(arguments.version, arguments.ref, arguments.sha)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return EXIT_USAGE

    try:
        index, path, original = read_index(checkout, arguments.target)
        meta = canonical_meta(Path(arguments.repo_root), arguments.target)
        plan = plan_entry(index, arguments.target, release, meta)
        if arguments.apply and plan.status != "UNCHANGED":
            apply_entry(path, plan, original, index)
    except TargetInvalid as error:
        payload = {"target": arguments.target, "verdict": "BLOCKED", "error": str(error)}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
              if arguments.as_json else f"BLOCKED {arguments.target}: {error}")
        return EXIT_TARGET_INVALID

    payload = {
        "target": arguments.target,
        "verdict": "APPLIED" if (arguments.apply and plan.status != "UNCHANGED") else "PREVIEW",
        "changed": plan.status != "UNCHANGED",
        "entry": plan.status,
        "version": release.version,
        "ref": release.ref,
        "sha": release.sha,
        "index": TARGETS[arguments.target]["index"],
    }
    if arguments.as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(f"{payload['verdict']} {arguments.target}: entrada {plan.status}, "
              f"versão {release.version}, ref {release.ref}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
