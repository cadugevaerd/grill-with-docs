# Evidência constitucional — hotfix 6.0.1

Constituição `.specify/memory/constitution.md`, sha256 `54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569`. Base `origin/main` `29c96681b714ac7ca827e79a5c4ba405795f71f2` (v6.0.0).

| Cláusula | Status | Evidência | Justificativa |
|---|---|---|---|
| Evidência antes de afirmação | PASS | `.grill/triage-evidence/hotfix-6-0-1-debug-report.md` (causa raiz comprovada, reproduções em cópia limpa de 29c9668); triagem selada `.grill/triage/tri-hotfix-6-0-1.json`; CI run 35009700240 | Cada defeito e cada correção têm reprodução e teste objetivos. |
| Work item isolado e ownership | PASS | Worktree dedicada `hotfix-6-0-1`, branch `cadugevaerd/hotfix-6-0-1`; bundle criado por este verbo `hotfix` com identidade própria | Não escreve em outro work_id; trabalho isolado do work item `feature-new-subagents-unified`. |
| Feature/fix plan-only | NOT-APPLICABLE→PASS | Rota triada `hotfix`, severidade `critical`, `production_impact=true` | Hotfix é a trilha executável prevista; feature/fix não são usados. |
| Sequência obrigatória do desenvolvimento | PASS | Trilha hotfix-fast com `HOTFIX-GO` fail-closed, prevista no SKILL.md para incidente | A exceção operacional fechada exige escopo, reprodução, teste de correção e rollback, todos presentes. |
| Verify/review antes de ship | PASS | Suíte completa `tests/run_validators.py` e `git diff --check` na worktree antes do commit (log `/tmp/gwd-hotfix-6.0.1-suite.log`); check de portabilidade (timeout do job elevado para 45 min em `.github/workflows/ci.yml`, pois a suíte completa excede 20 min e a matriz era cancelada) e bump gate da PR antes do merge | Ship só após verificação executável verde e gate de PR. |
| Fail-closed sem waiver | PASS | Diff de `_full_read` só remove eventos anteriores à última compactação; nenhum gate relaxado | A correção torna a aceitação de carga mais restritiva; não há waiver. |
| Rastreabilidade | PASS | Triagem `tri-hotfix-6-0-1`, bundle hotfix, commit e PR referenciam o laudo e o run de CI | Mudança rastreável a work item, triagem e commit. |
| Tier de modelo e esforço do worker Orca | NOT-APPLICABLE | Nenhum worker Orca criado para o hotfix; execução na sessão ativa | Cláusula aplica-se a `worker-start`. |
| Bump obrigatório do plugin | PASS | 6.0.0→6.0.1 em `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `tests/validate_distribution.py`, headings de `SKILL.md`, `session-protocol.md`, `README.md`; `## 6.0.1` no CHANGELOG; `python3 tests/validate_distribution.py` → `distribution: OK` | Alteração em `plugin/**` acompanha bump SemVer patch idêntico nos oito pontos. |
| Release obrigatória por versão | PASS | Publicação apenas pelo workflow `publish to marketplaces` no merge para `main`, que cria tag `v6.0.1` e Release | Nenhuma tag ou release manual; tag v6.0.0 não é reutilizada. |
