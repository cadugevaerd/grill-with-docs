# Quickstart: Gauntlet Loop Activation

## Prerequisites

- A repository containing this plugin.
- An explicitly migrated V3 workflow and a V3 work item migrated or rebound after that workflow, so its immutable workflow digest is current.
- A current shipped Claude Code capability catalog resolving all eleven canonical stages.
- Python 3.10+.

For a V3-migrated legacy work item whose workflow digest is stale, preview then explicitly apply the rebind before activation:

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  migrate-v3 . --work-id <work-item-id> --rebind-workflow
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  migrate-v3 . --work-id <work-item-id> --rebind-workflow --apply
```

## Activate

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-init . --work-id <work-item-id> --max-workers 3
```

Expected: one JSON response with `"verdict":"ACTIVATED"`; `.grill/gauntlet.yaml` contains the selected activation.

## Inspect

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-status . --work-id <work-item-id>
```

Expected: one `STATUS` response with exactly one of `ELIGIBLE`, `ACTIVATED`,
`STALE`, or `BLOCKED`. A currently matching record is `ACTIVATED`; changed
verified inputs report `STALE` with a reason. A current proof failure for an
otherwise valid subject reports `BLOCKED` with a reason. Invalid roots and
work-item IDs remain top-level `BLOCKED` command failures, not `STATUS`.

## Admit a run

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-run . --work-id <work-item-id>
```

Expected: `RUN-ADMITTED` only for a current activation. This is admission
only: it creates no worker, worktree, branch, receipt, or durable run record.

## Resume and cleanup boundary

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-resume . --work-id <work-item-id>
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-cleanup . --work-id <work-item-id>
```

Expected: `gauntlet-resume` returns `ACTIVATION-REQUIRED` until the activation
is current; both commands then return `SCHEDULING-NOT-AVAILABLE`. FASE-001
does not schedule, resume, or delete any runtime state.

## Validate the feature

```bash
python3 tests/validate_gauntlet_activation_contract.py
python3 tests/run_validators.py
```

Expected: all validators pass; V2 commands retain their existing behavior.
