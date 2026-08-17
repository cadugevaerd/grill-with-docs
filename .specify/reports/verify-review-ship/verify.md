## Verify Report

Verdict: PASS
Source fingerprint: tree 81c0bd9b4b80b2cc9928ce22569d17666e857b64f38a2c0329cfe783505269a0 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan ac49cbc2c8496efb1077406d34bb3fae1f195f05f27c0d28360967c402f16c68   (gate reports excluded)
Converge: CONVERGED

Handoff: três passagens de `/speckit.converge`. A primeira retornou `tasks_appended` com T027 e T028; a segunda, `converged`; a terceira, disparada por mudanças de código feitas durante a revisão, retornou `tasks_appended` com T029 e agora fecha em `converged`. Este relatório se apoia na terceira. As duas versões anteriores deste relatório ficaram stale por mudança de fonte, conforme o próprio contrato exige.

### Operational Gates

| Gate | Command | Result | Evidence | Validator |
|---|---|---|---|---|
| tests | `python3 tests/run_validators.py` | PASS | 970 testes, exit 0, 1 skip dependente de ambiente; baseline de abertura era 940 | sessão |
| tests (alvo) | `python3 tests/validate_backlog_contract.py` | PASS | 52 testes, exit 0; eram 22 antes da fase | sessão |
| tests (sem backlogctl) | `HOME=/nonexistent python3 tests/validate_backlog_contract.py` | PASS | 52 testes, exit 0; prova que a cobertura não depende do binário nem do ambiente do operador, que é a condição da matriz de CI | sessão |
| distribution | `python3 tests/validate_distribution.py` | PASS | `distribution: OK` com 2.9.0 idêntico nos oito lugares | sessão |
| build | — | SKIPPED | projeto é biblioteca de scripts stdlib, sem etapa de build | sessão |
| lint / typecheck / format | — | SKIPPED | não há linter, type checker nem formatter declarados no repositório ou no CI | sessão |
| security | — | SKIPPED | nenhum gate de segurança declarado; varredura de segredo feita na higiene de diff | sessão |
| quickstart | `specs/015-backlog-bridge-unlock/quickstart.md` cenários 1, 2, 3, 6 | PASS | cenários 1, 2 e 6 executados; cenário 3 executado contra os três work items reais, devolvendo `PREVIEW` onde antes devolvia `BUNDLE-INTEGRITY` | sessão |
| quickstart (4) | aplicação real no backlog | SKIPPED | exige `--apply` contra o backlog do operador; é mutação e não foi autorizada para esta verificação | sessão |
| matriz multi-SO | GitHub Actions `ci.yml` | DEFERRED | SC-005 exige ubuntu, macos e windows em Python 3.10 e 3.13; só o CI verifica, e ainda não rodou nesta branch | CI |

### Diff Hygiene

47 arquivos no diff contra `main`, todos explicáveis: 2 arquivos de produção, 1 validador, 8 superfícies de versão, 20 artefatos do work item, 11 artefatos da spec, 2 documentos, `.specify/feature.json`.

- Nenhum arquivo gerado ou não relacionado.
- Nenhum segredo: varredura por `ghp_`, `github_pat_`, `AKIA`, blocos de chave privada e atribuições de senha ou segredo não retornou nada.
- Nenhum `.env`, `.pem`, `.key` ou arquivo de credencial.
- Nada foi encenado nem commitado por este gate além do próprio relatório.

### Executable Scenarios

Cada cenário do quickstart tem teste de suporte. Os três defeitos e as duas lacunas do converge têm regressão nomeada. A mudança de comportamento mais delicada — `TRANSITION-REFUSED` — foi observada em dado real do repositório antes de virar teste: `SGD-3` está `open` enquanto `BL-0001` está `resolved`, e não há transição legal entre os dois.

### Failures / Blockers

Nenhum.

Ressalva registrada, não bloqueante: SC-005 depende da matriz de CI e permanece não verificado até a branch ser empurrada. O gate local não substitui os três sistemas operacionais.

### Next Action

- PASS: run `/speckit.verify-review-ship.review`
