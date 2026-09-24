# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "../../triage/latest-models-debug.md",
        "docs/adr/ADR-0001.md#Contexto",
        "ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Causa raiz reproduzida por resolve_model (codex small/medium -> gpt-5.6-luna/terra) contra o catalogo local que lista gpt-6-*; 7 launch-verified reais com gpt-5.6-terra. A ausencia de alias no Codex foi verificada por codex debug models e codex debug prompt-input no codex-cli 0.155.1 nesta sessao.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json#work_id"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Trabalho no bundle proprio feature-latest-models-dbf134a84fc14114a438bddf1da709b6 na branch cadugevaerd/fix-latest-models; nenhum byte escrito em outro work item; triagem em .grill/triage.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git status: somente .grill/",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Trabalho do tipo feature. Nenhum arquivo de produto ou teste alterado; entrega e handoff e a sessao termina em PLAN_ONLY_STOP sem specify, plan ou implementacao.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "state.json#development.workflow_version=v4"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "Bundle declara a sequencia v4 canonica completa em current_step=specify com todas as etapas pending; este ciclo entrega o handoff que alimenta specify.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "verify e review pending precedem ship; o handoff carrega suite verde, git diff --check e os sete cenarios offline como criterios de aceite.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md#Decisão",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Catalogo ausente, ilegivel ou familia sem slug listado recusam com TIER-MODEL-UNRESOLVED antes de worktree/payload, sem fallback para modelo antigo; FRONTIER-MODEL-FORBIDDEN preservado. Nenhum waiver pedido.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "DECISION-FRONTIER.md",
        "ROADMAP.md",
        "PLAN-CONTEXT.md",
        "DELIVERY-MAP.md",
        "../../triage/tri-latest-models.json"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "R-0001..R-0004 ligam DQ-0001..DQ-0004 ao ADR-0001; ROADMAP, PLAN-CONTEXT, DELIVERY-MAP e handoff referenciam ADR-0001 e DU-001 sem BL; a triagem tri-latest-models aponta o laudo.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "ausencia de worker-start para este work item"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker Orca foi despachado por este work item: entrevista, triagem e leitura de codigo correram na sessao lider. A clausula volta a valer no ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "git status: nenhum caminho sob plugin/** modificado",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHY"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhum byte de plugin/** alterado por este work item plan-only. O handoff registra a obrigacao de bump nos oito pontos de versao e release como pre-requisito do ship do ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json#status=in-progress"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Trabalho plan-only nao publica versao, tag nem release; a clausula e exercida pelo pipeline no merge do ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json#constitution.sha256=54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
        "CONSTITUTION-CHECK.md#constitution_sha256"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "Constituicao lida somente leitura; hash gravado coincide com o arquivo; nenhuma emenda proposta e nenhum ADR pede waiver.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
