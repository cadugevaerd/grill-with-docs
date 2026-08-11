# DECISION-BACKLOG

## BL-0001 — Migrar a credencial de publicação para escopo mínimo
- state: open
- phase: FASE-002
- owner: Carlos Araujo
- motivo: ADR-0004 adota o PAT classic existente, que concede admin:org, admin:enterprise e delete_repo, enquanto a publicação exige apenas contents:write em dois repositórios
- impacto: qualquer workflow na main executa com poder de administrar organizações e apagar repositórios
- evidence-needed: GitHub App instalado em claude-skills e codex-skills com contents:write, ou PAT fine-grained equivalente, com uma publicação verde usando a credencial nova
- next-action: criar o GitHub App e substituir o secret no repositório canônico
- gatilho de retomada: primeira rotação do PAT, ou qualquer sinal de comprometimento, ou o momento em que um terceiro ganhar permissão de merge no canônico
- ponto de parada: antes de conceder acesso de escrita a qualquer colaborador adicional no repositório canônico

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
