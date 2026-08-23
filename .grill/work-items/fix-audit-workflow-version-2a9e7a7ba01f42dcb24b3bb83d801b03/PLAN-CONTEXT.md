# PLAN-CONTEXT

## FASE-001 — Versão de workflow derivada do documento
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW

**Sítios exatos.** Quatro arquivos, todos em `plugin/skills/grill-with-docs/`:

| Sítio | Hoje | Depois |
|---|---|---|
| `scripts/grill_workspace.py:691` | `value["workflow"] = {**workflow, "version": "v2"}` | versão vem do marcador resolvido |
| `assets/state.template.json:5` | `"workflow_version": "v4"` congelado | sobrescrito no `init` pelo marcador resolvido |
| `scripts/ensure_workflow.py:111` | só `managed_version` (first-match) | ganha `sole_managed_version` ao lado, intacta a existente |
| `scripts/audit_decisions.py:801` | `value.get("version") != "v2"` | `value.get("version") not in ACCEPTED_WORKFLOW_MARKERS` |

**Ordem de resolução no `init`.** O `init` já fixa o `WORKFLOW.md` antes de montar o bundle, então o documento existe quando o marcador é lido; a leitura usa o texto já materializado, não uma segunda passada de rede ou disco fora da fronteira. `grill_workspace.py:1129` já expõe `sibling("ensure_workflow")`, então nenhum import novo é criado. `workflow_info()` (`:645`) continua devolvendo `path` e `sha256`; a versão é resolvida no chamador e aplicada em `state_template()`, que é o único lugar que escreve os dois campos.

**Fail-closed.** Marcador ausente, duplicado ou fora de `ACCEPTED_WORKFLOW_MARKERS` recusa o `init` antes de qualquer escrita — sem staging, sem bundle parcial, coerente com o publish atômico já existente. A mensagem nomeia quantos marcadores foram encontrados e quais são aceitos; recusa que não diz o que fazer é correta e inútil.

**Restrição de dependência.** `audit_decisions.py` é stdlib puro e permanece assim: `ACCEPTED_WORKFLOW_MARKERS` já é local ao módulo (`:70`) e a mudança é de operador, não de import. `ensure_workflow._load_grill_core` continua degradando a `None` de propósito. A concordância entre os dois detectores é responsabilidade do teste de paridade, não de um módulo compartilhado — ver ADR-0002.

**Blast radius do que não muda.** `managed_version` mantém semântica first-match para seus 7 chamadores em `ensure_workflow`, para `workflow_v3.marker_version:356` e para os dois testes em `validate_workflow_v3_contract.py`. Em particular `ensure_workflow.py:335` e `:473` dependem do `or VERSION` na materialização e não podem ver `None` onde hoje veem um marcador.

**Compatibilidade da frota.** Os 9 bundles deste repositório carimbam `"v2"`; `"v2"` pertence a `ACCEPTED_WORKFLOW_MARKERS`, então nenhum deles muda de veredito. Essa invariância é caso de teste, não expectativa — ela é o que separa esta escolha do cross-check rejeitado em ADR-0001.

**Cobertura de teste.** A matriz mínima: zero marcador, um marcador v2/v3/v4, dois marcadores, marcador `v9` desconhecido. Cada caso é exercido nos dois detectores e comparado, e no `init` end-to-end. A fixture do `WORKFLOW.md` precisa ser o documento real materializado, não um texto derivado do código do detector — uma fixture mais limpa que a realidade já deixou passar bug de parsing aqui antes.

**Governança de distribuição.** A mudança toca `plugin/**`, então exige bump SemVer nos oito lugares travados por `tests/validate_distribution.py` — quatro manifests, a constante `VERSION` do validador e três headings de documentação. É cláusula constitucional, não convenção.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
