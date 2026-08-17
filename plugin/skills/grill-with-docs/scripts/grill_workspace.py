#!/usr/bin/env python3
"""Deterministic isolated work-item lifecycle for grill-with-docs v2 (stdlib only)."""
from __future__ import annotations

import argparse
import contextlib
import errno
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
from datetime import date
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


def state_template(root: Path, work_id: str, constitution: dict[str, Any], workflow: dict[str, Any]) -> bytes:
    value = json.loads((ASSETS / "state.template.json").read_text(encoding="utf-8"))
    value["work_id"] = work_id
    value["constitution"] = constitution
    value["workflow"] = {**workflow, "version": "v2"}
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def initial_files(root: Path, work_id: str, immutable: dict[str, Any], *,
                  backlog_skipped: bool = False) -> dict[str, bytes]:
    _, _, clauses = constitution_info(root)
    files = {name: read_asset(name) for name in ROOT_FILES if name not in {"state.json", "CONSTITUTION-CHECK.md"}}
    files["state.json"] = state_template(root, work_id, immutable["constitution"], immutable["workflow"])
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


def dependency_report(root: Path, *, allow_install: bool) -> dict[str, Any]:
    """Detect the external toolchain; install only when explicitly authorised."""
    dependencies = sibling("ensure_dependencies")
    try:
        return dependencies.preflight(root, allow_install=allow_install)
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


