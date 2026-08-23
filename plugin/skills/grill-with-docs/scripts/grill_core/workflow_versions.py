#!/usr/bin/env python3
"""Frozen, per-version tables for the canonical workflow sequence.

Stdlib only, no I/O, no network. This module is pure data: it must stay
importable from anywhere in the core without dragging a dependency graph
behind it, exactly like ``ensure_workflow.REGISTRY`` is kept a literal.

Freezing contract
-----------------
Every table below is a **literal**, never derived from another table. v3 and
v4 must be able to drift without one silently rewriting the other -- the same
doctrine ``workflow_v3.ESSENTIAL`` states for the allowlists. Deriving
``SEQUENCE_V4`` from ``SEQUENCE_V3`` through ``STEP_RENAMES_V3_TO_V4`` would
read as tidier and would defeat the point: a typo in the rename map would
silently rewrite the canonical order instead of failing a contract test.

``STEP_RENAMES_V3_TO_V4`` exists for provenance (``state.json`` records where a
step came from) and for diagnostics, never as the source of the v4 order.
"""
from __future__ import annotations

#: Canonical order of the v3 cycle. Frozen: a bundle or receipt minted under v3
#: keeps being read against this exact tuple forever, even though v3 is no
#: longer an execution surface (see EXECUTABLE_VERSIONS).
SEQUENCE_V3 = (
    "specify",
    "plan",
    "checklist",
    "tasks",
    "analyze",
    "agent-assign",
    "agent-execute",
    "converge",
    "verify",
    "review",
    "ship",
)

#: Canonical order of the v4 cycle. Same length and same no-skip ordering; the
#: two execution steps are renamed to say what they actually do.
SEQUENCE_V4 = (
    "specify",
    "plan",
    "checklist",
    "tasks",
    "analyze",
    "partition",
    "implement-parallel",
    "converge",
    "verify",
    "review",
    "ship",
)

#: Provenance only. Not the source of ``SEQUENCE_V4`` -- see module docstring.
STEP_RENAMES_V3_TO_V4 = {
    "agent-assign": "partition",
    "agent-execute": "implement-parallel",
}

#: Minimum model tier per step (ADR-0001: smallest capable tier). Promotion may
#: only happen before dispatch; there is never a silent downgrade.
TIER_POLICY_V3 = {
    "specify": "large",
    "plan": "large",
    "checklist": "small",
    "tasks": "medium",
    "analyze": "large",
    "agent-assign": "large",
    "agent-execute": "medium",
    "converge": "medium",
    "verify": "medium",
    "review": "large",
    "ship": "large",
}

#: v4 floors. ``partition`` drops from large to medium because it stopped being
#: a judgement call: v3's ``agent-assign`` matched tasks to agents by name and
#: reasoning, while ``partition`` is deterministic parsing plus bin-packing with
#: the heuristic pinned in ``grill_core.partition``. ADR-0013 records this.
TIER_POLICY_V4 = {
    "specify": "large",
    "plan": "large",
    "checklist": "small",
    "tasks": "medium",
    "analyze": "large",
    "partition": "medium",
    "implement-parallel": "medium",
    "converge": "medium",
    "verify": "medium",
    "review": "large",
    "ship": "large",
}

#: The step whose floor governs the workers dispatched under it. Read through
#: this map instead of indexing a tier policy with a hard-coded step id --
#: ``grill_workspace._tier_floors`` used to do the latter and raised KeyError
#: with rc=1 and an empty stdout, which collides with the NO-GO exit code.
EXECUTOR_STEP_BY_VERSION = {
    "v3": "agent-execute",
    "v4": "implement-parallel",
}

SEQUENCE_BY_VERSION = {
    "v3": SEQUENCE_V3,
    "v4": SEQUENCE_V4,
}

TIER_POLICY_BY_VERSION = {
    "v3": TIER_POLICY_V3,
    "v4": TIER_POLICY_V4,
}

