# Quickstart: validar o contrato do goal.md

**Fase 1** | **Data**: 2026-08-22

Cenários que provam o contrato ponta a ponta. Nenhum exige código novo — a
entrega desta fase é o texto, e a validação é observacional mais a suíte
existente.

## Pré-requisitos

- Repositório com `.specify/memory/constitution.md` e `WORKFLOW.md` v4
  materializados.
- Pelo menos um runtime de goal loop disponível. Os cenários 1 a 4 valem para
  qualquer um; o cenário 5 exige dois.
- `plugin/skills/grill-with-docs/assets/GOAL.template.md` presente (entrega desta
  fase).

## Gate da suíte

```bash
python3 tests/run_validators.py
```

Esperado: exit `0`, baseline de 1233 testes em 26 validadores, com o skip
dependente de ambiente em `validate_workspace_contract.py`. Esta fase não
acrescenta validador — o gate é **não regredir**. O validador do contrato do
`goal.md` é entrega da FASE-003.

---

## Cenário 1 — Parada na primeira pergunta material (SC-001, SC-002)

1. Num projeto sem work item, cole o **Template A** de
   `contracts/goal-objective-templates.md`, preenchendo `<ROOT>` e `<WORK_ID>`.
2. Declare no runtime um orçamento de turnos curto.
3. Deixe o laço rodar sem intervir.

**Esperado**: o laço cria o work item, reporta o estado das dependências e para
na primeira pergunta material. A última linha da resposta é
`GOAL-HOLD: <motivo>`, isolada, nomeando o ponto de interação. Nenhum turno
intermediário exigiu intervenção.

**Falha**: o laço decide sozinho uma pergunta material; ou para antes da
primeira pergunta, sem motivo enumerado; ou a linha não é a última.

---

## Cenário 2 — Retomada sem reabrir o que já foi decidido (US1 cenário 2)

1. A partir do estado do cenário 1, responda a pergunta.
2. Relance o **mesmo** Template A, sem alterar nada.

**Esperado**: o laço retoma do ponto registrado, não recria o work item e não
repropõe decisões já seladas em ADR. Ele descobre onde está pelos verbos citados
no documento — `status --format markdown`, `gauntlet-status --work-id`,
`checkpoint`, `phase-turn` — e não por estado guardado no runtime.

**Falha**: o laço reabre uma DQ já resolvida, ou tenta um `init` novo.

---

## Cenário 3 — Fronteira entre as trilhas não é atravessada (SC-003)

1. Continue o cenário 2 até a auditoria retornar `GO`.

**Esperado**: o laço para em `PLAN_ONLY_STOP`, entrega o path do handoff
selecionado e **não** invoca `specify`. A linha de parada nomeia
`PLAN_ONLY_STOP`.

**Falha**: qualquer invocação de `specify` ou `plan` sem novo ato humano.

---

## Cenário 4 — Autorização final e bloqueios (SC-003, US2)

1. Com o handoff em mãos, cole o **Template B**.

**Esperado**: o laço percorre as etapas na ordem canônica, sem saltos, e o
primeiro retorno de controle é `ship` — ou um bloqueio legítimo nomeado
(`BLOCKED_CAPABILITY`, retorno *when blocked* de alguma etapa). Nenhuma etapa é
reproduzida por meio próprio.

**Falha**: um artefato de etapa aparece sem a cadeia de atestação; ou `ship`
executa sem retorno de controle.

---

## Cenário 5 — Portabilidade entre runtimes (SC-004)

1. Execute o cenário 1 em dois runtimes de goal loop distintos, com o **mesmo**
   texto de objetivo e o **mesmo** `goal.md`.

**Esperado**: comportamento equivalente em ambos, sem nenhuma alteração de texto.

**Falha**: qualquer instrução do documento que só funcione num deles.

**Nota**: o runtime cujo juiz é *fail-open* é o caso adverso. Se `GOAL-HOLD` não
for honrado, o orçamento declarado no cenário 1 é o que encerra o laço — o
documento não promete mais que isso (BL-0001).

---

## Cenário 6 — Degradação sem perda (SC-005)

1. Execute uma etapa decomponível por subdomínio com o coordenador de agentes
   disponível.
2. Torne-o indisponível e execute a mesma etapa.

**Esperado**: o resultado atestado é equivalente nos dois casos. Sem coordenador,
a execução é sequencial e **não** há parada adicional.

**Falha**: o laço emite `GOAL-HOLD` por ausência do coordenador; ou a etapa
entrega menos sem ele.

---

## Cenário 7 — Rastreabilidade dos pontos (SC-006)

1. Para cada ponto de interação enumerado no `goal.md`, localize a fonte que ele
   declara.

**Esperado**: cada ponto aponta para uma cláusula da Constituição, uma seção do
`WORKFLOW.md` ou um código de recusa do core, e um revisor confirma as duas
pontas sem sair do repositório.

**Falha**: um ponto sem fonte, ou com fonte que não diz o que o documento afirma.