def preflight_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Report and optionally repair the environment without creating a work item."""
    root = project_root(args.root)
    payload = {
        "schema": "grill-preflight/v1",
        "workflow": ensure_project_workflow(root),
        "dependencies": dependency_report(root, allow_install=args.allow_install),
    }
    if not args.skip_backlog:
        payload["backlog"] = backlog_report(root, apply=args.allow_install, db=getattr(args, "db", None))
    payload["verdict"] = payload["dependencies"].get("verdict", "BLOCKED")
    return payload, EXIT_OK if payload["verdict"] == "OK" else EXIT_BLOCKED


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
    """Mirror the open BLs of one work item into the bound backlog, preview-first."""
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


def init_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if args.type not in KINDS or not SLUG_RE.fullmatch(args.slug):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-IDENTITY", "type or slug invalid")
    work_id = args.work_id or f"{args.type}-{args.slug}-{uuid.uuid4().hex}"
    if not WORK_ID_RE.fullmatch(work_id):
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-WORK-ID", work_id)
    workflow = ensure_project_workflow(root)
    dependencies = dependency_report(root, allow_install=getattr(args, "allow_install", False))
    if getattr(args, "require_dependencies", False) and dependencies.get("verdict") != "OK":
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "MISSING-DEPENDENCY",
                         ",".join(dependencies.get("missing_required") or ["unknown"]))
    environment = {"workflow": workflow, "dependencies": dependencies}
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
            bundle = read_local_bundle(root, target)
            immutable = validate_metadata(bundle.metadata, work_id)
            if immutable.get("type") != args.type or immutable.get("slug") != args.slug:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "IDENTITY-DIVERGENCE", work_id)
            return {"status": "REUSED", "work_id": work_id, "path": str(target), "fingerprint": bundle.fingerprint, **environment}, EXIT_OK
        constitution_created, constitution_hash = ensure_managed_constitution(root)
        immutable = immutable_metadata(root, args, work_id)
        files = initial_files(root, work_id, immutable, backlog_skipped=skipped_backlog)
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
            return {"status": "REUSED", "work_id": work_id, "path": str(target), "fingerprint": bundle.fingerprint, **environment}, EXIT_OK
        bundle = read_local_bundle(root, target)
        return {"status": "CREATED", "work_id": work_id, "path": str(target), "fingerprint": bundle.fingerprint,
                "constitution": "CREATED" if constitution_created else "PRESERVED", "constitution_sha256": constitution_hash,
                "backlog_skipped": skipped_backlog,
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
        for prior_id, receipt in sorted(existing.items()):
            if prior_id == args.work_id:
                continue
            for left in scope:
                for right in receipt.get("scope", []):
                    if isinstance(right, str) and scopes_overlap(left, right):
                        conflicts.append(f"SCOPE-OVERLAP:{args.work_id}:{left}<->{prior_id}:{right}")
            for reference in target.metadata.get("conflicts-with-adrs", []):
                if isinstance(reference, str) and reference in receipt.get("qualified_ids", []):
                    conflicts.append(f"ADR-CONFLICT:{args.work_id}->{reference}")
        dependencies = target.metadata.get("depends-on-work", [])
        if not isinstance(dependencies, list) or not all(isinstance(value, str) for value in dependencies):
            conflicts.append(f"DEPENDENCY-SCHEMA:{args.work_id}")
        else:
            for dependency in sorted(set(dependencies)):
                if dependency == args.work_id:
                    conflicts.append(f"DEPENDENCY-SELF:{args.work_id}")
                elif dependency not in existing:
                    conflicts.append(f"DEPENDENCY-NOT-RECONCILED:{args.work_id}->{dependency}")
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


SEQUENCE = ["specify", "plan", "checklist", "tasks", "analyze", "agent-assign", "agent-execute", "converge", "verify", "review", "ship"]


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
        workflow_v3 = grill_core_module("workflow_v3")
        try:
            _, workflow_bytes, workflow_text = workflow_v3.load_workflow(root)
            gate = workflow_v3.execution_gate(workflow_text)
        except workflow_v3.Failure as error:
            code = workflow_v3.CLI_CODE_ALIASES.get(error.code, error.code.replace("_", "-"))
            raise CliFailure(
                error.exit_code,
                error.verdict,
                code,
                error.message,
                extra=dict(error.extra) if error.extra else None,
            ) from error
        if gate.status != "OK":
            code = workflow_v3.CLI_CODE_ALIASES.get(gate.code or "WORKFLOW_INCOMPATIBLE", (gate.code or "WORKFLOW_INCOMPATIBLE").replace("_", "-"))
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
                        _, workflow_bytes, workflow_text = workflow_v3.load_workflow(root)
                        gate = workflow_v3.execution_gate(workflow_text)
                    except workflow_v3.Failure as error:
                        code = workflow_v3.CLI_CODE_ALIASES.get(error.code, error.code.replace("_", "-"))
                        raise CliFailure(
                            error.exit_code,
                            error.verdict,
                            code,
                            error.message,
                            extra=dict(error.extra) if error.extra else None,
                        ) from error
                    if gate.status != "OK":
                        code = workflow_v3.CLI_CODE_ALIASES.get(
                            gate.code or "WORKFLOW_INCOMPATIBLE",
                            (gate.code or "WORKFLOW_INCOMPATIBLE").replace("_", "-"),
                        )
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


def gauntlet_init_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Explicitly activate one verified V3 work item for the FASE-001 Gauntlet."""
    root = project_root(args.root)
    resolve_development_item(root, args.work_id)
    gauntlet = grill_core_module("gauntlet")
    workflow_v3 = grill_core_module("workflow_v3")
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
                _, workflow_bytes, workflow_text = workflow_v3.load_workflow(root)
            except workflow_v3.Failure as error:
                code = workflow_v3.CLI_CODE_ALIASES.get(error.code, error.code.replace("_", "-"))
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
                workflow_v3=workflow_v3,
                work_item_v3=work_item_v3,
                step_skills=step_skills,
            )
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        return {
            "verdict": verdict,
            "work_id": args.work_id,
            "config": ".grill/gauntlet.yaml",
            "max_workers": args.max_workers,
            "stall_minutes": 15,
            "runtime": "claude",
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
    workflow_v3 = grill_core_module("workflow_v3")
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
            _, workflow_bytes, workflow_text = workflow_v3.load_workflow(root)
        except workflow_v3.Failure as error:
            code = workflow_v3.CLI_CODE_ALIASES.get(error.code, error.code.replace("_", "-"))
            return root, "BLOCKED", code
        try:
            state, reason = gauntlet.activation_state(
                root=root,
                work_id=args.work_id,
                item_dir_fd=item_fd,
                grill_fd=grill_fd,
                workflow_bytes=workflow_bytes,
                workflow_text=workflow_text,
                workflow_v3=workflow_v3,
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
    workflow_v3 = grill_core_module("workflow_v3")
    work_item_v3 = grill_core_module("work_item_v3")
    step_skills = grill_core_module("step_skills")
    gauntlet_runs = grill_core_module("gauntlet_runs")
    item_fd: int | None = None
    grill_fd: int | None = None
    try:
        item_fd = open_development_item_fd(root, args.work_id)
        grill_fd = gauntlet.open_config_directory(root)
        try:
            _, workflow_bytes, workflow_text = workflow_v3.load_workflow(root)
        except workflow_v3.Failure as error:
            code = workflow_v3.CLI_CODE_ALIASES.get(error.code, error.code.replace("_", "-"))
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message) from error
        try:
            state, reason = gauntlet.activation_state(
                root=root, work_id=args.work_id, item_dir_fd=item_fd, grill_fd=grill_fd,
                workflow_bytes=workflow_bytes, workflow_text=workflow_text,
                workflow_v3=workflow_v3, work_item_v3=work_item_v3, step_skills=step_skills,
            )
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        if state != "ACTIVATED":
            code = "ACTIVATION-REQUIRED" if state == "ELIGIBLE" else (reason or "ACTIVATION-REQUIRED")
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, "a current Gauntlet activation is required", extra={"work_id": args.work_id})
        try:
            proof = gauntlet.current_activation(
                root=root, work_id=args.work_id, item_dir_fd=item_fd, workflow_bytes=workflow_bytes,
                workflow_text=workflow_text, workflow_v3=workflow_v3,
                work_item_v3=work_item_v3, step_skills=step_skills,
            )
            config, config_bytes, _ = gauntlet._read_config(grill_fd)
        except gauntlet.GauntletError as error:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", error.code, error.message, extra=error.extra or None) from error
        record = config["activations"].get(args.work_id)
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


