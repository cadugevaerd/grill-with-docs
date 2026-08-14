# Quickstart: Verify FASE-001

```bash
python3 tests/validate_step_skill_registry_contract.py
```

Expected: every contract test passes. A catalog with a recomputed attacker hash, a mismatched registry pin, an unobserved runtime, or a forged invocation receipt must be blocked.

Evidence: 2026-08-14 — `Ran 103 tests ... OK`.
