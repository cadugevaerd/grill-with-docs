# DECISION-BACKLOG

## BL-0001 — Placement de child em worktree de gauntlet não registrado no Orca
- phase: FASE-001
- state: resolved
- owner: sessão líder da entrevista
- evidence: `orca worktree show --worktree path:/home/carlosaraujo/Documentos/Projetos/grill-with-docs/.git/grill/wt-run-a68b9871b8b7ff9c3a07ea5c-p01-a --json` retornou `ok: true` com `id` `<repo-id>::<path>` e `identity`; o seletor `path:` resolve worktree de gauntlet sem registro prévio (Orca 1.4.200, 2026-09-15)
- trigger: etapa `plan`, antes de qualquer task de despacho de worker
- decision-needed: `path:<wt-run-*>` posiciona o child diretamente, ou o plan precisa de passo determinístico de registro (e cleanup) no Orca antes do `worker-start`
- resolution: sem passo de registro; `worker-start --worktree path:<wt>` é o placement. O lançamento real de child nesse seletor continua sendo critério de aceite live, não decisão pendente
- origin: DQ-0007

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
