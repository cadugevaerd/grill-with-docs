# Tasks: Explicit Workflow V3 Migration

- [x] T001 Render and validate `WORKFLOW.v3.template.md` with the live registry pin.
- [x] T002 Implement preview/identity-confirmed migration in `grill_core/workflow_v3.py`.
- [x] T003 Preserve V2 compatibility in `ensure_workflow.py`.
- [x] T004 Reject divergent pins and reordered external cycles in `grill_core/workflow_v3.py`.
- [x] T005 Make loader failures one structured, read-only response in `workflow_v3.py` and `ensure_workflow.py`.
- [x] T006 Cover migration, order, pins, V2 compatibility and hook failures in `tests/validate_workflow_v3_contract.py` and `tests/validate_v3_wiring_contract.py`.
