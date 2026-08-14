#!/usr/bin/env python3
"""``grill-work-item/v3`` schema, dual-read v2/v3 and preview-first migration.

Plan clauses implemented here: 5.6 (minimal v3 extension), 5.2 (versioned
bundle vs. local/non-versioned state), 5.1 (hierarchical identity and
qualified ``<project-id>/<work-item-id>/<local-id>`` ids), phase 1 ("dual-read
de WORK-ITEM.json v2/v3; operacao que exigir v3 retorna erro nomeado com
comando de migracao"; ``STATE_DIVERGENCE`` fails closed), 22/Core (v2->v3
migration, qualified ids) and 23 (v2 bundles stay readable; the v3 migration
is explicit and preview-first).

The module is deliberately free of any *static* import from ``grill_workspace``:
the public CLI will later import *this* module, never the other way round.
``production_reader_accepts_v3`` loads ``grill_workspace.py`` dynamically, the
same way ``grill_workspace.py`` itself already loads its own siblings (see its
``grill_sibling_*`` loader) -- a read, never an edit, so it does not trip
LD-003, and there is still no static cycle.

Vocabulary (LD-002, revised in round 3): a code that describes a condition v2
already diagnosed keeps the live ``SCREAMING-KEBAB`` spelling exactly
(``METADATA-SCHEMA``, ``IMMUTABLE-TAMPERED``, ``WORK-ID-DIVERGENCE``,
``WORK-ITEM-MISSING``, ``WORK-ITEM-SYMLINK``, ``SYMLINK-REJECTED``,
``UNSAFE-FILE``, ``INVALID-UTF8``, ``UNEXPECTED-INPUT``, ``LOCK-CONTENTION``,
``FILESYSTEM``); a condition that exists only in the v3 world is
``SCREAMING_SNAKE`` (``INVALID_PARENT``, ``WORKTREE_PATH_FORBIDDEN``,
``WORKTREE_KEY_DIVERGENCE``, ``INVALID_ORCHESTRATION``, ``INVALID_SOURCE``,
``MIGRATION_DIVERGENCE``, ``STATE_DIVERGENCE``, ``WORK_ITEM_V3_REQUIRED``,
``V3_READERS_NOT_WIRED``, ``INVALID_QUALIFIED_ID``).
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_V2 = "grill-work-item/v2"
SCHEMA_V3 = "grill-work-item/v3"
SCHEMAS = (SCHEMA_V2, SCHEMA_V3)
ORCHESTRATION_SCHEMA = "grill-orchestrator/v1"
# grill_workspace.py now wires a real `migrate-v3` verb (peça E, LD-004 item
# 2 / LD-010 peça E): `migrate-v3 ROOT --work-id ID [--apply]` runs and exits
# 0. require_v3 below never hardcodes that fact -- LD-010 caught exactly this
# module claiming `migration_wired: False` as a constant even after the verb
# started working. It asks `production_cli_wires_migrate_v3()`, a live
# functional probe over the real, unmocked sibling module, the same way
# `production_reader_accepts_v3()` already probes the reader side.
# `MIGRATION_CAPABILITY` remains the fallback the payload names whenever that
# probe reports the CLI verb is not (yet) wired in whatever tree is running
# this code.
MIGRATION_CAPABILITY = "grill_core.work_item_v3.migrate_bundle"

HERE = Path(__file__).resolve()
SCRIPTS_DIR = HERE.parents[1]
GRILL_WORKSPACE_PATH = SCRIPTS_DIR / "grill_workspace.py"

EXIT_OK = 0
EXIT_NO_GO = 1
EXIT_BLOCKED = 2

KINDS = frozenset({"feature", "fix", "hotfix"})
WORK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,100}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
REQUEST_KEY_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,128}$")
LOCAL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")
# Any string shaped like a host-specific location: POSIX/UNC/drive-absolute,
# a single-backslash Windows drive-relative path, a `~`-relative home path or
# a URI with a scheme (file://, ...). Section 5.6 forbids all of these from
# entering the versioned bundle, not just the strict POSIX-absolute case.
ABSOLUTE_RE = re.compile(r"^(?:/|\\|[A-Za-z]:[\\/]|~|[A-Za-z][A-Za-z0-9+.-]*://)")

WORKTREE_KEY_PREFIX = "wt-"
SOURCE_FIELDS = ("kind", "request_key", "relation", "source_ref")
SOURCE_KINDS = frozenset({"backlog-request"})
SOURCE_RELATIONS = frozenset({"blocking", "non-blocking", "informational"})
# v2 fields that v3 must preserve verbatim; absence in either schema is fatal.
V2_IMMUTABLE_FIELDS = (
    "base_commit",
    "base_ref",
    "branch",
    "constitution",
    "head",
    "schema",
    "slug",
    "type",
    "work_id",
    "workflow",
)
V3_IMMUTABLE_FIELDS = ("parent_work_id", "source", "worktree_key")
# Keys that would smuggle a host-specific absolute worktree path into the
# versioned bundle. Section 5.6: only the logical key may be persisted.
# Checked everywhere in the document, not only under `immutable`.
FORBIDDEN_PATH_KEYS = frozenset(
    {"worktree_path", "worktree_root", "worktree_dir", "worktree_abspath", "worktree"}
)


@dataclass
class WorkItemError(Exception):
    """Structured failure with the same shape as ``grill_workspace.CliFailure``."""

    exit_code: int
    verdict: str
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {"verdict": self.verdict, "code": self.code, "error": self.message, **self.details}


def blocked(code: str, message: str, **details: Any) -> WorkItemError:
    return WorkItemError(EXIT_BLOCKED, "BLOCKED", code, message, details)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def immutable_sha256(immutable: Any) -> str:
    """Digest of the canonical immutable block; new v3 fields are covered by shape."""
    return hash_bytes(canonical(immutable))


def document_bytes(metadata: dict[str, Any]) -> bytes:
    """Serialize exactly like ``write_bundle_staging`` does for v2."""
    return (json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


# --------------------------------------------------------------------------
# 5.1 hierarchical identity
# --------------------------------------------------------------------------


def worktree_key_for(work_id: str) -> str:
    """Logical, host-independent worktree key. Never a filesystem path."""
    return f"{WORKTREE_KEY_PREFIX}{work_id}"


def _ensure_logical_key(key: Any, work_id: str) -> None:
    """Fail closed unless ``key`` is a bare logical token, never a path."""
    if (
        not isinstance(key, str)
        or not key
        or ABSOLUTE_RE.match(key)
        or "/" in key
        or "\\" in key
    ):
        raise blocked("WORKTREE_PATH_FORBIDDEN", "worktree_key must be a logical key, not a path", work_id=work_id)


def qualified_id(project_id: str, work_item_id: str, local_id: str) -> str:
    """Build ``<project-id>/<work-item-id>/<local-id>`` (section 5.1)."""
    if not isinstance(project_id, str) or not PROJECT_ID_RE.fullmatch(project_id):
        raise blocked("INVALID_QUALIFIED_ID", "project id invalid", segment="project_id")
    if not isinstance(work_item_id, str) or not WORK_ID_RE.fullmatch(work_item_id):
        raise blocked("INVALID_QUALIFIED_ID", "work item id invalid", segment="work_item_id")
    if not isinstance(local_id, str) or not LOCAL_ID_RE.fullmatch(local_id):
        raise blocked("INVALID_QUALIFIED_ID", "local id invalid", segment="local_id")
    return f"{project_id}/{work_item_id}/{local_id}"


def parse_qualified_id(value: Any) -> tuple[str, str, str]:
    """Inverse of :func:`qualified_id`; fail-closed on any other shape."""
    if not isinstance(value, str) or value.count("/") != 2:
        raise blocked("INVALID_QUALIFIED_ID", "qualified id must have exactly three segments")
    project_id, work_item_id, local_id = value.split("/")
    qualified_id(project_id, work_item_id, local_id)
    return project_id, work_item_id, local_id


# --------------------------------------------------------------------------
# validation (dual-read)
# --------------------------------------------------------------------------


def _reject_worktree_paths(node: Any, trail: str = "document") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_PATH_KEYS:
                raise blocked("WORKTREE_PATH_FORBIDDEN", f"{trail}.{key} may not be persisted in the bundle")
            _reject_worktree_paths(value, f"{trail}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _reject_worktree_paths(value, f"{trail}[{index}]")
    elif isinstance(node, str) and ABSOLUTE_RE.match(node):
        raise blocked("WORKTREE_PATH_FORBIDDEN", f"{trail} holds an absolute path")


def validate_source(source: Any, *, parent_work_id: Any) -> None:
    """Validate ``immutable.source`` (section 5.6) fail-closed."""
    if source is None:
        return
    if not isinstance(source, dict) or set(source) != set(SOURCE_FIELDS):
        raise blocked("INVALID_SOURCE", f"source requires exactly {sorted(SOURCE_FIELDS)}")
    if source["kind"] not in SOURCE_KINDS:
        raise blocked("INVALID_SOURCE", "unknown source kind", kind=str(source["kind"]))
    if not isinstance(source["request_key"], str) or not REQUEST_KEY_RE.fullmatch(source["request_key"]):
        raise blocked("INVALID_SOURCE", "request_key must be a sha256 digest")
    if source["relation"] not in SOURCE_RELATIONS:
        raise blocked("INVALID_SOURCE", "unknown source relation", relation=str(source["relation"]))
    reference = source["source_ref"]
    if (
        not isinstance(reference, str)
        or not reference.strip()
        or any(character in reference for character in "\n\r\\")
        or ABSOLUTE_RE.match(reference)
        or any(part in {"", ".", ".."} for part in reference.split("/"))
    ):
        raise blocked("INVALID_SOURCE", "source_ref must be a relative reference without traversal")
    if not isinstance(parent_work_id, str):
        raise blocked("INVALID_SOURCE", "source requires a parent_work_id")


def _validate_v3_extension(metadata: dict[str, Any], immutable: dict[str, Any]) -> None:
    missing = [name for name in V3_IMMUTABLE_FIELDS if name not in immutable]
    if missing:
        raise blocked("METADATA-SCHEMA", f"v3 immutable is missing {sorted(missing)}")
    work_id = immutable["work_id"]
    parent = immutable["parent_work_id"]
    if parent is not None and (not isinstance(parent, str) or not WORK_ID_RE.fullmatch(parent) or parent == work_id):
        raise blocked("INVALID_PARENT", "parent_work_id invalid or self-referential", work_id=work_id)
    validate_source(immutable["source"], parent_work_id=parent)
    key = immutable["worktree_key"]
    _ensure_logical_key(key, work_id)
    if key != worktree_key_for(work_id):
        raise blocked("WORKTREE_KEY_DIVERGENCE", "worktree_key does not derive from work_id", work_id=work_id)
    orchestration = metadata.get("orchestration")
    if not isinstance(orchestration, dict) or set(orchestration) != {"schema"} or orchestration["schema"] != ORCHESTRATION_SCHEMA:
        raise blocked("INVALID_ORCHESTRATION", f"orchestration must be {{'schema': '{ORCHESTRATION_SCHEMA}'}}", work_id=work_id)


def validate_metadata(metadata: Any, expected_work_id: str | None = None) -> dict[str, Any]:
    """Dual-read validator: accepts v2 and v3, rejects everything else.

    Returns the validated ``immutable`` block. The check order matches the live
    v2 implementation so migrated bundles keep producing the same first error.
    """
    if not isinstance(metadata, dict):
        raise blocked("METADATA-SCHEMA", "WORK-ITEM.json must be a JSON object")
    immutable = metadata.get("immutable")
    if not isinstance(immutable, dict) or metadata.get("immutable_sha256") != immutable_sha256(immutable):
        raise blocked("IMMUTABLE-TAMPERED", str(expected_work_id or "unknown"))
    schema = immutable.get("schema")
    if schema not in SCHEMAS or metadata.get("schema") != schema:
        raise blocked("METADATA-SCHEMA", "unknown or divergent work-item schema", schema=str(schema))
    missing = [name for name in V2_IMMUTABLE_FIELDS if name not in immutable]
    if missing:
        raise blocked("METADATA-SCHEMA", f"immutable is missing {sorted(missing)}")
    if (
        not isinstance(immutable["work_id"], str)
        or not WORK_ID_RE.fullmatch(immutable["work_id"])
        or immutable["type"] not in KINDS
        or not isinstance(immutable["slug"], str)
        or not SLUG_RE.fullmatch(immutable["slug"])
        or not isinstance(immutable["constitution"], dict)
        or not isinstance(immutable["workflow"], dict)
        or not all(isinstance(immutable[name], str) for name in ("branch", "head", "base_ref", "base_commit"))
    ):
        raise blocked("METADATA-SCHEMA", str(expected_work_id or immutable.get("work_id") or "unknown"))
    if expected_work_id is not None and immutable["work_id"] != expected_work_id:
        raise blocked("WORK-ID-DIVERGENCE", expected_work_id)
    # Section 5.6: no host-specific absolute path may enter the versioned
    # bundle. Swept over the *whole* document, not only `immutable` -- a
    # top-level `worktree_path` sibling of `immutable` used to slip through.
    _reject_worktree_paths(metadata)
    if schema == SCHEMA_V2:
        smuggled = [name for name in V3_IMMUTABLE_FIELDS if name in immutable]
        if smuggled or "orchestration" in metadata:
            raise blocked("METADATA-SCHEMA", "v2 document carries v3 fields", work_id=immutable["work_id"])
    else:
        _validate_v3_extension(metadata, immutable)
    return immutable


def schema_of(metadata: Any) -> str:
    """Validated schema literal of a work-item document."""
    return validate_metadata(metadata)["schema"]


# --------------------------------------------------------------------------
# production-reader capability probe
# --------------------------------------------------------------------------


def _load_production_reader():
    """Dynamically load grill_workspace.py, mirroring its own sibling loader.

    Never a static import (module docstring: this package stays free of any
    import from ``grill_workspace``) and never a write -- LD-003 forbids
    editing ``grill_workspace.py``, not reading it. Returns ``None`` on any
    load failure so the caller stays conservative.
    """
    try:
        spec = importlib.util.spec_from_file_location("grill_core._grill_workspace_probe", GRILL_WORKSPACE_PATH)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        original_stdout = sys.stdout
        capture = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
        try:
            sys.stdout = capture
            spec.loader.exec_module(module)
        finally:
            sys.stdout = original_stdout
            capture.close()
    except BaseException:
        if 'spec' in locals() and spec is not None:
            sys.modules.pop(spec.name, None)
        return None
    return module


def production_reader_accepts_v3() -> bool:
    """Whether grill_workspace.py's own ``validate_metadata`` already reads v3.

    A functional probe, not a version-string comparison: builds a minimal,
    self-consistent v3 document and asks the *real* production reader -- the
    same function ``grill_workspace.py status``/``audit`` call on every real
    bundle -- to validate it. Returns False on any load or validation
    failure, so ``migrate_bundle(apply=True)`` stays fail-closed by default
    until a CLI-wiring round actually teaches the reader about v3 (Fase 1 /
    secao 23: applying the only migration this module offers must never make
    the live CLI regress from a working ``status``/``audit`` to
    ``METADATA-SCHEMA``).
    """
    module = _load_production_reader()
    if module is None or not hasattr(module, "validate_metadata"):
        return False
    probe_work_id = "grill-v3-probe"
    probe_immutable = {
        "schema": SCHEMA_V3,
        "work_id": probe_work_id,
        "type": "feature",
        "slug": "grill-v3-probe",
        "branch": "probe",
        "head": "0" * 40,
        "base_ref": "probe",
        "base_commit": "0" * 40,
        "constitution": {},
        "workflow": {},
        "parent_work_id": None,
        "source": None,
        "worktree_key": worktree_key_for(probe_work_id),
    }
    probe_document = {
        "schema": SCHEMA_V3,
        "immutable": probe_immutable,
        "immutable_sha256": immutable_sha256(probe_immutable),
        "orchestration": {"schema": ORCHESTRATION_SCHEMA},
    }
    try:
        result = module.validate_metadata(probe_document, probe_work_id)
    except Exception:
        return False
    return isinstance(result, dict) and result.get("schema") == SCHEMA_V3


def production_cli_wires_migrate_v3() -> tuple[bool, str | None]:
    """Whether grill_workspace.py's own CLI actually runs ``migrate-v3``, live.

    Same spirit as :func:`production_reader_accepts_v3` (LD-010): no
    hardcoded verdict, no version-string comparison, and no manually-typed
    command string to go stale. Loads the real production module the same
    way that probe does, asks its *own* ``build_parser()`` whether
    ``migrate-v3 ROOT --work-id ID`` parses to ``command == "migrate-v3"``,
    confirms a callable handler is exported for it -- and only then derives
    the exact runnable invocation (positionals and flags, in the order the
    live subparser declares them) straight out of that subparser, instead of
    hand-typing it. Returns ``(False, None)`` on any load, parse or
    introspection failure, so ``require_v3`` can never advertise a command
    that cannot actually run.
    """
    module = _load_production_reader()
    if module is None or not callable(getattr(module, "build_parser", None)):
        return False, None
    if not callable(getattr(module, "migrate_v3_command", None)):
        return False, None
    try:
        parser = module.build_parser()
        probe_args = parser.parse_args(["migrate-v3", "/grill-v3-probe-root", "--work-id", "grill-v3-probe"])
        subparsers_action = next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        )
        migrate_v3_parser = subparsers_action.choices["migrate-v3"]
    except Exception:
        return False, None
    if getattr(probe_args, "command", None) != "migrate-v3":
        return False, None
    positionals = [action.dest.upper() for action in migrate_v3_parser._actions if not action.option_strings]
    flags: list[str] = []
    for action in migrate_v3_parser._actions:
        if not action.option_strings or action.dest == "help":
            continue
        flag = action.option_strings[-1]
        if action.required:
            flags.append(f"{flag} ID" if "work" in action.dest else flag)
        else:
            flags.append(f"[{flag}]")
    command = " ".join(["grill_workspace.py", "migrate-v3", *positionals, *flags])
    return True, command


def require_v3(metadata: Any, operation: str, expected_work_id: str | None = None) -> dict[str, Any]:
    """Gate for operations that need v3; a v2 bundle gets a named error.

    ``migration_wired`` and ``migration_command`` come from a live functional
    probe (:func:`production_cli_wires_migrate_v3`), never a hardcoded
    constant -- LD-010 caught exactly that bug: this payload used to claim
    ``migration_wired: False`` unconditionally, even once grill_workspace.py
    grew a real, callable ``migrate-v3`` verb, because the field was a
    literal rather than a probe result. The recommendation nests three ways,
    best to worst: (1) a production reader accepts v3 *and*
    grill_workspace.py's own CLI wires ``migrate-v3`` -- quote the exact,
    live-derived command; (2) a reader accepts v3 but no CLI verb is wired --
    point at the callable capability directly; (3) no reader accepts v3 yet
    -- ``migration_note`` must not tell the caller to run anything, since
    doing so would only earn ``V3_READERS_NOT_WIRED``.
    """
    immutable = validate_metadata(metadata, expected_work_id)
    if immutable["schema"] == SCHEMA_V3:
        return immutable
    work_id = immutable["work_id"]
    readers_wired = production_reader_accepts_v3()
    cli_wired, migration_command = production_cli_wires_migrate_v3() if readers_wired else (False, None)
    if cli_wired:
        note = (
            f"run `{migration_command}` -- omit --apply for a preview; the production "
            "reader already accepts grill-work-item/v3, so applying is safe."
        )
    elif readers_wired:
        note = (
            "no migrate-v3 verb is wired into grill_workspace.py's CLI yet; call "
            f"{MIGRATION_CAPABILITY}(item_dir, apply=True) directly -- the production "
            "reader already accepts grill-work-item/v3, so applying is safe."
        )
    else:
        note = (
            "no production reader accepts grill-work-item/v3 yet; "
            f"{MIGRATION_CAPABILITY}(item_dir, apply=True) refuses fail-closed with "
            "V3_READERS_NOT_WIRED until a CLI-wiring round teaches the reader about v3"
        )
    details: dict[str, Any] = {
        "work_id": work_id,
        "operation": operation,
        "schema": SCHEMA_V2,
        "required_schema": SCHEMA_V3,
        "migration_wired": cli_wired,
        "v3_readers_wired": readers_wired,
        "migration_capability": MIGRATION_CAPABILITY,
        "migration_note": note,
    }
    if cli_wired:
        details["migration_command"] = migration_command
    raise WorkItemError(
        EXIT_BLOCKED,
        "BLOCKED",
        "WORK_ITEM_V3_REQUIRED",
        f"{operation} requires {SCHEMA_V3}; {work_id} is {SCHEMA_V2}",
        details,
    )


# --------------------------------------------------------------------------
# upgrade (pure) and migration (preview-first)
# --------------------------------------------------------------------------


def upgrade_immutable(
    immutable: dict[str, Any],
    *,
    parent_work_id: str | None = None,
    source: dict[str, Any] | None = None,
    worktree_key: str | None = None,
) -> dict[str, Any]:
    """Return the v3 immutable block, preserving every v2 field verbatim.

    Arguments left at ``None`` keep whatever an already-v3 block carries, so the
    upgrade is idempotent and byte-stable when replayed.
    """
    work_id = immutable["work_id"]
    if worktree_key is not None:
        _ensure_logical_key(worktree_key, work_id)
    parent = parent_work_id if parent_work_id is not None else immutable.get("parent_work_id")
    if parent is not None and (not isinstance(parent, str) or not WORK_ID_RE.fullmatch(parent) or parent == work_id):
        raise blocked("INVALID_PARENT", "parent_work_id invalid or self-referential", work_id=work_id)
    inherited = source if source is not None else immutable.get("source")
    # Validate the caller's input here so the specific code wins over the
    # generic absolute-path sweep run later by validate_metadata.
    validate_source(inherited, parent_work_id=parent)
    result = dict(immutable)
    result["schema"] = SCHEMA_V3
    result["parent_work_id"] = parent
    result["source"] = dict(inherited) if isinstance(inherited, dict) else inherited
    result["worktree_key"] = worktree_key or immutable.get("worktree_key") or worktree_key_for(work_id)
    return result


def upgrade_metadata(
    metadata: dict[str, Any],
    *,
    parent_work_id: str | None = None,
    source: dict[str, Any] | None = None,
    worktree_key: str | None = None,
) -> dict[str, Any]:
    """Pure v2->v3 document upgrade: every unrelated v2 key is carried over."""
    immutable = validate_metadata(metadata)
    upgraded = upgrade_immutable(immutable, parent_work_id=parent_work_id, source=source, worktree_key=worktree_key)
    result = dict(metadata)
    result["schema"] = SCHEMA_V3
    result["immutable"] = upgraded
    result["immutable_sha256"] = immutable_sha256(upgraded)
    result["orchestration"] = {"schema": ORCHESTRATION_SCHEMA}
    validate_metadata(result, upgraded["work_id"])
    return result


def read_document(path: Path) -> dict[str, Any]:
    """Read one WORK-ITEM.json through an O_NOFOLLOW descriptor."""
    return read_document_with_digest(path)[0]


def read_document_with_digest(path: Path) -> tuple[dict[str, Any], str]:
    """Read one WORK-ITEM.json through an O_NOFOLLOW descriptor.

    Returns the parsed document together with the sha256 of the *exact bytes
    read from disk* -- the compare-and-swap anchor ``migrate_bundle`` uses to
    detect a concurrent writer touching *any* top-level key, not only
    ``immutable`` (see that function's docstring; this is the fix for the
    lost-update bug LD-010/round-3 proved 5/5 against the old,
    ``immutable_sha256``-only anchor).
    """
    if path.is_symlink():
        raise blocked("WORK-ITEM-SYMLINK", str(path))
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as exc:
        raise WorkItemError(EXIT_NO_GO, "NO-GO", "WORK-ITEM-MISSING", str(path)) from exc
    except OSError as exc:
        code = "SYMLINK-REJECTED" if exc.errno in {errno.ELOOP, errno.EMLINK} else "UNSAFE-FILE"
        raise blocked(code, str(path)) from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise blocked("WORK-ITEM-NOT-REGULAR", str(path))
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise WorkItemError(EXIT_NO_GO, "NO-GO", "INVALID-UTF8", str(path)) from exc
    try:
        return json.loads(text), hash_bytes(raw)
    except json.JSONDecodeError as exc:
        raise blocked("UNEXPECTED-INPUT", "WORK-ITEM.json is not valid JSON") from exc


def read_document_with_digest_at(directory_fd: int, name: str = "WORK-ITEM.json") -> tuple[dict[str, Any], str]:
    """Read a document relative to a pinned no-follow bundle directory."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError as exc:
        raise WorkItemError(EXIT_NO_GO, "NO-GO", "WORK-ITEM-MISSING", name) from exc
    except OSError as exc:
        code = "SYMLINK-REJECTED" if exc.errno in {errno.ELOOP, errno.EMLINK} else "UNSAFE-FILE"
        raise blocked(code, name) from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise blocked("WORK-ITEM-NOT-REGULAR", name)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    try:
        text = raw.decode("utf-8")
        return json.loads(text), hash_bytes(raw)
    except UnicodeError as exc:
        raise WorkItemError(EXIT_NO_GO, "NO-GO", "INVALID-UTF8", name) from exc
    except json.JSONDecodeError as exc:
        raise blocked("UNEXPECTED-INPUT", "WORK-ITEM.json is not valid JSON") from exc


