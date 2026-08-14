#!/usr/bin/env python3
"""Shared local JSON store at ``<git-common-dir>/grill`` (``grill-orchestrator/v1``).

Plan clauses implemented here: 5.2 (directory layout incl. receipt category
subdirectories, path obtained from ``git rev-parse --git-common-dir``), 5.4
(``orchestrator.json`` schema, including the declared shape of ``work_items``,
``dispatch_control`` and ``backlog_links``, and rejection of unknown top-level
keys), 5.5 invariants 10-14 (monotonic revision + CAS against the revision
read by the caller; lock + same-directory temp file + fsync + ``os.replace``
+ re-read + hash; fail-closed ``ORCHESTRATOR_INVALID`` that never recreates
silently; read-only status/preview; ``worktree.state`` is a closed enum that
includes ``READY`` and ``ORPHANED``, but *detecting* an orphaned worktree is
reconcile/worktree-piece work this module does not own), 5.5.1 (the seven
bootstrap steps, including comparing the *derived* ``integration_branch`` even
when the caller omits it), and 22/Core (lock, CAS, revision, hash, fsync,
rename, re-read, UTF-8, symlink/traversal, chained + head-witnessed event
journal, cross-check against a durable artifact outside the snapshot file).

Revision anchoring (invariant 10 + "snapshot local divergente ... do
journal") is *bidirectional* and head-of-journal, not a point lookup:

* every commit (``bootstrap``'s revision 1, every ``write_snapshot`` /
  ``transact``) appends its ``orchestrator.snapshot.committed`` record to
  ``events.jsonl`` *before* the matching ``orchestrator.json`` bytes become
  visible (journal-before-visibility), and then stamps that record's
  ``{sequence, record_sha256}`` back into the document itself as
  ``journal_head`` -- a witness pointing from the snapshot *to* the journal;
* on every read, :func:`_check_revision_anchor` requires (i) the *last*
  commit record in the journal to name the snapshot's own revision -- not
  merely *some* commit record whose hash happens to match, which is what
  makes a byte-exact rollback to an earlier, once-legitimately-committed
  revision fail even though that earlier revision has a real, untouched
  anchor sitting earlier in the journal; (ii) that check is symmetric, so a
  phantom commit record naming a *later* revision than the snapshot's is
  refused by name, not silently ignored; (iii) the document's own
  ``journal_head`` must match that same last commit record, closing the loop
  journal-side too;
* independently, :func:`_check_events_head` persists a witness of the
  journal's true tail (``events-head.json``, updated on *every* append, not
  only commits) so a pure tail-cut of *domain* events -- which a hash chain
  alone cannot detect, since a valid chain of length N is always a valid
  prefix of one of length N+k -- fails closed too, and does not let a
  subsequent append silently reissue an already-used sequence number;
* :func:`append_event` refuses ``event == 'orchestrator.snapshot.committed'``
  from any caller; only the internal commit path may mint that record, so the
  public API alone can never forge an anchor;
* :func:`_check_receipt_consistency` cross-checks the snapshot against
  ``receipts/worktree/<work_id>.json`` -- a durable artifact written on every
  commit that registers a work item, but never rewritten by a snapshot
  rollback -- and fails closed when a receipt names a work item the current
  snapshot does not know about.

Deliberate boundaries:

* the module never imports ``grill_workspace``; the public CLI will import
  *this* module in a later wiring round, never the other way round;
* nothing here downloads bytes, touches the network or requires an external
  CLI other than ``git``;
* ``project-register`` (:func:`bootstrap`) is the **only** creator.  Every read
  path is byte read-only: it never creates the directory, the JSON, a
  persistent lock or a database;
* leader-lease acquisition/renewal/takeover/heartbeat (plan 5.5 invariants
  15-18) are deliberately **not** implemented here -- see ``gaps_deferred`` in
  the round report, not this docstring, for the ownership call.

Error codes use the plan's literal SCREAMING_SNAKE spelling
(``ORCHESTRATOR_INVALID``, ``PROJECT_IDENTITY_DIVERGENCE``,
``STATE_DIVERGENCE``).  The live v2 CLI speaks SCREAMING-KEBAB; the two
conventions are reconciled once, at the wiring boundary, through
:data:`KEBAB_ALIASES` -- never per call site.
"""
from __future__ import annotations

import copy
import errno
import hashlib
import json
import math
import os
import re
import shutil
import socket
import stat
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, NoReturn

SCHEMA = "grill-orchestrator/v1"
STORE_DIRNAME = "grill"
ORCHESTRATOR_NAME = "orchestrator.json"
EVENTS_NAME = "events.jsonl"
EVENTS_HEAD_NAME = "events-head.json"
STORE_SUBDIRS = ("locks", "receipts", "policies")
RECEIPT_CATEGORIES = (
    "backlog",
    "fanout",
    "dispatch",
    "authorization",
    "skill-resolution",
    "skill-invocation",
    "step-output",
    "resume-execution",
    "worktree",
    "runtime",
)
DIR_MODE = 0o700
FILE_MODE = 0o600
LOCK_TIMEOUT = 15.0
LOCK_POLL = 0.03
ORCHESTRATOR_LOCK = "orchestrator.lock"

ORCHESTRATOR_INVALID = "ORCHESTRATOR_INVALID"
PROJECT_IDENTITY_DIVERGENCE = "PROJECT_IDENTITY_DIVERGENCE"
STATE_DIVERGENCE = "STATE_DIVERGENCE"
LOCK_CONTENTION = "LOCK_CONTENTION"
# Every code this module can raise, paired with the process exit code the CLI
# must return for it.  2 is EXIT_BLOCKED in grill_workspace.
EXIT_BY_CODE = {
    ORCHESTRATOR_INVALID: 2,
    PROJECT_IDENTITY_DIVERGENCE: 2,
    STATE_DIVERGENCE: 2,
    LOCK_CONTENTION: 2,
}
# Translation table for the wiring round; the live CLI vocabulary is kebab.
KEBAB_ALIASES = {
    ORCHESTRATOR_INVALID: "ORCHESTRATOR-INVALID",
    PROJECT_IDENTITY_DIVERGENCE: "PROJECT-IDENTITY-DIVERGENCE",
    STATE_DIVERGENCE: "STATE-DIVERGENCE",
    LOCK_CONTENTION: "LOCK-CONTENTION",
}

WORK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,100}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
PROJECT_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
IDENTITY_FIELDS = ("project_id", "git_common_dir", "control_worktree")
PROJECT_FIELDS = IDENTITY_FIELDS + ("integration_branch",)

