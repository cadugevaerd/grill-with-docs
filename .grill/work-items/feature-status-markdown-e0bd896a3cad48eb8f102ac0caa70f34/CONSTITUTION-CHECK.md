# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "docs/adr/ADR-0001.md#Contexto",
        "docs/adr/ADR-0002.md#Contexto",
        "ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "O planejamento parte do comportamento observado em grill_status.py, do contrato executável validate_status_contract.py e das decisões explícitas do usuário. As ADRs distinguem o JSON já determinístico da apresentação humana variável e não afirmam implementação ainda inexistente.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json#work_id",
        ".grill/work-items/feature-status-markdown-e0bd896a3cad48eb8f102ac0caa70f34/"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "A feature possui identidade imutável própria, vive somente em seu namespace e foi iniciada na branch dedicada feat/status-markdown. Os artefatos alterados nesta sessão pertencem exclusivamente a esse work item; Constituição e WORKFLOW foram preservados.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md#FASE-001",
        "PLAN-CONTEXT.md#FASE-001",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "A sessão somente materializa decisões, decomposição e handoff. Nenhum arquivo de produto, teste executável, manifest ou versão foi alterado; a entrega termina em PLAN_ONLY_STOP antes de specify ou implementação.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "state.json#development.steps",
        "WORKFLOW.md"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "state.json conserva os onze passos na ordem constitucional, current_step em specify e todos os passos pending. O handoff prepara a entrada de specify sem marcar ou saltar etapa executável.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "ROADMAP.md#FASE-001"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhum ship ocorre no ciclo plan-only. Verify, review e ship permanecem pending e a fase somente alcançará esses passos pela sequência registrada.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "docs/adr/ADR-0002.md#Decisão",
        "docs/adr/ADR-0003.md#Decisão",
        "DECISION-FRONTIER.md"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Nenhuma DQ material ou BL permanece aberto. O produto planejado mantém inconsistências terminais e erros globais visíveis como blocked, e trata workspace nunca inicializado como pendência em vez de falso all good. Não há waiver de fechamento, finding ou etapa GWD.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "DECISION-FRONTIER.md",
        "DELIVERY-MAP.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Cada uma das quatro decisões possui DQ, rodada, ADR aceita e relação com a fase. ROADMAP, PLAN-CONTEXT, handoff e DELIVERY-MAP declaram o mesmo conjunto de ADRs e DUs, todos sob o work_id e branch dedicados.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0004.md",
        "PLAN-CONTEXT.md#FASE-001",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhum byte de plugin foi alterado na sessão plan-only. A implementação futura já tem decisão fechada para bump minor 3.3.2 para 3.4.0, sincronização das superfícies fixadas e gate de distribuição antes de merge ou push.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0004.md#Decisão",
        ".specify/memory/constitution.md#Release-obrigatória-por-versão"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "A sessão não publica versão. ADR-0004 fixa que a futura 3.4.0 só completa publicação com tag e release automáticas ancoradas no mesmo commit após merge na main.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json#constitution.sha256=d5b676ff0a56aca3153e4c8e498723cc155ac02ee1b1b7c45dcd378db8d6f736",
        "WORK-ITEM.json",
        "CONSTITUTION-CHECK.md"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição 1.2.0 foi preservada byte a byte e seu SHA-256 coincide entre metadata, state e este registro. Nenhuma ADR cria exceção, dispensa ou enfraquecimento constitucional.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "d5b676ff0a56aca3153e4c8e498723cc155ac02ee1b1b7c45dcd378db8d6f736",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