def gauntlet_run_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root, gauntlet_runs, admission, _record = gauntlet_run_admission(args)
    try:
        return gauntlet_runs.admit_or_reuse_run(root, args.work_id, admission), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code) if isinstance(error, gauntlet_runs.store.StoreError) else error.code
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


def gauntlet_resume_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    # Retain the FASE-001 control boundary for callers that did not select a
    # durable run.  FASE-002 recovery is deliberately opt-in via --run-id.
    if args.run_id is None:
        _, state, _ = gauntlet_activation_projection(args)
        if state != "ACTIVATED":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ACTIVATION-REQUIRED", "a current Gauntlet activation is required", extra={"work_id": args.work_id})
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SCHEDULING-NOT-AVAILABLE", "durable recovery requires --run-id", extra={"work_id": args.work_id})
    root, gauntlet_runs, admission, _record = gauntlet_run_admission(args)
    try:
        return gauntlet_runs.record_resume_decision(root, args.work_id, args.run_id, admission), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code) if isinstance(error, gauntlet_runs.store.StoreError) else error.code
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


def gauntlet_cleanup_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    # Retain the FASE-001 control response for the legacy form.  The durable
    # worker lifecycle is selected only by the complete run/worker pair, so
    # an older caller cannot accidentally target a workspace.
    if args.run_id is None and args.worker_id is None:
        root = project_root(args.root)
        resolve_gauntlet_subject(root, args.work_id)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "SCHEDULING-NOT-AVAILABLE", "cleanup is unavailable before durable scheduling", extra={"work_id": args.work_id})
    if args.run_id is None or args.worker_id is None:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-ARGUMENTS", "--run-id and --worker-id must be supplied together", extra={"work_id": args.work_id})
    root, gauntlet_runs, admission, _record = gauntlet_run_admission(args)
    try:
        result = gauntlet_runs.cleanup_worker(root, args.work_id, args.run_id, args.worker_id, admission)
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error
    # PRESERVED is a deliberate, non-mutating safety result rather than a
    # core error; preserve its diagnostic verdict but make it a blocked CLI
    # outcome so automation cannot mistake preservation for cleanup.
    return result, EXIT_OK if result.get("verdict") in {"CLEANED", "REUSED"} else EXIT_BLOCKED


