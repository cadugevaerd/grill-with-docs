## Verify Report

Verdict: PASS
Source fingerprint: tree eda0132e795fba921a0b21499e1f8a93675e688f7666a6723890beb934960cac / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan a67563382c5ff689ce514ad7e20a4b31422ccb06a7f7b7df68d20da86d2c110d   (gate reports excluded)
Converge: CONVERGED

### Operational Gates

| Gate | Command | Result | Evidence |
|---|---|---|---|
| tests | `python3 tests/run_validators.py` | PASS | 1018 testes, exit 0; entrada da fase era 1007 |
| tests (alvo) | `python3 tests/validate_dependencies_contract.py` | PASS | 32 testes, exit 0; eram 21 |
| distribution | `python3 tests/validate_distribution.py` | PASS | 3.1.0 nos oito lugares |
| forma real do defeito | detecção sobre árvore sintética espelhando o caso desta sessão | PASS | atalho e destino reportados como sombras distintas, ambos ocupam o nome |
| ambiente real | detecção sobre o repositório e o HOME correntes | PASS | nenhuma sombra; a colisão foi removida antes desta fase |
| build / lint / typecheck / format / security | — | SKIPPED | não declarados |
| matriz multi-SO | GitHub Actions | DEFERRED | SC-005 exige três sistemas; só o CI verifica |

### Diff Hygiene

Produção: um arquivo. Testes: um arquivo, onze casos. Documentação e oito superfícies de versão. Nenhum segredo, nenhum arquivo de ambiente.

### Executable Scenarios

Todos cobertos, com uma ressalva de plataforma declarada: os casos de atalho pulam onde symlink não é suportado, em vez de falhar — o mesmo tratamento que o validador de workspace já dá.

### Failures / Blockers

Nenhum.

### Next Action

- PASS: run `/speckit.verify-review-ship.review`