# Plan §6.1 work item lifecycle -- the terminal + lateral projection states.
WORK_ITEM_LIFECYCLE = frozenset(
    {
        "NEW", "INITIALIZING", "ACTIVE", "AWAITING_SHIP", "COMPLETE",
        "PAUSED_BLOCKING_BACKLOG", "PAUSED_USER", "AWAITING_HUMAN",
        "SUSPECTED_STALL", "RECOVERING_STALL", "MONITOR_DEGRADED",
        "NEEDS_INPUT", "BLOCKED_CAPABILITY", "BLOCKED_DEPENDENCY",
        "NEEDS_RECONCILIATION", "SAFETY_STOP", "BUDGET_EXHAUSTED",
        "FAILED", "CANCELLED",
    }
)
# ``worktree.state`` (plan §5.4 schema example uses "READY"; §5.5 invariant 14
# names "ORPHANED" literally) is a closed enum, not an opaque string: CREATING
# is the transitional state implied by §8.7 ("git worktree add acontece antes
# do grill init"). *Detecting/marking* ORPHANED is the worktree/reconcile
# piece's job per LD-006, not this module's -- the store only has to validate
# and round-trip the value once the owning piece starts setting it.
WORKTREE_STATES = frozenset({"CREATING", "READY", "ORPHANED"})
DISPATCH_RUNTIMES = frozenset({"hermes", "claude", "codex", "core-cli"})
# Plan §8.3/§8.4: the Grill-level classification of a backlog link.
BACKLOG_LINK_RELATIONS = frozenset({"blocking", "non-blocking", "informational"})
# Plan §6.4 fan-out/promotion submachine, plus the literal §5.4 schema example
# value ("CHILD_READY_FOR_GRILL") and the catch-all failure state (§6.4 note).
BACKLOG_LINK_STATES = frozenset(
    {
        "DISCOVERED", "CLASSIFIED_OUT_OF_SCOPE", "BACKLOG_PREVIEWED",
        "BACKLOG_APPLIED", "BACKLOG_REUSED", "PARENT_PAUSED",
        "WAITING_BACKLOG_RESOLUTION", "RECONCILED", "PARENT_RESUMED",
        "CHILD_ID_RESERVED", "WORKTREE_CREATING", "WORKTREE_READY",
        "CHILD_INITIALIZING", "CHILD_GRILL_STARTED", "RUNNING_IN_PARALLEL",
        "TRACKED", "NEEDS_RECONCILIATION", "CHILD_READY_FOR_GRILL",
    }
)

# Append-only journal anchoring (plan §22/Core "journal corrompido, truncado
# ou com hash divergente" + "snapshot local divergente ... do journal").
COMMIT_EVENT = "orchestrator.snapshot.committed"
EVENTS_GENESIS_SHA256 = "0" * 64

# Plan §5.4 top-level document keys, plus ``journal_head`` -- the store's own
# addition, not in the plan's illustrative schema, that closes invariant 10
# (see module docstring). Anything else is rejected.
ALLOWED_TOP_LEVEL_KEYS = frozenset(
    {
        "schema", "revision", "project", "dispatch_control", "work_items",
        "backlog_links", "updated_at", "content_sha256", "journal_head",
    }
)


class StoreError(Exception):
    """Named, fail-closed store failure.  Mirrors CliFailure field by field."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.verdict = "BLOCKED"
        self.exit_code = EXIT_BY_CODE[code]

    def payload(self) -> dict[str, Any]:
        return {"verdict": self.verdict, "code": self.code, "error": self.message}


def _fail(code: str, message: Any) -> NoReturn:
    raise StoreError(code, str(message))


def _invalid(message: Any) -> NoReturn:
    _fail(ORCHESTRATOR_INVALID, message)


# --------------------------------------------------------------------------
# RFC 8785 (JSON Canonicalization Scheme)
# --------------------------------------------------------------------------

_ESCAPES = {0x08: "\\b", 0x09: "\\t", 0x0A: "\\n", 0x0C: "\\f", 0x0D: "\\r"}


def _jcs_string(value: str) -> str:
    out = ['"']
    for char in value:
        point = ord(char)
        if char == '"':
            out.append('\\"')
        elif char == "\\":
            out.append("\\\\")
        elif point in _ESCAPES:
            out.append(_ESCAPES[point])
        elif point < 0x20:
            out.append("\\u%04x" % point)
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _jcs_number(value: int | float) -> str:
    """Serialise per ECMAScript ``Number::toString``, as RFC 8785 requires."""
    if isinstance(value, int):
        return str(value)
    if not math.isfinite(value):
        _invalid("non-finite number is not serialisable")
    if value == int(value) and abs(value) < 1e21:
        return str(int(value))
    text = repr(float(value))
    if "e" in text:
        mantissa, exponent = text.split("e")
        sign = "-" if exponent.startswith("-") else "+"
        digits = exponent.lstrip("+-").lstrip("0") or "0"
        text = f"{mantissa}e{sign}{digits}"
    return text


def _jcs_value(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _jcs_string(value)
    if isinstance(value, (int, float)):
        return _jcs_number(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_jcs_value(item) for item in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                _invalid(f"non-string object key: {key!r}")
        # RFC 8785 sorts member names by UTF-16 code unit, not by code point.
        pairs = sorted(value.items(), key=lambda item: item[0].encode("utf-16-be"))
        return "{" + ",".join(_jcs_string(k) + ":" + _jcs_value(v) for k, v in pairs) + "}"
    _invalid(f"unsupported JSON type: {type(value).__name__}")


def jcs(document: Any) -> bytes:
    """Canonical RFC 8785 bytes of ``document`` (UTF-8, no trailing newline)."""
    return _jcs_value(document).encode("utf-8")


def jcs_sha256(document: Any) -> str:
    return hashlib.sha256(jcs(document)).hexdigest()


def content_hash(document: dict[str, Any]) -> str:
    """SHA-256 over the canonical document, excluding its own hash field and
    ``journal_head``.

    ``journal_head`` is a witness *of* the commit that publishes this exact
    ``content_sha256`` (see the module docstring): its value -- the sequence
    and hash of the journal record that anchors this document -- can only be
    known *after* that record has been appended, which is itself only
    possible once this hash exists.  Excluding it from the hash breaks that
    circularity: ``content_sha256`` covers the document's actual content,
    and ``journal_head`` is stamped on afterwards without perturbing it.
    """
    excluded = {"content_sha256", "journal_head"}
    return jcs_sha256({key: value for key, value in document.items() if key not in excluded})


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            _invalid(f"duplicate JSON key: {key}")
        seen[key] = value
    return seen


def loads(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        _invalid(f"invalid JSON: {exc.msg}")


def _decode(data: bytes, path: Path) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        _invalid(f"invalid utf-8: {path}")


# --------------------------------------------------------------------------
# Filesystem primitives (fail-closed, no silent creation)
# --------------------------------------------------------------------------


def _lstat(path: Path) -> os.stat_result | None:
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        _invalid(f"{type(exc).__name__}: {path}")


def _validate_directory(path: Path) -> None:
    info = _lstat(path)
    if info is None:
        _invalid(f"missing directory: {path}")
    if stat.S_ISLNK(info.st_mode):
        _invalid(f"symlink rejected: {path}")
    if not stat.S_ISDIR(info.st_mode):
        _invalid(f"not a directory: {path}")
    if os.name == "posix":
        if info.st_uid != os.getuid():
            _invalid(f"unexpected owner: {path}")
        if info.st_mode & 0o077:
            _invalid(f"permissions wider than project policy: {path}")


def _validate_regular(path: Path) -> None:
    info = _lstat(path)
    if info is None:
        _invalid(f"missing file: {path}")
    if stat.S_ISLNK(info.st_mode):
        _invalid(f"symlink rejected: {path}")
    if not stat.S_ISREG(info.st_mode):
        _invalid(f"not a regular file: {path}")


def _ensure_directory(path: Path) -> None:
    """Create one directory, or accept EEXIST only after lstat/owner/mode."""
    try:
        os.mkdir(path, DIR_MODE)
    except FileExistsError:
        _validate_directory(path)
        return
    except OSError as exc:
        _invalid(f"{type(exc).__name__}: {path}")
    if os.name == "posix":
        os.chmod(path, DIR_MODE)  # mkdir mode is masked by umask
    _validate_directory(path)


def _read_regular(path: Path) -> bytes:
    """Read one regular file through an O_NOFOLLOW descriptor."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        handle = os.open(path, flags)
    except FileNotFoundError:
        _invalid(f"missing file: {path}")
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.EMLINK}:
            _invalid(f"symlink rejected: {path}")
        _invalid(f"{type(exc).__name__}: {path}")
    try:
        info = os.fstat(handle)
        if not stat.S_ISREG(info.st_mode):
            _invalid(f"not a regular file: {path}")
        chunks = []
        while True:
            chunk = os.read(handle, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(handle)


def _fsync_directory(path: Path) -> None:
    try:
        handle = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return  # directory fsync is unavailable on some supported filesystems
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)


