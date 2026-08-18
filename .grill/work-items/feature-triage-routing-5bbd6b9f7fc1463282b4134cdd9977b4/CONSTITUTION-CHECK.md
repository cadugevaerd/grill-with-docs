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
        "docs/adr/ADR-0003.md",
        "docs/adr/ADR-0004.md",
        "tests/validate_triage_contract.py"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada decisão cita contrato executável ou documento atual, e o gate central do produto é literalmente esse princípio: nenhuma rota abre enquanto o laudo não comprovar a causa raiz.",
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
        "handoffs/FASE-001-SPECIFY-HANDOFF.md",
        "ROUND-LOG.jsonl#R-0004"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "A sessão Grill produziu roadmap, decisões e handoff sem autorizar nada por si. A implementação foi conduzida depois, pelo ciclo externo das etapas, sob autorização explícita do operador ao plano apresentado; nenhum plano deste bundle autoriza publicação.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "ROADMAP.md#execution-order"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "O estado mantém a sequência imutável das onze etapas e a trilha de checkpoints percorre todas elas sem salto, a partir de specify.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "AUDIT.md"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Verify e review foram concluídos com evidência antes de ship, e o próprio core recusa a transição de ship enquanto ambos não estiverem complete.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0003.md",
        "docs/adr/ADR-0004.md",
        "tests/validate_triage_contract.py"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Laudo inconclusivo, evidência faltante e evidência contraditória recusam em vez de avisar; ADR-0003 registra explicitamente a rejeição de aceitar laudo inconclusivo com ressalva por ser waiver implícito.",
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
      "justification": "Cada DQ termina em ADR, e roadmap, plano, delivery map e handoff usam os mesmos IDs de fase, ADR e DU; o registro de triagem acrescenta um id que atravessa laudo e trabalho.",
      "status": "PASS"
    },
    {
      "evidence": [
        "CHANGELOG.md#3.3.0",
        "tests/validate_distribution.py",
        "plugin/.claude-plugin/plugin.json"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "A alteração em plugin/** foi acompanhada do bump SemVer 3.2.2 para 3.3.0 nos oito lugares que o validador de distribuição fixa, e o validador aprova.",
      "status": "PASS"
    },
    {
      "evidence": [
        ".specify/memory/constitution.md#38b899e2",
        "WORK-ITEM.json"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição 1.1.0 foi preservada byte a byte pelo init e seu SHA-256 está fixado no metadata imutável e neste check.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "38b899e2c10157e0eb37f6968d90af32ec735b6269771e604aa3e013b89976d6",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
