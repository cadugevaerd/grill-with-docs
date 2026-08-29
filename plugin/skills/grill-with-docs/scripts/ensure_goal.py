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


def resolve_goal(root_argument: str | Path) -> GoalResult:
    """Materialise or validate ``goal.md`` and return the decision without
    printing (contracts/materialization-cli.md).

    Covers the creation path (FR-001) and the reuse path: existing document
    carrying the ``v1`` marker with ``compatible() is True`` returns
    ``REUSED`` without writing anything.

    The ``PRESERVED`` branch -- existing document with no marker (``human
    document``), with another version's marker (``managed version
    mismatch``), or with a ``v1`` marker that fails ``compatible()``
    (``incompatible goal``) -- performs no write, no rename and no auxiliary
    file of any kind (FR-003, FR-006, FR-007). An existing-but-empty document
    is classified the same way, never treated as absent (Edge Case).
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

        if target.exists():
            if target.is_dir():
                return GoalResult("BLOCKED", None, b"", "unsafe target")
            content, text = read_regular(target)
            version = goal_document.managed_version(text)
            if version == goal_document.VERSION and goal_document.compatible(text):
                return GoalResult("REUSED", target, content, None)
            # Three named PRESERVED reasons (FR-003, FR-006). An empty
            # document has no marker on its first line, so it falls into
            # "human document" here -- existing-but-empty is PRESERVED, not
            # treated as absent (Edge Case), because this branch runs before
            # the creation path below ever sees the target.
            if version is None:
                reason = "human document"
            elif version != goal_document.VERSION:
                reason = "managed version mismatch"
            else:
                reason = "incompatible goal"
            return GoalResult("PRESERVED", target, content, reason)

        template_content, template_text = read_regular(goal_document.TEMPLATE)
        if (
            goal_document.managed_version(template_text) != goal_document.VERSION
            or not goal_document.compatible(template_text)
        ):
            return GoalResult("BLOCKED", None, b"", "invalid bundled template")
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
