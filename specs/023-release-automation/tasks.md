# Tasks: Release automática por versão publicada

- [x] **T001** Medir o gap: confirmar que só existe a release `v2.4.1` e que `publish.yml` cria
      apenas a tag.
- [x] **T002** Escrever a spec com os requisitos de ordem, idempotência e ancoragem.
- [x] **T003** Adicionar o passo `Criar a release da tag, sem sobrescrever` ao job `release`.
- [x] **T004** Cobrir com cinco testes de contrato em `WorkflowWiring`.
- [x] **T005** Provar que os testes testam a mudança revertendo `publish.yml`.
- [x] **T006** Rodar a suíte completa e o gate de bump.
- [x] **T007** Verify e review.

## Dependências

T001 → T002 → T003 → T004 → T005 → T006 → T007.

## Resultado

`tests/validate_bump_gate_contract.py` de 45 para 50 testes. Suíte total sobe para 1108, exit 0.
Sem mudança em `plugin/**`, então sem bump de versão do plugin.

### O que a fase encontrou e o plano não previa

`publish.yml` nunca teve o shell validado — `test_both_workflows_have_valid_shell` cobria só
`bump-gate.yml` e `ci.yml`. O workflow que mais roda shell era o único sem essa guarda. Corrigido
junto, em teste próprio.

### Escopo que cresceu durante a execução

Só a guarda de shell acima, que é uma linha de cobertura sobre arquivo já existente.
