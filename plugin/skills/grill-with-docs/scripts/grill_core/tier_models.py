#!/usr/bin/env python3
"""Tier -> model binding for dispatched actors (ADR-0001, ADR-0013).

Stdlib only, no network. Reads one versioned asset and answers a single
question: given a runtime, a node tier and the class of actor being
dispatched, which concrete model is that, and is dispatching it allowed?

Why an asset and not a prompt line
----------------------------------
"Do not use a frontier model" written into a worker's brief is an instruction,
and an instruction is not a control. The binding makes the answer *derived*:
``declare_worker`` resolves the model from the node's tier and never accepts a
``--model`` from its caller, a frontier model for actor class ``worker`` raises
before any worktree exists, and the resolved model is written into the worker
record, so which model ran which node is a durable fact rather than session
memory.

The tier itself stays abstract in the rest of the core -- ``gauntlet`` and
``gauntlet_runs`` keep speaking small/medium/large. This module is the only
place a tier becomes a model id, so adding a runtime is one asset edit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ASSETS = Path(__file__).resolve().parents[2] / "assets"
BINDING_PATH = ASSETS / "workflow-tier-models.json"
BINDING_REF = "assets/workflow-tier-models.json"
SCHEMA = "workflow-tier-models/v1"

_DOCUMENT_KEYS = frozenset(
    {"schema", "workflow_version", "binding_version", "tier_order", "actor_classes", "runtimes"}
)
_RESOLVED_RUNTIME_KEYS = frozenset({"resolved", "adapter", "selection", "tiers"})
_UNRESOLVED_RUNTIME_KEYS = frozenset({"resolved", "unresolved_reason"})
_TIER_KEYS = frozenset({"model", "frontier"})
#: A placeholder that survived into a resolved runtime means the asset was
#: shipped half-filled. Falling back to a default here would silently dispatch
#: some other model, so it is a refusal instead.
_PLACEHOLDER_PREFIX = "__"


class TierModelError(Exception):
    """Named, public-safe denial, mirroring ``gauntlet.GauntletError``."""

    def __init__(self, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


def _fail(code: str, message: str, **extra: Any) -> None:
    raise TierModelError(code, message, **extra)


def binding_sha256(path: Path | None = None) -> str:
    """SHA-256 over the literal bytes on disk, for pinning."""
    target = Path(path) if path is not None else BINDING_PATH
    return "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()


def load_binding(path: Path | None = None) -> dict[str, Any]:
    """Parse and fully validate the binding document.

    Closed key sets throughout: an unknown key is a malformed asset, not a
    forward-compatible extension. A binding is the thing that decides which
    model runs, so it fails closed on anything it does not recognise.
    """
    target = Path(path) if path is not None else BINDING_PATH
    try:
        document = json.loads(target.read_bytes())
    except OSError:
        _fail("BINDING-UNAVAILABLE", "tier model binding is unavailable", ref=str(target))
    except ValueError:
        _fail("BINDING-MALFORMED", "tier model binding is not valid JSON")
    if not isinstance(document, dict) or set(document) != _DOCUMENT_KEYS:
        _fail("BINDING-MALFORMED", "tier model binding document is invalid")
    if document["schema"] != SCHEMA:
        _fail("BINDING-MALFORMED", "tier model binding schema is unrecognized")
    order = document["tier_order"]
    if not isinstance(order, list) or not order or len(set(order)) != len(order):
        _fail("BINDING-MALFORMED", "tier model binding tier order is invalid")

    actors = document["actor_classes"]
    if not isinstance(actors, dict) or not actors:
        _fail("BINDING-MALFORMED", "tier model binding actor classes are invalid")
    for name, actor in actors.items():
        if not isinstance(actor, dict) or set(actor) != {"frontier_allowed"}:
            _fail("BINDING-MALFORMED", f"actor class is invalid: {name}")
        if actor["frontier_allowed"] not in (True, False):
            _fail("BINDING-MALFORMED", f"actor class frontier flag is invalid: {name}")

    runtimes = document["runtimes"]
    if not isinstance(runtimes, dict) or not runtimes:
        _fail("BINDING-MALFORMED", "tier model binding runtimes are invalid")
    for name, runtime in runtimes.items():
        if not isinstance(runtime, dict):
            _fail("BINDING-MALFORMED", f"runtime is invalid: {name}")
        if runtime.get("resolved") is False:
            if set(runtime) != _UNRESOLVED_RUNTIME_KEYS or not runtime["unresolved_reason"]:
                _fail("BINDING-MALFORMED", f"unresolved runtime is invalid: {name}")
            continue
        if set(runtime) != _RESOLVED_RUNTIME_KEYS or runtime["resolved"] is not True:
            _fail("BINDING-MALFORMED", f"resolved runtime is invalid: {name}")
        tiers = runtime["tiers"]
        if not isinstance(tiers, dict) or set(tiers) != set(order):
            _fail("BINDING-MALFORMED", f"runtime does not cover every tier: {name}")
        for tier, entry in tiers.items():
            if not isinstance(entry, dict) or set(entry) != _TIER_KEYS:
                _fail("BINDING-MALFORMED", f"tier entry is invalid: {name}/{tier}")
            if not isinstance(entry["model"], str) or not entry["model"]:
                _fail("BINDING-MALFORMED", f"tier model is invalid: {name}/{tier}")
            if entry["model"].startswith(_PLACEHOLDER_PREFIX):
                _fail("TIER-MODEL-UNRESOLVED",
                      f"tier model placeholder was never filled in: {name}/{tier}",
                      runtime=name, tier=tier)
            if entry["frontier"] not in (True, False):
                _fail("BINDING-MALFORMED", f"tier frontier flag is invalid: {name}/{tier}")
    return document


def resolve_model(runtime: str, tier: str, *, actor_class: str,
                  binding: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Resolve one dispatch to a concrete model, or refuse.

    ``FRONTIER-MODEL-FORBIDDEN`` is raised before the caller can act on the
    answer, which is the whole point: the refusal has to land earlier than any
    worktree, lease or grant, so a forbidden dispatch leaves nothing behind.
    """
    document = dict(binding) if binding is not None else load_binding()
    actors = document["actor_classes"]
    if actor_class not in actors:
        _fail("UNKNOWN-ACTOR-CLASS", f"actor class is not declared: {actor_class}",
              actor_class=actor_class)
    runtimes = document["runtimes"]
    if runtime not in runtimes:
        _fail("UNKNOWN-RUNTIME", f"runtime is not declared: {runtime}", runtime=runtime)
    entry = runtimes[runtime]
    if entry.get("resolved") is not True:
        _fail("RUNTIME-UNRESOLVED", f"runtime has no proven entrypoint: {runtime}",
              runtime=runtime, unresolved_reason=entry.get("unresolved_reason"))
    if tier not in entry["tiers"]:
        _fail("UNKNOWN-TIER", f"tier is not declared for this runtime: {tier}",
              runtime=runtime, tier=tier)
    resolved = entry["tiers"][tier]
    if resolved["frontier"] and not actors[actor_class]["frontier_allowed"]:
        _fail("FRONTIER-MODEL-FORBIDDEN",
              f"actor class {actor_class} may not run a frontier model",
              runtime=runtime, tier=tier, model=resolved["model"], actor_class=actor_class)
    return {
        "runtime": runtime,
        "tier": tier,
        "actor_class": actor_class,
        "adapter": entry["adapter"],
        "model": resolved["model"],
        "frontier": resolved["frontier"],
    }


def resolved_runtimes(binding: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    document = dict(binding) if binding is not None else load_binding()
    return tuple(sorted(
        name for name, entry in document["runtimes"].items() if entry.get("resolved") is True
    ))
