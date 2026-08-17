#!/usr/bin/env python3
"""Detect, and optionally delegate the installation of, the external toolchain.

The grill core never downloads bytes. Every install listed in
``assets/dependencies.json`` is a delegation to the tool that already owns the
artifact, so verification here is by resolved version, never by hash.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve()
MANIFEST = HERE.parents[1] / "assets/dependencies.json"
SCHEMA = "grill-dependencies/v1"
KINDS = {"runtime", "binary", "path", "specify-extension"}
PROBE_TIMEOUT = 15
INSTALL_TIMEOUT = 600
VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")
BACKLOG_INSTALLER = "${BACKLOG_INSTALLER}"
SKIP_ENV = "GRILL_SKIP_DEPENDENCIES"


class ManifestError(ValueError):
    """The bundled dependency manifest is not usable."""


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ManifestError("invalid schema")
    entries = manifest.get("dependencies")
    if not isinstance(entries, list) or not entries:
        raise ManifestError("missing dependencies")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ManifestError("invalid entry")
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ManifestError(f"invalid or duplicated id: {identifier!r}")
        seen.add(identifier)
        if entry.get("kind") not in KINDS:
            raise ManifestError(f"invalid kind for {identifier}")
        for command in entry.get("install") or []:
            if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
                raise ManifestError(f"invalid install command for {identifier}")
    return manifest


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def parse_version(text: str) -> tuple[int, ...] | None:
    match = VERSION_RE.search(text or "")
    if not match:
        return None
    return tuple(int(part) for part in match.groups(default="0"))


def meets(found: tuple[int, ...] | None, minimum: str | None) -> bool:
    if not minimum:
        return True
    required = parse_version(minimum)
    return bool(found and required and found >= required)


class Toolchain:
    """Every side effect of this module, in one replaceable object."""

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        self.environ = dict(os.environ if environ is None else environ)

    def which(self, command: str) -> str | None:
        return shutil.which(command)

    def run(self, argv: list[str], *, cwd: Path | None = None, timeout: int = PROBE_TIMEOUT) -> tuple[int, str]:
        try:
            process = subprocess.run(
                argv, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                check=False, timeout=timeout, shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return 1, ""
        return process.returncode, ((process.stdout or "") + (process.stderr or ""))

    def backlog_installer(self) -> str | None:
        """Locate the installer owned by the backlog plugin, never a copy of it."""
        declared = self.environ.get("BACKLOG_PLUGIN_ROOT")
        roots = [Path(declared)] if declared else []
        cache = Path(self.environ.get("HOME", "~")).expanduser() / ".claude/plugins/cache/claude-skills/backlog"
        if cache.is_dir():
            roots.extend(sorted((entry for entry in cache.iterdir() if entry.is_dir()), reverse=True))
        for root in roots:
            candidate = root / "scripts/ensure-backlogctl.js"
            if candidate.is_file():
                return str(candidate)
        return None


def resolve_binary(entry: dict[str, Any], tools: Toolchain) -> str | None:
    declared = entry.get("env")
    if isinstance(declared, str):
        override = tools.environ.get(declared)
        if override and Path(override).is_file():
            return override
    command = entry.get("command")
    found = tools.which(command) if isinstance(command, str) else None
    if found is not None:
        return found
    home = Path(tools.environ.get("HOME", "~")).expanduser()
    for candidate in entry.get("search_paths") or []:
        location = Path(str(candidate).replace("${HOME}", str(home)))
        if location.is_file():
            return str(location)
    return None


def expand(command: list[str], tools: Toolchain) -> list[str] | None:
    resolved: list[str] = []
    for part in command:
        if part == BACKLOG_INSTALLER:
            installer = tools.backlog_installer()
            if installer is None:
                return None
            resolved.append(installer)
        else:
            resolved.append(part)
    return resolved


def remediation(entry: dict[str, Any], tools: Toolchain) -> str | None:
    commands = entry.get("install") or []
    rendered = []
    for command in commands:
        expanded = expand(command, tools)
        rendered.append(" ".join(expanded if expanded else command))
    if not rendered:
        return None
    return " && ".join(rendered)


def installed_extensions(root: Path, specify: str | None, tools: Toolchain) -> set[str]:
    if specify is None:
        return set()
    code, output = tools.run([specify, "extension", "list"], cwd=root)
    if code != 0 or "No extensions installed" in output:
        return set()
    return set(re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", output))


def detect(root: Path, manifest: dict[str, Any], tools: Toolchain) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    specify_path: str | None = None
    extensions: set[str] | None = None
    for entry in manifest["dependencies"]:
        kind = entry["kind"]
        report: dict[str, Any] = {
            "id": entry["id"],
            "kind": kind,
            "required": bool(entry.get("required")),
            "status": "missing",
            "version": None,
            "source": None,
        }
        if kind == "runtime":
            found = sys.version_info[:3]
            report["version"] = ".".join(str(part) for part in found)
            report["source"] = sys.executable
            report["status"] = "present" if meets(found, entry.get("min")) else "outdated"
        elif kind == "binary":
            location = resolve_binary(entry, tools)
            if location is not None:
                report["source"] = location
                _, output = tools.run([location, *(entry.get("version_args") or [])])
                found = parse_version(output)
                report["version"] = ".".join(str(part) for part in found) if found else None
                report["status"] = "present" if meets(found, entry.get("min")) else "outdated"
            if entry["id"] == "specify" and report["status"] == "present":
                specify_path = location
        elif kind == "path":
            target = root / str(entry["path"])
            expected = entry.get("contains")
            if target.exists() and (not expected or expected in read_text(target)):
                report["status"] = "present"
                report["source"] = str(target)
        elif kind == "specify-extension":
            if extensions is None:
                extensions = installed_extensions(root, specify_path, tools)
            if entry["extension"] in extensions:
                report["status"] = "present"
                report["source"] = "specify extension list"
        if report["status"] != "present":
            report["remediation"] = remediation(entry, tools)
            if entry.get("reason"):
                report["reason"] = entry["reason"]
        reports.append(report)
    return reports


def install(root: Path, manifest: dict[str, Any], reports: Iterable[dict[str, Any]], tools: Toolchain) -> list[dict[str, Any]]:
    """Run only the commands declared in the manifest, for entries not present."""
    by_id = {entry["id"]: entry for entry in manifest["dependencies"]}
    pending = [report["id"] for report in reports if report["status"] != "present"]
    results: list[dict[str, Any]] = []
    for identifier in pending:
        entry = by_id[identifier]
        commands = entry.get("install") or []
        if not commands:
            results.append({"id": identifier, "status": "SKIPPED", "reason": "no declared installer"})
            continue
        outcome = {"id": identifier, "status": "INSTALLED", "commands": []}
        for command in commands:
            expanded = expand(command, tools)
            if expanded is None:
                outcome["status"] = "BLOCKED"
                outcome["reason"] = "unresolved installer placeholder"
                break
            code, output = tools.run(expanded, cwd=root, timeout=INSTALL_TIMEOUT)
            outcome["commands"].append({"argv": expanded, "returncode": code, "output": output[-2048:]})
            if code != 0:
                outcome["status"] = "FAILED"
                break
        results.append(outcome)
    return results


PUBLISHED_SKILLS = ("grill-with-docs",)


def skill_search_roots(root: Path, environ: dict[str, str]) -> list[Path]:
    """Where a same-named skill can shadow the plugin's own.

    Project scope first, then the user's, which is the order a host agent
    resolves. The plugin's own cache is deliberately absent: a copy living
    there is the plugin, not a shadow of it.
    """
    home = Path(environ.get("HOME") or environ.get("USERPROFILE") or "~").expanduser()
    return [root / ".claude" / "skills", root / ".agents" / "skills",
            home / ".claude" / "skills", home / ".agents" / "skills"]


def detect_shadowed_skills(root: Path, environ: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Report every published name that also exists outside the plugin.

    Observed defect: a personal skill named after the plugin won the host's
    resolution, and the session command reached a version without the
    protocol's subcommands. Nothing warned; the discovery came from an
    argument making no sense to whoever answered.

    Scope stays on the plugin's own names. It has authority over those and
    none over third-party ones, and sweeping the whole environment for any
    duplicate would raise false alarms.
    """
    environ = environ if environ is not None else dict(os.environ)
    found: list[dict[str, Any]] = []
    for base in skill_search_roots(root, environ):
        for name in PUBLISHED_SKILLS:
            candidate = base / name
            # A broken link still occupies the name, so is_symlink comes first:
            # exists() is False for a dangling one and would hide the shadow.
            if not candidate.is_symlink() and not candidate.exists():
                continue
            entry: dict[str, Any] = {"skill": name, "path": str(candidate),
                                     "kind": "symlink" if candidate.is_symlink() else "directory"}
            if candidate.is_symlink():
                entry["target"] = os.path.realpath(candidate)
                entry["broken"] = not candidate.exists()
            found.append(entry)
    return found