# --------------------------------------------------------------------------
# Git identity
# --------------------------------------------------------------------------


def _git(root: Path, *args: str, required: bool = True) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if process.returncode != 0:
        if required:
            _invalid(f"git {' '.join(args)} failed in {root}")
        return ""
    return process.stdout.strip()


def git_common_dir(root: str | Path) -> Path:
    """Resolve ``<git-common-dir>`` for ``root``; creates nothing.

    ``git rev-parse --git-common-dir`` answers ``.git`` (relative) in a normal
    checkout.  The answer is resolved against the **worktree**, never against
    the process working directory.
    """
    path = Path(root)
    if path.is_symlink() or not path.is_dir():
        _invalid(f"root must be a real directory: {path}")
    top = _git(path, "rev-parse", "--show-toplevel")
    if not top or Path(os.path.realpath(top)) != Path(os.path.realpath(path)):
        _invalid(f"root must be the Git top-level: {path}")
    raw = _git(path, "rev-parse", "--git-common-dir")
    if not raw:
        _invalid(f"git-common-dir unavailable: {path}")
    candidate = Path(raw)
    common = candidate if candidate.is_absolute() else (path / candidate)
    common = Path(os.path.abspath(common))
    if os.path.islink(common):
        _invalid(f"symlink rejected: {common}")
    if not os.path.isdir(common):
        _invalid(f"not a directory: {common}")
    return Path(os.path.realpath(common))


