# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": ["DECISION-FRONTIER.md", "PLAN-CONTEXT.md"],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "O plano separa evidência local, decisões resolvidas e validações futuras por fase.",
      "status": "PASS"
    },
    {
      "evidence": ["WORK-ITEM.json", "ROADMAP.md"],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "A feature possui work item próprio e o ROADMAP delimita os módulos e dependências.",
      "status": "PASS"
    },
    {
      "evidence": ["ROADMAP.md#Delivery First", "handoffs/FASE-001-SPECIFY-HANDOFF.md"],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Os handoffs e o ROADMAP mantêm a feature em planejamento; nenhuma implementação é afirmada.",
      "status": "PASS"
    },
    {
      "evidence": ["ROADMAP.md", "state.json"],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "A primeira fase está pronta para specify e o desenvolvimento preserva a sequência canônica.",
      "status": "PASS"
    },
    {
      "evidence": ["ROADMAP.md#FASE-004", "docs/adr/0002-autonomous-run-and-human-ship-gate.md"],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "A fase de fechamento exige verify, Independent Review e autorização humana antes de ship.",
      "status": "PASS"
    },
    {
      "evidence": ["docs/adr/0009-fail-closed-convergence.md", "docs/adr/0011-review-block-without-macro-loop.md"],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Conflitos e review reprovado bloqueiam sem auto-merge, bypass ou exceção implícita.",
      "status": "PASS"
    },
    {
      "evidence": ["DELIVERY-MAP.md", "PLAN-CONTEXT.md", "DECISION-FRONTIER.md"],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Fases, DUs, ADRs e decisões têm referências cruzadas determinísticas.",
      "status": "PASS"
    },
    {
      "evidence": ["ROADMAP.md#FASE-004", "docs/adr/0007-project-gauntlet-configuration.md"],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "A entrega prevê a versão 2.6.0 para a mudança publicada no bundle do plugin.",
      "status": "PASS"
    },
    {
      "evidence": ["DECISION-FRONTIER.md", "CONTEXT.md"],
      "heading": "Governance",
      "id": "governance",
      "justification": "Termos, decisões e gates foram registrados antes da execução da feature.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "38b899e2c10157e0eb37f6968d90af32ec735b6269771e604aa3e013b89976d6",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
