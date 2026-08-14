# Implementation Plan: Cooperative Execution Attestation

## Summary

Validate the structural canonical-skill chain at the public V3 transition. The receipt is supplied by the coordinating workflow or an assigned subagent; it is coordination evidence, not a cryptographic claim.

## Design

1. Validate the full structural chain and direct predecessor correlation as pure data.
2. Require that structural validation before public completion.
3. Preserve state on missing, replayed, stale, divergent, direct or non-terminal receipts.
4. Suppress lazy-loader noise and return structured failures at public boundaries.
5. Document the cooperative trust boundary; signed runtime provenance is a separate future capability.

Research evidence and the exact admission contract are recorded in [research.md](research.md).

## Verification

Run `python3 tests/validate_attestation_contract.py` and `python3 tests/validate_v3_wiring_contract.py`. A current correlated receipt advances; invalid chains remain blocked.
