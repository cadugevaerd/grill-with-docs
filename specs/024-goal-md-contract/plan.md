# Implementation Plan: Contrato do goal.md

**Branch**: `feature/goal-instruct` | **Date**: 2026-08-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/024-goal-md-contract/spec.md`

## Summary

Entregar o texto normativo do `goal.md`: um documento que um goal loop segue para
conduzir as duas trilhas do protocolo — pré-ciclo GWD e ciclo externo de onze
etapas — parando por `GOAL-HOLD` em cada ponto de interação enumerado e sob a
cláusula residual.

A abordagem já está selada em ADR pela entrevista que produziu o handoff: o
documento é neutro em relação ao runtime de goal loop (ADR-0001), cobre as duas
trilhas separadas por `PLAN_ONLY_STOP` nomeado (ADR-0002), embute a condição de
parada na formulação julgada por meio de dois templates de objetivo normativos
(ADR-0004), enumera pontos de interação por trilha com cláusula residual
fail-closed (ADR-0005), e descreve a delegação a workers Orca como interna à
etapa, com a sessão principal permanecendo leader e única Evidence Boundary
(ADR-0006, ADR-0007).

Esta fase entrega **apenas** o arquivo de texto. Materialização pelo `init`
(FASE-002) e validador na suíte canônica (FASE-003) são fases seguintes.

## Technical Context

**Language/Version**: Nenhuma. O artefato desta fase é Markdown. O repositório
que o hospeda é Python >=3.10, somente biblioteca padrão.

**Primary Dependencies**: Nenhuma. O documento não pode depender de recurso
exclusivo de nenhum runtime de goal loop (FR-009), e o repositório não admite
dependência externa.

**Storage**: Arquivo versionado em Git. Nenhum estado em runtime.

**Testing**: `python3 tests/run_validators.py` — a suíte canônica precisa
permanecer verde. O validador específico do contrato do `goal.md` é entrega da
FASE-003; nesta fase o gate é a suíte existente não regredir e a revisão humana
do texto contra os critérios do spec.

**Target Platform**: Multiplataforma. O documento é lido por agentes rodando em
Linux, macOS e Windows; a matriz de CI cobre os três com Python 3.10 e 3.13.

**Project Type**: Asset documental de um plugin distribuído.

**Performance Goals**: N/A. O único orçamento relevante é o de turnos do goal
loop, que o documento instrui o operador a declarar (FR-005) e não controla.

**Constraints**:
- O documento não assume `token_budget`, transição de status persistida nem
  armazenamento local de nenhum runtime (ADR-0001, FR-009).
- Criar o arquivo sob `plugin/**` dispara a cláusula **Bump obrigatório do
  plugin**; o bump é entrega da FASE-003 e precisa ocorrer antes de qualquer
  merge que carregue esta fase.
- O texto é lido por LLM sob pressão de continuação: precisa ser inequívoco na
  parada, não apenas correto.

**Scale/Scope**: Um arquivo. Dois templates de objetivo. Sete pontos de
interação na trilha pré-ciclo, cinco na trilha do ciclo v4, mais a cláusula
residual. Dezoito requisitos funcionais.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Veredito | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | Cada ponto de interação do documento é rastreável a uma fonte nomeada — cláusula constitucional, seção do `WORKFLOW.md` ou código de recusa do core (FR-006). |
| Work item isolado e ownership | PASS | Todo artefato decisório vive sob `.grill/work-items/feature-goal-autopilot-6f0eaefce4064eebb6bc16d5734bee0c/`; esta fase escreve apenas em `specs/024-goal-md-contract/` e no asset declarado no escopo do work item. |
| Feature/fix plan-only | PASS | O documento planejado trata a travessia de `PLAN_ONLY_STOP` como parada obrigatória e não configurável (FR-008), logo não pode autorizar o que a cláusula proíbe. |
| Sequência obrigatória do desenvolvimento | PASS | O documento reproduz a sequência de onze etapas sem saltos e declara que reproduzir o resultado de uma etapa por meio próprio não a avança (FR-017). |
| Verify/review antes de ship | PASS | `ship` é ponto de interação obrigatório com autorização humana explícita, e os retornos when-blocked de `verify` e `review` são pontos de parada enumerados. |
| Fail-closed sem waiver | PASS | A enumeração fecha com cláusula residual (FR-007): situação não prevista para o loop em vez de autorizá-lo. |
| Rastreabilidade | PASS | Spec, plano e artefatos de desenho referenciam os ADRs que os originaram; o `ROUND-LOG.jsonl` do work item registra cada decisão. |
| Tier de modelo e esforço do worker Orca | PASS | O documento exige `--model`, `--effort` quando suportado, e conferência de `launch.effective` com bloqueio na divergência (FR-012), registrando a exceção de `implement-parallel` (FR-013). Nenhum worker foi despachado nesta fase. |
| Bump obrigatório do plugin | PASS (condicional) | Esta fase cria arquivo sob `plugin/**`. O bump é entrega da FASE-003 e precisa preceder o merge. Registrado em Complexity Tracking. |
| Release obrigatória por versão | PASS | Fora do escopo desta fase; a release é criada pelo pipeline no merge para `main`, conforme planejado na FASE-003. |
| Governance | PASS | A Constituição foi lida em UTF-8 e seu SHA-256 (`54d5522b…`) está fixado no `state.json` e no `CONSTITUTION-CHECK.md` do work item. Nenhum ADR desta fase a dispensa ou reinterpreta. |

**Veredito**: PASS. Nenhuma violação a justificar; a única ressalva é de ordem,
não de conformidade, e está em Complexity Tracking.

### Re-check pós-Fase 1

Os artefatos de desenho não introduziram violação nova. `contracts/stop-signal.md`
e `contracts/goal-objective-templates.md` reforçam **Fail-closed sem waiver** ao
fixarem forma e posição da sinalização e ao declararem a alternativa de parada
como parte da formulação julgada. `data-model.md` carrega a coluna *fonte* em
cada ponto de interação, que é o que **Evidência antes de afirmação** exige.
`quickstart.md` mantém o gate em não regredir a suíte existente, sem inventar
validador que pertence à FASE-003. Veredito mantido: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/024-goal-md-contract/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1 — estrutura normativa do documento
├── quickstart.md        # Fase 1 — como validar o contrato ponta a ponta
├── contracts/
│   ├── goal-objective-templates.md   # Os dois templates de objetivo
│   ├── stop-signal.md                # Forma e semântica do GOAL-HOLD
│   ├── interaction-points.md         # Par ponto→fonte; nasce em T001
│   └── essential-substrings.md       # Tupla ESSENTIAL congelada; nasce em T003
└── tasks.md             # Fase 2 (/speckit-tasks — não criado aqui)
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/
└── assets/
    └── GOAL.template.md      # ÚNICO artefato de produto desta fase

tests/
└── run_validators.py         # Suíte canônica; precisa permanecer verde
```

**Structure Decision**: o documento nasce já como asset do plugin, em
`plugin/skills/grill-with-docs/assets/GOAL.template.md`, ao lado de
`WORKFLOW.v4.template.md`. Nasce como template porque a FASE-002 vai
materializá-lo no projeto consumidor pela mesma máquina que fixa o
`WORKFLOW.md`; criá-lo primeiro em outro lugar e movê-lo depois produziria um
diff de movimentação sem ganho. Nenhum outro caminho é tocado nesta fase — em
particular, `ensure_workflow.py`, `grill_workspace.py` e `tests/` permanecem
intactos, porque materialização e validação são as duas fases seguintes.

## Complexity Tracking

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| A fase cria arquivo sob `plugin/**` sem fazer o bump que a cláusula exige | O bump é ato único por release e pertence à FASE-003; fazê-lo três vezes, uma por fase, produziria três versões publicadas para uma mudança só | Criar o arquivo fora de `plugin/**` e movê-lo na FASE-002 evitaria a ressalva, mas geraria um diff de movimentação puro e um período em que o asset existe num caminho que o contrato de distribuição não reconhece |
| A fase alterou `tests/validate_work_item_v3_contract.py`, que o plano declarava intacto | O bundle deste work item foi migrado para `grill-work-item/v3` por exigência da ativação Gauntlet, e o validador fixava `v2` para todo bundle rastreado — a suíte ficou vermelha por uma migração autorizada, não por defeito novo | Deixar a suíte vermelha até a FASE-003 esconderia uma regressão real atrás de um limite de fase; e mover a correção para lá exigiria que `verify` desta fase rodasse com a suíte quebrada, que é exatamente o que o gate existe para impedir |
