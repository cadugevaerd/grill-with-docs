# Baseline — T001

Comando: `python3 tests/run_validators.py`, executado a partir da raiz do worktree
(`/home/carlosaraujo/Documentos/Projetos/grill-with-docs/.git/grill/wt-run-9dc83b33c8caf359c612ac62-p01-a`),
sob `python3`. Rodado duas vezes de forma independente para descartar flutuação; os dois runs
concordam byte a byte nas contagens abaixo (exit code, validadores executados, soma de testes).

## Exit code

**`exit=1`** — lido diretamente do `$?` do processo `python3`, nunca de um pipe.

`tests/run_validators.py` é fail-fast: pára no primeiro `validate_*.py` que retorna código
não-zero e propaga esse código.

## Contagem de validadores

- **26** validadores registrados no repositório (glob `tests/validate_*.py`).
- **22** validadores chegaram a iniciar (`==> nome.py` impresso) antes do runner parar.
- **21** desses 22 terminaram OK.
- **1** falhou: `validate_work_item_v3_contract.py` — é o que interrompe o runner.
- **4** nunca chegaram a rodar (ordem alfabética pós-falha): `validate_workflow_contract.py`,
  `validate_workflow_v3_contract.py`, `validate_workflow_versions_contract.py`,
  `validate_workspace_contract.py`.

## Contagem de testes

**1077** testes somados de todos os blocos `Ran N tests` efetivamente impressos (21 blocos de
validadores com relatório `unittest`, incluindo o bloco `Ran 84 tests` do validador que falhou;
`validate_distribution.py` não imprime bloco `unittest`, só `distribution: OK`, e por isso não
soma nenhum bloco).

## Skips

**0** skips observados nesta execução (nenhuma ocorrência de `skipped=` nem de `... skipped` na
saída). O skip dependente de ambiente documentado para `validate_workspace_contract.py`
(ver `CLAUDE.md`) não pôde ocorrer porque esse validador está entre os 4 que nunca chegaram a
rodar — o runner já havia parado antes de alcançá-lo.

## Falha observada

`validate_work_item_v3_contract.py::WorkItemV3Contract::test_tracked_repository_bundles_stay_readable`
(`bundle='fix-audit-workflow-version-2a9e7a7ba01f42dcb24b3bb83d801b03'`):

```
AssertionError: 'grill-work-item/v3' != 'grill-work-item/v2'
- grill-work-item/v3
?                  ^
+ grill-work-item/v2
?                  ^
```

O bundle rastreado deste próprio work item está gravado com `schema: grill-work-item/v3`, mas o
teste espera `grill-work-item/v2` para bundles rastreados no repositório. É estado real do
worktree no momento da captura da linha de base — T001 só observa e registra, não corrige.

## Runs de verificação

Dois runs independentes, output redirecionado a arquivo, exit code lido do `python3`:

1. `tests/run_validators.py > <scratchpad>/p01a-baseline-run.txt 2>&1; echo "EXITCODE:$?"` → `EXITCODE:1`
2. `tests/run_validators.py > /tmp/suite-p01a.log 2>&1; echo "exit=$?"` → `exit=1`

Ambos: 22 validadores iniciados, 21 blocos `Ran N tests`, soma de 1077 testes, mesma falha em
`validate_work_item_v3_contract.py`.

---

## Superada em 2026-08-24 — medição vigente

A medição acima registra o repositório **antes** da correção de
`test_tracked_repository_bundles_stay_readable`, e continua aqui porque é a evidência que
levou àquela correção: foi este `exit=1` que expôs a exclusão mútua entre `gauntlet-init`,
que recusa bundle fora de `grill-work-item/v3`, e a asserção que exigia `v2` em todo bundle
rastreado.

Corrigido em `55e1ec1`. A linha de base contra a qual as mudanças desta feature devem ser
medidas passa a ser:

| Métrica | Valor |
|---|---|
| exit code | **0** |
| validadores | 26, todos executados |
| testes | **1239** |
| falhas | 0 |
| skips | 1 (dependente de ambiente, em `validate_workspace_contract.py`) |

Medido com `python3 tests/run_validators.py` redirecionado para arquivo, com o exit code lido
do próprio `python3` — nunca de um pipe, que devolve o código do último estágio e mente.

**T028 compara contra esta tabela, não contra a medição fail-fast acima**: aquela parou no
primeiro validador vermelho e por isso soma 1077 testes de 22 validadores, não o total do
repositório.

---

## Reconfirmação em 2026-08-24 (run run-d14b5a3163cb94301fa29292)

Medição vigente reconfirmada na base `516370c`, worker `p01-a`. `tests/run_validators.py`
executado a partir da raiz do worktree, `exit` lido de `echo "exit=$?"` (nunca de pipe): **0**.
26 validadores (`==> `), 1239 testes somados de todos os blocos `Ran N tests`, 0 `FAILED`/`ERROR`,
25 blocos `OK`, 1 skip (`skipped=1`, `validate_workspace_contract.py`, dependente de ambiente).
Bate com a tabela "Superada em 2026-08-24 — medição vigente" acima; nenhum valor foi reescrito.
