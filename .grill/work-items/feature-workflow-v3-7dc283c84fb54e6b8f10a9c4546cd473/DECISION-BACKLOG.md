# DECISION-BACKLOG

## BL-0001 — Verificador nativo de receipt ainda não está disponível
- phase: FASE-004
- state: superseded
- owner: product owner
- evidence-needed: decisão explícita de que o produto organiza agentes cooperativos, sem threat model de executor malicioso
- next-action: se o threat model mudar, criar novo BL para autoridade externa com signer, trust anchor e anti-replay
- context-refs: Execution Attestation, Canonical Skill, Skill Resolution

## BL-0002 — Autorização explícita de release pendente
- phase: FASE-004
- state: resolved
- owner: product owner
- evidence-needed: autorização explícita para criar commit, integrar a branch e publicar o resultado remoto
- next-action: executar o release conforme o WORKFLOW ativo; autorização recebida em 2026-08-14
- context-refs: Managed Workflow, Work Item V3

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
