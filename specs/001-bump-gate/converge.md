# Converge — integração das tarefas e evidência executada

Todas as tarefas de `tasks.md` integradas na branch `001-bump-gate`. Evidência abaixo é execução real, não leitura de código.

## Cenários do handoff, contra repositório git real

Clone descartável a partir de `001-bump-gate`, base fixada no HEAD da branch. Comando: `python3 tests/check_version_bump.py --base-ref <BASE> --json`.

| Cenário | Código | Exit | Esperado |
|---|---|---|---|
| CEN-1 — muda só `tests/`, sem bump | `NO-PLUGIN-CHANGE` | 0 | conforme |
| CEN-2 — muda `plugin/` sem bump | `MISSING-BUMP` | 1 | conforme |
| CEN-3 — muda `plugin/` com bump 2.5.0 → 2.6.0 | `BUMPED` | 0 | conforme |
| CEN-4 — muda `plugin/` com versão reduzida 2.5.0 → 2.4.0 | `VERSION-REGRESSION` | 1 | conforme |

## Bordas

| Borda | Código | Exit |
|---|---|---|
| versão malformada (`2.5`) | `VERSION-UNREADABLE` | 2 |
| remoção de arquivo em `plugin/` sem bump | `MISSING-BUMP` | 1 |
| única mudança em `plugin/` é a própria versão | `BUMPED` | 0 |
| base inalcançável (SHA inexistente) | `VERSION-UNREADABLE` | 2 |

A última é a que importa para a cláusula fail-closed: sem base não há decisão possível, e o resultado é reprovação, não aprovação silenciosa.

## Suíte do repositório

`python3 tests/run_validators.py` → exit `0`.

```text
validate_backlog_contract.py       22 OK
validate_bump_gate_contract.py     26 OK
validate_checkpoint_contract.py    36 OK
validate_contract.py               30 OK
validate_dependencies_contract.py  21 OK
validate_distribution.py           distribution: OK
validate_status_contract.py        27 OK
validate_workflow_contract.py      14 OK
validate_workspace_contract.py     52 OK (skipped=1)
```

Total 228 testes. Baseline antes desta fase era 202; os 26 novos são de `validate_bump_gate_contract.py`.

## Fronteiras confirmadas

- `tests/check_version_bump.py` **não** é coletado pelo glob `validate_*.py` de `run_validators.py`, verificado por enumeração do glob.
- Nada foi criado ou alterado dentro de `plugin/`.
- A matriz de portabilidade existente em `ci.yml` permanece inalterada; o job novo é adicional e condicionado a `pull_request`.

## Reconvergência após achado de review

O gate de review encontrou um bypass e a correção mudou a fonte, o que invalida a evidência acima. Reexecutado.

**Achado**: com detecção de rename ligada, `git diff --name-only base...head` reporta apenas o destino. Mover um arquivo para **fora** de `plugin/` remove conteúdo do bundle publicado, mas era lido como `NO-PLUGIN-CHANGE`, exit `0`. Reproduzido em clone real.

**Correção**: `--no-renames` em `changed_paths`, que faz o caminho de origem sob `plugin/` reaparecer no diff. Três testes de regressão em `tests/validate_bump_gate_contract.py`, classe `GitLayer`.

| Vetor | Antes | Depois |
|---|---|---|
| mover arquivo de `plugin/` para fora, sem bump | `NO-PLUGIN-CHANGE`, exit 0 | `MISSING-BUMP`, exit 1 |
| rename dentro de `plugin/` | já reprovava | `MISSING-BUMP`, exit 1 |
| mudança só de modo (`chmod +x`) em `plugin/` | — | `MISSING-BUMP`, exit 1 |
| substituir arquivo de `plugin/` por symlink | — | `MISSING-BUMP`, exit 1 |
| copiar arquivo para dentro de `plugin/` | — | `MISSING-BUMP`, exit 1 |

Os quatro cenários do handoff e as quatro bordas originais foram reexecutados e permanecem conforme.

Suíte após a correção: `python3 tests/run_validators.py` → exit `0`, 231 testes. Os três testes novos elevam `validate_bump_gate_contract.py` de 26 para 29.
