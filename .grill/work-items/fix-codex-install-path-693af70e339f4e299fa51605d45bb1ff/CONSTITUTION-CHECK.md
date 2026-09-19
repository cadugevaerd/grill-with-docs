# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "../../triage-evidence/codex-install-path-debug.md",
        "docs/adr/ADR-0001.md#Contexto",
        "ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "A causa raiz foi reproduzida offline com a saída real de codex plugin list --json 0.154.0 e confirmada por contrafactual de uma variável (so installPath separa falha de sucesso); o laudo cita agent_runtime.py:204, :218-219, :512-515 e o rollout Codex do C1. O ADR cita ensure_dependencies.py:278-288 conferido nesta sessao.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json#work_id"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "O trabalho vive no bundle proprio fix-codex-install-path-693af70e339f4e299fa51605d45bb1ff, na branch cadugevaerd/feat-new-subagents, como os fixes precedentes do mesmo ciclo. Nenhum byte foi escrito no diretorio de outro work item; o registro de triagem fica em .grill/triage e .grill/triage-evidence, fora dos bundles.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git diff --stat do ciclo: somente .grill/",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Trabalho do tipo fix. Nenhum arquivo de produto ou de teste foi alterado; o resultado e plano entregue por handoff e a sessao termina em PLAN_ONLY_STOP sem specify, plan ou implementacao.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "state.json#development.workflow_version=v4"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "O bundle declara a sequencia v4 canonica completa de specify a ship, em current_step=specify com todas as etapas pending; este ciclo entrega o handoff que alimenta specify.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "verify e review estao pending e precedem ship; o handoff carrega a suite verde, git diff --check e os seis cenarios offline como criterios de aceite do ciclo executor.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md#Decisão",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "A decisao amplia a evidencia aceita sem relaxar o fail-closed: campo ausente, installed=false, diretorio inexistente ou hash divergente mantem a instalacao undetermined (cenarios 2-5). Nenhum waiver e pedido e as demais lacunas do T029 ficam explicitamente fora do escopo, nao dispensadas.",
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
      "justification": "R-0001 liga DQ-0001 ao ADR-0001; ROADMAP, PLAN-CONTEXT, DELIVERY-MAP e handoff referenciam o mesmo ADR-0001 e DU-001 sem BL; REQUEST.md aponta a triagem tri-codex-install-path e o work item de origem.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "ausencia de worker-start para este work item"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker Orca foi despachado para este work item: entrevista, triagem e leitura de codigo correram na sessao principal. Os workers da mesma sessao pertencem ao ensaio T029 do work item de origem. A clausula volta a valer no ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "git diff: nenhum caminho sob plugin/** modificado por este work item",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHY"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhum byte de plugin/** foi alterado por este work item plan-only. O plano altera plugin/**: o handoff registra a obrigacao de bump patch 6.0.1 -> 6.0.2 nos oito pontos de versao e a release correspondente como pre-requisito do ship do ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json#status=in-progress"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Trabalho plan-only nao publica versao, tag nem release. A clausula e exercida pelo pipeline no merge para main do ciclo executor, junto com o bump.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json#constitution.sha256=54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
        "CONSTITUTION-CHECK.md#constitution_sha256"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituicao foi lida somente leitura; o hash gravado coincide com o arquivo em disco. Nenhuma emenda foi proposta e nenhum ADR deste bundle pede waiver.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