def remove_shadowed_skill(entry: dict[str, Any]) -> dict[str, Any]:
    """Remove one shadow.

    A symlink is unlinked, never followed, so the target survives. A real
    directory, however, is removed **whole** — there is no smaller thing to
    remove in that case. That is destructive and irreversible, which is why the
    caller must ask for it through a flag that says so, and never as a side
    effect of authorising a dependency install.
    """
    path = Path(entry["path"])
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
    except OSError as error:
        return {**entry, "removed": False, "error": type(error).__name__}
    return {**entry, "removed": True}


def preflight(root: Path, *, allow_install: bool = False, tools: Toolchain | None = None,
              manifest: dict[str, Any] | None = None, remove_shadows: bool = False) -> dict[str, Any]:
    tools = tools or Toolchain()
    if tools.environ.get(SKIP_ENV) == "1":
        # Air-gapped and CI runs opt out explicitly; a skip never counts as OK,
        # so --require-dependencies still refuses to proceed on it.
        return {"schema": SCHEMA, "verdict": "SKIPPED", "dependencies": [], "missing_required": []}
    manifest = manifest or load_manifest()
    reports = detect(root, manifest, tools)
    payload: dict[str, Any] = {"schema": SCHEMA, "dependencies": reports}
    if allow_install and any(report["status"] != "present" for report in reports):
        payload["installed"] = install(root, manifest, reports, tools)
        payload["dependencies"] = reports = detect(root, manifest, tools)
    shadows = detect_shadowed_skills(root, tools.environ)
    if shadows:
        # Reported, never blocking: a shadow breaks the session command, but
        # refusing the whole preflight over it would hide the dependency report
        # the operator came for.
        # Removal is deliberately NOT tied to allow_install. That flag
        # authorises delegated installs and the backlog bind; deleting a
        # directory outside the repository is a different act, and hiding it
        # behind a flag that does not name it is the implicit waiver the
        # constitution forbids. Detection always reports; removal is opt-in.
        payload["shadowed_skills"] = [remove_shadowed_skill(entry) for entry in shadows] if remove_shadows else shadows
    missing = [report["id"] for report in reports if report["required"] and report["status"] != "present"]
    payload["missing_required"] = missing
    payload["verdict"] = "MISSING-DEPENDENCY" if missing else "OK"
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--allow-install", action="store_true")
    parser.add_argument("--remove-shadowed-skills", action="store_true", dest="remove_shadows")
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).expanduser().resolve()
    try:
        payload = preflight(root, allow_install=arguments.allow_install, remove_shadows=arguments.remove_shadows)
    except (ManifestError, OSError, json.JSONDecodeError) as error:
        payload = {"schema": SCHEMA, "verdict": "BLOCKED", "error": type(error).__name__, "detail": str(error)}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if payload["verdict"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
