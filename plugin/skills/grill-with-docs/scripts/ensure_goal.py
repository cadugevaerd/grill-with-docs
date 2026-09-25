#!/usr/bin/env python3
"""Materialise or validate ``goal.md`` at a project root (stdlib only).

Mirrors ``ensure_workflow.py``'s shape: a pure decision function
(``resolve_goal``) that an embedding command (``init``) can consume directly,
plus a CLI wrapper that owns stdout's single-line JSON contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve()

# The SSOT this module never redeclares any constant of (FR-009, FR-010).
# ``ensure_goal.py`` lives directly inside ``scripts/``, alongside the
# ``grill_core`` package, so a plain package import resolves it whenever
# ``scripts/`` is on ``sys.path`` -- true for direct invocation
# (``sys.path[0]`` is the script's own directory) and for any caller that
# has put ``scripts/`` on ``sys.path`` before importing this module.
from grill_core import goal_document


class GoalResult(NamedTuple):
    """Decision taken about ``goal.md``, decoupled from how it is reported."""

    status: str
    path: Path | None
    content: bytes
    reason: str | None


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def git_root(path: Path) -> Path | None:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return Path(output.strip()).resolve()


def read_regular(path: Path) -> tuple[bytes, str]:
    """Open one regular file without following a final-component symlink (FR-008).

    The object verified (``fstat`` of the already-open descriptor) is the
    object read -- no window between checking and opening.
    """
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    content = b"".join(chunks)
    return content, content.decode("utf-8")


def atomic_create(target: Path, content: bytes) -> bool:
    """Create target exactly once; never replace an existing directory entry
    (FR-002, FR-015).

    The no-clobber guarantee is structural, not a checked-then-written race:
    ``os.link`` refuses an existing destination in the kernel itself.
    """
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
            created = True
        except FileExistsError:
            created = False
        try:
            directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            directory_descriptor = os.open(target.parent, directory_flags)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError:
            # Directory fsync is unavailable on some supported filesystems.
            pass
        return created
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def atomic_replace(target: Path, content: bytes) -> None:
    """Replace target's bytes in one rename; readers see the old or the new file, never half."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def resolve_goal(root_argument: str | Path) -> GoalResult:
    """Materialise or validate ``goal.md`` and return the decision without
    printing (contracts/materialization-cli.md).

    goal.md is plugin-owned: every ``init`` leaves a managed document equal to
    the bundled template. Absent -> ``CREATED``; managed (any marker in
    ``KNOWN_VERSIONS``) and already identical -> ``REUSED``; managed but
    older, edited or mutilated -> rewritten atomically, ``UPDATED`` with the
    previous version as reason.

    ``PRESERVED`` -- no write, no rename, no auxiliary file -- is kept only
    where rewriting would destroy something the plugin does not own: a
    document with no marker (``human document``, including an empty one,
    never treated as absent) and a marker newer than this build
    (``newer managed version``), which a downgrade must not clobber.
    """
    candidate = Path(root_argument).expanduser()
    if not candidate.is_dir():
        return GoalResult("BLOCKED", None, b"", "ROOT must be existing Git top-level")
    root = candidate.resolve()
    if git_root(root) != root:
        return GoalResult("BLOCKED", None, b"", "ROOT must be existing Git top-level")

    target = root / "goal.md"
    try:
        if target.is_symlink() or target.resolve(strict=False).parent != root:
            return GoalResult("BLOCKED", None, b"", "unsafe target")

        # Decided once, from the first read: a concurrent init may create the
        # file between two exists() calls, and then it is that init's to write.
        existing: bytes | None = None
        if target.exists():
            if target.is_dir():
                return GoalResult("BLOCKED", None, b"", "unsafe target")
            existing, text = read_regular(target)
            content = existing
            version = goal_document.managed_version(text)
            # An empty document has no marker on its first line, so it falls
            # into "human document" -- PRESERVED, never treated as absent.
            if version is None:
                return GoalResult("PRESERVED", target, content, "human document")
            if goal_document.is_newer(version):
                return GoalResult("PRESERVED", target, content, "newer managed version")

        template_content, template_text = read_regular(goal_document.TEMPLATE)
        if (
            goal_document.managed_version(template_text) != goal_document.VERSION
            or not goal_document.compatible(template_text)
        ):
            return GoalResult("BLOCKED", None, b"", "invalid bundled template")
        if existing is not None:
            if existing == template_content:
                return GoalResult("REUSED", target, content, None)
            atomic_replace(target, template_content)
            content, text = read_regular(target)
            if content != template_content:
                return GoalResult("BLOCKED", None, b"", "read-back validation failed")
            return GoalResult("UPDATED", target, content, f"from {version}")
        created = atomic_create(target, template_content)

        if target.is_symlink() or target.resolve(strict=False).parent != root:
            return GoalResult("BLOCKED", None, b"", "unsafe target after create")
        content, text = read_regular(target)
        version = goal_document.managed_version(text)
        if (version and version != goal_document.VERSION) or not goal_document.compatible(text):
            return GoalResult("BLOCKED", None, b"", "read-back validation failed")
        return GoalResult("CREATED" if created else "REUSED", target, content, None)
    except UnicodeError:
        return GoalResult("BLOCKED", None, b"", "invalid UTF-8 goal")
    except OSError as error:
        return GoalResult("BLOCKED", None, b"", f"filesystem-error:{type(error).__name__}")


def emit(status: str, path: Path | None = None, content: bytes | None = None, *, reason: str | None = None) -> None:
    payload: dict[str, str] = {"status": status}
    if reason is not None:
        payload["reason"] = reason
    if path is not None and content is not None:
        payload["path"] = str(path)
        payload["sha256"] = digest(content)
        try:
            version = goal_document.managed_version(content.decode("utf-8"))
        except UnicodeError:
            version = None
        if version is not None:
            payload["version"] = version
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def ensure(root_argument: str) -> int:
    result = resolve_goal(root_argument)
    if result.status == "BLOCKED":
        emit("BLOCKED", reason=result.reason or "unknown")
        return 2
    emit(result.status, result.path, result.content, reason=result.reason)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ensure", required=True)
    arguments = parser.parse_args(argv)
    return ensure(arguments.ensure)


if __name__ == "__main__":
    raise SystemExit(main())
