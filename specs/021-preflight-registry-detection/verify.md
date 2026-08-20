# Verify: Detecção de extensão pelo registro

**Date**: 2026-08-20 · **Branch**: `worktree-fix-preflight-ansi`

## Gates executáveis

| Gate | Comando | Resultado |
|---|---|---|
| Contrato novo | `python3 tests/validate_extension_detection.py` | 21 testes, OK |
| Contrato de dependências | `python3 tests/validate_dependencies_contract.py` | 34 testes, OK |
| Distribuição | `python3 tests/validate_distribution.py` | `distribution: OK` |
| Suíte completa | `python3 tests/run_validators.py` | **1087 testes, 21 validadores, exit 0** |

Baseline anterior: 1066 testes. Delta +21, todos do contrato novo. Zero `FAILED`, zero `ERROR`.

## Prova de que o teste testa o defeito

`tests/validate_extension_detection.py` foi escrito antes da correção e executado contra o código antigo: **21 falhas e 2 erros**. Depois da correção: 21 OK. Um contrato que nunca ficou vermelho não prova nada sobre o código que ele acompanha.

## Checklist de aceitação

| Grupo | Itens | Situação |
|---|---|---|
| A — fonte de verdade | A1-A4 | 4/4 automatizados, verdes |
| B — estado por extensão | B1-B4 | 4/4 automatizados, verdes |
| C — registro não legível | C1-C8 | 8/8 automatizados, verdes |
| D — ambiente íntegro | D1, D2 | D1 automatizado; **D2 manual, executado** (evidência abaixo) |
| E — contrato e regressão | E1-E6 | 6/6 verdes |
| F — higiene do diff | F1-F3 | 3/3 verdes |

## D2 — o cenário que originou SGD-16

```
$ python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py preflight .
preflight verdict: OK
dependencies verdict: OK
missing_required: []
```

```
$ python3 plugin/skills/grill-with-docs/scripts/ensure_dependencies.py . ; echo $?
verdict: OK
  spec-kit-extension-registry      present
  ext:git                          present   version=1.0.0
  ext:agent-assign                 present   version=1.0.0
  ext:bugfix                       present   version=1.0.0
  ext:verify-review-ship           present   version=0.4.2
0
```

Estado anterior no mesmo ambiente, sem nenhuma alteração de configuração: `MISSING-DEPENDENCY`, com `ext:git`, `ext:agent-assign` e `ext:verify-review-ship` em `missing`, `ext:bugfix` em `present` por falso positivo, e `version: null` nas quatro.

## Higiene de diff

13 arquivos modificados, 1 novo. 211 inserções, 58 remoções.

Conferido contra o escopo declarado em `assign.md`:

- **Dentro do escopo**: `ensure_dependencies.py`, `dependencies.json`, os dois validadores, os oito pontos de versão, `CHANGELOG.md`, os artefatos da spec.
- **Fora do escopo, intocados**: `.grill/**` (bundle auditado, hash preservado), `.specify/extensions/**` (terceiros vendorizados), `WORKFLOW.md`, `.specify/memory/constitution.md`, hooks, workflows de CI. **Zero arquivos tocados fora do declarado (F3).**
- `dependencies.json`: 33 inserções, **0 remoções** — nenhuma reformatação em massa mascarando a mudança real.

## Restrições do core preservadas

- Somente biblioteca padrão; nenhum import novo.
- Nenhum teste toca a rede, cria processo filho ou exige `specify`/`node`/`backlogctl` reais. `RefusingToolchain` falha o teste se a detecção tentar subprocess (A1).
- A mudança **remove** um subprocess por execução de preflight.
- Nenhum `except Exception` introduzido (F2, com teste).
- `SCHEMA` inalterado: `grill-dependencies/v1` (E1, com teste).

## Ressalva declarada

`undetermined` entra em `grill-dependencies/v1` sem trocar o identificador do schema. Decisão registrada em ADR-0004, com o custo nomeado: quem enumerar o conjunto de status por igualdade exata precisa ser atualizado sem que a versão o avise. Mitigado dentro do repositório pelos validadores; para fora, o consumidor que testa `status == "present"` permanece correto.

## Veredito

**PASS.** Todos os gates verdes, checklist completa, D2 provado no ambiente real. Pronto para `review`.
