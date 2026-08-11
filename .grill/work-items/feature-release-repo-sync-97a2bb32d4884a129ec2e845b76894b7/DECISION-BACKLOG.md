# DECISION-BACKLOG

## BL-0001 — Migrar a credencial de publicação para escopo mínimo
- state: resolved
- phase: FASE-002
- owner: Carlos Araujo
- motivo: ADR-0004 adota o PAT classic existente, que concede admin:org, admin:enterprise e delete_repo, enquanto a publicação exige apenas contents:write em dois repositórios
- impacto: qualquer workflow na main executa com poder de administrar organizações e apagar repositórios
- evidence-needed: GitHub App instalado em claude-skills e codex-skills com contents:write, ou PAT fine-grained equivalente, com uma publicação verde usando a credencial nova
- next-action: acompanhar SGD-3 no backlog externo
- final-ref: ADR-0004
- resolucao: a decisão foi tomada em ADR-0004 e não está adiada; o que resta é melhoria futura com gatilho, que pertence ao backlog externo e não ao DECISION-BACKLOG. Espelhado como SGD-3 em ~/.backlog/backlog.db, vinculado a este repositório.
- gatilho de retomada: primeira rotação do PAT, ou qualquer sinal de comprometimento, ou o momento em que um terceiro ganhar permissão de merge no canônico
- ponto de parada: antes de conceder acesso de escrita a qualquer colaborador adicional no repositório canônico

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
