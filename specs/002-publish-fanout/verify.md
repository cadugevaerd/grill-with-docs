## Verify Report

Verdict: PASS
Source fingerprint: tree 865be940ae3243a8ae0ad07d9323072658bf228ed8f1bd444bb8221816e0fc75 / work 5ca57aa376734971ba8aa511e74f275034b333b684fb07fd8f7d0e7ba0ff7329 / plan 88814086ed1b31a2530b2b7b99f389353f1062e24107a7c01b06c9d3cc5f6479
Converge: CONVERGED

Evidência em `specs/002-publish-fanout/converge.md`, produzida contra clones dos dois marketplaces publicados.

### Operational Gates

| Gate | Command | Result | Evidence | Validator |
|---|---|---|---|---|
| tests | `python3 tests/run_validators.py` | PASS | 267 testes, exit 0, 1 skip de ambiente | orquestrador |
| tests (alvo) | `python3 tests/validate_publish_contract.py` | PASS | 30 testes, OK | orquestrador |
| build / lint / typecheck / format | — | SKIPPED | nenhuma dessas ferramentas existe no repositório | orquestrador |
| security | inspeção do manuseio de segredo no workflow | PASS | token vai por `http.extraheader`, nunca na URL do remote; `::add-mask::` antes de exportar; `persist-credentials: false` no checkout canônico | orquestrador |
| quickstart/contracts | publicador contra clones reais dos dois marketplaces | PASS | UPDATED, CREATED, UNCHANGED e BLOCKED conforme `contracts/cli.md` | orquestrador |
| workflow YAML | `yaml.safe_load` | PASS | jobs `release` e `publish`; `fail-fast: false`; `paths: plugin/**`; permissões mínimas | orquestrador |

### Diff Hygiene

- Alterados: dois arquivos novos em `tests/`, um workflow novo, artefatos de `specs/002-publish-fanout/`.
- Nada em `plugin/`; `ci.yml` intocado.
- Nenhum segredo, credencial ou arquivo gerado no diff.
- O segredo `MARKETPLACE_PUBLISH_TOKEN` **não existe** no repositório e não foi criado: instalar um PAT de escopo amplo é ato humano. Na sua ausência o workflow reprova no primeiro passo com erro nomeado.

### Executable Scenarios

Os cenários de `contracts/cli.md` foram exercitados contra os índices reais dos dois marketplaces e têm teste correspondente que roda sem rede e sem credencial. Os dois defeitos encontrados durante a convergência ganharam teste de regressão.

O que **não** foi exercitado: a publicação de ponta a ponta pelo GitHub Actions, porque depende do segredo. Fica para a FASE-003.

### Failures / Blockers

Nenhum. Limite conhecido e declarado: a prova é local; a primeira execução real do workflow ainda não aconteceu.

### Next Action

- PASS: run `/speckit.verify-review-ship.review`