def _main_worktree(root: Path) -> Path:
    for line in _git(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            return Path(os.path.realpath(line[len("worktree ") :]))
    _invalid(f"git worktree list produced no worktree: {root}")


def project_identity(root: str | Path) -> dict[str, str]:
    """Derive the stable project identity; creates nothing.

    The identity material is the set of root commits, which survives clones and
    is identical from every worktree.  A repository without commits falls back
    to the resolved common directory, which is stable per machine.
    """
    path = Path(root)
    common = git_common_dir(path)
    commits = [line for line in _git(path, "rev-list", "--max-parents=0", "--all", required=False).splitlines() if line]
    if commits:
        material: dict[str, Any] = {"kind": "root-commits", "root_commits": sorted(commits)}
    else:
        material = {"kind": "git-common-dir", "git_common_dir": str(common)}
    return {
        "project_id": "sha256:" + jcs_sha256(material),
        "git_common_dir": str(common),
        "control_worktree": str(_main_worktree(path)),
    }


def _default_integration_branch(root: Path) -> str:
    branch = _git(_main_worktree(root), "symbolic-ref", "--short", "HEAD", required=False)
    return branch or "main"


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StorePaths:
    common: Path
    root: Path
    orchestrator: Path
    events: Path
    events_head: Path
    locks: Path
    receipts: Path
    policies: Path


def _paths_for(common: Path) -> StorePaths:
    base = common / STORE_DIRNAME
    return StorePaths(
        common=common,
        root=base,
        orchestrator=base / ORCHESTRATOR_NAME,
        events=base / EVENTS_NAME,
        events_head=base / EVENTS_HEAD_NAME,
        locks=base / "locks",
        receipts=base / "receipts",
        policies=base / "policies",
    )


def store_paths(root: str | Path) -> StorePaths:
    """Compute every store path.  Read-only: creates nothing."""
    return _paths_for(git_common_dir(root))


def receipt_path(root: str | Path, category: str, name: str) -> Path:
    """Path of one receipt.  Read-only; rejects traversal before touching disk."""
    if category not in RECEIPT_CATEGORIES:
        _invalid(f"unknown receipt category: {category}")
    if not isinstance(name, str) or not SAFE_NAME_RE.match(name):
        _invalid(f"unsafe receipt name: {name!r}")
    return store_paths(root).receipts / category / f"{name}.json"


def _lock_name(work_id: str) -> str:
    if not isinstance(work_id, str) or not WORK_ID_RE.match(work_id):
        _invalid(f"invalid work id: {work_id!r}")
    return f"work-{work_id}.lock"


# --------------------------------------------------------------------------
# Lock (mkdir mutex; the store directory is never derived from raw input)
# --------------------------------------------------------------------------


def _process_start_token(pid: int) -> tuple[str, str | None]:
    path = Path("/proc") / str(pid) / "stat"
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return "missing", None
    except OSError:
        return "unavailable", None
    tail = raw.rpartition(")")[2].split()
    if len(tail) <= 19:
        return "unavailable", None
    return "found", f"linux:{tail[19]}"


def _stale_lock(lock: Path) -> bool:
    try:
        owner = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
        pid, host, recorded = owner.get("pid"), owner.get("host"), owner.get("process_start")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return False
    if type(pid) is not int or pid <= 0 or host != socket.gethostname():
        return False
    observation, current = _process_start_token(pid)
    return bool(
        isinstance(recorded, str)
        and recorded.startswith("linux:")
        and observation in {"found", "missing"}
        and current != recorded
    )


@contextmanager
def _mutex(directory: Path, name: str, timeout: float) -> Iterator[Path]:
    _validate_directory(directory)
    lock = directory / name
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.mkdir(lock, DIR_MODE)
            break
        except FileExistsError:
            recovery = directory / f".{name}.recovery"
            recovered = False
            try:
                os.mkdir(recovery, DIR_MODE)
            except FileExistsError:
                pass
            else:
                try:
                    # Re-read the owner while holding the recovery mutex, so an
                    # old waiter cannot delete a freshly acquired lock.
                    if _stale_lock(lock):
                        shutil.rmtree(lock, ignore_errors=False)
                        recovered = True
                except FileNotFoundError:
                    recovered = True
                finally:
                    shutil.rmtree(recovery, ignore_errors=True)
            if recovered:
                continue
            if time.monotonic() >= deadline:
                _fail(LOCK_CONTENTION, str(lock))
            time.sleep(LOCK_POLL)
        except OSError as exc:
            _invalid(f"{type(exc).__name__}: {lock}")
    owner: dict[str, Any] = {"pid": os.getpid(), "host": socket.gethostname()}
    status, token = _process_start_token(os.getpid())
    if status == "found" and token is not None:
        owner["process_start"] = token
    (lock / "owner.json").write_text(json.dumps(owner, sort_keys=True), encoding="utf-8")
    try:
        yield lock
    finally:
        shutil.rmtree(lock, ignore_errors=True)


@contextmanager
def orchestrator_lock(paths: StorePaths, timeout: float = LOCK_TIMEOUT) -> Iterator[Path]:
    """Global write lock for ``orchestrator.json`` (invariant 11)."""
    with _mutex(paths.locks, ORCHESTRATOR_LOCK, timeout) as lock:
        yield lock


@contextmanager
def work_lock(root: str | Path, work_id: str, timeout: float = LOCK_TIMEOUT) -> Iterator[Path]:
    """Per-work-item lock; the name is validated before any path is opened."""
    name = _lock_name(work_id)
    with _mutex(store_paths(root).locks, name, timeout) as lock:
        yield lock


# --------------------------------------------------------------------------
# Snapshot read / validation
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Snapshot:
    document: dict[str, Any]
    revision: int
    content_sha256: str
    project_id: str
    path: Path


def _validate_worktree_block(worktree: Any, work_id: str) -> None:
    """Plan §5.4 ``work_items.<id>.worktree``.  ``state`` is validated against
    the closed :data:`WORKTREE_STATES` enum (which includes ``READY`` and
    ``ORPHANED``, invariant 14), and ``base_commit`` must be 40-hex or
    ``null``."""
    if worktree is None:
        return
    if not isinstance(worktree, dict):
        _invalid(f"invalid worktree block: {work_id}")
    if not isinstance(worktree.get("worktree_id"), str) or not SAFE_NAME_RE.match(worktree["worktree_id"]):
        _invalid(f"invalid worktree.worktree_id: {work_id}")
    if not isinstance(worktree.get("path"), str) or not worktree["path"]:
        _invalid(f"invalid worktree.path: {work_id}")
    if not isinstance(worktree.get("branch"), str) or not worktree["branch"]:
        _invalid(f"invalid worktree.branch: {work_id}")
    if worktree.get("state") not in WORKTREE_STATES:
        _invalid(f"invalid worktree.state: {work_id}: {worktree.get('state')!r}")
    if "base_commit" not in worktree:
        _invalid(f"missing worktree.base_commit: {work_id}")
    base_commit = worktree["base_commit"]
    if base_commit is not None and not (isinstance(base_commit, str) and HEX40_RE.match(base_commit)):
        _invalid(f"invalid worktree.base_commit: {work_id}: {base_commit!r}")


def _validate_backlog_links(backlog_links: Any) -> None:
    """Plan §5.4 ``backlog_links``: a safe key mapping to an object whose
    ``state`` and ``relation`` come from closed enumerations (§6.4, §8.3)."""
    if not isinstance(backlog_links, dict):
        _invalid("invalid backlog_links block")
    for key, link in backlog_links.items():
        if not isinstance(key, str) or not SAFE_NAME_RE.match(key):
            _invalid(f"invalid backlog_links key: {key!r}")
        if not isinstance(link, dict):
            _invalid(f"backlog link must be an object: {key}")
        if link.get("state") not in BACKLOG_LINK_STATES:
            _invalid(f"invalid backlog_links.{key}.state: {link.get('state')!r}")
        if link.get("relation") not in BACKLOG_LINK_RELATIONS:
            _invalid(f"invalid backlog_links.{key}.relation: {link.get('relation')!r}")


def _validate_monitoring_block(monitoring: Any, work_id: str) -> None:
    """Plan §5.4 ``work_items.<id>.monitoring``."""
    if monitoring is None:
        return
    if not isinstance(monitoring, dict):
        _invalid(f"invalid monitoring block: {work_id}")
    for key in ("dispatcher_epoch", "fencing_token"):
        if key in monitoring and monitoring[key] is not None and type(monitoring[key]) is not int:
            _invalid(f"invalid monitoring.{key}: {work_id}")


def _validate_work_items(work_items: Any) -> None:
    """Plan §5.4: ``work_items`` maps a safe ``work_id`` to an object with at
    least ``type``/``slug``/``lifecycle``/``worktree``/``monitoring``."""
    if not isinstance(work_items, dict):
        _invalid("invalid work_items block")
    for work_id, item in work_items.items():
        if not isinstance(work_id, str) or not WORK_ID_RE.match(work_id):
            _invalid(f"invalid work_items key: {work_id!r}")
        if not isinstance(item, dict):
            _invalid(f"work item must be an object: {work_id}")
        if not isinstance(item.get("type"), str) or not item["type"]:
            _invalid(f"invalid work item type: {work_id}")
        if not isinstance(item.get("slug"), str) or not SAFE_NAME_RE.match(item["slug"]):
            _invalid(f"invalid work item slug: {work_id}")
        if item.get("lifecycle") not in WORK_ITEM_LIFECYCLE:
            _invalid(f"invalid work item lifecycle: {work_id}")
        _validate_worktree_block(item.get("worktree"), work_id)
        _validate_monitoring_block(item.get("monitoring"), work_id)


def _validate_dispatch_control(dispatch_control: Any) -> None:
    """Plan §5.4: ``dispatch_control`` has ``leader_epoch`` and ``leader_lease``."""
    if not isinstance(dispatch_control, dict):
        _invalid("invalid dispatch_control block")
    epoch = dispatch_control.get("leader_epoch")
    if type(epoch) is not int or isinstance(epoch, bool) or epoch < 0:
        _invalid(f"invalid dispatch_control.leader_epoch: {epoch!r}")
    lease = dispatch_control.get("leader_lease")
    if lease is None:
        return
    if not isinstance(lease, dict):
        _invalid(f"invalid dispatch_control.leader_lease: {lease!r}")
    for field in ("lease_id", "owner_id"):
        if not isinstance(lease.get(field), str) or not lease[field]:
            _invalid(f"invalid leader_lease.{field}")
    if lease.get("runtime") not in DISPATCH_RUNTIMES:
        _invalid(f"invalid leader_lease.runtime: {lease.get('runtime')!r}")
    token = lease.get("fencing_token")
    if type(token) is not int or isinstance(token, bool) or token < 0:
        _invalid(f"invalid leader_lease.fencing_token: {token!r}")
    for field in ("acquired_at", "expires_at"):
        if not isinstance(lease.get(field), str) or not RFC3339_RE.match(lease[field]):
            _invalid(f"invalid leader_lease.{field}: {lease.get(field)!r}")


def _validate_journal_head(head: Any) -> None:
    """Shape only.  Whether it actually names the journal's last commit
    record is a *content* question, answered by :func:`_check_revision_anchor`
    on read -- this only guards against a structurally bogus value."""
    if not isinstance(head, dict):
        _invalid(f"invalid journal_head: {head!r}")
    sequence = head.get("sequence")
    if type(sequence) is not int or isinstance(sequence, bool) or sequence < 1:
        _invalid(f"invalid journal_head.sequence: {sequence!r}")
    digest = head.get("record_sha256")
    if not isinstance(digest, str) or not HEX64_RE.match(digest):
        _invalid(f"invalid journal_head.record_sha256: {digest!r}")


def _validate_document(document: Any, path: Path) -> dict[str, Any]:
    if not isinstance(document, dict):
        _invalid(f"document must be a JSON object: {path}")
    unknown = set(document) - ALLOWED_TOP_LEVEL_KEYS
    if unknown:
        _invalid(f"unknown top-level key: {sorted(unknown)}")
    schema = document.get("schema")
    if schema != SCHEMA:
        _invalid(f"unknown schema: {schema!r}")
    revision = document.get("revision")
    if type(revision) is not int or revision < 1:
        _invalid(f"invalid revision: {revision!r}")
    project = document.get("project")
    if not isinstance(project, dict) or any(not isinstance(project.get(f), str) for f in PROJECT_FIELDS):
        _invalid("invalid project block")
    if not PROJECT_ID_RE.match(project["project_id"]):
        _invalid(f"invalid project_id: {project['project_id']!r}")
    for key in ("dispatch_control", "work_items", "backlog_links"):
        if not isinstance(document.get(key), dict):
            _invalid(f"invalid {key} block")
    _validate_dispatch_control(document["dispatch_control"])
    _validate_work_items(document["work_items"])
    _validate_backlog_links(document["backlog_links"])
    if "journal_head" in document:
        _validate_journal_head(document["journal_head"])
    if not isinstance(document.get("updated_at"), str) or not RFC3339_RE.match(document["updated_at"]):
        _invalid(f"invalid updated_at: {document.get('updated_at')!r}")
    digest = document.get("content_sha256")
    if not isinstance(digest, str) or not HEX64_RE.match(digest):
        _invalid(f"invalid content_sha256: {digest!r}")
    expected = content_hash(document)
    if digest != expected:
        _invalid(f"content hash mismatch: {path}")
    return document


def _snapshot_from(data: bytes, path: Path) -> Snapshot:
    document = _validate_document(loads(_decode(data, path)), path)
    return Snapshot(
        document=document,
        revision=document["revision"],
        content_sha256=document["content_sha256"],
        project_id=document["project"]["project_id"],
        path=path,
    )


def _read_paths(paths: StorePaths, *, required: bool) -> Snapshot | None:
    info = _lstat(paths.root)
    if info is None:
        if required:
            _invalid(f"store not initialised: {paths.root} (run project-register)")
        return None
    _validate_directory(paths.root)
    if _lstat(paths.orchestrator) is None:
        if required:
            _invalid(f"store not initialised: {paths.orchestrator} (run project-register)")
        return None
    snapshot = _snapshot_from(_read_regular(paths.orchestrator), paths.orchestrator)
    _check_revision_anchor(paths, snapshot)
    return snapshot


def read_snapshot(root: str | Path, *, required: bool = True) -> Snapshot | None:
    """Read and fully validate the snapshot.  Read-only: creates nothing."""
    return _read_paths(store_paths(root), required=required)


def store_exists(root: str | Path) -> bool:
    """True when the store is initialised.  Read-only: creates nothing."""
    paths = store_paths(root)
    return _lstat(paths.root) is not None and _lstat(paths.orchestrator) is not None


def _require(paths: StorePaths) -> Snapshot:
    snapshot = _read_paths(paths, required=True)
    assert snapshot is not None
    return snapshot


# --------------------------------------------------------------------------
# Snapshot write
# --------------------------------------------------------------------------


def _now(now: Callable[[], str] | None) -> str:
    if now is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    value = now()
    if not isinstance(value, str) or not RFC3339_RE.match(value):
        _invalid(f"clock produced a non RFC3339 timestamp: {value!r}")
    return value


def stamp(document: dict[str, Any], revision: int, timestamp: str) -> dict[str, Any]:
    """Return ``document`` with revision, timestamp and a fresh content hash."""
    stamped = {key: value for key, value in document.items() if key != "content_sha256"}
    stamped["revision"] = revision
    stamped["updated_at"] = timestamp
    stamped["content_sha256"] = content_hash(stamped)
    return stamped


def initial_document(project: dict[str, str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "revision": 1,
        "project": dict(project),
        "dispatch_control": {"leader_epoch": 0, "leader_lease": None},
        "work_items": {},
        "backlog_links": {},
        "updated_at": "1970-01-01T00:00:00Z",
        "content_sha256": "0" * 64,
    }


def _atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    """Temp file in the same directory + fsync + ``os.replace``, for
    artifacts that live beside ``orchestrator.json`` but are not it (the
    events-head witness, worktree receipts)."""
    payload = jcs(document) + b"\n"
    handle, temporary_name = tempfile.mkstemp(prefix=".grill-", dir=path.parent)
    temporary: Path | None = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    _fsync_directory(path.parent)


def _write_document(paths: StorePaths, document: dict[str, Any]) -> Snapshot:
    """Invariant 11: temp file in the same directory, fsync, replace, re-read, hash."""
    payload = jcs(document) + b"\n"
    handle, temporary_name = tempfile.mkstemp(prefix=".orchestrator-", dir=paths.root)
    temporary: Path | None = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, paths.orchestrator)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    _fsync_directory(paths.root)
    snapshot = _snapshot_from(_read_regular(paths.orchestrator), paths.orchestrator)
    if (snapshot.revision, snapshot.content_sha256) != (document["revision"], document["content_sha256"]):
        _invalid(f"post-write verification failed: {paths.orchestrator}")
    return snapshot


def _create_exclusive(paths: StorePaths, document: dict[str, Any]) -> bool:
    """Publish revision 1 with a create-exclusive link; never clobbers."""
    payload = jcs(document) + b"\n"
    handle, temporary_name = tempfile.mkstemp(prefix=".orchestrator-", dir=paths.root)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary_name, paths.orchestrator)
            created = True
        except FileExistsError:
            created = False
        _fsync_directory(paths.root)
        return created
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _identity_of(project: dict[str, Any]) -> dict[str, Any]:
    return {field: project.get(field) for field in IDENTITY_FIELDS}


