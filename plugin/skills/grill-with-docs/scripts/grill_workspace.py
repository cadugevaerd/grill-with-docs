#!/usr/bin/env python3
"""Deterministic isolated work-item lifecycle for grill-with-docs v2 (stdlib only)."""
from __future__ import annotations

import argparse
import copy
import contextlib
import errno
import functools
import hashlib
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import date, datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, NoReturn

EXIT_OK = 0
EXIT_NO_GO = 1
EXIT_BLOCKED = 2
EXIT_CONSTITUTION = 3
KINDS = {"feature", "fix", "hotfix"}
WORK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,100}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
ADR_RE = re.compile(r"\bADR-\d{4}\b")
DQ_RE = re.compile(r"\bDQ-\d{4}\b")
BL_RE = re.compile(r"\bBL-\d{4}\b")
PHASE_RE = re.compile(r"\bFASE-\d{3}\b")
ROUND_RE = re.compile(r"\bR-\d{4}\b")
ASSETS = Path(__file__).resolve().parents[1] / "assets"
CONSTITUTION_PATH = ".specify/memory/constitution.md"
ROOT_FILES = (
    "CONTEXT.md",
    "DECISION-BACKLOG.md",
    "DECISION-FRONTIER.md",
    "ROADMAP.md",
    "ROUND-LOG.jsonl",
    "state.json",
    "PLAN-CONTEXT.md",
    "CONSTITUTION-CHECK.md",
    "AUDIT.md",
    "DELIVERY-MAP.md",
)
LEGACY_FILES = tuple(name for name in ROOT_FILES if name != "CONSTITUTION-CHECK.md")
MANAGED_GLOBAL = {".grill/global/ROADMAP.md", ".grill/global/AUDIT.md"}
CHECK_START = "<!-- grill-constitution-check:start -->"
CHECK_END = "<!-- grill-constitution-check:end -->"
_SIBLINGS: dict[str, Any] = {}
_MISSING = object()


def sibling(name: str) -> Any:
    """Load a sibling script by path, so the import survives any module loader."""
    if name not in _SIBLINGS:
        path = Path(__file__).resolve().with_name(f"{name}.py")
        spec = importlib.util.spec_from_file_location(f"grill_sibling_{name}", path)
        if spec is None or spec.loader is None:
            raise ImportError(name)
        module = importlib.util.module_from_spec(spec)
        # dataclass resolution looks the module up in sys.modules while the body runs.
        sys.modules[spec.name] = module
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                spec.loader.exec_module(module)
        except BaseException as exc:
            sys.modules.pop(spec.name, None)
            raise ImportError(f"unable to load sibling {name}") from exc
        _SIBLINGS[name] = module
    return _SIBLINGS[name]


_GRILL_CORE: dict[str, Any] = {}


def grill_core_module(name: str) -> Any:
    """Load a ``grill_core/<name>.py`` module by path, same mechanism as ``sibling()``.

    The v3 library (work_item_v3.py, workflow_v3.py and its other modules)
    lives one directory deeper than the flat scripts/ siblings ``sibling()``
    targets, so ``.with_name()`` cannot reach it (it rejects a name containing
    a path separator). This is peça E's own loader (LD-004): it is the only
    piece authorised to wire grill_core into the public CLI, so the cache is
    kept separate from ``_SIBLINGS`` rather than generalising that loader.
    Only ``work_item_v3`` is actually loaded this round -- see gaps_deferred.
    """
    # Gauntlet's standalone loader owns the Store ContextVar. All CLI paths
    # must share it, including activity/checkpoint and direct filesystem effects.
    if name == "store":
        return grill_core_module("gauntlet_runs").store
    if name not in _GRILL_CORE:
        path = Path(__file__).resolve().with_name("grill_core") / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"grill_core_{name}", path)
        if spec is None or spec.loader is None:
            raise ImportError(name)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            # The public CLI owns stdout's one-JSON contract.  A plugin core
            # must not be able to prepend import-time diagnostic noise before
            # this boundary renders its structured failure.
            with contextlib.redirect_stdout(io.StringIO()):
                spec.loader.exec_module(module)
        except BaseException as exc:
            # A grill_core module is an optional capability behind this public
            # boundary.  Its arbitrary import-time failure must retain the
            # CLI's one-JSON/EXIT_BLOCKED contract instead of escaping as an
            # interpreter traceback (where exit 1 misleadingly means NO-GO).
            sys.modules.pop(spec.name, None)
            raise ImportError(f"unable to load grill_core.{name}") from exc
        _GRILL_CORE[name] = module
    return _GRILL_CORE[name]


# LD-002 revisada: the eight codes literally named by §22/§23 -- the ones a
# reviewer judges the wiring against by name -- get an explicit, tested
# table entry. A code that already belongs to the live v2 contract
# (METADATA-SCHEMA, LOCK-CONTENTION, IMMUTABLE-TAMPERED, WORK-ITEM-MISSING,
# ...) is not in this table and must pass through unchanged: reusing the
# existing code *is* the correct behaviour, never to be mistaken for one of
# the eight and rewritten.
V3_CODE_TRANSLATION: dict[str, str] = {
    "BLOCKED_CAPABILITY": "BLOCKED-CAPABILITY",
    "STALE_LEASE": "STALE-LEASE",
    "ORCHESTRATOR_INVALID": "ORCHESTRATOR-INVALID",
    "STALE_PLAN": "STALE-PLAN",
    "UNATTESTED_STEP_OUTPUT": "UNATTESTED-STEP-OUTPUT",
    "STALE_SKILL_RESOLUTION": "STALE-SKILL-RESOLUTION",
    "PROJECT_IDENTITY_DIVERGENCE": "PROJECT-IDENTITY-DIVERGENCE",
    "STATE_DIVERGENCE": "STATE-DIVERGENCE",
}
# grill_core.work_item_v3's own module docstring (LD-002 revisada, applied to
# its full vocabulary, not just the eight plan-literal names) mints new
# SCREAMING_SNAKE codes for every v3-only condition as its validation grows
# (WORKTREE_PATH_FORBIDDEN, INVALID_PARENT, WORK_ITEM_V3_REQUIRED,
# V3_READERS_NOT_WIRED, ... -- the exact set is that module's to evolve, not
# this one's to enumerate). The live v2 contract has never used an
# underscore in ~200 assertions, so any code shaped like SCREAMING_SNAKE is,
# by that convention alone, v3-only vocabulary that still needs routing even
# when it is not one of the eight names above. A code that already contains
# a hyphen (the v2 spelling, reused on purpose by v3 modules) is left alone.
_SNAKE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")


def translate_v3_code(code: str) -> str:
    """Translate a v3 code to the live SCREAMING-KEBAB vocabulary; identity otherwise."""
    translated = V3_CODE_TRANSLATION.get(code)
    if translated is not None:
        return translated
    if "-" not in code and _SNAKE_CODE_RE.fullmatch(code):
        return code.replace("_", "-")
    return code


def raise_from_work_item_error(error: Any) -> NoReturn:
    """Re-raise a ``grill_core.work_item_v3.WorkItemError`` as ``CliFailure``.

    Runs every code through :func:`translate_v3_code` at this exact boundary
    (LD-002 revisada) so no v3 module output reaches the public JSON payload
    unrouted through the table, and carries the structured ``details`` dict
    over as ``extra`` so callers (e.g. WORK-ITEM-V3-REQUIRED) keep their
    diagnostic fields instead of collapsing to a bare message.
    """
    raise CliFailure(
        error.exit_code,
        error.verdict,
        translate_v3_code(error.code),
        error.message,
        extra=dict(error.details) if error.details else None,
    ) from error


def raise_from_triage_error(error: Any) -> NoReturn:
    """Re-raise a ``grill_core.triage.TriageError`` as ``CliFailure``.

    Same boundary contract as :func:`raise_from_work_item_error`: every code
    goes through :func:`translate_v3_code`, so the triage module mints its
    conditions in ``SCREAMING_SNAKE`` and the public payload still speaks the
    live ``SCREAMING-KEBAB`` vocabulary.
    """
    raise CliFailure(
        error.exit_code,
        error.verdict,
        translate_v3_code(error.code),
        error.message,
        extra=dict(error.details) if error.details else None,
    ) from error


class JsonParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", message)


@dataclass
class CliFailure(Exception):
    exit_code: int
    verdict: str
    code: str
    message: str
    findings: list[str] | None = None
    # Peça E / LD-004 item 5: carries a translated grill_core.work_item_v3
    # WorkItemError's `details` dict (work_id, operation, migration hints, ...)
    # across the CLI boundary without inventing a second payload shape.
    extra: dict[str, Any] | None = None

    def payload(self) -> dict[str, Any]:
        result: dict[str, Any] = {"verdict": self.verdict, "code": self.code, "error": self.message}
        if self.findings:
            result["findings"] = sorted(set(self.findings))
        if self.extra:
            for key, value in self.extra.items():
                result.setdefault(key, value)
        return result


@dataclass
class ItemBundle:
    work_id: str
    files: dict[str, bytes]
    origin: str
    fingerprint: str
    metadata: dict[str, Any]


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(root: Path, *args: str, text: bool = True, check: bool = True) -> str | bytes:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=text,
        check=False,
    )
    if check and process.returncode != 0:
        stderr = process.stderr.strip() if text else process.stderr.decode("utf-8", "replace").strip()
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "GIT-ERROR", stderr or "git command failed")
    return process.stdout


def git_optional(root: Path, *args: str) -> str:
    process = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    return process.stdout.strip() if process.returncode == 0 else ""


def project_root(raw: str | Path) -> Path:
    path = Path(raw)
    if not path.is_dir() or path.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ROOT", "root must be a real directory")
    top = git_optional(path, "rev-parse", "--show-toplevel")
    if not top or Path(top).resolve() != path.resolve():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ROOT", "root must be the Git top-level")
    return path.resolve()


def reject_symlink_chain(root: Path, path: Path, *, allow_missing: bool = True) -> None:
    # Resolve only the trusted root.  The path under inspection must remain
    # lexical so that every component can be checked before it is followed.
    root_lexical = Path(os.path.abspath(root))
    root_resolved = root_lexical.resolve()
    path_lexical = Path(os.path.abspath(path))
    relative: Path | None = None
    cursor_root = root_lexical
    for candidate_root in (root_lexical, root_resolved):
        try:
            relative = path_lexical.relative_to(candidate_root)
            cursor_root = candidate_root
            break
        except ValueError:
            continue
    # macOS exposes /var as a symlink to /private/var.  Accept that alias
    # only when the host actually presents it; do not realpath the evaluated
    # path, which would hide an unsafe link in the chain.
    if relative is None and os.path.islink("/var"):
        try:
            if os.readlink("/var") in {"private/var", "/private/var"}:
                alias_root = Path("/var") / root_resolved.relative_to("/private/var")
                try:
                    relative = path_lexical.relative_to(alias_root)
                    cursor_root = alias_root
                except ValueError:
                    pass
        except (OSError, ValueError):
            pass
    if relative is None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PATH-ESCAPE", str(path))
    cursor = cursor_root
    for part in relative.parts:
        if part in {"", ".", ".."}:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PATH-ESCAPE", str(path))
        cursor = cursor / part
        if cursor.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(cursor))
        if not cursor.exists() and allow_missing:
            continue


def ensure_directory(root: Path, relative: str) -> Path:
    target = root / relative
    reject_symlink_chain(root, target)
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.exists():
            if cursor.is_symlink() or not cursor.is_dir():
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-DIRECTORY", str(cursor))
        else:
            try:
                cursor.mkdir()
            except FileExistsError:
                # Another cooperating process may create the same parent
                # between exists() and mkdir(). Revalidate instead of leaking
                # the benign race as a filesystem failure.
                if cursor.is_symlink() or not cursor.is_dir():
                    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-DIRECTORY", str(cursor))
    return target


def safe_read(path: Path, *, root: Path | None = None, utf8: bool = False) -> bytes | str:
    try:
        data = safe_read_regular_fd(root or path.parent, path)
        return data.decode("utf-8") if utf8 else data
    except UnicodeError as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-UTF8", str(path)) from exc
    except OSError as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "FILESYSTEM", type(exc).__name__) from exc


def safe_read_regular_fd(root: Path, path: Path) -> bytes:
    """Read one regular file through an O_NOFOLLOW descriptor.

    The lexical chain check is deliberately repeated immediately before open;
    fstat then makes the object being hashed the object actually read.
    """
    reject_symlink_chain(root, path, allow_missing=False)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "EVIDENCE-MISSING", str(path)) from exc
    except OSError as exc:
        code = "SYMLINK-REJECTED" if exc.errno in {errno.ELOOP, errno.EMLINK} else "UNSAFE-FILE"
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, str(path)) from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "EVIDENCE-NOT-REGULAR", str(path))
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk: break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def atomic_write(root: Path, path: Path, data: bytes) -> bool:
    reject_symlink_chain(root, path)
    if path.exists() and path.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return False
    fd, temporary = tempfile.mkstemp(prefix=".grill-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        return True
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def ensure_managed_constitution(root: Path) -> tuple[bool, str]:
    """Create the managed Constitution once without following path races."""
    path = root / CONSTITUTION_PATH
    template = (ASSETS / "GRILL-CONSTITUTION.template.md").read_text(encoding="utf-8")
    today = date.today().isoformat()
    data = template.replace("{{RATIFIED}}", today).replace("{{LAST_AMENDED}}", today).encode("utf-8")
    validate_constitution_text(data.decode("utf-8"))
    constitution_clauses(data.decode("utf-8"))

    def validate_existing(existing: bytes) -> tuple[bool, str]:
        try:
            text = existing.decode("utf-8")
        except UnicodeError as exc:
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CONSTITUTION-INVALID-UTF8", str(path)) from exc
        validate_constitution_text(text)
        constitution_clauses(text)
        return False, hash_bytes(existing)

    def read_descriptor(fd: int) -> bytes:
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    supports_openat = os.open in getattr(os, "supports_dir_fd", set()) and os.mkdir in getattr(os, "supports_dir_fd", set())
    if supports_openat:
        descriptors: list[int] = []
        try:
            current = os.open(root, os.O_RDONLY | directory | nofollow)
            descriptors.append(current)
            for component in (".specify", "memory"):
                try:
                    os.mkdir(component, 0o755, dir_fd=current)
                except FileExistsError:
                    pass
                child = os.open(component, os.O_RDONLY | directory | nofollow, dir_fd=current)
                descriptors.append(child)
                current = child
            try:
                created_fd = os.open("constitution.md", os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, 0o644, dir_fd=current)
            except FileExistsError:
                existing_fd = os.open("constitution.md", os.O_RDONLY | nofollow, dir_fd=current)
                try:
                    return validate_existing(read_descriptor(existing_fd))
                finally:
                    os.close(existing_fd)
            with os.fdopen(created_fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.fsync(current)
            readback_fd = os.open("constitution.md", os.O_RDONLY | nofollow, dir_fd=current)
            try:
                check = read_descriptor(readback_fd)
            finally:
                os.close(readback_fd)
            if check != data:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONSTITUTION-READBACK", str(path))
            return True, hash_bytes(data)
        except OSError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-DIRECTORY", type(exc).__name__) from exc
        finally:
            for descriptor in reversed(descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    # Portable fallback. Component validation and optional O_NOFOLLOW retain
    # the same structured fail-closed contract on runtimes without openat.
    ensure_directory(root, ".specify/memory")
    reject_symlink_chain(root, path)
    try:
        created_fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, 0o644)
    except FileExistsError:
        existing = safe_read(path, root=root)
        assert isinstance(existing, bytes)
        return validate_existing(existing)
    with os.fdopen(created_fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    reject_symlink_chain(root, path, allow_missing=False)
    check = safe_read(path, root=root)
    assert isinstance(check, bytes)
    if check != data:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONSTITUTION-READBACK", str(path))
    return True, hash_bytes(data)


def read_asset(name: str) -> bytes:
    mapping = {
        "CONTEXT.md": "CONTEXT.template.md",
        "DECISION-BACKLOG.md": "DECISION-BACKLOG.template.md",
        "DECISION-FRONTIER.md": "DECISION-FRONTIER.template.md",
        "ROADMAP.md": "ROADMAP.template.md",
        "ROUND-LOG.jsonl": "ROUND-LOG.template.jsonl",
        "PLAN-CONTEXT.md": "PLAN-CONTEXT.template.md",
        "AUDIT.md": "AUDIT.template.md",
        "DELIVERY-MAP.md": "DELIVERY-MAP.template.md",
    }
    asset = ASSETS / mapping[name]
    return asset.read_bytes()


def validate_constitution_text(text: str) -> None:
    placeholder_patterns = (
        r"\{\{[^}]+\}\}",
        r"\[(?:PROJECT|PRINCIPLE|CONSTITUTION|RATIFICATION|LAST_AMENDED)[A-Z0-9_]*\]",
        r"\bYYYY-MM-DD\b",
    )
    if not text.strip() or any(re.search(pattern, text) for pattern in placeholder_patterns):
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CONSTITUTION-INVALID", "placeholders or empty content")


def constitution_clauses(text: str) -> list[dict[str, str]]:
    clauses: list[dict[str, str]] = []
    seen: set[str] = set()
    containers = {"core principles", "princípios fundamentais", "principios fundamentais"}
    for match in re.finditer(r"(?m)^(#{2,3})\s+(.+?)\s*$", text):
        heading = match.group(2).strip().strip("#").strip()
        normalized = re.sub(r"\s+", " ", heading).strip()
        if normalized.casefold() in containers:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-") or "clause"
        clause_id = slug
        suffix = 2
        while clause_id in seen:
            clause_id = f"{slug}-{suffix}"
            suffix += 1
        seen.add(clause_id)
        clauses.append({"id": clause_id, "heading": normalized})
    if not clauses:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CONSTITUTION-AMBIGUOUS", "no normative H2/H3 headings")
    return clauses


def constitution_info(root: Path) -> tuple[dict[str, Any], str | None, list[dict[str, str]]]:
    path = root / ".specify" / "memory" / "constitution.md"
    try:
        reject_symlink_chain(root, path, allow_missing=True)
    except CliFailure as failure:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", failure.code, failure.message) from failure
    if path.is_symlink():
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "SYMLINK-REJECTED", str(path))
    if not path.exists():
        return {"state": "not-present", "path": None, "sha256": None}, None, []
    try:
        text = safe_read(path, root=root, utf8=True)
    except CliFailure as failure:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", failure.code, failure.message) from failure
    assert isinstance(text, str)
    validate_constitution_text(text)
    digest = hash_bytes(text.encode("utf-8"))
    return {"state": "present", "path": ".specify/memory/constitution.md", "sha256": digest}, text, constitution_clauses(text)


def check_document(info: dict[str, Any], clauses: list[dict[str, str]], *, pending: bool) -> bytes:
    if info["state"] == "not-present":
        payload = {"constitution_state": "not-present", "constitution_sha256": None, "clauses": []}
    else:
        payload = {
            "constitution_state": "present",
            "constitution_sha256": info["sha256"],
            "clauses": [
                {
                    "id": clause["id"],
                    "heading": clause["heading"],
                    "status": "PENDING" if pending else "PASS",
                    "evidence": [] if pending else ["verified evidence"],
                    "justification": "" if pending else "verified against the work-item artifacts",
                }
                for clause in clauses
            ],
        }
    return (
        "# Constitution Check\n\n"
        + CHECK_START
        + "\n```json\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n"
        + CHECK_END
        + "\n"
    ).encode("utf-8")


def parse_check(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-INVALID-UTF8", "CONSTITUTION-CHECK.md") from exc
    if text.count(CHECK_START) != 1 or text.count(CHECK_END) != 1:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-MARKERS", "managed block missing or duplicated")
    block = text.split(CHECK_START, 1)[1].split(CHECK_END, 1)[0]
    match = re.search(r"```json\s*(\{.*\})\s*```", block, re.DOTALL)
    if not match:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", "JSON block missing")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", exc.msg) from exc
    if not isinstance(value, dict):
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", "root must be object")
    return value


def validate_constitution_check(root: Path, files: dict[str, bytes], recorded: dict[str, Any]) -> dict[str, Any] | None:
    current, text, clauses = constitution_info(root)
    if current["state"] == "not-present":
        # Auditing an item is read-only and must remain useful when a project
        # constitution is absent.  A changed (present) constitution is stale,
        # but disappearance is an ungoverned/legacy audit, not a constitutional
        # validation failure.
        return None
    if recorded.get("state") != "present" or recorded.get("sha256") != current["sha256"]:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CONSTITUTION-STALE", "constitution hash changed")
    raw = files.get("CONSTITUTION-CHECK.md")
    if raw is None:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-MISSING", "CONSTITUTION-CHECK.md")
    check = parse_check(raw)
    if check.get("constitution_state") != "present" or check.get("constitution_sha256") != current["sha256"]:
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-STALE", "constitution hash mismatch")
    entries = check.get("clauses")
    if not isinstance(entries, list):
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", "clauses must be an array")
    expected = {clause["id"]: clause["heading"] for clause in clauses}
    actual: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-SCHEMA", "invalid clause entry")
        clause_id = entry["id"]
        if clause_id in actual:
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-DUPLICATE", clause_id)
        actual[clause_id] = entry
    if set(actual) != set(expected):
        raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-COVERAGE", "missing or unknown clauses")
    for clause_id, heading in expected.items():
        entry = actual[clause_id]
        status = str(entry.get("status", "")).upper()
        evidence = entry.get("evidence")
        justification = entry.get("justification")
        evidence_ok = (isinstance(evidence, str) and bool(evidence.strip())) or (
            isinstance(evidence, list) and bool(evidence) and all(isinstance(value, str) and value.strip() for value in evidence)
        )
        if entry.get("heading") != heading or status not in {"PASS", "NOT-APPLICABLE"} or not evidence_ok or not isinstance(justification, str) or not justification.strip():
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-NOT-APPROVED", clause_id)
    return {"state": "present", "sha256": current["sha256"], "clauses": len(expected)}


def constitution_reseal_check(info: dict[str, Any], clauses: list[dict[str, str]], evidence: str) -> bytes:
    payload = {
        "constitution_state": "present",
        "constitution_sha256": info["sha256"],
        "clauses": [{
            "id": clause["id"], "heading": clause["heading"], "status": "PASS",
            "evidence": [evidence], "justification": "approved after reviewing the amended constitution",
        } for clause in clauses],
    }
    return (
        "# Constitution Check\n\n" + CHECK_START + "\n```json\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n" + CHECK_END + "\n"
    ).encode("utf-8")


def workflow_info(root: Path) -> dict[str, Any]:
    path = root / "WORKFLOW.md"
    if not path.exists():
        return {"path": "WORKFLOW.md", "sha256": None}
    data = safe_read(path, root=root)
    assert isinstance(data, bytes)
    return {"path": "WORKFLOW.md", "sha256": hash_bytes(data)}


def base_information(root: Path, requested: str | None) -> tuple[str, str]:
    head = git_optional(root, "rev-parse", "HEAD")
    if requested:
        target = git_optional(root, "rev-parse", "--verify", requested)
        if not target:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-BASE-REF", requested)
        merge_base = git_optional(root, "merge-base", "HEAD", requested) if head else ""
        return requested, merge_base or target
    upstream = git_optional(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if upstream:
        merge_base = git_optional(root, "merge-base", "HEAD", upstream)
        if merge_base:
            return upstream, merge_base
    return ("HEAD", head) if head else ("UNBORN", "UNBORN")


def immutable_metadata(root: Path, args: argparse.Namespace, work_id: str) -> dict[str, Any]:
    # T017: no "goal" key here, by design. This dict is serialised verbatim
    # into WORK-ITEM.json -- sealed identity that invalidates the work item if
    # it changes. goal.md is a project-wide artefact a human can legitimately
    # edit later (unlike constitution/workflow fixation), so it is reported
    # via ensure_project_goal()/state.json's own goal block, never sealed
    # here. tests/validate_goal_document_contract.py (T031b) asserts this.
    constitution, _, _ = constitution_info(root)
    base_ref, base_commit = base_information(root, getattr(args, "base_ref", None))
    return {
        "schema": "grill-work-item/v2",
        "work_id": work_id,
        "type": args.type,
        "slug": args.slug,
        "branch": git_optional(root, "branch", "--show-current") or "DETACHED",
        "head": git_optional(root, "rev-parse", "HEAD") or "UNBORN",
        "base_ref": base_ref,
        "base_commit": base_commit,
        "constitution": constitution,
        "workflow": workflow_info(root),
    }


def state_template(root: Path, work_id: str, constitution: dict[str, Any], workflow: dict[str, Any],
                   goal: dict[str, Any] | None = None) -> bytes:
    value = json.loads((ASSETS / "state.template.json").read_text(encoding="utf-8"))
    value["work_id"] = work_id
    if _workflow_module(root).VERSION == "v5":
        value["development"]["workflow_version"] = "v5"
    value["constitution"] = constitution
    # "schema", not "version": the value is this block's own frozen shape tag and
    # has never tracked the WORKFLOW.md document version -- that one lives in
    # development.workflow_version.  The old name invited exactly the misreading
    # that a v4 document with "version": "v2" here was inconsistent.  Readers
    # accept both spellings, so materialised bundles need no migration.
    value["workflow"] = {**workflow, "schema": "v2"}
    if goal is not None:
        # E4 (data-model.md): only path/sha256/status land in state.json --
        # "version" and "reason" are init's payload-only fields (E5). ``goal``
        # defaults to None for callers (migrate_command) that never
        # materialise goal.md, so their state.json stays exactly as before.
        value["goal"] = {"path": goal["path"], "sha256": goal["sha256"], "status": goal["status"]}
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def initial_files(root: Path, work_id: str, immutable: dict[str, Any], goal: dict[str, Any] | None = None, *,
                  backlog_skipped: bool = False) -> dict[str, bytes]:
    _, _, clauses = constitution_info(root)
    files = {name: read_asset(name) for name in ROOT_FILES if name not in {"state.json", "CONSTITUTION-CHECK.md"}}
    files["state.json"] = state_template(root, work_id, immutable["constitution"], immutable["workflow"], goal)
    if backlog_skipped:
        # Stamped here, not after publication: initial_artifacts is computed
        # from these bytes, so writing the stamp afterwards would make every
        # bundle created through the escape hatch fail its own integrity gate.
        state = json.loads(files["state.json"].decode("utf-8"))
        state["backlog_skipped"] = True
        files["state.json"] = (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    files["CONSTITUTION-CHECK.md"] = check_document(immutable["constitution"], clauses, pending=immutable["constitution"]["state"] == "present")
    files["handoffs/FASE-001-SPECIFY-HANDOFF.md"] = (ASSETS / "PHASE-SPECIFY-HANDOFF.template.md").read_bytes()
    return files


def hotfix_files(root: Path, work_id: str, immutable: dict[str, Any], details: dict[str, str]) -> dict[str, bytes]:
    """Build a prepared, self-contained incident record with no roadmap dependencies."""
    files = {"HOTFIX.md": ("# HOTFIX-PREPARED\n\n" + "\n".join(f"- {key}: {value}" for key, value in details.items()) + "\n\n## Delivery boundary\n\nHOTFIX-GO requires the separate hotfix-go revalidation step. Reconciliation and full documentary audit are post-ship.\n").encode("utf-8")}
    files["state.json"] = (json.dumps({"version": "1.1.0", "status": "prepared", "audit_verdict": "PREPARED", "mode": "hotfix", "work_id": work_id, "post_ship": ["reconcile", "full-document-audit"]}, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    files["CONSTITUTION-CHECK.md"] = check_document(immutable["constitution"], constitution_info(root)[2], pending=True)
    return files


def hotfix_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if not SLUG_RE.fullmatch(args.slug):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-IDENTITY", "slug invalid")
    values = {"scope": args.scope, "reproduction": args.reproduction, "evidence": args.evidence, "correction-test": args.correction_test, "rollback": args.rollback, "constitution-evidence": args.constitution_evidence, "test-command": args.test_command}
    if any(not value.strip() for value in values.values()):
        raise CliFailure(EXIT_NO_GO, "NO-GO", "HOTFIX-INCOMPLETE", "all hotfix evidence fields are required")
    scope_paths = validate_scope(args.scope)
    if args.test_timeout < 1 or args.test_timeout > 300:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-TEST-TIMEOUT", str(args.test_timeout))
        raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-NOT-CLOSED", "scope contains traversal or line break")
    work_id = args.work_id or f"hotfix-{args.slug}-{uuid.uuid4().hex}"
    if not WORK_ID_RE.fullmatch(work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-WORK-ID", work_id)
    target = root / ".grill" / "work-items" / work_id
    lock = acquire_lock(root, work_id, target, reuse_if_target_exists=True)
    try:
        if target.exists():
            bundle = read_local_bundle(root, target)
            validate_bundle_integrity(bundle)
            existing = bundle.metadata.get("hotfix", {})
            requested = {**values, "closed": True, "test-timeout": args.test_timeout, "post_ship": ["reconcile", "full-document-audit"]}
            if existing != requested or bundle.metadata.get("scope", {}).get("paths") != scope_paths or bundle.metadata.get("immutable", {}).get("slug") != args.slug:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "HOTFIX-IDENTITY-DIVERGENCE", work_id)
            return {"verdict": "HOTFIX-PREPARED", "status": "REUSED", "work_id": work_id, "path": str(target)}, EXIT_OK
        immutable = immutable_metadata(root, argparse.Namespace(type="hotfix", slug=args.slug, base_ref=args.base_ref), work_id)
        constitution = immutable["constitution"]
        if constitution.get("state") == "present" and args.constitution_evidence != "not-applicable":
            evidence = Path(args.constitution_evidence)
            if evidence.is_absolute() or any(part in {"", ".", ".."} for part in evidence.parts):
                raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-CONSTITUTION-EVIDENCE", args.constitution_evidence)
            evidence_path = root / evidence
            text = safe_read(evidence_path, root=root, utf8=True)
            if not isinstance(text, str) or not text.strip():
                raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-CONSTITUTION-EVIDENCE", args.constitution_evidence)
            values["constitution-evidence"] = json.dumps({"path": evidence.as_posix(), "sha256": hash_bytes(text.encode("utf-8"))}, sort_keys=True)
        else:
            values["constitution-evidence"] = "not-present"
        files = hotfix_files(root, work_id, immutable, values)
        if immutable["constitution"].get("state") == "present" and args.constitution_evidence != "not-applicable":
            evidence = json.loads(values["constitution-evidence"])
            payload = {"constitution_state": "present", "constitution_sha256": immutable["constitution"]["sha256"], "clauses": [{"id": clause["id"], "heading": clause["heading"], "status": "PASS", "evidence": [evidence["path"] + "#" + evidence["sha256"]], "justification": "constitution evidence recorded reproducibly"} for clause in constitution_info(root)[2]]}
            files["CONSTITUTION-CHECK.md"] = ("# Constitution Check\n\n" + CHECK_START + "\n```json\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n```\n" + CHECK_END + "\n").encode("utf-8")
        metadata = metadata_document(immutable, files)
        metadata["scope"] = {"paths": scope_paths}
        metadata["hotfix"] = {**values, "closed": True, "test-timeout": args.test_timeout, "post_ship": ["reconcile", "full-document-audit"]}
        metadata["hotfix_sha256"] = hash_bytes(canonical(metadata["hotfix"]))
        staging = write_bundle_staging(root, work_id, metadata, files)
        try:
            rename_child(target.parent, staging, target)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return {"verdict": "HOTFIX-PREPARED", "status": "CREATED", "work_id": work_id, "path": str(target), "mode": "hotfix-fast", "post_ship": metadata["hotfix"]["post_ship"]}, EXIT_OK
    finally:
        if lock is not None:
            shutil.rmtree(lock, ignore_errors=True)


def metadata_document(immutable: dict[str, Any], files: dict[str, bytes], *, migration: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "grill-work-item/v2",
        "immutable": immutable,
        "immutable_sha256": hash_bytes(canonical(immutable)),
        "scope": {"paths": []},
        "depends-on-work": [],
        "conflicts-with-adrs": [],
        "initial_artifacts": {path: hash_bytes(data) for path, data in sorted(files.items())},
    }
    if immutable.get("type") in {"feature", "fix"}:
        result["capability"] = {"name": "module-decomposition", "version": "v1", "schema": "v1"}
    if migration:
        result["migration"] = migration
    return result



def validate_scope(raw: str) -> list[str]:
    if not isinstance(raw, str) or not raw.strip() or "\n" in raw or "\r" in raw:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-NOT-CLOSED", "scope contains line break or is empty")
    paths = [part.strip() for part in raw.split(",")]
    for path in paths:
        candidate = Path(path)
        if not path or candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts) or "\\" in path:
            raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-NOT-CLOSED", path or raw)
    return paths


def changed_paths_from_base(root: Path, base_commit: str) -> set[str]:
    if not isinstance(base_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", base_commit):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-BASE-COMMIT", str(base_commit))
    output = run_git(root, "diff", "--name-only", "--diff-filter=ACDMRTUXB", base_commit, "HEAD")
    status = run_git(root, "status", "--porcelain=v1", "--untracked-files=all")
    paths = {line.strip() for line in output.splitlines() if line.strip()}
    for line in status.splitlines():
        if len(line) >= 4:
            paths.add(line[3:].split(" -> ", 1)[-1])
    return paths


def validate_hotfix_scope_changes(root: Path, bundle: ItemBundle) -> None:
    changed = changed_paths_from_base(root, bundle.metadata.get("immutable", {}).get("base_commit"))
    allowed = set(bundle.metadata.get("scope", {}).get("paths", []))
    allowed.add(f".grill/work-items/{bundle.work_id}")
    outside = sorted(path for path in changed if not any(path == item or path.startswith(item.rstrip("/") + "/") for item in allowed))
    if outside:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "HOTFIX-SCOPE-VIOLATION", ",".join(outside))


def validate_bundle_integrity(bundle: ItemBundle) -> None:
    expected = bundle.metadata.get("initial_artifacts")
    actual = {path: hash_bytes(data) for path, data in sorted(bundle.files.items()) if path != "WORK-ITEM.json"}
    if not isinstance(expected, dict) or expected != actual:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "BUNDLE-INTEGRITY", bundle.work_id)


def validated_hotfix(bundle: ItemBundle) -> dict[str, Any]:
    hotfix = bundle.metadata.get("hotfix")
    if not isinstance(hotfix, dict) or bundle.metadata.get("hotfix_sha256") != hash_bytes(canonical(hotfix)):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "HOTFIX-METADATA-TAMPERED", bundle.work_id)
    if hotfix.get("closed") is not True:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "HOTFIX-INCOMPLETE", bundle.work_id)
    scope = validate_scope(hotfix.get("scope", ""))
    if bundle.metadata.get("scope", {}).get("paths") != scope:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "HOTFIX-SCOPE-DIVERGENCE", bundle.work_id)
    return hotfix


SCHEMA_WORK_ITEM_V3 = "grill-work-item/v3"
# LD-010 item 4: field names that only ever belong to a v3 immutable block
# (mirrors grill_core.work_item_v3.V3_IMMUTABLE_FIELDS minus "worktree_key"'s
# sibling path-guard keys, which validate_metadata never needs to duplicate
# here -- only the presence check does). Kept as a small local literal, not
# imported from grill_core, so the v2 fast path stays free of any load-time
# dependency on it, matching this function's existing "zero behavioural
# change for v2" contract.
V3_ORPHAN_IMMUTABLE_FIELDS = ("parent_work_id", "source", "worktree_key")


def validate_metadata(metadata: dict[str, Any], expected_work_id: str | None = None) -> dict[str, Any]:
    """Dual-read v2/v3 validator (LD-004 peça E, item 1).

    A v2 document takes the exact path this function has always taken --
    zero behavioural change for any pre-v3 consumer, byte for byte. A v3
    document's *form* is delegated to grill_core.work_item_v3 (the schema's
    owner module); this function only translates its exceptions at the CLI
    boundary. The branch is decided from the raw, unvalidated probe alone --
    the real (hash-checked) schema read happens inside whichever path is
    taken, exactly as before.
    """
    probe = metadata.get("immutable") if isinstance(metadata, dict) else None
    probe_schema = probe.get("schema") if isinstance(probe, dict) else None
    if probe_schema == SCHEMA_WORK_ITEM_V3:
        work_item_v3 = grill_core_module("work_item_v3")
        try:
            return work_item_v3.validate_metadata(metadata, expected_work_id)
        except work_item_v3.WorkItemError as error:
            raise_from_work_item_error(error)
    immutable = metadata.get("immutable")
    if not isinstance(immutable, dict) or metadata.get("immutable_sha256") != hash_bytes(canonical(immutable)):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IMMUTABLE-TAMPERED", expected_work_id or "unknown")
    # Downgrade guard (LD-010 item 4 / §22 Core "snapshot local divergente ...
    # falha fechado"). The branch above (v2 vs v3) is chosen from
    # `immutable.schema` alone -- exactly the field an attacker controls.
    # Recomputing immutable_sha256 with THIS module's own canonicalizer over a
    # tampered immutable block that claims schema=v2 while still carrying v3
    # fields (parent_work_id, source, worktree_key -- including a path-escape
    # worktree_key payload) is self-consistent, so the hash check above alone
    # does not catch it; nothing below this point has ever known those v3
    # field names exist. Migration is monotonic: once a document carries any
    # v3-shaped field it can never again validate as v2.
    if any(name in immutable for name in V3_ORPHAN_IMMUTABLE_FIELDS) or "orchestration" in metadata:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", translate_v3_code("STATE_DIVERGENCE"), expected_work_id or immutable.get("work_id") or "unknown")
    if (
        immutable.get("schema") != "grill-work-item/v2"
        or not isinstance(immutable.get("work_id"), str)
        or immutable.get("type") not in KINDS
        or not isinstance(immutable.get("slug"), str)
        or not SLUG_RE.fullmatch(immutable["slug"])
        or not WORK_ID_RE.fullmatch(immutable["work_id"])
    ):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "METADATA-SCHEMA", expected_work_id or "unknown")
    if expected_work_id is not None and immutable["work_id"] != expected_work_id:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORK-ID-DIVERGENCE", expected_work_id)
    migration = metadata.get("migration")
    if migration is not None:
        if not isinstance(migration, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "MIGRATION-SCHEMA", immutable["work_id"])
        source_hashes = migration.get("source_hashes")
        source_paths = migration.get("source_paths")
        if (
            not isinstance(source_hashes, dict)
            or not isinstance(source_paths, dict)
            or set(source_hashes) != set(source_paths)
            or not all(isinstance(key, str) and isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for key, value in source_hashes.items())
            or not all(isinstance(key, str) and isinstance(value, str) and value for key, value in source_paths.items())
        ):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "MIGRATION-SCHEMA", immutable["work_id"])
    return immutable


def process_start_observation(pid: int) -> tuple[str, str | None]:
    """Observe Linux process identity without treating read errors as death."""
    if not sys.platform.startswith("linux"):
        return "unsupported", None
    path = Path("/proc") / str(pid) / "stat"
    try:
        fields = path.read_text(encoding="utf-8").rsplit(")", 1)[1].split()
    except FileNotFoundError:
        return "missing", None
    except (OSError, UnicodeError, IndexError):
        return "unavailable", None
    if len(fields) <= 19:
        return "unavailable", None
    return "found", f"linux:{fields[19]}"


def process_start_token(pid: int) -> str | None:
    status, token = process_start_observation(pid)
    return token if status == "found" else None


def stale_local_lock(lock: Path) -> bool:
    try:
        value = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
        pid, host, recorded_start = value.get("pid"), value.get("host"), value.get("process_start")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return False
    observation, current_start = process_start_observation(pid) if type(pid) is int else ("unavailable", None)
    return bool(
        host == socket.gethostname()
        and type(pid) is int
        and pid > 0
        and isinstance(recorded_start, str)
        and recorded_start.startswith("linux:")
        and observation in {"found", "missing"}
        and current_start != recorded_start
    )


def acquire_lock(
    root: Path,
    work_id: str,
    target: Path,
    timeout: float = 15.0,
    *,
    reuse_if_target_exists: bool = False,
) -> Path | None:
    locks = ensure_directory(root, ".grill/locks")
    lock = locks / f"{work_id}.lock"
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock.mkdir()
            owner = {"pid": os.getpid(), "host": socket.gethostname()}
            start_token = process_start_token(os.getpid())
            if start_token is not None:
                owner["process_start"] = start_token
            (lock / "owner.json").write_text(json.dumps(owner, sort_keys=True), encoding="utf-8")
            return lock
        except FileExistsError:
            # Work-item directories are published by one atomic rename. Once the
            # target is visible, readers can safely validate/reuse it without
            # waiting for the creator to remove its diagnostic lock directory.
            if reuse_if_target_exists and target.is_dir() and not target.is_symlink():
                return None
            recovery = locks / f".{work_id}.recovery"
            recovered = False
            try:
                recovery.mkdir()
            except FileExistsError:
                pass
            else:
                try:
                    # Re-read the owner while holding the recovery mutex. This
                    # prevents an old waiter from deleting a newly acquired lock.
                    if stale_local_lock(lock):
                        shutil.rmtree(lock, ignore_errors=False)
                        recovered = True
                except FileNotFoundError:
                    recovered = True
                finally:
                    shutil.rmtree(recovery, ignore_errors=True)
            if recovered:
                continue
            if time.monotonic() >= deadline:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LOCK-CONTENTION", work_id)
            time.sleep(0.03)


def write_bundle_staging(root: Path, work_id: str, metadata: dict[str, Any], files: dict[str, bytes]) -> Path:
    parent = ensure_directory(root, ".grill/work-items")
    staging = Path(tempfile.mkdtemp(prefix=f".{work_id}-", dir=parent))
    try:
        for relative, data in sorted(files.items()):
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        (staging / "docs/adr").mkdir(parents=True, exist_ok=True)
        (staging / "handoffs").mkdir(parents=True, exist_ok=True)
        (staging / "WORK-ITEM.json").write_bytes(
            (json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        )
        return staging
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def replace_work_item_bundle(root: Path, target: Path, metadata: dict[str, Any], files: dict[str, bytes]) -> None:
    """Publish a complete replacement and restore the old bundle on failure."""
    parent = target.parent
    staging = write_bundle_staging(root, target.name, metadata, files)
    backup = parent / f".{target.name}-backup-{uuid.uuid4().hex}"
    try:
        rename_child(parent, target, backup)
        try:
            rename_child(parent, staging, target)
            read_local_bundle(root, target)
        except Exception:
            failed = parent / f".{target.name}-failed-{uuid.uuid4().hex}"
            if target.exists():
                rename_child(parent, target, failed)
            rename_child(parent, backup, target)
            shutil.rmtree(failed, ignore_errors=True)
            raise
        shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _rename_dirfd_capable() -> bool:
    """Return true only when the complete protected dir-fd primitive is available."""
    return (os.rename in os.supports_dir_fd and hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW"))


def rename_child(parent: Path, source: Path, target: Path) -> None:
    """Move child directories after rejecting a target visible during validation.

    POSIX uses a verified parent FD and dir-fd rename. The path fallback is
    portable but does not reproduce protection against substitution of the
    parent or creation of the target between validation and rename (TOCTOU
    limitation). The per-work-item lock serializes cooperating plugin writers.
    """
    if source.parent != parent or target.parent != parent:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-RENAME-PATH", str(parent))
    if parent.is_symlink() or not parent.is_dir() or source.is_symlink() or not source.is_dir() or target.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-RENAME-PATH", str(parent))
    protected = _rename_dirfd_capable()
    if protected:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory_fd = os.open(parent, flags)
        try:
            parent_stat = os.stat(parent, follow_symlinks=False)
            fd_stat = os.fstat(directory_fd)
            if (fd_stat.st_dev, fd_stat.st_ino) != (parent_stat.st_dev, parent_stat.st_ino):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DIRECTORY-RACE", str(parent))
            os.stat(source.name, dir_fd=directory_fd, follow_symlinks=False)
            try:
                os.stat(target.name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise FileExistsError(errno.EEXIST, "target exists", str(target))
            os.rename(source.name, target.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
        return
    if target.exists():
        raise FileExistsError(errno.EEXIST, "target exists", str(target))
    os.rename(source, target)


def read_local_bundle(root: Path, item: Path) -> ItemBundle:
    reject_symlink_chain(root, item, allow_missing=False)
    if item.is_symlink() or not item.is_dir():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-WORK-ITEM", str(item))
    files: dict[str, bytes] = {}
    for path in sorted(item.rglob("*")):
        if path.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(path))
        if path.is_file():
            relative = path.relative_to(item).as_posix()
            files[relative] = safe_read_regular_fd(root, path)
    return bundle_from_files(item.name, files, str(item))


def read_external_bundle(item: Path) -> ItemBundle:
    """Read an artifact root that is intentionally separate from the Git project root."""
    absolute = Path(os.path.abspath(item))
    if Path(os.path.realpath(absolute)) != absolute or absolute.is_symlink() or not absolute.is_dir():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-ARTIFACT-ROOT", str(item))
    files: dict[str, bytes] = {}
    for path in sorted(absolute.rglob("*")):
        if path.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(path))
        if path.is_file():
            files[path.relative_to(absolute).as_posix()] = safe_read_regular_fd(absolute, path)
    raw = files.get("WORK-ITEM.json")
    if raw is None:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-MISSING", str(absolute))
    try:
        metadata = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-INVALID", str(absolute)) from exc
    immutable = validate_metadata(metadata)
    work_id = immutable["work_id"]
    return ItemBundle(work_id, files, str(absolute), bundle_fingerprint(files), metadata)


def bundle_fingerprint(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path, data in sorted(files.items()):
        digest.update(path.encode("utf-8") + b"\0" + hashlib.sha256(data).digest())
    return digest.hexdigest()


def bundle_from_files(work_id: str, files: dict[str, bytes], origin: str) -> ItemBundle:
    raw = files.get("WORK-ITEM.json")
    if raw is None:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-MISSING", origin)
    try:
        metadata = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-INVALID", origin) from exc
    immutable = validate_metadata(metadata, work_id)
    return ItemBundle(work_id, files, origin, bundle_fingerprint(files), metadata)


def ensure_project_workflow(root: Path) -> dict[str, Any]:
    """Materialise or validate the project-wide WORKFLOW.md before any bundle exists."""
    workflow = sibling("ensure_workflow")
    result = workflow.resolve_workflow(root)
    if result.status == "BLOCKED":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORKFLOW-UNAVAILABLE", result.reason or "unknown")
    return {"status": result.status, "path": "WORKFLOW.md", "sha256": workflow.digest(result.content)}


_GOAL_MARKER_RE = re.compile(r"grill-with-docs-goal:(v\d+)")


def _goal_document_version(content: bytes) -> str | None:
    """The goal.md marker version declared on the first line, or ``None``.

    Mirrors ``ensure_workflow.managed_version``/``grill_core.goal_document
    .managed_version``: matched only against the first line
    (contracts/goal-document.md) so a marker loose in the document body never
    identifies prose as managed.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeError:
        return None
    first_line = text.split("\n", 1)[0]
    match = _GOAL_MARKER_RE.search(first_line)
    return match.group(1) if match else None


def ensure_project_goal(root: Path) -> dict[str, Any]:
    """Materialise or validate the project-wide goal.md, symmetric to ensure_project_workflow.

    goal.md is a project-wide, plugin-owned artefact: every init rewrites a
    managed goal.md to the bundled template (``UPDATED``), unlike WORKFLOW.md,
    which is fixed once per project. This block never enters
    ``WORK-ITEM.json`` / ``immutable_metadata`` (T017): bytes that change on
    every plugin upgrade do not belong in sealed work-item identity.
    """
    goal = sibling("ensure_goal")
    result = goal.resolve_goal(root)
    if result.status == "BLOCKED":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "GOAL-UNAVAILABLE", result.reason or "unknown")
    block: dict[str, Any] = {
        "status": result.status,
        "path": "goal.md",
        "sha256": hashlib.sha256(result.content).hexdigest(),
    }
    version = _goal_document_version(result.content)
    if version is not None:
        block["version"] = version
    if result.status in {"PRESERVED", "UPDATED"}:
        block["reason"] = result.reason
    return block


def dependency_report(root: Path, *, runtime: str, allow_install: bool, remove_shadows: bool = False) -> dict[str, Any]:
    """Detect the external toolchain; install only when explicitly authorised.

    ``remove_shadows`` is separate from ``allow_install`` on purpose: deleting a
    skill directory outside the repository is not part of authorising an install.
    """
    dependencies = sibling("ensure_dependencies")
    try:
        return dependencies.preflight(
            root, runtime=runtime, allow_install=allow_install, remove_shadows=remove_shadows
        )
    except (dependencies.ManifestError, OSError, json.JSONDecodeError) as error:
        return {"schema": dependencies.SCHEMA, "verdict": "BLOCKED", "error": type(error).__name__}


def backlog_report(root: Path, *, apply: bool, create: bool = True, db: str | None = None) -> dict[str, Any]:
    bridge = sibling("backlog_bridge")
    try:
        return bridge.ensure_bind(root, apply=apply, create=create, db=db)
    except bridge.BacklogUnavailable as error:
        return {"schema": bridge.SCHEMA, "db": bridge.store_path(db), "verdict": "BLOCKED",
                "code": "BACKLOG-UNAVAILABLE", "detail": str(error)}


def backlog_is_bound(report: dict[str, Any]) -> bool:
    return (report.get("backlog") or {}).get("status") == "BOUND"


def _workflow_module(root: Path) -> Any:
    """Dispatch by the document being used, never by the installed default."""
    legacy = grill_core_module("workflow_v4")
    try:
        _, _, text = legacy.load_workflow(root)
    except legacy.Failure:
        return legacy
    if legacy.marker_version(text) == "v5" or (legacy.marker_version(text) is None and "workflow-step-skills.v5.json" in text):
        return grill_core_module("workflow_v5")
    return legacy


def _policy_path(root: Path, work_id: str | None = None, item: dict[str, Any] | None = None) -> Path:
    """An adopted item's pinned policy takes precedence over fresh defaults."""
    versions = grill_core_module("workflow_versions")
    if item is None and work_id is not None:
        snapshot = grill_core_module("store").read_snapshot(root, required=False)
        if snapshot is not None:
            item = snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(work_id)
    if item is not None:
        allowed = {"assets/" + name for name in versions.ORCHESTRATION_POLICY_BY_VERSION.values()}
        if item.get("policy_ref") not in allowed:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", str(work_id))
        path = ASSETS / item["policy_ref"].removeprefix("assets/")
        if hash_bytes(path.read_bytes()) != item.get("policy_sha256"):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", str(work_id))
        return path
    workflow = root / "WORKFLOW.md"
    version = versions.ACTIVE_VERSION
    if workflow.exists():
        version = _workflow_module(root).VERSION
    return ASSETS / versions.ORCHESTRATION_POLICY_BY_VERSION[version]


def _step_assessment(root: Path, work_id: str, step_id: str, policy: dict[str, Any]) -> dict[str, Any] | None:
    if policy.get("policy_version") != "2":
        return None
    reference = f".grill/work-items/{work_id}/step-inputs/{step_id}.json"
    contract = grill_core_module("agent_orchestration")
    try:
        raw = safe_read_regular_fd(root, root / reference)
        value = grill_core_module("store").loads(raw.decode("utf-8"))
        contract.validate_step_assessment(value, policy, step_id)
        for file in value["files"]:
            if hash_bytes(safe_read_regular_fd(root, root / file["path"])) != file["sha256"]:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STEP-ASSESSMENT-STALE", file["path"])
    except CliFailure:
        raise
    except (OSError, ValueError, grill_core_module("store").StoreError) as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STEP-ASSESSMENT-INVALID", reference) from exc
    return value


def _coordinator_response(runtime: str) -> dict[str, Any]:
    """Report the policy recommendation without touching the active model."""
    contract = grill_core_module("agent_orchestration")
    try:
        policy = json.loads((ASSETS / "agent-orchestration.v1.json").read_text(encoding="utf-8"))
        recommendation = contract.coordinator_recommendation(policy, runtime)
    except (OSError, json.JSONDecodeError, contract.OrchestrationError) as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", str(exc)) from exc
    return {"coordinator_recommendation": recommendation, "active_model_changed": False}


def _with_coordinator_response(payload: dict[str, Any], runtime: str) -> dict[str, Any]:
    return {**payload, **_coordinator_response(runtime)}


def require_openrouter_key() -> None:
    """The GWD decides through Jev; without the key the workflow cannot run."""
    jev = grill_core_module("jev")
    try:
        jev.require_key()
    except jev.JevError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.detail) from exc


# Local telemetry lives next to the orchestrator store, under the git common
# dir: shared by every worktree, never versioned, and never an untracked file
# that would make reconcile refuse DIRTY-WORKTREE.
TELEMETRY_DIR = "grill-telemetry"
JEV_LOG = f"<git-common-dir>/{TELEMETRY_DIR}/jev-decisions.jsonl"


def _telemetry_append(root: Path, name: str, record: dict[str, Any]) -> Path:
    directory = grill_core_module("store").git_common_dir(root) / TELEMETRY_DIR
    if directory.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(directory))
    directory.mkdir(mode=0o700, exist_ok=True)
    line = json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record},
                      ensure_ascii=False, sort_keys=True)
    path = directory / name
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return path


def _jev_log(root: Path, record: dict[str, Any]) -> None:
    """Append one line to the calibration log: Jev's answer, later the agent's final one."""
    _telemetry_append(root, "jev-decisions.jsonl", record)


def _decide_items(jev: Any, kind: str, state: dict[str, Any], root: Path, work_id: str | None,
                  step: str | None, has_files: bool) -> tuple[list[str], dict[str, Any] | None]:
    """Items each kind asks one question about; the state was already shaped by the caller."""
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    if kind == "step-assessment":
        if not step or not work_id or not WORK_ID_RE.fullmatch(work_id) or not has_files:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS",
                             "step-assessment needs --work-id, --step and --file")
        policy = json.loads(_policy_path(root, work_id).read_bytes())
        return list(policy.get("review_risks", [])), policy
    keyed = {"dq-batch": "candidates", "finding-severity": "findings", "human-or-author": "decisions"}
    if kind in keyed:
        value = context.get(keyed[kind])
        return (list(value) if isinstance(value, dict) else []), None
    if kind == "spec-coverage":
        return list(state.get("requirements", {})), None
    if kind == "constitution-check":
        return list(state.get("clauses", {})), None
    if kind == "diff-hygiene":
        return list(state["files"]), None
    return [], None


def _previous_step_evidence(root: Path, work_id: str | None, step: str | None) -> dict[str, str]:
    """Evidence the previous step was completed with, as ``{path: sha256}``.

    ``attested_outputs`` carries digests, not paths; the audit entry that
    completed the predecessor is the only record naming the files it rested on.
    """
    if not step or not work_id or not WORK_ID_RE.fullmatch(work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS",
                         "step-assessment needs --work-id, --step and --file")
    _path, state = read_development_state(root, resolve_development_item(root, work_id), work_id)
    development = state.get("development") or {}
    sequence = development_sequence(development) or []
    if step not in sequence or sequence.index(step) == 0:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS",
                         f"{step} has no previous step; pass --file")
    previous = sequence[sequence.index(step) - 1]
    entries = [entry for entry in development.get("audit") or []
               if isinstance(entry, dict) and entry.get("step") == previous and entry.get("state") == "complete"]
    evidence = entries[-1].get("evidence") if entries else None
    if (development.get("steps", {}).get(previous) != "complete" or not isinstance(evidence, list) or not evidence
            or not all(isinstance(e, dict) and isinstance(e.get("path"), str) for e in evidence)):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STEP-ASSESSMENT-EVIDENCE-MISSING", previous)
    return {entry["path"]: entry.get("sha256") for entry in evidence}


def decide_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Answer typed workflow decisions through Jev, several kinds in one request.

    Read-only except for the calibration log and ``step-assessment --apply``,
    which writes the same ``step-inputs/<step>.json`` the agent would otherwise
    write by hand, and only when Jev cleared the threshold on every question.

    Without ``--file``, a step assessment reads the evidence the previous step
    was completed with, and refuses when any of it changed since.
    """
    jev = grill_core_module("jev")
    root = project_root(args.root)
    kinds = [k for k in args.kind.split(",") if k]
    refs: list[dict[str, str]] = []
    texts: dict[str, str] = {}
    expected: dict[str, str] = {}
    if not args.file and "step-assessment" in kinds:
        expected = _previous_step_evidence(root, args.work_id, args.step)
    for relative in args.file or list(expected):
        data = safe_read_regular_fd(root, root / relative)
        if relative in expected and hash_bytes(data) != expected[relative]:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STEP-ASSESSMENT-EVIDENCE-STALE", relative)
        refs.append({"path": Path(relative).as_posix(), "sha256": hash_bytes(data)})
        texts[Path(relative).as_posix()] = data.decode("utf-8", errors="replace")
    # Structured state: the spec and the constitution become named fields the
    # questions point at, instead of whole documents mixed with the diff.
    state: dict[str, Any] = {"files": texts}
    if "spec-coverage" in kinds:
        spec = "".join(texts.pop(p) for p in [p for p in texts if p.endswith("spec.md")])
        state["requirements"] = jev.requirements(spec)
    if "constitution-check" in kinds:
        text = "".join(texts.pop(p) for p in [p for p in texts if p.endswith("constitution.md")])
        state["clauses"] = {k: v for k, v in jev.clauses(text).items() if v}
    if args.step:
        state["step"] = args.step
    if args.context:
        state["context"] = json.loads(safe_read_regular_fd(root, root / args.context).decode("utf-8"))
    items: dict[str, list[str]] = {}
    policy: dict[str, Any] | None = None
    for kind in kinds:
        items[kind], kind_policy = _decide_items(jev, kind, state, root, args.work_id, args.step, bool(refs))
        policy = kind_policy or policy
    try:
        decisions = jev.decide_many(kinds, state, items, jev.Transport(), session_id=args.work_id)
    except jev.JevError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.detail) from exc
    if args.work_id and WORK_ID_RE.fullmatch(args.work_id):
        _jev_log(root, {"event": "decision", "work_id": args.work_id, "step": args.step, "files": refs,
                        "decisions": {k: {f: d[f] for f in ("model", "confidence", "decided", "hint")}
                                      for k, d in decisions.items()}})
    written = None
    step_decision = decisions.get("step-assessment")
    if step_decision and step_decision["decided_by"] == "jev" and args.apply:
        confidence = ", ".join(f"{k}={v:.2f}" for k, v in sorted(step_decision["confidence"].items()))
        assessment = {
            "schema": "grill-step-assessment/v1", "step": args.step,
            "new_how": step_decision["result"]["new_how"], "risks": step_decision["result"]["risks"],
            "justification": f"decided_by=jev model={step_decision['model']} confidence: {confidence}",
            "files": refs,
        }
        try:
            grill_core_module("agent_orchestration").validate_step_assessment(assessment, policy, args.step)
        except grill_core_module("agent_orchestration").OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STEP-ASSESSMENT-INVALID", str(exc)) from exc
        written = f".grill/work-items/{args.work_id}/step-inputs/{args.step}.json"
        if not (root / ".grill/work-items" / args.work_id).is_dir():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORK-ITEM-MISSING", args.work_id)
        data = (json.dumps(assessment, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        atomic_write(root, root / written, data)
    base = {"schema": "grill-decision/v1", "verdict": "OK", "files": refs, "written": written}
    if len(kinds) == 1:
        return {**base, **decisions[kinds[0]]}, EXIT_OK
    return {**base, "decisions": decisions}, EXIT_OK


def decide_label_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Record the agent's final answer for a kind; the ground truth for recalibration."""
    root = project_root(args.root)
    if not WORK_ID_RE.fullmatch(args.work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-WORK-ID", args.work_id)
    answers = json.loads(args.answers)
    if not isinstance(answers, dict) or not answers:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "--answers must be a non-empty JSON object")
    _jev_log(root, {"event": "label", "work_id": args.work_id, "kind": args.kind, "step": args.step,
                    "answers": answers})
    return {"schema": "grill-decision-label/v1", "verdict": "OK", "log": JEV_LOG}, EXIT_OK


def preflight_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Report and optionally repair the environment without creating a work item."""
    root = project_root(args.root)
    payload = {
        "schema": "grill-preflight/v1",
        "workflow": ensure_project_workflow(root),
        "runtime": args.runtime,
        "dependencies": dependency_report(root, runtime=args.runtime, allow_install=args.allow_install,
                                          remove_shadows=getattr(args, "remove_shadows", False)),
    }
    if not args.skip_backlog:
        payload["backlog"] = backlog_report(root, apply=args.allow_install, db=getattr(args, "db", None))
    payload["verdict"] = payload["dependencies"].get("verdict", "BLOCKED")
    if payload["dependencies"].get("code"):
        payload["code"] = payload["dependencies"]["code"]
    try:
        payload["presentation"] = _session_readiness(
            root, args.runtime, args.session_ref, work_id=None)["presentation"]
    except CliFailure as exc:
        payload["verdict"], payload["code"] = "BLOCKED", exc.code
        if exc.extra and isinstance(exc.extra.get("presentation"), dict):
            payload["presentation"] = exc.extra["presentation"]
    try:
        require_openrouter_key()
    except CliFailure as exc:
        payload["verdict"], payload["code"] = "BLOCKED", exc.code
    return _with_coordinator_response(payload, args.runtime), EXIT_OK if payload["verdict"] == "OK" else EXIT_BLOCKED


# A spec reference that does not resolve is a routing failure, not a missing
# evidence file: the operator pointed `bugfix` at a spec that is not there, and
# `EVIDENCE-MISSING` would send them looking at the report instead.
SPEC_REF_FAILURES = {"EVIDENCE-MISSING", "EVIDENCE-NOT-REGULAR"}


def triage_evidence(
    root: Path,
    relative: str,
    *,
    decode: bool,
    missing_code: str | None = None,
) -> tuple[dict[str, str], str | None]:
    """Read one evidence file below ``root`` and fingerprint the bytes actually read.

    Goes through :func:`safe_read_regular_fd`, so an absolute path, a ``..``
    component or any symlink in the chain is refused before the open, and the
    object hashed is the object read.
    """
    target = root / relative
    try:
        data = safe_read_regular_fd(root, target)
    except CliFailure as failure:
        if missing_code is not None and failure.code in SPEC_REF_FAILURES:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", missing_code, str(target)) from failure
        raise
    reference = {"path": Path(relative).as_posix(), "sha256": hash_bytes(data)}
    if not decode:
        return reference, None
    try:
        return reference, data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CliFailure(
            EXIT_BLOCKED, "BLOCKED", "TRIAGE-REPORT-INVALID", "report is not valid UTF-8"
        ) from exc


def triage_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Seal a routing decision derived from a proven root-cause report.

    Pre-cycle like :func:`preflight_command`: it runs before any work item
    exists, so it takes no work-item lock and reads no bundle. Preview-first
    like every other mutating command here -- without ``--apply`` it computes
    the entire record and writes nothing.

    The record lands in ``.grill/triage/``, never ``.grill/global/``, so it is
    outside the projection ``snapshot_global`` guards and cannot trip
    ``GLOBAL-MUTATION``.
    """
    triage = grill_core_module("triage")
    root = project_root(args.root)
    try:
        report, text = triage_evidence(root, args.report, decode=True)
        parsed = triage.parse_report(text)
        triage.require_proven(parsed)
        spec_ref = None
        if args.spec_ref:
            spec_ref, _ = triage_evidence(
                root, args.spec_ref, decode=False, missing_code="SPEC-REF-NOT-FOUND"
            )
        scope = validate_scope(args.scope) if args.scope else []
        triage.check_route_evidence(
            args.route,
            severity=args.severity,
            production_impact=args.production_impact,
            spec_ref=spec_ref,
            scope=scope,
            rollback=args.rollback,
        )
        record = triage.seal(
            triage.build_record(
                triage_id=args.triage_id or f"tri-{uuid.uuid4().hex}",
                route=args.route,
                severity=args.severity,
                production_impact=args.production_impact,
                report=report,
                spec_ref=spec_ref,
                scope=scope,
                rollback=args.rollback,
                recorded_at_commit=git_optional(root, "rev-parse", "HEAD") or None,
            )
        )
    except triage.TriageError as error:
        raise_from_triage_error(error)
    payload: dict[str, Any] = {
        "schema": triage.SCHEMA,
        "triage_id": record["triage_id"],
        "route": record["route"],
        "report_status": parsed["status"],
        "record": record,
        "written": False,
    }
    if not args.apply:
        payload["verdict"] = "TRIAGE-PREVIEW"
        return payload, EXIT_OK
    target = root / ".grill/triage" / f"{record['triage_id']}.json"
    if target.exists():
        existing = json.loads(safe_read_regular_fd(root, target).decode("utf-8"))
        try:
            body = triage.verify_seal(existing)
        except triage.TriageError as error:
            raise_from_triage_error(error)
        if body != {key: value for key, value in record.items() if key != "triage_sha256"}:
            raise CliFailure(
                EXIT_BLOCKED, "BLOCKED", "TRIAGE-IDENTITY-DIVERGENCE", record["triage_id"]
            )
        payload["verdict"] = "REUSED"
        return payload, EXIT_OK
    payload["written"] = atomic_write(root, target, canonical(record))
    payload["verdict"] = "TRIAGE-RECORDED"
    return payload, EXIT_OK


def write_state_field(item: Path, key: str, value: Any) -> None:
    """Set or drop one field of state.json, atomically."""
    path = item / "state.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    if value is None:
        state.pop(key, None)
    else:
        state[key] = value
    staging = path.with_name(f".{path.name}.staging")
    staging.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    staging.replace(path)


def stamp_backlog_skipped(item: Path) -> None:
    """Record that this bundle was created without a bound backlog.

    Without the stamp a bundle created through the escape hatch would be
    indistinguishable from a compliant one, and the gate would end up
    asserting a prerequisite it never checked.
    """
    write_state_field(item, "backlog_skipped", True)


def backlog_adopt_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Clear the escape stamp once the repository is actually bound.

    Without this the escape hatch would be a cell: a bundle created without a
    backlog could never reach approval, even after being bound.
    """
    root = project_root(args.root)
    item = root / ".grill" / "work-items" / args.work_id
    bundle = read_local_bundle(root, item)
    validate_metadata(bundle.metadata, args.work_id)
    report = backlog_report(root, apply=args.apply, db=getattr(args, "db", None))
    if not backlog_is_bound(report):
        return {"schema": "grill-backlog/v1", "work_id": args.work_id, "verdict": "BLOCKED",
                "code": "BACKLOG-REQUIRED", "backlog": report,
                "detail": "vincule o backlog antes de limpar o carimbo"}, EXIT_BLOCKED
    state = json.loads((item / "state.json").read_text(encoding="utf-8"))
    if not state.get("backlog_skipped"):
        return {"schema": "grill-backlog/v1", "work_id": args.work_id, "verdict": "OK",
                "code": "NOTHING-TO-ADOPT", "backlog": report, "changed": False}, EXIT_OK
    write_state_field(item, "backlog_skipped", None)
    return {"schema": "grill-backlog/v1", "work_id": args.work_id, "verdict": "APPLIED",
            "backlog": report, "changed": True}, EXIT_OK


def backlog_sync_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Mirror every BL of one work item into the bound backlog, preview-first."""
    root = project_root(args.root)
    item = root / ".grill" / "work-items" / args.work_id
    bundle = read_local_bundle(root, item)
    # Identity, not artifact hashes: this command exists to read
    # DECISION-BACKLOG.md, which the protocol requires to change. Gating on
    # initial_artifacts made the precondition and the purpose mutually
    # exclusive. Tamper evidence of the immutable block is what still matters.
    validate_metadata(bundle.metadata, args.work_id)
    bridge = sibling("backlog_bridge")
    try:
        payload = bridge.sync_items(root, item, args.work_id, apply=args.apply, db=args.db)
    except bridge.BacklogUnavailable as error:
        return {"schema": bridge.SCHEMA, "db": bridge.store_path(args.db), "verdict": "BLOCKED",
                "code": "BACKLOG-UNAVAILABLE", "detail": str(error)}, EXIT_BLOCKED
    return payload, EXIT_OK if payload.get("verdict") in {"PREVIEW", "APPLIED"} else EXIT_BLOCKED


def _projection_command(args: argparse.Namespace, operation: str) -> tuple[dict[str, Any], int]:
    """Shared entry for project and verify: same gates, different verb."""
    root = project_root(args.root)
    item = root / ".grill" / "work-items" / args.work_id
    bundle = read_local_bundle(root, item)
    validate_metadata(bundle.metadata, args.work_id)
    bridge = sibling("backlog_bridge")
    try:
        if operation == "project":
            if bridge.bundle_mode(item) == "authored":
                # Mutating the projection of an authored bundle would silently
                # discard the hand-written record. Migration is the supported
                # path, and it needs explicit authorisation.
                return {"schema": bridge.PROJECTION_FORMAT, "db": bridge.store_path(args.db),
                        "work_id": args.work_id, "verdict": "BLOCKED",
                        "code": "BACKLOG-MIGRATION-REQUIRED",
                        "detail": "rode backlog-migrate --apply antes de projetar"}, EXIT_BLOCKED
            payload = bridge.project(root, item, args.work_id, apply=args.apply, db=args.db)
        elif operation == "migrate":
            payload = bridge.migrate(root, item, args.work_id, apply=args.apply, db=args.db)
        else:
            payload = bridge.verify(root, item, args.work_id, db=args.db)
    except bridge.BacklogUnavailable as error:
        return {"schema": bridge.PROJECTION_FORMAT, "db": bridge.store_path(args.db),
                "work_id": args.work_id, "verdict": "BLOCKED", "code": "BACKLOG-UNAVAILABLE",
                "detail": str(error)}, EXIT_BLOCKED
    ok = payload.get("verdict") in {"PREVIEW", "APPLIED", "REUSED", "FRESH"}
    return payload, EXIT_OK if ok else EXIT_NO_GO if payload.get("verdict") == "DIVERGED" else EXIT_BLOCKED


def backlog_project_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    return _projection_command(args, "project")


def backlog_verify_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    return _projection_command(args, "verify")


def backlog_migrate_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    return _projection_command(args, "migrate")


def _orchestration_origin(root: Path, item: Path, work_id: str) -> dict[str, Any]:
    state_path, state = read_development_state(root, item, work_id)
    state_bytes = safe_read_regular_fd(root, state_path)
    bundle = read_local_bundle(root, item)
    return {
        "state_sha256": hash_bytes(state_bytes),
        "metadata_sha256": hash_bytes(canonical(bundle.metadata)),
        "activation": state.get("activation"), "campaign": state.get("attestation_campaign"),
        "lifecycle": bundle.metadata.get("lifecycle"),
        "worktree": {"root": str(root), "branch": git_optional(root, "branch", "--show-current") or "DETACHED"},
    }


def _leader_boundary(root: Path, runtime: str, session_ref: str, work_id: str | None):
    """The public CLI reads native Orca output; tests inject this transport."""
    agent_runtime = grill_core_module("agent_runtime")
    handle = os.environ.get("ORCA_TERMINAL_HANDLE")
    def read(argv: list[str]) -> bytes:
        if not handle:
            raise agent_runtime.RuntimeError("LEADER-ADAPTER-UNSUPPORTED")
        executable = os.environ.get("ORCA_CLI_COMMAND") or "orca"
        try:
            result = subprocess.run([executable, *argv], cwd=root, capture_output=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise agent_runtime.RuntimeError("LEADER-ADAPTER-UNAVAILABLE") from exc
        if result.returncode:
            raise agent_runtime.RuntimeError("LEADER-ADAPTER-UNAVAILABLE")
        return result.stdout
    return agent_runtime.LeaderBoundary(session_ref, root, runtime, handle, read)


def _takeover_observation(root: Path, runtime: str, session_ref: str) -> tuple[dict[str, Any], str | None, dict[str, Any] | None]:
    """Observe predecessor termination through the same read transport as _leader_boundary.

    agent_runtime.observe_predecessor_termination (T002) only returns the
    verdict/reference/digest; U1/T003 need dispatch.status and liveness too,
    to tell an alive dispatch (TAKEOVER-LEADER-ACTIVE) apart from every other
    inconclusive case (TAKEOVER-EVIDENCE-UNPROVEN). Capture the raw response
    as a side effect of the same read() call instead of reading twice.
    """
    agent_runtime = grill_core_module("agent_runtime")
    handle = os.environ.get("ORCA_TERMINAL_HANDLE")
    captured: dict[str, bytes] = {}
    def read(argv: list[str]) -> bytes:
        if not handle:
            raise agent_runtime.RuntimeError("LEADER-ADAPTER-UNSUPPORTED")
        executable = os.environ.get("ORCA_CLI_COMMAND") or "orca"
        try:
            result = subprocess.run([executable, *argv], cwd=root, capture_output=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise agent_runtime.RuntimeError("LEADER-ADAPTER-UNAVAILABLE") from exc
        if result.returncode:
            raise agent_runtime.RuntimeError("LEADER-ADAPTER-UNAVAILABLE")
        captured["raw"] = result.stdout
        return result.stdout
    observation = agent_runtime.observe_predecessor_termination(session_ref, read)
    status: str | None = None
    liveness: dict[str, Any] | None = None
    raw = captured.get("raw")
    dispatch_id = session_ref.removeprefix("orca:") if isinstance(session_ref, str) else None
    if raw is not None:
        try:
            # Same envelope the adapter already unwraps ({"ok": true, "result": {...}});
            # reuse it instead of reading show.get(...) off the raw top level.
            show = agent_runtime._object(raw, "Orca worker-show")
        except Exception:
            show = None
        if isinstance(show, dict):
            dispatch = show.get("dispatch")
            if isinstance(dispatch, dict) and dispatch.get("id") == dispatch_id and isinstance(dispatch.get("status"), str):
                status = dispatch["status"]
            projection = show.get("projection")
            candidate = projection.get("liveness") if isinstance(projection, dict) else None
            if isinstance(candidate, dict) and isinstance(candidate.get("verdict"), str):
                liveness = {"verdict": candidate["verdict"], "source": candidate.get("source")}
    return observation, status, liveness


def _session_readiness(root: Path, runtime: str, session_ref: str | None, *,
                       work_id: str | None) -> dict[str, Any]:
    """Read one adapter observation and derive presentation at the CLI boundary."""
    policy_path = _policy_path(root, work_id)
    policy_raw = policy_path.read_bytes()
    gwd_raw = (ASSETS.parent / "SKILL.md").read_bytes()
    agent_runtime = grill_core_module("agent_runtime")
    def unobserved() -> dict[str, Any]:
        dependencies = sibling("ensure_dependencies")
        status, version, source, _reason = dependencies.plugin_registry_state(
            {"id": "i-have-adhd", "plugin": "i-have-adhd", "marketplace": "i-have-adhd", "min": "0.3.0"},
            dependencies.Toolchain(), runtime)
        return agent_runtime.presentation_state(
            policy=json.loads(policy_raw), policy_sha256=hash_bytes(policy_raw),
            gwd_skill_sha256=hash_bytes(gwd_raw), runtime=runtime,
            session_identity="unobserved", config_fingerprint="unobserved",
            scope={"kind": "gwd", "root": str(root), "work_id": work_id},
            installation={"status": status, "version": version, "manifest_ref": source},
            enablement=None, trust=None)
    if not isinstance(session_ref, str) or not session_ref:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", "--session-ref is required",
                         extra={"presentation": unobserved()})
    try:
        observed, presentation = agent_runtime.project_leader_presentation(
            _leader_boundary(root, runtime, session_ref, work_id),
            policy=json.loads(policy_raw), policy_sha256=hash_bytes(policy_raw),
            gwd_skill_sha256=hash_bytes(gwd_raw), runtime=runtime,
            scope={"kind": "gwd", "root": str(root), "work_id": work_id})
    except agent_runtime.PresentationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", str(exc), "presentation evidence is not correlated") from exc
    except agent_runtime.RuntimeError as exc:
        code = str(exc) if str(exc).startswith("LEADER-") else "LEADER-AUTHORITY-UNPROVEN"
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, str(exc), extra={"presentation": unobserved()}) from exc
    scope = presentation["scope"]
    if (scope.get("kind") != "gwd" or scope.get("root") != str(root)
            or work_id is not None and scope.get("work_id") != work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STYLE-SCOPE-CONFLICT", "presentation scope is not current")
    if not presentation["work_ready"]:
        codes = [entry.get("code") for entry in presentation["diagnostics"]
                 if isinstance(entry, dict) and isinstance(entry.get("code"), str)]
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", codes[0] if codes else "STYLE-LOAD-UNCONFIRMED",
                         "presentation is not ready", extra={"presentation": presentation})
    return {"ref": session_ref, "sha256": observed["source_sha256"],
            "incarnation": observed["incarnation"], "presentation": presentation}


def _require_current_leader(root: Path, work_id: str, context: dict[str, Any], session_ref: str,
                            readiness: dict[str, Any] | None = None) -> None:
    """Reuse the work observation; cleanup/switch reobserve without presentation."""
    if readiness is None:
        runtime = grill_core_module("agent_runtime")
        try:
            observed = _leader_boundary(root, context["runtime"], session_ref, work_id).observe()
        except runtime.RuntimeError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
        readiness = {"ref": observed["source_ref"], "sha256": observed["source_sha256"], "incarnation": observed["incarnation"]}
    if any(context["leader"].get(key) != readiness[field] for key, field in (
            ("session_ref", "ref"), ("observation_ref", "ref"),
            ("observation_sha256", "sha256"), ("incarnation", "incarnation"))):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", "current leader changed")


def _require_released_leader(root: Path, work_id: str, context: dict[str, Any], session_ref: str) -> dict[str, Any]:
    runtime = grill_core_module("agent_runtime")
    try:
        observed = _leader_boundary(root, context["runtime"], session_ref, work_id).observe_released(
            allow_unarchived_stopped=True)
    except runtime.RuntimeError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-RELEASE-UNPROVEN", str(exc)) from exc
    if (context["leader"].get("session_ref") != observed["source_ref"]
            or context["leader"].get("incarnation") != observed["incarnation"]):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-RELEASE-UNPROVEN", "released leader changed")
    return observed


def _orchestration_inputs(root: Path, work_id: str, runtime: str, session_ref: str | None,
                          scope_files: list[str], readiness: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
    item = resolve_development_item(root, work_id)
    contract = grill_core_module("agent_orchestration")
    readiness = readiness or _session_readiness(root, runtime, session_ref, work_id=work_id)
    try:
        inputs = contract.adoption_inputs(work_id=work_id, runtime=runtime, session_ref=session_ref,
                                          session_observation={key: readiness[key] for key in ("ref", "sha256", "incarnation")},
                                          presentation=readiness["presentation"],
                                          scope_files=scope_files, origin=_orchestration_origin(root, item, work_id))
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ORCHESTRATION-ADOPTION", str(exc)) from exc
    return contract, inputs


def _initialize_orchestration(root: Path, work_id: str, runtime: str, session_ref: str | None,
                              readiness: dict[str, Any]) -> dict[str, Any]:
    """New init persists its observed session when supplied; it never invents one."""
    contract, inputs = _orchestration_inputs(root, work_id, runtime, session_ref, [], readiness)
    store = grill_core_module("store")
    policy = _policy_path(root, work_id)
    policy_bytes = policy.read_bytes()
    policy_ref = "assets/" + policy.name
    policy_sha256 = hash_bytes(policy_bytes)
    store.bootstrap(root)
    try:
        snapshot = store.transact(root, lambda document: _bind_orchestration(
            document, work_id, contract.new_work_item(inputs, policy_ref=policy_ref,
            policy_sha256=policy_sha256, adopted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            context_id=f"ctx-{contract.adoption_sha256(inputs)[:12]}" if session_ref else None)))
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.message) from exc
    return {"store_revision": snapshot.revision, "orchestration": "INITIALIZED",
            "presentation": readiness["presentation"]}


def _bind_orchestration(document: dict[str, Any], work_id: str, item: dict[str, Any]) -> dict[str, Any]:
    block = document.get("agent_orchestration")
    if block is None:
        document["agent_orchestration"] = {"schema": "grill-agent-orchestration/v1", "work_items": {work_id: item}}
        return document
    existing = block["work_items"].get(work_id)
    if existing is None:
        block["work_items"][work_id] = item
    else:
        current = existing["contexts"].get(existing["current_context_id"])
        incoming = item["contexts"][item["current_context_id"]]
        if not _same_observed_leader(current, incoming):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTEXT-FENCED", "existing leader observation differs")
        current["presentation"] = incoming["presentation"]
    return document


def _same_observed_leader(current: Any, incoming: dict[str, Any]) -> bool:
    return (isinstance(current, dict) and current.get("state") == "ACTIVE"
            and current.get("leader", {}).get("state") == "ACTIVE"
            and current.get("runtime") == incoming["runtime"]
            and all(current.get("leader", {}).get(key) == incoming["leader"][key]
                    for key in ("session_ref", "incarnation", "observation_ref", "observation_sha256")))


def _adoption_conflict(root: Path, work_id: str, inputs: dict[str, Any], policy_sha256: str,
                       incoming: dict[str, Any]) -> tuple[Any, dict[str, Any] | None]:
    """Read the existing binding and enforce the write-once/leader checks the
    apply mutate() closure already applies. T006/FR-007: the preview must
    raise the same refusal the apply would, not just when applying."""
    store = grill_core_module("store")
    existing_snapshot = store.read_snapshot(root, required=False)
    if existing_snapshot is None:
        return None, None
    existing = existing_snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(work_id)
    if not isinstance(existing, dict):
        return existing_snapshot, None
    if existing.get("policy_sha256") != policy_sha256:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", "adoption source changed")
    current = existing.get("contexts", {}).get(existing.get("current_context_id"))
    if current is not None and not _same_observed_leader(current, incoming):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTEXT-FENCED", "existing context has different runtime or session")
    # Merge note (main 6.0.11): a changed origin is no longer refused outright.
    # The apply closure below refreshes `presentation` in place when a current
    # context exists and the declared scope is unchanged, so mirroring the
    # refusal here means mirroring that exception too -- otherwise the preview
    # is stricter than the apply, which is the inversion this helper exists to
    # prevent. The order matches the apply: policy digest, then leader fence,
    # then origin.
    if existing.get("origin") != inputs["origin"] and (
            current is None or existing.get("scope_files") != inputs["scope_files"]):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", "adoption source changed")
    return existing_snapshot, existing


def orchestration_adopt_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    contract, inputs = _orchestration_inputs(root, args.work_id, args.runtime, args.session_ref, args.scope_file or [])
    expected = contract.adoption_sha256(inputs)
    policy = _policy_path(root, args.work_id)
    policy_bytes = policy.read_bytes()
    policy_ref, policy_sha256 = "assets/" + policy.name, hash_bytes(policy_bytes)
    context_id = f"ctx-{expected[:12]}"
    candidate = contract.new_work_item(inputs, policy_ref=policy_ref, policy_sha256=policy_sha256,
        adopted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), context_id=context_id)
    incoming = candidate["contexts"][candidate["current_context_id"]]
    existing_snapshot, existing = _adoption_conflict(root, args.work_id, inputs, policy_sha256, incoming)
    preview = {"verdict": "PREVIEW", "work_id": args.work_id, "expected_sha256": expected,
               "origin": inputs["origin"], "scope_files": inputs["scope_files"],
               "presentation": inputs["presentation"],
               "limitations": ["does not rewrite legacy state, activation, campaign or receipts"]}
    if not args.apply:
        return preview, EXIT_OK
    if args.expected_sha256 != expected:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", "expected_sha256 does not match reread adoption inputs")
    store = grill_core_module("store")
    if isinstance(existing, dict):
        current = existing.get("contexts", {}).get(existing.get("current_context_id"))
        # T064/FR-010: origin equality must gate REUSED, matching the apply
        # closure's precedence below. _adoption_conflict already guarantees
        # policy_sha256 equality and leader-fence agreement unconditionally
        # before this point -- neither has the origin-changed exception, so
        # both always raise on mismatch regardless of scope/current. Origin
        # is the one check _adoption_conflict now lets through when a changed
        # origin comes with an existing context and unchanged scope (main
        # 6.0.11 loosening), so it is the only one this shortcut must repeat:
        # otherwise that exact input reads as an identical repeat here while
        # the apply closure below still treats it as a live origin change.
        if (existing.get("origin") == inputs["origin"] and existing.get("scope_files") == inputs["scope_files"]
                and current is not None and current.get("presentation") == inputs["presentation"]):
            return {"verdict": "REUSED", "work_id": args.work_id, "context_id": existing["current_context_id"],
                    "expected_sha256": expected, "store_revision": existing_snapshot.revision}, EXIT_OK
    store.bootstrap(root)
    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        block = document.get("agent_orchestration")
        if block is None or args.work_id not in block["work_items"]:
            return _bind_orchestration(document, args.work_id, contract.new_work_item(
                inputs, policy_ref=policy_ref, policy_sha256=policy_sha256,
                adopted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), context_id=context_id))
        item = block["work_items"][args.work_id]
        if item["policy_sha256"] != policy_sha256:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", "adoption source changed")
        current = item.get("contexts", {}).get(item.get("current_context_id"))
        if current is not None and not _same_observed_leader(current, incoming):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTEXT-FENCED", "existing context has different runtime or session")
        if item["origin"] != inputs["origin"]:
            if current is None or item["scope_files"] != inputs["scope_files"]:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", "adoption source changed")
            current["presentation"] = inputs["presentation"]
            return document
        if current is not None:
            current["presentation"] = inputs["presentation"]
        if item["scope_files"] != inputs["scope_files"]:
            item["scope_revision"] += 1
            item["scope_files"] = inputs["scope_files"]
            item["scope_history"].append({"revision": item["scope_revision"], "files": inputs["scope_files"],
                                          "inputs_sha256": expected})
        if current is None:
            replacement = contract.new_work_item(inputs, policy_ref=policy_ref, policy_sha256=policy_sha256,
                                                 adopted_at=item["adopted_at"], context_id=context_id)
            replacement["scope_revision"], replacement["scope_history"] = item["scope_revision"], item["scope_history"]
            block["work_items"][args.work_id] = replacement
        return document
    try:
        snapshot = store.transact(root, mutate)
    except CliFailure:
        raise
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.message) from exc
    committed_context_id = snapshot.document["agent_orchestration"]["work_items"][args.work_id]["current_context_id"]
    return {"verdict": "ORCHESTRATION-ADOPTED", "work_id": args.work_id, "context_id": committed_context_id,
            "expected_sha256": expected, "store_revision": snapshot.revision}, EXIT_OK


def _checkpoint_ref(root: Path, value: str | None) -> dict[str, str] | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-EVIDENCE-PATH", value)
    full = root / path
    if not full.is_file() or full.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "EVIDENCE-MISSING", value)
    return {"ref": path.as_posix(), "sha256": hash_bytes(safe_read_regular_fd(root, full))}


def _cleanup_checkpoint_projection(root: Path, work_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Capture already-known cleanup obligations without probing or mutating."""
    gauntlet_runs = grill_core_module("gauntlet_runs")
    projection = gauntlet_runs.cleanup_projection(root, work_id)
    pending = {
        f"{entry['run_id']}:{entry['worker_id']}": entry
        for entry in projection["pending"]
    }
    preserved = {
        f"{entry['run_id']}:{entry['worker_id']}": entry
        for entry in projection["preserved"]
    }
    return pending, preserved


def _commit_orchestrated_checkpoint(root: Path, state_path: Path, state_before: bytes,
                                    state: dict[str, Any], args: argparse.Namespace,
                                    payload: dict[str, Any]) -> dict[str, Any] | None:
    """Use the v2 Store WAL only for an already-adopted work item.

    Legacy checkpoints keep their established bytes and transition behavior;
    an adopted item must provide a stable operation id and the bound session.
    """
    store = grill_core_module("store")
    snapshot = store.read_snapshot(root, required=False)
    if snapshot is None:
        return None
    block = snapshot.document.get("agent_orchestration")
    item = block.get("work_items", {}).get(args.work_id) if isinstance(block, dict) else None
    if item is None:
        return None
    if not getattr(args, "operation_id", None):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "OPERATION-ID-REQUIRED", args.work_id)
    if not getattr(args, "session_ref", None):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", "session_ref is required")
    contract = grill_core_module("agent_orchestration")
    context_id = item.get("current_context_id")
    context = item.get("contexts", {}).get(context_id)
    try:
        if not isinstance(context, dict):
            raise contract.OrchestrationError("no current context")
        contract.require_authority(item, context_id, context["epoch"], args.session_ref)
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
    existing = item.get("operations", {}).get(args.operation_id)
    prior_origin = existing.get("request", {}).get("store_origin") if isinstance(existing, dict) else None
    evidence = sorted(({"path": record["path"], "sha256": record["sha256"]} for record in payload["evidence"]), key=lambda record: record["path"])
    request = contract.checkpoint_request(
        store_origin=prior_origin if isinstance(prior_origin, dict) else {"revision": snapshot.revision, "content_sha256": snapshot.content_sha256},
        work_id=args.work_id, operation_id=args.operation_id, context_id=context_id,
        step=args.step, state=args.state, evidence=evidence, reason=payload["reason"],
        attestation=_checkpoint_ref(root, args.attestation),
        supersedes_attestation=_checkpoint_ref(root, args.supersedes_attestation),
        initialize_legacy=bool(args.initialize_legacy), from_step=args.from_step,
    )
    if existing is not None:
        if existing.get("request") != request:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "OPERATION-ID-COLLISION", args.operation_id)
        if existing.get("state") != "CONFIRMED" or not isinstance(existing.get("content_ref"), str):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "OPERATION-RECOVERY-REQUIRED", args.operation_id)
        content_path = root / existing["content_ref"]
        try:
            content = json.loads(safe_read_regular_fd(root, content_path).decode("utf-8"))
            contract.validate_checkpoint_content(content)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, contract.OrchestrationError) as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CHECKPOINT-CONTENT-INVALID", args.operation_id) from exc
        if contract.checkpoint_content_sha256(content) != existing.get("result_sha256"):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CHECKPOINT-CONTENT-INVALID", args.operation_id)
        return {"verdict": "REUSED", "work_id": args.work_id, **content["result"], "store_revision": snapshot.revision}
    accepted_campaign = _checkpoint_campaign(item, context, state, args.work_id)
    state_after = (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    relative_state = state_path.relative_to(root).as_posix()
    checkpoint_id = "cp-" + store.jcs_sha256({"store_origin": request["store_origin"], "work_id": args.work_id, "operation_id": args.operation_id})
    cleanup_obligations, preserved_resources = _cleanup_checkpoint_projection(root, args.work_id)
    checkpoint = {
        "schema": contract.CHECKPOINT_SCHEMA_V2, "checkpoint_id": checkpoint_id, "context_id": context_id,
        "previous_checkpoint_id": item.get("checkpoint_head"), "worktree_identity": context.get("worktree_identity", {}),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "store_revision": snapshot.revision + 1,
        "journal_anchor": snapshot.document["journal_head"], "state_sha256": hash_bytes(state_after),
        "inputs_manifest": {"evidence": evidence}, "context_inputs_sha256": context["inputs_sha256"],
        "origin_metadata_sha256": item["origin"]["metadata_sha256"], "policy_sha256": item["policy_sha256"],
        "activation": context["activation"], "campaign": accepted_campaign,
        "development_sequence": state.get("development", {}).get("sequence", []),
        "current_step": state.get("development", {}).get("current_step"), "step_states": state.get("development", {}).get("steps", {}),
        "accepted_outputs": state.get("development", {}).get("attested_outputs", {}),
        "accepted_executions": state.get("development", {}).get("attested_executions", {}),
        "pending_attempts": {}, "scheduler_runs": context["scheduler_runs"], "operations": item["operations"],
        "cleanup_obligations": cleanup_obligations, "preserved_resources": preserved_resources,
        "blocking_activity": None, "visual_state": {},
        "presentation": context.get("presentation"), "checkpoint_sha256": "",
    }
    checkpoint["checkpoint_sha256"] = store.jcs_sha256({key: value for key, value in checkpoint.items() if key != "checkpoint_sha256"})
    import base64
    state_write = {"work_id": args.work_id, "destination": relative_state, "before_sha256": hash_bytes(state_before),
                   "after_base64": base64.b64encode(state_after).decode("ascii"), "after_sha256": hash_bytes(state_after),
                   "expected_store_revision": snapshot.revision, "expected_journal_anchor": snapshot.document["journal_head"]}
    result = {"work_id": args.work_id, "context_id": context_id, "epoch": context["epoch"], "operation_id": args.operation_id,
              "checkpoint_id": checkpoint_id, "step": args.step, "state": args.state, "evidence": evidence,
              "reason": payload["reason"], "execution_branch": payload.get("execution_branch"),
              "supersedes": _checkpoint_ref(root, args.supersedes_attestation),
              "current_step": state.get("development", {}).get("current_step")}
    content = {"schema": contract.CHECKPOINT_CONTENT_SCHEMA, "work_id": args.work_id, "operation_id": args.operation_id,
               "request": request, "checkpoint": checkpoint, "before_base64": base64.b64encode(state_before).decode("ascii"),
               "state_write": state_write, "binding_transition": None, "result": result}
    digest = contract.checkpoint_content_sha256(content)
    content_ref = f".grill/work-items/{args.work_id}/agent-orchestration/checkpoints/{args.operation_id}.json"
    operation = {"kind": "checkpoint", "context_id": context_id, "fence": context["leader"]["fence"], "subject_ids": [relative_state],
                 "input_sha256": store.jcs_sha256(request), "expected_before": {"state_sha256": state_write["before_sha256"]},
                 "intended_after": {"state_sha256": state_write["after_sha256"]}, "idempotency_key": args.operation_id,
                 "state": "CONFIRMED", "result_ref": content_ref, "result_sha256": digest, "observation_ref": content_ref,
                 "error": None, "request": request, "content_ref": content_ref}
    receipt = {"schema": "grill-orchestration-receipt/v1", "category": "runtime", "name": "checkpoint-" + checkpoint_id,
               "work_id": args.work_id, "context_id": context_id, "operation_id": args.operation_id,
               "input_sha256": operation["input_sha256"], "output_sha256": digest}
    event = {"schema": "grill-orchestration-event/v1", "event": "agent.orchestration.checkpoint", "work_id": args.work_id,
             "context_id": context_id, "operation_id": args.operation_id, "input_sha256": operation["input_sha256"],
             "output_sha256": digest, "receipt_sha256": store.jcs_sha256(receipt)}
    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        target = document["agent_orchestration"]["work_items"][args.work_id]
        if args.operation_id in target["operations"]:
            raise store.StoreError(store.STATE_DIVERGENCE, "checkpoint operation appeared during commit")
        target["operations"][args.operation_id] = operation
        target_context = target["contexts"][context_id]
        if target_context["campaign"] is None and accepted_campaign is not None:
            target_context["campaign"] = accepted_campaign
        elif target_context["campaign"] != accepted_campaign:
            raise store.StoreError(store.STATE_DIVERGENCE, "checkpoint campaign changed before commit")
        target["checkpoints"][checkpoint_id] = checkpoint
        target["checkpoint_head"] = checkpoint_id
        return document
    try:
        committed = store.transact_checkpoint_with_content(root, mutate, event=event, receipt=receipt,
                                                           content_ref=content_ref, content=content)
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.message) from exc
    return {"verdict": "UPDATED", "work_id": args.work_id, **result, "store_revision": committed.revision}


def _checkpoint_campaign(item: dict[str, Any], context: dict[str, Any],
                         state: dict[str, Any], work_id: str) -> dict[str, Any] | None:
    """Advance development state only across validated continuity bridges."""
    accepted = context["campaign"]
    development = state.get("development", {})
    current = development.get("attestation_campaign") if isinstance(development, dict) else None
    if accepted is None and isinstance(current, dict):
        return current
    if accepted is None or not isinstance(current, dict) or accepted == current:
        return accepted
    cursor = context
    visited: set[str] = set()
    while isinstance(cursor, dict) and cursor.get("campaign") != current:
        continuity_ref = cursor.get("continuity_ref")
        if not isinstance(continuity_ref, str) or continuity_ref in visited:
            break
        visited.add(continuity_ref)
        operation = item.get("operations", {}).get(continuity_ref, {})
        bridge = operation.get("intended_after", {}).get("campaign_bridge") if isinstance(operation, dict) else None
        if not isinstance(bridge, dict) or bridge.get("to_campaign") != cursor.get("campaign"):
            break
        if bridge.get("from_campaign") == current:
            development["attestation_campaign"] = copy.deepcopy(accepted)
            return accepted
        predecessor = item.get("contexts", {}).get(cursor.get("predecessor_context_id"))
        if not isinstance(predecessor, dict) or predecessor.get("campaign") != bridge.get("from_campaign"):
            break
        cursor = predecessor
    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CHECKPOINT-CAMPAIGN-DIVERGENT", work_id)


def init_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if args.type not in KINDS or not SLUG_RE.fullmatch(args.slug):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-IDENTITY", "type or slug invalid")
    work_id = args.work_id or f"{args.type}-{args.slug}-{uuid.uuid4().hex}"
    if not WORK_ID_RE.fullmatch(work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-WORK-ID", work_id)
    require_openrouter_key()
    readiness = _session_readiness(root, args.runtime, args.session_ref, work_id=work_id)
    workflow = ensure_project_workflow(root)
    goal = ensure_project_goal(root)
    dependencies = dependency_report(
        root, runtime=args.runtime, allow_install=getattr(args, "allow_install", False)
    )
    if getattr(args, "require_dependencies", False) and dependencies.get("verdict") != "OK":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "MISSING-DEPENDENCY",
                         ",".join(dependencies.get("missing_required") or ["unknown"]))
    environment = {"workflow": workflow, "goal": goal, "runtime": args.runtime, "dependencies": dependencies,
                   **_coordinator_response(args.runtime)}
    skipped_backlog = bool(getattr(args, "skip_backlog", False))
    if not skipped_backlog:
        # Binding no longer waits for --allow-install: the prerequisite is the
        # bind itself, and gating it behind an install flag is what let every
        # consumer repository stay unbound while looking configured.
        # create=False: init binds to a backlog that already exists. Creating
        # one named after the root directory would satisfy the check by
        # inventing the very thing it is supposed to verify.
        environment["backlog"] = backlog_report(root, apply=True, create=False, db=getattr(args, "db", None))
        if not backlog_is_bound(environment["backlog"]):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "BACKLOG-REQUIRED",
                             environment["backlog"].get("code") or "no bound backlog")
    target = root / ".grill" / "work-items" / work_id
    lock = acquire_lock(root, work_id, target, reuse_if_target_exists=True)
    try:
        if target.exists():
            # T016b / data-model.md E4 "Alcance": a reencountered bundle's
            # state.json was sealed by another execution. It is read and
            # reported, never rewritten to carry the goal block -- mutating it
            # here would change the fingerprint of a bundle nobody asked to
            # change. The fixation this call just computed is still reported
            # via **environment below.
            bundle = read_local_bundle(root, target)
            immutable = validate_metadata(bundle.metadata, work_id)
            if immutable.get("type") != args.type or immutable.get("slug") != args.slug:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IDENTITY-DIVERGENCE", work_id)
            return {"status": "REUSED", "work_id": work_id, "path": str(target), "fingerprint": bundle.fingerprint,
                    **_initialize_orchestration(root, work_id, args.runtime, args.session_ref, readiness), **environment}, EXIT_OK
        constitution_created, constitution_hash = ensure_managed_constitution(root)
        immutable = immutable_metadata(root, args, work_id)
        files = initial_files(root, work_id, immutable, goal, backlog_skipped=skipped_backlog)
        metadata = metadata_document(immutable, files)
        staging = write_bundle_staging(root, work_id, metadata, files)
        try:
            rename_child(target.parent, staging, target)
        except OSError as exc:
            if exc.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
                raise
            shutil.rmtree(staging, ignore_errors=True)
            bundle = read_local_bundle(root, target)
            immutable = validate_metadata(bundle.metadata, work_id)
            if immutable.get("type") != args.type or immutable.get("slug") != args.slug:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IDENTITY-DIVERGENCE", work_id)
            return {"status": "REUSED", "work_id": work_id, "path": str(target), "fingerprint": bundle.fingerprint,
                    **_initialize_orchestration(root, work_id, args.runtime, args.session_ref, readiness), **environment}, EXIT_OK
        bundle = read_local_bundle(root, target)
        return {"status": "CREATED", "work_id": work_id, "path": str(target), "fingerprint": bundle.fingerprint,
                "constitution": "CREATED" if constitution_created else "PRESERVED", "constitution_sha256": constitution_hash,
                "backlog_skipped": skipped_backlog,
                **_initialize_orchestration(root, work_id, args.runtime, args.session_ref, readiness),
                **environment}, EXIT_OK
    finally:
        if lock is not None:
            shutil.rmtree(lock, ignore_errors=True)



def parse_test_command(command: str, *, platform: str | None = None) -> str | list[str]:
    """Prepare a command for shell=False using the host's native argument grammar."""
    return command if (platform or os.name) == "nt" else shlex.split(command)


def hotfix_go_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    item = root / ".grill" / "work-items" / args.work_id
    bundle = read_local_bundle(root, item)
    validate_bundle_integrity(bundle)
    hotfix = validated_hotfix(bundle)
    validate_hotfix_scope_changes(root, bundle)
    validate_constitution_check(root, bundle.files, bundle.metadata["immutable"].get("constitution", {}))
    command = hotfix.get("test-command")
    if not isinstance(command, str) or not command.strip():
        raise CliFailure(EXIT_NO_GO, "NO-GO", "TEST-COMMAND-MISSING", args.work_id)
    try:
        argv = parse_test_command(command)
    except ValueError as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "TEST-COMMAND-INVALID", str(exc)) from exc
    if not argv:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "TEST-COMMAND-MISSING", args.work_id)
    timeout = hotfix.get("test-timeout", 30)
    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-TEST-TIMEOUT", str(timeout))
    try:
        process = subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False, timeout=timeout, shell=False)
        output = ((process.stdout or "") + (process.stderr or ""))[:4096]
        if process.returncode != 0:
            return {"verdict": "NO-GO", "code": "CORRECTION-TEST-FAILED", "returncode": process.returncode, "output": output}, EXIT_NO_GO
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") if isinstance(exc.stdout, str) else "")[:4096]
        return {"verdict": "NO-GO", "code": "CORRECTION-TEST-TIMEOUT", "output": output}, EXIT_NO_GO
    return {"verdict": "HOTFIX-GO", "code": "HOTFIX-GO", "work_id": args.work_id, "test": {"returncode": 0, "output": output}}, EXIT_OK


def reconcile_resealed_activation(root: Path, bundle: ItemBundle, args: argparse.Namespace) -> dict[str, bool]:
    """Project the bundle reseal into Gauntlet; bound contexts remain write-once."""
    history = bundle.metadata.get("constitution_reseals")
    if not isinstance(history, list) or not history:
        return {"activation_reconciled": False, "continuity_required": False}
    latest = history[-1]
    check = bundle.files.get("CONSTITUTION-CHECK.md")
    current = bundle.metadata["immutable"].get("constitution")
    if (not isinstance(latest, dict) or latest.get("to") != current or check is None
            or latest.get("check_sha256") != hash_bytes(check)):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONSTITUTION-RESEAL-SCHEMA", args.work_id)
    raw = bundle.files["WORK-ITEM.json"]
    document_sha256 = hash_bytes(raw)
    gauntlet = grill_core_module("gauntlet")
    work_item_v3 = grill_core_module("work_item_v3")
    try:
        previous, activation, config_changed = gauntlet.reseal_work_item_activation(
            root=root, work_id=args.work_id, document_sha256=document_sha256, work_item_v3=work_item_v3)
    except gauntlet.GauntletError as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
    store = grill_core_module("gauntlet_runs").store
    snapshot = store.read_snapshot(root, required=False)
    block = snapshot.document.get("agent_orchestration") if snapshot is not None else None
    orchestrated = block.get("work_items", {}).get(args.work_id) if isinstance(block, dict) else None
    if not isinstance(orchestrated, dict):
        return {"activation_reconciled": config_changed, "continuity_required": False}
    contract = grill_core_module("agent_orchestration")
    context = orchestrated.get("contexts", {}).get(args.context_id)
    try:
        contract.require_authority(orchestrated, args.context_id, args.epoch, args.session_ref)
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
    if isinstance(context, dict) and context.get("activation") is None and activation is None:
        return {"activation_reconciled": config_changed, "continuity_required": False}
    if not isinstance(context, dict) or not isinstance(context.get("activation"), dict) or activation is None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IDENTITY-STALE", "resealed activation is unavailable")
    bound_sha256 = context["activation"].get("work_item", {}).get("document_sha256")
    if bound_sha256 == document_sha256:
        return {"activation_reconciled": config_changed, "continuity_required": False}
    if previous != document_sha256 and bound_sha256 != previous:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IDENTITY-STALE", "activation changed during reseal")
    return {"activation_reconciled": config_changed, "continuity_required": True}


def constitution_reseal_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Rebind a stale work item to the current Constitution under the leader fence."""
    root = project_root(args.root)
    if not isinstance(args.human_evidence, str) or not args.human_evidence.strip():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONSTITUTION-EVIDENCE-REQUIRED", "--human-evidence is required")
    item = root / ".grill" / "work-items" / args.work_id
    lock = acquire_lock(root, args.work_id, item) if args.apply else None
    try:
        bundle = read_local_bundle(root, item)
        immutable = validate_metadata(bundle.metadata, args.work_id)
        previous_check = bundle.files.get("CONSTITUTION-CHECK.md")
        if previous_check is None:
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CHECK-MISSING", "CONSTITUTION-CHECK.md")
        current, _text, clauses = constitution_info(root)
        if current.get("state") != "present":
            raise CliFailure(EXIT_CONSTITUTION, "BLOCKED-CONSTITUTION", "CONSTITUTION-NOT-PRESENT", args.work_id)
        recorded = immutable.get("constitution", {})
        if recorded.get("state") == current["state"] and recorded.get("sha256") == current["sha256"]:
            constitutional = validate_constitution_check(root, bundle.files, recorded)
            activation_status = reconcile_resealed_activation(root, bundle, args)
            return {"verdict": "REUSED", "code": "CONSTITUTION-ALREADY-SEALED", "work_id": args.work_id,
                    "constitutional": constitutional, **activation_status}, EXIT_OK
        check = constitution_reseal_check(current, clauses, args.human_evidence.strip())
        request = {
            "work_id": args.work_id, "bundle_fingerprint": bundle.fingerprint,
            "from": recorded, "to": current, "check_sha256": hash_bytes(check),
            "human_evidence": args.human_evidence.strip(), "context_id": args.context_id,
            "epoch": args.epoch, "session_ref": args.session_ref,
        }
        expected = hash_bytes(canonical(request))
        if not args.apply:
            return {"verdict": "PREVIEW", "code": "CONSTITUTION-RESEAL-READY", "work_id": args.work_id,
                    "from_sha256": recorded.get("sha256"), "to_sha256": current["sha256"],
                    "expected_sha256": expected}, EXIT_OK
        if args.expected_sha256 != expected:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONSTITUTION-RESEAL-STALE", "reseal inputs changed")
        files = {path: data for path, data in bundle.files.items() if path != "WORK-ITEM.json"}
        state_raw = files.get("state.json")
        try:
            state = json.loads(state_raw.decode("utf-8")) if state_raw is not None else None
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STATE-SCHEMA", args.work_id) from exc
        if not isinstance(state, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STATE-SCHEMA", args.work_id)
        state["constitution"] = current
        files["state.json"] = (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        files["CONSTITUTION-CHECK.md"] = check
        metadata = copy.deepcopy(bundle.metadata)
        previous_immutable_sha256 = metadata["immutable_sha256"]
        metadata["immutable"]["constitution"] = current
        metadata["immutable_sha256"] = hash_bytes(canonical(metadata["immutable"]))
        history = metadata.setdefault("constitution_reseals", [])
        if not isinstance(history, list):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONSTITUTION-RESEAL-SCHEMA", args.work_id)
        history.append({
            "schema": "grill-constitution-reseal/v1", "from": recorded, "to": current,
            "previous_immutable_sha256": previous_immutable_sha256,
            "immutable_sha256": metadata["immutable_sha256"],
            "previous_check_sha256": hash_bytes(previous_check),
            "check_sha256": hash_bytes(check), "human_evidence": args.human_evidence.strip(),
            "context_id": args.context_id, "epoch": args.epoch, "session_ref": args.session_ref,
        })
        validate_metadata(metadata, args.work_id)
        validate_constitution_check(root, {**files, "WORK-ITEM.json": b""}, metadata["immutable"]["constitution"])
        replace_work_item_bundle(root, item, metadata, files)
        activation_status = reconcile_resealed_activation(root, read_local_bundle(root, item), args)
        return {"verdict": "APPLIED", "code": "CONSTITUTION-RESEALED", "work_id": args.work_id,
                "from_sha256": recorded.get("sha256"), "to_sha256": current["sha256"],
                "expected_sha256": expected, **activation_status}, EXIT_OK
    finally:
        if lock is not None:
            shutil.rmtree(lock, ignore_errors=True)


def audit_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.project_root or args.root)
    # A guarda precisa vir antes de montar o caminho: `root / ... / None` levanta
    # TypeError, e um traceback não diz ao operador qual argumento faltou.
    if not args.artifact_root and not args.work_id:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "--work-id or --artifact-root is required")
    item = Path(os.path.abspath(args.artifact_root)) if args.artifact_root else root / ".grill" / "work-items" / args.work_id
    if item.is_dir() and (item / "WORK-ITEM.json").is_file():
        try:
            probe = json.loads((item / "WORK-ITEM.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            probe = {}
        if isinstance(probe, dict) and isinstance(probe.get("hotfix"), dict):
            bundle = read_external_bundle(item) if args.artifact_root else read_local_bundle(root, item)
            try:
                validate_bundle_integrity(bundle)
                hotfix = validated_hotfix(bundle)
            except CliFailure as failure:
                return {"verdict": failure.verdict, "code": failure.code}, failure.exit_code
            required = ("scope", "reproduction", "evidence", "correction-test", "rollback", "constitution-evidence")
            missing = [key for key in required if not isinstance(hotfix.get(key), str) or not hotfix[key].strip()]
            if missing or hotfix.get("closed") is not True:
                return {"verdict": "NO-GO", "code": "HOTFIX-INCOMPLETE", "missing": missing}, EXIT_NO_GO
            try:
                scope_paths = validate_scope(hotfix["scope"])
            except CliFailure:
                return {"verdict": "NO-GO", "code": "SCOPE-NOT-CLOSED"}, EXIT_NO_GO
            if bundle.metadata.get("scope", {}).get("paths") != scope_paths:
                return {"verdict": "NO-GO", "code": "SCOPE-METADATA-DIVERGENCE"}, EXIT_NO_GO
            try:
                constitutional = validate_constitution_check(root, bundle.files, bundle.metadata["immutable"].get("constitution", {}))
            except CliFailure as failure:
                return {"verdict": "BLOCKED-CONSTITUTION", "code": failure.code}, EXIT_CONSTITUTION
            return {"verdict": "HOTFIX-PREPARED", "code": "HOTFIX-PREPARED", "work_id": bundle.work_id,
                    "scope": hotfix["scope"], "constitutional": constitutional,
                    "post_ship": hotfix.get("post_ship", ["reconcile", "full-document-audit"])}, EXIT_OK
    if not item.is_dir():
        return {"verdict": "NO-GO", "code": "WORK-ITEM-MISSING"}, EXIT_NO_GO
    before = read_external_bundle(item) if args.artifact_root else read_local_bundle(root, item)
    immutable = validate_metadata(before.metadata, before.work_id)
    constitutional = validate_constitution_check(root, before.files, immutable.get("constitution", {}))
    auditor = Path(__file__).with_name("audit_decisions.py")
    process = subprocess.run(
        [sys.executable, str(auditor), str(item), "--project-root", str(root), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        receipt = json.loads(process.stdout.strip())
    except json.JSONDecodeError:
        return {"verdict": "NO-GO", "code": "AUDITOR-INVALID-OUTPUT"}, EXIT_NO_GO
    after = read_external_bundle(item) if args.artifact_root else read_local_bundle(root, item)
    if before.fingerprint != after.fingerprint:
        return {"verdict": "NO-GO", "code": "AUDITOR-MUTATED-WORK-ITEM"}, EXIT_NO_GO
    exit_code = process.returncode if process.returncode in {0, 1, 2, 3} else EXIT_NO_GO
    payload = {
        "verdict": receipt.get("verdict", "NO-GO"),
        "code": receipt.get("code", "OK" if exit_code == 0 else "AUDIT-FAILED"),
        "work_id": before.work_id,
        "constitutional": constitutional,
        "audit": receipt,
    }
    # Surfaced on every verdict, never silenced. A bundle created through the
    # escape hatch must not be able to look compliant with a prerequisite it
    # bypassed. It does not flip the verdict on its own: blocking outright
    # would make every air-gapped and CI-created bundle unauditable, which is a
    # worse failure than the one it prevents.
    if bundle_skipped_backlog(before):
        payload["backlog_skipped"] = True
    return payload, exit_code


def bundle_skipped_backlog(bundle: ItemBundle) -> bool:
    raw = bundle.files.get("state.json")
    if raw is None:
        return False
    try:
        return bool(json.loads(raw.decode("utf-8")).get("backlog_skipped"))
    except (UnicodeError, ValueError, AttributeError):
        return False


def local_items(root: Path) -> list[ItemBundle]:
    directory = root / ".grill" / "work-items"
    if not directory.exists():
        return []
    reject_symlink_chain(root, directory, allow_missing=False)
    return [read_local_bundle(root, item) for item in sorted(directory.iterdir()) if item.is_dir()]


def ref_items(root: Path, ref: str) -> list[ItemBundle]:
    if not git_optional(root, "rev-parse", "--verify", ref):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-SOURCE-REF", ref)
    output = run_git(root, "ls-tree", "-r", "-z", ref, "--", ".grill/work-items", text=False)
    assert isinstance(output, bytes)
    grouped: dict[str, dict[str, bytes]] = {}
    for record in output.split(b"\0"):
        if not record:
            continue
        header, raw_path = record.split(b"\t", 1)
        mode, object_type, _sha = header.decode("ascii").split()
        path = raw_path.decode("utf-8")
        parts = Path(path).parts
        if len(parts) < 4 or parts[:2] != (".grill", "work-items") or object_type != "blob" or mode == "120000":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-SOURCE-REF", path)
        work_id = parts[2]
        relative = Path(*parts[3:]).as_posix()
        data = run_git(root, "show", f"{ref}:{path}", text=False)
        assert isinstance(data, bytes)
        grouped.setdefault(work_id, {})[relative] = data
    return [bundle_from_files(work_id, files, f"{ref}:{work_id}") for work_id, files in sorted(grouped.items())]


def normalized_scope(metadata: dict[str, Any], work_id: str) -> list[str]:
    scope = metadata.get("scope", {})
    values = scope.get("paths", []) if isinstance(scope, dict) else []
    if not isinstance(values, list):
        raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-SCHEMA", work_id)
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-SCHEMA", work_id)
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise CliFailure(EXIT_NO_GO, "NO-GO", "SCOPE-PATH", f"{work_id}:{value}")
        result.append(path.as_posix().rstrip("/"))
    return sorted(set(result))


def scopes_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def overlap_authorized(left: str, right: str, dependencies: dict[str, list[str]]) -> bool:
    # Only a direct declared dependency authorizes reusing scope; never a
    # transitive one. A -> B -> C does not let A reuse C without A -> C too.
    return right in dependencies.get(left, []) or left in dependencies.get(right, [])


def scan_qualified_ids(bundle: ItemBundle) -> set[str]:
    ids: set[str] = set()
    for path, data in bundle.files.items():
        if path == "WORK-ITEM.json":
            continue
        name = Path(path).stem
        if ADR_RE.fullmatch(name):
            ids.add(f"{bundle.work_id}/{name}")
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-UTF8", bundle.origin)
        for pattern in (ADR_RE, DQ_RE, BL_RE, PHASE_RE):
            ids.update(f"{bundle.work_id}/{match.group(0)}" for match in pattern.finditer(text))
        if path == "ROUND-LOG.jsonl":
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise CliFailure(EXIT_NO_GO, "NO-GO", "ROUND-LOG-INVALID", bundle.work_id) from exc
                round_id = value.get("round_id")
                if isinstance(round_id, str) and ROUND_RE.fullmatch(round_id):
                    ids.add(f"{bundle.work_id}/{round_id}")
    return ids


def reconciliation_roadmap_is_terminal(files: dict[str, bytes]) -> bool:
    raw = files.get("ROADMAP.md")
    if raw is None:
        return False
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return False
    order_lines = [line for line in text.splitlines() if line.startswith("- execution-order:")]
    if len(order_lines) != 1:
        return False
    raw_order = order_lines[0].split(":", 1)[1]
    execution_order = [value.strip() for value in raw_order.split(",") if value.strip()]
    if not execution_order or len(execution_order) != len(set(execution_order)) or any(PHASE_RE.fullmatch(value) is None for value in execution_order):
        return False
    phase_states: dict[str, str] = {}
    seen_phases: set[str] = set()
    current_phase: str | None = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(FASE-\d{3})\b", line)
        if heading:
            phase_id = heading.group(1)
            if phase_id in seen_phases:
                return False
            seen_phases.add(phase_id)
            current_phase = phase_id
            continue
        state_match = re.fullmatch(r"- state:\s*(\S+)\s*", line)
        if state_match and current_phase:
            if current_phase in phase_states:
                return False
            phase_states[current_phase] = state_match.group(1)
    return (
        seen_phases == set(execution_order)
        and set(phase_states) == set(execution_order)
        and all(phase_states[phase_id] in {"complete", "superseded"} for phase_id in execution_order)
    )


def validate_reconciliation(root: Path, bundles: list[ItemBundle]) -> tuple[dict[str, ItemBundle], list[str], list[str]]:
    unique: dict[str, ItemBundle] = {}
    conflicts: list[str] = []
    for bundle in bundles:
        previous = unique.get(bundle.work_id)
        if previous and previous.fingerprint != bundle.fingerprint:
            conflicts.append(f"DUPLICATE-WORK-ID:{bundle.work_id}")
        elif previous is None:
            unique[bundle.work_id] = bundle
    scopes: dict[str, list[str]] = {}
    dependencies: dict[str, list[str]] = {}
    qualified: set[str] = set()
    for work_id, bundle in sorted(unique.items()):
        immutable = validate_metadata(bundle.metadata, work_id)
        recorded = immutable.get("constitution", {})
        # Imported bundles are governed by the constitution of their source
        # project, not by the destination used to preview reconciliation.
        bundle_root = Path(bundle.origin).parent.parent.parent if bundle.origin and Path(bundle.origin).is_absolute() else root
        target_constitution, _text, _clauses = constitution_info(bundle_root if bundle_root.is_dir() else root)
        if recorded.get("state") != target_constitution.get("state") or recorded.get("sha256") != target_constitution.get("sha256"):
            conflicts.append(f"CONSTITUTION-STALE:{work_id}")
        else:
            try:
                validate_constitution_check(bundle_root if bundle_root.is_dir() else root, bundle.files, recorded)
            except CliFailure as failure:
                conflicts.append(f"CONSTITUTION-CHECK:{work_id}:{failure.code}")
        state_raw = bundle.files.get("state.json")
        try:
            state = json.loads(state_raw.decode("utf-8")) if state_raw else {}
        except (UnicodeError, json.JSONDecodeError):
            state = {}
        if not isinstance(state, dict):
            state = {}
        if (
            state.get("status") != "complete"
            or state.get("milestone_status") != "completed"
            or state.get("active_phase") is not None
            or state.get("audit_verdict") != "GO"
        ):
            conflicts.append(f"STATE-NOT-RECONCILABLE:{work_id}")
        if not reconciliation_roadmap_is_terminal(bundle.files):
            conflicts.append(f"ROADMAP-NOT-TERMINAL:{work_id}")
        scopes[work_id] = normalized_scope(bundle.metadata, work_id)
        raw_deps = bundle.metadata.get("depends-on-work", [])
        if not isinstance(raw_deps, list) or not all(isinstance(value, str) for value in raw_deps):
            conflicts.append(f"DEPENDENCY-SCHEMA:{work_id}")
            dependencies[work_id] = []
        else:
            dependencies[work_id] = sorted(set(raw_deps))
        qualified.update(scan_qualified_ids(bundle))
    work_ids = set(unique)
    for work_id, deps in dependencies.items():
        for dependency in deps:
            if dependency not in work_ids:
                conflicts.append(f"DEPENDENCY-MISSING:{work_id}->{dependency}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(work_id: str) -> None:
        if work_id in visiting:
            conflicts.append(f"DEPENDENCY-CYCLE:{work_id}")
            return
        if work_id in visited:
            return
        visiting.add(work_id)
        for dependency in dependencies.get(work_id, []):
            if dependency in work_ids:
                visit(dependency)
        visiting.remove(work_id)
        visited.add(work_id)

    for work_id in sorted(work_ids):
        visit(work_id)
    ordered = sorted(scopes)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if overlap_authorized(left, right, dependencies):
                continue
            for left_path in scopes[left]:
                for right_path in scopes[right]:
                    if scopes_overlap(left_path, right_path):
                        conflicts.append(f"SCOPE-OVERLAP:{left}:{left_path}<->{right}:{right_path}")
    for work_id, bundle in sorted(unique.items()):
        references = bundle.metadata.get("conflicts-with-adrs", [])
        if not isinstance(references, list):
            conflicts.append(f"ADR-CONFLICT-SCHEMA:{work_id}")
            continue
        for reference in references:
            if not isinstance(reference, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,100}/ADR-\d{4}", reference):
                conflicts.append(f"ADR-CONFLICT-SCHEMA:{work_id}")
            elif reference in qualified:
                conflicts.append(f"ADR-CONFLICT:{work_id}->{reference}")
    return unique, sorted(set(conflicts)), sorted(qualified)


def global_documents(items: dict[str, ItemBundle], qualified: list[str], preview: dict[str, Any]) -> tuple[bytes, bytes]:
    lines = ["# Global ROADMAP", "", "Generated deterministically from reconciled work items.", ""]
    for work_id, bundle in sorted(items.items()):
        immutable = bundle.metadata["immutable"]
        lines.append(f"- **{work_id}** ({immutable['type']}): {immutable['slug']}")
    lines.extend(["", "## Qualified artifact IDs", ""])
    lines.extend(f"- `{value}`" for value in qualified)
    roadmap = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    audit = (
        "# Global Reconciliation Audit\n\n```json\n"
        + json.dumps(preview, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n"
    ).encode("utf-8")
    return roadmap, audit


RECEIPT_SCHEMA = "grill-with-docs.reconciliation-receipt"
RECEIPT_VERSION = 1


def decomposition_summary(files: dict[str, bytes]) -> dict[str, Any]:
    """Project only explicit v1 map data; legacy items remain unclassified."""
    raw = files.get("DELIVERY-MAP.md")
    if not raw:
        return {"decomposition_schema": None, "modules": "none", "modules_justification": "legacy-unclassified", "development_types": [], "delivery_units": []}
    try: text = raw.decode("utf-8")
    except UnicodeDecodeError as exc: raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DECOMPOSITION-INVALID", "invalid UTF-8") from exc
    if not re.search(r"(?m)^\s*decomposition-schema:\s*v1\s*$", text):
        return {"decomposition_schema": None, "modules": "none", "modules_justification": "legacy-unclassified", "development_types": [], "delivery_units": []}
    modules = sorted(set(re.findall(r"(?m)^##\s+(MOD-\d{3})\b", text)))
    units = sorted(set(re.findall(r"(?m)^###\s+(DU-\d{3})\b", text)))
    types = sorted(set(re.findall(r"(?m)^-\s+development-type:\s*(\S+)\s*$", text)))
    return {"decomposition_schema": "v1", "modules": modules, "development_types": types, "delivery_units": units}


def receipt_for(bundle: ItemBundle, constitution: dict[str, Any], scope: list[str], qualified: list[str]) -> dict[str, Any]:
    immutable = validate_metadata(bundle.metadata, bundle.work_id)
    decomposition = decomposition_summary(bundle.files)
    return {"schema": RECEIPT_SCHEMA, "version": RECEIPT_VERSION, "work_id": bundle.work_id,
            "fingerprint": bundle.fingerprint,
            "identity": {"type": immutable["type"], "slug": immutable["slug"]},
            "constitution": {"state": constitution.get("state"), "sha256": constitution.get("sha256")},
            "scope": scope, "qualified_ids": qualified,
            "depends_on_work": sorted(set(bundle.metadata.get("depends-on-work", []))),
            "conflicts_with_adrs": sorted(set(bundle.metadata.get("conflicts-with-adrs", []))), **decomposition}


def read_receipts(root: Path) -> dict[str, dict[str, Any]]:
    directory = root / ".grill" / "global" / "receipts"
    reject_symlink_chain(root, directory, allow_missing=False)
    if not directory.exists():
        return {}
    if not directory.is_dir() or directory.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-RECEIPTS", str(directory))
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "UNSAFE-RECEIPT", str(path))
        try:
            value = json.loads(safe_read(path, root=root, utf8=True))
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECEIPT-INVALID", str(path)) from exc
        if (not isinstance(value, dict) or value.get("schema") != RECEIPT_SCHEMA
                or value.get("version") != RECEIPT_VERSION
                or not WORK_ID_RE.fullmatch(str(value.get("work_id", "")))
                or path.name != f"{value['work_id']}.json"):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECEIPT-INVALID", str(path))
        required = ("fingerprint", "identity", "constitution", "scope", "qualified_ids", "depends_on_work", "conflicts_with_adrs")
        if any(key not in value for key in required):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECEIPT-INVALID", str(path))
        decomposition_keys = ("decomposition_schema", "modules", "development_types", "delivery_units")
        if not any(key in value for key in decomposition_keys):
            value.update({"decomposition_schema": None, "modules": "none", "modules_justification": "legacy-unclassified", "development_types": [], "delivery_units": []})
        if value.get("decomposition_schema") not in (None, "v1"):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECEIPT-INVALID", str(path))
        if value.get("decomposition_schema") == "v1":
            if (not isinstance(value.get("modules"), list) or not all(isinstance(v, str) for v in value["modules"])
                    or not isinstance(value.get("development_types"), list) or not all(isinstance(v, str) for v in value["development_types"])
                    or not isinstance(value.get("delivery_units"), list) or not all(isinstance(v, str) for v in value["delivery_units"])):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECEIPT-INVALID", str(path))
        elif value.get("modules") != "none" or value.get("modules_justification") not in (None, "legacy-unclassified"):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECEIPT-INVALID", str(path))
        if (not isinstance(value["fingerprint"], str) or not isinstance(value["identity"], dict)
                or not isinstance(value["constitution"], dict) or not isinstance(value["scope"], list)
                or not all(isinstance(v, str) for v in value["scope"])
                or not isinstance(value["qualified_ids"], list) or not all(isinstance(v, str) for v in value["qualified_ids"])
                or not isinstance(value["depends_on_work"], list) or not all(isinstance(v, str) for v in value["depends_on_work"])
                or not isinstance(value["conflicts_with_adrs"], list) or not all(isinstance(v, str) for v in value["conflicts_with_adrs"])):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECEIPT-INVALID", str(path))
        result[value["work_id"]] = value
    return result


def dirty_paths(root: Path) -> set[str]:
    output = run_git(root, "status", "--porcelain=v1", "--untracked-files=all", "-z", text=False)
    assert isinstance(output, bytes)
    paths: set[str] = set()
    records = output.split(b"\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        status = record[:2].decode("ascii", "replace")
        value = record[3:].decode("utf-8", "surrogateescape")
        paths.add(value)
        if "R" in status or "C" in status:
            if index < len(records) and records[index]:
                paths.add(records[index].decode("utf-8", "surrogateescape"))
                index += 1
    return paths


def replace_global_directory(root: Path, roadmap: bytes, audit: bytes, receipts: dict[str, bytes] | None = None) -> None:
    grill = ensure_directory(root, ".grill")
    target = grill / "global"
    if target.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SYMLINK-REJECTED", str(target))
    staging = Path(tempfile.mkdtemp(prefix=".global-", dir=grill))
    backup = grill / f".global-backup-{uuid.uuid4().hex}"
    try:
        (staging / "ROADMAP.md").write_bytes(roadmap)
        (staging / "AUDIT.md").write_bytes(audit)
        if receipts is not None:
            (staging / "receipts").mkdir()
            for name, data in sorted(receipts.items()):
                (staging / "receipts" / name).write_bytes(data)
        if target.exists():
            rename_child(grill, target, backup)
        rename_child(grill, staging, target)
        shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        if target.exists() and backup.exists():
            shutil.rmtree(target, ignore_errors=True)
        if backup.exists() and not target.exists():
            rename_child(grill, backup, target)
        shutil.rmtree(staging, ignore_errors=True)
        raise


def reconciliation_bundles(root: Path, args: argparse.Namespace) -> list[ItemBundle]:
    bundles = local_items(root)
    for source in args.source_root:
        bundles.extend(local_items(project_root(source)))
    for ref in args.source_ref:
        bundles.extend(ref_items(root, ref))
    return bundles


def targeted_bundle(root: Path, args: argparse.Namespace, bundles: list[ItemBundle]) -> tuple[ItemBundle, dict[str, Any], list[str], list[str]]:
    target_bundles = [bundle for bundle in bundles if bundle.work_id == args.work_id]
    if not target_bundles:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-MISSING", args.work_id)
    if len({bundle.fingerprint for bundle in target_bundles}) != 1:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "DUPLICATE-WORK-ID", args.work_id)
    target = target_bundles[0]
    constitution, _text, _clauses = constitution_info(root)
    immutable = validate_metadata(target.metadata, args.work_id)
    recorded = immutable.get("constitution", {})
    if recorded.get("state") != constitution.get("state") or recorded.get("sha256") != constitution.get("sha256"):
        raise CliFailure(EXIT_NO_GO, "NO-GO", "CONSTITUTION-STALE", args.work_id)
    validate_constitution_check(root, target.files, recorded)
    state = json.loads(target.files.get("state.json", b"{}").decode("utf-8"))
    if (state.get("status") != "complete" or state.get("milestone_status") != "completed"
            or state.get("active_phase") is not None or state.get("audit_verdict") != "GO"):
        raise CliFailure(EXIT_NO_GO, "NO-GO", "STATE-NOT-RECONCILABLE", args.work_id)
    if not reconciliation_roadmap_is_terminal(target.files):
        raise CliFailure(EXIT_NO_GO, "NO-GO", "ROADMAP-NOT-TERMINAL", args.work_id)
    return target, constitution, normalized_scope(target.metadata, args.work_id), sorted(scan_qualified_ids(target))


def reconcile_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    bundles = reconciliation_bundles(root, args)
    if not args.work_id:
        held_lock = acquire_lock(root, "global-reconciliation", root / ".grill" / "global") if args.apply else None
        try:
            items, conflicts, qualified = validate_reconciliation(root, bundles)
            preview = {"verdict": "NO-GO" if conflicts else "PREVIEW", "code": "CONFLICTS" if conflicts else "OK",
                       "work_ids": sorted(items), "qualified_ids": qualified, "conflicts": conflicts, "count": len(items)}
            existing = read_receipts(root)
            return reconcile_apply(root, args, preview, items, qualified, None, existing, held_lock, False)
        finally:
            if held_lock is not None:
                shutil.rmtree(held_lock, ignore_errors=True)

    try:
        target, constitution, scope, qualified = targeted_bundle(root, args, bundles)
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeError) as exc:
        return {"verdict": "NO-GO", "code": "BUNDLE-INVALID", "work_id": args.work_id, "error": str(exc)}, EXIT_NO_GO
    global_dir = root / ".grill" / "global"
    held_lock = acquire_lock(root, "global-reconciliation", global_dir) if args.apply else None
    try:
        if held_lock is not None:
            locked_bundles = reconciliation_bundles(root, args)
            locked_target, locked_constitution, locked_scope, locked_qualified = targeted_bundle(root, args, locked_bundles)
            if locked_target.fingerprint != target.fingerprint or len([b for b in locked_bundles if b.work_id == args.work_id]) != 1:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TARGET-CHANGED-DURING-RECONCILIATION", args.work_id)
            target, constitution, scope, qualified = locked_target, locked_constitution, locked_scope, locked_qualified
        existing = read_receipts(root)
        if not existing and global_dir.is_dir() and any((global_dir / name).is_file() for name in ("ROADMAP.md", "AUDIT.md")):
            return {"verdict": "BLOCKED", "code": "GLOBAL-BASELINE-UNVERIFIED", "work_id": args.work_id}, EXIT_BLOCKED
        conflicts: list[str] = []
        dependencies = target.metadata.get("depends-on-work", [])
        if not isinstance(dependencies, list) or not all(isinstance(value, str) for value in dependencies):
            conflicts.append(f"DEPENDENCY-SCHEMA:{args.work_id}")
            direct_dependencies: dict[str, list[str]] = {}
        else:
            direct_dependencies = {args.work_id: sorted(set(dependencies))}
            for dependency in sorted(set(dependencies)):
                if dependency == args.work_id:
                    conflicts.append(f"DEPENDENCY-SELF:{args.work_id}")
                elif dependency not in existing:
                    conflicts.append(f"DEPENDENCY-NOT-RECONCILED:{args.work_id}->{dependency}")
        for prior_id, receipt in sorted(existing.items()):
            if prior_id == args.work_id:
                continue
            if not overlap_authorized(args.work_id, prior_id, direct_dependencies):
                for left in scope:
                    for right in receipt.get("scope", []):
                        if isinstance(right, str) and scopes_overlap(left, right):
                            conflicts.append(f"SCOPE-OVERLAP:{args.work_id}:{left}<->{prior_id}:{right}")
            for reference in target.metadata.get("conflicts-with-adrs", []):
                if isinstance(reference, str) and reference in receipt.get("qualified_ids", []):
                    conflicts.append(f"ADR-CONFLICT:{args.work_id}->{reference}")
        preview = {"verdict": "NO-GO" if conflicts else "PREVIEW", "code": "CONFLICTS" if conflicts else "OK",
                   "work_ids": [args.work_id], "qualified_ids": qualified, "conflicts": sorted(set(conflicts)), "count": 1}
        receipt = receipt_for(target, constitution, scope, qualified)
        return reconcile_apply(root, args, preview, {args.work_id: target}, qualified, receipt, existing, held_lock, False)
    finally:
        if held_lock is not None:
            shutil.rmtree(held_lock, ignore_errors=True)


def reconcile_apply(root: Path, args: argparse.Namespace, preview: dict[str, Any], items: dict[str, ItemBundle], qualified: list[str], receipt: dict[str, Any] | None, existing: dict[str, dict[str, Any]] | None = None, held_lock: Path | None = None, release_held_lock: bool = True) -> tuple[dict[str, Any], int]:
    if not args.apply:
        return preview, EXIT_NO_GO if preview.get("conflicts") else EXIT_OK
    branch = git_optional(root, "branch", "--show-current")
    if not args.integration_branch or branch != args.integration_branch:
        return {**preview, "verdict": "BLOCKED", "code": "WRONG-INTEGRATION-BRANCH"}, EXIT_BLOCKED
    if preview.get("conflicts"):
        return preview, EXIT_NO_GO
    existing = existing if existing is not None else {}
    if receipt is None and existing:
        return {**preview, "verdict": "BLOCKED", "code": "RECEIPTS-WOULD-BE-DROPPED"}, EXIT_BLOCKED
    if receipt is not None:
        all_qualified = sorted(set(qualified) | {item for value in existing.values() for item in value.get("qualified_ids", [])})
        roadmap_lines = ["# Global ROADMAP", "", "Generated deterministically from reconciled work items.", ""]
        identities = {key: value.get("identity", {}) for key, value in existing.items()}
        identities[receipt["work_id"]] = receipt["identity"]
        for work_id in sorted(identities):
            roadmap_lines.append(f"- **{work_id}** ({identities[work_id].get('type')}): {identities[work_id].get('slug')}")
        roadmap_lines += ["", "## Qualified artifact IDs", ""] + [f"- `{value}`" for value in all_qualified]
        roadmap = ("\n".join(roadmap_lines).rstrip() + "\n").encode()
        audit = ("# Global Reconciliation Audit\n\n```json\n" + json.dumps({**preview, "work_ids": sorted(identities), "qualified_ids": all_qualified}, sort_keys=True, indent=2) + "\n```\n").encode()
        payloads = {f"{key}.json": canonical(value) for key, value in existing.items()}
        payloads[f"{receipt['work_id']}.json"] = canonical(receipt)
    else:
        roadmap, audit = global_documents(items, qualified, preview)
        payloads = None
    global_dir = root / ".grill" / "global"
    lock = held_lock or acquire_lock(root, "global-reconciliation", global_dir)
    try:
        managed = MANAGED_GLOBAL | ({".grill/global/receipts"} if payloads is not None else set())
        current_roadmap = global_dir / "ROADMAP.md"
        current_audit = global_dir / "AUDIT.md"
        current_receipts = {p.name: p.read_bytes() for p in (global_dir / "receipts").glob("*.json")} if payloads is not None and (global_dir / "receipts").is_dir() else {}
        if current_roadmap.is_file() and current_audit.is_file() and current_roadmap.read_bytes() == roadmap and current_audit.read_bytes() == audit and (payloads is None or current_receipts == payloads):
            dirty = {path for path in dirty_paths(root) if path not in managed and not path.startswith(".grill/global/receipts/") and not path.startswith(".grill/locks/global-reconciliation.lock/")}
            if dirty:
                return {**preview, "verdict": "BLOCKED", "code": "DIRTY-WORKTREE", "dirty": sorted(dirty)}, EXIT_BLOCKED
            return {**preview, "verdict": "REUSED", "code": "OK"}, EXIT_OK
        dirty = {path for path in dirty_paths(root) if not path.startswith(".grill/locks/global-reconciliation.lock/") and not path.startswith(".grill/global/receipts/") and path not in managed}
        if dirty:
            return {**preview, "verdict": "BLOCKED", "code": "DIRTY-WORKTREE", "dirty": sorted(dirty)}, EXIT_BLOCKED
        replace_global_directory(root, roadmap, audit, payloads)
        return {**preview, "verdict": "APPLIED", "code": "OK"}, EXIT_OK
    finally:
        if lock is not None and (held_lock is None or release_held_lock):
            shutil.rmtree(lock, ignore_errors=True)


def collect_legacy(root: Path) -> tuple[dict[str, bytes], dict[str, str]]:
    mapped: dict[str, bytes] = {}
    sources: dict[str, str] = {}

    def add(source: Path, destination: str) -> None:
        reject_symlink_chain(root, source, allow_missing=False)
        if source.is_symlink() or not source.is_file():
            raise CliFailure(EXIT_NO_GO, "NO-GO", "LEGACY-UNSAFE", str(source))
        data = safe_read(source, root=root)
        assert isinstance(data, bytes)
        try:
            data.decode("utf-8")
        except UnicodeError as exc:
            raise CliFailure(EXIT_NO_GO, "NO-GO", "INVALID-UTF8", str(source)) from exc
        if destination in mapped and mapped[destination] != data:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-CONFLICT", destination)
        mapped[destination] = data
        sources[destination] = source.relative_to(root).as_posix()

    for name in LEGACY_FILES:
        path = root / name
        if path.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-SYMLINK", str(path))
        if path.exists():
            add(path, name)
    for directory_name, destination_name in (("docs/adr", "docs/adr"), ("adrs", "docs/adr"), ("handoffs", "handoffs")):
        directory = root / directory_name
        if directory.is_symlink():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-SYMLINK", directory_name)
        if not directory.exists():
            continue
        reject_symlink_chain(root, directory, allow_missing=False)
        if directory.is_symlink() or not directory.is_dir():
            raise CliFailure(EXIT_NO_GO, "NO-GO", "LEGACY-UNSAFE", directory_name)
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise CliFailure(EXIT_NO_GO, "NO-GO", "LEGACY-SYMLINK", str(path))
            if path.is_file():
                relative = path.relative_to(directory).as_posix()
                add(path, f"{destination_name}/{relative}")
    return mapped, sources


def migrate_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if args.type not in KINDS or not SLUG_RE.fullmatch(args.slug):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-IDENTITY", "type or slug invalid")
    mapped, sources = collect_legacy(root)
    hashes = {path: hash_bytes(data) for path, data in sorted(mapped.items())}
    preview: dict[str, Any] = {"verdict": "PREVIEW", "code": "OK", "map": sources, "hashes": hashes}
    if not args.apply:
        return preview, EXIT_OK
    work_id = args.work_id or f"{args.type}-{args.slug}-migration-{uuid.uuid4().hex}"
    if not WORK_ID_RE.fullmatch(work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-WORK-ID", work_id)
    target = root / ".grill" / "work-items" / work_id
    lock = acquire_lock(root, work_id, target, reuse_if_target_exists=True)
    try:
        if target.exists():
            bundle = read_local_bundle(root, target)
            immutable = validate_metadata(bundle.metadata, work_id)
            if immutable.get("type") != args.type or immutable.get("slug") != args.slug:
                return {**preview, "verdict": "BLOCKED", "code": "IDENTITY-DIVERGENCE", "work_id": work_id}, EXIT_BLOCKED
            migration = bundle.metadata.get("migration", {})
            if migration.get("source_hashes") != hashes:
                return {**preview, "verdict": "BLOCKED", "code": "TARGET-DIVERGES", "work_id": work_id}, EXIT_BLOCKED
            for path, data in mapped.items():
                if path == "state.json":
                    continue
                if bundle.files.get(path) != data:
                    return {**preview, "verdict": "BLOCKED", "code": "TARGET-DIVERGES", "work_id": work_id}, EXIT_BLOCKED
            return {**preview, "verdict": "REUSED", "work_id": work_id}, EXIT_OK
        immutable = immutable_metadata(root, args, work_id)
        files = initial_files(root, work_id, immutable)
        files.update({path: data for path, data in mapped.items() if path != "state.json"})
        metadata = metadata_document(immutable, files, migration={"source_hashes": hashes, "source_paths": sources})
        staging = write_bundle_staging(root, work_id, metadata, files)
        try:
            rename_child(target.parent, staging, target)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return {**preview, "verdict": "APPLIED", "work_id": work_id}, EXIT_OK
    finally:
        if lock is not None:
            shutil.rmtree(lock, ignore_errors=True)


#: Read from the SSOT rather than restated here.  These five names used to be
#: local literals, which is how this file came to declare the active frontier in
#: one constant while injecting the *previous* version's gate a few hundred lines
#: below: two sources of truth cannot disagree loudly, only silently.
#:
#: This is a deliberate exception to the local-literal rule stated for
#: ``V3_ORPHAN_IMMUTABLE_FIELDS`` (LD-010 item 4).  That rule exists to keep hot
#: paths free of a load-time dependency on ``grill_core``; it does not reach
#: ``workflow_versions``, which is pure data with no imports of its own -- a
#: property its own contract test (``Purity``) enforces.  Do not "restore
#: consistency" by copying these back.
_workflow_versions = grill_core_module("workflow_versions")
SEQUENCE = list(_workflow_versions.SEQUENCE_BY_VERSION[_workflow_versions.ACTIVE_VERSION])
DEVELOPMENT_SCHEMAS = dict(_workflow_versions.DEVELOPMENT_SCHEMAS)
SEQUENCE_BY_VERSION = {
    version: list(sequence)
    for version, sequence in _workflow_versions.SEQUENCE_BY_VERSION.items()
}
ACTIVE_DEVELOPMENT_SCHEMA = _workflow_versions.ACTIVE_DEVELOPMENT_SCHEMA
ACTIVE_WORKFLOW_VERSION = _workflow_versions.ACTIVE_VERSION


def development_workflow_version(development: object) -> str | None:
    """Which workflow version a development block speaks, or None if it is not one.

    Dual-read is the whole point: a bundle written under /v1 keeps projecting
    and keeps checkpointing after this build ships, against the sequence it was
    written with. Migration is a separate, explicit act.
    """
    if not isinstance(development, dict):
        return None
    schema = development.get("schema")
    if schema not in DEVELOPMENT_SCHEMAS:
        return None
    implied = DEVELOPMENT_SCHEMAS[schema]
    if implied is not None:
        return implied
    declared = development.get("workflow_version")
    return declared if declared in SEQUENCE_BY_VERSION else None


def development_sequence(development: object) -> list[str] | None:
    """The canonical sequence a development block must declare, or None."""
    version = development_workflow_version(development)
    return None if version is None else SEQUENCE_BY_VERSION[version]



def resolve_development_item(root: Path, work_id: str) -> Path:
    """Locate a work item bundle for a state-writing command, refusing symlinks."""
    if not WORK_ID_RE.fullmatch(work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-WORK-ID", work_id)
    item = root / ".grill" / "work-items" / work_id
    try:
        # Checking only `item.is_symlink()` follows an unsafe ancestor such as
        # `.grill/work-items -> /outside`, allowing an apply to mutate bytes
        # outside the project.  The lexical chain guard rejects every ancestor
        # before this command opens, locks, or writes the bundle.
        reject_symlink_chain(root, item, allow_missing=False)
    except CliFailure as exc:
        if exc.code == "SYMLINK-REJECTED":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORK-ITEM-SYMLINK", work_id) from exc
        raise
    if item.is_symlink():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORK-ITEM-SYMLINK", work_id)
    if not item.is_dir():
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-MISSING", work_id)
    return item


def open_development_item_fd(root: Path, work_id: str) -> int:
    """Open a work-item directory through no-follow ancestor descriptors.

    The returned descriptor pins the directory that was verified underneath
    ``root``.  A later rename of ``.grill/work-items`` can no longer redirect
    a migration's reads or write to an outside tree.  Platforms without the
    required openat primitives fail closed rather than fall back to a
    path-based mutation with that TOCTOU exposure.
    """
    if not (hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SAFE-DIRECTORY-FD-UNAVAILABLE", work_id)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors: list[int] = []
    try:
        current = os.open(root, flags)
        descriptors.append(current)
        for component in (".grill", "work-items", work_id):
            current = os.open(component, flags, dir_fd=current)
            descriptors.append(current)
        result = descriptors.pop()
        return result
    except FileNotFoundError as exc:
        raise CliFailure(EXIT_NO_GO, "NO-GO", "WORK-ITEM-MISSING", work_id) from exc
    except OSError as exc:
        # Linux reports O_DIRECTORY|O_NOFOLLOW on a symlink as ENOTDIR;
        # other POSIX kernels use ELOOP.  Both mean this ancestry cannot be
        # trusted for a state-changing work-item operation.
        code = "WORK-ITEM-SYMLINK" if exc.errno in {errno.ELOOP, errno.EMLINK, errno.ENOTDIR} else "UNSAFE-WORK-ITEM"
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, work_id) from exc
    finally:
        for descriptor in descriptors:
            os.close(descriptor)


def migrate_v3_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Preview-first ``grill-work-item/v2`` -> ``/v3`` bundle upgrade (LD-004 item 2).

    Delegates entirely to ``grill_core.work_item_v3.migrate_bundle``, which
    already is preview-first (``apply=False`` never writes and takes no lock),
    idempotent (``REUSED`` on a second apply) and CAS-guarded on write. This
    function only resolves/locks the target bundle the same way every other
    mutating work-item command does, and translates the module's exceptions at
    the CLI boundary. It is the real, callable replacement the payload of
    ``WORK-ITEM-V3-REQUIRED`` (grill_core.work_item_v3.require_v3) points a
    caller at today via ``migration_capability``.
    """
    root = project_root(args.root)
    item = resolve_development_item(root, args.work_id)
    work_item_v3 = grill_core_module("work_item_v3")
    rebind_workflow = bool(getattr(args, "rebind_workflow", False))
    workflow_sha256: str | None = None
    if rebind_workflow:
        workflow_gate = _workflow_module(root)
        try:
            _, workflow_bytes, workflow_text = workflow_gate.load_workflow(root)
            gate = workflow_gate.execution_gate(workflow_text)
        except workflow_gate.Failure as error:
            code = translate_v3_code(error.code)
            raise CliFailure(
                error.exit_code,
                error.verdict,
                code,
                error.message,
                extra=dict(error.extra) if error.extra else None,
            ) from error
        if gate.status != "OK":
            code = translate_v3_code(gate.code or "WORKFLOW_INCOMPATIBLE")
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, "current workflow is not eligible for rebind")
        workflow_sha256 = hash_bytes(workflow_bytes)
    lock = acquire_lock(root, args.work_id, item) if args.apply else None
    item_fd: int | None = None
    try:
        item_fd = open_development_item_fd(root, args.work_id)
        try:
            if rebind_workflow:
                if args.apply:
                    # Preview's workflow identity is informational.  A write
                    # must instead bind the workflow accepted while its
                    # work-item commit window is held, never an earlier read.
                    try:
                        _, workflow_bytes, workflow_text = workflow_gate.load_workflow(root)
                        gate = workflow_gate.execution_gate(workflow_text)
                    except workflow_gate.Failure as error:
                        code = translate_v3_code(error.code)
                        raise CliFailure(
                            error.exit_code,
                            error.verdict,
                            code,
                            error.message,
                            extra=dict(error.extra) if error.extra else None,
                        ) from error
                    if gate.status != "OK":
                        code = translate_v3_code(gate.code or "WORKFLOW_INCOMPATIBLE")
                        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, "current workflow is not eligible for rebind")
                    workflow_sha256 = hash_bytes(workflow_bytes)
                assert workflow_sha256 is not None
                result = work_item_v3.rebind_workflow_bundle(
                    item,
                    workflow_sha256=workflow_sha256,
                    apply=args.apply,
                    item_dir_fd=item_fd,
                    lock_held=lock is not None,
                )
            else:
                result = work_item_v3.migrate_bundle(
                    item,
                    apply=args.apply,
                    item_dir_fd=item_fd,
                    lock_held=lock is not None,
                )
        except work_item_v3.WorkItemError as error:
            raise_from_work_item_error(error)
        exit_code = EXIT_OK if result.get("verdict") in {"PREVIEW", "REUSED", "APPLIED"} else EXIT_BLOCKED
        return result, exit_code
    finally:
        if item_fd is not None:
            os.close(item_fd)
        if lock is not None:
            shutil.rmtree(lock, ignore_errors=True)


def migrate_v4_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Expose the preview-first WORKFLOW.md v2/v3 -> v4 migration."""
    workflow_v4 = grill_core_module("workflow_v4")
    try:
        return workflow_v4.migrate_command(
            args.root,
            apply=args.apply,
            expected_sha256=args.expected_sha256,
            allow_local_edits=args.allow_local_edits,
        )
    except workflow_v4.Failure as error:
        code = translate_v3_code(error.code)
        raise CliFailure(
            error.exit_code,
            error.verdict,
            code,
            error.message,
            extra=dict(error.extra) if error.extra else None,
        ) from error


def gauntlet_init_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Explicitly activate one verified V3 work item for the FASE-001 Gauntlet."""
    root = project_root(args.root)
    resolve_development_item(root, args.work_id)
    gauntlet = grill_core_module("gauntlet")
    workflow_gate = _workflow_module(root)
    work_item_v3 = grill_core_module("work_item_v3")
    step_skills = grill_core_module("step_skills")
    config_lock: Any | None = None
    item_lock: Any | None = None
    item_fd: int | None = None
    try:
        # A configuration map is shared by every work item, so serialize its
        # writer first. The existing item lock follows it; rebind takes only
        # that latter lock, which makes this ordering deadlock-free.
        try:
            config_lock = gauntlet.acquire_config_lock(root)
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        try:
            item_lock = gauntlet.acquire_work_item_lock(config_lock.grill_fd, args.work_id)
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        try:
            item_fd = gauntlet.open_work_item_fd(config_lock.grill_fd, args.work_id)
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        try:
            try:
                _, workflow_bytes, workflow_text = workflow_gate.load_workflow(root)
            except workflow_gate.Failure as error:
                code = translate_v3_code(error.code)
                raise CliFailure(
                    error.exit_code,
                    error.verdict,
                    code,
                    error.message,
                    extra=dict(error.extra) if error.extra else None,
                ) from error
            verdict = gauntlet.activate(
                root=root,
                work_id=args.work_id,
                max_workers=args.max_workers,
                item_dir_fd=item_fd,
                grill_fd=config_lock.grill_fd,
                workflow_bytes=workflow_bytes,
                workflow_text=workflow_text,
                workflow_gate=workflow_gate,
                work_item_v3=work_item_v3,
                step_skills=step_skills,
                runtime=args.runtime,
            )
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        return {
            "verdict": verdict,
            "work_id": args.work_id,
            "config": ".grill/gauntlet.yaml",
            "max_workers": args.max_workers,
            "stall_minutes": 15,
            "runtime": args.runtime,
            **_coordinator_response(args.runtime),
        }, EXIT_OK
    finally:
        if item_fd is not None:
            os.close(item_fd)
        if item_lock is not None:
            gauntlet.release_work_item_lock(item_lock)
        if config_lock is not None:
            gauntlet.release_config_lock(config_lock)


def resolve_gauntlet_subject(root: Path, work_id: str) -> Path:
    """Resolve a control subject with its closed top-level denial contract."""
    try:
        return resolve_development_item(root, work_id)
    except CliFailure as error:
        # Control commands distinguish invalid subjects from a projected
        # eligibility failure.  Their public boundary is always BLOCKED.
        if error.verdict != "BLOCKED":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
        raise


def gauntlet_activation_projection(args: argparse.Namespace) -> tuple[Path, str, str | None]:
    """Read one valid subject's FASE-001 activation state without a lock or write."""
    root = project_root(args.root)
    resolve_gauntlet_subject(root, args.work_id)
    # Loading the capability precedes the point at which a status subject can
    # be safely projected. An unloadable core is therefore a top-level public
    # failure, never a synthetic STATUS response.
    gauntlet = grill_core_module("gauntlet")
    workflow_gate = _workflow_module(root)
    work_item_v3 = grill_core_module("work_item_v3")
    step_skills = grill_core_module("step_skills")
    item_fd: int | None = None
    grill_fd: int | None = None
    try:
        try:
            item_fd = open_development_item_fd(root, args.work_id)
        except CliFailure as error:
            return root, "BLOCKED", "SAFE-PATH-UNAVAILABLE" if error.code == "SAFE-DIRECTORY-FD-UNAVAILABLE" else error.code
        try:
            grill_fd = gauntlet.open_config_directory(root)
        except gauntlet.GauntletError as error:
            return root, "BLOCKED", error.code
        try:
            _, workflow_bytes, workflow_text = workflow_gate.load_workflow(root)
        except workflow_gate.Failure as error:
            code = translate_v3_code(error.code)
            return root, "BLOCKED", code
        try:
            state, reason = gauntlet.activation_state(
                root=root,
                work_id=args.work_id,
                item_dir_fd=item_fd,
                grill_fd=grill_fd,
                workflow_bytes=workflow_bytes,
                workflow_text=workflow_text,
                workflow_gate=workflow_gate,
                work_item_v3=work_item_v3,
                step_skills=step_skills,
            )
        except gauntlet.GauntletError as error:
            return root, "BLOCKED", error.code
        return root, state, reason
    finally:
        if item_fd is not None:
            os.close(item_fd)
        if grill_fd is not None:
            os.close(grill_fd)


def gauntlet_status_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root, state, reason = gauntlet_activation_projection(args)
    payload: dict[str, Any] = {"verdict": "STATUS", "work_id": args.work_id, "activation_state": state}
    if state in {"STALE", "BLOCKED"}:
        payload["reason"] = reason or "ELIGIBILITY-UNAVAILABLE"
        return payload, EXIT_OK
    # Run state is a FASE-002 projection layered on the existing, read-only
    # FASE-001 activation projection.  An activation does not initialise the
    # Store, so status before the first admission deliberately has no `run`.
    gauntlet_runs = grill_core_module("gauntlet_runs")
    if gauntlet_runs.store.store_exists(root):
        try:
            run = gauntlet_runs.project_run(root, args.work_id, args.run_id)
        except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
            code = gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code) if isinstance(error, gauntlet_runs.store.StoreError) else error.code
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error
        if run is not None:
            payload["run"] = run
    elif args.run_id is not None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RUN-NOT-FOUND", "requested durable run does not exist", extra={"work_id": args.work_id})
    return payload, EXIT_OK


def gauntlet_run_admission(args: argparse.Namespace) -> tuple[Path, Any, dict[str, str], dict[str, Any]]:
    """Build a durable admission only from a newly verified FASE-001 proof.

    The activation-state projection is intentionally repeated here instead of
    trusting a prior status call: each mutable FASE-002 command must prove the
    current activation for itself.  The resulting hashes use the exact config
    record and bytes observed by this proof boundary; no formatted or prefixed
    digest enters the Store.

    Also returns the exact activation ``record`` this proof read (config
    ``limits``/``tier_policy`` included).  FASE-003 commands need explicit
    live values (e.g. the activation-configured worker cap) that ``gauntlet_
    runs`` -- a hash-only coordinator boundary -- never reads for itself; the
    CLI resolves them once, here, from the same proof every other field
    already comes from, and threads them down explicitly.
    """
    root = project_root(args.root)
    resolve_gauntlet_subject(root, args.work_id)
    gauntlet = grill_core_module("gauntlet")
    workflow_gate = _workflow_module(root)
    work_item_v3 = grill_core_module("work_item_v3")
    step_skills = grill_core_module("step_skills")
    gauntlet_runs = grill_core_module("gauntlet_runs")
    item_fd: int | None = None
    grill_fd: int | None = None
    try:
        item_fd = open_development_item_fd(root, args.work_id)
        grill_fd = gauntlet.open_config_directory(root)
        try:
            _, workflow_bytes, workflow_text = workflow_gate.load_workflow(root)
        except workflow_gate.Failure as error:
            code = translate_v3_code(error.code)
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message) from error
        try:
            state, reason = gauntlet.activation_state(
                root=root, work_id=args.work_id, item_dir_fd=item_fd, grill_fd=grill_fd,
                workflow_bytes=workflow_bytes, workflow_text=workflow_text,
                workflow_gate=workflow_gate, work_item_v3=work_item_v3, step_skills=step_skills,
            )
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        if state != "ACTIVATED":
            code = "ACTIVATION-REQUIRED" if state == "ELIGIBLE" else (reason or "ACTIVATION-REQUIRED")
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, "a current Gauntlet activation is required", extra={"work_id": args.work_id})
        try:
            config, config_bytes, _ = gauntlet._read_config(grill_fd)
            record = config["activations"].get(args.work_id)
            if record is None:
                raise gauntlet.GauntletError(
                    "ACTIVATION-REQUIRED", "a current Gauntlet activation is required", work_id=args.work_id
                )
            proof = gauntlet.current_activation(
                root=root, work_id=args.work_id, item_dir_fd=item_fd, workflow_bytes=workflow_bytes,
                workflow_text=workflow_text, workflow_gate=workflow_gate,
                work_item_v3=work_item_v3, step_skills=step_skills,
                runtime=record["runtime"]["id"],
            )
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        identity = {key: proof[key] for key in ("work_item_id", "work_item", "workflow", "runtime", "catalog")}
        if config_bytes is None or record is None:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVATION-REQUIRED", "a current Gauntlet activation is required", extra={"work_id": args.work_id})
        if any(record.get(key) != value for key, value in identity.items()):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IDENTITY-STALE", "Gauntlet activation identity is stale", extra={"work_id": args.work_id})
        base_commit = git_optional(root, "rev-parse", "HEAD")
        if not re.fullmatch(r"[0-9a-f]{40}", base_commit):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "BASE-COMMIT-UNAVAILABLE", "current Git base commit is unavailable", extra={"work_id": args.work_id})
        try:
            admission = gauntlet_runs.admission_from_proof(
                activation=record,
                work_item_sha256=proof["work_item"]["document_sha256"],
                workflow_sha256=hash_bytes(workflow_bytes),
                config_sha256=hash_bytes(config_bytes),
                base_commit=base_commit,
            )
        except gauntlet_runs.GauntletRunError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra={"work_id": args.work_id}) from error
        return root, gauntlet_runs, admission, record
    finally:
        if item_fd is not None:
            os.close(item_fd)
        if grill_fd is not None:
            os.close(grill_fd)


def _gauntlet_authorized(handler: Callable[[argparse.Namespace], tuple[dict[str, Any], int]]) -> Callable[[argparse.Namespace], tuple[dict[str, Any], int]]:
    """Require the adopted context fence around a mutable Gauntlet command."""
    @functools.wraps(handler)
    def wrapped(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
        root = project_root(args.root)
        # ``gauntlet_runs`` owns the Store module identity on the direct-file
        # CLI path.  Its ContextVar must be set on that exact module, not a
        # second sibling import with an identical filename.
        store = grill_core_module("gauntlet_runs").store
        # A concurrent commit publishes its journal anchor before its snapshot.
        # Read the authority fence under the same lock, never between those writes.
        try:
            snapshot = None
            if store.store_exists(root):
                with store.orchestrator_lock(store.store_paths(root)):
                    if handler.__name__ == "gauntlet_tasks_import_command" and args.apply:
                        _recover_task_import(root, args, store)
                    snapshot = store.read_snapshot(root, required=False)
        except store.StoreError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.message) from exc
        block = snapshot.document.get("agent_orchestration") if snapshot is not None else None
        item = block.get("work_items", {}).get(args.work_id) if isinstance(block, dict) else None
        if item is None:
            return handler(args)
        if handler.__name__ in {"partition_emit_command", "gauntlet_tasks_reconcile_command", "gauntlet_tasks_import_command"} and not args.apply:
            return handler(args)
        context_id = item.get("current_context_id")
        context = item.get("contexts", {}).get(context_id)
        session_ref = getattr(args, "session_ref", None)
        if not isinstance(context, dict) or not isinstance(session_ref, str):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", args.work_id)
        contract = grill_core_module("agent_orchestration")
        selected_id, selected_epoch = getattr(args, "context_id", None), getattr(args, "epoch", None)
        if ((selected_id is None) != (selected_epoch is None)):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "incomplete context selectors")
        # Run abandonment is the one recovery that may remove the active work
        # preventing a QUIESCING context from becoming RELEASED.  Admit only
        # the exact former leader after Orca proves its release; the handler
        # still requires a human authorization scoped to the target run.
        released_abandon = (handler.__name__ == "gauntlet_run_abandon_command"
                             and context.get("state") == "QUIESCING"
                             and context.get("leader", {}).get("state") == "RELEASING")
        if released_abandon:
            if (selected_id is not None or session_ref != context.get("leader", {}).get("session_ref")):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", args.work_id)
            _require_released_leader(root, args.work_id, context, session_ref)
            return handler(args)
        try:
            contract.require_authority(item, selected_id if selected_id is not None else context_id,
                                       selected_epoch if selected_epoch is not None else context["epoch"], session_ref)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
        # Cleanup and constitutional recovery require the current observed
        # leader, but must remain usable when presentation itself is stale.
        cleanup = handler.__name__ == "gauntlet_cleanup_command"
        administrative_recovery = cleanup or handler.__name__ == "constitution_reseal_command"
        if administrative_recovery:
            readiness = None
        else:
            try:
                contract.require_presentation_work_ready(context)
            except contract.OrchestrationError as exc:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", str(exc), "presentation is not ready") from exc
            if getattr(args, "runtime", None) not in (None, context["runtime"]):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", "runtime changed without continuity")
            readiness = _session_readiness(root, context["runtime"], session_ref, work_id=args.work_id)
        _require_current_leader(root, args.work_id, context, session_ref, readiness)
        if not administrative_recovery:
            try:
                contract.require_presentation_work_ready(readiness)
            except contract.OrchestrationError as exc:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", str(exc), "presentation is not ready") from exc
            if any(context["presentation"].get(key) != readiness["presentation"].get(key)
                   for key in ("session_identity", "runtime", "scope", "policy_sha256")):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STYLE-SCOPE-CONFLICT", "presentation authority, scope or policy changed")
            # Configuration/version changes require a fresh full read, not a
            # new leader context. Keep the existing CAS and append-only Store.
            if (any(context["presentation"].get(key) != readiness["presentation"].get(key)
                    for key in ("config_fingerprint", "gwd_skill_sha256"))
                    and not readiness["presentation"]["use_ready"]):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STYLE-LOAD-UNCONFIRMED", "presentation upgrade requires a fresh full read",
                                 extra={"presentation": readiness["presentation"]})
            if context["presentation"] != readiness["presentation"]:
                def refresh(document: dict[str, Any]) -> dict[str, Any]:
                    target = document["agent_orchestration"]["work_items"][args.work_id]
                    if target.get("current_context_id") != context_id or target["contexts"].get(context_id) != context:
                        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTEXT-FENCED", "context changed during observation")
                    target["contexts"][context_id]["presentation"] = readiness["presentation"]
                    return document
                snapshot = store.transact(root, refresh)
                context = snapshot.document["agent_orchestration"]["work_items"][args.work_id]["contexts"][context_id]
        try:
            with store.orchestration_authority(
                root, args.work_id, context_id=context_id, epoch=context["epoch"], session_ref=session_ref,
                observed_context=context, cleanup=cleanup,
            ):
                return handler(args)
        except store.StoreError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.message) from exc
    return wrapped


def _recover_task_import(root: Path, args: argparse.Namespace, store: Any) -> None:
    """Recover only this previewed import, including journal-before-snapshot faults.

    Called under the Store lock. The raw snapshot is authority only for recovery;
    the normal anchored read and entry guards still run immediately afterwards.
    """
    paths = store.store_paths(root)
    pending = store._pending_path(paths)
    if not pending.exists():
        return
    intent = store.loads(store._read_regular(pending).decode("utf-8"))
    if not isinstance(intent, dict) or intent.get("schema") != "grill-transition-wal/v1":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-IMPORT-CAS-CONFLICT", "another operation requires recovery")
    event, receipt = store._transition_fields(intent.get("event"), intent.get("receipt"))
    store._bind_receipt_hash(event, receipt)
    candidate = store._validate_document(intent.get("candidate"), paths.orchestrator)
    run = candidate.get("work_items", {}).get(args.work_id, {}).get("gauntlet", {}).get("runs", {}).get(args.run_id, {})
    imported = run.get("task_import", {})
    if (event.get("event") != "gauntlet.tasks.imported" or event.get("work_id") != args.work_id
            or event.get("run_id") != args.run_id or event.get("input_sha256") != args.expected_sha256
            or store.jcs_sha256(imported) != args.expected_sha256 or imported.get("dag_ref") != args.dag
            or sorted(f"{task}={source}" for task, source in imported.get("source_tasks", {}).items()) != sorted(args.source_task)):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-IMPORT-CAS-CONFLICT", "retry must match the pending import")
    current = store._snapshot_from(store._read_regular(paths.orchestrator), paths.orchestrator)
    item = current.document.get("agent_orchestration", {}).get("work_items", {}).get(args.work_id)
    if item is not None:
        context = item["contexts"][item["current_context_id"]]
        contract = grill_core_module("agent_orchestration")
        try:
            contract.require_authority(item, item["current_context_id"], context["epoch"], args.session_ref)
        except contract.OrchestrationError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(error)) from error
        readiness = _session_readiness(root, context["runtime"], args.session_ref, work_id=args.work_id)
        _require_current_leader(root, args.work_id, context, args.session_ref, readiness)
    store._recover_pending_transition_locked(paths, root)


constitution_reseal_command = _gauntlet_authorized(constitution_reseal_command)


@_gauntlet_authorized
def gauntlet_run_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root, gauntlet_runs, admission, _record = gauntlet_run_admission(args)
    try:
        return gauntlet_runs.admit_or_reuse_run(root, args.work_id, admission), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code) if isinstance(error, gauntlet_runs.store.StoreError) else error.code
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


def gauntlet_resume_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if args.checkpoint is not None or args.runtime is not None:
        if args.run_id is not None or args.checkpoint is None or args.runtime is None:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "choose scheduler recovery or continuity resume")
        return continuity_resume_command(args)
    return _gauntlet_authorized(_gauntlet_scheduler_resume_command)(args)


def _gauntlet_scheduler_resume_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    # Retain the FASE-001 control boundary for callers that did not select a
    # durable run.  FASE-002 recovery is deliberately opt-in via --run-id.
    if args.run_id is None:
        _, state, _ = gauntlet_activation_projection(args)
        if state != "ACTIVATED":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVATION-REQUIRED", "a current Gauntlet activation is required", extra={"work_id": args.work_id})
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SCHEDULING-NOT-AVAILABLE", "durable recovery requires --run-id", extra={"work_id": args.work_id})
    root, gauntlet_runs, admission, record = gauntlet_run_admission(args)
    try:
        payload = gauntlet_runs.record_resume_decision(root, args.work_id, args.run_id, admission)
        return _with_coordinator_response(payload, record["runtime"]["id"]), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code) if isinstance(error, gauntlet_runs.store.StoreError) else error.code
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


def _continuity_identity(root: Path, work_id: str, state: dict[str, Any]) -> dict[str, str]:
    """The identity a CLI switch may preserve; no branch or worktree migration."""
    store = grill_core_module("store")
    project = store.project_identity(root)
    branch = git_optional(root, "branch", "--show-current")
    if not branch:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", "detached HEAD")
    # T055: validate `development`'s shape here, unconditionally -- not only
    # when `active_phase` is falsy. `_continuity_refuse_branch_contradiction`
    # carries the same DEVELOPMENT-SCHEMA guard, but it runs *after* this
    # function in all three continuity verbs; leaving it as the only guard
    # means a present-but-wrong-type `development` only misses `.get()`
    # (AttributeError, not the named refusal) when `active_phase` happens to
    # be falsy -- exactly the terminal-milestone shape audit_decisions.py
    # requires (`active_phase` null).
    development = state.get("development")
    if development is not None and not isinstance(development, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DEVELOPMENT-SCHEMA", work_id)
    phase = state.get("active_phase") or (development or {}).get("current_step") or "unassigned"
    return {"project_id": project["project_id"], "work_id": work_id, "phase": str(phase),
            "du": "work-item", "git_common_dir": project["git_common_dir"],
            "real_path": str(root.resolve()), "branch": branch}


# T035: the structural tuple, in one place. `phase` and `branch` are stamped
# for the record but stay OUT of it: both move in normal life -- a step turn
# advances the phase, a branch is switched -- and no verb ever re-stamps, so
# comparing the stamped value would mean "nothing moved since the stamp was
# first written", which is not what quiescence proves. Quiescence proves
# nothing is running *now*; it says nothing about how old the stamp is.
# The live branch *is* compared, just not against this stamp: see
# `_continuity_refuse_branch_contradiction`, which checks it against
# `development["execution_branch"]`, the work item's own sealed SSOT.
_CONTINUITY_STRUCTURAL = ("project_id", "work_id", "du", "git_common_dir", "real_path")


def _continuity_identity_matches(sealed: Any, identity: dict[str, str]) -> bool:
    """Fail-closed: a missing or non-mapping stamp never matches."""
    if not isinstance(sealed, dict):
        return False
    return all(sealed.get(field) == identity[field] for field in _CONTINUITY_STRUCTURAL)


def _continuity_refuse_branch_contradiction(state: Any, identity: dict[str, str], work_id: str) -> None:
    """Refuse when the work item's sealed execution branch contradicts the live one.

    R6-T045: this comparison used to exist only in `continuity-resume`, so
    `prepare-switch` created the operation, wrote the resume point and released
    the leader before anything noticed the divergence -- which then surfaced on
    the resume, with the context already loose. The failure has to be named
    before mutating, so the single point is called by all three verbs.

    T047: also guards `development`'s own schema -- DEVELOPMENT-SCHEMA when the
    block is present but not a mapping -- before reading `execution_branch`.
    Since T055, that is defense in depth, not the effective guard: all three
    continuity verbs derive `identity` via `_continuity_identity` first, on
    this same `state`, and it already refuses a malformed `development` block
    before this function ever runs. No CLI path reaches this raise today. It
    stays -- the signature accepts a value of any type, the project is
    fail-closed -- for a future caller that builds `identity` without going
    through `_continuity_identity`.

    T052: an absent or empty sealed branch passes in silence, on purpose --
    nothing bound yet is not a contradiction -- so this only refuses an actual
    contradiction, never a missing requirement; that is why it is named for
    the refusal, not for a requirement. Each caller also raises
    CONTINUITY-STATE-DIVERGENCE for a *different* reason right before calling
    this one: a live worktree/context identity mismatch ("worktree identity
    changed", "project or worktree changed..."). Both share the code, so tell
    them apart by message, not by code: this function always names the work
    item's bound branch ("work item is bound to <branch>"); it never speaks
    for the context's identity.
    """
    development = state.get("development") if isinstance(state, dict) else None
    if development is None:
        development = {}
    if not isinstance(development, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DEVELOPMENT-SCHEMA", work_id)
    sealed = development.get("execution_branch")
    if isinstance(sealed, str) and sealed and sealed != identity["branch"]:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE",
                         f"work item is bound to {sealed}")


def _continuity_quiescence(document: dict[str, Any], item: dict[str, Any], work_id: str,
                           quiet_activity_ids: set[str] | None = None) -> tuple[list[str], list[str]]:
    """Only explicit terminal observations are quiet; lease expiry and silence are ignored."""
    quiet_activity_ids = quiet_activity_ids or set()
    active, unknown = [], []
    for activity_id, activity in item.get("activities", {}).items():
        resource = item.get("resources", {}).get(activity.get("session_resource_id"))
        result_session_closed = (activity.get("state") == "RESULT_RECORDED"
            and isinstance(resource, dict) and resource.get("state") == "CLOSED"
            and resource.get("result_acceptance_ref") == activity.get("result_ref"))
        if (activity.get("state") in {"BOOTSTRAPPING", "VERIFIED", "DISPATCHED", "RESULT_RECORDED"}
                and activity_id not in quiet_activity_ids and not result_session_closed):
            active.append("activity:" + activity_id)
    for resource_id, resource in item.get("resources", {}).items():
        if resource.get("kind") == "session" and resource.get("state") == "UNKNOWN":
            unknown.append("session:" + resource_id)
    runs = document.get("work_items", {}).get(work_id, {}).get("gauntlet", {}).get("runs", {})
    worker_active, worker_unknown = grill_core_module("gauntlet_runs").continuity_worker_quiescence(runs)
    return sorted(active + worker_active), sorted(unknown + worker_unknown)


def _takeover_prepared_workers(document: dict[str, Any], work_id: str) -> list[str]:
    """Prepared workers survive a proven-terminal leader and pass to its successor."""
    runs = document.get("work_items", {}).get(work_id, {}).get("gauntlet", {}).get("runs", {})
    return sorted(f"worker:{run_id}:{worker_id}"
                  for run_id, run in runs.items() if run.get("state") != "BLOCKED"
                  for worker_id, worker in run.get("workers", {}).items()
                  if worker.get("state") == "PREPARED")


def _released_activity_sessions(root: Path, item: dict[str, Any], work_id: str) -> dict[str, tuple[str, dict[str, Any]]]:
    """Return pending result sessions whose exact Orca release archive is current."""
    runtime = grill_core_module("agent_runtime")
    released: dict[str, tuple[str, dict[str, Any]]] = {}
    for activity_id, activity in item.get("activities", {}).items():
        resource_id = activity.get("session_resource_id")
        resource = item.get("resources", {}).get(resource_id)
        identity = resource.get("identity", {}) if isinstance(resource, dict) else {}
        dispatch = identity.get("owner_dispatch")
        if (activity.get("state") != "RESULT_RECORDED" or activity.get("activity_type") != "author"
                or not isinstance(resource_id, str)
                or resource.get("state") not in {"CLOSE_PENDING", "CLOSED"}
                or resource.get("kind") != "session" or resource.get("activity_id") != activity_id
                or not isinstance(dispatch, str)):
            continue
        try:
            observed = _leader_boundary(root, identity.get("provider"), "orca:" + dispatch, work_id).observe_released()
        except (runtime.RuntimeError, TypeError):
            continue
        observed_identity = {key: observed.get(key) for key in (
            "provider", "adapter", "host", "runtime_instance", "handle", "incarnation",
            "owner_dispatch", "task_id", "dispatch_incarnation", "worktree_id")}
        if identity == observed_identity:
            released[activity_id] = (resource_id, observed)
    return released


def _transferred_activity_sessions(item: dict[str, Any]) -> dict[str, tuple[str, str, dict[str, str]]]:
    """Find abandoned dispatches whose exact terminal was closed by an accepted retry."""
    physical = ("provider", "adapter", "host", "runtime_instance", "handle", "incarnation",
                "dispatch_incarnation", "worktree_id")
    recovered: dict[str, tuple[str, str, dict[str, str]]] = {}
    activities, resources = item.get("activities", {}), item.get("resources", {})
    for activity_id, activity in activities.items():
        resource_id = activity.get("session_resource_id")
        resource = resources.get(resource_id)
        if (activity.get("state") != "DISPATCHED" or not isinstance(resource_id, str)
                or not isinstance(resource, dict) or resource.get("kind") != "session"
                or resource.get("state") != "REGISTERED" or resource.get("activity_id") != activity_id):
            continue
        identity = resource.get("identity", {})
        matches = []
        for successor_id, successor in activities.items():
            successor_resource = resources.get(successor.get("session_resource_id"))
            if (successor_id == activity_id or successor.get("state") != "ACCEPTED"
                    or successor.get("context_id") != activity.get("context_id")
                    or successor.get("activity_type") != activity.get("activity_type")
                    or successor.get("step_id") != activity.get("step_id")
                    or successor.get("author_activity_ids") != activity.get("author_activity_ids")
                    or not isinstance(successor_resource, dict) or successor_resource.get("state") != "CLOSED"
                    or successor_resource.get("activity_id") != successor_id
                    or successor_resource.get("result_acceptance_ref") != successor.get("acceptance_ref")):
                continue
            successor_identity = successor_resource.get("identity", {})
            if (any(identity.get(key) != successor_identity.get(key) for key in physical)
                    or identity.get("owner_dispatch") == successor_identity.get("owner_dispatch")
                    or resource.get("creation_observation", {}).get("collected_at", "")
                       >= successor_resource.get("creation_observation", {}).get("collected_at", "")):
                continue
            observation_ref = successor_resource.get("last_observation")
            receipts = [receipt for receipt in successor_resource.get("evidence_manifest", {}).get("receipts", [])
                        if receipt.get("ref") == observation_ref]
            if len(receipts) == 1:
                matches.append((resource_id, successor_id, copy.deepcopy(receipts[0])))
        if len(matches) == 1:
            recovered[activity_id] = matches[0]
    return recovered


def _continuity_operation(item: dict[str, Any], context_id: str, to_runtime: str) -> tuple[str, dict[str, Any]] | None:
    matches = [(operation_id, operation) for operation_id, operation in item.get("operations", {}).items()
               if operation.get("kind") == "continuity-switch" and operation.get("context_id") == context_id
               and operation.get("intended_after", {}).get("to_runtime") == to_runtime]
    if len(matches) > 1:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", "ambiguous switch operation")
    return matches[0] if matches else None


def _continuity_checkpoint(item: dict[str, Any], *, operation_id: str, context_id: str,
                           identity: dict[str, str], store_revision: int, journal_anchor: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    contract = grill_core_module("agent_orchestration")
    store = grill_core_module("store")
    head = item.get("checkpoint_head")
    if not isinstance(head, str) or head not in item.get("checkpoints", {}):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-CHECKPOINT-MISSING", "no committed checkpoint")
    checkpoint_id = "cp-" + operation_id
    existing = item["checkpoints"].get(checkpoint_id)
    if isinstance(existing, dict):
        return checkpoint_id, existing
    checkpoint = copy.deepcopy(item["checkpoints"][head])
    checkpoint.update({"checkpoint_id": checkpoint_id, "context_id": context_id,
                       "previous_checkpoint_id": head, "worktree_identity": copy.deepcopy(identity),
                       "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "store_revision": store_revision, "journal_anchor": copy.deepcopy(journal_anchor),
                       "checkpoint_sha256": ""})
    checkpoint["checkpoint_sha256"] = store.jcs_sha256({key: value for key, value in checkpoint.items()
                                                          if key != "checkpoint_sha256"})
    try:
        contract.validate_block({"schema": contract.SCHEMA, "work_items": {"x": {**item,
            "checkpoints": {**item["checkpoints"], checkpoint_id: checkpoint}, "checkpoint_head": checkpoint_id}}})
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", str(exc)) from exc
    return checkpoint_id, checkpoint


def _initial_continuity_checkpoint(root: Path, work_id: str, item: dict[str, Any], context: dict[str, Any],
                                   context_id: str, checkpoint_id: str, identity: dict[str, str],
                                   state: dict[str, Any], state_bytes: bytes, store_revision: int,
                                   journal_anchor: dict[str, Any]) -> dict[str, Any]:
    """T005: project the current state into a first checkpoint instead of
    refusing switch prep with CONTINUITY-CHECKPOINT-MISSING when no step was
    confirmed yet. Mirrors the checkpoint shape `checkpoint_command` commits."""
    contract = grill_core_module("agent_orchestration")
    store = grill_core_module("store")
    cleanup_obligations, preserved_resources = _cleanup_checkpoint_projection(root, work_id)
    development = state.get("development", {})
    checkpoint = {
        "schema": contract.CHECKPOINT_SCHEMA_V2, "checkpoint_id": checkpoint_id, "context_id": context_id,
        "previous_checkpoint_id": None, "worktree_identity": copy.deepcopy(identity),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "store_revision": store_revision,
        "journal_anchor": copy.deepcopy(journal_anchor), "state_sha256": hash_bytes(state_bytes),
        "inputs_manifest": {"evidence": []}, "context_inputs_sha256": context["inputs_sha256"],
        "origin_metadata_sha256": item["origin"]["metadata_sha256"], "policy_sha256": item["policy_sha256"],
        "activation": context["activation"], "campaign": context["campaign"],
        "development_sequence": development.get("sequence", []),
        "current_step": development.get("current_step"), "step_states": development.get("steps", {}),
        "accepted_outputs": development.get("attested_outputs", {}),
        "accepted_executions": development.get("attested_executions", {}),
        "pending_attempts": {}, "scheduler_runs": copy.deepcopy(context["scheduler_runs"]),
        "operations": copy.deepcopy(item["operations"]), "cleanup_obligations": cleanup_obligations,
        "preserved_resources": preserved_resources, "blocking_activity": None, "visual_state": {},
        "presentation": context.get("presentation"), "checkpoint_sha256": "",
    }
    checkpoint["checkpoint_sha256"] = store.jcs_sha256({key: value for key, value in checkpoint.items()
                                                          if key != "checkpoint_sha256"})
    try:
        contract.validate_block({"schema": contract.SCHEMA, "work_items": {"x": {**item,
            "checkpoints": {**item["checkpoints"], checkpoint_id: checkpoint}, "checkpoint_head": checkpoint_id}}})
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", str(exc)) from exc
    return checkpoint


def gauntlet_prepare_switch_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    store = grill_core_module("store")
    contract = grill_core_module("agent_orchestration")
    snapshot = store.read_snapshot(root, required=True)
    item = snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(args.work_id)
    if not isinstance(item, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-MIGRATION-REQUIRED", args.work_id)
    context_id = args.context_id
    context = item.get("contexts", {}).get(context_id)
    if (not isinstance(context, dict) or item.get("current_context_id") != context_id
            or context.get("epoch") != args.epoch or context.get("leader", {}).get("session_ref") != args.session_ref
            or context.get("state") not in {"ACTIVE", "QUIESCING"}):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", args.work_id)
    released = _require_released_leader(root, args.work_id, context, args.session_ref) if args.released_source else None
    if released is None:
        _require_current_leader(root, args.work_id, context, args.session_ref)
    released_sessions = _released_activity_sessions(root, item, args.work_id) if released is not None else {}
    transferred_sessions = _transferred_activity_sessions(item) if released is not None else {}
    state_path, state = read_development_state(root, resolve_development_item(root, args.work_id), args.work_id)
    identity = _continuity_identity(root, args.work_id, state)
    sealed = context.get("worktree_identity")
    # An absent stamp is stamped below for the first time; a present one is
    # judged on the structural tuple only, like the takeover. Merge note (main
    # 6.0.11): the incoming side compared the whole identity mapping, which is
    # the J1/H1 defect this delivery closed -- `phase` and `branch` move in
    # normal life and no verb re-stamps them. The structural comparison is
    # kept; only the released-leader logic is taken from the incoming side.
    if sealed is not None and not _continuity_identity_matches(sealed, identity):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", "worktree identity changed")
    _continuity_refuse_branch_contradiction(state, identity, args.work_id)
    operation_entry = _continuity_operation(item, context_id, args.to_runtime)
    initial_checkpoint = None
    source_checkpoint = None
    if operation_entry is None:
        source_checkpoint = item.get("checkpoint_head")
        if source_checkpoint is not None and source_checkpoint not in item.get("checkpoints", {}):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-CHECKPOINT-MISSING", args.work_id)
        if source_checkpoint is None:
            # T005: no confirmed step yet -- project current state into an
            # initial checkpoint instead of refusing. A declared-but-unknown
            # head (the branch above) still refuses.
            source_checkpoint = "cp-init-" + hashlib.sha256(canonical(
                {"context": context_id, "epoch": args.epoch})).hexdigest()[:24]
            initial_checkpoint = _initial_continuity_checkpoint(
                root, args.work_id, item, context, context_id, source_checkpoint, identity, state,
                safe_read_regular_fd(root, state_path), snapshot.revision + 1, snapshot.document["journal_head"])
        operation_id = "switch-" + hashlib.sha256(canonical({"context": context_id, "checkpoint": source_checkpoint,
            "to_runtime": args.to_runtime})).hexdigest()[:24]
        checkpoint_id = "cp-" + operation_id
        source_campaign = context.get("campaign")
        if source_campaign is None and isinstance(item.get("checkpoints", {}).get(source_checkpoint), dict):
            source_campaign = item["checkpoints"][source_checkpoint].get("campaign")
        # A fresh initial_checkpoint always carries context["campaign"] verbatim
        # (T005/_initial_continuity_checkpoint), so source_campaign is already
        # correct without reading it back from item["checkpoints"].
        bridge = None
        if source_campaign is not None:
            try:
                destination_adapter = grill_core_module("gauntlet").ADAPTER_BY_RUNTIME[args.to_runtime]
                successor = contract.successor_campaign(source_campaign, runtime=args.to_runtime,
                    adapter=destination_adapter, registry_sha256=source_campaign["registry_sha256"],
                    bridge_seed={"context": context_id, "checkpoint": checkpoint_id})
                bridge = contract.campaign_bridge(source_campaign, successor,
                    accepted_outputs=item["checkpoints"][source_checkpoint]["accepted_outputs"], worktree_identity=identity)
            except (KeyError, contract.OrchestrationError) as exc:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", str(exc)) from exc
        request = {"context_id": context_id, "checkpoint_id": checkpoint_id, "to_runtime": args.to_runtime,
                   "worktree_identity": identity, "campaign_bridge": bridge}
        operation = {"kind": "continuity-switch", "context_id": context_id, "fence": context["leader"]["fence"],
            "subject_ids": [context_id, checkpoint_id], "input_sha256": store.jcs_sha256(request),
            "expected_before": {"checkpoint_id": checkpoint_id, "worktree_identity": copy.deepcopy(identity)},
            "intended_after": {"to_runtime": args.to_runtime, "campaign_bridge": bridge},
            "idempotency_key": operation_id, "state": "INTENT", "result_ref": None, "result_sha256": None,
            "observation_ref": None, "error": None}
    else:
        operation_id, operation = operation_entry
        checkpoint_id = operation.get("expected_before", {}).get("checkpoint_id")
        if not isinstance(checkpoint_id, str):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", operation_id)
    quiet_sessions = set(released_sessions) | set(transferred_sessions)
    active, unknown = _continuity_quiescence(snapshot.document, item, args.work_id, quiet_sessions)
    began_active = context["state"] == "ACTIVE"
    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        target = document["agent_orchestration"]["work_items"][args.work_id]
        source = target["contexts"].get(context_id)
        if (not isinstance(source, dict) or target.get("current_context_id") != context_id
                or source.get("epoch") != args.epoch or source.get("leader", {}).get("session_ref") != args.session_ref):
            raise store.StoreError(store.STATE_DIVERGENCE, "continuity source changed")
        if initial_checkpoint is not None and source_checkpoint not in target["checkpoints"]:
            if target.get("checkpoint_head") is not None:
                raise store.StoreError(store.STATE_DIVERGENCE, "checkpoint head appeared during switch preparation")
            target["checkpoints"][source_checkpoint] = copy.deepcopy(initial_checkpoint)
            target["checkpoint_head"] = source_checkpoint
        target["operations"].setdefault(operation_id, copy.deepcopy(operation))
        for activity_id, (resource_id, observation) in released_sessions.items():
            activity = target["activities"].get(activity_id)
            resource = target["resources"].get(resource_id)
            if (not isinstance(activity, dict) or activity.get("state") != "RESULT_RECORDED"
                    or not isinstance(resource, dict) or resource.get("identity") != item["resources"][resource_id]["identity"]
                    or resource.get("state") not in {"CLOSE_PENDING", "CLOSED"}):
                raise store.StoreError(store.STATE_DIVERGENCE, "released activity session changed")
            if resource["state"] == "CLOSE_PENDING":
                release_ref = observation["source_ref"] + ":release"
                receipt = {"ref": release_ref, "sha256": observation["source_sha256"]}
                if receipt not in resource["evidence_manifest"]["receipts"]:
                    resource["evidence_manifest"]["receipts"].append(receipt)
                resource.update({"state": "CLOSED", "last_observation": release_ref,
                                 "result_acceptance_ref": activity["result_ref"]})
                activity.update({"released_at": observation["source_ref"],
                                 "accepted_by_context": source["context_id"],
                                 "acceptance_ref": activity["result_ref"],
                                 "review_verdict": "APPROVED", "state": "ACCEPTED"})
        for activity_id, (resource_id, successor_id, receipt) in transferred_sessions.items():
            activity = target["activities"].get(activity_id)
            resource = target["resources"].get(resource_id)
            successor = target["activities"].get(successor_id)
            if (not isinstance(activity, dict) or activity.get("state") != "DISPATCHED"
                    or not isinstance(resource, dict) or resource.get("state") != "REGISTERED"
                    or not isinstance(successor, dict) or successor.get("state") != "ACCEPTED"):
                raise store.StoreError(store.STATE_DIVERGENCE, "transferred activity session changed")
            if receipt not in resource["evidence_manifest"]["receipts"]:
                resource["evidence_manifest"]["receipts"].append(copy.deepcopy(receipt))
            resource.update({"state": "PRESERVED", "last_observation": receipt["ref"],
                             "preservation_reasons": ["RESULT_NOT_DURABLE"], "operation_id": operation_id})
            activity.update({"state": "FAILED", "diagnostic_ref":
                             f"orca:{resource['identity']['owner_dispatch']}:superseded-by:{successor_id}"})
        source.setdefault("worktree_identity", copy.deepcopy(identity))
        if source["campaign"] is None and operation["intended_after"]["campaign_bridge"] is not None:
            source["campaign"] = copy.deepcopy(operation["intended_after"]["campaign_bridge"]["from_campaign"])
        started_active = source["state"] == "ACTIVE"
        if started_active:
            source["state"] = "QUIESCING"; source["leader"]["state"] = "RELEASING"
        if not started_active and not active and not unknown and source["state"] == "QUIESCING":
            source["state"] = "RELEASED"; source["leader"]["state"] = "RELEASED"
            if checkpoint_id not in target["checkpoints"]:
                _, checkpoint = _continuity_checkpoint(target, operation_id=operation_id, context_id=context_id,
                    identity=identity, store_revision=document["revision"] + 1, journal_anchor=document["journal_head"])
                target["checkpoints"][checkpoint_id] = checkpoint; target["checkpoint_head"] = checkpoint_id
            target["operations"][operation_id]["state"] = "APPLIED"
            if released is not None:
                target["operations"][operation_id]["observation_ref"] = released["source_ref"]
        return document
    try:
        committed = store.transact(root, mutate)
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-CAS-CONFLICT", exc.message) from exc
    if active:
        return {"verdict": "BLOCKED", "code": "CONTINUITY-ACTIVE-WORK", "work_id": args.work_id,
                "context_id": context_id, "epoch": args.epoch, "operation_id": operation_id, "active": active}, EXIT_BLOCKED
    if unknown:
        return {"verdict": "BLOCKED", "code": "CONTINUITY-QUIESCENCE-UNPROVEN", "work_id": args.work_id,
                "context_id": context_id, "epoch": args.epoch, "operation_id": operation_id, "unknown": unknown}, EXIT_BLOCKED
    if began_active:
        return {"verdict": "QUIESCING", "work_id": args.work_id, "context_id": context_id,
                "epoch": args.epoch, "operation_id": operation_id, "next": "repeat prepare-switch after quiescence"}, EXIT_OK
    return {"verdict": "SWITCH-PREPARED", "work_id": args.work_id, "context_id": context_id,
            "epoch": args.epoch, "operation_id": operation_id, "checkpoint_id": checkpoint_id,
            "store_revision": committed.revision}, EXIT_OK


def _continuity_effective_activation(root: Path, work_id: str, runtime: str) -> dict[str, Any]:
    """Prove the destination runtime while retaining the source scheduler pins."""
    gauntlet = grill_core_module("gauntlet")
    workflow_gate = _workflow_module(root)
    work_item_v3 = grill_core_module("work_item_v3")
    step_skills = grill_core_module("step_skills")
    item_fd = config_fd = None
    try:
        item_fd = open_development_item_fd(root, work_id)
        config_fd = gauntlet.open_config_directory(root)
        _, workflow_bytes, workflow_text = workflow_gate.load_workflow(root)
        source = gauntlet.require_activation(config_fd, work_id)
        proof = gauntlet.current_activation(root=root, work_id=work_id, item_dir_fd=item_fd,
            workflow_bytes=workflow_bytes, workflow_text=workflow_text, workflow_gate=workflow_gate,
            work_item_v3=work_item_v3, step_skills=step_skills, runtime=runtime)
        return gauntlet.effective_activation(source, proof)
    except (gauntlet.GauntletError, workflow_gate.Failure) as exc:
        code = getattr(exc, "code", "ACTIVATION-REQUIRED")
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, str(exc)) from exc
    finally:
        if item_fd is not None: os.close(item_fd)
        if config_fd is not None: os.close(config_fd)


def continuity_resume_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if not isinstance(args.session_ref, str) or not args.session_ref:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "continuity resume requires --session-ref")
    store = grill_core_module("store")
    contract = grill_core_module("agent_orchestration")
    snapshot = store.read_snapshot(root, required=True)
    item = snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(args.work_id)
    if not isinstance(item, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-MIGRATION-REQUIRED", args.work_id)
    checkpoint = item.get("checkpoints", {}).get(args.checkpoint)
    if not isinstance(checkpoint, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-CHECKPOINT-MISSING", args.checkpoint)
    source_id = checkpoint.get("context_id")
    source = item.get("contexts", {}).get(source_id)
    operation_entry = _continuity_operation(item, source_id, args.runtime) if isinstance(source_id, str) else None
    if (not isinstance(source, dict) or item.get("current_context_id") != source_id or source.get("state") != "RELEASED"
            or source.get("leader", {}).get("state") != "RELEASED" or operation_entry is None):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-QUIESCENCE-UNPROVEN", args.work_id)
    operation_id, operation = operation_entry
    if operation.get("state") not in {"APPLIED", "CONFIRMED"} or operation.get("expected_before", {}).get("checkpoint_id") != args.checkpoint:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", args.checkpoint)
    state = read_development_state(root, resolve_development_item(root, args.work_id), args.work_id)[1]
    identity = _continuity_identity(root, args.work_id, state)
    if not (_continuity_identity_matches(checkpoint.get("worktree_identity"), identity)
            and _continuity_identity_matches(source.get("worktree_identity"), identity)):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", "project or worktree changed")
    # R5-1: `branch` left the structural tuple (T035) because it moves in
    # normal life and no verb re-stamps it. The compensating control is the
    # binding the work item already seals, so compare against *that* SSOT --
    # not against the stamp -- whenever it exists.
    _continuity_refuse_branch_contradiction(state, identity, args.work_id)
    active, unknown = _continuity_quiescence(snapshot.document, item, args.work_id)
    if active:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-ACTIVE-WORK", ",".join(active))
    if unknown:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-QUIESCENCE-UNPROVEN", ",".join(unknown))
    readiness = _session_readiness(root, args.runtime, args.session_ref, work_id=args.work_id)
    activation = _continuity_effective_activation(root, args.work_id, args.runtime)
    bridge = operation.get("intended_after", {}).get("campaign_bridge")
    if bridge is not None:
        try:
            expected_campaign = contract.successor_campaign(bridge["from_campaign"], runtime=args.runtime,
                adapter=activation["runtime"]["adapter"], registry_sha256=activation["workflow"]["registry_sha256"],
                bridge_seed={"context": source_id, "checkpoint": args.checkpoint})
        except (KeyError, contract.OrchestrationError) as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", str(exc)) from exc
        if bridge.get("to_campaign") != expected_campaign:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-STATE-DIVERGENCE", "runtime bridge differs from checkpoint")
    else:
        expected_campaign = None
    pending = copy.deepcopy(checkpoint.get("pending_attempts", {}))
    retained = {resource_id: copy.deepcopy(resource) for resource_id, resource in item.get("resources", {}).items()
                if resource.get("state") not in {"CLOSED", "REMOVED"}}
    reconcile = {operation_id: copy.deepcopy(record) for operation_id, record in item.get("operations", {}).items()
                 if record.get("state") in {"INTENT", "APPLIED", "UNKNOWN"}}
    preview = {"verdict": "PREVIEW", "work_id": args.work_id, "checkpoint_id": args.checkpoint,
        "from_context_id": source_id, "to_runtime": args.runtime, "accepted_outputs": copy.deepcopy(checkpoint["accepted_outputs"]),
        "pending_attempts": pending, "preserved_resources": retained, "operations_to_reconcile": reconcile,
        "campaign": expected_campaign, "activation": activation, "presentation": readiness["presentation"],
        "expected_sha256": store.jcs_sha256({"revision": snapshot.revision, "checkpoint": args.checkpoint,
            "runtime": args.runtime, "session_ref": args.session_ref, "identity": identity,
            "campaign": expected_campaign, "readiness": readiness}),
        **_coordinator_response(args.runtime)}
    if not args.apply:
        return preview, EXIT_OK
    if args.expected_sha256 != preview["expected_sha256"]:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", "expected_sha256 does not match preview")
    context_id = "ctx-" + hashlib.sha256(canonical({"operation": operation_id, "session": args.session_ref})).hexdigest()[:24]
    result_ref = f"continuity/{operation_id}.json"
    result_sha = store.jcs_sha256({"checkpoint": args.checkpoint, "from_context": source_id,
        "to_context": context_id, "campaign": expected_campaign, "accepted_outputs": checkpoint["accepted_outputs"]})
    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        if document["revision"] != snapshot.revision:
            raise store.StoreError(store.STATE_DIVERGENCE, "continuity inputs changed during observation")
        target = document["agent_orchestration"]["work_items"][args.work_id]
        current = target["contexts"].get(source_id)
        existing = target["contexts"].get(context_id)
        if existing is not None:
            if target.get("current_context_id") == context_id:
                return document
            raise store.StoreError(store.STATE_DIVERGENCE, "continuity context id already exists")
        if (target.get("current_context_id") != source_id or not isinstance(current, dict)
                or current.get("state") != "RELEASED" or current.get("leader", {}).get("state") != "RELEASED"):
            raise store.StoreError(store.STATE_DIVERGENCE, "continuity source changed")
        current_operation = target["operations"].get(operation_id)
        if not isinstance(current_operation, dict) or current_operation.get("state") != "APPLIED":
            raise store.StoreError(store.STATE_DIVERGENCE, "continuity operation changed")
        next_epoch = current["epoch"] + 1
        target["contexts"][context_id] = {"context_id": context_id, "epoch": next_epoch,
            "predecessor_context_id": source_id, "continuity_ref": operation_id, "runtime": args.runtime,
            "adapter": activation["runtime"]["adapter"], "activation": copy.deepcopy(activation),
            "campaign": copy.deepcopy(expected_campaign), "scheduler_runs": copy.deepcopy(current["scheduler_runs"]),
            "leader": {"owner_id": context_id, "session_ref": args.session_ref, "incarnation": readiness["incarnation"],
                "fence": next_epoch, "epoch": next_epoch, "state": "ACTIVE", "observation_ref": readiness["ref"],
                "observation_sha256": readiness["sha256"]}, "state": "ACTIVE", "policy_sha256": current["policy_sha256"],
            "presentation": copy.deepcopy(readiness["presentation"]),
            "inputs_sha256": current["inputs_sha256"], "worktree_identity": copy.deepcopy(identity)}
        current["state"] = "SUPERSEDED"
        current_operation.update({"state": "CONFIRMED", "result_ref": result_ref, "result_sha256": result_sha,
                                  "observation_ref": result_ref})
        target["current_context_id"] = context_id
        return document
    try:
        committed = store.transact(root, mutate)
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-CAS-CONFLICT", exc.message) from exc
    return {"verdict": "RESUMED", "work_id": args.work_id, "checkpoint_id": args.checkpoint,
        "context_id": context_id, "epoch": snapshot.document["agent_orchestration"]["work_items"][args.work_id]["contexts"][source_id]["epoch"] + 1,
        "campaign": expected_campaign, "pending_attempts": pending, "preserved_resources": retained,
        "operations_to_reconcile": reconcile, "store_revision": committed.revision, "presentation": readiness["presentation"],
        **_coordinator_response(args.runtime)}, EXIT_OK


def gauntlet_context_takeover_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """T003/T004: a new session assumes a work item once the environment --
    not the caller -- proves the previous conductor ended (FR-001..FR-005).

    Preview and apply run the exact same checks (contract context-takeover);
    the only difference is that apply additionally requires a matching
    --expected-sha256 and performs the CAS mutation. A refusal is raised the
    same way in both modes, so the preview never lies about what apply would
    do (mirrors T006's fix to orchestration-adopt for the same reason).
    """
    root = project_root(args.root)
    if not isinstance(args.session_ref, str) or not args.session_ref:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "gauntlet-context-takeover requires --session-ref")
    store = grill_core_module("store")
    snapshot = store.read_snapshot(root, required=True)
    item = snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(args.work_id)
    if not isinstance(item, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-MIGRATION-REQUIRED", args.work_id)
    context_id = item.get("current_context_id")
    context = item.get("contexts", {}).get(context_id)
    if not isinstance(context, dict) or context.get("state") not in {"ACTIVE", "QUIESCING"}:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", args.work_id)
    # Idempotent replay: this session already took over as the current context.
    continuity_ref = context.get("continuity_ref")
    prior_operation = item.get("operations", {}).get(continuity_ref) if isinstance(continuity_ref, str) else None
    if (context.get("leader", {}).get("session_ref") == args.session_ref and isinstance(prior_operation, dict)
            and prior_operation.get("kind") == "continuity-switch"
            and prior_operation.get("intended_after", {}).get("reason") == "takeover"):
        return {"verdict": "TAKEOVER-REUSED", "work_id": args.work_id, "context_id": context_id,
                "from_context_id": context.get("predecessor_context_id"), "epoch": context["epoch"],
                "store_revision": snapshot.revision}, EXIT_OK
    old_session_ref = context["leader"]["session_ref"]
    observation, status, liveness = _takeover_observation(root, context["runtime"], old_session_ref)
    if observation["verdict"] == "not_observable":
        # U1: not_observable is the form of the registered identifier; the
        # adapter cannot even shape a query out of it.
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TAKEOVER-NOT-OBSERVABLE", old_session_ref)
    if observation["verdict"] != "terminal":
        if status in {"dispatched", "running"}:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TAKEOVER-LEADER-ACTIVE", old_session_ref)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TAKEOVER-EVIDENCE-UNPROVEN", old_session_ref)
    # A proven-terminal predecessor cannot advance workers it fully prepared.
    # The successor inherits only that exact state; activities, unknown workers
    # and every earlier worker state still block the takeover.
    active, unknown = _continuity_quiescence(snapshot.document, item, args.work_id)
    inherited_prepared_workers = _takeover_prepared_workers(snapshot.document, args.work_id)
    blocking_active = sorted(set(active) - set(inherited_prepared_workers))
    if blocking_active or unknown:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TAKEOVER-WORK-ACTIVE", ",".join(blocking_active + unknown))
    # T016: the environment proves the predecessor ended, but nobody had
    # observed the *incoming* session, so its leader was installed with null
    # incarnation/observation and every @_gauntlet_authorized command refused
    # it with LEADER-AUTHORITY-UNPROVEN. Same readiness source the resume
    # sibling uses; it raises when the observation does not conclude, so the
    # absence of proof never authorizes the takeover.
    readiness = _session_readiness(root, context["runtime"], args.session_ref, work_id=args.work_id)
    old_campaign = context.get("campaign")
    checkpoint_ref, bridge = None, None
    if old_campaign is not None:
        head = item.get("checkpoint_head")
        if not isinstance(head, str) or head not in item.get("checkpoints", {}):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-CHECKPOINT-MISSING", args.work_id)
        checkpoint_ref = head
        # Same campaign on both sides: the runtime is not changing, only the
        # session driving it. validate_block only requires the bridge to
        # agree with the contexts and the referenced checkpoint's outputs.
        bridge = {"from_campaign": copy.deepcopy(old_campaign), "to_campaign": copy.deepcopy(old_campaign),
                  "accepted_outputs": copy.deepcopy(item["checkpoints"][head]["accepted_outputs"]),
                  "worktree_identity": copy.deepcopy(context.get("worktree_identity") or {})}
    evidence = {"observation_ref": observation["reference"], "observation_sha256": observation["digest"],
                "dispatch_status": status, "liveness": liveness}
    operation_id = "takeover-" + hashlib.sha256(canonical({"context": context_id, "session_ref": args.session_ref,
        "observation": observation})).hexdigest()[:24]
    new_context_id = "ctx-" + hashlib.sha256(canonical({"operation": operation_id})).hexdigest()[:24]
    # T023: the successor used to inherit a blind copy of the predecessor's
    # worktree_identity. That identity carries `branch`, and LeaderBoundary
    # only pins the worktree *path* -- so switching branch after the session
    # died (routine, once nobody is driving the tree) left the successor
    # holding an identity that lies about the live tree, and every later
    # continuity-resume refused forever, with no re-stamp verb in the core.
    # Derive it live from the same helper the resume sibling uses and store
    # the derived value below. Computed before `expected` so preview and
    # apply reach the same verdict.
    #
    # T030: the divergence guard compares only the *structural* fields. The
    # other two move during the normal life of a context: `phase` advances
    # with every cycle step (and with the `development.current_step` fallback
    # that most work items land on), and `branch` is exactly what the
    # paragraph above says a dead session's tree is free to change. Comparing
    # them made the takeover refuse the very scenario it exists to cure, and
    # refuse it forever, since only a successful takeover rewrites the stamp
    # and the core has no re-stamp verb. Both are re-stamped from the derived
    # identity below instead of being asserted here. T035: the resume sibling
    # and `prepare-switch` now share the same structural tuple. Their window
    # being quiescent does not justify the strict comparison -- quiescence
    # proves nothing is running now, not that the stamp is fresh, and since a
    # takeover stamps the phase of that instant and nothing ever re-stamps,
    # the first step turn made `prepare-switch` refuse forever.
    #
    # When the source carries no stamp at all -- the field is optional in the
    # context schema -- there is no prior claim to contradict, so the derived
    # identity is stamped for the first time instead of refusing a takeover
    # that no verb could ever unblock. Accepted side effect, the same one the
    # resume already accepts: _continuity_identity refuses on a detached HEAD.
    #
    # T048: that same freedom outlives this takeover. The instant this
    # successor's own session ends, or its branch changes again for any
    # routine reason, the value just re-stamped here goes exactly as stale as
    # the one it replaced -- no verb re-stamps it either. A reader elsewhere
    # in the core must not treat this stamp as a live oracle for "the branch
    # this work item currently runs on"; only a future takeover or
    # continuity-resume re-derives it, and only at the moment it runs. That is
    # why the checkpoint and phase-turn commands mint their own binding from
    # the live branch instead of comparing against this stamp.
    state = read_development_state(root, resolve_development_item(root, args.work_id), args.work_id)[1]
    identity = _continuity_identity(root, args.work_id, state)
    sealed = context.get("worktree_identity")
    if sealed is not None and not _continuity_identity_matches(sealed, identity):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TAKEOVER-IDENTITY-DIVERGENT",
                         "project or worktree changed since the predecessor stamped its identity")
    _continuity_refuse_branch_contradiction(state, identity, args.work_id)
    # T018: digest the decision, not the coordinator's raw answer.
    # observation["digest"] hashes the live worker-show bytes, and preview and
    # apply are separate CLI invocations: any volatile field there made apply
    # refuse with TAKEOVER-INPUTS-STALE while nothing in the store had moved.
    # The response digest stays in `evidence`, where it is succession proof.
    #
    # T024: `snapshot.revision` is gone from here for the same reason. It is
    # the *global* document revision -- transact stamps current.revision + 1
    # on the whole document, not per work item -- so any write by any work
    # item invalidated the preview, including the one @_gauntlet_authorized
    # itself performs whenever the observed presentation differs from the
    # persisted one. The revision guard inside `mutate` below already pins
    # the same thing under the lock, strictly stronger and more precise.
    expected = store.jcs_sha256({"work_id": args.work_id, "from_context_id": context_id,
        "from_session_ref": old_session_ref, "to_session_ref": args.session_ref,
        "observation": {"verdict": observation["verdict"], "reference": observation["reference"]},
        "checkpoint_ref": checkpoint_ref, "inherited_prepared_workers": inherited_prepared_workers})
    if not args.apply:
        return {"verdict": "TAKEOVER-PREVIEW", "work_id": args.work_id, "from_context_id": context_id,
                "inherited_prepared_workers": inherited_prepared_workers,
                "expected_sha256": expected}, EXIT_OK
    if args.expected_sha256 != expected:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TAKEOVER-INPUTS-STALE",
                         "expected_sha256 does not match reread takeover inputs")
    next_epoch = context["epoch"] + 1
    fence = context["leader"]["fence"]
    # T019/T026: the superseded context never satisfies require_authority
    # again (current *and* ACTIVE), so gauntlet-cleanup over it refuses
    # forever and its resources stay pinned in the store. This projection
    # exists for *auditing* only -- it names what stayed pinned. Reconciling
    # it is NOT implemented: no path in the core reconciles a resource whose
    # origin_context_id is the superseded context, since both consumers
    # (gauntlet_cleanup_command and the acceptance path) filter by the
    # current context. Same projection shape as the resume.
    retained = {resource_id: copy.deepcopy(resource) for resource_id, resource in item.get("resources", {}).items()
                if resource.get("state") not in {"CLOSED", "REMOVED"}}
    reconcile = {record_id: copy.deepcopy(record) for record_id, record in item.get("operations", {}).items()
                 if record.get("state") in {"INTENT", "APPLIED", "UNKNOWN"}}
    taken_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    result_ref = f"context-takeover/{operation_id}.json"
    result_sha256 = store.jcs_sha256({"from_context": context_id, "to_context": new_context_id,
        "session_ref": args.session_ref, "evidence": evidence})
    # kind stays "continuity-switch": validate_block only accepts that kind
    # for a successor context's continuity_ref (agent_orchestration.py); the
    # succession facts (reason/evidence/taken_at) live in intended_after.
    operation = {
        "kind": "continuity-switch", "context_id": context_id, "fence": fence,
        "subject_ids": [context_id, new_context_id], "input_sha256": expected,
        "expected_before": {"context_id": context_id, "session_ref": old_session_ref, "checkpoint_id": checkpoint_ref},
        "intended_after": {"reason": "takeover", "to_runtime": context["runtime"],
                            "from_session_ref": old_session_ref, "to_session_ref": args.session_ref,
                            "evidence": evidence, "taken_at": taken_at, "campaign_bridge": bridge},
        "idempotency_key": operation_id, "state": "CONFIRMED", "result_ref": result_ref,
        "result_sha256": result_sha256, "observation_ref": result_ref, "error": None,
    }
    leader_advance = {"ACTIVE": "RELEASING", "RELEASING": "RELEASED", "RELEASED": "RELEASED"}
    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        # T017: the whole verdict (observation, quiescence, checkpoint_head,
        # bridge) was computed from `snapshot`, read outside the lock. Without
        # this guard a worker transitioning DECLARED->PREPARING between the
        # read and the commit would be committed over, and TAKEOVER-APPLIED
        # would be returned where TAKEOVER-WORK-ACTIVE was due.
        if document["revision"] != snapshot.revision:
            raise store.StoreError(store.STATE_DIVERGENCE, "takeover inputs changed during observation")
        target = document["agent_orchestration"]["work_items"][args.work_id]
        source = target["contexts"].get(context_id)
        if (not isinstance(source, dict) or target.get("current_context_id") != context_id
                or source.get("state") not in {"ACTIVE", "QUIESCING"}
                or source.get("leader", {}).get("session_ref") != old_session_ref):
            raise store.StoreError(store.STATE_DIVERGENCE, "takeover source changed")
        if new_context_id in target["contexts"] or operation_id in target["operations"]:
            raise store.StoreError(store.STATE_DIVERGENCE, "takeover already recorded under a different outcome")
        source["state"] = "SUPERSEDED"
        source["leader"]["state"] = leader_advance[source["leader"]["state"]]
        new_context = {
            "context_id": new_context_id, "epoch": next_epoch,
            "predecessor_context_id": context_id, "continuity_ref": operation_id,
            "runtime": source["runtime"], "adapter": source["adapter"],
            "activation": copy.deepcopy(source["activation"]), "campaign": copy.deepcopy(source["campaign"]),
            "scheduler_runs": copy.deepcopy(source["scheduler_runs"]),
            "leader": {"owner_id": new_context_id, "session_ref": args.session_ref,
                       "incarnation": readiness["incarnation"],
                       "fence": next_epoch, "epoch": next_epoch, "state": "ACTIVE",
                       "observation_ref": readiness["ref"], "observation_sha256": readiness["sha256"]},
            "state": "ACTIVE", "policy_sha256": source["policy_sha256"], "inputs_sha256": source["inputs_sha256"],
            "presentation": copy.deepcopy(readiness["presentation"]),
        }
        # T023: the derived identity, never the predecessor's copy.
        new_context["worktree_identity"] = copy.deepcopy(identity)
        target["contexts"][new_context_id] = new_context
        target["operations"][operation_id] = copy.deepcopy(operation)
        target["current_context_id"] = new_context_id
        return document
    try:
        committed = store.transact(root, mutate)
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TAKEOVER-CAS-CONFLICT", exc.message) from exc
    return {"verdict": "TAKEOVER-APPLIED", "work_id": args.work_id, "context_id": new_context_id,
            "from_context_id": context_id, "epoch": next_epoch,
            "succession": {"from_context_id": context_id, "from_session_ref": old_session_ref,
                           "reason": "takeover", "evidence": evidence, "taken_at": taken_at},
            "preserved_resources": retained, "operations_to_reconcile": reconcile,
            "inherited_prepared_workers": inherited_prepared_workers,
            "presentation": readiness["presentation"],
            "store_revision": committed.revision}, EXIT_OK


_FENCE_HOPS = {("DISPATCHED", "REGISTERED"): 2, ("RESULT_RECORDED", "CLOSE_PENDING"): 1}


def _fence_recorded(item: dict[str, Any], operation_id: str, activity_id: str, resource_id: str,
                    session_ref: str) -> str:
    """none | replay | resume | foreign | conflict -- how a recorded fence relates to this caller."""
    operation = item.get("operations", {}).get(operation_id)
    if operation is None:
        return "none"
    activity, resource = item.get("activities", {}).get(activity_id), item.get("resources", {}).get(resource_id)
    if (operation.get("kind") != "activity-fence" or operation.get("state") != "CONFIRMED"
            or operation.get("subject_ids") != [activity_id, resource_id]
            or not isinstance(activity, dict) or activity.get("state") != "FAILED"
            or activity.get("diagnostic_ref") != operation.get("result_ref")
            or not isinstance(resource, dict) or resource.get("state") not in {"CLOSED", "CLOSE_PENDING"}):
        return "conflict"
    requester = operation.get("intended_after", {}).get("requester", {})
    if requester.get("ref") != session_ref:
        return "foreign"
    return "replay" if resource["state"] == "CLOSED" else "resume"


def _fence_conflict(item: dict[str, Any], activity_id: str, resource_id: str, operation_id: str, message: str) -> CliFailure:
    return CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-CAS-CONFLICT", message, extra={
        "activity_state": item.get("activities", {}).get(activity_id, {}).get("state"),
        "resource_state": item.get("resources", {}).get(resource_id, {}).get("state"),
        "operation_id": operation_id})


def _fence_authorization(root: Path, args: argparse.Namespace, scope: str) -> dict[str, Any]:
    """Every way the bundle can fail to authorize is one code (contract activity-fence)."""
    attestation = grill_core_module("attestation")
    if args.authorization is None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-AUTHORIZATION-INVALID", "--authorization is required")
    try:
        bundle = load_checkpoint_attestation(root, args.authorization)
    except CliFailure as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-AUTHORIZATION-INVALID", error.message) from error
    try:
        attestation._validate_human_authorization(bundle, scope)
    except attestation.AttestationError as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-AUTHORIZATION-INVALID", error.reason) from error
    return bundle


def _fence_observe(root: Path, runtime: str, ref: str | None, who: str) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Observe one dispatch; returns (observation, evidence entry, live). Inconclusive raises UNPROVEN."""
    observation, status, liveness = _takeover_observation(root, runtime, ref)  # type: ignore[arg-type]
    if observation["verdict"] == "not_observable":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-NOT-OBSERVABLE", str(ref))
    live = observation["verdict"] != "terminal"
    if live and status not in {"dispatched", "running"}:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", f"FENCE-{who}-UNPROVEN", str(ref))
    return observation, {"session_ref": ref, "observation_ref": observation["reference"],
                         "observation_sha256": observation["digest"], "dispatch_status": status,
                         "liveness": liveness, "verdict": "active" if live else "terminal"}, live


def _fence_prove_requester(root: Path, work_id: str, context: dict[str, Any], session_ref: str, role: str) -> dict[str, Any]:
    if role == "successor":
        readiness = _session_readiness(root, context["runtime"], session_ref, work_id=work_id)
        return {"role": role, "ref": readiness["ref"], "sha256": readiness["sha256"], "incarnation": readiness["incarnation"]}
    _require_current_leader(root, work_id, context, session_ref)
    leader = context["leader"]
    return {"role": role, "ref": leader["session_ref"], "sha256": leader["observation_sha256"],
            "incarnation": leader["incarnation"]}


def gauntlet_activity_fence_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Fence an orphaned/retained specialist activity under exact human authorization.

    Not @_gauntlet_authorized: in the orphan form the context leader is
    terminal and require_authority would refuse first. Preview and apply run
    the same checks in the same order (contract activity-fence).
    """
    root = project_root(args.root)
    if not isinstance(args.session_ref, str) or not args.session_ref:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "gauntlet-activity-fence requires --session-ref")
    store = grill_core_module("store")
    snapshot = store.read_snapshot(root, required=True)
    item = snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(args.work_id)
    if not isinstance(item, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-MIGRATION-REQUIRED", args.work_id)
    activity = item.get("activities", {}).get(args.activity_id)
    if not isinstance(activity, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-ACTIVITY-NOT-FOUND", args.activity_id)
    context_id, resource_id = activity["context_id"], activity["session_resource_id"]
    context = item["contexts"][context_id]
    resource = item.get("resources", {}).get(resource_id)
    if not isinstance(resource, dict) or resource.get("kind") != "session":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-ACTIVITY-STATE", str(resource_id))
    operation_id = "fence-" + hashlib.sha256(canonical({"context": context_id, "activity": args.activity_id})).hexdigest()[:24]
    recorded = _fence_recorded(item, operation_id, args.activity_id, resource_id, args.session_ref)
    if recorded == "conflict":
        raise _fence_conflict(item, args.activity_id, resource_id, operation_id, "fence recorded under a different outcome")
    base = {"work_id": args.work_id, "context_id": context_id, "activity_id": args.activity_id, "operation_id": operation_id,
            "activity_state": "FAILED", "resource_state": "CLOSED"}
    if recorded == "replay":
        operation = item["operations"][operation_id]
        return {"verdict": "FENCE-REUSED", **base, "evidence": operation["intended_after"]["evidence"],
                "requester": operation["intended_after"]["requester"], "store_revision": snapshot.revision}, EXIT_OK
    if recorded == "resume":
        operation = item["operations"][operation_id]
        intended = operation["intended_after"]
        if not args.apply:
            return {"verdict": "FENCE-PREVIEW", **base, "evidence": intended["evidence"], "requester": intended["requester"],
                    "expected_sha256": operation["input_sha256"], "hops": 1, "resume": True}, EXIT_OK
        if args.expected_sha256 != operation["input_sha256"]:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-INPUTS-STALE", "expected_sha256 does not match the recorded fence")
        _fence_prove_requester(root, args.work_id, context, args.session_ref, intended["requester"]["role"])
        return _fence_hop2(root, store, args, base, resource_id, operation_id, operation["input_sha256"], intended)
    pair = (activity.get("state"), resource.get("state"))
    if pair not in _FENCE_HOPS:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-ACTIVITY-STATE", f"{pair[0]}/{pair[1]}")
    bundle = _fence_authorization(root, args, f"{args.work_id}:{context_id}:{args.activity_id}")
    owner = resource.get("identity", {}).get("owner_dispatch")
    specialist_ref = "orca:" + owner if isinstance(owner, str) else None
    specialist, specialist_evidence, specialist_live = _fence_observe(root, context["runtime"], specialist_ref, "SPECIALIST")
    if specialist_live:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-SPECIALIST-ACTIVE", str(specialist_ref))
    leader_ref = context["leader"]["session_ref"]
    leader, leader_evidence, leader_live = _fence_observe(root, context["runtime"], leader_ref, "LEADER")
    if leader_live and args.session_ref != leader_ref:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-LEADER-ACTIVE", leader_ref)
    requester = _fence_prove_requester(root, args.work_id, context, args.session_ref,
                                       "current-leader" if leader_live else "successor")
    evidence = {"specialist": specialist_evidence, "leader": leader_evidence}
    expected = store.jcs_sha256({"work_id": args.work_id, "context_id": context_id, "activity_id": args.activity_id,
        "activity_state": pair[0], "resource_id": resource_id, "resource_state": pair[1], "to_session_ref": args.session_ref,
        "specialist": {"verdict": specialist_evidence["verdict"], "reference": specialist["reference"]},
        "leader": {"verdict": leader_evidence["verdict"], "reference": leader["reference"]},
        "authorization": {key: bundle.get(key) for key in ("scope", "decision", "authorized_by", "receipt_ref", "content_sha256")}})
    hops = _FENCE_HOPS[pair]
    if not args.apply:
        return {"verdict": "FENCE-PREVIEW", **base, "evidence": evidence, "requester": requester,
                "expected_sha256": expected, "hops": hops}, EXIT_OK
    if args.expected_sha256 != expected:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FENCE-INPUTS-STALE", "expected_sha256 does not match reread fence inputs")
    result_ref = f"activity-fence/{operation_id}.json"
    intended = {"reason": "activity-fence", "activity_state": "FAILED", "resource_state": "CLOSED", "evidence": evidence,
                "requester": requester, "authorization": copy.deepcopy(bundle), "successor": "attempt-2-as-new-activity",
                "applied_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    operation = {
        "kind": "activity-fence", "context_id": context_id, "fence": context["leader"]["fence"],
        "subject_ids": [args.activity_id, resource_id], "input_sha256": expected,
        "expected_before": {"context_id": context_id, "activity_id": args.activity_id, "activity_state": pair[0],
                            "resource_id": resource_id, "resource_state": pair[1]},
        "intended_after": intended, "idempotency_key": operation_id, "state": "CONFIRMED", "result_ref": result_ref,
        "result_sha256": store.jcs_sha256({"evidence": evidence, "requester": requester, "authorization": bundle}),
        "observation_ref": result_ref, "error": None}
    fence_receipt = {"ref": specialist_ref + ":fence", "sha256": specialist["digest"]}
    def hop1(document: dict[str, Any]) -> dict[str, Any]:
        if document["revision"] != snapshot.revision:
            raise store.StoreError(store.STATE_DIVERGENCE, "fence inputs changed during observation")
        target = document["agent_orchestration"]["work_items"][args.work_id]
        current, held = target["activities"].get(args.activity_id), target["resources"].get(resource_id)
        if (not isinstance(current, dict) or current.get("state") != pair[0] or current.get("session_resource_id") != resource_id
                or not isinstance(held, dict) or held.get("state") != pair[1] or operation_id in target["operations"]):
            raise store.StoreError(store.STATE_DIVERGENCE, "fence target changed")
        target["operations"][operation_id] = copy.deepcopy(operation)
        current.update({"state": "FAILED", "diagnostic_ref": result_ref})
        receipts = held["evidence_manifest"]["receipts"]
        if all(receipt["ref"] != fence_receipt["ref"] for receipt in receipts):
            receipts.append(dict(fence_receipt))
        held.update({"last_observation": fence_receipt["ref"], "operation_id": operation_id,
                     "state": "CLOSE_PENDING" if pair[1] == "REGISTERED" else "CLOSED"})
        return document
    try:
        committed = store.transact(root, hop1)
    except store.StoreError as exc:
        raise _fence_failure(root, store, args, resource_id, operation_id, exc) from exc
    if hops == 1:
        return {"verdict": "FENCE-APPLIED", **base, "evidence": evidence, "requester": requester,
                "store_revision": committed.revision}, EXIT_OK
    return _fence_hop2(root, store, args, base, resource_id, operation_id, expected, intended)


def _fence_failure(root: Path, store: Any, args: argparse.Namespace, resource_id: str, operation_id: str, exc: Any) -> CliFailure:
    fresh = store.read_snapshot(root, required=True).document["agent_orchestration"]["work_items"][args.work_id]
    return _fence_conflict(fresh, args.activity_id, resource_id, operation_id, exc.message)


def _fence_hop2(root: Path, store: Any, args: argparse.Namespace, base: dict[str, Any], resource_id: str, operation_id: str,
                expected: str, intended: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Second hop: no revision guard (hop 1 stamped a new one), state guard only."""
    def hop2(document: dict[str, Any]) -> dict[str, Any]:
        target = document["agent_orchestration"]["work_items"][args.work_id]
        operation = target["operations"].get(operation_id)
        current, held = target["activities"].get(args.activity_id), target["resources"].get(resource_id)
        if (not isinstance(operation, dict) or operation.get("state") != "CONFIRMED" or operation.get("kind") != "activity-fence"
                or operation.get("input_sha256") != expected or not isinstance(current, dict) or current.get("state") != "FAILED"
                or current.get("diagnostic_ref") != operation.get("result_ref") or not isinstance(held, dict)):
            raise store.StoreError(store.STATE_DIVERGENCE, "fence target changed")
        if held.get("state") != "CLOSE_PENDING":
            raise store.StoreError(store.STATE_DIVERGENCE, "fence already completed")
        held["state"] = "CLOSED"
        return document
    try:
        committed = store.transact(root, hop2)
    except store.StoreError as exc:
        fresh = store.read_snapshot(root, required=True).document["agent_orchestration"]["work_items"][args.work_id]
        if _fence_recorded(fresh, operation_id, args.activity_id, resource_id, args.session_ref) == "replay":
            return {"verdict": "FENCE-REUSED", **base, "evidence": intended["evidence"], "requester": intended["requester"],
                    "store_revision": store.read_snapshot(root, required=True).revision}, EXIT_OK
        raise _fence_conflict(fresh, args.activity_id, resource_id, operation_id, exc.message) from exc
    return {"verdict": "FENCE-APPLIED", **base, "evidence": intended["evidence"], "requester": intended["requester"],
            "store_revision": committed.revision}, EXIT_OK


@_gauntlet_authorized
def gauntlet_cleanup_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    activity_id = getattr(args, "activity_id", None)
    context_id, epoch = getattr(args, "context_id", None), getattr(args, "epoch", None)
    if (activity_id is not None and (args.run_id is not None or args.worker_id is not None)
            or args.worker_id is not None and args.run_id is None
            or (context_id is None) != (epoch is None)):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "mixed or incomplete cleanup selectors")
    root = project_root(args.root)
    runs = grill_core_module("gauntlet_runs")
    contract = grill_core_module("agent_orchestration")
    selected = activity_id is not None or context_id is not None or (args.run_id is not None and args.worker_id is None)
    if not selected and args.run_id is None:
        resolve_gauntlet_subject(root, args.work_id)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SCHEDULING-NOT-AVAILABLE", "cleanup needs a context or run and worker",
                         extra={"work_id": args.work_id})
    item = None
    if selected:
        snapshot = runs.store.read_snapshot(root, required=False)
        item = snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(args.work_id) if snapshot else None
        if not isinstance(item, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-MIGRATION-REQUIRED", args.work_id)
        try:
            contract.require_authority(item, context_id, epoch, args.session_ref)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
        if activity_id is not None and (activity_id not in item["activities"]
                or item["activities"][activity_id]["context_id"] != context_id):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", "activity is not owned by the selected context")
    # T025: candidates counted before the *activity* filters below, so the
    # guard at the end can tell "there was nothing to do" from "there was
    # something and the selection never reached it". Zero candidates is a
    # legitimate no-op. T031: resources owned by another context are not
    # counted here at all -- see the filter below.
    results, retained, candidates = [], [], 0
    if activity_id is None:
        if args.run_id is not None:
            run_ids = [args.run_id]
        else:
            run_ids = list(item["contexts"][context_id]["scheduler_runs"])
        if run_ids:
            _, _, admission, _ = gauntlet_run_admission(args)
            try:
                targets = {run_id: runs._run_for_worker(root, args.work_id, run_id, admission, purpose="cleanup")
                           for run_id in run_ids}
            except (runs.GauntletRunError, runs.store.StoreError) as exc:
                code = runs.store.KEBAB_ALIASES.get(exc.code, exc.code) if isinstance(exc, runs.store.StoreError) else exc.code
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, exc.message) from exc
            for run_id, run in targets.items():
                worker_ids = [args.worker_id] if args.worker_id else sorted(run["workers"])
                candidates += len(worker_ids)
                for worker_id in worker_ids:
                    try:
                        result = runs.cleanup_worker(root, args.work_id, run_id, worker_id, admission)
                        if not selected:
                            return result, EXIT_OK if result.get("verdict") in {"CLEANED", "REUSED"} else EXIT_BLOCKED
                        results.append(result)
                    except (runs.GauntletRunError, runs.store.StoreError) as exc:
                        code = runs.store.KEBAB_ALIASES.get(exc.code, exc.code) if isinstance(exc, runs.store.StoreError) else exc.code
                        if not selected:
                            raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, exc.message) from exc
                        results.append({"run_id": run_id, "worker_id": worker_id, "verdict": "PRESERVED", "code": code})
    if item is not None and args.run_id is None:
        for resource_id, resource in item["resources"].items():
            if resource["origin_context_id"] != context_id:
                # T031: a resource pinned by another context is not something
                # this selection was ever meant to reach, so counting it as a
                # candidate made the guard below refuse a successor that owns
                # nothing -- forever, since T026 leaves no verb to reconcile a
                # predecessor's resource. The hole the guard exists to close
                # is one of *reporting*, not of authorization: the caller must
                # not read success over a resource still open in the store.
                # So report it and let the verdict stop being CLEANED, instead
                # of refusing the cleanup of what this context does own.
                #
                # T034: and only when the selection would have reached it.
                # The collection used to happen before any selector
                # discrimination -- the activity filter is applied further
                # down -- so a cleanup aimed at one activity came back
                # downgraded because of a resource that selection was never
                # meant to touch, and permanently, for the same reason. The
                # run branch and the unselected single-worker path never get
                # here: the loop is guarded by `args.run_id is None`, and the
                # single-worker path returns inside the run loop above, before
                # `retained` is read by the verdict they share.
                in_scope = activity_id is None or resource["activity_id"] == activity_id
                if in_scope and resource["state"] not in {"CLOSED", "REMOVED"}:
                    retained.append({"resource_id": resource_id, "kind": resource["kind"],
                                     "state": resource["state"],
                                     "origin_context_id": resource["origin_context_id"],
                                     "code": "RESOURCE-RETAINED-ELSEWHERE"})
                continue
            candidates += 1
            if (resource["activity_id"] is None
                    or activity_id is not None and resource["activity_id"] != activity_id):
                continue
            # No session-close transport is wired here. Preserve the resource until
            # the existing activity acceptance path records a correlated close.
            closed = resource["state"] in {"CLOSED", "REMOVED"} and bool(resource["result_acceptance_ref"])
            results.append({"resource_id": resource_id, "kind": resource["kind"], "identity": resource["identity"],
                            "state": resource["state"], "verdict": "REUSED" if closed else "UNKNOWN",
                            "code": None if closed else "SESSION-CLOSE-UNPROVEN"})
        if activity_id is not None and not results:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", "activity has no registered resource")
    # T025: candidates existed and the selection reached none of them. With
    # results == [] both any() below are false and the verdict fell through
    # to CLEANED/exit 0, telling the caller that resources still open in the
    # store had been closed. The activity branch already refused this way;
    # the context and run branches get the same code and state. The takeover
    # case that motivated it is now handled by `retained` above, which keeps
    # the verdict honest without refusing.
    #
    # `candidates` is what keeps this narrow. Cleaning a context that owns no
    # resource and no run is a legitimate no-op, not a selection failure, so
    # zero candidates still reaches the verdict below. The unselected
    # single-worker path never gets here at all: it returns inside the loop
    # above with cleanup_worker's own verdict.
    if selected and candidates and not results:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT",
                         "cleanup selection reached none of the registered runs or resources")
    verdict = ("UNKNOWN" if any(result["verdict"] == "UNKNOWN" for result in results) else
               "PRESERVED" if retained or any(result["verdict"] not in {"CLEANED", "REUSED"} for result in results)
               else "CLEANED")
    return {"verdict": verdict, "work_id": args.work_id, "context_id": context_id,
            "epoch": epoch, "resources": results, "retained": retained}, EXIT_OK if verdict == "CLEANED" else EXIT_BLOCKED


@_gauntlet_authorized
def gauntlet_prepare_worker_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Prepare one passive, scoped worker workspace from a fresh admission."""
    root, gauntlet_runs, admission, _record = gauntlet_run_admission(args)
    _require_scheduler_task_phase(root, gauntlet_runs, args, args.worker_id)
    try:
        return gauntlet_runs.prepare_worker(
            root, args.work_id, args.run_id, args.worker_id, args.scope, admission
        ), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        # Store's public vocabulary predates this adapter and uses a small
        # alias table.  Every core/store failure crosses this one JSON
        # boundary as a kebab-cased BLOCKED response.
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


#: Which step's floor governs the workers dispatched under it, per workflow
#: version. Kept beside the sequence tables it belongs to.
EXECUTOR_STEP_BY_VERSION = _workflow_versions.EXECUTOR_STEP_BY_VERSION


def _tier_floors(record: dict[str, Any]) -> tuple[str, str]:
    """FR-002 SSOT: resolve both tier floors from the caller's own current
    activation-pinned tier policy -- never a literal duplicated in
    ``grill_core``, so a future policy change can't silently desync from
    this enforcement point.

    The executor step is looked up by the record's own workflow version. This
    used to index ``minimum_by_step["agent-execute"]`` directly, which raised
    KeyError the moment that step was renamed -- rc=1 with an empty stdout,
    colliding with the NO-GO exit code, so a caller parsing JSON got nothing at
    all. A missing floor is now a named, parseable denial.
    """
    tier_policy = record["tier_policy"]
    version = record.get("workflow", {}).get("version")
    executor = EXECUTOR_STEP_BY_VERSION.get(version)
    if executor is None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TIER-POLICY-VERSION-UNKNOWN",
                         f"activation declares an unknown workflow version: {version}")
    floors = tier_policy.get("minimum_by_step", {})
    supplemental = tier_policy.get("supplemental", {})
    if executor not in floors or "markdown-maintenance" not in supplemental:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TIER-POLICY-STEP-MISSING",
                         f"activation tier policy declares no floor for {executor}")
    return floors[executor], supplemental["markdown-maintenance"]


def _feature_paths(root: Path, feature: str) -> tuple[Path, str, str]:
    """Resolve one feature's spec directory and its two emitted documents."""
    if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]{0,127}", feature or ""):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "--feature is invalid")
    directory = root / "specs" / feature
    if not directory.is_dir():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FEATURE-ABSENT", f"specs/{feature} does not exist")
    return directory, f"specs/{feature}/execution-dag.json", f"specs/{feature}/partition-report.json"


def _next_partition_revision(directory: Path, feature: str) -> tuple[str, str]:
    """Return the first unused, complete rN partition pair."""
    revision = 2
    while True:
        dag = directory / f"execution-dag.r{revision}.json"
        report = directory / f"partition-report.r{revision}.json"
        dag_exists = dag.exists() or dag.is_symlink()
        report_exists = report.exists() or report.is_symlink()
        if dag_exists != report_exists:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PARTITION-REVISION-INCOMPLETE",
                             f"partition revision r{revision} is incomplete")
        if not dag_exists:
            prefix = f"specs/{feature}"
            return f"{prefix}/{dag.name}", f"{prefix}/{report.name}"
        revision += 1


@_gauntlet_authorized
def partition_emit_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """WORKFLOW v4 `partition`: derive the Execution DAG from tasks.md.

    Preview-first like every other mutating verb here: without ``--apply`` it
    returns the two documents and writes nothing. The grouping itself is
    deterministic and lives in ``grill_core.partition`` -- see ADR-0012 for why
    it may not be a judgement call.
    """
    root = project_root(args.root)
    resolve_gauntlet_subject(root, args.work_id)
    _require_visual_gate(root, args.work_id)
    partition = grill_core_module("partition")
    directory, dag_ref, report_ref = _feature_paths(root, args.feature)
    tasks_path = directory / "tasks.md"
    if not tasks_path.is_file():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASKS-ABSENT", f"specs/{args.feature}/tasks.md does not exist")
    text = safe_read_regular_fd(root, tasks_path).decode("utf-8", errors="replace")
    adopted = partition.TASK_FILES_MARKER in text
    groups = args.groups
    if groups is None:
        groups = json.loads(_policy_path(root, args.work_id).read_bytes()).get("partition_groups", 3)
    if adopted:
        # Every sealed DAG is evidence, never an input to overwrite. A changed
        # task source receives the next explicit revision pair.
        dag_ref, report_ref = _next_partition_revision(directory, args.feature)
    try:
        dag, report = (partition.partition_task_files(text, feature=args.feature, groups=groups, root=root)
                       if adopted else partition.partition(
                           text, feature=args.feature, sidecar_dir=f"specs/{args.feature}/implement",
                           groups=groups,
                       ))
    except partition.PartitionError as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message,
                         extra={"work_id": args.work_id, **error.extra}) from error
    payload = {
        "verdict": report["verdict"], "work_id": args.work_id, "feature": args.feature,
        "dag": dag_ref, "report": report_ref, "max_workers": dag["max_workers"],
        "nodes": len(dag["nodes"]), "deferred_to_leader": report["deferred_to_leader"],
        "unmapped_task_ids": report.get("unmapped_task_ids", []),
        "read_only_tasks": report.get("read_only_tasks", []),
    }
    if not args.apply:
        return {**payload, "verdict": "PREVIEW", "partition_verdict": report["verdict"],
                "execution_dag": dag, "partition_report": report}, EXIT_OK
    _require_visual_gate(root, args.work_id)
    for target, document in ((root / dag_ref, dag), (root / report_ref, report)):
        reject_symlink_chain(root, target, allow_missing=True)
        if adopted and target.exists():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DAG-SEALED", f"partition output is already sealed: {target.relative_to(root)}")
        target.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    return {**payload, "verdict": "APPLIED", "partition_verdict": report["verdict"]}, EXIT_OK


def gauntlet_partition_brief_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Emit one worker's brief from the DAG and the partition report.

    Generated by command rather than written as prose so the same node always
    yields the same brief. The brief is a hint; the fence is the worker's grant
    plus the diff check at convergence.
    """
    root = project_root(args.root)
    dag = _read_json_document(root, args.dag, "DAG-MALFORMED")
    report = _read_json_document(root, args.report, "PARTITION-REPORT-MALFORMED")
    nodes = {node["id"]: node for node in dag.get("nodes", []) if isinstance(node, dict)}
    entries = {entry["id"]: entry for entry in report.get("nodes", []) if isinstance(entry, dict)}
    if args.node_id not in nodes or args.node_id not in entries:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DAG-NODE-UNKNOWN", f"no such node: {args.node_id}")
    node, entry = nodes[args.node_id], entries[args.node_id]
    if dag.get("schema") == "grill-gauntlet-execution-dag/v2":
        if (dag.get("tasks_contract") != "task-files/v1" or entry.get("task_ids") != node.get("task_ids")
                or entry.get("files") != node.get("files") or entry.get("result_files") != node.get("result_files")):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-RESULT-DIVERGENT", "DAG and report do not bind the same node")
        phase_match = re.match(r"^p(\d+)-", args.node_id)
        if phase_match is None:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-PHASE-PENDING", "v2 node has no phase identity")
        # This command only renders a read-only brief.  The mutable scheduler
        # entrances enforce the phase barrier against current accepted-task
        # receipts before a wave or worker can exist.
        results = node["result_files"]
        lines = [
            f"You are worker {args.node_id} of feature {dag.get('feature')}.", "",
            "Tasks assigned to you: " + ", ".join(node["task_ids"]) + ".", "Paths you may write:",
            *(f"  - {path}" for path in node["files"]), "",
            "Do not edit tasks.md. Write exactly one grill-task-result/v1 per assigned task:",
            *(f"  - {task_id}: {path}" for task_id, path in results.items()),
            "Do not write .grill/ or .specify/reports/. The leader observes the terminal commit.",
        ]
        return {"verdict": "BRIEF", "node_id": args.node_id, "tier": node["tier"],
                "parallel": node["parallel"], "files": node["files"], "task_ids": node["task_ids"],
                "result_files": results, "brief": "\n".join(lines)}, EXIT_OK
    sidecar = next((f for f in node["files"] if f.endswith(f"/{args.node_id}.tasks.json")), None)
    lines = [
        f"You are worker {args.node_id} of feature {dag.get('feature')}.",
        "",
        "Tasks assigned to you: " + ", ".join(entry["task_ids"]) + ".",
        "Paths you may write:",
        *(f"  - {path}" for path in node["files"]),
        "",
        "Do not edit tasks.md. Record your result in "
        + (sidecar or "your node sidecar")
        + " and let the leader mark [X] after the merge.",
        "Do not write .grill/ or .specify/reports/. Do not checkpoint the step.",
        "Writing outside the paths above fails the merge with GRANT-SCOPE-VIOLATION.",
    ]
    return {"verdict": "BRIEF", "node_id": args.node_id, "tier": node["tier"],
            "parallel": node["parallel"], "files": node["files"],
            "task_ids": entry["task_ids"], "scope": entry["scope"],
            "brief": "\n".join(lines)}, EXIT_OK


@_gauntlet_authorized
def gauntlet_tasks_import_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root, runs, admission, record = gauntlet_run_admission(args)
    sources = {}
    for value in args.source_task:
        task, separator, source = value.partition("=")
        if not separator or not task or not source or task in sources:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "--source-task requires unique TASK=RUN entries")
        sources[task] = source
    try:
        execute_floor, markdown_floor = _tier_floors(record)
        runs.validate_execution_dag(root, args.work_id, args.run_id, args.dag, admission,
            agent_execute_floor=execute_floor, markdown_floor=markdown_floor)
        return runs.import_task_results(root, args.work_id, args.run_id, args.dag, sources, admission,
            apply=args.apply, expected_sha256=args.expected_sha256), EXIT_OK
    except (runs.GauntletRunError, runs.store.StoreError) as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
    except (UnicodeError, ValueError) as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-IMPORT-DIVERGENT", "invalid evidence document") from error


@_gauntlet_authorized
def gauntlet_tasks_rebase_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Carry unchanged accepted tasks into a newly partitioned successor DAG."""
    root, runs, admission, record = gauntlet_run_admission(args)
    try:
        execute_floor, markdown_floor = _tier_floors(record)
        runs.validate_execution_dag(root, args.work_id, args.run_id, args.dag, admission,
            agent_execute_floor=execute_floor, markdown_floor=markdown_floor)
        return runs.rebase_task_results(root, args.work_id, args.run_id, args.dag,
            args.source_run_id, args.source_dag, args.task, admission,
            source_commit=args.source_commit, apply=args.apply,
            expected_sha256=args.expected_sha256), EXIT_OK
    except (runs.GauntletRunError, runs.store.StoreError) as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
    except (UnicodeError, ValueError) as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-IMPORT-DIVERGENT", "invalid evidence document") from error


@_gauntlet_authorized
def gauntlet_tasks_reconcile_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    store = grill_core_module("store")
    # Same work-item lock as migration; every input is read after acquiring it.
    with store.work_lock(root, args.work_id) if args.apply else contextlib.nullcontext():
        with store.orchestrator_lock(store.store_paths(root)) if args.apply else contextlib.nullcontext():
            if args.apply:
                store.require_orchestration_authority(root, args.work_id, purpose="tasks-reconcile")
            return _gauntlet_tasks_reconcile_locked(args)


def _gauntlet_tasks_reconcile_locked(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Mark completed tasks in tasks.md once, on the coordinator's branch.

    Deterministic bookkeeping, no model in the loop: it reads the sidecars the
    workers already merged and rewrites the checkboxes. Workers never touch
    tasks.md -- if it were in two nodes' scopes the wave would be rejected for
    overlap, and if it were in one the others would be writing out of scope.
    """
    root = project_root(args.root)
    resolve_gauntlet_subject(root, args.work_id)
    dag = _read_json_document(root, args.dag, "DAG-MALFORMED")
    feature = dag.get("feature")
    directory, _, _ = _feature_paths(root, feature)
    tasks_path = directory / "tasks.md"
    if not tasks_path.is_file():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASKS-ABSENT", f"specs/{feature}/tasks.md does not exist")
    if dag.get("schema") == "grill-gauntlet-execution-dag/v2":
        partition = grill_core_module("partition")
        text = safe_read_regular_fd(root, tasks_path).decode("utf-8", errors="replace")
        try:
            tasks = partition.parse_task_files(text, feature=feature, root=root)
            semantic = partition.tasks_semantic_sha256(text, tasks)
        except partition.PartitionError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
        if dag.get("tasks_semantic_sha256") != semantic:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASKS-SOURCE-STALE", "tasks.md differs from the DAG pin")
        valid = {task.id: task for task in tasks}
        runs = grill_core_module("gauntlet_runs")
        try:
            imported = runs.verified_task_import(root, args.work_id, args.run_id) if args.run_id else None
        except (runs.GauntletRunError, runs.store.StoreError) as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
        if imported and imported["dag_content_sha256"] != runs.store.jcs_sha256(dag):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DAG-CONTENT-MISMATCH", "reconcile DAG differs from imported DAG")
        completed: set[str] = set()
        missing: list[str] = []
        for node in dag.get("nodes", []):
            if not isinstance(node, dict):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DAG-MALFORMED", "node is invalid")
            for task_id, result_path in node.get("result_files", {}).items():
                task = valid.get(task_id)
                target = root / result_path
                if task is None or task.result != result_path or not target.is_file():
                    missing.append(str(task_id))
                    continue
                result = _read_json_document(root, result_path, "TASK-RESULT-MISSING")
                accepted = imported["tasks"].get(task_id) if imported else None
                if accepted:
                    origin, seen = imported, set()
                    # A successor can mix tasks created locally in an
                    # intermediate run with tasks inherited from its import.
                    # Follow only this task while revalidating every receipt.
                    while origin["schema"] == "grill-task-import/v2":
                        source_run_id = origin["source_run_id"]
                        if source_run_id in seen:
                            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-IMPORT-DIVERGENT",
                                             "task import ancestry is cyclic")
                        seen.add(source_run_id)
                        try:
                            source = runs.verified_task_import(root, args.work_id, source_run_id,
                                tasks_commit=origin["source_commit"])
                        except (runs.GauntletRunError, runs.store.StoreError) as error:
                            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
                        inherited = source["tasks"].get(task_id) if source else None
                        if inherited is None:
                            break
                        origin, accepted = source, inherited
                expected_run = accepted["source_run_id"] if accepted else args.run_id
                try:
                    runs.validate_task_result(result, work_id=args.work_id, task_id=task_id,
                        node_id=accepted["node_id"] if accepted else node.get("id"), run_id=expected_run)
                except runs.GauntletRunError as error:
                    raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
                completed.add(task_id)
        marked: list[str] = []
        lines = []
        for line in text.splitlines(keepends=True):
            match = re.match(r"^(- \[)[ xX](\]\s+)(T\d+)", line)
            if match and match.group(3) in completed and not line.startswith("- [X]"):
                line = line[:len(match.group(1))] + "X" + line[len(match.group(1)) + 1:]
                marked.append(match.group(3))
            lines.append(line)
        payload = {"verdict": "PREVIEW", "work_id": args.work_id, "feature": feature,
                   "marked": sorted(marked), "completed": sorted(completed), "missing_results": sorted(missing),
                   "tasks_semantic_sha256": semantic}
        if not args.apply:
            return payload, EXIT_OK
        reject_symlink_chain(root, tasks_path, allow_missing=False)
        atomic_write(root, tasks_path, "".join(lines).encode("utf-8"))
        return {**payload, "verdict": "APPLIED"}, EXIT_OK
    completed: set[str] = set()
    missing: list[str] = []
    for node in dag.get("nodes", []):
        sidecar = next((f for f in node.get("files", []) if f.endswith(f"/{node['id']}.tasks.json")), None)
        if sidecar is None or not (root / sidecar).is_file():
            missing.append(node["id"])
            continue
        document = _read_json_document(root, sidecar, "SIDECAR-MALFORMED")
        for task_id in document.get("completed", []):
            if isinstance(task_id, str):
                completed.add(task_id)
    text = safe_read_regular_fd(root, tasks_path).decode("utf-8", errors="replace")
    marked: list[str] = []
    lines = []
    for line in text.splitlines(keepends=True):
        # Read both `[x]` and `[X]`; write one. The corpus uses the lowercase
        # form and speckit-implement's own instructions use the uppercase one.
        match = re.match(r"^(- \[)[ xX](\]\s+)(T\d+)", line)
        if match and match.group(3) in completed and not line.startswith("- [X]"):
            line = line[:len(match.group(1))] + "X" + line[len(match.group(1)) + 1:]
            marked.append(match.group(3))
        lines.append(line)
    payload = {"verdict": "PREVIEW", "work_id": args.work_id, "feature": feature,
               "marked": sorted(marked), "completed": sorted(completed),
               "missing_sidecars": missing}
    if not args.apply:
        return payload, EXIT_OK
    reject_symlink_chain(root, tasks_path, allow_missing=False)
    atomic_write(root, tasks_path, "".join(lines).encode("utf-8"))
    return {**payload, "verdict": "APPLIED"}, EXIT_OK


@_gauntlet_authorized
def task_files_migrate_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Apply only the current, independently reviewed proposal under its authority fence."""
    root = project_root(args.root)
    resolve_gauntlet_subject(root, args.work_id)
    directory, _, _ = _feature_paths(root, args.feature)
    current_path = directory / "tasks.md"
    proposal_ref = args.proposal
    if (not isinstance(proposal_ref, str) or Path(proposal_ref).parent != directory.relative_to(root)
            or Path(proposal_ref).name in {"", ".", "..", "tasks.md"}):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "--proposal must be a separate feature-local file")
    store = grill_core_module("store")
    contract = grill_core_module("agent_orchestration")
    partition = grill_core_module("partition")

    def preview() -> tuple[dict[str, Any], bytes]:
        _, _, document, item, _context = _activity_policy(
            root, args.work_id, args.context_id, args.epoch, args.session_ref)
        if not current_path.is_file():
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASKS-ABSENT", str(current_path))
        current_raw = safe_read_regular_fd(root, current_path)
        proposal_raw = safe_read_regular_fd(root, root / proposal_ref)
        try:
            current, proposal = current_raw.decode("utf-8"), proposal_raw.decode("utf-8")
            accepted = re.findall(r"^- \[[xX]\]\s+(T\d+)", current, re.MULTILINE)
            result = contract.task_files_migration_preview(
                current, proposal, expected_sha256=hash_bytes(current_raw), accepted_task_ids=accepted)
            tasks = partition.parse_task_files(proposal, feature=args.feature, root=root)
            previous_tasks = (partition.parse_task_files(current, feature=args.feature, root=root)
                              if partition.TASK_FILES_MARKER in current else [])
            contract.require_task_files_review(item, context_id=args.context_id,
                author_id=args.author_activity, reviewer_id=args.review_activity,
                proposal={"path": proposal_ref, "sha256": hash_bytes(proposal_raw), "size": len(proposal_raw)})
        except (contract.OrchestrationError, partition.PartitionError, UnicodeError) as exc:
            code = getattr(exc, "code", str(exc) if isinstance(exc, contract.OrchestrationError) else "TASK-FILES-INVALID")
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, "migration inputs are not current") from exc
        if any(not re.search(rf"^- \[[xX]\]\s+{re.escape(task_id)}(?:\s|$)", proposal, re.MULTILINE) for task_id in accepted):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-RESULT-DIVERGENT", "accepted checkbox was reopened")
        for activity_id in (args.author_activity, args.review_activity):
            activity = item["activities"][activity_id]
            if hash_bytes(safe_read_regular_fd(root, root / activity["result_ref"])) != activity["result_sha256"]:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASKS-SOURCE-STALE", "specialist result changed")
        active, unknown = _continuity_quiescence(document, item, args.work_id)
        if active or unknown or any(op.get("state") in {"INTENT", "APPLIED", "UNKNOWN"} for op in item["operations"].values()):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTINUITY-ACTIVE-WORK", "migration requires quiescence")
        previous_files = {task.id: list(task.files) for task in previous_tasks}
        files_changes = [{"task_id": task.id, "before": previous_files.get(task.id), "after": list(task.files)}
                         for task in tasks if previous_files.get(task.id) != list(task.files)]
        semantic = partition.tasks_semantic_sha256(current, previous_tasks) if previous_tasks else None
        affected_dags = []
        for path in sorted(directory.glob("execution-dag*.json")):
            raw = safe_read_regular_fd(root, path)
            dag = json.loads(raw)
            if dag.get("feature") != args.feature:
                continue
            if dag.get("schema") == "grill-gauntlet-execution-dag/v2" and dag.get("tasks_semantic_sha256") != semantic:
                continue
            affected_dags.append({"path": path.relative_to(root).as_posix(), "sha256": hash_bytes(raw),
                                  "dag_content_sha256": store.jcs_sha256(dag),
                                  "revision": "current" if semantic is not None and dag.get("tasks_semantic_sha256") == semantic else "legacy-unproven"})
        dag_hashes = {entry["dag_content_sha256"] for entry in affected_dags}
        runs = document.get("work_items", {}).get(args.work_id, {}).get("gauntlet", {}).get("runs", {})
        affected_runs = [{"run_id": run_id, "state": run["state"], "dag_content_sha256": run["dag_content_sha256"]}
                         for run_id, run in sorted(runs.items()) if run.get("dag_content_sha256") in dag_hashes]
        inputs = {"work_id": args.work_id, "feature": args.feature, "root": str(root),
                  "context_id": args.context_id, "epoch": args.epoch, "session_ref": args.session_ref,
                  "store_sha256": store.jcs_sha256(document), "proposal": proposal_ref,
                  "current_sha256": result["current_sha256"], "proposal_sha256": result["proposal_sha256"],
                  "author_activity": args.author_activity, "review_activity": args.review_activity,
                  "files_changes": files_changes, "affected_dags": affected_dags, "affected_runs": affected_runs}
        return {**result, **inputs, "expected_sha256": store.jcs_sha256(inputs),
                "tasks": [task.id for task in tasks]}, proposal_raw

    payload, proposal_raw = preview()
    if not args.apply:
        return payload, EXIT_OK
    if args.expected_sha256 != payload["expected_sha256"] or (
            args.expected_proposal_sha256 is not None and args.expected_proposal_sha256 != payload["proposal_sha256"]):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASKS-SOURCE-STALE", "migration changed after preview")
    with store.work_lock(root, args.work_id), store.orchestrator_lock(store.store_paths(root)):
        fresh, proposal_raw = preview()
        if fresh != payload:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASKS-SOURCE-STALE", "migration changed before apply")
        atomic_write(root, current_path, proposal_raw)
    return {**payload, "verdict": "APPLIED"}, EXIT_OK


def _read_json_document_bytes(root: Path, reference: Any, code: str) -> tuple[dict[str, Any], bytes]:
    """Read one repo-relative JSON document through the safe-path boundary."""
    if not isinstance(reference, str) or not reference:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "a document path is required")
    candidate = Path(reference)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", f"unsafe path: {reference}")
    target = root / candidate
    if not target.is_file():
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, f"document is unavailable: {reference}")
    try:
        raw = safe_read_regular_fd(root, target)
        return json.loads(raw), raw
    except ValueError as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, f"document is not valid JSON: {reference}") from error


def _read_json_document(root: Path, reference: Any, code: str) -> dict[str, Any]:
    return _read_json_document_bytes(root, reference, code)[0]


def _task_phase_documents(root: Path, gauntlet_runs: Any,
                          args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], str] | None:
    """Resolve the v2 DAG/report pair; ``None`` preserves v1 scheduling."""
    dag_ref = getattr(args, "dag", None)
    if isinstance(dag_ref, str):
        try:
            dag, _ = _read_json_document_bytes(root, dag_ref, "DAG-MALFORMED")
        except CliFailure:
            return {}, {}, "0" * 64
        if dag.get("schema") != gauntlet_runs.DAG_V2_SCHEMA:
            return None
        name = Path(dag_ref).name
        if name == "execution-dag.json":
            report_ref = str(Path(dag_ref).with_name("partition-report.json"))
        elif re.fullmatch(r"execution-dag\.r[1-9][0-9]*\.json", name):
            report_ref = str(Path(dag_ref).with_name(name.replace("execution-dag", "partition-report", 1)))
        else:
            return dag, {}, gauntlet_runs.store.jcs_sha256(dag)
        try:
            report, _ = _read_json_document_bytes(root, report_ref, "PARTITION-REPORT-MALFORMED")
        except CliFailure:
            report = {}
        return dag, report, gauntlet_runs.store.jcs_sha256(dag)

    try:
        run = gauntlet_runs._read_runs(root, args.work_id).get(args.run_id)
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError):
        return None
    pin = run.get("dag_content_sha256") if isinstance(run, dict) else None
    if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin):
        return None
    for candidate in sorted((root / "specs").glob("*/execution-dag*.json")):
        try:
            dag, _ = _read_json_document_bytes(root, str(candidate.relative_to(root)), "DAG-MALFORMED")
        except CliFailure:
            continue
        if gauntlet_runs.store.jcs_sha256(dag) != pin:
            continue
        if dag.get("schema") != gauntlet_runs.DAG_V2_SCHEMA:
            return None
        name = candidate.name
        report_ref = str(candidate.relative_to(root).with_name(name.replace("execution-dag", "partition-report", 1)))
        try:
            report, _ = _read_json_document_bytes(root, report_ref, "PARTITION-REPORT-MALFORMED")
        except CliFailure:
            report = {}
        return dag, report, gauntlet_runs.store.jcs_sha256(dag)
    return {}, {}, "0" * 64


def _require_scheduler_task_phase(root: Path, gauntlet_runs: Any,
                                  args: argparse.Namespace, node_ids: Any) -> None:
    """Run the v2 phase fence before any mutable scheduler primitive."""
    documents = _task_phase_documents(root, gauntlet_runs, args)
    if documents is None:
        targets = [1]
        dag = report = None
        dag_sha256 = "0" * 64
        legacy = True
    else:
        dag, report, dag_sha256 = documents
        raw_ids = [node_ids] if isinstance(node_ids, str) else node_ids
        targets = []
        if not isinstance(raw_ids, (list, tuple)):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-PHASE-PENDING", "v2 node has no phase identity")
        for node_id in raw_ids:
            match = re.match(r"^p(\d+)-", node_id) if isinstance(node_id, str) else None
            if match is None:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-PHASE-PENDING", "v2 node has no phase identity")
            phase = int(match.group(1))
            if phase not in targets:
                targets.append(phase)
        legacy = False
        accepted_tasks = _scheduler_accepted_tasks(root, args.work_id, dag, dag_sha256, run_id=args.run_id)
    for target_phase in targets:
        try:
            guard = gauntlet_runs.task_phase_barrier(
                dag, report, target_phase=target_phase, dag_content_sha256=dag_sha256, legacy=legacy,
                accepted_tasks=None if legacy else accepted_tasks,
            )
        except gauntlet_runs.GauntletRunError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
        if guard["pending"]:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-PHASE-PENDING", ",".join(guard["pending"]))


def _scheduler_accepted_tasks(root: Path, work_id: str, dag: Mapping[str, Any],
                              dag_sha256: str, *, run_id: str | None = None) -> dict[str, Any]:
    """Project accepted task activities without rewriting the sealed DAG."""
    store = grill_core_module("store")
    snapshot = store.read_snapshot(root)
    item = snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(work_id)
    if not isinstance(item, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-PHASE-PENDING", "orchestration item is absent")
    context_id = item.get("current_context_id")
    contexts = item.get("contexts", {})
    lineage: set[str] = set()
    cursor = context_id
    while isinstance(cursor, str) and cursor not in lineage:
        context = contexts.get(cursor)
        if not isinstance(context, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-PHASE-PENDING", "context lineage is incomplete")
        lineage.add(cursor)
        cursor = context.get("predecessor_context_id")
    if cursor is not None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-PHASE-PENDING", "context lineage is cyclic")
    semantic = dag.get("tasks_semantic_sha256")
    accepted = dict(dag.get("accepted_tasks") or {})
    if run_id is not None:
        runs = grill_core_module("gauntlet_runs")
        try:
            imported = runs.verified_task_import(root, work_id, run_id)
        except (runs.GauntletRunError, runs.store.StoreError) as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message) from error
        if imported:
            if imported["dag_content_sha256"] != dag_sha256 or dag_sha256 != store.jcs_sha256(dag):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DAG-CONTENT-MISMATCH", "phase DAG differs from import")
            # The verified 6.0.20 receipt binds raw DAG bytes. Preserve it and
            # project canonical bindings only after its full evidence check.
            accepted.update({task_id: {**receipt, "task_binding": {
                **receipt["task_binding"], "dag_content_sha256": dag_sha256}}
                for task_id, receipt in imported["tasks"].items()})
    for activity_id, activity in item.get("activities", {}).items():
        if not isinstance(activity, dict) or activity.get("state") != "ACCEPTED":
            continue
        binding = activity.get("task_binding")
        activity_context = activity.get("context_id")
        if (activity.get("step_id") != "implement-parallel" or activity_context not in lineage
                or activity.get("accepted_by_context") != activity_context or not isinstance(binding, dict)
                or binding.get("tasks_semantic_sha256") != semantic
                or binding.get("dag_content_sha256") != dag_sha256):
            continue
        task_id = binding.get("task_id")
        if not isinstance(task_id, str):
            continue
        receipt = {"state": "ACCEPTED", "task_binding": binding,
                   "activity_id": activity_id, "acceptance_ref": activity.get("acceptance_ref")}
        previous = accepted.get(task_id)
        if previous is not None and (previous.get("state"), previous.get("task_binding")) != (
                receipt["state"], receipt["task_binding"]):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "TASK-RESULT-DIVERGENT", task_id)
        accepted[task_id] = receipt
    return accepted


def gauntlet_dag_validate_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-003 (FR-003/FR-004/FR-006): fail-closed Execution DAG validation."""
    root, gauntlet_runs, admission, record = gauntlet_run_admission(args)
    agent_execute_floor, markdown_floor = _tier_floors(record)
    try:
        return gauntlet_runs.validate_execution_dag(
            root, args.work_id, args.run_id, args.dag, admission,
            agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor,
        ), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


@_gauntlet_authorized
def gauntlet_wave_declare_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-003 (FR-004/FR-005, ADR-0013): declare the run's next Execution Wave."""
    root, gauntlet_runs, admission, record = gauntlet_run_admission(args)
    _require_scheduler_task_phase(root, gauntlet_runs, args, args.node_id)
    agent_execute_floor, markdown_floor = _tier_floors(record)
    try:
        return gauntlet_runs.declare_wave(
            root, args.work_id, args.run_id, args.dag, args.node_id, admission,
            activation_max_workers=record["limits"]["max_workers"],
            agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor,
        ), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


@_gauntlet_authorized
def gauntlet_converge_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-004 (FR-001-FR-005): integrate one wave into the execution branch.

    The work item's recorded ``execution_branch`` is resolved here, from the
    same ``development`` block ``checkpoint``/``phase-turn`` already read, and
    threaded down explicitly -- ``gauntlet_runs`` is a hash-only coordinator
    boundary that never reads work-item state for itself.
    """
    root, gauntlet_runs, admission, record = gauntlet_run_admission(args)
    item = resolve_gauntlet_subject(root, args.work_id)
    _, state = read_development_state(root, item, args.work_id)
    development = state.get("development")
    execution_branch = development.get("execution_branch") if isinstance(development, dict) else None
    agent_execute_floor, markdown_floor = _tier_floors(record)
    try:
        return gauntlet_runs.converge_wave(
            root, args.work_id, args.run_id, args.dag, args.wave_id, admission,
            execution_branch=execution_branch,
            agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor,
        ), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


@_gauntlet_authorized
def gauntlet_run_abandon_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-004 (FR-014, ADR-0020): mark one irrecoverable run BLOCKED.

    The only Gauntlet control that deliberately skips the current-activation
    half of the admission boundary: the identity that boundary would compare
    is exactly the one this command reads off the target run instead, and a
    run stale enough to need abandoning is by definition one whose identity
    no longer matches. Path resolution is unchanged -- root and work-item
    existence are not identity.

    The ``human-authorization/v1`` bundle is loaded by the same reader
    ``checkpoint`` already uses and validated standalone, without
    ``judge_checkpoint_attestation``'s resolution/dispatch/invocation chain,
    which this command has none of. Every way the bundle can fail to be a
    valid authorization -- absent, unreadable, malformed, out of scope, not
    approved -- is one public code: they all mean the same thing.
    """
    root = project_root(args.root)
    resolve_gauntlet_subject(root, args.work_id)
    gauntlet_runs = grill_core_module("gauntlet_runs")
    attestation = grill_core_module("attestation")
    try:
        bundle = load_checkpoint_attestation(root, args.attestation)
    except CliFailure as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ABANDON-AUTHORIZATION-INVALID", error.message,
                         extra={"work_id": args.work_id}) from error
    try:
        attestation._validate_human_authorization(bundle, args.run_id)
    except attestation.AttestationError as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ABANDON-AUTHORIZATION-INVALID", error.reason,
                         extra={"work_id": args.work_id}) from error
    try:
        return gauntlet_runs.abandon_run(root, args.work_id, args.run_id, bundle), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


@_gauntlet_authorized
def gauntlet_worker_declare_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-003 (FR-007): mint one first-dispatch worker, ``worker_id = node_id``."""
    root, gauntlet_runs, admission, record = gauntlet_run_admission(args)
    _require_scheduler_task_phase(root, gauntlet_runs, args, args.node_id)
    agent_execute_floor, markdown_floor = _tier_floors(record)
    try:
        return gauntlet_runs.declare_worker(
            root, args.work_id, args.run_id, args.node_id, args.wave_id, args.tier, args.files, args.dag, admission,
            agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor,
            runtime=record["runtime"]["id"],
        ), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


@_gauntlet_authorized
def gauntlet_progress_record_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-003 (FR-008(d)): renew one worker's lease past its original window."""
    root, gauntlet_runs, admission, _record = gauntlet_run_admission(args)
    try:
        return gauntlet_runs.record_progress(root, args.work_id, args.run_id, args.worker_id, admission), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


@_gauntlet_authorized
def gauntlet_worker_terminal_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-003 (FR-009/FR-010): terminate one worker, success or failure."""
    root, gauntlet_runs, admission, _record = gauntlet_run_admission(args)
    try:
        return gauntlet_runs.terminate_worker(
            root, args.work_id, args.run_id, args.worker_id, args.outcome, args.failure_class, admission,
        ), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


@_gauntlet_authorized
def gauntlet_worker_session_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Bind a scheduler worker to its Orca Dispatch and drain its exact release."""
    root, runs, admission, record = gauntlet_run_admission(args)
    runtime = grill_core_module("agent_runtime")
    store = runs.store
    snapshot = store.read_snapshot(root, required=True)
    item = snapshot.document["agent_orchestration"]["work_items"][args.work_id]
    context_id = item["current_context_id"]
    try:
        run = runs._run_for_worker(root, args.work_id, args.run_id, admission, purpose="cleanup")
        wave_id = runs._worker_wave_id(root, args.work_id, args.run_id, args.worker_id)
        target, _ = runs._workspace_identity(root, args.work_id, args.run_id, args.worker_id, run["admission"])
    except runs.GauntletRunError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.message) from exc
    worker = run.get("workers", {}).get(args.worker_id)
    if not isinstance(worker, dict) or not isinstance(worker.get("workspace"), dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORKER-NOT-FOUND", args.worker_id)
    dispatch_id = args.dispatch.removeprefix("orca:")
    if not re.fullmatch(r"ctx[-_][A-Za-z0-9_-]+", dispatch_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", args.dispatch)
    source_ref = "orca:" + dispatch_id
    resource_id = "session-" + hashlib.sha256(f"{args.run_id}:{args.worker_id}".encode()).hexdigest()[:24]
    resource = item["resources"].get(resource_id)
    worker_runtime = (resource.get("identity", {}).get("provider") if isinstance(resource, dict)
                      else record["runtime"]["id"])
    boundary = _leader_boundary(target, worker_runtime, source_ref, args.work_id)
    if (resource is not None and resource.get("state") == "CLOSED" and args.phase == "release"
            and resource.get("identity", {}).get("owner_dispatch") == dispatch_id
            and resource.get("scheduler_run_id") == args.run_id
            and resource.get("worker_id") == args.worker_id and resource.get("wave_id") == wave_id
            and resource.get("result_acceptance_ref") == args.result):
        return {"verdict": "REUSED", "resource_id": resource_id, "dispatch": dispatch_id}, EXIT_OK
    if args.phase == "register":
        if resource is not None:
            if (resource.get("identity", {}).get("owner_dispatch") != dispatch_id
                    or resource.get("scheduler_run_id") != args.run_id
                    or resource.get("worker_id") != args.worker_id or resource.get("wave_id") != wave_id):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", args.worker_id)
            return {"verdict": "REUSED", "resource_id": resource_id, "dispatch": dispatch_id}, EXIT_OK
        if not runs._workspace_is_registered(root, target, worker["workspace"]):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", args.worker_id)
        if worker["state"] not in {"PREPARED", "TERMINAL", "FAILED"}:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORKER-NOT-ELIGIBLE", args.worker_id)
        try:
            show = runtime._object(boundary.read(["orchestration", "worker-show", "--dispatch", dispatch_id, "--json"]), "Orca worker-show")
            handle = show["terminal"]["handle"]
            observed = runtime.LeaderBoundary(source_ref, target, record["runtime"]["id"], handle, boundary.read).observe(
                allow_settled=show["worker"].get("stage") == "settled")
            if worker["state"] != "PREPARED" and (show["worker"].get("stage") != "settled"
                    or show["worker"].get("state") != (
                        "succeeded" if worker["state"] == "TERMINAL" else "failed")):
                raise ValueError("settlement differs from worker outcome")
        except (runtime.RuntimeError, KeyError, TypeError, ValueError) as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", str(exc)) from exc
        identity = {key: observed[key] for key in ("provider", "adapter", "host", "runtime_instance", "handle",
            "incarnation", "owner_dispatch", "task_id", "dispatch_incarnation", "worktree_id")}
        created = {"kind": "session", "agent_id": observed["provider"], "activity_id": None,
            "scheduler_run_id": args.run_id, "worker_id": args.worker_id, "wave_id": wave_id,
            "origin_context_id": context_id, "identity": identity,
            "creation_observation": {"kind": "session", "identity": copy.deepcopy(identity),
                "source_ref": source_ref, "source_sha256": observed["source_sha256"],
                "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            "result_acceptance_ref": None,
            "evidence_manifest": {"files": [], "receipts": [{"ref": source_ref, "sha256": observed["source_sha256"]}],
                                  "terminal_head": None, "integrated_head": None},
            "state": "REGISTERED", "last_observation": source_ref,
            "preservation_reasons": [], "operation_id": None}
        binding = {"admission_sha256": store.jcs_sha256(run["admission"]),
                   "dag_sha256": run.get("dag_content_sha256"), "origin_context_id": context_id}
        if not isinstance(binding["dag_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", binding["dag_sha256"]):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DAG-PIN-MISSING", args.run_id)
        def register(document: dict[str, Any]) -> dict[str, Any]:
            target_item = document["agent_orchestration"]["work_items"][args.work_id]
            resources = target_item["resources"]
            if resource_id in resources or document["revision"] != snapshot.revision:
                raise store.StoreError(store.STATE_DIVERGENCE, "worker session changed")
            bindings = target_item["contexts"][context_id]["scheduler_runs"]
            existing_binding = bindings.get(args.run_id)
            if existing_binding is not None and any(existing_binding.get(key) != binding[key]
                    for key in ("admission_sha256", "dag_sha256")):
                raise store.StoreError(store.STATE_DIVERGENCE, "scheduler run binding changed")
            if existing_binding is None:
                bindings[args.run_id] = binding
            resources[resource_id] = created
            return document
        store.transact(root, register)
        return {"verdict": "REGISTERED", "resource_id": resource_id, "dispatch": dispatch_id}, EXIT_OK

    if resource is None or resource.get("identity", {}).get("owner_dispatch") != dispatch_id or resource.get("wave_id") != wave_id:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", args.worker_id)
    if not runs._workspace_is_registered(root, target, worker["workspace"]):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", args.worker_id)
    result = _checkpoint_ref(target, args.result)
    if result is None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESULT-NOT-DURABLE", args.worker_id)
    if worker["state"] not in {"TERMINAL", "FAILED", "PREPARED"}:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORKER-NOT-TERMINAL", args.worker_id)
    if resource["state"] == "REGISTERED":
        try:
            show = runtime._object(boundary.read(["orchestration", "worker-show", "--dispatch", dispatch_id, "--json"]), "Orca worker-show")
            actual = show["worker"]
            expected = "succeeded" if worker["state"] == "TERMINAL" else "failed"
            if (show["dispatch"].get("id") != dispatch_id or actual.get("dispatchId") != dispatch_id
                    or actual.get("stage") != "settled" or actual.get("state") != expected
                    or show["dispatch"].get("status") != {"succeeded": "completed", "failed": "failed"}[expected]):
                raise ValueError("worker_done settlement not accepted")
        except (runtime.RuntimeError, KeyError, TypeError, ValueError) as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SETTLEMENT-UNPROVEN", str(exc)) from exc
        def pending(document: dict[str, Any]) -> dict[str, Any]:
            held = document["agent_orchestration"]["work_items"][args.work_id]["resources"].get(resource_id)
            if held != resource:
                raise store.StoreError(store.STATE_DIVERGENCE, "worker session changed")
            held["evidence_manifest"]["receipts"].append(result)
            held["state"] = "CLOSE_PENDING"
            return document
        store.transact(root, pending)
    elif resource["state"] != "CLOSE_PENDING":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SESSION-CLOSE-UNPROVEN", args.worker_id)
    elif result not in resource["evidence_manifest"]["receipts"]:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESULT-NOT-DURABLE", args.worker_id)
    try:
        released = boundary.observe_released()
    except runtime.RuntimeError:
        # Only the first call issues release. Recovery reads the same Dispatch;
        # an uncertain request never creates a second process action.
        if resource["state"] != "REGISTERED":
            return {"verdict": "UNKNOWN", "code": "SESSION-CLOSE-UNPROVEN", "resource_id": resource_id}, EXIT_BLOCKED
        try:
            response = subprocess.run([os.environ.get("ORCA_CLI_COMMAND") or "orca", "orchestration", "worker-release",
                "--dispatch", dispatch_id, "--json"], cwd=root, capture_output=True, timeout=20)
            if response.returncode:
                return {"verdict": "UNKNOWN", "code": "SESSION-CLOSE-UNPROVEN", "resource_id": resource_id}, EXIT_BLOCKED
            released = boundary.observe_released()
        except (OSError, subprocess.TimeoutExpired, runtime.RuntimeError):
            return {"verdict": "UNKNOWN", "code": "SESSION-CLOSE-UNPROVEN", "resource_id": resource_id}, EXIT_BLOCKED
    observed_identity = {key: released.get(key) for key in resource["identity"]}
    if observed_identity != resource["identity"] or released.get("release_proof") != "archive":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", args.worker_id)
    receipt = {"ref": source_ref + ":release", "sha256": released["source_sha256"]}
    def close(document: dict[str, Any]) -> dict[str, Any]:
        held = document["agent_orchestration"]["work_items"][args.work_id]["resources"].get(resource_id)
        if not isinstance(held, dict) or held["state"] != "CLOSE_PENDING" or held["identity"] != resource["identity"]:
            raise store.StoreError(store.STATE_DIVERGENCE, "worker session changed")
        held["evidence_manifest"]["receipts"].append(receipt)
        held.update({"last_observation": receipt["ref"], "result_acceptance_ref": result["ref"], "state": "CLOSED"})
        return document
    store.transact(root, close)
    return {"verdict": "RELEASED", "resource_id": resource_id, "dispatch": dispatch_id}, EXIT_OK


@_gauntlet_authorized
def gauntlet_remediate_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-003 (FR-007/FR-009/FR-010, ADR-0015): remediate one node's
    current worker.

    Both accepted ``--reason`` values -- ``stall`` (User Story 3) and
    ``transient-failure`` (User Story 4) -- flow through unchanged to
    ``remediate_node``, which enforces each reason's own eligibility
    precondition and shares the same per-node remediation budget across
    both (a node cannot chain remediation by alternating reasons).
    """
    root, gauntlet_runs, admission, record = gauntlet_run_admission(args)
    _require_scheduler_task_phase(root, gauntlet_runs, args, args.worker_id)
    try:
        return gauntlet_runs.remediate_node(
            root, args.work_id, args.run_id, args.worker_id, args.reason, admission,
            stall_minutes=record["limits"]["stall_minutes"],
            activation_max_workers=record["limits"]["max_workers"],
        ), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


def global_snapshotter(root: Path) -> Callable[[], dict[str, tuple[bytes, int]]]:
    """Content+mtime snapshot of the global projection, to prove it stayed put.

    Shared by every command that writes work-item state: the projection is
    derived, never edited in place, so any difference across a state write is a
    bug in that write.
    """
    global_dir = root / ".grill" / "global"

    def snapshot() -> dict[str, tuple[bytes, int]]:
        if not global_dir.exists():
            return {}
        return {str(p.relative_to(global_dir)): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in global_dir.rglob("*") if p.is_file() and not p.is_symlink()}

    return snapshot


def read_development_state(root: Path, item: Path, work_id: str) -> tuple[Path, dict[str, Any]]:
    """Read and shape-check ``state.json`` for a state-writing command."""
    path = item / "state.json"
    raw = safe_read(path, root=root, utf8=True)
    assert isinstance(raw, str)
    try:
        state = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-STATE", work_id) from exc
    if not isinstance(state, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-STATE", work_id)
    return path, state


def checkpoint_attestation_required(root: Path) -> bool:
    """Return whether the materialised workflow activates the receipt gate.

    V2 work items retain their byte-compatible lifecycle.  A document declaring
    the active frontier (by marker or as a human equivalent) is different: an
    incompatible document is a block, never a quiet downgrade to the
    unauthenticated v2 checkpoint path.

    This asks the *active* frontier, not a version literal.  While it asked v3
    specifically, a v4 document fell through the ``return False`` and shipped
    with the attestation gate silently disabled -- precisely the quiet downgrade
    the paragraph above forbids, reintroduced by the frontier moving underneath
    a hardcoded check.
    """
    workflow_v3 = grill_core_module("workflow_v3")
    workflow_v4 = grill_core_module("workflow_v4")
    workflow_path = root / "WORKFLOW.md"
    try:
        text = safe_read(workflow_path, root=root, utf8=True)
        # Dispatch by the version the document declares, and only here.  The
        # Gauntlet activation gate deliberately does not do this: refusing an
        # older document there removes a *capability*.  Refusing one here would
        # remove a *check*, dropping a v3 repository onto the unauthenticated v2
        # checkpoint path -- the quiet downgrade this function exists to prevent.
        # A markerless human equivalent is placed by which frontier it satisfies.
        marker = workflow_v4.marker_version(text)
        if marker == "v5" or (marker is None and "workflow-step-skills.v5.json" in text):
            gate_module = grill_core_module("workflow_v5")
        elif marker == "v4" or (marker is None and workflow_v4.compatible_v4(text)):
            gate_module = workflow_v4
        elif marker == "v3" or (marker is None and workflow_v3.compatible_v3(text)):
            gate_module = workflow_v3
        else:
            # v2, or a document declaring nothing this runtime knows: byte
            # compatible lifecycle, exactly as before.
            return False
        gate = gate_module.execution_gate(text)
    # Both classes are named Failure and both descend from the v3 definition,
    # but they are not the same object here: workflow_v4 re-exports the Failure
    # of its *own* internally loaded v3, while grill_core_module hands back a
    # separately executed workflow_v3.  Catching only one lets the other escape
    # this boundary as UNEXPECTED-FAILURE.
    except (workflow_v3.Failure, workflow_v4.Failure) as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", translate_v3_code(exc.code), exc.message) from exc
    if gate.status != "OK":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", translate_v3_code(gate.code or "WORKFLOW_INCOMPATIBLE"), "WORKFLOW.md")
    return True


def load_checkpoint_attestation(root: Path, value: str) -> dict[str, Any]:
    """Read one caller-named receipt bundle without following symlinks."""
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ATTESTATION-PATH", value)
    full_path = root / path
    try:
        raw = safe_read_regular_fd(root, full_path)
        document = json.loads(raw.decode("utf-8"))
    except UnicodeError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ATTESTATION", value) from exc
    except json.JSONDecodeError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ATTESTATION", value) from exc
    except CliFailure as exc:
        if exc.code in {"SYMLINK-REJECTED", "UNSAFE-FILE", "EVIDENCE-NOT-REGULAR"}:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ATTESTATION-SYMLINK", value) from exc
        raise
    if not isinstance(document, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ATTESTATION", value)
    return document


def require_converged_runs(root: Path, work_id: str) -> None:
    """FASE-004 (FR-007/FR-008): ``ship`` never closes over a run still
    holding unconverged work.

    The predicate is the run's ``state`` alone (ADR-0020): ``COMPLETE`` is
    only ever reached once every ``node_id`` of the pinned Execution DAG has
    a converged lineage head, and ``BLOCKED`` only through an explicitly
    authorized abandonment. A worker/wave scan of this module's own would be
    vacuously satisfied by a run whose DAG is only half dispatched -- it has
    no pending worker to find, and is nowhere near ready.

    Read-only, and outside FR-012's admission boundary on purpose: this
    inspects Store state for the work item, it mutates nothing that boundary
    protects, and it must stay a no-op for a V2 or never-admitted item.
    """
    gauntlet_runs = grill_core_module("gauntlet_runs")
    try:
        states = gauntlet_runs.list_run_states(root, work_id)
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": work_id}) from error
    pending = sorted(entry["run_id"] for entry in states if entry["state"] not in {"COMPLETE", "BLOCKED"})
    if pending:
        raise CliFailure(
            EXIT_BLOCKED, "BLOCKED", "CONVERGENCE-INCOMPLETE",
            f"gauntlet runs are not converged: {', '.join(pending)}",
            extra={"work_id": work_id, "pending_runs": pending},
        )


def _v5_input_fingerprint(root: Path, work_id: str, step_id: str, head: str, artifact_sha256: str) -> str:
    policy = json.loads(_policy_path(root, work_id).read_bytes())
    assessment = _step_assessment(root, work_id, step_id, policy)
    contract = grill_core_module("agent_orchestration")
    digest = contract.validate_step_assessment(assessment, policy, step_id)
    return "sha256:" + grill_core_module("store").jcs_sha256({
        "work_id": work_id, "step": step_id, "head": head,
        "artifact_sha256": artifact_sha256, "assessment_sha256": digest,
    })


def verify_checkpoint_attestation(
    root: Path,
    development: dict[str, Any],
    *,
    work_id: str,
    step_id: str,
    attestation_path: str | None,
) -> dict[str, Any]:
    """Verify and bind the full canonical chain before a v3 completion."""
    if not attestation_path:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ATTESTATION-REQUIRED", step_id)
    attestation = grill_core_module("attestation")
    store = grill_core_module("store")
    bundle = load_checkpoint_attestation(root, attestation_path)
    try:
        project_id = store.project_identity(root)["project_id"]
        previous = None
        # The item's own sequence, never the build's: a bundle written under v3
        # names its predecessor `agent-execute`, and looking that up in the v4
        # tuple would report a missing predecessor that was never missing.
        item_sequence = development_sequence(development) or list(SEQUENCE)
        if step_id not in item_sequence:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ATTESTATION-STATE-DIVERGENCE", step_id)
        index = item_sequence.index(step_id)
        outputs = development.get("attested_outputs", {})
        if not isinstance(outputs, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ATTESTATION-STATE-DIVERGENCE", work_id)
        if index:
            previous = outputs.get(item_sequence[index - 1])
            if not isinstance(previous, dict):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ATTESTATION-PREDECESSOR-MISSING", item_sequence[index - 1])
        recorded_campaign = development.get("attestation_campaign")
        bridge = None
        snapshot = store.read_snapshot(root, required=False)
        item = (snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(work_id)
                if snapshot is not None else None)
        if isinstance(item, dict):
            context = item.get("contexts", {}).get(item.get("current_context_id"))
            if isinstance(context, dict) and context.get("campaign") is not None:
                recorded_campaign = context["campaign"]
                operation = item.get("operations", {}).get(context.get("continuity_ref"))
                if isinstance(operation, dict):
                    bridge = operation.get("intended_after", {}).get("campaign_bridge")
        verdict = attestation.judge_checkpoint_attestation(
            bundle,
            project_id=project_id,
            work_item_id=work_id,
            step_id=step_id,
            campaign=recorded_campaign,
            predecessor_output=previous,
            campaign_bridge=bridge,
        )
    except CliFailure:
        raise
    except attestation.AttestationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", translate_v3_code(exc.code), exc.reason) from exc
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", translate_v3_code(exc.code), exc.message) from exc
    if development.get("workflow_version") == "v5":
        expected = _v5_input_fingerprint(root, work_id, step_id,
            bundle["dispatch_intent"]["worktree_head"], bundle["step_output"]["output_sha256"])
        if bundle["step_output"]["input_fingerprint"] != expected:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STEP-ASSESSMENT-STALE", step_id)
    # The execution id travels with the verdict because the state has to record
    # it: the pair (artefact digest, receipt ref) does not pin *which execution*
    # produced the accepted receipt, and a later supersession needs exactly that.
    return {"path": attestation_path,
            "step_execution_id": bundle["step_output"]["step_execution_id"],
            **verdict}


def mark_chain_stale(development: dict[str, Any], step_id: str) -> list[str]:
    """Record which already-attested steps now rest on a replaced output.

    Superseding a step does not make the receipts after it wrong -- it makes
    them unverifiable. Each of them sealed the output of its predecessor, and
    that output is no longer the current one, so nothing in the chain can say
    whether the later work still holds under the corrected artefact.

    Naming them is the whole point. Left unnamed, a supersession would quietly
    relocate the divergence one step downstream instead of resolving it, which
    is the failure BL-0201 describes. Named, each one is cleared the only
    honest way: by being attested again against the predecessor that now
    stands.
    """
    sequence = development_sequence(development) or list(SEQUENCE)
    outputs = development.get("attested_outputs") or {}
    stale = set(development.get("chain_stale") or [])
    stale.discard(step_id)
    if step_id in sequence:
        for later in sequence[sequence.index(step_id) + 1:]:
            if later in outputs:
                stale.add(later)
    ordered = [step for step in sequence if step in stale]
    development["chain_stale"] = ordered
    return ordered


def verify_supersession(
    root: Path,
    development: dict[str, Any],
    *,
    work_id: str,
    step_id: str,
    current: str,
    state: str,
    reason: str,
    evidence: list[dict[str, Any]],
    attestation_path: str | None,
    superseded_path: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Accept a successor chain for a step whose artefact legitimately changed.

    This is the only path that writes a step's attested output twice, so it is
    the one place where "the receipt no longer matches the file" can be told
    from "the file was tampered with". It refuses everything that would blur
    that: a step that is not closed, a supersession with no stated reason, and
    above all a prior bundle that is merely well-formed rather than the one
    this work item actually accepted.

    The step's state never moves. Nothing is being redone -- ``complete`` was
    and remains true. What changes is which receipt is current for it, and what
    that receipt says it replaces.
    """
    if state != "complete" or current != "complete":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SUPERSEDE-STEP-NOT-COMPLETE", step_id)
    if not reason:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "REASON-REQUIRED", step_id)
    if not evidence:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "EVIDENCE-REQUIRED", step_id)
    attestation = grill_core_module("attestation")
    recorded = (development.get("attested_outputs") or {}).get(step_id)
    if not isinstance(recorded, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SUPERSEDE-NOTHING-ATTESTED", step_id)
    prior = load_checkpoint_attestation(root, superseded_path)
    prior_output = prior.get("step_output") if isinstance(prior, dict) else None
    if not isinstance(prior_output, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SUPERSEDE-BUNDLE-INVALID", superseded_path)
    # Being a valid bundle for this step is not enough: it has to be the bundle
    # this work item accepted. What proves that is what the state recorded at
    # acceptance -- the digest and receipt ref here, and the execution id
    # checked right below. Neither half is sufficient alone: the digest pair
    # does not pin which execution produced the receipt, and the execution id
    # is absent for receipts accepted before the field existed.
    if (prior_output.get("step_id") != step_id
            or prior_output.get("output_sha256") != recorded.get("output_sha256")
            or prior_output.get("skill_invocation_receipt_ref") != recorded.get("receipt_ref")):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SUPERSEDE-BUNDLE-NOT-RECORDED", step_id)
    # The pair above does not pin the execution: two chains for the same step and
    # the same artefact, differing only in wave index, carry an identical digest
    # and receipt ref under different execution ids. Without this check the
    # history would name an execution that was never the current receipt, and the
    # successor would link to it -- corrupting the one trail this mechanism
    # exists to make trustworthy.
    #
    # Absent for a receipt accepted before the field existed; falling back to the
    # pair there is a declared degradation, not a hole left open: every
    # acceptance from now on records the execution.
    recorded_execution = (development.get("attested_executions") or {}).get(step_id)
    if recorded_execution is not None and prior_output.get("step_execution_id") != recorded_execution:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SUPERSEDE-BUNDLE-NOT-RECORDED", step_id,
                         extra={"expected_step_execution_id": recorded_execution,
                                "actual_step_execution_id": prior_output.get("step_execution_id")})
    verdict = verify_checkpoint_attestation(
        root, development, work_id=work_id, step_id=step_id, attestation_path=attestation_path,
    )
    successor = load_checkpoint_attestation(root, attestation_path)
    successor_output = successor.get("step_output") if isinstance(successor, dict) else None
    try:
        attestation.supersede_step_execution({}, prior_output, successor_output)
    except attestation.AttestationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", translate_v3_code(exc.code), exc.reason) from exc
    history = {
        **recorded,
        "step_execution_id": prior_output.get("step_execution_id"),
        "attempt_id": prior_output.get("attempt_id"),
        "execution_round": prior_output.get("execution_round"),
        "attestation": superseded_path,
        "reason": reason,
        "superseded_by_step_execution_id": successor_output.get("step_execution_id"),
    }
    return verdict, history


def _converged_waves_exist(root: Path, work_id: str) -> bool:
    """Whether any run of this work item has a converged wave.

    Read from the durable run state, never from a caller-supplied flag: the
    whole point of ``worker-required`` is that the leader cannot simply declare
    that workers ran.

    Absent run state is not an error here -- a work item that never activated
    the Gauntlet has no converged wave, which is exactly the answer ``False``
    conveys.
    """
    try:
        gauntlet_runs = grill_core_module("gauntlet_runs")
        runs = gauntlet_runs._read_runs(root, work_id, absent_ok=True)
    except Exception:
        return False
    for run in (runs or {}).values():
        if not isinstance(run, dict):
            continue
        for wave in (run.get("waves") or {}).values():
            if isinstance(wave, dict) and wave.get("converged") is True:
                return True
    return False


def _activity_policy(root: Path, work_id: str, context_id: str, epoch: int,
                     session_ref: str) -> tuple[Any, Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Read one current adopted context and its exact versioned policy bytes."""
    store = grill_core_module("store")
    contract = grill_core_module("agent_orchestration")
    snapshot = store.read_snapshot(root, required=False)
    block = snapshot.document.get("agent_orchestration") if snapshot is not None else None
    item = block.get("work_items", {}).get(work_id) if isinstance(block, dict) else None
    if not isinstance(item, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-MIGRATION-REQUIRED", work_id)
    try:
        store.require_orchestration_authority(root, work_id, purpose="activity")
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", exc.message) from exc
    context = item.get("contexts", {}).get(context_id)
    try:
        contract.require_authority(item, context_id, epoch, session_ref)
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
    if not isinstance(context, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTEXT-FENCED", context_id)
    try:
        contract.require_presentation_work_ready(context)
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", str(exc), "presentation is not ready") from exc
    _policy_path(root, work_id, item)
    return store, contract, snapshot.document, item, context


def _activity_json(root: Path, value: str, code: str) -> tuple[dict[str, Any], dict[str, str]]:
    reference = _checkpoint_ref(root, value)
    assert reference is not None
    try:
        raw = safe_read_regular_fd(root, root / reference["ref"])
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, value) from exc
    if not isinstance(document, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, value)
    return document, reference


def _visual_manifest(root: Path, value: str) -> tuple[dict[str, Any], dict[str, str]]:
    try:
        return _activity_json(root, value, "PREVIEW-MISSING")
    except CliFailure as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-MISSING", value) from exc


def _visual_preview(root: Path, contract: Any, item: dict[str, Any], context: dict[str, Any],
                    manifest: dict[str, Any], reference: dict[str, str]) -> dict[str, Any]:
    def read_file(path: str) -> bytes:
        target = root / path
        reject_symlink_chain(root, target, allow_missing=False)
        return safe_read_regular_fd(root, target)
    try:
        return contract.inspect_visual_preview(
            manifest, preview_sha256=reference["sha256"], context_id=context["context_id"],
            activities=item["activities"], read_file=read_file,
        )
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", str(exc), "visual preview is not current") from exc


def _visual_registration(item: dict[str, Any]) -> dict[str, Any] | None:
    records = []
    for operation_id, operation in item.get("operations", {}).items():
        if not isinstance(operation, dict) or operation.get("kind") != "visual-preview" or operation.get("state") != "CONFIRMED":
            continue
        state = operation.get("intended_after", {}).get("visual_state")
        if isinstance(state, dict) and isinstance(state.get("recorded_at"), str):
            records.append((state["recorded_at"], operation_id, state))
    return dict(max(records)[2]) if records else None


def _visual_decision(item: dict[str, Any], preview_sha256: str, context_id: str) -> dict[str, Any] | None:
    decisions = [(decision_id, decision) for decision_id, decision in item.get("visual_decisions", {}).items()
                 if isinstance(decision, dict) and decision.get("preview_sha256") == preview_sha256
                 and decision.get("context_id") == context_id]
    if not decisions:
        return None
    return dict(max((decision["recorded_at"], decision_id, decision)
                    for decision_id, decision in decisions)[2])


def _current_human_preview_decision(root: Path, decision: dict[str, Any], preview_sha256: str) -> None:
    source = decision.get("source_ref")
    if not isinstance(source, str) or "#sha256:" not in source:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "human decision reference is incomplete")
    path, expected = source.rsplit("#sha256:", 1)
    try:
        document, reference = _activity_json(root, path, "PREVIEW-STALE")
    except CliFailure as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "human decision evidence changed") from exc
    if reference.get("sha256") != expected:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "human decision evidence changed")
    _human_preview_decision(document, preview_sha256=preview_sha256, requested=decision.get("decision"))


def _current_visual_state(root: Path, contract: Any, item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    registration = _visual_registration(item)
    if registration is None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-MISSING", "no registered visual classification")
    reference = registration.get("manifest")
    if not isinstance(reference, dict) or not isinstance(reference.get("ref"), str) or not isinstance(reference.get("sha256"), str):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "visual registration is incomplete")
    manifest, current = _visual_manifest(root, reference["ref"])
    if current != reference:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "visual manifest changed after registration")
    context = item.get("contexts", {}).get(item.get("current_context_id"))
    if not isinstance(context, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTEXT-FENCED", "visual context is unavailable")
    preview = _visual_preview(root, contract, item, context, manifest, current)
    if preview.get("preview_sha256") != registration.get("preview_sha256"):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "visual preview digest changed")
    decision = _visual_decision(item, current["sha256"], context["context_id"])
    if decision is not None:
        _current_human_preview_decision(root, decision, current["sha256"])
    state = contract.visual_gate_state(item, preview, decision=decision)
    return state, preview


def _require_visual_gate(root: Path, work_id: str) -> str | None:
    """Use the same current-preview projection at every tasks boundary."""
    store = grill_core_module("store")
    contract = grill_core_module("agent_orchestration")
    snapshot = store.read_snapshot(root, required=False)
    block = snapshot.document.get("agent_orchestration") if snapshot is not None else None
    item = block.get("work_items", {}).get(work_id) if isinstance(block, dict) else None
    if not isinstance(item, dict):
        return None
    context = item.get("contexts", {}).get(item.get("current_context_id"))
    if not isinstance(context, dict) or not item.get("scope_files"):
        return None
    state, _preview = _current_visual_state(root, contract, item)
    attestation = grill_core_module("attestation")
    try:
        attestation.require_visual_gate(state)
    except attestation.AttestationError as exc:
        code = "PREVIEW-STALE" if exc.reason == "PREVIEW_STALE" else "PREVIEW-APPROVAL-REQUIRED"
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, f"visual state is {state}") from exc
    return state


def _human_preview_decision(document: dict[str, Any], *, preview_sha256: str,
                            requested: str) -> dict[str, Any]:
    required = {"schema", "evidence_kind", "preview_sha256", "decision", "actor_ref", "source_ref", "source_sha256", "recorded_at"}
    if set(document) != required or document.get("schema") != "grill-human-preview-decision/v1" or document.get("evidence_kind") != "human_interaction":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-APPROVAL-REQUIRED", "human preview evidence is invalid")
    if document.get("preview_sha256") != preview_sha256 or document.get("decision") != requested:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-APPROVAL-REQUIRED", "human decision is not bound to this preview")
    for key in ("actor_ref", "source_ref", "recorded_at"):
        if not isinstance(document.get(key), str) or not document[key]:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-APPROVAL-REQUIRED", "human decision source is incomplete")
    if not isinstance(document.get("source_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", document["source_sha256"]):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-APPROVAL-REQUIRED", "human decision source digest is invalid")
    return document


def _activity_descriptors(policy: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Keep the canonical eleven-entry registry untouched; add only supplements."""
    references = policy.get("references")
    if not isinstance(references, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", "references")
    protocol_name = "agent-orchestration.v2.md" if policy.get("policy_version") == "2" else "agent-orchestration.md"
    targets = {
        "protocol": (Path(__file__).resolve().parent.parent / "references" / protocol_name,
                     "plugin/skills/grill-with-docs/references/" + protocol_name),
        "task_files_template": (ASSETS / "task-files.v1.template.md",
                                "plugin/skills/grill-with-docs/assets/task-files.v1.template.md"),
    }
    descriptors: list[dict[str, Any]] = []
    for key, (path, expected_path) in targets.items():
        declared = references.get(key)
        if not isinstance(declared, dict) or declared.get("path") != expected_path:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", key)
        try:
            digest = hash_bytes(path.read_bytes())
        except OSError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", key) from exc
        if declared.get("sha256") != "sha256:" + digest:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-POLICY-STALE", key)
        descriptors.append({"path": expected_path, "sha256": digest})
    return descriptors[0], descriptors[1]


def _step_activity_coverage(root: Path, work_id: str, step_id: str) -> dict[str, Any] | None:
    """Apply the policy at every bypass-prone macrostep boundary."""
    store = grill_core_module("store")
    contract = grill_core_module("agent_orchestration")
    snapshot = store.read_snapshot(root, required=False)
    block = snapshot.document.get("agent_orchestration") if snapshot is not None else None
    item = block.get("work_items", {}).get(work_id) if isinstance(block, dict) else None
    if not isinstance(item, dict):
        return None
    context_id = item.get("current_context_id")
    context = item.get("contexts", {}).get(context_id)
    if not isinstance(context, dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTEXT-FENCED", work_id)
    policy_path = _policy_path(root, work_id, item)
    policy = json.loads(policy_path.read_bytes())
    if not item.get("scope_files") and policy.get("policy_version") != "2":
        return None
    assessment = _step_assessment(root, work_id, step_id, policy)
    try:
        return contract.require_activity_coverage(
            item, policy, context_id=context_id, step_id=step_id,
            new_how=step_id == "specify" if assessment is None else assessment["new_how"],
            frontend=step_id == "plan" if assessment is None else "frontend" in assessment["risks"],
            assessment=assessment,
        )
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-REQUIRED", str(exc)) from exc


@_gauntlet_authorized
def gauntlet_step_enter_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Deliver the resolved entrypoint plus hashed supplements, never invoke it."""
    root = project_root(args.root)
    if args.step not in SEQUENCE:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-STEP", args.step)
    if args.step == "tasks":
        _require_visual_gate(root, args.work_id)
    _store, contract, _document, _item, context = _activity_policy(
        root, args.work_id, args.context_id, args.epoch, args.session_ref)
    policy_path = _policy_path(root, args.work_id, _item)
    policy = json.loads(policy_path.read_bytes())
    assessment = _step_assessment(root, args.work_id, args.step, policy)
    supplement, task_template = _activity_descriptors(policy)
    versions = grill_core_module("workflow_versions")
    step_skills = grill_core_module("step_skills")
    workflow_version = "v5" if policy.get("policy_version") == "2" else "v4"
    try:
        registry = (ASSETS / versions.REGISTRY_FILENAME_BY_VERSION[workflow_version]).read_bytes()
        catalog = (ASSETS / versions.CATALOG_FILENAME_BY_VERSION_RUNTIME[workflow_version][context["runtime"]]).read_bytes()
        parsed_catalog = step_skills.parse_strict(catalog)
        resolutions, _trusted = step_skills.resolve_shipped_workflow_skills(
            (args.step,), context["runtime"], step_skills.registry_sha256(registry), registry=registry,
            catalog=parsed_catalog, trusted_catalogs_path=ASSETS / versions.TRUSTED_CATALOGS_FILENAME_BY_VERSION[workflow_version],
        )
    except Exception as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SKILL-RESOLUTION-FAILED", args.step) from exc
    try:
        invocation = contract.invocation_context(
            policy=policy, policy_sha256=hash_bytes(policy_path.read_bytes()), context=context,
            step_id=args.step, canonical_entrypoint=resolutions[0], supplement=supplement,
            task_template=task_template, new_how=bool(args.new_how), frontend=bool(args.frontend), assessment=assessment,
        )
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-REQUIRED", str(exc)) from exc
    return {"verdict": "STEP-ENTERED", "work_id": args.work_id, "invocation_context": invocation,
            "limitation": "context delivery does not prove canonical skill invocation"}, EXIT_OK


@_gauntlet_authorized
def gauntlet_preview_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Register a byte-checked visual preview or a corroborated non-frontend classification."""
    root = project_root(args.root)
    store, contract, _document, item, context = _activity_policy(
        root, args.work_id, args.context_id, args.epoch, args.session_ref)
    manifest, reference = _visual_manifest(root, args.manifest)
    preview = _visual_preview(root, contract, item, context, manifest, reference)
    if preview["state"] == "REVIEWED" and (args.author_activity != preview["author_activity_id"]
                                            or args.review_activity != preview["review_activity_id"]):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-APPROVAL-REQUIRED", "preview activity arguments diverge")
    if preview["state"] == "NOT_APPLICABLE" and (args.author_activity is not None or args.review_activity is not None):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "FRONTEND-CLASSIFICATION-DIVERGENT", "non-frontend preview has specialist activities")
    operation_id = "visual-" + store.jcs_sha256({"manifest": reference})[:24]
    existing = item["operations"].get(operation_id)
    if existing is not None:
        state = existing.get("intended_after", {}).get("visual_state") if isinstance(existing, dict) else None
        if (not isinstance(state, dict) or existing.get("kind") != "visual-preview"
                or state.get("manifest") != reference or state.get("preview_sha256") != reference["sha256"]):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "registered preview differs")
        return {"verdict": "REUSED", "work_id": args.work_id, "visual_state": preview["state"],
                "preview_sha256": reference["sha256"], "store_revision": store.read_snapshot(root).revision}, EXIT_OK
    recorded = {**preview, "manifest": reference,
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    operation = {
        "kind": "visual-preview", "context_id": context["context_id"], "fence": context["leader"]["fence"],
        "subject_ids": [reference["ref"]], "input_sha256": reference["sha256"],
        "expected_before": {"visual_decisions": sorted(item["visual_decisions"])},
        "intended_after": {"visual_state": recorded}, "idempotency_key": operation_id,
        "state": "CONFIRMED", "result_ref": reference["ref"], "result_sha256": reference["sha256"],
        "observation_ref": reference["ref"], "error": None,
    }
    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        target = document["agent_orchestration"]["work_items"][args.work_id]
        try:
            contract.require_authority(target, args.context_id, args.epoch, args.session_ref)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
        if operation_id in target["operations"]:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "preview appeared during commit")
        target["operations"][operation_id] = operation
        return document
    try:
        committed = store.transact(root, mutate)
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.message) from exc
    return {"verdict": preview["state"], "work_id": args.work_id, "preview_sha256": reference["sha256"],
            "store_revision": committed.revision}, EXIT_OK


@_gauntlet_authorized
def gauntlet_preview_decide_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Persist an observed human decision; --decision alone never approves a preview."""
    root = project_root(args.root)
    store, contract, _document, item, context = _activity_policy(
        root, args.work_id, args.context_id, args.epoch, args.session_ref)
    manifest, reference = _visual_manifest(root, args.manifest)
    state, preview = _current_visual_state(root, contract, item)
    if preview.get("preview_sha256") != reference["sha256"] or state not in {"PENDING_APPROVAL", "REJECTED"}:
        code = "PREVIEW-STALE" if state == "STALE" else "PREVIEW-APPROVAL-REQUIRED"
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, f"visual state is {state}")
    human, human_ref = _activity_json(root, args.human_evidence, "PREVIEW-APPROVAL-REQUIRED")
    human = _human_preview_decision(human, preview_sha256=reference["sha256"], requested=args.decision)
    expected = store.jcs_sha256({"preview": reference, "decision": args.decision,
                                 "human_evidence": human_ref, "visual_decisions": item["visual_decisions"]})
    if not args.apply:
        return {"verdict": "PREVIEW", "work_id": args.work_id, "visual_state": state,
                "preview_sha256": reference["sha256"], "expected_sha256": expected}, EXIT_OK
    if args.expected_sha256 != expected:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "preview decision inputs changed")
    decision_id = "visual-decision-" + store.jcs_sha256({"preview": reference["sha256"], "human": human_ref})[:24]
    decision = {"decision_id": decision_id, "preview_sha256": reference["sha256"],
                "review_ref": preview["review_ref"], "actor_ref": human["actor_ref"],
                "decision": args.decision, "source_ref": human_ref["ref"] + "#sha256:" + human_ref["sha256"],
                "recorded_at": human["recorded_at"], "context_id": context["context_id"]}
    def mutate(document: dict[str, Any]) -> dict[str, Any]:
        target = document["agent_orchestration"]["work_items"][args.work_id]
        try:
            contract.require_authority(target, args.context_id, args.epoch, args.session_ref)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
        fresh = store.jcs_sha256({"preview": reference, "decision": args.decision,
                                  "human_evidence": human_ref, "visual_decisions": target["visual_decisions"]})
        if fresh != args.expected_sha256:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "preview decision changed before commit")
        previous = target["visual_decisions"].get(decision_id)
        if previous is not None and previous != decision:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREVIEW-STALE", "decision id collides")
        target["visual_decisions"][decision_id] = decision
        return document
    try:
        committed = store.transact(root, mutate)
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", exc.code, exc.message) from exc
    return {"verdict": "APPROVED" if args.decision == "approved" else "REJECTED", "work_id": args.work_id,
            "preview_sha256": reference["sha256"], "store_revision": committed.revision}, EXIT_OK


@_gauntlet_authorized
def gauntlet_activity_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Persist prepare -> verified -> dispatch -> result -> accept for one specialist."""
    root = project_root(args.root)
    scope = "interview" if args.scope == "interview" else "cycle"
    step_id = None if scope == "interview" else args.step
    if (scope == "interview") == (step_id is not None):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ACTIVITY-SCOPE", args.activity_id)
    store, contract, _document, _item, context = _activity_policy(
        root, args.work_id, args.context_id, args.epoch, args.session_ref)
    manifest, _manifest_ref = _activity_json(root, args.input_manifest, "INPUT-MANIFEST-INVALID")
    if scope == "cycle":
        policy = json.loads(_policy_path(root, args.work_id, _item).read_bytes())
        assessment = _step_assessment(root, args.work_id, step_id, policy)
        if assessment is not None:
            # Omitted: filled before the input hash, in every phase alike. Stated: must match.
            digest = manifest.setdefault("assessment_sha256", contract.validate_step_assessment(assessment, policy, step_id))
            if digest != contract.validate_step_assessment(assessment, policy, step_id):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STEP-ASSESSMENT-DIVERGENT", args.activity_id)
    try:
        current_input_sha256 = contract.activity_input_sha256(manifest)
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INPUT-MANIFEST-INVALID", str(exc)) from exc
    if args.author_activity and manifest.get("author_activity_ids") != args.author_activity:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-INPUT-DIVERGENT", args.activity_id)

    def current(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        item = document["agent_orchestration"]["work_items"][args.work_id]
        try:
            bound = contract.require_authority(item, args.context_id, args.epoch, args.session_ref)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEADER-AUTHORITY-UNPROVEN", str(exc)) from exc
        if scope == "cycle" and policy.get("policy_version") == "2":
            fresh = _step_assessment(root, args.work_id, step_id, policy)
            if contract.validate_step_assessment(fresh, policy, step_id) != manifest.get("assessment_sha256"):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STEP-ASSESSMENT-DIVERGENT", args.activity_id)
            if args.kind == "reviewer" and step_id == "review":
                try:
                    contract.require_final_review_authors(item, manifest["author_activity_ids"])
                except contract.OrchestrationError as exc:
                    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "REVIEWER-NOT-INDEPENDENT", args.activity_id) from exc
        return item, bound

    snapshot = store.read_snapshot(root)
    item, bound = current(snapshot.document)
    existing = item["activities"].get(args.activity_id)
    if existing is not None and (existing.get("activity_type") != args.kind
                                 or existing.get("activity_scope") != scope
                                 or existing.get("step_id") != step_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-STATE-DIVERGENCE", args.activity_id)
    if args.phase == "prepare":
        try:
            if existing is None:
                activity = contract.new_activity(
                    activity_id=args.activity_id, context_id=args.context_id, step_id=step_id,
                    activity_scope=scope, activity_type=args.kind, attempt=1, input_manifest=manifest,
                    policy_sha256=item["policy_sha256"], write_files=args.files or [],
                )
                activity = contract.prepare_activity(activity, bound)
            else:
                activity = contract.prepare_activity(existing, bound)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SPECIALIST-CAPABILITY-UNPROVEN", str(exc)) from exc
        def prepare(document: dict[str, Any]) -> dict[str, Any]:
            target, target_context = current(document)
            prior = target["activities"].get(args.activity_id)
            if prior is not None and prior != existing:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-STATE-DIVERGENCE", args.activity_id)
            target["activities"][args.activity_id] = contract.prepare_activity(activity, target_context)
            return document
        committed = store.transact(root, prepare)
        activity = committed.document["agent_orchestration"]["work_items"][args.work_id]["activities"][args.activity_id]
        if activity["activity_type"] == "deterministic_check":
            return {"verdict": "PREPARED", "activity_id": args.activity_id,
                    "store_revision": committed.revision}, EXIT_OK
        return {"verdict": "BOOTSTRAP-REQUIRED", "activity_id": args.activity_id,
                "bootstrap": contract.bootstrap_request(activity), "store_revision": committed.revision}, EXIT_OK

    input_divergent = existing is not None and existing.get("input_sha256") != current_input_sha256
    if existing is None or (input_divergent and not (args.phase == "accept"
                                                      and args.kind == "reviewer"
                                                      and existing.get("state") in {"DISPATCHED", "RESULT_RECORDED"})):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-INPUT-DIVERGENT", args.activity_id)
    if args.phase == "dispatch":
        if args.kind != "deterministic_check" and not args.observation:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SPECIALIST-CAPABILITY-UNPROVEN", "observation is required")
        observation = None
        if args.kind != "deterministic_check":
            observation, _observation_ref = _activity_json(root, args.observation, "SPECIALIST-CAPABILITY-UNPROVEN")
        try:
            verified = contract.record_verified_activity(existing, observation) if existing["state"] == "BOOTSTRAPPING" else existing
            if existing["state"] == "BOOTSTRAPPING":
                resource_id = resource = None
                if args.kind != "deterministic_check":
                    assert observation is not None
                    contract.require_reviewer_independence(
                        verified, observation, activities=item["activities"], resources=item["resources"])
                    resource_id, resource = contract.session_resource(
                        verified, observation, collected_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
                    if verified["session_resource_id"] != resource_id:
                        raise contract.OrchestrationError("SPECIALIST-CAPABILITY-UNPROVEN")
                def verify(document: dict[str, Any]) -> dict[str, Any]:
                    target, _target_context = current(document)
                    if target["activities"].get(args.activity_id) != existing:
                        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-STATE-DIVERGENCE", args.activity_id)
                    if resource_id is not None and resource_id in target["resources"]:
                        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RESOURCE-IDENTITY-DIVERGENT", resource_id)
                    target["activities"][args.activity_id] = verified
                    if resource_id is not None:
                        target["resources"][resource_id] = resource
                    return document
                store.transact(root, verify)
            snapshot = store.read_snapshot(root); item, bound = current(snapshot.document)
            verified = item["activities"][args.activity_id]
            if verified["state"] == "DISPATCHED":
                if args.kind != "deterministic_check":
                    assert observation is not None
                    readback = contract.verify_specialist(verified, observation)
                    resource = item["resources"].get(verified["session_resource_id"])
                    if not isinstance(resource, dict) or readback["owner_dispatch"] != resource.get("identity", {}).get("owner_dispatch"):
                        raise contract.OrchestrationError("SPECIALIST-CAPABILITY-UNPROVEN")
                payload = contract.activity_payload(verified, bound)
                return {"verdict": "REUSED", "activity_id": args.activity_id, "payload": payload}, EXIT_OK
            dispatched, payload = contract.dispatch_activity(verified, bound)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SPECIALIST-CAPABILITY-UNPROVEN", str(exc)) from exc
        def dispatch(document: dict[str, Any]) -> dict[str, Any]:
            target, target_context = current(document)
            prior = target["activities"].get(args.activity_id)
            if prior is None or prior.get("state") != "VERIFIED":
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-STATE-DIVERGENCE", args.activity_id)
            target["activities"][args.activity_id], _payload = contract.dispatch_activity(prior, target_context)
            return document
        committed = store.transact(root, dispatch)
        return {"verdict": "DISPATCHED", "activity_id": args.activity_id, "payload": payload,
                "store_revision": committed.revision}, EXIT_OK

    if args.phase != "accept":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ACTIVITY-PHASE", args.phase)
    if (existing.get("state") == "FAILED" and args.diagnostic and args.observation
            and existing.get("diagnostic_ref") == args.diagnostic):
        resource_id = existing.get("session_resource_id")
        resource = item["resources"].get(resource_id)
        if (isinstance(resource, dict) and resource.get("state") == "CLOSED"
                and resource.get("result_acceptance_ref") == args.diagnostic):
            return {"verdict": "FAILED-RELEASED-REUSED", "activity_id": args.activity_id}, EXIT_BLOCKED
        if not isinstance(resource, dict) or resource.get("state") != "CLOSE_PENDING":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SESSION-CLOSE-UNPROVEN", args.activity_id)
        observation, _ = _activity_json(root, args.observation, "SPECIALIST-CAPABILITY-UNPROVEN")
        try:
            contract.verify_specialist(existing, observation, require_open=False)
            closed = contract.close_session_resource(resource, observation, acceptance_ref=args.diagnostic)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SESSION-CLOSE-UNPROVEN", str(exc)) from exc
        def close_failure(document: dict[str, Any]) -> dict[str, Any]:
            target = document["agent_orchestration"]["work_items"][args.work_id]
            if target["activities"].get(args.activity_id) != existing or target["resources"].get(resource_id) != resource:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-STATE-DIVERGENCE", args.activity_id)
            target["resources"][resource_id] = closed
            return document
        committed = store.transact(root, close_failure)
        return {"verdict": "FAILED-RELEASED", "activity_id": args.activity_id,
                "store_revision": committed.revision}, EXIT_BLOCKED
    if existing.get("state") not in {"DISPATCHED", "RESULT_RECORDED"}:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-STATE-DIVERGENCE", args.activity_id)
    if not args.result and not args.diagnostic:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-RESULT-REQUIRED", args.activity_id)
    if args.diagnostic and not args.result:
        if existing.get("state") != "DISPATCHED":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-STATE-DIVERGENCE", args.activity_id)
        diagnostic = _checkpoint_ref(root, args.diagnostic)
        assert diagnostic is not None
        failed = copy.deepcopy(existing); failed.update({"diagnostic_ref": diagnostic["ref"], "state": "FAILED"})
        def record_failure(document: dict[str, Any]) -> dict[str, Any]:
            updated = _replace_activity(document, args.work_id, args.activity_id, existing, failed)
            if failed["activity_type"] != "deterministic_check":
                resource = updated["agent_orchestration"]["work_items"][args.work_id]["resources"].get(failed["session_resource_id"])
                if not isinstance(resource, dict) or resource.get("state") != "REGISTERED":
                    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SESSION-CLOSE-UNPROVEN", args.activity_id)
                resource["state"] = "CLOSE_PENDING"
            return updated
        committed = store.transact(root, record_failure)
        return {"verdict": "FAILED", "activity_id": args.activity_id, "diagnostic": diagnostic,
                "store_revision": committed.revision}, EXIT_BLOCKED
    result = _checkpoint_ref(root, args.result)
    assert result is not None
    output = {"files": [], "return_ref": result, "effect_ref": None}
    if existing["state"] == "DISPATCHED":
        try:
            recorded = contract.record_activity_result(existing, result_ref=result["ref"], result_sha256=result["sha256"],
                                                       output_manifest=output, diagnostic_ref=None)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-RESULT-INVALID", str(exc)) from exc
        def record(document: dict[str, Any]) -> dict[str, Any]:
            updated = _replace_activity(document, args.work_id, args.activity_id, existing, recorded)
            if recorded["activity_type"] != "deterministic_check":
                resource_id = recorded["session_resource_id"]
                resource = updated["agent_orchestration"]["work_items"][args.work_id]["resources"].get(resource_id)
                if not isinstance(resource, dict) or resource.get("state") != "REGISTERED":
                    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SESSION-CLOSE-UNPROVEN", args.activity_id)
                resource["state"] = "CLOSE_PENDING"
            return updated
        committed = store.transact(root, record)
        recorded_revision = committed.revision
    else:
        recorded = existing
        if (recorded.get("result_ref") != result["ref"] or recorded.get("result_sha256") != result["sha256"]
                or recorded.get("output_manifest") != output or recorded.get("diagnostic_ref") is not None):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-RESULT-INVALID", args.activity_id)
        recorded_revision = snapshot.revision
    if args.kind == "deterministic_check":
        snapshot = store.read_snapshot(root); item, bound = current(snapshot.document)
        recorded = item["activities"][args.activity_id]
        try:
            accepted = contract.accept_activity(
                recorded, context=bound, observation=None, acceptance_ref=result["ref"],
                current_input_sha256=current_input_sha256)
        except contract.OrchestrationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-RESULT-INVALID", str(exc)) from exc
        committed = store.transact(root, lambda document: _replace_activity(
            document, args.work_id, args.activity_id, recorded, accepted))
        return {"verdict": "ACCEPTED", "activity_id": args.activity_id,
                "store_revision": committed.revision}, EXIT_OK
    if not args.observation:
        return {"verdict": "RESULT-RECORDED", "activity_id": args.activity_id,
                "store_revision": recorded_revision}, EXIT_OK
    observation, _observation_ref = _activity_json(root, args.observation, "SPECIALIST-CAPABILITY-UNPROVEN")
    snapshot = store.read_snapshot(root); item, bound = current(snapshot.document)
    recorded = item["activities"][args.activity_id]
    try:
        accepted = contract.accept_activity(recorded, context=bound, observation=observation,
                                            acceptance_ref=result["ref"],
                                            review_verdict=args.review_verdict,
                                            current_input_sha256=current_input_sha256)
    except contract.OrchestrationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SPECIALIST-CAPABILITY-UNPROVEN", str(exc)) from exc
    def accept(document: dict[str, Any]) -> dict[str, Any]:
        updated = _replace_activity(document, args.work_id, args.activity_id, recorded, accepted)
        target = updated["agent_orchestration"]["work_items"][args.work_id]
        resource_id = accepted["session_resource_id"]
        resource = target["resources"].get(resource_id)
        if not isinstance(resource, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SESSION-CLOSE-UNPROVEN", args.activity_id)
        target["resources"][resource_id] = contract.close_session_resource(
            resource, observation, acceptance_ref=result["ref"])
        return updated
    committed = store.transact(root, accept)
    verdict = accepted["review_verdict"] if args.kind == "reviewer" else "ACCEPTED"
    return {"verdict": verdict, "activity_id": args.activity_id,
            "store_revision": committed.revision}, EXIT_OK if verdict in {"APPROVED", "ACCEPTED"} else EXIT_BLOCKED


def _replace_activity(document: dict[str, Any], work_id: str, activity_id: str,
                      expected: dict[str, Any], replacement: dict[str, Any]) -> dict[str, Any]:
    item = document["agent_orchestration"]["work_items"][work_id]
    if item["activities"].get(activity_id) != expected:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-STATE-DIVERGENCE", activity_id)
    item["activities"][activity_id] = replacement
    return document


def _attest_resolution(root: Path, args: argparse.Namespace, item: Path, step: str, workflow_version: str,
                       orchestration_context: dict[str, Any] | None,
                       modules: tuple[Any, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Resolve the runtime, the step's shipped skill and its catalog for minting.

    ``modules`` is ``(gauntlet, step_skills)`` as loaded by ``attest_command``:
    only the closed Gauntlet handlers load the resolver themselves.
    """
    versions = grill_core_module("workflow_versions")
    gauntlet, step_skills_module = modules
    if workflow_version in {"v4", "v5"}:
        config_fd: int | None = None
        try:
            config_fd = gauntlet.open_config_directory(root)
            activation = gauntlet.require_activation(config_fd, args.work_id)
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        finally:
            if config_fd is not None:
                os.close(config_fd)
        runtime = activation["runtime"]["id"]
        if orchestration_context is not None:
            context_runtime = orchestration_context.get("runtime")
            context_activation = orchestration_context.get("activation")
            if context_activation is not None:
                if not isinstance(context_activation, dict):
                    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVATION-REQUIRED", args.work_id)
                activation = context_activation
                runtime = context_runtime
            elif context_runtime != runtime:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVATION-RUNTIME-DIVERGENT",
                                 "successor runtime requires a proved effective activation", extra={"work_id": args.work_id})
        if args.runtime is not None and args.runtime != runtime:
            raise CliFailure(
                EXIT_BLOCKED,
                "BLOCKED",
                "ACTIVATION-RUNTIME-DIVERGENT",
                "--runtime may only confirm the immutable activation runtime",
                extra={"expected": runtime, "actual": args.runtime, "work_id": args.work_id},
            )
    else:
        # V3 predates Gauntlet activation and its only shipped capability proof
        # is Claude.  Keep minting legacy successor receipts readable without
        # retroactively requiring an activation V3 cannot create.
        runtime = args.runtime or "claude"

    # Compose the shipped asset paths from the versioned SSOT, the same way the
    # Gauntlet composes them -- not by importing the Gauntlet. Its resolver
    # bindings are a closed set on purpose, and widening that set to reach a
    # filename table would trade one duplication for a coupling.
    assets = Path(__file__).resolve().parent.parent / "assets"
    try:
        registry_bytes = (assets / versions.REGISTRY_FILENAME_BY_VERSION[workflow_version]).read_bytes()
        catalog_filename = versions.CATALOG_FILENAME_BY_VERSION_RUNTIME[workflow_version][runtime]
        catalog_bytes = (assets / catalog_filename).read_bytes()
        catalog = step_skills_module.parse_strict(catalog_bytes)
        resolutions, trusted_catalogs_bytes = step_skills_module.resolve_shipped_workflow_skills(
            (step,), runtime, step_skills_module.registry_sha256(registry_bytes),
            registry=registry_bytes, catalog=catalog,
            trusted_catalogs_path=assets / versions.TRUSTED_CATALOGS_FILENAME_BY_VERSION[workflow_version],
        )
    except KeyError as error:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "WORKFLOW-VERSION-UNKNOWN",
                         str(workflow_version), extra={"work_id": args.work_id}) from error
    except Exception as error:  # resolution owns its own refusal vocabulary
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SKILL-RESOLUTION-FAILED",
                         str(error), extra={"work_id": args.work_id, "step": step}) from error
    resolution = resolutions[0]

    if workflow_version in {"v4", "v5"}:
        activation_identity = {
            "work_item": {
                "document_sha256": hashlib.sha256(
                    safe_read_regular_fd(root, item / "WORK-ITEM.json")
                ).hexdigest(),
            },
            "workflow": {
                "version": workflow_version,
                "sha256": hashlib.sha256(
                    safe_read_regular_fd(root, root / "WORKFLOW.md")
                ).hexdigest(),
                "registry_sha256": step_skills_module.registry_sha256(registry_bytes),
            },
            "runtime": {"id": runtime, "adapter": resolution["adapter"]},
            "catalog": {
                "id": catalog["catalog_id"],
                "document_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
                "resolution_sha256": catalog["catalog_sha256"],
                "trusted_asset_document_sha256": hashlib.sha256(trusted_catalogs_bytes).hexdigest(),
            },
        }
        if any(activation.get(key) != value for key, value in activation_identity.items()):
            raise CliFailure(
                EXIT_BLOCKED,
                "BLOCKED",
                "IDENTITY-STALE",
                "attestation inputs differ from the immutable Gauntlet activation",
                extra={"work_id": args.work_id, "step": step},
            )
    return runtime, resolution, catalog


def _mint_one(args: argparse.Namespace, step: str, artifact: str, supersedes: str | None,
              dependency_override: dict[str, Any] | None, modules: tuple[Any, Any]) -> dict[str, Any]:
    """Mint one step's chain in memory; the caller decides where it is written.

    ``dependency_override`` names the predecessor output to declare instead of
    the recorded one: re-chaining mints a step on top of a predecessor that is
    minted but not yet checkpointed, so its output is not recorded anywhere yet.
    """
    root = project_root(args.root)
    if step == "tasks":
        _require_visual_gate(root, args.work_id)
    item = resolve_development_item(root, args.work_id)
    attestation = grill_core_module("attestation")
    coverage = _step_activity_coverage(root, args.work_id, step)
    if coverage is not None:
        try:
            attestation.require_activity_coverage(coverage, step_id=step)
        except attestation.AttestationError as exc:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-REQUIRED", exc.reason) from exc
    versions = grill_core_module("workflow_versions")
    step_skills_module = modules[1]
    store = grill_core_module("store")
    orchestration_context = None
    snapshot = store.read_snapshot(root, required=False)
    if snapshot is not None:
        item_record = snapshot.document.get("agent_orchestration", {}).get("work_items", {}).get(args.work_id)
        if isinstance(item_record, dict):
            candidate = item_record.get("contexts", {}).get(item_record.get("current_context_id"))
            if isinstance(candidate, dict):
                orchestration_context = candidate

    _, state = read_development_state(root, item, args.work_id)
    development = state.get("development") or {}
    workflow_version = development_workflow_version(development)
    if workflow_version is None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-UNTRACKED", args.work_id)

    # A ``worker-required`` step may be attested by the leader -- the step
    # receipt is always the leader's -- but only against proof that dispatched
    # workers actually did the work. That proof is converged waves on the run,
    # read from durable state rather than declared by the caller: a flag the
    # operator sets would be the self-certification the class exists to prevent.
    worker_execution_proven = _converged_waves_exist(root, args.work_id)
    try:
        # Refuse before reading anything: without the proof, a step whose
        # isolation is its safety mechanism must not even get as far as hashing
        # an artefact.
        execution_class = attestation.require_emission_allowed(
            step, workflow_version, versions,
            worker_execution_proven=worker_execution_proven)
        artefact_sha256, artefact_size = attestation.artefact_digest(
            lambda rel: safe_read_regular_fd(root, root / rel), artifact,
        )
    except attestation.AttestationError as error:
        raise CliFailure(EXIT_NO_GO, "NO-GO", error.reason,
                         f"{error.code}: {error.reason}",
                         extra={"work_id": args.work_id, **error.detail}) from error

    project_id = store.project_identity(root)["project_id"]
    runtime, resolution, catalog = _attest_resolution(
        root, args, item, step, workflow_version, orchestration_context, modules)

    # The authorization is read, not minted: it is a human artefact that exists
    # before the chain. `ship` is the only step whose resolution demands one,
    # and without this the emitter could mint for ten steps and not the
    # eleventh -- the same shape of gap the emitter itself was built to close.
    # A re-chain mints several steps at once; the authorization is ship's alone.
    human_authorization = None
    if args.authorization and (step == "ship" or not getattr(args, "rechain", False)):
        human_authorization = load_checkpoint_attestation(root, args.authorization)

    run_id = args.run_id or f"leader-{args.work_id}"
    lease_id, fencing_token = attestation.leader_lease(run_id, step)
    head = git_optional(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "BASE-COMMIT-UNAVAILABLE",
                         "current Git base commit is unavailable", extra={"work_id": args.work_id})

    # Each step must declare the attested output of the one before it: that is
    # what makes the chain a chain rather than eleven unrelated receipts. The
    # core already records those outputs in the shape dependency_outputs wants,
    # so inherit them instead of rebuilding -- a rebuilt copy is one more place
    # for the two to disagree.
    # Re-attestation of a step already closed: the successor names what it
    # replaces and advances the round, so the prior receipt stays readable
    # instead of being contradicted by bytes that no longer match it (BL-0201).
    execution_round = 1
    supersedes_step_execution_id = None
    supersedes_attempt_id = None
    if supersedes:
        prior = load_checkpoint_attestation(root, supersedes)
        prior_output = prior.get("step_output") if isinstance(prior, dict) else None
        if not isinstance(prior_output, dict) or prior_output.get("step_id") != step:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SUPERSEDE-BUNDLE-INVALID", supersedes,
                             extra={"work_id": args.work_id, "step": step})
        supersedes_step_execution_id = prior_output.get("step_execution_id")
        supersedes_attempt_id = prior_output.get("attempt_id")
        prior_round = prior_output.get("execution_round")
        if not isinstance(prior_round, int) or isinstance(prior_round, bool) or prior_round < 1:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SUPERSEDE-BUNDLE-INVALID", supersedes,
                             extra={"work_id": args.work_id, "step": step})
        execution_round = prior_round + 1

    sequence = development_sequence(development)
    attested_outputs = development.get("attested_outputs") or {}
    index = sequence.index(step) if step in sequence else 0
    dependency_outputs = []
    if dependency_override is not None:
        dependency_outputs = [dependency_override]
    elif index > 0:
        previous_step = sequence[index - 1]
        previous_output = attested_outputs.get(previous_step)
        if not isinstance(previous_output, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PREDECESSOR-UNATTESTED",
                             f"{previous_step} has no attested output to depend on",
                             extra={"work_id": args.work_id, "step": step})
        dependency_outputs = [previous_output]

    jcs = step_skills_module.sha256_jcs
    # The campaign binds every checkpoint of one run, and carries the recovery
    # generation. It must therefore be stable across steps: deriving it from the
    # step (or from HEAD, which moves with every commit) makes the second
    # checkpoint of the same run STALE against the first.
    campaign_identity = {"work_id": args.work_id, "run_id": run_id}
    identity = {"work_id": args.work_id, "step": step, "head": head}
    # Once the first checkpoint of a run is accepted, its campaign is recorded
    # and every later checkpoint must match it. Inherit the recorded values
    # instead of recomputing them: the recorded campaign is the authority, and a
    # formula that later changes would strand a run that had already started.
    derived_generation = "rg-" + hashlib.sha256(canonical(campaign_identity)).hexdigest()
    recorded = (orchestration_context.get("campaign") if orchestration_context is not None
                and isinstance(orchestration_context.get("campaign"), dict)
                else development.get("attestation_campaign"))
    if isinstance(recorded, dict):
        recovery_generation_id = recorded.get("recovery_generation_id", derived_generation)
        plan_revision = recorded.get("plan_revision", 0)
        run_id = recorded.get("run_id", run_id)
        lease_id, fencing_token = attestation.leader_lease(run_id, step)
    else:
        recovery_generation_id = derived_generation
        plan_revision = 0
    bundle = attestation.mint_chain(
        resolution=resolution,
        project_id=project_id,
        work_item_id=args.work_id,
        work_item_revision=int(state.get("version", "0").split(".")[0]) if isinstance(state.get("version"), str) else 0,
        run_id=run_id,
        step_id=step,
        attempt_id=f"{step}-{execution_round}",
        recovery_generation_id=recovery_generation_id,
        plan_revision=plan_revision,
        wave_index=versions.LEADER_WAVE_INDEX,
        worktree_id=f"wt-{args.work_id}",
        worktree_head=head,
        worker_lease_id=lease_id,
        worker_fencing_token=fencing_token,
        dispatcher_lease_id=lease_id,
        dispatcher_epoch=1,
        artefact_path=artifact,
        artefact_sha256=artefact_sha256,
        logical_plan_sha256=jcs(identity),
        executable_plan_sha256=jcs({**identity, "artifact": artifact}),
        input_fingerprint=(_v5_input_fingerprint(root, args.work_id, step, head, artefact_sha256)
                           if development.get("workflow_version") == "v5"
                           else jcs({**identity, "artifact_sha256": artefact_sha256})),
        dependency_outputs=dependency_outputs,
        catalog=catalog,
        execution_round=execution_round,
        supersedes_step_execution_id=supersedes_step_execution_id,
        supersedes_attempt_id=supersedes_attempt_id,
        human_authorization=human_authorization,
    )
    return {"bundle": bundle, "execution_class": execution_class,
            "worker_execution_proven": worker_execution_proven, "execution_round": execution_round,
            "artifact_sha256": artefact_sha256, "artifact_bytes": artefact_size}


def _write_attestation(root: Path, out: str, bundle: dict[str, Any]) -> Path:
    target = Path(out)
    if target.is_absolute() or any(part in {"", ".", ".."} for part in target.parts):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ATTESTATION-PATH", out)
    full = root / target
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _rechain_prior(root: Path, operations: dict[str, Any], step: str, execution_id: Any) -> tuple[str, dict[str, Any]]:
    """The bundle this item accepted for ``step``, found through its checkpoint operation."""
    for operation in operations.values():
        request = operation.get("request") if isinstance(operation, dict) else None
        reference = request.get("attestation") if isinstance(request, dict) else None
        if operation.get("kind") != "checkpoint" or request.get("step") != step or not isinstance(reference, dict):
            continue
        try:
            current = _checkpoint_ref(root, reference.get("ref"))
            bundle = load_checkpoint_attestation(root, reference["ref"])
        except CliFailure:
            continue
        output = bundle.get("step_output")
        if (current is not None and current["sha256"] == reference.get("sha256") and isinstance(output, dict)
                and execution_id is not None and output.get("step_execution_id") == execution_id):
            return reference["ref"], bundle
    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECHAIN-PRIOR-UNKNOWN", step)


def _rechain(args: argparse.Namespace, modules: tuple[Any, Any]) -> tuple[dict[str, Any], int]:
    """Mint successors for every stale step, each on top of the one before it.

    Everything is checked before the first byte is written: a stale step whose
    accepted bundle cannot be found, or whose artefact changed since, stops the
    re-chain with nothing minted -- a changed artefact is a new supersession,
    decided by someone, not a re-chain.
    """
    root = project_root(args.root)
    _, state = read_development_state(root, resolve_development_item(root, args.work_id), args.work_id)
    development = state.get("development") or {}
    sequence = development_sequence(development) or []
    stale = [step for step in sequence if step in (development.get("chain_stale") or [])]
    if "ship" in stale and not args.authorization:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "HUMAN-AUTHORIZATION-MISSING", "ship")
    snapshot = grill_core_module("store").read_snapshot(root, required=False)
    block = snapshot.document.get("agent_orchestration") if snapshot is not None else None
    record = block.get("work_items", {}).get(args.work_id) if isinstance(block, dict) else None
    operations = record.get("operations", {}) if isinstance(record, dict) else {}
    executions = development.get("attested_executions") or {}
    outputs = development.get("attested_outputs") or {}
    attestation = grill_core_module("attestation")
    plan = []
    for step in stale:
        prior_ref, prior = _rechain_prior(root, operations, step, executions.get(step))
        refs = prior["step_output"].get("evidence_refs")
        artifact = refs[0].get("path") if isinstance(refs, list) and refs and isinstance(refs[0], dict) else None
        if not isinstance(artifact, str):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECHAIN-PRIOR-UNKNOWN", step)
        try:
            digest, _size = attestation.artefact_digest(lambda rel: safe_read_regular_fd(root, root / rel), artifact)
        except (attestation.AttestationError, CliFailure):
            digest = None
        if digest is None or digest != (outputs.get(step) or {}).get("output_sha256"):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "RECHAIN-OUTPUT-CHANGED", step, extra={"artifact": artifact})
        plan.append((step, artifact, prior_ref))
    minted: list[dict[str, Any]] = []
    predicted: dict[str, Any] | None = None
    for step, artifact, prior_ref in plan:
        index = sequence.index(step)
        override = predicted if minted and sequence[index - 1] == minted[-1]["step"] else None
        try:
            result = _mint_one(args, step, artifact, prior_ref, override, modules)
        except CliFailure as failure:
            failure.extra = {**(failure.extra or {}), "minted": minted}
            raise
        target = _write_attestation(root, (Path(args.out) / f"{step}-r{result['execution_round']}.json").as_posix(),
                                    result["bundle"])
        predicted = attestation.accepted_output(result["bundle"]["step_output"])
        minted.append({"step": step, "attestation": target.as_posix(), "supersedes": prior_ref,
                       "artifact": artifact, "execution_round": result["execution_round"],
                       "predicted_output": predicted,
                       "next": (f"checkpoint {args.root} --work-id {args.work_id} --step {step} --state complete"
                                f" --evidence {artifact} --attestation {target.as_posix()}"
                                f" --supersedes-attestation {prior_ref} --reason <why>")})
    return {"verdict": "RECHAINED" if minted else "NOTHING-STALE", "work_id": args.work_id,
            "minted": minted}, EXIT_OK


@_gauntlet_authorized
def attest_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Mint the attestation chain for one leader-executed step.

    The core knew how to judge a chain and not how to mint one, so every step
    was unreachable by checkpoint once the gate started firing. This is the
    other half.

    What it writes is a bundle file; it never advances a step by itself. The
    caller still runs ``checkpoint --state complete --attestation <path>``, and
    the judge still has to accept it. Minting and advancing stay separate on
    purpose: a command that did both would make "the chain was accepted"
    indistinguishable from "the chain was written by the thing that wanted it
    accepted".

    ``--rechain`` mints, in order, a successor for every step in ``chain_stale``
    and writes them under ``--out``; checkpointing each one is still the
    caller's, with ``--supersedes-attestation``.
    """
    modules = (grill_core_module("gauntlet"), grill_core_module("step_skills"))
    if args.rechain:
        if args.step or args.artifact or args.supersedes:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS",
                             "--rechain derives steps, artefacts and superseded bundles itself")
        return _rechain(args, modules)
    if not args.step or not args.artifact:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "attest needs --step and --artifact")
    root = project_root(args.root)
    minted = _mint_one(args, args.step, args.artifact, args.supersedes, None, modules)
    target = _write_attestation(root, args.out, minted["bundle"])
    return {
        "verdict": "ATTESTED",
        "work_id": args.work_id,
        "step": args.step,
        "execution_class": minted["execution_class"],
        "worker_execution_proven": minted["worker_execution_proven"],
        "execution_round": minted["execution_round"],
        "supersedes": args.supersedes,
        "authorization": args.authorization,
        "artifact": args.artifact,
        "artifact_sha256": minted["artifact_sha256"],
        "artifact_bytes": minted["artifact_bytes"],
        "attestation": str(target),
        "next": (
            f"checkpoint {args.root} --work-id {args.work_id} --step {args.step} --state complete"
            f" --evidence {args.artifact} --attestation {target}"
            + (f" --supersedes-attestation {args.supersedes} --reason <why>" if args.supersedes else "")
        ),
    }, EXIT_OK


@_gauntlet_authorized
def checkpoint_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if args.step not in SEQUENCE:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-STEP", args.step)
    if args.step == "tasks" and args.state in {"in-progress", "complete"}:
        _require_visual_gate(root, args.work_id)
    item = resolve_development_item(root, args.work_id)
    snapshot_global = global_snapshotter(root)
    global_before = snapshot_global()
    lock = acquire_lock(root, args.work_id, item)
    try:
        path, state = read_development_state(root, item, args.work_id)
        state_before = safe_read_regular_fd(root, path)
        development = state.get("development")
        if development_workflow_version(development) is None:
            if not args.initialize_legacy:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-UNTRACKED", args.work_id)
            if args.from_step is not None and (args.from_step != "specify" or args.step != "specify"):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-INITIALIZATION-UNSAFE", args.work_id)
            if args.from_step is None or not args.evidence or not args.reason.strip():
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-INITIALIZATION-REQUIRES-DECISION-EVIDENCE", args.work_id)
            version = _workflow_module(root).VERSION
            development = {"schema":ACTIVE_DEVELOPMENT_SCHEMA, "workflow_version":version,
                           "sequence":SEQUENCE[:], "current_step":args.step,
                           "steps":{step:"pending" for step in SEQUENCE}, "renamed_from":{}, "audit":[]}
            state["development"] = development
            args.state = "in-progress"
        sequence = development.get("sequence"); steps = development.get("steps")
        # A trilha entra na validação de forma junto com o resto: ausente é
        # legítimo e vira lista, mas presente e de outro tipo derrubava o comando
        # com AttributeError no append lá embaixo — traceback onde devia haver
        # código nomeado.
        if sequence != development_sequence(development) or not isinstance(steps, dict) or not isinstance(development.setdefault("audit", []), list):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DEVELOPMENT-SCHEMA", args.work_id)
        if args.state in {"in-progress", "complete"}:
            coverage = _step_activity_coverage(root, args.work_id, args.step)
            if coverage is not None:
                try:
                    grill_core_module("attestation").require_activity_coverage(coverage, step_id=args.step)
                except Exception as exc:
                    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVITY-REQUIRED", str(exc)) from exc
        current = steps.get(args.step, "pending")
        evidence = []
        for value in args.evidence:
            ep = Path(value)
            if ep.is_absolute() or any(p in {"", ".", ".."} for p in ep.parts):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-EVIDENCE-PATH", value)
            evidence_path = root / ep
            if evidence_path.is_symlink():
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "EVIDENCE-SYMLINK", value)
            reject_symlink_chain(root, evidence_path, allow_missing=True)
            if not evidence_path.exists():
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "EVIDENCE-MISSING", value)
            if not evidence_path.is_file():
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "EVIDENCE-NOT-REGULAR", value)
            try:
                data = safe_read_regular_fd(root, evidence_path)
            except CliFailure as exc:
                if exc.code in {"SYMLINK-REJECTED", "UNSAFE-FILE"}:
                    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "EVIDENCE-SYMLINK", value) from exc
                raise
            evidence.append({"path": ep.as_posix(), "sha256": hash_bytes(data)})
        reason = args.reason.strip()
        execution_branch: str | None = None
        # The binding belongs to one phase, not to the whole work item.  A
        # first `specify` normally creates it; an older in-flight state may
        # have progressed past that checkpoint, so its next resumed transition
        # records the observed branch as an explicit, audited backfill instead
        # of remaining permanently blocked on init provenance.
        existing_branch = development.get("execution_branch", _MISSING)
        execution_branch = git_optional(root, "branch", "--show-current")
        if not execution_branch:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DETACHED-HEAD", "checkpoint requires an attached execution branch")
        run_git(root, "check-ref-format", "--branch", execution_branch)
        if existing_branch is _MISSING or existing_branch is None:
            # Explicit backfill for legacy/in-between-phase cycles.  It becomes
            # durable only after the requested state transition is valid.
            #
            # T048: no comparison against the context's worktree-identity stamp
            # here. That stamp is written once, at context creation, and no
            # verb ever re-writes it -- while a phase turn clears this very
            # binding on purpose, expecting the next phase's first confirmation
            # to mint a fresh one. Comparing an unrenewed stamp against the
            # live branch is monotonic and refuses forever, permanently, for
            # every work item that was ever taken over or resumed. The real
            # guard against a stale binding is `_continuity_refuse_branch_
            # contradiction`, and it only fires once `execution_branch` is
            # set -- exactly the case `existing_branch is _MISSING or None`
            # excludes. There is no upstream proof that the live branch is
            # the one the context ran on: `branch` was pulled out of the
            # structural tuple in T035, and two branches inside the same
            # worktree look identical on project/path/git_common_dir alone.
            # This just records the current branch as the first binding; it
            # does not verify one.
            pass
        elif not isinstance(existing_branch, str) or not existing_branch:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DEVELOPMENT-SCHEMA", args.work_id)
        elif existing_branch != execution_branch:
            raise CliFailure(
                EXIT_BLOCKED,
                "BLOCKED",
                "EXECUTION-BRANCH-MISMATCH",
                f"work item is bound to {existing_branch}",
            )
        payload = {"step": args.step, "state": args.state, "evidence": evidence, "reason": reason}
        if execution_branch is not None:
            payload["execution_branch"] = execution_branch
        audit = development.setdefault("audit", [])
        superseding = bool(getattr(args, "supersedes_attestation", None))
        if superseding:
            payload["supersedes"] = args.supersedes_attestation
        # A supersession is not a transition, so the identical-state guard does
        # not apply to it: the step was complete before and stays complete.
        if not superseding and current == args.state:
            if audit and audit[-1] == payload:
                return {"verdict":"REUSED", "work_id":args.work_id, **payload, "current_step":development.get("current_step")}, EXIT_OK
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STATE-DIVERGENCE", args.step)
        index = sequence.index(args.step)
        attestation_result: dict[str, Any] | None = None
        superseded_output: dict[str, Any] | None = None
        if superseding:
            attestation_result, superseded_output = verify_supersession(
                root, development,
                work_id=args.work_id, step_id=args.step,
                current=current, state=args.state, reason=reason, evidence=evidence,
                attestation_path=args.attestation, superseded_path=args.supersedes_attestation,
            )
        elif args.state == "in-progress":
            if current not in {"pending", "blocked"} or any(steps.get(s) != "complete" for s in sequence[:index]):
                # Uma fase inteiramente concluída não é transição inválida: é fase
                # encerrada esperando virada. Devolver INVALID-TRANSITION aqui
                # mandava o operador procurar defeito onde faltava um passo de
                # ciclo, e foi assim que duas fases inteiras ficaram sem trilha.
                if all(steps.get(s) == "complete" for s in sequence):
                    raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PHASE-TURN-REQUIRED", args.step)
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-TRANSITION", args.step)
        elif args.state == "complete":
            if not evidence:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "EVIDENCE-REQUIRED", args.step)
            if current != "in-progress" or any(steps.get(s) != "complete" for s in sequence[:index]):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-TRANSITION", args.step)
            if args.step == "ship" and not (steps.get("verify") == steps.get("review") == "complete"):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SHIP-GATE", args.step)
            # Shipping is where the chain stops being an internal record and
            # starts being the claim made to everyone downstream. A step still
            # resting on a replaced predecessor cannot be part of that claim.
            #
            # Checked before the run gates: a stale chain says the record itself
            # is unreliable, which decides the question ahead of anything the
            # record might report about execution.
            if args.step == "ship" and development.get("chain_stale"):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CHAIN-STALE",
                                 ", ".join(development["chain_stale"]))
            if args.step == "ship":
                require_converged_runs(root, args.work_id)
            if checkpoint_attestation_required(root):
                attestation_result = verify_checkpoint_attestation(
                    root,
                    development,
                    work_id=args.work_id,
                    step_id=args.step,
                    attestation_path=args.attestation,
                )
        elif args.state == "blocked":
            if current != "in-progress" or not reason:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "REASON-REQUIRED", args.step)
        if execution_branch is not None:
            development["execution_branch"] = execution_branch
        steps[args.step] = args.state; audit.append(payload)
        if attestation_result is not None:
            development["attestation_campaign"] = attestation_result["campaign"]
            outputs = development.setdefault("attested_outputs", {})
            development.setdefault("attested_executions", {})[args.step] = \
                attestation_result["step_execution_id"]
            if superseded_output is not None:
                development.setdefault("superseded_outputs", {}).setdefault(args.step, []).append(superseded_output)
                payload["chain_stale"] = mark_chain_stale(development, args.step)
            outputs[args.step] = attestation_result["output"]
        development["current_step"] = next((s for s in sequence if steps.get(s) != "complete"), "complete")
        orchestrated = _commit_orchestrated_checkpoint(root, path, state_before, state, args, payload)
        if orchestrated is not None:
            return orchestrated, EXIT_OK
        atomic_write(root, path, (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
        return {"verdict":"UPDATED", "work_id":args.work_id, **payload, "current_step":development["current_step"]}, EXIT_OK
    finally:
        shutil.rmtree(lock, ignore_errors=True)
        if snapshot_global() != global_before:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "GLOBAL-MUTATION", args.work_id)



def _advance_operation_id(root: Path, work_id: str, step: str, state: str,
                          development: dict[str, Any], attestation: str | None) -> str:
    """Derive a checkpoint id from the state it moves, never from the call.

    The audit length is what separates two legitimate visits to the same
    step: a phase turn or a resume from ``blocked`` appends to the audit, so
    the next visit gets a fresh id instead of a silent ``REUSED``.
    """
    reference = _checkpoint_ref(root, attestation) if state == "complete" else None
    return "adv-" + grill_core_module("store").jcs_sha256({
        "work_id": work_id, "step": step, "state": state,
        "audit_len": len(development.get("audit") or []),
        "attestation_sha256": reference["sha256"] if reference else None,
    })[:32]


@_gauntlet_authorized
def advance_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Close the current step and open the next one, as one resumable call.

    It composes the verbs a leader runs between steps -- ``checkpoint
    complete``, the next step's assessment, ``gauntlet-step-enter`` and
    ``checkpoint in-progress`` -- through their own handlers, so every gate
    each of them owns still fires. Human gates stay outside: a preview
    approval, a ship authorization, a reviewer verdict, a phase turn or a
    resume from ``blocked`` are refused here exactly as the verbs refuse them.
    A refusal lists the operations already done; re-running resumes.
    """
    root = project_root(args.root)
    store = grill_core_module("store")
    operations: list[dict[str, Any]] = []
    invocation: dict[str, Any] | None = None

    def development_now() -> dict[str, Any]:
        _path, state = read_development_state(root, resolve_development_item(root, args.work_id), args.work_id)
        return state.get("development") or {}

    def checkpoint(development: dict[str, Any], step: str, state: str) -> None:
        operation_id = _advance_operation_id(root, args.work_id, step, state, development, args.attestation)
        argv = ["checkpoint", args.root, "--work-id", args.work_id, "--step", step, "--state", state,
                "--operation-id", operation_id, "--session-ref", args.session_ref, "--reason", "advance"]
        if state == "complete":
            argv += [value for evidence in args.evidence for value in ("--evidence", evidence)]
            argv += ["--attestation", args.attestation] if args.attestation else []
        payload, _code = checkpoint_command(build_parser().parse_args(argv))
        operations.append({"verb": "checkpoint", "step": step, "state": state,
                           "operation_id": operation_id, "verdict": payload["verdict"]})

    snapshot = store.read_snapshot(root, required=False)
    block = snapshot.document.get("agent_orchestration") if snapshot is not None else None
    if not isinstance(block, dict) or not isinstance(block.get("work_items", {}).get(args.work_id), dict):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ORCHESTRATION-MIGRATION-REQUIRED", args.work_id)
    completed = None
    try:
        development = development_now()
        current = development.get("current_step")
        state = (development.get("steps") or {}).get(current)
        if state == "blocked":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STEP-BLOCKED", current)
        if state == "in-progress":
            checkpoint(development, current, "complete")
            completed, development = current, development_now()
        step = development.get("current_step")
        if step not in (development_sequence(development) or []):
            return {"verdict": "DONE", "work_id": args.work_id, "completed": completed,
                    "entered": None, "invocation_context": None, "operations": operations}, EXIT_OK
        policy = json.loads(_policy_path(root, args.work_id).read_bytes())
        try:
            _step_assessment(root, args.work_id, step, policy)
        except CliFailure as failure:
            # Missing or unreadable is Jev's to write; stale is a decision
            # someone already made on files that changed, never overwritten.
            if failure.code != "STEP-ASSESSMENT-INVALID":
                raise
            decision, _code = decide_command(argparse.Namespace(
                root=args.root, kind="step-assessment", file=None, context=None,
                work_id=args.work_id, step=step, apply=True))
            operations.append({"verb": "decide", "step": step, "written": decision.get("written")})
            if not decision.get("written"):
                return {"verdict": "ASSESSMENT-REQUIRED", "work_id": args.work_id, "completed": completed,
                        "entered": None, "step": step, "decision": decision,
                        "operations": operations}, EXIT_BLOCKED
        record = store.read_snapshot(root).document["agent_orchestration"]["work_items"][args.work_id]
        context = record.get("contexts", {}).get(record.get("current_context_id"))
        if not isinstance(context, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CONTEXT-FENCED", args.work_id)
        entered, _code = gauntlet_step_enter_command(build_parser().parse_args(
            ["gauntlet-step-enter", args.root, "--work-id", args.work_id, "--context-id", record["current_context_id"],
             "--epoch", str(context["epoch"]), "--session-ref", args.session_ref, "--step", step]
            + (["--frontend"] if args.frontend else [])))
        invocation = entered["invocation_context"]
        operations.append({"verb": "gauntlet-step-enter", "step": step})
        if (development.get("steps") or {}).get(step) == "pending":
            checkpoint(development, step, "in-progress")
    except CliFailure as failure:
        failure.extra = {**(failure.extra or {}), "completed": completed, "operations": operations,
                         "invocation_context": invocation}
        raise
    return {"verdict": "ADVANCED", "work_id": args.work_id, "completed": completed, "entered": step,
            "invocation_context": invocation, "operations": operations}, EXIT_OK


@_gauntlet_authorized
def phase_turn_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Close a finished phase and hand the step matrix back to the next one.

    The matrix lives once per work item while the roadmap holds several phases,
    so a completed cycle leaves every step ``complete`` and the next phase with
    nowhere to start. The history is not lost by resetting: ``development.audit``
    is append-only and already records every transition, which is why this
    reopens the matrix instead of changing the shape of the state — no existing
    bundle needs migrating, including ones already projected globally.
    """
    root = project_root(args.root)
    item = resolve_development_item(root, args.work_id)
    snapshot_global = global_snapshotter(root)
    global_before = snapshot_global()
    lock = acquire_lock(root, args.work_id, item)
    try:
        path, state = read_development_state(root, item, args.work_id)
        development = state.get("development")
        if development_workflow_version(development) is None:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-UNTRACKED", args.work_id)
        sequence = development.get("sequence")
        steps = development.get("steps")
        if sequence != development_sequence(development) or not isinstance(steps, dict) or not isinstance(development.setdefault("audit", []), list):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DEVELOPMENT-SCHEMA", args.work_id)
        reason = args.reason.strip()
        if not reason:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "REASON-REQUIRED", args.work_id)

        # Idempotência antes da recusa, e não depois: um registro inteiro em
        # `pending` é exatamente o que esta operação produz, então reprová-lo por
        # "fase incompleta" tornaria a reexecução impossível.
        if all(steps.get(s) == "pending" for s in sequence):
            return {"verdict": "REUSED", "work_id": args.work_id, "reason": reason,
                    "current_step": development.get("current_step")}, EXIT_OK
        pending = [s for s in sequence if steps.get(s) != "complete"]
        if pending:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "PHASE-INCOMPLETE", ", ".join(pending))
        # Turning the phase does not resolve a stale chain, it outlives it: the
        # matrix resets and the ledger does not, so the next phase would be
        # refused at ship over receipts that no longer apply to it. Leaving an
        # unverifiable chain behind is precisely what the ledger exists to stop,
        # so the turn is refused until the steps it names are attested again.
        if development.get("chain_stale"):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "CHAIN-STALE",
                             ", ".join(development["chain_stale"]))

        development["steps"] = {step: "pending" for step in sequence}
        development["current_step"] = sequence[0]
        previous_execution_branch = development.get("execution_branch", _MISSING)
        if previous_execution_branch is _MISSING or previous_execution_branch is None:
            previous_execution_branch = git_optional(root, "branch", "--show-current")
            if not previous_execution_branch:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DETACHED-HEAD", "phase turn requires an attached execution branch")
            run_git(root, "check-ref-format", "--branch", previous_execution_branch)
            # T048: no comparison against the context's worktree-identity stamp
            # here either, for the same reason as the step-confirmation mint:
            # the stamp is never re-written, this very binding is cleared on
            # every phase turn by design (see below). The real guard against a
            # stale binding is `_continuity_refuse_branch_contradiction`, and it
            # only fires once `execution_branch` is set -- exactly the case
            # `previous_execution_branch is _MISSING or None` excludes. There is
            # no upstream proof that the live branch is the one the context ran
            # on: `branch` was pulled out of the structural tuple in T035, and
            # two branches inside the same worktree look identical on
            # project/path/git_common_dir alone. This just records the current
            # branch as the first binding for the new phase; it does not verify
            # one.
        elif not isinstance(previous_execution_branch, str) or not previous_execution_branch:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DEVELOPMENT-SCHEMA", args.work_id)
        else:
            live_branch = git_optional(root, "branch", "--show-current")
            if not live_branch:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DETACHED-HEAD", "phase turn requires an attached execution branch")
            run_git(root, "check-ref-format", "--branch", live_branch)
            if live_branch != previous_execution_branch:
                raise CliFailure(
                    EXIT_BLOCKED,
                    "BLOCKED",
                    "EXECUTION-BRANCH-MISMATCH",
                    f"work item is bound to {previous_execution_branch}",
                )
        # The prior branch remains in append-only audit history.  The active
        # binding is deliberately cleared so the first `specify` of the next
        # phase can bind its own branch.
        development["execution_branch"] = None
        development["audit"].append(
            {"step": "phase-turn", "state": "turned", "evidence": [], "reason": reason,
             "previous_execution_branch": previous_execution_branch})
        atomic_write(root, path, (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
        return {"verdict": "TURNED", "work_id": args.work_id, "reason": reason,
                "current_step": development["current_step"],
                "previous_execution_branch": previous_execution_branch}, EXIT_OK
    finally:
        shutil.rmtree(lock, ignore_errors=True)
        if snapshot_global() != global_before:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "GLOBAL-MUTATION", args.work_id)


STATUS_TIMEOUT_SECONDS = 30


def status_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Public workspace entry point for the read-only status projection."""
    script = Path(__file__).with_name("grill_status.py")
    command = [sys.executable, str(script), str(args.root)]
    if args.work_id:
        command += ["--work-id", args.work_id]
    if args.current_worktree:
        command.append("--current-worktree")
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=STATUS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"schema": "grill-status/v1", "verdict": "BLOCKED", "code": "STATUS-TIMEOUT", "next_action": "resolver-bloqueios"}, EXIT_BLOCKED
    try:
        payload = json.loads(process.stdout.strip())
    except json.JSONDecodeError:
        return {"schema": "grill-status/v1", "verdict": "BLOCKED", "code": "STATUS-INVALID-OUTPUT"}, EXIT_BLOCKED
    if not isinstance(payload, dict):
        return {"schema": "grill-status/v1", "verdict": "BLOCKED", "code": "STATUS-SCHEMA"}, EXIT_BLOCKED
    warnings = _stash_warnings(Path(args.root))
    if warnings:
        payload["warnings"] = warnings
    return payload, process.returncode if process.returncode in {0, 1, 2, 3} else EXIT_BLOCKED


def _stash_warnings(root: Path) -> list[str]:
    """A stash holding untracked files adds a parentless commit that shifts the
    project id (store.project_identity), and gauntlet-run then refuses
    PROJECT-IDENTITY-DIVERGENCE. Said before it bites, never acted on."""
    process = subprocess.run(["git", "-C", str(root), "log", "-g", "--format=%gd %P", "refs/stash"],
                             capture_output=True, text=True, check=False)
    return [f"STASH-SHIFTS-PROJECT-ID: {line.split()[0]} guarda arquivos não rastreados; "
            "drop com backup por SHA antes de gauntlet-run"
            for line in process.stdout.splitlines() if len(line.split()) == 4]


def status_markdown_command(args: argparse.Namespace) -> int:
    """Emit the canonical human renderer without changing JSON status defaults."""
    script = Path(__file__).with_name("grill_status.py")
    command = [sys.executable, str(script), str(args.root), "--format", "markdown"]
    if args.work_id:
        command += ["--work-id", args.work_id]
    if args.current_worktree:
        command.append("--current-worktree")
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=STATUS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        sys.stdout.write("| Item | Status | Pendência |\n|---|---|---|\n| workspace | blocked | STATUS-TIMEOUT: resolver bloqueios |\n")
        return EXIT_BLOCKED
    if not process.stdout:
        sys.stdout.write("| Item | Status | Pendência |\n|---|---|---|\n| workspace | blocked | STATUS-INVALID-OUTPUT: resolver bloqueios |\n")
        return EXIT_BLOCKED
    sys.stdout.write(process.stdout)
    for warning in _stash_warnings(Path(args.root)):
        sys.stdout.write(f"\n> aviso: {warning}\n")
    return process.returncode if process.returncode in {0, 1, 2, 3} else EXIT_BLOCKED


def build_parser() -> JsonParser:
    parser = JsonParser()
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=JsonParser)
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("root")
    init_parser.add_argument("--type", required=True)
    init_parser.add_argument("--slug", required=True)
    init_parser.add_argument("--work-id")
    init_parser.add_argument("--base-ref")
    init_parser.add_argument("--runtime", choices=("claude", "codex"), required=True)
    init_parser.add_argument("--session-ref")
    init_parser.add_argument("--allow-install", action="store_true", dest="allow_install")
    init_parser.add_argument("--require-dependencies", action="store_true", dest="require_dependencies")
    init_parser.add_argument("--skip-backlog", action="store_true", dest="skip_backlog")
    # Same reason backlog-sync needed it: without --db every run reaches the
    # operator's real store, so coverage would consult a different backlog on
    # CI than on a developer machine — and, worse, could write to it.
    init_parser.add_argument("--db")
    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("root")
    preflight_parser.add_argument("--runtime", choices=("claude", "codex"), required=True)
    preflight_parser.add_argument("--session-ref")
    preflight_parser.add_argument("--allow-install", action="store_true", dest="allow_install")
    preflight_parser.add_argument("--skip-backlog", action="store_true", dest="skip_backlog")
    preflight_parser.add_argument("--db")
    preflight_parser.add_argument("--remove-shadowed-skills", action="store_true", dest="remove_shadows")
    triage_parser = subparsers.add_parser("triage")
    triage_parser.add_argument("root")
    triage_parser.add_argument("--report", required=True)
    # No `choices=` on --route/--severity, same reason init's --type has none:
    # argparse would collapse a wrong value into INVALID-ARGUMENTS, while the
    # triage module answers with INVALID-ROUTE/INVALID-SEVERITY and lists what
    # it accepts.
    triage_parser.add_argument("--route", required=True)
    triage_parser.add_argument("--severity", required=True)
    triage_parser.add_argument("--production-impact", action="store_true", dest="production_impact")
    triage_parser.add_argument("--spec-ref", dest="spec_ref")
    # Comma-separated, the same shape `hotfix --scope` takes and validated by
    # the same validate_scope: two spellings for one concept is how they drift.
    triage_parser.add_argument("--scope")
    triage_parser.add_argument("--rollback")
    triage_parser.add_argument("--triage-id", dest="triage_id")
    triage_parser.add_argument("--apply", action="store_true")
    # No `choices=` on --kind, same reason as --route: jev answers with
    # JEV-KIND-UNKNOWN instead of argparse's INVALID-ARGUMENTS.
    decide_parser = subparsers.add_parser("decide")
    decide_parser.add_argument("root")
    decide_parser.add_argument("--kind", required=True)
    decide_parser.add_argument("--file", action="append")
    decide_parser.add_argument("--context")
    decide_parser.add_argument("--work-id", dest="work_id")
    decide_parser.add_argument("--step")
    decide_parser.add_argument("--apply", action="store_true")
    label_parser = subparsers.add_parser("decide-label")
    label_parser.add_argument("root")
    label_parser.add_argument("--work-id", dest="work_id", required=True)
    label_parser.add_argument("--kind", required=True)
    label_parser.add_argument("--step")
    label_parser.add_argument("--answers", required=True)
    backlog_parser = subparsers.add_parser("backlog-sync")
    backlog_parser.add_argument("root")
    backlog_parser.add_argument("--work-id", required=True)
    backlog_parser.add_argument("--apply", action="store_true")
    backlog_parser.add_argument("--db")
    adopt_parser = subparsers.add_parser("backlog-adopt")
    adopt_parser.add_argument("root")
    adopt_parser.add_argument("--work-id", required=True)
    adopt_parser.add_argument("--apply", action="store_true")
    adopt_parser.add_argument("--db")
    project_parser = subparsers.add_parser("backlog-project")
    project_parser.add_argument("root")
    project_parser.add_argument("--work-id", required=True)
    project_parser.add_argument("--apply", action="store_true")
    project_parser.add_argument("--db")
    migrate_backlog_parser = subparsers.add_parser("backlog-migrate")
    migrate_backlog_parser.add_argument("root")
    migrate_backlog_parser.add_argument("--work-id", required=True)
    migrate_backlog_parser.add_argument("--apply", action="store_true")
    migrate_backlog_parser.add_argument("--db")
    verify_parser = subparsers.add_parser("backlog-verify")
    verify_parser.add_argument("root")
    verify_parser.add_argument("--work-id", required=True)
    verify_parser.add_argument("--db")
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("root")
    audit_parser.add_argument("--work-id")
    audit_parser.add_argument("--artifact-root")
    audit_parser.add_argument("--project-root")
    reseal_parser = subparsers.add_parser("constitution-reseal")
    reseal_parser.add_argument("root")
    reseal_parser.add_argument("--work-id", required=True)
    reseal_parser.add_argument("--context-id", required=True)
    reseal_parser.add_argument("--epoch", type=int, required=True)
    reseal_parser.add_argument("--session-ref", required=True)
    reseal_parser.add_argument("--human-evidence", required=True)
    reseal_parser.add_argument("--apply", action="store_true")
    reseal_parser.add_argument("--expected-sha256")
    reconcile_parser = subparsers.add_parser("reconcile")
    reconcile_parser.add_argument("root")
    reconcile_parser.add_argument("--source-root", action="append", default=[])
    reconcile_parser.add_argument("--source-ref", action="append", default=[])
    reconcile_parser.add_argument("--work-id")
    reconcile_parser.add_argument("--apply", action="store_true")
    reconcile_parser.add_argument("--integration-branch")
    hotfix_parser = subparsers.add_parser("hotfix")
    hotfix_parser.add_argument("root")
    hotfix_parser.add_argument("--slug", required=True)
    hotfix_parser.add_argument("--scope", required=True)
    hotfix_parser.add_argument("--reproduction", required=True)
    hotfix_parser.add_argument("--evidence", required=True)
    hotfix_parser.add_argument("--correction-test", required=True, dest="correction_test")
    hotfix_parser.add_argument("--rollback", required=True)
    hotfix_parser.add_argument("--constitution-evidence", required=True, dest="constitution_evidence")
    hotfix_parser.add_argument("--test-command", required=True, dest="test_command")
    hotfix_parser.add_argument("--test-timeout", type=int, default=30, dest="test_timeout")
    hotfix_parser.add_argument("--work-id")
    hotfix_parser.add_argument("--base-ref")
    go_parser = subparsers.add_parser("hotfix-go")
    go_parser.add_argument("root")
    go_parser.add_argument("--work-id", required=True)
    migrate_parser = subparsers.add_parser("migrate")
    migrate_parser.add_argument("root")
    migrate_parser.add_argument("--type", required=True)
    migrate_parser.add_argument("--slug", required=True)
    migrate_parser.add_argument("--work-id")
    migrate_parser.add_argument("--base-ref")
    migrate_parser.add_argument("--apply", action="store_true")
    migrate_v3_parser = subparsers.add_parser("migrate-v3")
    migrate_v3_parser.add_argument("root")
    migrate_v3_parser.add_argument("--work-id", required=True)
    migrate_v3_parser.add_argument("--rebind-workflow", action="store_true")
    migrate_v3_parser.add_argument("--apply", action="store_true")
    migrate_v4_parser = subparsers.add_parser("migrate-v4")
    migrate_v4_parser.add_argument("root")
    migrate_v4_parser.add_argument("--apply", action="store_true")
    migrate_v4_parser.add_argument("--expected-sha256")
    migrate_v4_parser.add_argument("--allow-local-edits", action="store_true")
    orchestration_adopt_parser = subparsers.add_parser("gauntlet-orchestration-adopt")
    orchestration_adopt_parser.add_argument("root")
    orchestration_adopt_parser.add_argument("--work-id", required=True)
    orchestration_adopt_parser.add_argument("--runtime", choices=("claude", "codex"), required=True)
    orchestration_adopt_parser.add_argument("--session-ref", required=True)
    orchestration_adopt_parser.add_argument("--scope-file", action="append", default=[])
    orchestration_adopt_parser.add_argument("--apply", action="store_true")
    orchestration_adopt_parser.add_argument("--expected-sha256")
    step_enter_parser = subparsers.add_parser("gauntlet-step-enter")
    step_enter_parser.add_argument("root")
    step_enter_parser.add_argument("--work-id", required=True)
    step_enter_parser.add_argument("--context-id", required=True)
    step_enter_parser.add_argument("--epoch", type=int, required=True)
    step_enter_parser.add_argument("--session-ref", required=True)
    step_enter_parser.add_argument("--step", required=True)
    step_enter_parser.add_argument("--new-how", action="store_true")
    step_enter_parser.add_argument("--frontend", action="store_true")
    preview_parser = subparsers.add_parser("gauntlet-preview")
    preview_parser.add_argument("root")
    preview_parser.add_argument("--work-id", required=True)
    preview_parser.add_argument("--context-id", required=True)
    preview_parser.add_argument("--epoch", type=int, required=True)
    preview_parser.add_argument("--session-ref", required=True)
    preview_parser.add_argument("--manifest", required=True)
    preview_parser.add_argument("--author-activity")
    preview_parser.add_argument("--review-activity")
    preview_decide_parser = subparsers.add_parser("gauntlet-preview-decide")
    preview_decide_parser.add_argument("root")
    preview_decide_parser.add_argument("--work-id", required=True)
    preview_decide_parser.add_argument("--context-id", required=True)
    preview_decide_parser.add_argument("--epoch", type=int, required=True)
    preview_decide_parser.add_argument("--session-ref", required=True)
    preview_decide_parser.add_argument("--manifest", required=True)
    preview_decide_parser.add_argument("--decision", choices=("approved", "rejected"), required=True)
    preview_decide_parser.add_argument("--human-evidence", required=True)
    preview_decide_parser.add_argument("--apply", action="store_true")
    preview_decide_parser.add_argument("--expected-sha256")
    activity_parser = subparsers.add_parser("gauntlet-activity")
    activity_parser.add_argument("root")
    activity_parser.add_argument("--work-id", required=True)
    activity_parser.add_argument("--context-id", required=True)
    activity_parser.add_argument("--epoch", type=int, required=True)
    activity_parser.add_argument("--session-ref", required=True)
    activity_parser.add_argument("--activity-id", required=True)
    activity_parser.add_argument("--step")
    activity_parser.add_argument("--scope")
    activity_parser.add_argument("--kind", required=True, choices=("author", "reviewer", "deterministic_check"))
    activity_parser.add_argument("--phase", required=True, choices=("prepare", "dispatch", "accept"))
    activity_parser.add_argument("--input-manifest", required=True)
    activity_parser.add_argument("--author-activity", action="append", default=[])
    activity_parser.add_argument("--files", action="append", default=[])
    activity_parser.add_argument("--observation")
    activity_parser.add_argument("--result")
    activity_parser.add_argument("--diagnostic")
    activity_parser.add_argument("--review-verdict", choices=("APPROVED", "CHANGES_REQUIRED"), default="APPROVED")
    gauntlet_init_parser = subparsers.add_parser("gauntlet-init")
    gauntlet_init_parser.add_argument("root")
    gauntlet_init_parser.add_argument("--work-id", required=True)
    gauntlet_init_parser.add_argument("--max-workers", type=int, required=True)
    gauntlet_init_parser.add_argument("--runtime", choices=("claude", "codex"), required=True)
    for command in ("gauntlet-status", "gauntlet-run", "gauntlet-cleanup"):
        control_parser = subparsers.add_parser(command)
        control_parser.add_argument("root")
        control_parser.add_argument("--work-id", required=True)
        if command == "gauntlet-status":
            control_parser.add_argument("--run-id")
        else:
            control_parser.add_argument("--session-ref")
        if command == "gauntlet-cleanup":
            # The handler distinguishes adopted selectors from the legacy pair.
            control_parser.add_argument("--run-id")
            control_parser.add_argument("--worker-id")
            control_parser.add_argument("--activity-id")
            control_parser.add_argument("--context-id")
            control_parser.add_argument("--epoch", type=int)
    prepare_worker_parser = subparsers.add_parser("gauntlet-prepare-worker")
    prepare_worker_parser.add_argument("root")
    prepare_worker_parser.add_argument("--work-id", required=True)
    prepare_worker_parser.add_argument("--run-id", required=True)
    prepare_worker_parser.add_argument("--worker-id", required=True)
    prepare_worker_parser.add_argument("--scope", action="append", required=True)
    prepare_worker_parser.add_argument("--session-ref")
    partition_emit_parser = subparsers.add_parser("partition-emit")
    partition_emit_parser.add_argument("root")
    partition_emit_parser.add_argument("--work-id", required=True)
    partition_emit_parser.add_argument("--feature", required=True)
    partition_emit_parser.add_argument("--groups", type=int, default=None)
    partition_emit_parser.add_argument("--apply", action="store_true")
    partition_emit_parser.add_argument("--session-ref")
    partition_brief_parser = subparsers.add_parser("gauntlet-partition-brief")
    partition_brief_parser.add_argument("root")
    partition_brief_parser.add_argument("--dag", required=True)
    partition_brief_parser.add_argument("--report", required=True)
    partition_brief_parser.add_argument("--node-id", required=True)
    tasks_import_parser = subparsers.add_parser("gauntlet-tasks-import")
    tasks_import_parser.add_argument("root")
    tasks_import_parser.add_argument("--work-id", required=True)
    tasks_import_parser.add_argument("--run-id", required=True)
    tasks_import_parser.add_argument("--dag", required=True)
    tasks_import_parser.add_argument("--source-task", action="append", required=True, metavar="TASK=RUN")
    tasks_import_parser.add_argument("--apply", action="store_true")
    tasks_import_parser.add_argument("--expected-sha256")
    tasks_import_parser.add_argument("--session-ref")
    tasks_rebase_parser = subparsers.add_parser("gauntlet-tasks-rebase")
    tasks_rebase_parser.add_argument("root")
    tasks_rebase_parser.add_argument("--work-id", required=True)
    tasks_rebase_parser.add_argument("--run-id", required=True)
    tasks_rebase_parser.add_argument("--dag", required=True)
    tasks_rebase_parser.add_argument("--source-run-id", required=True)
    tasks_rebase_parser.add_argument("--source-dag", required=True)
    tasks_rebase_parser.add_argument("--source-commit", required=True)
    tasks_rebase_parser.add_argument("--task", action="append", required=True)
    tasks_rebase_parser.add_argument("--apply", action="store_true")
    tasks_rebase_parser.add_argument("--expected-sha256")
    tasks_rebase_parser.add_argument("--session-ref")
    tasks_reconcile_parser = subparsers.add_parser("gauntlet-tasks-reconcile")
    tasks_reconcile_parser.add_argument("root")
    tasks_reconcile_parser.add_argument("--work-id", required=True)
    tasks_reconcile_parser.add_argument("--dag", required=True)
    tasks_reconcile_parser.add_argument("--run-id")
    tasks_reconcile_parser.add_argument("--apply", action="store_true")
    tasks_reconcile_parser.add_argument("--session-ref")
    task_files_migrate_parser = subparsers.add_parser("task-files-migrate")
    task_files_migrate_parser.add_argument("root")
    task_files_migrate_parser.add_argument("--work-id", required=True)
    task_files_migrate_parser.add_argument("--feature", required=True)
    task_files_migrate_parser.add_argument("--proposal", required=True)
    task_files_migrate_parser.add_argument("--context-id")
    task_files_migrate_parser.add_argument("--epoch", type=int)
    task_files_migrate_parser.add_argument("--session-ref")
    task_files_migrate_parser.add_argument("--author-activity")
    task_files_migrate_parser.add_argument("--review-activity")
    task_files_migrate_parser.add_argument("--expected-sha256")
    task_files_migrate_parser.add_argument("--expected-proposal-sha256")
    task_files_migrate_parser.add_argument("--apply", action="store_true")
    dag_validate_parser = subparsers.add_parser("gauntlet-dag-validate")
    dag_validate_parser.add_argument("root")
    dag_validate_parser.add_argument("--work-id", required=True)
    dag_validate_parser.add_argument("--run-id", required=True)
    dag_validate_parser.add_argument("--dag", required=True)
    wave_declare_parser = subparsers.add_parser("gauntlet-wave-declare")
    wave_declare_parser.add_argument("root")
    wave_declare_parser.add_argument("--work-id", required=True)
    wave_declare_parser.add_argument("--run-id", required=True)
    wave_declare_parser.add_argument("--dag", required=True)
    wave_declare_parser.add_argument("--node-id", action="append", required=True)
    wave_declare_parser.add_argument("--session-ref")
    converge_parser = subparsers.add_parser("gauntlet-converge")
    converge_parser.add_argument("root")
    converge_parser.add_argument("--work-id", required=True)
    converge_parser.add_argument("--run-id", required=True)
    converge_parser.add_argument("--dag", required=True)
    converge_parser.add_argument("--wave-id", required=True)
    converge_parser.add_argument("--session-ref")
    run_abandon_parser = subparsers.add_parser("gauntlet-run-abandon")
    run_abandon_parser.add_argument("root")
    run_abandon_parser.add_argument("--work-id", required=True)
    run_abandon_parser.add_argument("--run-id", required=True)
    run_abandon_parser.add_argument("--attestation", required=True)
    run_abandon_parser.add_argument("--session-ref")
    worker_declare_parser = subparsers.add_parser("gauntlet-worker-declare")
    worker_declare_parser.add_argument("root")
    worker_declare_parser.add_argument("--work-id", required=True)
    worker_declare_parser.add_argument("--run-id", required=True)
    worker_declare_parser.add_argument("--wave-id", required=True)
    worker_declare_parser.add_argument("--node-id", required=True)
    worker_declare_parser.add_argument("--tier", required=True)
    worker_declare_parser.add_argument("--files", action="append", required=True)
    worker_declare_parser.add_argument("--dag", required=True)
    worker_declare_parser.add_argument("--session-ref")
    progress_record_parser = subparsers.add_parser("gauntlet-progress-record")
    progress_record_parser.add_argument("root")
    progress_record_parser.add_argument("--work-id", required=True)
    progress_record_parser.add_argument("--run-id", required=True)
    progress_record_parser.add_argument("--worker-id", required=True)
    progress_record_parser.add_argument("--session-ref")
    worker_terminal_parser = subparsers.add_parser("gauntlet-worker-terminal")
    worker_terminal_parser.add_argument("root")
    worker_terminal_parser.add_argument("--work-id", required=True)
    worker_terminal_parser.add_argument("--run-id", required=True)
    worker_terminal_parser.add_argument("--worker-id", required=True)
    worker_terminal_parser.add_argument("--outcome", choices=("completed", "failed"), required=True)
    worker_terminal_parser.add_argument("--failure-class", choices=("process-timeout", "transport-failure"))
    worker_terminal_parser.add_argument("--session-ref")
    worker_session_parser = subparsers.add_parser("gauntlet-worker-session")
    worker_session_parser.add_argument("root")
    worker_session_parser.add_argument("--work-id", required=True)
    worker_session_parser.add_argument("--run-id", required=True)
    worker_session_parser.add_argument("--worker-id", required=True)
    worker_session_parser.add_argument("--dispatch", required=True)
    worker_session_parser.add_argument("--phase", choices=("register", "release"), required=True)
    worker_session_parser.add_argument("--result")
    worker_session_parser.add_argument("--session-ref")
    remediate_parser = subparsers.add_parser("gauntlet-remediate")
    remediate_parser.add_argument("root")
    remediate_parser.add_argument("--work-id", required=True)
    remediate_parser.add_argument("--run-id", required=True)
    remediate_parser.add_argument("--worker-id", required=True)
    remediate_parser.add_argument("--reason", choices=("stall", "transient-failure"), required=True)
    remediate_parser.add_argument("--session-ref")
    gauntlet_resume_parser = subparsers.add_parser("gauntlet-resume")
    gauntlet_resume_parser.add_argument("root")
    gauntlet_resume_parser.add_argument("--work-id", required=True)
    gauntlet_resume_parser.add_argument("--run-id")
    gauntlet_resume_parser.add_argument("--session-ref")
    gauntlet_resume_parser.add_argument("--runtime", choices=("claude", "codex"))
    gauntlet_resume_parser.add_argument("--checkpoint")
    gauntlet_resume_parser.add_argument("--apply", action="store_true")
    gauntlet_resume_parser.add_argument("--expected-sha256")
    prepare_switch_parser = subparsers.add_parser("gauntlet-prepare-switch")
    prepare_switch_parser.add_argument("root")
    prepare_switch_parser.add_argument("--work-id", required=True)
    prepare_switch_parser.add_argument("--context-id", required=True)
    prepare_switch_parser.add_argument("--epoch", type=int, required=True)
    prepare_switch_parser.add_argument("--session-ref", required=True)
    prepare_switch_parser.add_argument("--to-runtime", choices=("claude", "codex"), required=True)
    prepare_switch_parser.add_argument("--released-source", action="store_true")
    context_takeover_parser = subparsers.add_parser("gauntlet-context-takeover")
    context_takeover_parser.add_argument("root")
    context_takeover_parser.add_argument("--work-id", required=True)
    context_takeover_parser.add_argument("--session-ref", required=True)
    context_takeover_parser.add_argument("--expected-sha256")
    context_takeover_parser.add_argument("--apply", action="store_true")
    activity_fence_parser = subparsers.add_parser("gauntlet-activity-fence")
    activity_fence_parser.add_argument("root")
    activity_fence_parser.add_argument("--work-id", required=True)
    activity_fence_parser.add_argument("--activity-id", required=True)
    activity_fence_parser.add_argument("--session-ref", required=True)
    activity_fence_parser.add_argument("--authorization", default=None)
    activity_fence_parser.add_argument("--expected-sha256")
    activity_fence_parser.add_argument("--apply", action="store_true")
    attest_parser = subparsers.add_parser("attest")
    attest_parser.add_argument("root")
    attest_parser.add_argument("--work-id", required=True)
    attest_parser.add_argument("--step")
    attest_parser.add_argument("--rechain", action="store_true",
                               help="mint successors for every chain_stale step, in order, under --out")
    attest_parser.add_argument("--artifact",
                               help="project-relative path to the artefact the step produced")
    attest_parser.add_argument("--out", required=True,
                               help="project-relative path to write the attestation bundle to")
    attest_parser.add_argument("--run-id", default=None)
    attest_parser.add_argument("--runtime", choices=("claude", "codex"), default=None)
    attest_parser.add_argument("--session-ref")
    attest_parser.add_argument("--supersedes", default=None,
                               help="project-relative path to the accepted bundle this one replaces")
    attest_parser.add_argument("--authorization", default=None,
                               help="project-relative path to the human-authorization/v1 document (required by ship)")

    advance_parser = subparsers.add_parser("advance")
    advance_parser.add_argument("root")
    advance_parser.add_argument("--work-id", required=True)
    advance_parser.add_argument("--session-ref", required=True)
    advance_parser.add_argument("--attestation")
    advance_parser.add_argument("--evidence", action="append", default=[])
    advance_parser.add_argument("--frontend", action="store_true")

    checkpoint_parser = subparsers.add_parser("checkpoint")
    checkpoint_parser.add_argument("root")
    checkpoint_parser.add_argument("--work-id", required=True)
    checkpoint_parser.add_argument("--step", required=True)
    checkpoint_parser.add_argument("--state", choices=("in-progress", "complete", "blocked"), required=True)
    checkpoint_parser.add_argument("--evidence", action="append", default=[])
    checkpoint_parser.add_argument("--attestation")
    checkpoint_parser.add_argument("--supersedes-attestation", default=None,
                                   help="accept a successor chain for a step already complete")
    checkpoint_parser.add_argument("--reason", default="")
    checkpoint_parser.add_argument("--initialize-legacy", action="store_true")
    checkpoint_parser.add_argument("--from-step")
    checkpoint_parser.add_argument("--operation-id")
    checkpoint_parser.add_argument("--session-ref")
    phase_turn_parser = subparsers.add_parser("phase-turn")
    phase_turn_parser.add_argument("root")
    phase_turn_parser.add_argument("--work-id", required=True)
    phase_turn_parser.add_argument("--session-ref")
    # A razão é exigida pela lógica, não pelo parser: assim a falta sai como
    # REASON-REQUIRED, um código nomeado, em vez de erro de uso do argparse.
    phase_turn_parser.add_argument("--reason", default="")
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("root")
    status_parser.add_argument("--work-id")
    status_parser.add_argument("--current-worktree", action="store_true")
    status_parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser


def diagnostic_path(value: object) -> str:
    """Return a JSON-safe path while preserving undecodable bytes visibly."""
    if isinstance(value, bytes):
        return value.decode(sys.getfilesystemencoding(), errors="backslashreplace")
    return str(value)


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.command == "status" and args.format == "markdown":
            return status_markdown_command(args)
        handlers = {
            "init": init_command,
            "audit": audit_command,
            "constitution-reseal": constitution_reseal_command,
            "reconcile": reconcile_command,
            "migrate": migrate_command,
            "migrate-v3": migrate_v3_command,
            "migrate-v4": migrate_v4_command,
            "gauntlet-orchestration-adopt": orchestration_adopt_command,
            "gauntlet-step-enter": gauntlet_step_enter_command,
            "gauntlet-preview": gauntlet_preview_command,
            "gauntlet-preview-decide": gauntlet_preview_decide_command,
            "gauntlet-activity": gauntlet_activity_command,
            "gauntlet-init": gauntlet_init_command,
            "gauntlet-status": gauntlet_status_command,
            "gauntlet-run": gauntlet_run_command,
            "gauntlet-resume": gauntlet_resume_command,
            "gauntlet-prepare-switch": gauntlet_prepare_switch_command,
            "gauntlet-context-takeover": gauntlet_context_takeover_command,
            "gauntlet-activity-fence": gauntlet_activity_fence_command,
            "gauntlet-prepare-worker": gauntlet_prepare_worker_command,
            "gauntlet-cleanup": gauntlet_cleanup_command,
            "partition-emit": partition_emit_command,
            "gauntlet-partition-brief": gauntlet_partition_brief_command,
            "gauntlet-tasks-reconcile": gauntlet_tasks_reconcile_command,
            "gauntlet-tasks-import": gauntlet_tasks_import_command,
            "gauntlet-tasks-rebase": gauntlet_tasks_rebase_command,
            "task-files-migrate": task_files_migrate_command,
            "gauntlet-dag-validate": gauntlet_dag_validate_command,
            "gauntlet-wave-declare": gauntlet_wave_declare_command,
            "gauntlet-converge": gauntlet_converge_command,
            "gauntlet-run-abandon": gauntlet_run_abandon_command,
            "gauntlet-worker-declare": gauntlet_worker_declare_command,
            "gauntlet-progress-record": gauntlet_progress_record_command,
            "gauntlet-worker-terminal": gauntlet_worker_terminal_command,
            "gauntlet-worker-session": gauntlet_worker_session_command,
            "gauntlet-remediate": gauntlet_remediate_command,
            "hotfix": hotfix_command,
            "hotfix-go": hotfix_go_command,
            "attest": attest_command,
            "checkpoint": checkpoint_command,
            "advance": advance_command,
            "phase-turn": phase_turn_command,
            "status": status_command,
            "preflight": preflight_command,
            "triage": triage_command,
            "decide": decide_command,
            "decide-label": decide_label_command,
            "backlog-sync": backlog_sync_command,
            "backlog-adopt": backlog_adopt_command,
            "backlog-project": backlog_project_command,
            "backlog-verify": backlog_verify_command,
            "backlog-migrate": backlog_migrate_command,
        }
        payload, exit_code = handlers[args.command](args)
    except CliFailure as failure:
        payload, exit_code = failure.payload(), failure.exit_code
    except OSError as exc:
        payload = {"verdict": "BLOCKED", "code": "FILESYSTEM", "error": str(exc)}
        if exc.errno is not None:
            payload["errno"] = exc.errno
        if exc.filename is not None:
            payload["path"] = diagnostic_path(exc.filename)
        if exc.filename2 is not None:
            payload["path2"] = diagnostic_path(exc.filename2)
        exit_code = EXIT_BLOCKED
    except (ImportError, SyntaxError) as exc:
        # §5.7 / 22 Core: exactly one JSON document on stdout, always -- even
        # when grill_core_module()'s exec_module() hits a syntactically broken
        # or unloadable grill_core/*.py sibling. Previously unhandled: the CLI
        # exited 1 with empty stdout and a raw traceback on stderr, which is
        # itself an out-of-contract exit code (1 means NO-GO here, not an
        # interpreter-level failure) as well as a broken stdout contract.
        payload = {"verdict": "BLOCKED", "code": "GRILL-CORE-UNAVAILABLE", "error": type(exc).__name__, "detail": str(exc)}
        exit_code = EXIT_BLOCKED
    except (UnicodeError, json.JSONDecodeError) as exc:
        payload = {"verdict": "BLOCKED", "code": "UNEXPECTED-INPUT", "error": type(exc).__name__}
        exit_code = EXIT_BLOCKED
    except Exception as exc:
        # Public commands are protocol boundaries: unexpected core failures
        # cannot turn into a traceback/exit 1 after having emitted no JSON.
        payload = {"verdict": "BLOCKED", "code": "UNEXPECTED-FAILURE", "error": type(exc).__name__}
        exit_code = EXIT_BLOCKED
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
