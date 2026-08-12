# Analysis — FASE-003

## Cobertura dos requisitos

| FR | Onde é satisfeito | Novo nesta fase |
|---|---|---|
| FR-001 gatilho manual | `publish.yml` `on.workflow_dispatch` | não — verificado (CHK-015) |
| FR-002 uma execução leva ambos | matriz de dois jobs + `plan_entry` CREATED/UPDATED | não — verificado em T-005 |
| FR-003 releitura do remoto | T-001, T-002, T-004 | sim |
| FR-004 tag resolve no canônico | T-004 | sim |
| FR-005 nomear cada divergência | T-001 | sim |
| FR-006 sem backfill histórico | nenhuma versão sobe; publica a corrente | não — restrição negativa |
| FR-007 gatilho sobrevive | nada remove `workflow_dispatch` | não — verificado |

Cinco dos sete requisitos já eram propriedades do código de FASE-002. Isso é esperado: a fase é de reconciliação e verificação, não de construção.

## Riscos

**R-1 — O bloqueio da credencial é externo e não tem contorno técnico.**
Sem o segredo, a execução real não acontece. Publicar à mão a partir desta sessão produziria o *resultado* (os dois destinos em dia) mas não o *objetivo* declarado no WHY do handoff: exercitar a automação uma vez em condições reais. Uma reconciliação manual deixaria a automação tão não-exercitada quanto está hoje, e o primeiro teste real continuaria acontecendo às cegas num merge futuro. Portanto: não contornar. Entregar tudo o resto e nomear o bloqueio.

**R-2 — A releitura introduz um novo modo de falha.**
Antes, o job terminava depois do push. Agora pode ficar vermelho depois de ter publicado com sucesso, se a comparação for estrita demais. Mitigado por comparar exatamente os cinco campos que o publicador escreve e mais nada.

**R-3 — Falso verde sobrevivente.**
A releitura clona de novo, mas do mesmo remoto e no mesmo job. Uma corrupção do índice depois do clone de verificação passaria. Aceito: a janela é de segundos e a concorrência do workflow já serializa a publicação.

**R-4 — Os critérios do handoff contradizem o modelo vigente.**
O handoff pede manifesto vendorizado e ausência do diretório de testes na cópia publicada; sob ADR-0006 não existe cópia. Se a fase fosse fechada contra o texto literal do handoff, ela seria infechável. Resolvido declarando a substituição na spec e registrando em ADR — não silenciosamente.

**R-5 — O drift registrado no ROADMAP está errado.**
`2.4.0` contra `2.4.1` observado. Erro de baixo impacto no resultado, alto impacto na confiança do documento. Corrigido em T-006.

**R-6 — O codex nunca serviu este plugin.**
A entrada será criada, não atualizada, e é o primeiro `git-subdir` daquele índice — os outros 15 vendorizam. Se o cliente do codex tratar `git-subdir` de forma diferente na prática, isso só aparece na instalação, fora do alcance desta fase. Evidência de que o formato é aceito está registrada na spec de FASE-002.

## Dependências

- Ordem interna: T-001 → T-002 → {T-003, T-004} → T-005 → T-006.
- Externa e bloqueante para T-007: instalação do segredo, ato humano.
- Nenhuma dependência nova de terceiros. Tudo continua stdlib.

## Fora de escopo, deliberadamente

- Guarda de fork no workflow. ADR-0004 já analisou a exposição e concluiu que segredos não vazam para PRs de fork em repositório público. Não é dívida declarada desta fase.
- Migração da credencial para escopo mínimo. É BL-0001, resolvido como decisão, e SGD-3 no backlog externo.
- O filtro de paths do CI contra o required check (SGD-4/SGD-7).
- Backfill de `2.4.1` ou de qualquer versão histórica nos destinos.