def _assert_same_project(existing: Snapshot, project: dict[str, str]) -> None:
    """§5.5.1 step 6: identity OR content divergence fails PROJECT_IDENTITY_DIVERGENCE.

    ``integration_branch`` is always compared against the stored value, not
    only when the caller passes it explicitly: ``bootstrap`` always resolves
    a concrete branch (explicit or derived from the current worktree HEAD via
    :func:`_default_integration_branch`), so a caller that omits the flag
    after switching branches must not silently get ``REUSED``.
    """
    stored = existing.document["project"]
    if jcs(_identity_of(stored)) != jcs(_identity_of(project)):
        divergent = sorted(f for f in IDENTITY_FIELDS if stored.get(f) != project.get(f))
        _fail(PROJECT_IDENTITY_DIVERGENCE, f"stored project differs on: {','.join(divergent)}")
    if stored.get("integration_branch") != project.get("integration_branch"):
        _fail(PROJECT_IDENTITY_DIVERGENCE, "stored project differs on: integration_branch")


def _ensure_events(paths: StorePaths) -> None:
    try:
        handle = os.open(paths.events, os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
    except FileExistsError:
        _validate_regular(paths.events)
        return
    except OSError as exc:
        _invalid(f"{type(exc).__name__}: {paths.events}")
    os.close(handle)


def _write_worktree_receipts(paths: StorePaths, candidate: dict[str, Any]) -> None:
    """§22/Core cross-check artifact: every commit that registers a work item
    leaves a durable receipt at ``receipts/worktree/<work_id>.json``, so a
    later snapshot divergence that "forgets" a work item is still caught by
    :func:`_check_receipt_consistency` even though it never touches this
    file.  ``work_id`` is already validated by :data:`WORK_ID_RE` (a subset
    of :data:`SAFE_NAME_RE`) via the caller's prior ``_validate_document``."""
    for work_id in candidate["work_items"]:
        _atomic_write_json(
            paths.receipts / "worktree" / f"{work_id}.json",
            {"work_id": work_id, "revision": candidate["revision"], "content_sha256": candidate["content_sha256"]},
        )


def _finalize_commit(paths: StorePaths, candidate: dict[str, Any], now: Callable[[], str] | None) -> dict[str, Any]:
    """Journal-before-visibility commit: append the anchor record, stamp the
    document's own ``journal_head`` witness from it, and leave a worktree
    receipt for every registered work item.  Caller must already hold the
    global write lock and must already have validated ``candidate``'s shape
    (``journal_head`` excepted -- it does not exist until this returns)."""
    record = _append_record_locked(paths, _commit_fields(candidate["revision"], candidate["content_sha256"]), now)
    candidate = dict(candidate)
    candidate["journal_head"] = {"sequence": record["sequence"], "record_sha256": record["content_sha256"]}
    _write_worktree_receipts(paths, candidate)
    return candidate


def bootstrap(
    root: str | Path,
    *,
    integration_branch: str | None = None,
    now: Callable[[], str] | None = None,
    timeout: float = LOCK_TIMEOUT,
) -> dict[str, Any]:
    """``project-register``: the seven steps of plan 5.5.1.  The only creator.

    Returns ``{"verdict": "CREATED"|"REUSED", ...}``.  Concurrent identical
    initialisers observe ``REUSED``; a different identity or an explicitly
    different content fails ``PROJECT_IDENTITY_DIVERGENCE``.
    """
    path = Path(root)
    identity = project_identity(path)  # steps 1 and 2
    project = dict(identity)
    project["integration_branch"] = integration_branch or _default_integration_branch(path)
    paths = _paths_for(Path(identity["git_common_dir"]))
    _ensure_directory(paths.root)  # step 3
    for name in STORE_SUBDIRS:
        _ensure_directory(paths.root / name)
    for category in RECEIPT_CATEGORIES:
        _ensure_directory(paths.receipts / category)
    digest = identity["project_id"].split(":", 1)[1]
    with _mutex(paths.locks, f"bootstrap-{digest}.lock", timeout):  # step 4
        existing = _read_paths(paths, required=False)
        if existing is None:
            document = stamp(initial_document(project), 1, _now(now))  # step 5
            _ensure_events(paths)
            with orchestrator_lock(paths, timeout):  # journal-before-visibility, see §22/Core note
                document = _finalize_commit(paths, document, now)
            if _create_exclusive(paths, document):
                snapshot = _require(paths)
                return _register_payload("CREATED", paths, snapshot)
            existing = _require(paths)
        _assert_same_project(existing, project)  # step 6
        _ensure_events(paths)
        return _register_payload("REUSED", paths, existing)


def _register_payload(verdict: str, paths: StorePaths, snapshot: Snapshot) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "verdict": verdict,
        "project_id": snapshot.project_id,
        "git_common_dir": str(paths.common),
        "store_root": str(paths.root),
        "revision": snapshot.revision,
        "content_sha256": snapshot.content_sha256,
    }


