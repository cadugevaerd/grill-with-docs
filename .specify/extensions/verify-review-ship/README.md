# Verify Review Ship for Spec Kit

A Spec Kit extension that adds post-convergence operational verification, technical review, learning capture, and transactional delivery:

- `/speckit.verify-review-ship.verify`
- `/speckit.verify-review-ship.review`
- `/speckit.verify-review-ship.ship`

```text
constitution → specify → clarify → plan → checklist → tasks → analyze
→ implement ⇄ converge → verify → review → ship: learn → approve → revalidate → merge → cleanup
```

`/speckit.converge` is a required official Spec Kit command (Spec Kit `>=0.11.2`). Repeat `implement → converge` until it reports **Converged**. This extension registers **3 commands and 0 hooks**: it does not inject or modify the official command.

## Responsibility Boundaries

| Command | Authority |
|---|---|
| `/speckit.converge` | Compares code with spec/plan/tasks, identifies gaps, and appends remaining tasks. |
| `verify` | Consumes a fresh Converge handoff and runs executable gates: tests, build, lint, typecheck, security, contracts, quickstart, and diff hygiene. |
| `review` | Reviews runtime correctness, tests, readability, architecture, security, and performance. It does not redo completeness analysis. |
| `ship` | Requires fresh evidence, governs approved learnings, revalidates changes, and performs safe Git integration. |

## Operational flow

`verify` blocks when Converge appended tasks, the source changed, or its official outcome is unavailable. `review` requires matching Verify evidence. `ship` requires matching `CONVERGED`, `PASS`, and `APPROVE` evidence and never launches a redundant completeness/reviewer pass.

## Learning and policy gate

Before merge, `ship` extracts evidence-backed candidates and requires explicit approval. Each candidate can be approved, rejected, or deferred individually. Approved versioned changes receive a dedicated work-branch commit and invalidate stale reports.

| Destination | Use for |
|---|---|
| `constitution` | Durable project-wide, non-negotiable and testable governance. |
| `agent-context` | Repository/runtime operating instructions; managed blocks are never overwritten. |
| `adr-docs` | Architecture decisions, procedures, and durable technical documentation. |
| `backlog` | Valid future work outside this delivery. |
| `memory` | Stable cross-project, non-normative context; default is `propose-only`. |
| `discard` | Noise, duplicates, transient observations, or feature-local details. |

Constitution or Spec Kit artifact changes require `analyze → converge` before Verify and Review. Memory finalization occurs after remote primary-ref verification by default.

## Transactional ship

```text
fresh evidence → learning proposal → explicit approval → versioned commit
→ required converge/revalidation → isolated merge → non-force push
→ remote verification → memory finalization → safe cleanup
```

`ship --dry-run` performs no proposal, worktree, ref, fetch, merge, push, or cleanup mutation. `ship` merges Git state; it does not deploy applications or infrastructure.

## Configuration

Copy `config-template.yml` to:

```text
.specify/extensions/verify-review-ship/verify-review-ship-config.yml
```

Configure convergence enforcement, executable gates, review axes, learning destinations, remote/base branch, and merge strategy.

## Installation

### Release v0.4.1

```bash
specify extension add verify-review-ship \
  --from https://github.com/cadugevaerd/spec-kit-verify-review-ship/archive/refs/tags/v0.4.1.zip
specify extension list
```

### Local development

```bash
specify extension add --dev /path/to/spec-kit-verify-review-ship
specify extension list
```

## License

MIT. See `LICENSE`.
