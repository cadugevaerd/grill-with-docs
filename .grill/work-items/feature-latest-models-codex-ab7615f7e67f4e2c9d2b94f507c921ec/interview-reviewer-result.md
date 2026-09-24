# Revisão independente — interview-reviewer-latest-models

**Veredito: CHANGES_REQUIRED.** As cinco decisões humanas estão preservadas nos ADRs e na fronteira, mas o handoff não expressa corretamente a precedência de `priority` e uma justificativa constitucional atribui evidência importada à sessão atual. São correções documentais; não exigem nova decisão humana nem implementação nesta atividade.

- Work item: `feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec`.
- Atividade: `interview-reviewer-latest-models`.
- Input informado: `5a33f04da4a4b69ef82beb5b3eab95b25aec449d836868bac802b5989cc64c11`.
- Base dos caminhos e linhas abaixo: `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/`.
- Método: leitura integral dos 11 documentos autorizados pelo manifesto, sem executar código do projeto, testes ou consultas externas e sem alterar arquivos do repositório. Hashes tratados como declarados, não certificados por esta revisão.

## Findings que exigem correção

### R1 — P2: critérios do handoff substituem preferência do catálogo por novidade da geração

**Local:** `handoffs/FASE-001-SPECIFY-HANDOFF.md:14`, `:19`, `:20` e `:21`; também `ROADMAP.md:7`.

O cenário 1 exige `gpt-6-luna` apenas pela presença dele junto de `gpt-5.6-luna`; o cenário 2 promete a troca assim que uma terra mais nova for listada. Nenhum desses cenários informa a prioridade. Isso não equivale à DQ-0001: `ROUND-LOG.jsonl:1`, `docs/adr/ADR-0001.md:20` e `PLAN-CONTEXT.md:12` mandam escolher o slug listado de menor `priority` dentro da família. O próprio autor preserva essa distinção em `interview-author-result.md:38` e `:41`.

**Contraprova do contrato:** com ambas as lunas listadas, `gpt-5.6-luna` em prioridade 1 e `gpt-6-luna` em prioridade 10, o ADR escolhe a primeira; o cenário 1 exige a segunda. Uma implementação fiel ao ADR poderia reprovar o handoff, ou uma implementação que ordena gerações poderia passar os exemplos e contrariar a escolha humana.

**Correção mínima:** definir o resultado como “slug listado preferido da família, de menor `priority`”; explicitar as prioridades nos exemplos e condicionar a atualização automática à preferência do catálogo. Registrar um caso em que a geração mais nova não tem menor prioridade. Não é necessário escolher agora a política de empate: essa continua detalhe do plan, conforme `interview-author-result.md:117`.

### R2 — P2: PASS constitucional afirma verificação técnica nesta sessão sem distingui-la da evidência herdada

**Local:** `CONSTITUTION-CHECK.md:15` e `:16`.

A justificativa de “Evidência antes de afirmação” diz que `codex debug models` e `codex debug prompt-input` foram verificados “nesta sessao”. As fontes acessíveis atribuem os comandos a 2026-09-23 (`docs/adr/ADR-0001.md:5`); o novo bundle declara importação do work item anterior e reconfirmação humana em 2026-09-24 (`CONTEXT.md:17`, `ROUND-LOG.jsonl:1`). O autor ressalva expressamente que não verificou novamente catálogo, código ou disponibilidade (`interview-author-result.md:9`). Reconfirmação humana da decisão não comprova repetição dos comandos na sessão nova.

**Impacto:** a justificativa mistura proveniência histórica com observação atual e pode fazer a auditoria interpretar o PASS como evidência técnica recém-produzida. Esta revisão não afirma que uma execução nova inexista; afirma que a justificativa não a sustenta nos arquivos autorizados.

**Correção mínima:** atribuir os resultados à sessão fonte de 2026-09-23, com caminho/commit já registrados, separando a reconfirmação humana de 2026-09-24. Se os comandos foram realmente repetidos, citar a evidência durável correspondente. O uso de evidência histórica não exige, por si só, repetir comandos nem invalidar a decisão.

## Coerência das decisões humanas