def write_snapshot(
    root: str | Path,
    document: dict[str, Any],
    expected_revision: int,
    *,
    now: Callable[[], str] | None = None,
    timeout: float = LOCK_TIMEOUT,
) -> Snapshot:
    """Compare-and-swap against the revision the caller read (invariants 10-11)."""
    paths = store_paths(root)
    with orchestrator_lock(paths, timeout):
        current = _require(paths)
        if type(expected_revision) is not int or expected_revision != current.revision:
            _fail(
                STATE_DIVERGENCE,
                f"expected revision {expected_revision!r}, store is at {current.revision}",
            )
        candidate = stamp(document, current.revision + 1, _now(now))
        if candidate["revision"] <= current.revision:
            _fail(STATE_DIVERGENCE, "revision must increase monotonically")
        _validate_document(candidate, paths.orchestrator)
        if jcs(candidate["project"]) != jcs(current.document["project"]):
            _fail(PROJECT_IDENTITY_DIVERGENCE, "project block is immutable after registration")
        candidate = _finalize_commit(paths, candidate, now)
        return _write_document(paths, candidate)


def transact(
    root: str | Path,
    mutate: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    now: Callable[[], str] | None = None,
    timeout: float = LOCK_TIMEOUT,
) -> Snapshot:
    """Read-modify-write under the global lock, with the same CAS guarantee."""
    paths = store_paths(root)
    with orchestrator_lock(paths, timeout):
        current = _require(paths)
        proposed = mutate(copy.deepcopy(current.document))
        if not isinstance(proposed, dict):
            _invalid("mutation must return a JSON object")
        if proposed.get("revision") != current.revision:
            _fail(
                STATE_DIVERGENCE,
                f"mutation carries revision {proposed.get('revision')!r}, store is at {current.revision}",
            )
        candidate = stamp(proposed, current.revision + 1, _now(now))
        _validate_document(candidate, paths.orchestrator)
        if jcs(candidate["project"]) != jcs(current.document["project"]):
            _fail(PROJECT_IDENTITY_DIVERGENCE, "project block is immutable after registration")
        candidate = _finalize_commit(paths, candidate, now)
        return _write_document(paths, candidate)


