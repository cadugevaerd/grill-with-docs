# Evidência constitucional — hotfix 9.3.1 (SGD-45)

Constituição `.specify/memory/constitution.md`, sha256 `54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569`. Base `origin/main` `38b161d98596c12a226ea63fb1dbe9007683657b` (v9.3.0).

| Cláusula | Status | Evidência | Justificativa |
|---|---|---|---|
| Evidência antes de afirmação | PASS | `.grill/triage-evidence/sgd-45-debug-report.md` (causa raiz comprovada por probe live no Orca e leitura do bundle); triagem selada `.grill/triage/tri-sgd-45-worker-worktree-orca.json`; teste de regressão em `tests/validate_gauntlet_run_contract.py` | Defeito e correção têm reprodução e teste objetivos; a correção candidata original foi falsificada antes de ser implementada. |
| Work item isolado e ownership | PASS | Worktree dedicada `hotfix-worker-worktree-orca`, branch `cadugevaerd/hotfix-worker-worktree-orca`; bundle criado pelo verbo `hotfix` com identidade própria | Não escreve em outro work_id nem no projeto consumidor. |
| Feature/fix plan-only | NOT-APPLICABLE | Rota triada `hotfix`, severidade `critical`, `production_impact=true` | Hotfix é a trilha executável prevista; feature/fix não são usados. |
| Sequência obrigatória do desenvolvimento | PASS | Trilha hotfix-fast com `HOTFIX-GO` fail-closed | Exceção operacional fechada com escopo, reprodução, teste de correção e rollback presentes. |
| Verify/review antes de ship | PASS | `python3 tests/run_validators.py --jobs 0` e `git diff --check` antes do commit; bump gate e CI da PR antes do merge | Ship só após verificação executável verde e gate de PR. |
| Fail-closed sem waiver | PASS | Guard `orphaned is False` de `agent_runtime.py` intacto; só muda onde o worktree nasce | Nenhum gate relaxado; o worker passa a satisfazer o guard existente. |
| Rastreabilidade | PASS | Backlog SGD-45, triagem `tri-sgd-45-worker-worktree-orca`, bundle hotfix, commit e PR referenciam o laudo | Mudança rastreável a item de backlog, triagem e commit. |
| Tier de modelo e esforço do worker Orca | NOT-APPLICABLE | Nenhum worker Orca criado para o hotfix; execução na sessão ativa | Cláusula aplica-se a `worker-start`. |
| Bump obrigatório do plugin | PASS | 9.3.0→9.3.1 nos oito pontos (quatro manifests, `VERSION` do validador, headings de `SKILL.md`, `session-protocol.md`, `README.md`); `## 9.3.1` no CHANGELOG; `validate_distribution.py` verde | Alteração em `plugin/**` acompanha bump SemVer patch. |
| Release obrigatória por versão | PASS | Publicação apenas pelo workflow `publish.yml` no merge para `main`, que cria tag `v9.3.1` e Release | Nenhuma tag ou release manual. |