def _atomic_replace(path: Path, data: bytes, *, mode: int | None = None) -> None:
    """Temp file in the same directory, fsync, replace, then fsync the parent.

    ``mode`` re-applies the original file's permission bits to the temp file
    before the rename, so the replace does not silently tighten them to
    whatever ``tempfile.mkstemp`` happens to default to (section 5.5.1: a
    write must not silently alter the artifact's metadata).
    """
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        if mode is not None:
            try:
                os.chmod(temporary, mode)
            except OSError:
                pass
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        parent = os.open(path.parent, directory_flags)
    except OSError:
        return
    try:
        os.fsync(parent)
    except OSError:
        pass
    finally:
        os.close(parent)


def _atomic_replace_at(directory_fd: int, name: str, data: bytes, *, mode: int | None = None) -> None:
    """Atomically replace ``name`` inside one already-pinned directory FD.

    A path-based ``mkstemp``/``replace`` pair can be redirected if an ancestor
    is exchanged while a command waits on its lock.  This variant never
    re-resolves the bundle path: open, rename and fsync all remain relative to
    the descriptor opened through the trusted Git-root chain by the CLI.
    """
    if os.open not in os.supports_dir_fd or os.rename not in os.supports_dir_fd:
        raise blocked("UNSAFE-FILE", "safe dir-fd replacement is unavailable")
    descriptor: int | None = None
    temporary: str | None = None
    try:
        # O_EXCL makes this a reservation, never an overwrite.  A directory
        # FD is the security boundary here; the timestamp/pid/retry suffix
        # merely gives concurrent writers distinct candidate names without
        # bringing a non-stdlib entropy dependency into this core module.
        for attempt in range(16):
            candidate = f".{name}.{os.getpid()}.{time.time_ns()}.{attempt}.tmp"
            try:
                descriptor = os.open(
                    candidate,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                    dir_fd=directory_fd,
                )
            except FileExistsError:
                continue
            temporary = candidate
            break
        if descriptor is None or temporary is None:
            raise blocked("UNSAFE-FILE", "could not reserve a safe temporary file")
        if mode is not None:
            try:
                os.fchmod(descriptor, mode)
            except OSError:
                pass
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # POSIX rename is the replace primitive when the destination already
        # exists; unlike ``os.replace``, CPython exposes its dir-fd support in
        # ``os.supports_dir_fd`` on every target we can safely authorise.
        os.rename(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    except Exception:
        try:
            if temporary is not None:
                os.unlink(temporary, dir_fd=directory_fd)
        except OSError:
            pass
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)