# --------------------------------------------------------------------------
# Append-only event journal -- chained (sequence + previous_sha256) and
# head-witnessed (events-head.json)
# --------------------------------------------------------------------------
#
# Every record carries a monotonic ``sequence`` (1, 2, 3, ...) and the
# ``previous_sha256`` of the record right before it (the genesis value is
# ``EVENTS_GENESIS_SHA256``).  ``content_sha256`` hashes the record
# *including* those two chain fields, so:
#
# * deleting a middle record breaks the chain at that point (the next
#   record's ``previous_sha256`` no longer matches anything on disk);
# * reordering two records breaks both the sequence progression and the
#   chain;
# * cutting whole records off the *end* does not, by itself, break the
#   remaining prefix's internal consistency -- a valid chain of length N is
#   always a valid prefix of a chain of length N+k.  Two independent
#   mechanisms close that:
#
#   1. ``events-head.json`` persists ``{sequence, content_sha256}`` of the
#      true last record on *every* append (:func:`_append_record_locked`,
#      under the same global lock), not only commits.  Every read
#      (:func:`_validated_journal_records`, via :func:`_check_events_head`)
#      and every append (:func:`_next_seq_and_prev`, which calls the same
#      validated-records path before computing the next sequence) recompute
#      the file's *actual* tail and compare it against that witness --
#      cutting whole records off the end, of any event type, leaves a
#      mismatch and fails closed instead of letting the next append silently
#      reissue an already-used ``sequence``.
#   2. Every successful snapshot commit (bootstrap's revision 1, every
#      ``write_snapshot``/``transact``, via :func:`_finalize_commit`) appends
#      an ``orchestrator.snapshot.committed`` record *before* the new
#      ``orchestrator.json`` becomes visible via ``os.replace``
#      (journal-before-visibility), and then stamps that record's own
#      ``{sequence, record_sha256}`` back into the document as
#      ``journal_head``.  :func:`_check_revision_anchor` (wired into every
#      ``_read_paths`` call) requires the snapshot's revision to be exactly
#      the revision named by the journal's *last* commit record -- not
#      merely *some* commit record with a matching hash -- and requires the
#      document's own ``journal_head`` to match that same record.  This is
#      what makes a byte-exact rollback to an earlier, once-legitimately-
#      committed revision fail even when the journal is otherwise completely
#      untouched: that earlier revision's commit record is real and
#      correctly hashed, but it is no longer the journal's *last* one.
#
# :func:`append_event` refuses ``event == COMMIT_EVENT`` from any caller, so
# the public API alone can never mint a forged anchor for mechanism 2 either.


def _next_seq_and_prev(paths: StorePaths) -> tuple[int, str]:
    records = _validated_journal_records(paths)
    if not records:
        return 1, EVENTS_GENESIS_SHA256
    last = records[-1]
    return last["sequence"] + 1, last["content_sha256"]


def _append_record_locked(paths: StorePaths, fields: dict[str, Any], now: Callable[[], str] | None) -> dict[str, Any]:
    """Append one chained record and persist the events-head witness.
    Caller must already hold the global write lock."""
    _validate_directory(paths.root)
    _validate_regular(paths.events)
    sequence, previous = _next_seq_and_prev(paths)
    record = dict(fields)
    record.setdefault("recorded_at", _now(now))
    record["sequence"] = sequence
    record["previous_sha256"] = previous
    record.pop("content_sha256", None)
    record["content_sha256"] = jcs_sha256(record)
    line = jcs(record) + b"\n"
    flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    handle = os.open(paths.events, flags)
    try:
        os.write(handle, line)
        os.fsync(handle)
    finally:
        os.close(handle)
    _atomic_write_json(paths.events_head, {"sequence": record["sequence"], "content_sha256": record["content_sha256"]})
    return record


def append_event(
    root: str | Path,
    event: dict[str, Any],
    *,
    now: Callable[[], str] | None = None,
    timeout: float = LOCK_TIMEOUT,
) -> dict[str, Any]:
    """Append one chained record to ``events.jsonl``.  Never creates the journal.

    Serialised by the same global write lock as ``orchestrator.json`` (plan
    invariant 11 speaks of a single "lock global"), so two processes can
    never read the same "last record" and assign it the same ``sequence``.

    ``event == COMMIT_EVENT`` is refused: minting that record is reserved
    for the internal commit path (:func:`_finalize_commit`), so a caller
    holding nothing but this public function can never forge the anchor
    that :func:`_check_revision_anchor` trusts.
    """
    if not isinstance(event, dict):
        _invalid("event must be a JSON object")
    if event.get("event") == COMMIT_EVENT:
        _invalid(f"{COMMIT_EVENT} is reserved for the internal snapshot-commit path")
    paths = store_paths(root)
    _validate_directory(paths.root)
    _validate_regular(paths.events)
    with orchestrator_lock(paths, timeout):
        return _append_record_locked(paths, event, now)


