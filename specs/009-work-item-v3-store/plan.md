# Implementation Plan: Work Item V3 and Project Store

## Summary

Deliver a preview-first Work Item V3 migration with immutable metadata, no-follow directory-FD writes, and a persistent project store guarded by identity, lock, CAS and journal checks.

## Design

1. Parse and validate V2/V3 metadata without static dependency on the public CLI.
2. Pin the migration bundle with no-follow descriptors before reading or replacing its document.
3. Hold one safe lock across late re-read, decision and atomic replacement.
4. Persist project identity and lifecycle data in the store with integrity checks.
5. Translate all V3 outcomes at the public boundary.

## Verification

Run `python3 tests/validate_work_item_v3_contract.py`, `python3 tests/validate_orchestrator_store_contract.py`, and `python3 tests/validate_v3_wiring_contract.py`.