def gauntlet_prepare_worker_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Prepare one passive, scoped worker workspace from a fresh admission."""
    root, gauntlet_runs, admission, _record = gauntlet_run_admission(args)
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


def _tier_floors(record: dict[str, Any]) -> tuple[str, str]:
    """FR-002 SSOT: resolve both tier floors from the caller's own current
    activation-pinned tier policy -- never a literal duplicated in
    ``grill_core``, so a future policy change can't silently desync from
    this enforcement point."""
    tier_policy = record["tier_policy"]
    return tier_policy["minimum_by_step"]["agent-execute"], tier_policy["supplemental"]["markdown-maintenance"]


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


def gauntlet_wave_declare_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-003 (FR-004/FR-005, ADR-0013): declare the run's next Execution Wave."""
    root, gauntlet_runs, admission, record = gauntlet_run_admission(args)
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


def gauntlet_worker_declare_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-003 (FR-007): mint one first-dispatch worker, ``worker_id = node_id``."""
    root, gauntlet_runs, admission, record = gauntlet_run_admission(args)
    agent_execute_floor, markdown_floor = _tier_floors(record)
    try:
        return gauntlet_runs.declare_worker(
            root, args.work_id, args.run_id, args.node_id, args.wave_id, args.tier, args.files, args.dag, admission,
            agent_execute_floor=agent_execute_floor, markdown_floor=markdown_floor,
        ), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


def gauntlet_progress_record_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """FASE-003 (FR-008(d)): renew one worker's lease past its original window."""
    root, gauntlet_runs, admission, _record = gauntlet_run_admission(args)
    try:
        return gauntlet_runs.record_progress(root, args.work_id, args.run_id, args.worker_id, admission), EXIT_OK
    except (gauntlet_runs.GauntletRunError, gauntlet_runs.store.StoreError) as error:
        code = (gauntlet_runs.store.KEBAB_ALIASES.get(error.code, error.code)
                if isinstance(error, gauntlet_runs.store.StoreError) else error.code)
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", code, error.message, extra={"work_id": args.work_id}) from error


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


def v3_checkpoint_attestation_required(root: Path) -> bool:
    """Return whether the materialised workflow activates the v3 receipt gate.

    V2 work items retain their byte-compatible lifecycle.  A v3 marker (or a
    human-equivalent v3 frontier) is different: an incompatible document is a
    block, never a quiet downgrade to the unauthenticated v2 checkpoint path.
    """
    workflow_v3 = grill_core_module("workflow_v3")
    workflow_path = root / "WORKFLOW.md"
    try:
        text = safe_read(workflow_path, root=root, utf8=True)
        v3_declared = workflow_v3.compatible_v3(text) or workflow_v3.marker_version(text) == "v3"
        if not v3_declared:
            return False
        gate = workflow_v3.execution_gate(text)
    except workflow_v3.Failure as exc:
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
        index = SEQUENCE.index(step_id)
        outputs = development.get("attested_outputs", {})
        if not isinstance(outputs, dict):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ATTESTATION-STATE-DIVERGENCE", work_id)
        if index:
            previous = outputs.get(SEQUENCE[index - 1])
            if not isinstance(previous, dict):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "ATTESTATION-PREDECESSOR-MISSING", SEQUENCE[index - 1])
        verdict = attestation.judge_checkpoint_attestation(
            bundle,
            project_id=project_id,
            work_item_id=work_id,
            step_id=step_id,
            campaign=development.get("attestation_campaign"),
            predecessor_output=previous,
        )
    except CliFailure:
        raise
    except attestation.AttestationError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", translate_v3_code(exc.code), exc.reason) from exc
    except store.StoreError as exc:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", translate_v3_code(exc.code), exc.message) from exc
    return {"path": attestation_path, **verdict}


