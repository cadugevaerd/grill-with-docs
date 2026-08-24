# PLAN-CONTEXT

## FASE-001 — Versão de workflow derivada do documento
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002, ADR-0003
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW

**Sítios exatos.** Três arquivos, todos em `plugin/skills/grill-with-docs/`, verificados contra o código da 5.0.0:

| Sítio | Hoje | Depois |
|---|---|---|
| `assets/state.template.json:5` | `"workflow_version": "v4"` congelado | sobrescrito no `init` pelo marcador resolvido |
| `scripts/grill_workspace.py:687` (`state_template`) | toca apenas `value["workflow"]`; `development` sai do asset intacto | resolve o marcador, grava `development.workflow_version` e recusa quando o marcador não resolve |
| `scripts/ensure_workflow.py:111` | só `managed_version` (first-match) | ganha `sole_managed_version` ao lado, intacta a existente |

O campo `value["workflow"]` **não** é tocado: a 5.0.0 o renomeou para `schema` e o redefiniu como tag de forma do próprio bloco, o que o põe fora deste trabalho (ADR-0003).

**Ordem de resolução no `init`.** O `init` já fixa o `WORKFLOW.md` antes de montar o bundle, então o documento existe quando o marcador é lido; a leitura usa o texto já materializado, não uma segunda passada de rede ou disco fora da fronteira. `grill_workspace.py` já expõe `sibling("ensure_workflow")`, então nenhum import novo é criado. `workflow_info()` continua devolvendo `path` e `sha256`; a versão é resolvida em `state_template()`, que é o único lugar que escreve `development.workflow_version` e é alcançado pelos dois writers, `init` e `migrate`.

**Fail-closed.** Marcador ausente, duplicado ou fora de `ACCEPTED_WORKFLOW_MARKERS` recusa o `init` antes de qualquer escrita — sem staging, sem bundle parcial, coerente com o publish atômico já existente. A mensagem nomeia quantos marcadores foram encontrados e quais são aceitos; recusa que não diz o que fazer é correta e inútil.

**Restrição de dependência.** `audit_decisions.py` não é alterado por este trabalho: a asserção de estado que ele faz passou a ser sobre a forma do bloco, não sobre a versão do documento. Ele permanece stdlib puro, e continua sendo a referência de paridade do detector estrito — `ACCEPTED_WORKFLOW_MARKERS` e a regex de marcador seguem locais ao módulo. `ensure_workflow._load_grill_core` continua degradando a `None` de propósito.

**Blast radius do que não muda.** `managed_version` mantém semântica first-match para seus chamadores em `ensure_workflow`, para `workflow_v3.marker_version` e para os testes em `validate_workflow_v3_contract.py`. Os sítios de materialização dependem do `or VERSION` e não podem ver `None` onde hoje veem um marcador. `R8` deixou de valer: a 5.0.0 passou a derivar `SEQUENCE_BY_VERSION` de `grill_core.workflow_versions`, que já era o SSOT declarado.

**Compatibilidade da frota.** Os bundles já materializados declaram `development.workflow_version` pelo literal do asset e não são reescritos; `development_workflow_version()` continua lendo o que cada um declara. Nenhum deles muda de veredito. Essa invariância é caso de teste, não expectativa — ela é o que separa esta escolha do cross-check rejeitado em ADR-0001.

**Cobertura de teste.** A matriz mínima: zero marcador, um marcador v2/v3/v4, dois marcadores, marcador `v9` desconhecido. Cada caso é exercido nos dois detectores e comparado, e no `init` end-to-end. A fixture do `WORKFLOW.md` precisa ser o documento real materializado, não um texto derivado do código do detector — uma fixture mais limpa que a realidade já deixou passar bug de parsing aqui antes.

**Governança de distribuição.** A mudança toca `plugin/**`, então exige bump SemVer nos oito lugares travados por `tests/validate_distribution.py` — quatro manifests, a constante `VERSION` do validador e três headings de documentação. É cláusula constitucional, não convenção.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
