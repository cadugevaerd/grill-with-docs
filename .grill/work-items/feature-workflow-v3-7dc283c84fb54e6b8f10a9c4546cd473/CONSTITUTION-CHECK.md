# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "docs/adr/ADR-0001.md",
        "docs/adr/ADR-0002.md",
        "docs/adr/ADR-0003.md"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada decisão usa validadores ou documentos atuais como evidência e a rodada correspondente está no log append-only.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "ROADMAP.md",
        "DELIVERY-MAP.md"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Os artefatos decisórios e o escopo pertencem somente a este work item, cuja identidade imutável está registrada em WORK-ITEM.json.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md#Delivery First",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "A sessão Grill produz roadmap, decisões e handoffs. A implementação é conduzida depois pelo ciclo externo das skills de cada etapa.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "ROADMAP.md#execution-order"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "O estado mantém a sequência imutável das onze etapas e o roadmap explicita a ordem topológica das quatro fases.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "handoffs/FASE-004-SPECIFY-HANDOFF.md"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhum ship foi iniciado; a exigência será aplicada no ciclo externo antes de qualquer avanço para ship.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md",
        "docs/adr/ADR-0002.md",
        "docs/adr/ADR-0003.md"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "As três decisões escolhem bloqueio para migração, capacidade não comprovada e concorrência divergente; nenhuma registra waiver.",
      "status": "PASS"
    },
    {
      "evidence": [
        "DECISION-FRONTIER.md",
        "ROUND-LOG.jsonl",
        "ROADMAP.md",
        "PLAN-CONTEXT.md",
        "DELIVERY-MAP.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Cada DQ termina em ADR, e roadmap, plano, delivery map e handoffs usam os mesmos IDs de fase, ADR e DU.",
      "status": "PASS"
    },
    {
      "evidence": [
        ".specify/memory/constitution.md#Bump obrigatório do plugin",
        ".github/workflows/publish.yml#Exigir bump antes de publicar",
        "tests/validate_bump_gate_contract.py"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "A regra agora exige bump SemVer para toda alteração distribuída e o publish repete esse gate no push para main antes da tag imutável.",
      "status": "PASS"
    },
    {
      "evidence": [
        "commit 0caed7f (2026-08-20) delimita a cláusula a versões novas posteriores à emenda",
        "gh release list em 2026-08-21: somente v2.4.1; tags anteriores permanecem dívida declarada"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "NOT-APPLICABLE nesta re-selagem: ela não publica versão. As publicações deste work item são anteriores à emenda 1.2.0; releases ausentes anteriores permanecem dívida declarada, não conformidade retroativa.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        ".specify/memory/constitution.md#d5b676ff0a56aca3153e4c8e498723cc155ac02ee1b1b7c45dcd378db8d6f736",
        "WORK-ITEM.json"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição 1.2.0 foi revalidada com a regra de release aplicável às versões novas; seu SHA-256 está fixado no metadata e neste check.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "d5b676ff0a56aca3153e4c8e498723cc155ac02ee1b1b7c45dcd378db8d6f736",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
