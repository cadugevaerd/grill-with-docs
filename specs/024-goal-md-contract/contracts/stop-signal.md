# Contrato: sinalização de parada

**Superfície**: a linha que o laço emite para devolver o controle ao humano. É o
que o juiz lê e o que o operador lê.

## Forma

```text
GOAL-HOLD: <motivo em uma frase>
```

## Regras

| Regra | Razão |
|---|---|
| Última linha da resposta | Texto no fim é o que o juiz pesa ao decidir sobre "a última resposta". |
| Linha própria, isolada | Motivo enterrado num parágrafo longo é material que o juiz pode não pesar. |
| Motivo em uma frase | Frase única força a nomear a causa em vez de narrar o percurso. |
| Cita o identificador do ponto | Código de recusa do núcleo quando existir, `HOLD-<TRILHA>-<NN>` quando não; ou a cláusula residual. Sem isso, duas paradas pelo mesmo motivo não são agrupáveis (FR-018, FR-019, SC-008). |
| Uma por resposta | Duas sinalizações na mesma resposta tornam ambíguo o que devolveu o controle. |

## Exemplos conformes

```text
GOAL-HOLD: HOLD-PRE-01 — DQ-0003 exige decisão de valor sobre a superfície de distribuição.
```

```text
GOAL-HOLD: PLAN_ONLY_STOP — handoff em .grill/work-items/<id>/handoffs/FASE-001-SPECIFY-HANDOFF.md; atravessar para specify é ato humano.
```

```text
GOAL-HOLD: cláusula residual — o registro de triagem existente diverge da rota declarada e nenhuma das duas leituras é reversível.
```

## Exemplos não conformes

| Texto | Por quê |
|---|---|
| `Preciso da sua confirmação para seguir.` | Não usa a forma; o juiz não tem como distinguir de narração. |
| `GOAL-HOLD` sem motivo | Devolve o controle sem dizer o que fazer com ele. |
| `GOAL-HOLD: preciso parar aqui` | Tem motivo mas não cita identificador de ponto nem a cláusula residual; duas paradas iguais ficam inagrupáveis. |
| `...portanto GOAL-HOLD: ship exige autorização, e enquanto isso vou preparando o próximo passo.` | Não é a última linha, não está isolada, e o texto seguinte contradiz a parada. |
| Duas linhas `GOAL-HOLD:` na mesma resposta | Ambíguo. |

## Semântica

`GOAL-HOLD` **satisfaz** o objetivo, porque os templates o declaram como
alternativa de conclusão. Ele não é erro, não é falha e não é bloqueio do
trabalho — é o contrato funcionando.

## Limite conhecido

Um juiz truncado ou teimoso pode devolver `done=false` mesmo com a linha
presente. O freio nesse caso é o orçamento de turnos declarado pelo operador, não
este contrato. Registrado em BL-0001.
