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

## BL-0002 — Qual credencial instalar antes da primeira publicação real
- state: open
- phase: FASE-003
- owner: Carlos Araujo
- motivo: ADR-0004 decidiu reusar o PAT classic existente, mas a credencial nunca foi instalada e nenhuma publicação jamais rodou. A primeira instalação é a última janela barata para escolher outra coisa: depois dela, trocar a credencial exige reconfigurar o pipeline com o drift já resolvido e sem pressão para revisitar o assunto.
- impacto: enquanto não houver decisão executada, a FASE-003 fica bloqueada e os dois marketplaces continuam servindo estado antigo — `claude-skills` em 2.4.1 e `codex-skills` sem entrada alguma. Se a decisão for executar ADR-0004 como está, todo workflow que chegar à main passa a rodar com `admin:org`, `admin:enterprise` e `delete_repo`.
- evidence-needed: o segredo instalado no canônico e uma execução manual verde, com a releitura aprovando nos dois destinos
- next-action: ato humano — instalar o segredo e disparar `publish.yml` por `workflow_dispatch` uma vez. Espelhado como SGD-9; a alternativa de escopo mínimo é SGD-3.
- gatilho de retomada: a instalação do segredo, por qualquer caminho
- ponto de parada: antes de qualquer tentativa de publicação real, porque sem credencial o job falha no primeiro passo que a consome

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
