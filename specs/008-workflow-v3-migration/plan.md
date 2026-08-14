# Implementation Plan: Explicit Workflow V3 Migration

## Summary

Implement an additive V2/V3 reader and a preview-first V3 migration whose document pin and ordered external cycle are checked again at execution time.

## Design

1. Render the shipped V3 template with the current registry SHA-256.
2. Require preview identity before any apply and reject changed workflow bytes.
3. Keep the V2 essentials and version untouched.
4. Make V3 readiness check the exact ordered eleven-step cycle and registry pin.
5. Treat dynamic-loader failures as structured, read-only failures without stdout noise.

## Verification

Run `python3 tests/validate_workflow_v3_contract.py` and `python3 tests/validate_v3_wiring_contract.py`.