#: Registry asset per workflow version. v3 keeps the original filename so its
#: bytes -- and therefore its ``registry_sha256`` -- never move: every v3
#: WORKFLOW.md already materialised in a consumer repository pins that hash,
#: and repointing it in place would turn all of them into
#: REGISTRY-PIN-DIVERGENT with no preview and no migration path.
REGISTRY_FILENAME_BY_VERSION = {
    "v3": "workflow-step-skills.json",
    "v4": "workflow-step-skills.v4.json",
}

#: Skill catalogue asset per workflow version. v4 owns a distinct catalogue --
#: with a distinct ``catalog_id`` -- rather than growing the v3 one, for the
#: same reason the registry does not move: ``workflow-trusted-catalogs.json``
#: pins the v3 catalogue by digest, and editing it in place would make every v3
#: consumer read an UNTRUSTED_CATALOG overnight.
CATALOG_FILENAME_BY_VERSION = {
    "v3": "claude-code-local-skills.catalog.json",
    "v4": "grill-v4-local-skills.catalog.json",
}

CATALOG_ID_BY_VERSION = {
    "v3": "claude-code-local-skills",
    "v4": "grill-v4-local-skills",
}

TRUSTED_CATALOGS_FILENAME_BY_VERSION = {
    "v3": "workflow-trusted-catalogs.json",
    "v4": "workflow-trusted-catalogs.v4.json",
}

TEMPLATE_FILENAME_BY_VERSION = {
    "v2": "WORKFLOW.template.md",
    "v3": "WORKFLOW.v3.template.md",
    "v4": "WORKFLOW.v4.template.md",
}

#: ``state.json`` development schema per workflow version. v2 of the schema adds
#: an explicit ``workflow_version`` so a renamed sequence stops being reported
#: as a generic DEVELOPMENT-SCHEMA failure.
DEVELOPMENT_SCHEMA_BY_VERSION = {
    "v3": "grill-development/v1",
    "v4": "grill-development/v2",
}

#: Workflow versions whose documents the runtime can execute. v3 was an
#: execution surface until the gate moved to the v4 frontier; v2 never was.
#: Shrinking this tuple is a deprecation, not a cleanup: it removes a
#: capability a consumer had.
EXECUTABLE_VERSIONS = ("v4",)

#: Workflow versions the runtime must still be able to *read*. Executing and
#: knowing how to read are different powers and this module keeps them apart:
#: activation receipts are immutable and get revalidated by later builds, and a
#: bundle written under an older sequence keeps projecting against the sequence
#: it declares. Every per-version table below is keyed by this tuple, never by
#: EXECUTABLE_VERSIONS -- dropping a key here would raise KeyError on a receipt
#: this build did not mint, instead of returning a verdict about it.
#: Invariant, tested: set(EXECUTABLE_VERSIONS) <= set(KNOWN_VERSIONS).
KNOWN_VERSIONS = ("v3", "v4")

#: The version this build executes. Kept distinct from KNOWN_VERSIONS so the
#: gate has one obvious source and cannot drift from the tables.
ACTIVE_VERSION = "v4"

#: ``state.json`` development schema -> the workflow version it speaks, or None
#: when the document declares its own. Frozen literal, never the inverse of
#: DEVELOPMENT_SCHEMA_BY_VERSION: /v1 predates ``workflow_version`` and can only
#: mean v3, while /v2 declares its version explicitly, so it maps to None rather
#: than to v4. Computing this by inverting the other table would lose exactly
#: that distinction.
DEVELOPMENT_SCHEMAS = {
    "grill-development/v1": "v3",
    "grill-development/v2": None,
}

#: The development schema a bundle created by this build declares.
ACTIVE_DEVELOPMENT_SCHEMA = "grill-development/v2"

#: Every canonical step id across every executable version. Reading a v3
#: receipt after this build ships still has to recognise ``agent-execute`` as a
#: canonical step id -- it was one, under the version that minted the receipt.
ALL_STEPS = tuple(sorted(set(SEQUENCE_V3) | set(SEQUENCE_V4)))
