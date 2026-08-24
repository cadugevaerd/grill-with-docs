# Contrato: templates de objetivo

**Superfície**: o texto que o operador cola no goal loop. É a única interface do
documento com o runtime, e é **normativa** — sem ela nada garante a parada
(FR-003).

## Forma comum

Todo template tem quatro partes, nesta ordem:

1. **Alvo** — a trilha e o work item.
2. **Conclusão** — o que encerra a trilha.
3. **Alternativa de parada** — literal e obrigatória.
4. **Fecho** — declara que qualquer uma das duas cumpre o objetivo.

A alternativa de parada é literal porque precisa entrar na formulação **julgada**
pelo juiz do laço. Reescrevê-la como instrução separada ("se precisar parar,
avise") a tira do que é julgado e devolve o modo de falha que ela existe para
derrotar.

## Template A — trilha pré-ciclo

```text
Conduza a trilha pré-ciclo do grill-with-docs no repositório <ROOT>, para o work
item <WORK_ID>, seguindo goal.md na raiz. A trilha termina quando a auditoria
retornar GO e o path do handoff selecionado for entregue — ou quando a resposta
contiver a linha GOAL-HOLD:. Qualquer um dos dois cumpre este objetivo.
```

**Orçamento**: nesta trilha o operador declara, no próprio runtime, um limite de
**no máximo cinco turnos, com três como recomendado**, em vez de herdar o padrão
(FR-005). A trilha para na primeira decisão que exige julgamento, o que ocorre
tipicamente em um a três turnos; margem maior só multiplica continuações caso o
`GOAL-HOLD` não seja honrado. O padrão de um dos runtimes conhecidos é 20 turnos
— alto demais para esta trilha.

## Template B — trilha ciclo v4

```text
Conduza o ciclo externo de onze etapas do WORKFLOW.md no repositório <ROOT>, para
o work item <WORK_ID>, a partir do handoff <HANDOFF_PATH>, seguindo goal.md na
raiz. O ciclo termina quando ship concluir — ou quando a resposta contiver a
linha GOAL-HOLD:. Qualquer um dos dois cumpre este objetivo.
```

## Placeholders

| Token | Valor |
|---|---|
| `<ROOT>` | Caminho do Git root real do projeto. |
| `<WORK_ID>` | Identidade do work item, como aparece em `.grill/work-items/`. |
| `<HANDOFF_PATH>` | Path do handoff selecionado, entregue pelo fim da trilha A. |

## Invariantes

- A frase `ou quando a resposta contiver a linha GOAL-HOLD:` aparece em ambos os
  templates, literal.
- Nenhum template cita orçamento, status persistido ou armazenamento de runtime
  específico (FR-009).
- O Template B nunca é colado antes de a trilha A ter entregue o handoff:
  atravessar `PLAN_ONLY_STOP` é ato humano (FR-008).
