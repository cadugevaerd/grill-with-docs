# FASE-001 — Probes Git por worktree e timeout público suficiente

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: STATUS-TIMEOUT, probe Git por worktree, timeout público suficiente
- ADRs: ADR-0001
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: backend
- Resultado observável: o comando público `status` (JSON e Markdown) deixa de bloquear com `STATUS-TIMEOUT` num workspace real com múltiplos work items/worktrees, mesmo quando a projeção leva mais de 5 segundos, porque o custo Git deixa de crescer com o número de work items e o timeout público passa a ter margem sobre o pior caso real.
- Atores: qualquer sessão ou automação que invoque `python3 grill_workspace.py status ROOT [--format markdown]` como pré-condição de trabalho.
- Cenários cobertos: workspace com um único work item; workspace com múltiplos work items no mesmo worktree; workspace com múltiplos worktrees reais; regressão que impeça a reintrodução do custo por item.
- Escopo incluído: correção do falso positivo (probes por worktree/repositório, timeout com margem), teste de regressão dedicado, bump SemVer obrigatório do plugin, atualização dos oito locais de distribuição (manifests, marketplaces, README, CHANGELOG) e revalidação dos gates de distribuição.
- Critérios de aceitação: `python3 tests/run_validators.py` passa; a suíte de status expõe um teste que trava o escopo por worktree; a versão do plugin e os oito locais de distribuição estão coerentes entre si.
- Escopo excluído: mudança de schema/formato do contrato `grill-status/v1`; novos códigos de status; qualquer otimização de performance além da necessária para eliminar o falso positivo.

## WHY
- Valor: o falso `STATUS-TIMEOUT` bloqueia o próprio comando de diagnóstico do workspace exatamente quando ele é mais necessário — num workspace real, com vários work items e worktrees acumulados —, tornando `status` inutilizável no cenário para o qual ele existe.
- Evidência: `.grill/evidence/grill-status-timeout-debug-report.md` prova causa raiz comprovada — a projeção real levou 10,56s e excedeu um `timeout=5` histórico, enquanto um contrafactual isolado confirmou que 5s falha e 30s conclui em 9,03s.
- Restrição: a correção não pode introduzir custo Git proporcional ao número de work items nem reduzir a margem do timeout abaixo do pior caso medido, sob risco de reintroduzir o mesmo falso positivo por outro caminho.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
