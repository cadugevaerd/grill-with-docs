# DECISION FRONTIER

## DQ-0001 — Sobre qual base o work item é planejado
- phase: FASE-001
- fingerprint: base-ref-do-work-item
- impact: high
- state: resolved
- context-refs: candidata 6.0.0
- artifacts: WORK-ITEM.json (depends-on-work)
- depends-on: none
- final-ref: R-0001

## DQ-0002 — Qual CLI abre o work item enquanto o init 6.0.0 exige líder despachado
- phase: FASE-001
- fingerprint: cli-do-init-pre-ship-6
- impact: high
- state: resolved
- context-refs: sessão líder, Dispatch, candidata 6.0.0
- artifacts: WORK-ITEM.json
- depends-on: DQ-0001
- final-ref: R-0002

## DQ-0003 — Topologia: quem é coordenador Orca e quais papéis viram child
- phase: FASE-001
- fingerprint: topologia-coordenador-e-children
- impact: high
- state: resolved
- context-refs: sessão líder, coordenador, child, Run, Dispatch, especialista, worker
- artifacts: docs/adr/ADR-0001.md
- depends-on: DQ-0001
- final-ref: ADR-0001

## DQ-0004 — Orca indisponível: fail-closed ou caminho degradado nativo
- phase: FASE-001
- fingerprint: orca-indisponivel-degradado-ou-bloqueio
- impact: high
- state: resolved
- context-refs: caminho degradado, child
- artifacts: docs/adr/ADR-0002.md
- depends-on: DQ-0003
- final-ref: ADR-0002

## DQ-0005 — Binding de modelo/esforço por --agent (claude|codex) no worker-start
- phase: FASE-001
- fingerprint: binding-modelo-esforco-por-agent
- impact: high
- state: resolved
- context-refs: child, tier
- artifacts: docs/adr/ADR-0003.md
- depends-on: DQ-0003
- final-ref: ADR-0003

## DQ-0006 — Child pode usar agent diferente do runtime do líder
- phase: FASE-001
- fingerprint: agent-do-child-vs-runtime-do-lider
- impact: medium
- state: resolved
- context-refs: child, sessão líder
- artifacts: docs/adr/ADR-0004.md
- depends-on: DQ-0003
- final-ref: ADR-0004

## DQ-0007 — Dono do worktree: grant do gauntlet ou placement do Orca
- phase: FASE-001
- fingerprint: dono-do-worktree-gauntlet-vs-orca
- impact: high
- state: resolved
- context-refs: child, worker, grant
- artifacts: docs/adr/ADR-0005.md, DECISION-BACKLOG.md (BL-0001)
- depends-on: DQ-0003
- final-ref: ADR-0005

## DQ-0008 — Que evidência do child o líder persiste (Dispatch ID, worker_done, launch.effective)
- phase: FASE-001
- fingerprint: evidencia-do-child-no-receipt
- impact: medium
- state: resolved
- context-refs: Dispatch, worker_done, child
- artifacts: PLAN-CONTEXT.md
- depends-on: DQ-0003, DQ-0007
- final-ref: R-0008

## DQ-0009 — Orca como dependência declarada obrigatória e impacto SemVer
- phase: FASE-001
- fingerprint: orca-dependencia-obrigatoria-e-semver
- impact: high
- state: resolved
- context-refs: child, caminho degradado, candidata 6.0.0
- artifacts: docs/adr/ADR-0006.md
- depends-on: DQ-0004
- final-ref: ADR-0006

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.
