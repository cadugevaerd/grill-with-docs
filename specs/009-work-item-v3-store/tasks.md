# Tasks: Work Item V3 and Project Store

- [x] T001 Define Work Item V3 schema, immutable digest and dual-read validation in `grill_core/work_item_v3.py`.
- [x] T002 Implement preview/apply migration with no-follow directory descriptors and atomic replacement.
- [x] T003 Cover locking, symlink swap and state-divergence attacks in `tests/validate_work_item_v3_contract.py` and `tests/validate_v3_wiring_contract.py`.
- [x] T004 Implement project identity, store CAS/lock/journal behavior in `grill_core/store.py`.
- [x] T005 Cover cross-worktree identity and store failures in `tests/validate_orchestrator_store_contract.py`.
- [x] T006 Verify public V3 error translation without a V2 regression.
