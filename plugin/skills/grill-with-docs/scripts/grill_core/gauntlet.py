#!/usr/bin/env python3
"""Strict FASE-001 Gauntlet activation primitives.

This module owns the project-scoped activation document.  It deliberately
receives the V3 guard modules from the public CLI instead of importing the
workspace back into the core, keeping the public JSON boundary acyclic.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


ASSETS = Path(__file__).resolve().parents[2] / "assets"
REGISTRY_PATH = ASSETS / "workflow-step-skills.json"
CATALOG_PATH = ASSETS / "claude-code-local-skills.catalog.json"
TRUSTED_CATALOGS_PATH = ASSETS / "workflow-trusted-catalogs.json"
CONFIG_NAME = "gauntlet.yaml"
CONFIG_SCHEMA = "grill-gauntlet/v1"
CONFIG_LOCK = ".gauntlet-config.lock"
CONFIG_LOCK_OWNER = ".owner"
WORKFLOW_STEPS = (
    "specify", "plan", "checklist", "tasks", "analyze", "agent-assign",
    "agent-execute", "converge", "verify", "review", "ship",
)
TIER_POLICY = {
    "specify": "large", "plan": "large", "checklist": "small", "tasks": "medium",
    "analyze": "large", "agent-assign": "large", "agent-execute": "medium",
    "converge": "medium", "verify": "medium", "review": "large", "ship": "large",
}
ADAPTER = "claude-code-skill/v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GauntletError(Exception):
    """Named, public-safe denial surfaced by ``grill_workspace``."""

    def __init__(self, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


@dataclass(frozen=True)
class ConfigLock:
    """A pinned configuration lock and the unforgeable owner token it created."""

    grill_fd: int
    owner_token: bytes


@dataclass(frozen=True)
class WorkItemLock:
    """The named work-item lock held below a pinned ``.grill`` descriptor."""

    locks_fd: int
    work_id: str
    owner_token: bytes


def _fail(code: str, message: str, **extra: Any) -> GauntletError:
    return GauntletError(code, message, **extra)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _public_code(code: str) -> str:
    return code if "-" in code else code.replace("_", "-")


def _write_all(fd: int, data: bytes) -> None:
    """Write every token byte or fail while the owner can still be cleaned up."""
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0 or written > len(data) - offset:
            raise OSError("short write while recording lock owner")
        offset += written


def _remove_partial_owner_at(lock_fd: int, owner: bytes) -> None:
    """Remove only the empty, partial, or complete token created by this owner."""
    try:
        recorded, _ = _read_regular_at(lock_fd, CONFIG_LOCK_OWNER)
        if recorded is not None and owner.startswith(recorded):
            os.unlink(CONFIG_LOCK_OWNER, dir_fd=lock_fd)
    except (GauntletError, OSError):
        pass


def _strict_json(data: bytes, *, code: str) -> dict[str, Any]:
    if data.startswith(b"\xef\xbb\xbf"):
        raise _fail(code, "JSON byte order mark is not allowed")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def reject_number(_: str) -> Any:
        raise ValueError("non-integer JSON number")

    try:
        parsed = json.loads(
            data.decode("utf-8"), object_pairs_hook=unique, parse_float=reject_number, parse_constant=reject_number
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise _fail(code, "configuration must be strict UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise _fail(code, "configuration must be a JSON object")
    return parsed


def _safe_directory_fd(root: Path) -> int:
    if not (
        hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW")
        and os.open in os.supports_dir_fd and os.mkdir in os.supports_dir_fd
    ):
        raise _fail("SAFE-PATH-UNAVAILABLE", "safe directory descriptors are unavailable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root_fd: int | None = None
    try:
        root_fd = os.open(root, flags)
        return os.open(".grill", flags, dir_fd=root_fd)
    except OSError as exc:
        raise _fail("SAFE-PATH-UNAVAILABLE", "could not safely open .grill") from exc
    finally:
        if root_fd is not None:
            os.close(root_fd)


def acquire_config_lock(root: Path) -> ConfigLock:
    """Acquire the config-wide lock with an owner token on its pinned parent."""
    grill_fd = _safe_directory_fd(root)
    lock_fd: int | None = None
    created = False
    owner: bytes | None = None
    try:
        os.mkdir(CONFIG_LOCK, 0o700, dir_fd=grill_fd)
        created = True
        flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
        lock_fd = os.open(CONFIG_LOCK, flags, dir_fd=grill_fd)
        owner = os.urandom(32)
        owner_fd = os.open(
            CONFIG_LOCK_OWNER,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=lock_fd,
        )
        try:
            _write_all(owner_fd, owner)
            os.fsync(owner_fd)
        finally:
            os.close(owner_fd)
    except FileExistsError as exc:
        if lock_fd is not None and owner is not None:
            _remove_partial_owner_at(lock_fd, owner)
        if lock_fd is not None:
            os.close(lock_fd)
            lock_fd = None
        if created:
            try:
                os.rmdir(CONFIG_LOCK, dir_fd=grill_fd)
            except OSError:
                pass
        os.close(grill_fd)
        raise _fail("CONFIG-LOCK-CONTENTION", "Gauntlet configuration lock already exists") from exc
    except OSError as exc:
        if lock_fd is not None and owner is not None:
            _remove_partial_owner_at(lock_fd, owner)
        if lock_fd is not None:
            os.close(lock_fd)
            lock_fd = None
        try:
            os.rmdir(CONFIG_LOCK, dir_fd=grill_fd)
        except OSError:
            pass
        os.close(grill_fd)
        raise _fail("SAFE-PATH-UNAVAILABLE", "could not create configuration lock") from exc
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
    return ConfigLock(grill_fd=grill_fd, owner_token=owner)


def release_config_lock(lock: ConfigLock) -> None:
    """Remove a config lock only when its on-disk owner still matches ours."""
    grill_fd = lock.grill_fd
    lock_fd: int | None = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
        lock_fd = os.open(CONFIG_LOCK, flags, dir_fd=grill_fd)
        before = os.fstat(lock_fd)
        owner, _ = _read_regular_at(lock_fd, CONFIG_LOCK_OWNER)
        if owner != lock.owner_token:
            return
        named = os.stat(CONFIG_LOCK, dir_fd=grill_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino):
            return
        os.unlink(CONFIG_LOCK_OWNER, dir_fd=lock_fd)
        named = os.stat(CONFIG_LOCK, dir_fd=grill_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino):
            return
        os.rmdir(CONFIG_LOCK, dir_fd=grill_fd)
    except OSError:
        # External intervention leaves a visible lock for a later fail-closed
        # command rather than risking deletion of a successor owner's lock.
        pass
    except GauntletError:
        pass
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(grill_fd)


def acquire_work_item_lock(grill_fd: int, work_id: str) -> WorkItemLock:
    """Acquire the shared named work-item lock without reopening ``.grill``."""
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    locks_fd: int | None = None
    lock_fd: int | None = None
    lock_name = f"{work_id}.lock"
    acquired = False
    created = False
    owner: bytes | None = None
    try:
        locks_fd = os.open("locks", flags, dir_fd=grill_fd)
        os.mkdir(lock_name, 0o700, dir_fd=locks_fd)
        created = True
        lock_fd = os.open(lock_name, flags, dir_fd=locks_fd)
        owner = os.urandom(32)
        owner_fd = os.open(
            CONFIG_LOCK_OWNER,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=lock_fd,
        )
        try:
            _write_all(owner_fd, owner)
            os.fsync(owner_fd)
        finally:
            os.close(owner_fd)
        acquired = True
        return WorkItemLock(locks_fd=locks_fd, work_id=work_id, owner_token=owner)
    except FileExistsError as exc:
        if lock_fd is not None and owner is not None:
            _remove_partial_owner_at(lock_fd, owner)
        if created and locks_fd is not None:
            try:
                os.rmdir(lock_name, dir_fd=locks_fd)
            except OSError:
                pass
        raise _fail("WORK-ITEM-LOCK-CONTENTION", "work item lock already exists", work_id=work_id) from exc
    except OSError as exc:
        if lock_fd is not None and owner is not None:
            _remove_partial_owner_at(lock_fd, owner)
        if created and locks_fd is not None:
            try:
                os.rmdir(lock_name, dir_fd=locks_fd)
            except OSError:
                pass
        raise _fail("SAFE-PATH-UNAVAILABLE", "could not safely acquire work item lock", work_id=work_id) from exc
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        # Ownership transfers only on a successful return.
        if locks_fd is not None and not acquired:
            os.close(locks_fd)


def release_work_item_lock(lock: WorkItemLock) -> None:
    """Release only the work-item lock whose on-disk token is still ours."""
    lock_fd: int | None = None
    lock_name = f"{lock.work_id}.lock"
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
        lock_fd = os.open(lock_name, flags, dir_fd=lock.locks_fd)
        before = os.fstat(lock_fd)
        owner, _ = _read_regular_at(lock_fd, CONFIG_LOCK_OWNER)
        if owner != lock.owner_token:
            return
        named = os.stat(lock_name, dir_fd=lock.locks_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino):
            return
        os.unlink(CONFIG_LOCK_OWNER, dir_fd=lock_fd)
        named = os.stat(lock_name, dir_fd=lock.locks_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino):
            return
        os.rmdir(lock_name, dir_fd=lock.locks_fd)
    except (GauntletError, OSError):
        pass
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(lock.locks_fd)


def open_work_item_fd(grill_fd: int, work_id: str) -> int:
    """Open one work-item below the same pinned ``.grill`` descriptor."""
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    work_items_fd: int | None = None
    try:
        work_items_fd = os.open("work-items", flags, dir_fd=grill_fd)
        return os.open(work_id, flags, dir_fd=work_items_fd)
    except OSError as exc:
        raise _fail("SAFE-PATH-UNAVAILABLE", "could not safely open work item", work_id=work_id) from exc
    finally:
        if work_items_fd is not None:
            os.close(work_items_fd)


def _read_regular_at(directory_fd: int, name: str) -> tuple[bytes | None, int | None]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        raise _fail("SAFE-PATH-UNAVAILABLE", "configuration path is unsafe") from exc
    try:
        mode = os.fstat(descriptor).st_mode
        if not stat.S_ISREG(mode):
            raise _fail("SAFE-PATH-UNAVAILABLE", "configuration is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks), stat.S_IMODE(mode)
    finally:
        os.close(descriptor)


def _validate_worker_count(value: Any) -> int:
    if type(value) is not int or not 1 <= value <= 5:
        raise _fail("INVALID-ARGUMENTS", "--max-workers must be an integer from 1 through 5")
    return value


def _validate_record(work_id: str, record: Any) -> None:
    if not isinstance(record, dict) or set(record) != {
        "work_item_id", "work_item", "workflow", "runtime", "catalog", "limits", "tier_policy"
    }:
        raise _fail("GAUNTLET-CONFIG-INVALID", "activation record has an invalid schema", work_id=work_id)
    if record["work_item_id"] != work_id:
        raise _fail("GAUNTLET-CONFIG-INVALID", "activation map key differs from record work item", work_id=work_id)
    work_item = record["work_item"]
    workflow = record["workflow"]
    runtime = record["runtime"]
    catalog = record["catalog"]
    limits = record["limits"]
    tiers = record["tier_policy"]
    if not isinstance(work_item, dict) or set(work_item) != {"document_sha256"} or not isinstance(work_item["document_sha256"], str) or not SHA256_RE.fullmatch(work_item["document_sha256"]):
        raise _fail("GAUNTLET-CONFIG-INVALID", "activation work item identity is invalid", work_id=work_id)
    if not isinstance(workflow, dict) or set(workflow) != {"version", "sha256", "registry_sha256"} or workflow.get("version") != "v3" or not isinstance(workflow.get("sha256"), str) or not SHA256_RE.fullmatch(workflow["sha256"]) or not isinstance(workflow.get("registry_sha256"), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", workflow["registry_sha256"]):
        raise _fail("GAUNTLET-CONFIG-INVALID", "activation workflow identity is invalid", work_id=work_id)
    if runtime != {"id": "claude", "adapter": ADAPTER}:
        raise _fail("GAUNTLET-CONFIG-INVALID", "activation runtime is invalid", work_id=work_id)
    if not isinstance(catalog, dict) or set(catalog) != {"id", "document_sha256", "resolution_sha256", "trusted_asset_document_sha256"} or not isinstance(catalog.get("id"), str) or not isinstance(catalog.get("document_sha256"), str) or not SHA256_RE.fullmatch(catalog["document_sha256"]) or not isinstance(catalog.get("resolution_sha256"), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", catalog["resolution_sha256"]) or not isinstance(catalog.get("trusted_asset_document_sha256"), str) or not SHA256_RE.fullmatch(catalog["trusted_asset_document_sha256"]):
        raise _fail("GAUNTLET-CONFIG-INVALID", "activation catalog identity is invalid", work_id=work_id)
    if not isinstance(limits, dict) or set(limits) != {"max_workers", "stall_minutes"} or type(limits.get("max_workers")) is not int or not 1 <= limits["max_workers"] <= 5 or limits.get("stall_minutes") != 15:
        raise _fail("GAUNTLET-CONFIG-INVALID", "activation limits are invalid", work_id=work_id)
    if not isinstance(tiers, dict) or set(tiers) != {"adapter", "minimum_by_step", "supplemental", "promotions"} or tiers.get("adapter") != ADAPTER or tiers.get("minimum_by_step") != TIER_POLICY or tiers.get("supplemental") != {"markdown-maintenance": "small"} or tiers.get("promotions") != []:
        raise _fail("GAUNTLET-CONFIG-INVALID", "activation tier policy is invalid", work_id=work_id)


def _read_config(directory_fd: int) -> tuple[dict[str, Any], bytes | None, int | None]:
    raw, mode = _read_regular_at(directory_fd, CONFIG_NAME)
    if raw is None:
        return {"schema": CONFIG_SCHEMA, "activations": {}}, None, None
    document = _strict_json(raw, code="GAUNTLET-CONFIG-INVALID")
    if set(document) != {"schema", "activations"} or document.get("schema") != CONFIG_SCHEMA or not isinstance(document.get("activations"), dict):
        raise _fail("GAUNTLET-CONFIG-INVALID", "Gauntlet configuration has an invalid schema")
    for work_id, record in document["activations"].items():
        if not isinstance(work_id, str) or not work_id:
            raise _fail("GAUNTLET-CONFIG-INVALID", "activation key is invalid")
        _validate_record(work_id, record)
    return document, raw, mode


def _skill_error_code(error: Any, step_skills: Any) -> str:
    if getattr(error, "code", None) == getattr(step_skills, "STALE_SKILL_RESOLUTION", "STALE_SKILL_RESOLUTION"):
        return "STALE-SKILL-RESOLUTION"
    reason = getattr(error, "reason", "")
    known = {
        "INVALID_DIGEST", "INVALID_RESOLVER_VERSION", "INVALID_VERSION", "UNKNOWN_RUNTIME", "UNKNOWN_STEP",
        "RUNTIME_UNSUPPORTED", "RUNTIME_ENTRYPOINT_UNPROVEN", "ADAPTER_MISMATCH", "ENTRYPOINT_ABSENT",
        "ENTRYPOINT_KIND_MISMATCH", "AMBIGUOUS_ENTRYPOINT", "NO_NATIVE_ENTRYPOINT", "SOURCE_REF_MISMATCH",
        "VERSION_BELOW_MINIMUM", "REGISTRY_SHA256_MISMATCH", "SKILL_NOT_PUBLISHED", "SKILL_CHANGED_AFTER_PREFLIGHT",
        "PINNED_RESOLUTION_INVALID", "PINNED_RESOLUTION_TAMPERED", "CATALOG_ABSENT", "CATALOG_CONTENT_MISMATCH",
        "CATALOG_DIGEST", "CATALOG_ENTRIES", "CATALOG_ENTRY_INVALID", "CATALOG_ID", "CATALOG_INVALID",
        "CATALOG_MISMATCH", "CATALOG_RUNTIME", "CATALOG_RUNTIME_MISMATCH", "CATALOG_SCHEMA", "CATALOG_SHA256_MISMATCH",
        "UNTRUSTED_CATALOG", "TRUSTED_CATALOGS_INVALID", "TRUSTED_CATALOGS_SCHEMA", "TRUSTED_CATALOGS_UNREADABLE",
        "TRUSTED_CATALOGS_WORKFLOW_VERSION", "REGISTRY_ADAPTER", "REGISTRY_ALLOWED_ENTRYPOINTS", "REGISTRY_CATALOG_ID",
        "REGISTRY_DUPLICATE_ENTRYPOINT", "REGISTRY_DUPLICATE_SKILL_ID", "REGISTRY_ENTRYPOINT", "REGISTRY_ENTRYPOINT_KIND",
        "REGISTRY_HUMAN_AUTHORIZATION", "REGISTRY_INVALID", "REGISTRY_PROPOSED_SKILL_ID", "REGISTRY_RESOLUTIONS",
        "REGISTRY_RESOLUTION_INVALID", "REGISTRY_RUNTIMES", "REGISTRY_SCHEMA", "REGISTRY_SKILL_ID", "REGISTRY_SOURCE_REF",
        "REGISTRY_STEPS", "REGISTRY_STEP_INVALID", "REGISTRY_STEP_NOT_REQUIRED", "REGISTRY_STEP_SET", "REGISTRY_UNREADABLE",
        "REGISTRY_UNRESOLVED_REASON", "REGISTRY_VERSION", "REGISTRY_WORKFLOW_VERSION",
    }
    return _public_code(reason) if reason in known else "BLOCKED-CAPABILITY"


def current_activation(
    *, root: Path, work_id: str, item_dir_fd: int, workflow_bytes: bytes, workflow_text: str,
    workflow_v3: Any, work_item_v3: Any, step_skills: Any, work_item_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Prove all immutable inputs required to create or use an activation."""
    try:
        gate = workflow_v3.execution_gate(workflow_text)
    except workflow_v3.Failure as exc:
        code = getattr(workflow_v3, "CLI_CODE_ALIASES", {}).get(exc.code, _public_code(exc.code))
        raise _fail(code, "workflow eligibility proof failed") from exc
    if gate.status != "OK":
        code = getattr(workflow_v3, "CLI_CODE_ALIASES", {}).get(gate.code, _public_code(gate.code or "WORKFLOW_INCOMPATIBLE"))
        raise _fail(code, "workflow is not eligible for Gauntlet activation")
    if work_item_bytes is None:
        try:
            metadata, document_sha256 = work_item_v3.read_document_with_digest_at(item_dir_fd)
            immutable = work_item_v3.require_v3(metadata, "gauntlet-init", work_id)
        except work_item_v3.WorkItemError as exc:
            raise _fail(_public_code(exc.code), "work item eligibility proof failed", work_id=work_id) from exc
    else:
        # The status projection supplies a raw no-follow snapshot.  Parse that
        # exact snapshot rather than opening the mutable pathname a second
        # time, so its STALE comparison and eligibility proof cannot disagree.
        try:
            metadata = json.loads(work_item_bytes.decode("utf-8"))
        except UnicodeError as exc:
            raise _fail("INVALID-UTF8", "work item eligibility proof failed", work_id=work_id) from exc
        except json.JSONDecodeError as exc:
            raise _fail("UNEXPECTED-INPUT", "work item eligibility proof failed", work_id=work_id) from exc
        try:
            immutable = work_item_v3.require_v3(metadata, "gauntlet-init", work_id)
        except work_item_v3.WorkItemError as exc:
            raise _fail(_public_code(exc.code), "work item eligibility proof failed", work_id=work_id) from exc
        document_sha256 = _sha256(work_item_bytes)
    workflow_sha256 = _sha256(workflow_bytes)
    if immutable["workflow"].get("sha256") != workflow_sha256:
        raise _fail("WORK-ITEM-WORKFLOW-DIVERGENT", "work item is not bound to the current workflow", work_id=work_id)
    try:
        registry_bytes = REGISTRY_PATH.read_bytes()
    except OSError as exc:
        raise _fail("REGISTRY-UNREADABLE", "shipped workflow registry is unavailable") from exc
    try:
        catalog_bytes = CATALOG_PATH.read_bytes()
    except OSError as exc:
        raise _fail("CATALOG-ABSENT", "shipped Claude catalog is unavailable") from exc
    try:
        catalog = step_skills.parse_strict(catalog_bytes)
        registry_sha256 = step_skills.registry_sha256(registry_bytes)
        resolutions, trusted_bytes = step_skills.resolve_shipped_workflow_skills(
            WORKFLOW_STEPS, "claude", registry_sha256, registry=registry_bytes, catalog=catalog
        )
    except step_skills.SkillResolutionError as exc:
        raise _fail(_skill_error_code(exc, step_skills), "Claude capability proof failed") from exc
    except Exception as exc:
        raise _fail("CATALOG-INVALID", "shipped Claude catalog is invalid") from exc
    if len(resolutions) != len(WORKFLOW_STEPS) or {entry["adapter"] for entry in resolutions} != {ADAPTER}:
        raise _fail("RUNTIME-ENTRYPOINT-UNPROVEN", "Claude does not prove every canonical entrypoint")
    catalog_id = catalog.get("catalog_id") if isinstance(catalog, dict) else None
    catalog_sha256 = catalog.get("catalog_sha256") if isinstance(catalog, dict) else None
    if not isinstance(catalog_id, str) or not isinstance(catalog_sha256, str):
        raise _fail("CATALOG-INVALID", "shipped Claude catalog has no identity")
    return {
        "work_item_id": work_id,
        "work_item": {"document_sha256": document_sha256},
        "workflow": {"version": "v3", "sha256": workflow_sha256, "registry_sha256": registry_sha256},
        "runtime": {"id": "claude", "adapter": ADAPTER},
        "catalog": {
            "id": catalog_id,
            "document_sha256": _sha256(catalog_bytes),
            "resolution_sha256": catalog_sha256,
            "trusted_asset_document_sha256": _sha256(trusted_bytes),
        },
    }