def checkpoint_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    root = project_root(args.root)
    if args.step not in SEQUENCE:
        raise CliFailure(EXIT_BLOCKED, "BLOCKED", "INVALID-STEP", args.step)
    item = resolve_development_item(root, args.work_id)
    snapshot_global = global_snapshotter(root)
    global_before = snapshot_global()
    lock = acquire_lock(root, args.work_id, item)
    try:
        path, state = read_development_state(root, item, args.work_id)
        development = state.get("development")
        if not isinstance(development, dict) or development.get("schema") != "grill-development/v1":
            if not args.initialize_legacy:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-UNTRACKED", args.work_id)
            if args.from_step is not None and (args.from_step != "specify" or args.step != "specify"):
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-INITIALIZATION-UNSAFE", args.work_id)
            if args.from_step is None or not args.evidence or not args.reason.strip():
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-INITIALIZATION-REQUIRES-DECISION-EVIDENCE", args.work_id)
            development = {"schema":"grill-development/v1", "sequence":SEQUENCE[:], "current_step":args.step,
                           "steps":{step:"pending" for step in SEQUENCE}, "audit":[]}
            state["development"] = development
            args.state = "in-progress"
        sequence = development.get("sequence"); steps = development.get("steps")
        # A trilha entra na validação de forma junto com o resto: ausente é
        # legítimo e vira lista, mas presente e de outro tipo derrubava o comando
        # com AttributeError no append lá embaixo — traceback onde devia haver
        # código nomeado.
        if sequence != SEQUENCE or not isinstance(steps, dict) or not isinstance(development.setdefault("audit", []), list):
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DEVELOPMENT-SCHEMA", args.work_id)
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
        if current == args.state:
            if audit and audit[-1] == payload:
                return {"verdict":"REUSED", "work_id":args.work_id, **payload, "current_step":development.get("current_step")}, EXIT_OK
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "STATE-DIVERGENCE", args.step)
        index = sequence.index(args.step)
        attestation_result: dict[str, Any] | None = None
        if args.state == "in-progress":
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
            if args.step == "ship":
                require_converged_runs(root, args.work_id)
            if v3_checkpoint_attestation_required(root):
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
            outputs[args.step] = attestation_result["output"]
        development["current_step"] = next((s for s in sequence if steps.get(s) != "complete"), "complete")
        atomic_write(root, path, (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
        return {"verdict":"UPDATED", "work_id":args.work_id, **payload, "current_step":development["current_step"]}, EXIT_OK
    finally:
        shutil.rmtree(lock, ignore_errors=True)
        if snapshot_global() != global_before:
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "GLOBAL-MUTATION", args.work_id)



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
        if not isinstance(development, dict) or development.get("schema") != "grill-development/v1":
            raise CliFailure(EXIT_BLOCKED, "BLOCKED", "LEGACY-UNTRACKED", args.work_id)
        sequence = development.get("sequence")
        steps = development.get("steps")
        if sequence != SEQUENCE or not isinstance(steps, dict) or not isinstance(development.setdefault("audit", []), list):
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

        development["steps"] = {step: "pending" for step in sequence}
        development["current_step"] = sequence[0]
        previous_execution_branch = development.get("execution_branch", _MISSING)
        if previous_execution_branch is _MISSING or previous_execution_branch is None:
            previous_execution_branch = git_optional(root, "branch", "--show-current")
            if not previous_execution_branch:
                raise CliFailure(EXIT_BLOCKED, "BLOCKED", "DETACHED-HEAD", "phase turn requires an attached execution branch")
            run_git(root, "check-ref-format", "--branch", previous_execution_branch)
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


def status_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Public workspace entry point for the read-only status projection."""
    script = Path(__file__).with_name("grill_status.py")
    command = [sys.executable, str(script), str(args.root)]
    if args.work_id:
        command += ["--work-id", args.work_id]
    if args.current_worktree:
        command.append("--current-worktree")
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
    except subprocess.TimeoutExpired:
        return {"schema": "grill-status/v1", "verdict": "BLOCKED", "code": "STATUS-TIMEOUT", "next_action": "resolver-bloqueios"}, EXIT_BLOCKED
    try:
        payload = json.loads(process.stdout.strip())
    except json.JSONDecodeError:
        return {"schema": "grill-status/v1", "verdict": "BLOCKED", "code": "STATUS-INVALID-OUTPUT"}, EXIT_BLOCKED
    if not isinstance(payload, dict):
        return {"schema": "grill-status/v1", "verdict": "BLOCKED", "code": "STATUS-SCHEMA"}, EXIT_BLOCKED
    return payload, process.returncode if process.returncode in {0, 1, 2, 3} else EXIT_BLOCKED


def build_parser() -> JsonParser:
    parser = JsonParser()
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=JsonParser)
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("root")
    init_parser.add_argument("--type", required=True)
    init_parser.add_argument("--slug", required=True)
    init_parser.add_argument("--work-id")
    init_parser.add_argument("--base-ref")
    init_parser.add_argument("--allow-install", action="store_true", dest="allow_install")
    init_parser.add_argument("--require-dependencies", action="store_true", dest="require_dependencies")
    init_parser.add_argument("--skip-backlog", action="store_true", dest="skip_backlog")
    # Same reason backlog-sync needed it: without --db every run reaches the
    # operator's real store, so coverage would consult a different backlog on
    # CI than on a developer machine — and, worse, could write to it.
    init_parser.add_argument("--db")
    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("root")
    preflight_parser.add_argument("--allow-install", action="store_true", dest="allow_install")
    preflight_parser.add_argument("--skip-backlog", action="store_true", dest="skip_backlog")
    preflight_parser.add_argument("--db")
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
    gauntlet_init_parser = subparsers.add_parser("gauntlet-init")
    gauntlet_init_parser.add_argument("root")
    gauntlet_init_parser.add_argument("--work-id", required=True)
    gauntlet_init_parser.add_argument("--max-workers", type=int, required=True)
    for command in ("gauntlet-status", "gauntlet-run", "gauntlet-cleanup"):
        control_parser = subparsers.add_parser(command)
        control_parser.add_argument("root")
        control_parser.add_argument("--work-id", required=True)
        if command == "gauntlet-status":
            control_parser.add_argument("--run-id")
        elif command == "gauntlet-cleanup":
            # Optional individually for the legacy FASE-001 command; the
            # handler requires the pair before selecting durable cleanup.
            control_parser.add_argument("--run-id")
            control_parser.add_argument("--worker-id")
    prepare_worker_parser = subparsers.add_parser("gauntlet-prepare-worker")
    prepare_worker_parser.add_argument("root")
    prepare_worker_parser.add_argument("--work-id", required=True)
    prepare_worker_parser.add_argument("--run-id", required=True)
    prepare_worker_parser.add_argument("--worker-id", required=True)
    prepare_worker_parser.add_argument("--scope", action="append", required=True)
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
    converge_parser = subparsers.add_parser("gauntlet-converge")
    converge_parser.add_argument("root")
    converge_parser.add_argument("--work-id", required=True)
    converge_parser.add_argument("--run-id", required=True)
    converge_parser.add_argument("--dag", required=True)
    converge_parser.add_argument("--wave-id", required=True)
    run_abandon_parser = subparsers.add_parser("gauntlet-run-abandon")
    run_abandon_parser.add_argument("root")
    run_abandon_parser.add_argument("--work-id", required=True)
    run_abandon_parser.add_argument("--run-id", required=True)
    run_abandon_parser.add_argument("--attestation", required=True)
    worker_declare_parser = subparsers.add_parser("gauntlet-worker-declare")
    worker_declare_parser.add_argument("root")
    worker_declare_parser.add_argument("--work-id", required=True)
    worker_declare_parser.add_argument("--run-id", required=True)
    worker_declare_parser.add_argument("--wave-id", required=True)
    worker_declare_parser.add_argument("--node-id", required=True)
    worker_declare_parser.add_argument("--tier", required=True)
    worker_declare_parser.add_argument("--files", action="append", required=True)
    worker_declare_parser.add_argument("--dag", required=True)
    progress_record_parser = subparsers.add_parser("gauntlet-progress-record")
    progress_record_parser.add_argument("root")
    progress_record_parser.add_argument("--work-id", required=True)
    progress_record_parser.add_argument("--run-id", required=True)
    progress_record_parser.add_argument("--worker-id", required=True)
    worker_terminal_parser = subparsers.add_parser("gauntlet-worker-terminal")
    worker_terminal_parser.add_argument("root")
    worker_terminal_parser.add_argument("--work-id", required=True)
    worker_terminal_parser.add_argument("--run-id", required=True)
    worker_terminal_parser.add_argument("--worker-id", required=True)
    worker_terminal_parser.add_argument("--outcome", choices=("completed", "failed"), required=True)
    worker_terminal_parser.add_argument("--failure-class", choices=("process-timeout", "transport-failure"))
    remediate_parser = subparsers.add_parser("gauntlet-remediate")
    remediate_parser.add_argument("root")
    remediate_parser.add_argument("--work-id", required=True)
    remediate_parser.add_argument("--run-id", required=True)
    remediate_parser.add_argument("--worker-id", required=True)
    remediate_parser.add_argument("--reason", choices=("stall", "transient-failure"), required=True)
    gauntlet_resume_parser = subparsers.add_parser("gauntlet-resume")
    gauntlet_resume_parser.add_argument("root")
    gauntlet_resume_parser.add_argument("--work-id", required=True)
    gauntlet_resume_parser.add_argument("--run-id")
    checkpoint_parser = subparsers.add_parser("checkpoint")
    checkpoint_parser.add_argument("root")
    checkpoint_parser.add_argument("--work-id", required=True)
    checkpoint_parser.add_argument("--step", required=True)
    checkpoint_parser.add_argument("--state", choices=("in-progress", "complete", "blocked"), required=True)
    checkpoint_parser.add_argument("--evidence", action="append", default=[])
    checkpoint_parser.add_argument("--attestation")
    checkpoint_parser.add_argument("--reason", default="")
    checkpoint_parser.add_argument("--initialize-legacy", action="store_true")
    checkpoint_parser.add_argument("--from-step")
    phase_turn_parser = subparsers.add_parser("phase-turn")
    phase_turn_parser.add_argument("root")
    phase_turn_parser.add_argument("--work-id", required=True)
    # A razão é exigida pela lógica, não pelo parser: assim a falta sai como
    # REASON-REQUIRED, um código nomeado, em vez de erro de uso do argparse.
    phase_turn_parser.add_argument("--reason", default="")
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("root")
    status_parser.add_argument("--work-id")
    status_parser.add_argument("--current-worktree", action="store_true")
    return parser


def diagnostic_path(value: object) -> str:
    """Return a JSON-safe path while preserving undecodable bytes visibly."""
    if isinstance(value, bytes):
        return value.decode(sys.getfilesystemencoding(), errors="backslashreplace")
    return str(value)


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        handlers = {
            "init": init_command,
            "audit": audit_command,
            "reconcile": reconcile_command,
            "migrate": migrate_command,
            "migrate-v3": migrate_v3_command,
            "gauntlet-init": gauntlet_init_command,
            "gauntlet-status": gauntlet_status_command,
            "gauntlet-run": gauntlet_run_command,
            "gauntlet-resume": gauntlet_resume_command,
            "gauntlet-prepare-worker": gauntlet_prepare_worker_command,
            "gauntlet-cleanup": gauntlet_cleanup_command,
            "gauntlet-dag-validate": gauntlet_dag_validate_command,
            "gauntlet-wave-declare": gauntlet_wave_declare_command,
            "gauntlet-converge": gauntlet_converge_command,
            "gauntlet-run-abandon": gauntlet_run_abandon_command,
            "gauntlet-worker-declare": gauntlet_worker_declare_command,
            "gauntlet-progress-record": gauntlet_progress_record_command,
            "gauntlet-worker-terminal": gauntlet_worker_terminal_command,
            "gauntlet-remediate": gauntlet_remediate_command,
            "hotfix": hotfix_command,
            "hotfix-go": hotfix_go_command,
            "checkpoint": checkpoint_command,
            "phase-turn": phase_turn_command,
            "status": status_command,
            "preflight": preflight_command,
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
