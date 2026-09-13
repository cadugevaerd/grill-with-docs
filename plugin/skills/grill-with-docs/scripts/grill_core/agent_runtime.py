"""Observed runtime boundary; caller supplied JSON is never evidence."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable

_HEX = re.compile(r"^[0-9a-f]{64}$")

class RuntimeError(ValueError): pass

def _fail(message: str) -> None: raise RuntimeError(message)

def _digest(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()

def _identity(value: dict[str, Any]) -> tuple[Any, ...]:
    keys = ("adapter", "provider", "handle", "incarnation", "runtime_instance", "host", "owner_dispatch")
    if any(not value.get(key) for key in keys): _fail("runtime identity incomplete")
    return tuple(value[key] for key in keys)

def validate_observation(value: Any, raw: bytes | None = None) -> dict[str, Any]:
    if not isinstance(value, dict): _fail("observation must be object")
    required = {"schema", "adapter", "provider", "handle", "incarnation", "runtime_instance", "host", "owner_dispatch", "source_ref", "source_sha256", "requested_model", "requested_effort", "effective_model", "effective_effort", "resolved_model_id", "activity", "close"}
    if set(value) != required or value["schema"] != "grill-agent-observation/v1": _fail("invalid observation keys")
    _identity(value)
    if value["adapter"] not in {"orca", "codex", "claude"}:
        _fail("unknown runtime adapter")
    if not isinstance(value["source_ref"], str) or not value["source_ref"] or not isinstance(value["source_sha256"], str) or not _HEX.fullmatch(value["source_sha256"]): _fail("invalid observation source")
    if raw is not None and _digest(raw) != value["source_sha256"]: _fail("observation digest mismatch")
    if value["activity"] not in {"active", "idle", "exited", "unknown"} or value["close"] not in {"not_requested", "pending", "closed", "unknown", "preserved"}: _fail("invalid observation state")
    for key in ("requested_model", "requested_effort", "effective_model", "effective_effort", "resolved_model_id"):
        if value[key] is not None and (not isinstance(value[key], str) or not value[key]): _fail(f"invalid {key}")
    return value

@dataclass
class RuntimeBoundary:
    """Known adapter seams. Probe/read-back must return bytes actually observed."""
    probe: Callable[[], tuple[bytes, bytes]]
    observe: Callable[[], tuple[bytes, bytes]]
    request_close: Callable[[], tuple[bytes, bytes]]
    read_after_close: Callable[[], tuple[bytes, bytes]]

    def _read(self, fn: Callable[[], tuple[bytes, bytes]]) -> dict[str, Any]:
        pair = fn()
        if not isinstance(pair, tuple) or len(pair) != 2 or not all(isinstance(x, bytes) for x in pair): _fail("adapter did not return source and observation bytes")
        source, raw = pair
        try: value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise RuntimeError("adapter observation is invalid JSON") from exc
        return validate_observation(value, source)

    def verified(self, requested_model: str, requested_effort: str) -> dict[str, Any]:
        observation = self._read(self.probe)
        if observation["effective_model"] != requested_model or observation["effective_effort"] != requested_effort or observation["resolved_model_id"] is None:
            _fail("SPECIALIST-CAPABILITY-UNPROVEN")
        return observation

    def close(self, expected: dict[str, Any]) -> dict[str, Any]:
        expected = validate_observation(expected)
        requested = self._read(self.request_close)
        if _identity(requested) != _identity(expected): _fail("runtime close identity diverged")
        observed = self._read(self.read_after_close)
        if _identity(observed) != _identity(expected) or observed["close"] != "closed" or observed["activity"] not in {"idle", "exited"}:
            _fail("runtime close unconfirmed")
        return observed