| Decisão | Evidência acessível | Resultado da revisão |
|---|---|---|
| DQ-0001: família, catálogo local, menor prioridade e slug durável | `ROUND-LOG.jsonl:1`; `DECISION-FRONTIER.md:3`; `docs/adr/ADR-0001.md:19`; `PLAN-CONTEXT.md:11` | Preservada no ADR/HOW; corrigir a tradução para critérios do handoff em R1. |
| DQ-0002: manter `medium=terra` | `ROUND-LOG.jsonl:2`; `DECISION-FRONTIER.md:13`; `docs/adr/ADR-0001.md:23`; handoff `:20` | Preservada; ausência de terra geração 6 não autoriza outra família. |
| DQ-0003: recusa fail-closed | `ROUND-LOG.jsonl:3`; `DECISION-FRONTIER.md:23`; `docs/adr/ADR-0001.md:22`; handoff `:22` | Preservada, com erro nomeado e recusa antes de worktree, lease ou payload. |
| DQ-0004: especialistas Codex via `astra` | `ROUND-LOG.jsonl:4`; `DECISION-FRONTIER.md:33`; `PLAN-CONTEXT.md:11`; handoff `:14` | Preservada; compatibilidade da policy selada permanece obrigação explícita do plan. |
| DQ-0005: especialistas Claude `opus/xhigh` e `opus/high` | `ROUND-LOG.jsonl:5`; `DECISION-FRONTIER.md:43`; `docs/adr/ADR-0002.md:19`; `PLAN-CONTEXT.md:18` | Preservada; `fable` proibido e bloqueio operacional Claude explícito até existir caminho admissível. |

Não identifiquei decisão humana material perdida, nova família introduzida ou concessão de exceção ao piso dos workers. A regra de correspondência entre alias Claude e efetivo observado continua investigação de implementação explicitamente atribuída ao plan (`PLAN-CONTEXT.md:19`), não prova de funcionamento atual.

## Classificação e relatório do autor

**Manter `development-type: platform-devops`.** A classificação corrente é consistente em `PLAN-CONTEXT.md:8`, `DELIVERY-MAP.md:12` e handoff `:12`. O escopo altera resolução em core Python, assets e gates de despacho (`PLAN-CONTEXT.md:11`, `:18`; `DELIVERY-MAP.md:8` e `:14`). A parada desta sessão em `PLAN_ONLY_STOP` delimita a execução autorizada, não transforma o tipo da feature em documentação.

Rejeito a recomendação `documentation` de `interview-author-result.md:94` e `:115`; ela confunde o artefato desta entrevista com o comportamento de produto a desenvolver. O bundle já tomou a direção correta. Não é preciso editar retroativamente o relatório histórico do autor; este parecer registra a divergência e sua resolução.

As diferenças de fingerprint entre a tabela proposta pelo autor e a fronteira incorporada não mudam as cinco decisões nem criam duplicações na fronteira lida. A menção do autor a placeholders e `pending` descreve o estado que ele leu, não demonstra regressão do bundle posterior.

## Triagem, limites e fechamento

A proveniência documental é coerente: `CONTEXT.md:16`, handoff `:41` e `interview-author-result.md:18` ligam a feature a `tri-latest-models` e ao mesmo laudo. Contudo, os dois arquivos de triagem não fazem parte dos 11 autorizados; não foram abertos. Portanto, esta revisão confirma consistência das referências, não autentica seu conteúdo, hashes, o commit fonte ou os metadados imutáveis do work item.

O fato relatado de sete workers em `gpt-5.6-terra` não comprova isoladamente escolha incorreta: o próprio escopo preserva terra enquanto não houver opção preferida dessa família. A causa tratada é o pin permanente entre gerações, como explicado em `interview-author-result.md:33`; R1 impede que o handoff reintroduza a confusão entre geração global e preferência por família.

`CONSTITUTION-CHECK.md:89` mantém pendente a observação dos especialistas. Esta revisão não certifica bootstrap, modelo/esforço efetivos, independência observada pelo runtime, hash constitucional, estado Git ou testes; os respectivos comprovantes não estão no recorte autorizado. O coordenador deve finalizar essa evidência e a auditoria após corrigir R1/R2. O veredito desta revisão não autoriza implementar, publicar ou ultrapassar `PLAN_ONLY_STOP`.
