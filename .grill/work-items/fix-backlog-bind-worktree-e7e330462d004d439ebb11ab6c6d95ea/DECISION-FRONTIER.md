# DECISION FRONTIER

## DQ-0001 — Como a ponte decide que uma worktree pertence ao repositório vinculado
- phase: FASE-001
- fingerprint: identidade-do-repo-para-bound-path
- impact: high
- state: resolved
- context-refs: worktree de controle, worktree linkada, caminho vinculado, conjunto de candidatos, resolução do backlog
- artifacts: docs/adr/ADR-0001.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — Por onde a ponte enumera as worktrees
- phase: FASE-001
- fingerprint: enumerar-worktrees-pelo-seam-de-toolchain
- impact: medium
- state: resolved
- context-refs: seam de toolchain, conjunto de candidatos
- artifacts: PLAN-CONTEXT.md
- depends-on: DQ-0001
- final-ref: R-0002

## DQ-0003 — Dois backlogs vinculados a worktrees distintas do mesmo repositório, e enumeração que falha
- phase: FASE-001
- fingerprint: ambiguidade-e-fallback-do-conjunto-de-candidatos
- impact: high
- state: resolved
- context-refs: conjunto de candidatos, resolução do backlog
- artifacts: docs/adr/ADR-0001.md
- depends-on: DQ-0001
- final-ref: ADR-0001

## DQ-0004 — Que teste teria reprovado este bug, e entra nesta fase
- phase: FASE-001
- fingerprint: cobertura-de-teste-resolucao-por-worktree
- impact: high
- state: resolved
- context-refs: seam de toolchain, worktree linkada, resolução do backlog
- artifacts: docs/adr/ADR-0002.md
- depends-on: DQ-0002
- final-ref: ADR-0002

## DQ-0005 — Caminho vinculado a worktree que já foi removida
- phase: FASE-001
- fingerprint: bound-path-de-worktree-removida
- impact: medium
- state: out-of-scope
- context-refs: caminho vinculado, worktree linkada
- artifacts: docs/adr/ADR-0001.md, ROADMAP.md#FASE-001
- depends-on: DQ-0001
- final-ref: R-0005

## DQ-0006 — Leitura SemVer do bump obrigatório
- phase: FASE-001
- fingerprint: semver-do-bump-para-este-fix
- impact: medium
- state: resolved
- context-refs: resolução do backlog
- artifacts: PLAN-CONTEXT.md
- depends-on: none
- final-ref: R-0006

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.