# --------------------------------------------------------------------------
# global lock per work_id (section 5.2, 5.5 invariant 11)
# --------------------------------------------------------------------------

RECOVERY_SUFFIX = ".recovery"
LOCK_TIMEOUT_SECONDS = 15.0
LOCK_POLL_SECONDS = 0.02


def _git_common_dir(item_dir: Path) -> Path | None:
    """Resolve ``<git-common-dir>`` for ``item_dir``; ``None`` if no repo.

    Section 5.2: ``git rev-parse --git-common-dir``. Read-only -- never
    creates a repository, never writes anything.
    """
    try:
        completed = subprocess.run(
            ["git", "-C", str(item_dir), "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    raw = completed.stdout.strip()
    if not raw:
        return None
    common = (item_dir / raw).resolve()
    return common if common.is_dir() else None


def lock_root(item_dir: Path) -> Path:
    """Where per-work-item migration locks live: never inside the bundle.

    Section 5.2 places locks at ``<git-common-dir>/grill/locks/``, outside
    the tracked tree, so ``bundle_fingerprint()`` (which hashes every file
    under the bundle directory) and ``git status`` never see them. Without an
    enclosing Git repository (an isolated fixture, for instance) there is no
    ``<git-common-dir>`` to use; the fallback still lives outside
    ``item_dir`` itself, so it never joins the bundle either.
    """
    common = _git_common_dir(item_dir)
    if common is not None:
        return common / "grill" / "locks"
    return item_dir.parent / ".grill-locks"


def lock_path(item_dir: Path, work_id: str) -> Path:
    return lock_root(item_dir) / f"work-{work_id}.lock"


def _lock_owner_is_dead(lock: Path) -> bool:
    """True only when the recorded owner process is provably gone.

    Conservative on purpose: any ambiguity (missing/garbled owner file,
    different host, permission to signal unknown) keeps the lock held.
    """
    try:
        owner = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
        pid, host = owner.get("pid"), owner.get("host")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return False
    if host != socket.gethostname() or type(pid) is not int or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return False


class _BundleLock:
    """Exclusive, filesystem-durable lock serializing writes to one bundle.

    Acquisition is a single ``os.mkdir`` (atomic across processes on every
    platform this project targets). The critical section held under this
    lock spans the pre-write read, the "already v3?"/divergence decision and
    the write itself, so two concurrent migrations of the same bundle can
    never both observe "not yet migrated" and both persist.

    Reclaiming a *stale* lock (owner PID provably dead) is itself serialized
    through a second, disposable mutex directory (``<lock>.recovery``): only
    the process that wins that ``mkdir`` may inspect and delete the stale
    lock, and it re-checks staleness while holding it. Without this second
    gate, two racers that both see the same stale lock could each try to
    delete it -- the loser deleting the directory the winner had *just*
    recreated for itself, letting both enter the critical section together
    (reproduced with real subprocesses before this fix; see the contract
    test). This mirrors the recovery-mutex pattern already used by the
    sibling orchestrator store lock.
    """

    def __init__(self, item_dir: Path, work_id: str) -> None:
        self._lock = lock_path(item_dir, work_id)
        self._recovery = self._lock.with_name(self._lock.name + RECOVERY_SUFFIX)
        self._work_id = work_id

    def __enter__(self) -> "_BundleLock":
        os.makedirs(self._lock.parent, exist_ok=True)
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            try:
                os.mkdir(self._lock, 0o700)
                break
            except FileExistsError:
                self._try_reclaim()
                if time.monotonic() >= deadline:
                    raise blocked("LOCK-CONTENTION", "another migration holds the bundle lock", work_id=self._work_id)
                time.sleep(LOCK_POLL_SECONDS)
        owner = json.dumps({"pid": os.getpid(), "host": socket.gethostname()}).encode("utf-8")
        try:
            descriptor = os.open(self._lock / "owner.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(descriptor, owner)
            finally:
                os.close(descriptor)
        except OSError:
            pass
        return self

    def _try_reclaim(self) -> None:
        """Atomically hand a provably-stale lock to exactly one reclaimer.

        ``os.mkdir`` on the recovery directory is the exclusion point: only
        its winner may act. Losers do nothing to ``self._lock`` at all --
        they neither unlink nor rmdir it -- so a loser can never destroy a
        lock the winner (or a brand-new, live owner) just (re)created.
        """
        try:
            os.mkdir(self._recovery, 0o700)
        except FileExistsError:
            return
        try:
            if _lock_owner_is_dead(self._lock):
                shutil.rmtree(self._lock, ignore_errors=True)
        finally:
            shutil.rmtree(self._recovery, ignore_errors=True)

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        shutil.rmtree(self._lock, ignore_errors=True)


class _HeldBundleLock:
    """Context-manager shape used when the CLI already owns the safe lock.

    ``migrate-v3`` pins the bundle directory and acquires its outer lock before
    it calls this core routine.  Re-acquiring a path-based lock here would both
    deadlock and re-open the ancestor-symlink race this dir-FD path avoids.
    """

    def __enter__(self) -> "_HeldBundleLock":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


def _validate_requested_fields(
    immutable: dict[str, Any],
    *,
    parent_work_id: str | None,
    source: dict[str, Any] | None,
    worktree_key: str | None,
) -> None:
    """Validate caller-supplied migration args before *any* schema branch.

    Applies whether the bundle is still v2 (about to be upgraded) or already
    v3 (about to be checked for divergence): an invalid ``worktree_key`` or
    ``parent_work_id`` must fail as itself, not be swallowed into a generic
    MIGRATION_DIVERGENCE because it merely differs from what is on disk.
    """
    work_id = immutable["work_id"]
    if worktree_key is not None:
        _ensure_logical_key(worktree_key, work_id)
    if parent_work_id is not None and (
        not isinstance(parent_work_id, str) or not WORK_ID_RE.fullmatch(parent_work_id) or parent_work_id == work_id
    ):
        raise blocked("INVALID_PARENT", "parent_work_id invalid or self-referential", work_id=work_id)
    if source is not None:
        effective_parent = parent_work_id if parent_work_id is not None else immutable.get("parent_work_id")
        validate_source(source, parent_work_id=effective_parent)


def migrate_bundle(
    item_dir: Path,
    *,
    apply: bool = False,
    parent_work_id: str | None = None,
    source: dict[str, Any] | None = None,
    worktree_key: str | None = None,
    item_dir_fd: int | None = None,
    lock_held: bool = False,
) -> dict[str, Any]:
    """Preview-first, idempotent, lock-serialized v2->v3 migration of one bundle.

    ``apply=False`` writes nothing at all: it only reports what would change,
    and takes no lock (previews stay read-only, section 22/Core).

    ``apply=True`` first proves a production reader actually accepts v3
    (:func:`production_reader_accepts_v3`) and refuses fail-closed with
    ``V3_READERS_NOT_WIRED`` when none does -- the only migration this module
    offers must never make the live CLI regress from a working
    ``status``/``audit`` to ``METADATA-SCHEMA`` (Fase 1 / secao 23). Once
    proven, it holds :class:`_BundleLock` from the read that the decision is
    based on through the fsync of the parent directory, so the "already v3?"
    check, the divergence check and the write happen inside one critical
    section (section 5.5 invariant 11).

    Immediately before writing it re-reads the *entire on-disk document*
    through :func:`read_document_with_digest` and refuses with
    ``STATE_DIVERGENCE`` if the sha256 of those raw bytes no longer matches
    what the decision was based on -- a compare-and-swap over the whole
    document, not merely ``metadata["immutable_sha256"]``. That narrower
    anchor was proven wrong (LD-010/round-3, reproduced 5/5 with a real,
    independent OS process): a concurrent writer outside this lock's domain
    that only edits an unrelated top-level key (``scope``, say) leaves
    ``immutable_sha256`` untouched, so a CAS anchored there let the migrated
    document -- built from the *first* read -- silently overwrite that
    writer's change with ``APPLIED`` and no warning. Anchoring on the whole
    document's bytes instead means any change made while the lock was held,
    by any process, to any key, is detected and refused fail-closed. Running
    it again once applied returns ``REUSED``. Any unexpected OS-level failure
    (a read-only bundle directory, for instance) is reported as a structured
    ``FILESYSTEM`` error, never a raw exception.
    """
    item_dir = Path(item_dir)
    work_id = item_dir.name
    path = item_dir / "WORK-ITEM.json"
    if lock_held and item_dir_fd is None:
        raise blocked("UNSAFE-FILE", "lock_held requires a pinned work-item directory descriptor")
    if item_dir_fd is not None:
        try:
            if not stat.S_ISDIR(os.fstat(item_dir_fd).st_mode):
                raise blocked("UNSAFE-FILE", "work-item descriptor is not a directory")
        except OSError as exc:
            raise blocked("UNSAFE-FILE", "work-item descriptor is unavailable") from exc

        def read_current() -> tuple[dict[str, Any], str]:
            return read_document_with_digest_at(item_dir_fd)

        def original_mode() -> int:
            return stat.S_IMODE(os.stat("WORK-ITEM.json", dir_fd=item_dir_fd, follow_symlinks=False).st_mode)

        def replace_current(data: bytes, mode: int) -> None:
            _atomic_replace_at(item_dir_fd, "WORK-ITEM.json", data, mode=mode)
    else:
        def read_current() -> tuple[dict[str, Any], str]:
            return read_document_with_digest(path)

        def original_mode() -> int:
            return stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode)

        def replace_current(data: bytes, mode: int) -> None:
            _atomic_replace(path, data, mode=mode)

    def decide(metadata: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        immutable = validate_metadata(metadata, work_id)
        _validate_requested_fields(immutable, parent_work_id=parent_work_id, source=source, worktree_key=worktree_key)
        current = immutable["schema"]
        base = {
            "work_id": work_id,
            "path": str(path),
            "from_schema": current,
            "to_schema": SCHEMA_V3,
            "worktree_key": worktree_key or worktree_key_for(work_id),
        }
        if current == SCHEMA_V3:
            requested = {
                "parent_work_id": parent_work_id,
                "source": source,
                "worktree_key": worktree_key,
            }
            divergent = sorted(name for name, value in requested.items() if value is not None and immutable.get(name) != value)
            if divergent:
                raise blocked("MIGRATION_DIVERGENCE", f"already migrated with different {divergent}", work_id=work_id)
            return {
                **base,
                "verdict": "REUSED",
                "code": "OK",
                "from_schema": SCHEMA_V3,
                "worktree_key": immutable["worktree_key"],
                "immutable_sha256": {"current": metadata["immutable_sha256"], "next": metadata["immutable_sha256"]},
                "adds": [],
                "writes": [],
            }, None
        upgraded = upgrade_metadata(metadata, parent_work_id=parent_work_id, source=source, worktree_key=worktree_key)
        preview = {
            **base,
            "verdict": "PREVIEW",
            "code": "OK",
            "worktree_key": upgraded["immutable"]["worktree_key"],
            "immutable_sha256": {"current": metadata["immutable_sha256"], "next": upgraded["immutable_sha256"]},
            "adds": sorted([*V3_IMMUTABLE_FIELDS, "orchestration"]),
            "writes": [],
        }
        return preview, upgraded

    if not apply:
        preview, _ = decide(read_current()[0])
        return preview

    if not production_reader_accepts_v3():
        raise blocked(
            "V3_READERS_NOT_WIRED",
            "no production reader accepts grill-work-item/v3 yet; migration stays "
            "fail-closed until a CLI-wiring round teaches the reader about v3",
            work_id=work_id,
        )

    try:
        lock_context = _HeldBundleLock() if lock_held else _BundleLock(item_dir, work_id)
        with lock_context:
            metadata, baseline_document_sha256 = read_current()
            preview, upgraded = decide(metadata)
            if upgraded is None:
                return preview
            data = document_bytes(upgraded)
            preserved_mode = original_mode()
            # Re-read the whole document as late as possible -- immediately
            # before the write -- so the unprotected window between this
            # check and `_atomic_replace` below is as small as it can be.
            _, current_document_sha256 = read_current()
            if current_document_sha256 != baseline_document_sha256:
                raise blocked(
                    "STATE_DIVERGENCE",
                    "WORK-ITEM.json changed between read and write",
                    work_id=work_id,
                )
            replace_current(data, preserved_mode)
            persisted, persisted_document_sha256 = read_current()
            if persisted != upgraded or persisted_document_sha256 != hash_bytes(data):
                raise blocked("STATE_DIVERGENCE", "persisted document does not match the migrated document", work_id=work_id)
            validate_metadata(persisted, work_id)
            return {**preview, "verdict": "APPLIED", "writes": ["WORK-ITEM.json"], "document_sha256": hash_bytes(data)}
    except WorkItemError:
        raise
    except OSError as exc:
        raise blocked("FILESYSTEM", f"filesystem-error:{type(exc).__name__}", work_id=work_id) from exc
