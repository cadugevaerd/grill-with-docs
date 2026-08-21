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
      "justification": "O fechamento histórico autorizado registrou o checkpoint specify com evidências já aprovadas; state.json agora atesta todos os passos da sequência como completos, sem alegar nova invocação canônica.",
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
      "evidence": ["commit 0caed7f (2026-08-20)", "gh release list (2026-08-21): somente v2.4.1"],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "NOT-APPLICABLE nesta re-selagem: ela não publica versão. As publicações deste work item são anteriores à emenda 1.2.0; releases ausentes anteriores permanecem dívida declarada, não conformidade retroativa.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": ["DECISION-FRONTIER.md", "CONTEXT.md"],
      "heading": "Governance",
      "id": "governance",
      "justification": "Termos, decisões, gates e a autorização explícita do fechamento histórico foram registrados sem fabricar uma invocação canônica inexistente.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "d5b676ff0a56aca3153e4c8e498723cc155ac02ee1b1b7c45dcd378db8d6f736",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
