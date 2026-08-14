# Implementation Plan: Canonical Step Skills

**Branch**: `feat/v3-gauntlet` | **Date**: 2026-08-14 | **Spec**: [spec.md](spec.md)

## Summary

Implement the FASE-001 canonical registry contract: exactly eleven ordered `step_id`s resolve to one pinned native skill per runtime; unresolved capability blocks. Registry, catalog and trusted-catalog bytes remain versioned assets and every resolution carries their immutable hashes.

## Technical Context

**Language/Version**: Python 3.12, standard library only.
**Primary Dependencies**: local SpecKit skills; no network or package install.
**Storage**: versioned JSON assets plus JSON receipts.
**Testing**: standalone `unittest` contract scripts under `tests/`.
**Target Platform**: POSIX/macOS/Linux CLI.
**Project Type**: local plugin and CLI library.
**Constraints**: fail closed; JCS/SHA-256 over exact asset bytes; no direct, emulated or best-effort fallback; only observed Claude runtime entrypoints are usable.
**Scope**: registry/resolution boundary only; persistence and checkpoint enforcement are later FASE-004 work.

## Constitution Check

The active work-item's eight clauses are recorded as `PASS` or `NOT-APPLICABLE` with linked evidence in `.grill/work-items/feature-workflow-v3-7dc283c84fb54e6b8f10a9c4546cd473/CONSTITUTION-CHECK.md`. No exception is needed: no global write, network access, fabricated runtime, or unpinned fallback is allowed.

## Design

1. Validate `workflow-step-skills/v1` as the sole list of the canonical eleven steps and their runtime resolutions.
2. Read registry bytes and trusted catalog bytes from shipped assets; calculate and compare their SHA-256 pins before resolving.
3. Accept a supplied observed runtime catalog only when its catalog ID and content hash match both the registry and trusted-catalog asset.
4. Emit a self-hashed `skill-resolution/v1`; rejection has a named `BLOCKED_CAPABILITY` or `STALE_SKILL_RESOLUTION` reason.
5. Validate invocation envelopes against a freshly recomputed resolution, so a receipt cannot borrow another step, runtime, work item, run, or content hash.

## Project Structure

```text
plugin/skills/grill-with-docs/
├── assets/workflow-step-skills.json
├── assets/workflow-trusted-catalogs.json
└── scripts/grill_core/step_skills.py

tests/
├── fixtures/workflow-step-skills/claude-catalog.json
└── validate_step_skill_registry_contract.py

specs/007-workflow-v3/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/skill-resolution.md
```

**Structure Decision**: keep resolver as a pure `grill_core` module. Public CLI wiring belongs to a later phase and must consume this contract rather than recreate it.

## Verification

Run `python3 tests/validate_step_skill_registry_contract.py`. It must prove the exact order, pins, trusted catalog anchoring, native invocation correlation and failure of direct/emulated/best-effort paths.
