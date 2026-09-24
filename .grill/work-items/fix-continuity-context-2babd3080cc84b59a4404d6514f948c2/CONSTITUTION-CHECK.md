# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "../../triage-evidence/continuity-context-debug.md",
        "docs/adr/ADR-0001.md#Contexto",
        "ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "A recusa foi reproduzida offline com quatro variantes (lider ACTIVE, lider RELEASED, contexto RELEASED) e correlacionada ao codigo em grill_workspace.py:1636 e :1640-1645; as duas ocorrencias ao vivo do T029 estao citadas com dispatch e codigo exatos.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json#work_id"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Bundle proprio fix-continuity-context-2babd3080cc84b59a4404d6514f948c2 na branch cadugevaerd/feat-new-subagents; nada escrito no diretorio de outro work item.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git status",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Trabalho do tipo fix: nenhum arquivo de produto ou de teste alterado nesta etapa; a entrega e o handoff e a sessao termina em PLAN_ONLY_STOP.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "state.json#development.workflow_version=v4"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "Sequencia v4 completa declarada, current_step=specify e demais etapas pending; este ciclo entrega o handoff que alimenta specify.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "verify e review permanecem pending e precedem ship; o handoff carrega suite verde, diff limpo e os sete cenarios como aceite.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md#Decisão",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "A tomada exige prova do host de dispatch terminal; lider ativo, ausencia de resposta e resposta ambigua continuam recusados, cada um com codigo nomeado. Nenhum waiver e pedido; BL-0001 fica registrado como adiamento explicito, nao como dispensa.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "DECISION-FRONTIER.md",
        "ROADMAP.md",
        "PLAN-CONTEXT.md",
        "DELIVERY-MAP.md",
        "REQUEST.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Tres rounds ligam DQ-0001 a ADR-0001, DQ-0002 a ADR-0002 e DQ-0003 ao escopo da fase; ROADMAP, PLAN-CONTEXT, DELIVERY-MAP e handoff referenciam o mesmo par de ADRs e DU-001; REQUEST aponta a triagem selada.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "ausencia de worker-start para este work item"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker Orca foi despachado para este work item: entrevista, laudo e triagem correram na sessao principal. A clausula volta a valer no ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "git status: nenhum caminho sob plugin/** modificado por este work item",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHY"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhum byte de plugin/** alterado neste trabalho plan-only. O plano altera plugin/**: o handoff registra bump patch 6.0.2 -> 6.0.3 nos oito pontos e a release como pre-requisito do ship.",
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
      "justification": "Constituicao lida somente leitura; hash gravado coincide com o arquivo em disco. Nenhuma emenda proposta e nenhum ADR pede waiver.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
