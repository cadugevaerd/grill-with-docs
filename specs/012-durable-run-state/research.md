# Research: Durable Gauntlet Runs

## Decision: Extend the existing Project Store per work item

**Rationale**: `grill_core.store` already provides common-Git scope, strict JSON validation, atomic CAS writes, chained events, head witnesses, receipt categories, and rollback detection. An optional strict `gauntlet` block keeps run ownership tied to one work item.

**Alternatives considered**: A new run database or `.grill` sidecar was rejected because it would create parallel authority and bypass Store journal integrity.

## Decision: Record coordinator-owned evidence before visible state

**Rationale**: ADR-0010 makes the coordinator the Evidence Boundary. A transition can reference only a receipt and journal event that the coordinator has re-read and hashed.

**Alternatives considered**: Workers writing receipts or a snapshot-first transition were rejected because they permit self-approval or a visible state without proof.

## Decision: Prepare, but do not run, workers

**Rationale**: ADR-0003 requires isolated worktrees, while the FASE-002 handoff excludes scheduler and parallelism. Explicit preparation proves base pinning and cleanup conditions without spawning a process.

**Alternatives considered**: Creating workers automatically from `gauntlet-run` or invoking Claude was rejected as FASE-003 dispatch work.

## Decision: Use logical identifiers and derived workspace targets

**Rationale**: Work item V3 avoids physical path authority. Store-backed logical keys permit deterministic target derivation and descriptor-safe cleanup.

**Alternatives considered**: User-provided absolute paths and broad workspace scans were rejected for traversal and accidental deletion risk.

## Decision: Persist one explicit recovery decision only

**Rationale**: ADR-0005 reserves automatic stall recovery for the later scheduler. FASE-002 needs durable eligibility and one validated operator-requested decision.

**Alternatives considered**: Watchdogs, automatic replacement, relaunch, and retry were rejected as premature dispatch authority.