def activate(
    *, root: Path, work_id: str, max_workers: Any, item_dir_fd: int, grill_fd: int,
    workflow_bytes: bytes, workflow_text: str, workflow_v3: Any, work_item_v3: Any, step_skills: Any,
) -> str:
    """Create or reuse an activation while the caller owns both write locks."""
    workers = _validate_worker_count(max_workers)
    proof = current_activation(
        root=root, work_id=work_id, item_dir_fd=item_dir_fd, workflow_bytes=workflow_bytes,
        workflow_text=workflow_text, workflow_v3=workflow_v3, work_item_v3=work_item_v3, step_skills=step_skills,
    )
    record = {
        **proof,
        "limits": {"max_workers": workers, "stall_minutes": 15},
        "tier_policy": {
            "adapter": ADAPTER, "minimum_by_step": dict(TIER_POLICY),
            "supplemental": {"markdown-maintenance": "small"}, "promotions": [],
        },
    }
    _validate_record(work_id, record)
    document, baseline, mode = _read_config(grill_fd)
    existing = document["activations"].get(work_id)
    if existing is not None:
        if existing == record:
            return "REUSED"
        raise _fail(
            "ACTIVATION-CONFLICT", "existing activation differs from current request", work_id=work_id,
            remediation="Use the existing activation or create a new work item; activation records are immutable.",
        )
    document["activations"][work_id] = record
    data = (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    current, _ = _read_regular_at(grill_fd, CONFIG_NAME)
    if current != baseline:
        raise _fail("CONFIG-CHANGED", "Gauntlet configuration changed during activation")
    try:
        work_item_v3._atomic_replace_at(grill_fd, CONFIG_NAME, data, mode=mode if mode is not None else 0o600)
    except work_item_v3.WorkItemError as exc:
        raise _fail(_public_code(exc.code), "could not atomically write Gauntlet configuration") from exc
    return "ACTIVATED"


def open_config_directory(root: Path) -> int:
    """Open the read-only Gauntlet configuration parent without a lock."""
    return _safe_directory_fd(root)


def _activation_is_stale(
    record: Mapping[str, Any], *, item_dir_fd: int, workflow_bytes: bytes,
) -> tuple[bool, bytes | None]:
    """Compare available raw identities before attempting a fresh proof.

    This deliberately does not require the current proof to be valid.  A
    changed work-item digest must be projected as STALE even when a separate
    workflow or catalog error would otherwise make the fresh proof BLOCKED.
    """
    try:
        # Identity staleness is about the raw immutable document.  Parsing it
        # first would incorrectly hide a changed-but-malformed document behind
        # a proof failure, so read bytes via the same no-follow FD boundary.
        item_bytes, _ = _read_regular_at(item_dir_fd, "WORK-ITEM.json")
    except GauntletError:
        # Do not retry an unsafe or failed snapshot through a second pathname
        # read.  The public projection maps this to STATUS/BLOCKED.
        raise
    except Exception as exc:
        raise _fail("SAFE-PATH-UNAVAILABLE", "could not capture work item identity") from exc
    if item_bytes is None or record["work_item"]["document_sha256"] != _sha256(item_bytes):
        return True, item_bytes
    try:
        registry_bytes = REGISTRY_PATH.read_bytes()
        catalog_bytes = CATALOG_PATH.read_bytes()
        trusted_bytes = TRUSTED_CATALOGS_PATH.read_bytes()
    except Exception:
        return False, item_bytes
    workflow = record["workflow"]
    catalog = record["catalog"]
    return any((
        workflow["sha256"] != _sha256(workflow_bytes),
        workflow["registry_sha256"] != "sha256:" + _sha256(registry_bytes),
        catalog["document_sha256"] != _sha256(catalog_bytes),
        catalog["trusted_asset_document_sha256"] != _sha256(trusted_bytes),
    )), item_bytes


def activation_state(
    *, root: Path, work_id: str, item_dir_fd: int, grill_fd: int, workflow_bytes: bytes,
    workflow_text: str, workflow_v3: Any, work_item_v3: Any, step_skills: Any,
) -> tuple[str, str | None]:
    """Return the closed read-only activation projection and optional reason."""
    document, _, _ = _read_config(grill_fd)
    record = document["activations"].get(work_id)
    work_item_bytes: bytes | None = None
    if record is not None:
        stale, work_item_bytes = _activation_is_stale(
            record, item_dir_fd=item_dir_fd, workflow_bytes=workflow_bytes,
        )
        if stale:
            return "STALE", "IDENTITY-STALE"
    try:
        proof = current_activation(
            root=root, work_id=work_id, item_dir_fd=item_dir_fd, workflow_bytes=workflow_bytes,
            workflow_text=workflow_text, workflow_v3=workflow_v3, work_item_v3=work_item_v3,
            step_skills=step_skills, work_item_bytes=work_item_bytes,
        )
    except GauntletError as exc:
        return "BLOCKED", exc.code
    if record is None:
        return "ELIGIBLE", None
    identity = {key: proof[key] for key in ("work_item_id", "work_item", "workflow", "runtime", "catalog")}
    if any(record[key] != value for key, value in identity.items()):
        return "STALE", "IDENTITY-STALE"
    return "ACTIVATED", None
