# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "CONTEXT.md#Glossário",
        "DECISION-FRONTIER.md",
        "ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada termo do glossário e cada DQ citam arquivo lido nesta sessão (dependencies.json, ensure_dependencies.py:24,222-320, installed_plugins.json, ~/.codex/config.toml:59, plugin.json do ponytail 4.9.0, saída de `claude plugin install --help` e `codex plugin --help`). Nenhuma afirmação repousa em memória.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json#work_id",
        "git status: único caminho novo é .grill/work-items/feature-add-ponytail-d8c0bd7e8ffd4442a806b2e1067ed06c/"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Bundle próprio com identidade imutável feature-add-ponytail-d8c0bd7e8ffd4442a806b2e1067ed06c, em worktree e branch dedicadas (cadugevaerd/chore-add-ponytail). Nenhum byte escrito fora do bundle nem em outro work item.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#status",
        "ROADMAP.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Tipo feature. A sessão produz apenas artefatos de decisão e termina em PLAN_ONLY_STOP; nenhum arquivo em plugin/**, CLAUDE.md ou AGENTS.md é alterado aqui.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "WORKFLOW.md"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "O bundle nasce com a sequência v4 de onze etapas e current_step=specify; a entrevista não avança nem pula etapa alguma.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhuma etapa do ciclo executor iniciou; verify, review e ship permanecem pending. A cláusula volta a valer no ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json#backlog_skipped",
        "DECISION-FRONTIER.md"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Backlog não vinculado neste worktree foi carimbado como backlog_skipped=true, visível em toda auditoria, e não escondido. Ambiguidades viraram DQs abertas em vez de suposição.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json#immutable",
        "ROUND-LOG.jsonl",
        "DELIVERY-MAP.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Identidade, branch, HEAD e base_commit selados em WORK-ITEM.json; cada rodada da entrevista registra evidência e artefatos alterados; DU/MOD mapeados no DELIVERY-MAP.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "ausência de chamada a orca orchestration worker-start nesta sessão"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker Orca foi criado: entrevista e leitura correram na sessão principal. A cláusula governa despacho de worker e volta a valer se o ciclo executor despachar um.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "git status: plugin/** intocado",
        "DECISION-FRONTIER.md#DQ-0007"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Esta sessão não altera plugin/**. O bump é decisão registrada (DQ-0007) e obrigação do ciclo executor antes do merge.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "git status: nenhuma tag ou release tocada"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Nenhuma versão é publicada nesta sessão; a release é produzida pelo pipeline no merge, fora do escopo plan-only.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "WORK-ITEM.json#immutable.constitution",
        "CONSTITUTION-CHECK.md#constitution_sha256"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "Constituição lida em UTF-8, hash 54d5522b… registrado no metadata e neste check; nenhum ADR ou decisão local a dispensa ou enfraquece.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
