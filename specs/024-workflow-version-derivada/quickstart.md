# Quickstart: validar a versão derivada

**Phase**: 1 | **Contratos**: [contracts/cli.md](./contracts/cli.md) | **Modelo**: [data-model.md](./data-model.md)

Cenários executáveis que provam a feature ponta a ponta. Todos usam repositório temporário — nenhum toca o checkout real.

## Pré-requisitos

- Python >= 3.10, somente biblioteca padrão
- `git` disponível (a criação de work item resolve o Git root)
- Nenhuma rede, nenhum `specify`/`node`/`backlogctl` real: use `GRILL_SKIP_DEPENDENCIES=1` e `--skip-backlog`

## Suíte completa

```bash
python3 tests/run_validators.py
```

Esperado: exit 0. Baseline antes desta mudança: 1233 testes em 26 validadores, com 1 skip dependente de ambiente. A contagem sobe; o exit não muda.

## Cenário 1 — Registro verdadeiro sobre documento v4 (US1)

```bash
REPO=$(mktemp -d) && git -C "$REPO" init -q
GRILL_SKIP_DEPENDENCIES=1 python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  init "$REPO" --type fix --slug demo --skip-backlog
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['workflow']['version'], d['development']['workflow_version'])" \
  "$REPO"/.grill/work-items/*/state.json
```

Esperado: `v4 v4`. Hoje imprime `v2 v4`.

```bash
GRILL_SKIP_DEPENDENCIES=1 python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  audit "$REPO" --work-id "$(basename "$REPO"/.grill/work-items/*)"
```

Esperado: nenhum finding contendo `workflow version divergence`.

## Cenário 2 — Documento v3 preservado (US2)

Materialize um `WORKFLOW.md` v3 no repositório temporário **antes** da criação, pelo próprio `ensure_workflow` — nunca escrevendo o texto à mão (FR-009). Crie o work item e leia os dois campos.

Esperado: `v3 v3`, e a projeção de status classificando o bundle pela sequência v3, com as etapas `agent-assign`/`agent-execute` no lugar de `partition`/`implement-parallel`.

## Cenário 3 — Declaração ausente ou múltipla (US3)

Para cada caso da matriz de [research.md](./research.md) R5 — sem marcador, dois marcadores iguais, dois distintos, um `v9` desconhecido — tente criar o work item.

Esperado, em todos: recusa `WORKFLOW-MARKER-UNRESOLVED`, exit 2, com `markers_found` e `accepted` na saída, e **nenhum diretório sob `.grill/work-items/`** depois da tentativa. Conferir a ausência é parte do cenário: é ela que prova "antes de qualquer escrita".

## Cenário 4 — Frota intacta (US4)

```bash
for W in .grill/work-items/*/; do
  python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
    audit . --work-id "$(basename "$W")" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['work_id'], d['verdict'])"
done
```

Rode antes e depois da mudança e compare as duas saídas. Esperado: idênticas, linha a linha. Os 9 bundles deste repositório carimbam `"v2"` e devem manter o veredito exato.

## Cenário 5 — Paridade dos detectores (FR-006)

Para cada documento da matriz R5, compare o que `ensure_workflow.sole_managed_version` resolve com o que a verificação de `audit_decisions` decide.

Esperado: mesma quantidade de declarações reconhecida e mesma decisão de aceitar ou recusar, em 100% dos casos. Divergência em qualquer caso reprova — é ela que substitui o módulo compartilhado recusado em ADR-0002.

## Cenário 6 — Bump de distribuição (FR-010)

```bash
python3 tests/validate_distribution.py
```

Esperado: exit 0, com a versão nova idêntica nos oito pontos fixados — quatro manifests, a constante `VERSION` do validador e três headings de documentação.
