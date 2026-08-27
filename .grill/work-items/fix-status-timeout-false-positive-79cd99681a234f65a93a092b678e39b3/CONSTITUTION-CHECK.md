# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [".grill/evidence/grill-status-timeout-debug-report.md", ".grill/triage/tri-status-timeout-false-positive.json"],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "A causa raiz foi provada por um relatório code-debug com todas as seções exigidas preenchidas e não vazias antes de a triagem selar a rota bugfix; esta entrevista referencia essa mesma evidência em ADR-0001 e no handoff, sem afirmação nova sem lastro.",
      "status": "PASS"
    },
    {
      "evidence": ["WORK-ITEM.json"],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "O work item fix-status-timeout-false-positive-79cd99681a234f65a93a092b678e39b3 tem identidade imutável própria (WORK-ITEM.json) e todos os artefatos decisórios desta sessão vivem exclusivamente sob .grill/work-items/<este-id>/.",
      "status": "PASS"
    },
    {
      "evidence": ["WORKFLOW.md", "state.json"],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "O work item é do tipo fix; esta sessão apenas completa entrevista e documentação decisória, sem executar specify/plan nem alterar código do fix, e encerra em PLAN_ONLY_STOP.",
      "status": "PASS"
    },
    {
      "evidence": ["state.json"],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "development.sequence em state.json reproduz exatamente a ordem canônica v4 (specify..ship) e nenhuma etapa foi avançada fora de ordem por esta sessão; todas seguem pending.",
      "status": "PASS"
    },
    {
      "evidence": ["state.json"],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhuma etapa de desenvolvimento foi avançada nesta sessão plan-only; ship não foi solicitado nem alcançado, logo a cláusula não tem violação para julgar ainda.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": ["DECISION-FRONTIER.md"],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "DQ-0001 foi resolvida com evidência e ADR, não adiada nem contornada; o gate constitucional é aplicado por completo nesta sessão, sem exceção nem waiver implícito.",
      "status": "PASS"
    },
    {
      "evidence": ["docs/adr/ADR-0001.md", "DECISION-FRONTIER.md", "ROADMAP.md"],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "ADR-0001, DQ-0001 e a fase FASE-001 referenciam o mesmo work item e o mesmo laudo/triagem, selados no commit 070bb29d15ea25207d46266405aaa40534a45d91, formando uma cadeia rastreável ponta a ponta.",
      "status": "PASS"
    },
    {
      "evidence": ["sessão condutora sem despacho de worker Orca"],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Esta entrevista foi conduzida diretamente pela sessão, sem despachar nenhum worker via Orca Orchestration; não há worker-start a conferir.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": ["ROADMAP.md#FASE-001", "PLAN-CONTEXT.md#FASE-001"],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhuma alteração em plugin/** foi mesclada ou publicada por esta sessão plan-only; o bump SemVer obrigatório está declarado como escopo obrigatório em ROADMAP.md#FASE-001 e PLAN-CONTEXT.md#FASE-001 para a fase de implementação subsequente.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": ["ROADMAP.md#FASE-001", "PLAN-CONTEXT.md#FASE-001"],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Nenhuma versão foi publicada por esta sessão plan-only; a atualização dos oito locais de distribuição e a revalidação dos gates estão declaradas como escopo obrigatório para a implementação subsequente.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [".specify/memory/constitution.md"],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição foi lida somente-leitura em UTF-8, seu hash foi registrado neste CONSTITUTION-CHECK.md e em state.json, e nenhuma cláusula foi dispensada, enfraquecida ou violada por esta sessão.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
