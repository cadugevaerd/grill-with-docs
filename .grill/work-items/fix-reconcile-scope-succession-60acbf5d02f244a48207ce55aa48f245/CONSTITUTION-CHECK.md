# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        ".grill/triage-evidence/SGD-24-debug.md",
        ".grill/triage-evidence/SGD-24-contract.md",
        "docs/adr/ADR-0001.md"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Sintoma, causa raiz, contrato e decisão estão registrados em fontes rastreáveis.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "O fix possui identidade imutável, branch dedicada, escopo e dependência explícitos.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "O trabalho produzido limita-se aos artefatos decisórios e termina antes de implementação.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "A sequência constitucional está registrada integralmente e o próximo passo é specify.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhum ship ocorre neste ciclo; verify e review permanecem gates anteriores ao ship.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md",
        "PLAN-CONTEXT.md"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "A autorização exige dependência direta; ausência, terceiro, transitividade e conflitos independentes continuam bloqueando.",
      "status": "PASS"
    },
    {
      "evidence": [
        ".grill/triage/tri-sgd24-scope-succession.json",
        "DECISION-FRONTIER.md",
        "ROUND-LOG.jsonl",
        "docs/adr/ADR-0001.md",
        "DELIVERY-MAP.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Triagem, decisão humana, ADR, fase e unidade de entrega mantêm referências locais estáveis.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker foi criado via Orca Orchestration neste ciclo plan-only.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "PLAN-CONTEXT.md",
        "DELIVERY-MAP.md"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "O plano exige bump patch 5.0.1 sincronizado e gate de distribuição para a futura alteração em plugin/**.",
      "status": "PASS"
    },
    {
      "evidence": [
        "PLAN-CONTEXT.md"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Nenhuma versão é publicada neste ciclo; o plano exige tag e release no mesmo commit pelo pipeline futuro.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        ".specify/memory/constitution.md",
        "WORK-ITEM.json",
        "CONSTITUTION-CHECK.md"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição 2.1.0 foi preservada read-only e seu SHA-256 está selado no work item e neste check.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
