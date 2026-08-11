# Analyze — consistência, riscos e dependências

## Cobertura de requisitos

| Requisito | Tarefas | Situação |
|---|---|---|
| FR-001 tag imutável no canônico | T-004 | coberto pelo job `release`, que recusa remarcação |
| FR-002 atualizar version/ref/sha | T-001, T-002 | coberto |
| FR-003 preservar campos curados | T-001, T-002 | coberto e testado com vizinho compactado à mão |
| FR-004 criar entrada ausente | T-001 | coberto, schema do Codex |
| FR-005 idempotência | T-001, T-002 | coberto; `UNCHANGED` não escreve e não commita |
| FR-006 alvos independentes | T-004 | `fail-fast: false` na matriz |
| FR-007 disparo por merge filtrado | T-004 | `push` em main com `paths: plugin/**` |
| FR-008 disparo manual | T-004 | `workflow_dispatch` |
| FR-009 falhar em vez de adivinhar | T-001, T-002 | índice ausente, JSON inválido e `source` inesperado reprovam |

Nenhum requisito órfão; nenhuma tarefa sem requisito.

## Riscos

1. **Segredo ausente.** `MARKETPLACE_PUBLISH_TOKEN` não existe no repositório. O workflow reprova no primeiro passo com erro nomeado, em vez de seguir e falhar difuso. Instalar o segredo é ato humano; a fase entrega o pipeline, não a credencial.
2. **Escopo do token.** ADR-0004 escolheu o PAT classic existente, que concede `admin:org`, `admin:enterprise` e `delete_repo`. Este workflow precisa apenas de `contents: write` em dois repositórios. Acompanhado em `SGD-3`.
3. **Remarcação de tag.** Reescrever uma tag publicada mudaria o que já foi entregue a quem instalou. O job recusa quando a tag existe apontando para outro commit. Se alguém apagar a tag manualmente, a proteção não alcança — é limite conhecido.
4. **Reformatação de índice.** Reserializar o JSON inteiro normalizaria entradas vizinhas escritas à mão e afogaria uma mudança de três linhas. Mitigado por edição textual cirúrgica, coberta por teste que exige exatamente três linhas alteradas e vizinhas idênticas.
5. **Publicação parcial.** Um alvo pode falhar com o outro publicado. Aceito em ADR-0005; a idempotência garante que o re-run converge.
6. **Divergência de mecanismo.** Se alguém converter a entrada para vendorização (`source: local`), o publicador recusa em vez de reconverter, porque isso mudaria a distribuição sem decisão registrada.

## Dependências

`T-001 → T-002 → {T-003, T-004} → T-005`. Nenhum ciclo, nenhuma dependência externa nos testes: sem rede, sem credencial, sem os repositórios reais.

## Nota sobre o processo

A matriz de checkpoints do grill está esgotada pela FASE-001 e recusa novas transições (`SGD-6`). Os onze passos foram percorridos e evidenciados aqui; o que falta é o registro na matriz, não a execução.

## Veredito

Artefatos consistentes após a correção de premissa. Nenhum bloqueio para a implementação.