def _check_events_head(paths: StorePaths, last_record: dict[str, Any] | None) -> None:
    """§22/Core: the persisted witness of the journal's true tail, updated on
    every append (not only commits).  A pure tail-cut of *domain* events
    cannot be detected by chain validation alone (see the module note
    above) -- this closes it: the file's actual last record must match what
    was last durably appended."""
    info = _lstat(paths.events_head)
    if info is None:
        if last_record is not None:
            _invalid(f"event journal head missing: {paths.events_head}")
        return
    head = loads(_decode(_read_regular(paths.events_head), paths.events_head))
    if not isinstance(head, dict):
        _invalid(f"invalid event journal head: {paths.events_head}")
    if (
        last_record is None
        or head.get("sequence") != last_record.get("sequence")
        or head.get("content_sha256") != last_record.get("content_sha256")
    ):
        _invalid(f"event journal tail does not match the persisted head: {paths.events}")


def _validated_journal_records(paths: StorePaths) -> list[dict[str, Any]]:
    """Parse ``events.jsonl``, verify hash + sequence + chain, and verify the
    result's tail against the persisted events-head witness.  Assumes the
    file exists and is a validated regular file (callers check that)."""
    data = _read_regular(paths.events)
    records: list[dict[str, Any]] = []
    if data:
        text = _decode(data, paths.events)
        if not text.endswith("\n"):
            _invalid(f"truncated event journal: {paths.events}")
        expected_seq = 1
        expected_prev = EVENTS_GENESIS_SHA256
        for index, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                _invalid(f"blank record at line {index}: {paths.events}")
            record = loads(line)
            if not isinstance(record, dict):
                _invalid(f"record must be a JSON object at line {index}")
            digest = record.get("content_sha256")
            expected_digest = jcs_sha256({k: v for k, v in record.items() if k != "content_sha256"})
            if digest != expected_digest:
                _invalid(f"event hash mismatch at line {index}: {paths.events}")
            sequence = record.get("sequence")
            if type(sequence) is not int or isinstance(sequence, bool) or sequence != expected_seq:
                _invalid(
                    f"event journal sequence broken at line {index}: expected {expected_seq}, got {sequence!r}"
                )
            previous = record.get("previous_sha256")
            if previous != expected_prev:
                _invalid(f"event journal chain broken at line {index}: previous_sha256 mismatch")
            records.append(record)
            expected_seq += 1
            expected_prev = digest
    _check_events_head(paths, records[-1] if records else None)
    return records


def read_events(root: str | Path) -> list[dict[str, Any]]:
    """Parse and verify the journal.  Read-only: creates nothing."""
    paths = store_paths(root)
    _validate_directory(paths.root)
    _validate_regular(paths.events)
    return _validated_journal_records(paths)


def _check_receipt_consistency(paths: StorePaths, snapshot: Snapshot) -> None:
    """§22/Core "snapshot local divergente ... de receipt": a worktree
    receipt (:func:`_write_worktree_receipts`) is written on every commit
    that registers a work item and, unlike ``orchestrator.json``, is never
    rewritten by a snapshot rollback or a later work-item removal -- so a
    receipt naming a work item the current snapshot does not know about
    proves the snapshot diverges from already-durable history."""
    worktree_receipts = paths.receipts / "worktree"
    if _lstat(worktree_receipts) is None:
        return
    known = set(snapshot.document.get("work_items", {}))
    for entry in sorted(worktree_receipts.iterdir()):
        if entry.suffix != ".json":
            continue
        work_id = entry.stem
        if work_id not in known:
            _fail(STATE_DIVERGENCE, f"receipt exists for unknown work item: {work_id}")


def _check_revision_anchor(paths: StorePaths, snapshot: Snapshot) -> None:
    """Plan invariant 10 + §22/Core "snapshot local divergente ... do
    journal [ou] receipt".  Bidirectional, head-of-journal -- see the module
    note above the journal section for the full rationale.  Three checks,
    all required, plus the receipt cross-check:

    (i)   the snapshot's revision must equal the revision named by the
          journal's *last* commit record -- a point lookup that merely
          finds *some* matching commit record is not enough, since a
          byte-exact rollback to an earlier, once-legitimately-committed
          revision would still find one;
    (ii)  that equality check is symmetric, so a commit record naming a
          *later* revision than the snapshot's fails by name too, instead
          of the point lookup for the snapshot's own revision silently
          succeeding and the extra record being ignored;
    (iii) the document's own ``journal_head`` must match that same last
          commit record's ``{sequence, content_sha256}``, closing the loop
          from the snapshot side back to the journal, not only journal side
          to snapshot.
    """
    if _lstat(paths.events) is None:
        _invalid(f"event journal missing: {paths.events}")
    _validate_regular(paths.events)
    commit_records = [
        record for record in _validated_journal_records(paths) if record.get("event") == COMMIT_EVENT
    ]
    if not commit_records:
        _fail(STATE_DIVERGENCE, "journal has no journal-anchored commit record")
    last_commit = commit_records[-1]
    last_revision = last_commit.get("revision")
    if last_revision != snapshot.revision:
        _fail(
            STATE_DIVERGENCE,
            f"revision {snapshot.revision} is not the journal's last journal-anchored commit "
            f"(last journal-anchored revision is {last_revision!r})",
        )
    if last_commit.get("snapshot_sha256") != snapshot.content_sha256:
        _fail(
            STATE_DIVERGENCE,
            f"orchestrator content diverges from journal-anchored hash for revision {snapshot.revision}",
        )
    head = snapshot.document.get("journal_head")
    if (
        not isinstance(head, dict)
        or head.get("sequence") != last_commit.get("sequence")
        or head.get("record_sha256") != last_commit.get("content_sha256")
    ):
        _fail(STATE_DIVERGENCE, "snapshot's journal_head does not match the journal-anchored last commit record")
    _check_receipt_consistency(paths, snapshot)


def _commit_fields(snapshot_revision: int, snapshot_sha256: str) -> dict[str, Any]:
    return {"event": COMMIT_EVENT, "revision": snapshot_revision, "snapshot_sha256": snapshot_sha256}
