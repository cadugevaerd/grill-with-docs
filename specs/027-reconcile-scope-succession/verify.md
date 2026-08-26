## Verify Report

Verdict: PASS
Source fingerprint: tree 1c39f65b4dad64d77d7c38612d30ba7333e051a6cceb840c1cbb93363659ebf9 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan fb440b73d3784db6877322bfd708dbaeaa2943c9d45fd4cf8f9018b224e9f261   (gate reports and step receipts excluded)
Converge: CONVERGED

Feature: `specs/027-reconcile-scope-succession`
Base: `origin/main` v5.2.0, commit `f13c18ea487cdf0fe3ec070861cf799f8f49ceaf`
Head version: 5.2.1

Segunda execução deste gate. A primeira mediu sob uma regra de exclusão
defeituosa e por isso não podia ancorar `ship`; ver **Reexecução** abaixo.

### Converge Handoff

Outcome: `converged` — segunda passada, zero findings, `tasks.md` byte-idêntico.

A evidência do `converge` continua fresca: nenhum dos 11 caminhos declarados no
`WORK-ITEM.json` mudou entre o commit `7cb6529` (fecho do converge) e este HEAD.
Verificado por `git diff --name-only 7cb6529 HEAD -- <os 11>` e
`git status --porcelain -- <os 11>`, ambos vazios. O componente `plan` do
fingerprint (`fb440b73…`) é o mesmo `tasks.md` selado no receipt do `converge`.

### Reexecução: por que este relatório substitui o anterior

A primeira execução registrou `tree 90a82a5f… / work af0fa3d1…`. Aquele valor
não servia de âncora para `ship`, e a causa não era o código.

`converge.fingerprint_exclude` declarava `.grill/attestations/**`, caminho que
nunca existiu: sob o protocolo grill os bundles ficam em
`.grill/work-items/<work_id>/attestations/`. Cada etapa de gate cunha o próprio
receipt ali, então `verify` e `review` moviam o fingerprint entre as duas
medições e `ship` recusava por `STALE-EVIDENCE` — o laço que o comentário da
própria config descreve, acontecendo de fato. Reexecutar não resolvia: produzia
outro bundle e outro valor.

A correção foi autorizada explicitamente pelo humano depois do `ship` reportar
`BLOCKED`, e é mínima: acrescenta o padrão correto e a autorização humana de
`ship`, que é evidência sobre a entrega pela mesma razão. A detecção permanece
ativa sobre `WORK-ITEM.json`, evidência de triagem e `gauntlet.yaml` — não foi
usada uma exclusão cega de `.grill/**`.

Estabilidade comprovada antes de reexecutar os gates, não assumida: cunhar um
bundle no diretório de atestações e medir de novo devolve `tree` e `work`
idênticos.

Um segundo defeito apareceu ao aplicar a correção e está registrado na config:
o leitor de `fingerprint_exclude` para de coletar na primeira linha não-vazia
que não é item de lista, então um comentário **entre** itens descarta em
silêncio tudo o que vem depois. A primeira tentativa de correção caiu nisso.

### Operational Gates

| Gate | Command | Result | Evidence | Validator |
|---|---|---|---|---|
| tests | `python3 tests/validate_*.py` (27 arquivos) | PASS | 27 validadores, todos exit 0, reexecutados nesta árvore em dois blocos. A suíte completa via `run_validators.py` excede o limite de um único job neste ambiente, então foi executada por glob em dois lotes de 14 e 13; nenhum validador ficou de fora | leader |
| tests (contrato afetado) | `python3 tests/validate_workspace_contract.py` | PASS | 76 testes, 1 skip de ambiente (`test_reject_symlink_chain_accepts_macos_var_root_alias`). Eram 67 na base; +9 casos de sucessão | leader |
| tests (seletor do quickstart) | `python3 -m unittest tests.validate_workspace_contract -k succession` | PASS | 9 testes, OK. Confirma o seletor que `quickstart.md §2` promete | leader |
| distribution | `python3 tests/validate_distribution.py` | PASS | `distribution: OK`. Os oito pontos de versão concordam em 5.2.1 | leader |
| version bump | `python3 tests/check_version_bump.py --base-ref origin/main --json` | PASS | `{"verdict":"PASS","code":"BUMPED","base_version":"5.2.0","head_version":"5.2.1"}` | leader |
| build | — | SKIPPED | Não existe passo de build. Bundle Python de biblioteca padrão, distribuído como fonte | leader |
| lint | — | SKIPPED | Nenhuma configuração no repositório (`pyproject.toml`, `setup.cfg`, `ruff.toml`, `.flake8` ausentes) | leader |
| typecheck | — | SKIPPED | Nenhuma configuração (`mypy.ini` ausente). Type hints são convenção, não gate executável | leader |
| format | — | SKIPPED | Nenhum formatador configurado | leader |
| security | varredura do diff | PASS | Nenhuma chave, segredo, token, credencial ou bloco de chave privada no diff de código. Nenhum `.env`, `.pem` ou `.key` | leader |
| quickstart / contracts | `quickstart.md §1–§3` | PASS | Os três passos automatizáveis correspondem aos gates acima e todos passam. §4 e §5 são reprodução manual em repositório descartável; o comportamento que descrevem está travado por `test_reconcile_succession_targeted_dependency_authorizes_scope_overlap` e `..._preview_is_read_only_with_authorized_overlap` | leader |

