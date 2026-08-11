#!/usr/bin/env python3
"""Refuse a pull request that changes the distributed bundle without a version bump.

Deliberately named outside the ``validate_*.py`` glob of ``tests/run_validators.py``:
the decision needs a pull request base, which the portability matrix does not have,
and a silent no-op there would hide the absence of the check behind a success.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Iterable, NamedTuple

MANIFEST = "plugin/.claude-plugin/plugin.json"
BUNDLE_PREFIX = "plugin/"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
EXIT_CODES = {
    "NO-PLUGIN-CHANGE": 0,
    "BUMPED": 0,
    "MISSING-BUMP": 1,
    "VERSION-REGRESSION": 1,
    "VERSION-UNREADABLE": 2,
}


class Verdict(NamedTuple):
    verdict: str  # PASS | FAIL
    code: str
    base_version: str | None
    head_version: str | None
    message: str


class GitError(RuntimeError):
    """A git invocation this check depends on did not succeed."""


# --- pure decision layer: no git, no I/O -------------------------------------


def parse_version(text: str) -> tuple[int, int, int]:
    if not isinstance(text, str) or not VERSION_RE.match(text):
        raise ValueError(f"versão inválida: {text!r}")
    major, minor, patch = (int(part) for part in text.split("."))
    return major, minor, patch


def touches_plugin(paths: Iterable[str]) -> bool:
    """Addition, modification and deletion all reach here as a path in the diff."""
    return any(path.startswith(BUNDLE_PREFIX) for path in paths)


def shown(version: str | None) -> str:
    return version if isinstance(version, str) and version else "ausente"


def decide(paths: Iterable[str], base_version: str | None, head_version: str | None) -> Verdict:
    if not touches_plugin(paths):
        return Verdict(
            "PASS", "NO-PLUGIN-CHANGE", base_version, head_version,
            f"Nenhuma mudança em {BUNDLE_PREFIX}; bump de versão não é exigido.",
        )
    versions = f"Versão na base de merge: {shown(base_version)}; versão no HEAD: {shown(head_version)}."
    try:
        base = parse_version(base_version)
        head = parse_version(head_version)
    except ValueError:
        return Verdict(
            "FAIL", "VERSION-UNREADABLE", base_version, head_version,
            f"{versions} Não foi possível comparar: a versão em {MANIFEST} precisa casar X.Y.Z "
            f"dos dois lados, e a versão precisa aumentar.",
        )
    if head > base:
        return Verdict(
            "PASS", "BUMPED", base_version, head_version,
            f"{BUNDLE_PREFIX} mudou e a versão aumentou de {base_version} para {head_version}.",
        )
    if head < base:
        return Verdict(
            "FAIL", "VERSION-REGRESSION", base_version, head_version,
            f"{BUNDLE_PREFIX} mudou e a versão regrediu. {versions} "
            f"A versão declarada em {MANIFEST} precisa aumentar.",
        )
    return Verdict(
        "FAIL", "MISSING-BUMP", base_version, head_version,
        f"{BUNDLE_PREFIX} mudou sem bump. {versions} "
        f"A versão declarada em {MANIFEST} precisa aumentar.",
    )


def exit_code(result: Verdict) -> int:
    return EXIT_CODES[result.code]


# --- thin git layer ----------------------------------------------------------


def git(argv: list[str]) -> str:
    try:
        process = subprocess.run(["git", *argv], capture_output=True, text=True, check=False)
    except OSError as error:
        raise GitError(f"git {' '.join(argv)}: {error}") from error
    if process.returncode != 0:
        raise GitError(f"git {' '.join(argv)}: {(process.stderr or '').strip()}")
    return process.stdout


def changed_paths(base_ref: str, head_ref: str) -> list[str]:
    """Three dots: the diff is against the merge base, not against the tip of base."""
    output = git(["diff", "--name-only", f"{base_ref}...{head_ref}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def read_version(rev: str) -> str | None:
    """None whenever the declared version cannot be read — never a substitute value."""
    try:
        blob = git(["show", f"{rev}:{MANIFEST}"])
    except GitError:
        return None
    try:
        manifest = json.loads(blob)
    except json.JSONDecodeError:
        return None
    version = manifest.get("version") if isinstance(manifest, dict) else None
    return version if isinstance(version, str) else None


def emit(result: Verdict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result._asdict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(f"{result.verdict} {result.code}: {result.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exige bump de versão quando a pull request altera plugin/.")
    parser.add_argument("--base-ref", required=True, help="base de merge da pull request")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--json", action="store_true", dest="as_json")
    arguments = parser.parse_args(argv)  # argparse já sai com 2 em uso incorreto
    try:
        paths = changed_paths(arguments.base_ref, arguments.head_ref)
    except GitError as error:
        # Sem changeset não há decisão possível: ausência de informação é reprovação.
        result = Verdict(
            "FAIL", "VERSION-UNREADABLE", None, None,
            f"Não foi possível comparar {arguments.base_ref}...{arguments.head_ref} ({error}). "
            f"A versão declarada em {MANIFEST} precisa aumentar quando {BUNDLE_PREFIX} muda.",
        )
    else:
        result = decide(paths, read_version(arguments.base_ref), read_version(arguments.head_ref))
    emit(result, arguments.as_json)
    return exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
