# Phase 0 fixtures — `workflow-step-skills`

Plan §4.1: "a Fase 0 deve resolver os IDs/entrypoints reais de cada runtime e
congelá-los nas fixtures antes da implementação."

## What this directory contains

`claude-catalog.json` is the one and only `skill-catalog/v1` document Phase 0
could freeze. It was captured read-only from `.claude/skills` in this
environment: 11 entries, one per Spec Kit step, each with a real
`entrypoint`, `manifest_sha256` and `content_sha256`. It is the catalogue
`assets/workflow-trusted-catalogs.json` pins by digest, and it is what
`assets/workflow-step-skills.json` resolves against for `runtime="claude"` in
all 11 steps.

## Why `hermes` and `codex` have no catalogue here

There is no reachable Hermes or Codex installation in this environment to
observe a native skill/command surface from. Phase 0 could not honestly
freeze entrypoints, manifests or content hashes for either runtime — doing so
would mean inventing values nothing ever verified.

The registry (`assets/workflow-step-skills.json`) reflects exactly that: for
every one of the 11 steps, `resolutions.hermes` and `resolutions.codex` are
`{"resolved": false, "unresolved_reason": "RUNTIME_ENTRYPOINT_UNPROVEN"}`.
`resolve_workflow_skill(step_id, "hermes" | "codex", ...)` blocks with
`BLOCKED_CAPABILITY/RUNTIME_ENTRYPOINT_UNPROVEN` for all 11 steps — 22 of the
33 step × runtime pairs are unresolved by design, not by omission.

This is not a placeholder waiting to be filled in casually: closing it
requires a real Phase 0 pass against an actual Hermes and an actual Codex
install (or their maintainers' own manifest of native skill/command
entrypoints), captured read-only the same way `claude-catalog.json` was, then
frozen here and wired into the registry's `resolutions.hermes` /
`resolutions.codex` entries. Until that happens, the fail-closed behaviour
above is correct and load-bearing, not a bug to silence.