Nenhum gate obrigatório foi inferido a partir de outro.

### Diff Hygiene

Diff contra `origin/main...HEAD`, em quatro grupos:

- **Escopo declarado (os 11 caminhos do `WORK-ITEM.json`)**: `grill_workspace.py`,
  `tests/validate_workspace_contract.py`, `tests/validate_distribution.py`, os
  quatro manifests, `SKILL.md`, `references/session-protocol.md`, `README.md`,
  `CHANGELOG.md`. Todos tocados; nenhum além deles.
- **Artefatos do ciclo**: `specs/027-reconcile-scope-succession/**`,
  `.grill/work-items/<work_id>/**`, `.specify/feature.json`, `.grill/gauntlet.yaml`.
- **Correção de gate autorizada**: `.specify/extensions/verify-review-ship/verify-review-ship-config.yml`.
  Fora do escopo declarado do work item e assumido como tal: é correção de
  ferramenta, não do produto, autorizada explicitamente após o `BLOCKED`.
- **Herdados da branch**: `.grill/triage-evidence/SGD-24-*.md` e
  `.grill/triage/tri-sgd24-scope-succession.json`, vindos de `748c33f`, intocados.

Verificações: nenhum arquivo não relacionado, nenhum gerado comitado
indevidamente, nenhum segredo, nenhum arquivo de ambiente. Nada staged ou
comitado por este gate. O componente `work` é o sha do vazio: não há mudança
pendente no escopo medido.

### Executable Scenarios

| Cenário | Suporte de teste |
|---|---|
| US1 — sucessor declarado atravessa (targeted e completo, ambas as direções) | `test_reconcile_succession_targeted_dependency_authorizes_scope_overlap`, `test_reconcile_succession_full_dependency_authorizes_scope_overlap_both_directions` |
| US2 — ausência, terceiro e transitividade continuam bloqueando | `test_reconcile_succession_negative_cases_still_flag_scope_overlap` |
| US3 — recusas independentes preservadas, cada uma no caminho que a emite | `test_reconcile_succession_preserves_full_path_refusals`, `test_reconcile_succession_preserves_targeted_path_refusals` |
| US4 — preview read-only, apply idempotente, recibo legado sem migração | `test_reconcile_succession_preview_is_read_only_with_authorized_overlap`, `test_reconcile_succession_targeted_apply_is_byte_idempotent_and_reuses_prior_receipt`, `test_reconcile_succession_full_apply_is_byte_idempotent_with_authorized_overlap` |
| Autorização é do prior nomeado, não de "declara qualquer coisa" | `test_reconcile_succession_multi_id_dependency_authorizes_only_the_declared_prior` |

Todo cenário executável declarado tem teste de suporte.

### Failures / Blockers

Nenhum.

Registrado sem efeito no veredito: `CHK025` permanece aberto como dívida
declarada — `SC-006` não define formalmente o que conta como falha nem menciona
o skip dependente de ambiente. Lacuna de redação do critério, não de
verificação; o gate mediu a suíte e ela fecha em exit 0 com o skip conhecido.
Decisão humana no gate `CHECKLIST-INCOMPLETE`; rastreado como `F5` em
`analysis.md`.

### Next Action

- PASS: run `/speckit.verify-review-ship.review`
