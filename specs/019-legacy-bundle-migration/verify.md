## Verify Report

Verdict: PASS
Source fingerprint: tree 422766057daecf81feb2cd3a77fdbee1a2bc08d66dd9e3378617a8735367f33d / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan c84eb5f54d0f1e06985ecd030da53d0b60862cb2e4a4ba9e13fc9bb12b0a179f   (gate reports excluded)
Converge: CONVERGED

### Operational Gates

| Gate | Command | Result | Evidence |
|---|---|---|---|
| tests | `python3 tests/run_validators.py` | PASS | 1027 testes, exit 0; entrada da fase era 1018 |
| tests (alvo) | `python3 tests/validate_backlog_contract.py LegacyMigration` | PASS | 9 casos, exit 0 |
| distribution | `python3 tests/validate_distribution.py` | PASS | 3.2.0 nos oito lugares |
| prévia contra dados reais | `backlog-migrate` sobre os quatro bundles do repositório | PASS | sete contrapartes a criar, uma já existente marcada `REUSED`; nada foi aplicado |
| build / lint / typecheck / format / security | — | SKIPPED | não declarados |
| matriz multi-SO | GitHub Actions | DEFERRED | SC-006 exige três sistemas; só o CI verifica |

### Diff Hygiene

Dois arquivos de produção, um de teste, documentação e oito superfícies de versão. Nenhum segredo.

### Executable Scenarios

A prévia contra os quatro bundles reais é a evidência mais forte desta fase: ela reproduz exatamente o diagnóstico que abriu o work item — dos oito registros de decisão, um só tinha chegado ao backlog — e mostra o caminho para os sete restantes, sem tocar em nada.

### Failures / Blockers

Nenhum.

Consequência aberta e deliberada: a migração dos bundles reais **não foi aplicada**. Ela cria itens no backlog do operador, e o contrato exige confirmação explícita. O comando está pronto e a prévia está verificada.

### Next Action

- PASS: run `/speckit.verify-review-ship.review`
