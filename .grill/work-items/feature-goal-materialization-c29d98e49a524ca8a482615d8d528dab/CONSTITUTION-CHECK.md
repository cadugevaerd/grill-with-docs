# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "docs/adr/ADR-0101.md",
        "ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada decisão cita a fonte: ADR-0101 aponta o commit 055a886, que corrigiu em campo o defeito causado por duplicar tabelas de versão, e ADR-0102 aponta a seção do WORKFLOW.md que já resolve o caso equivalente para documento humano.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "ROADMAP.md#Origem"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Identidade própria e imutável; o ROADMAP declara a origem — as fases superseded do work item feature-goal-autopilot — em vez de absorvê-las em silêncio.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md#FASE-001"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "A sessão termina em PLAN_ONLY_STOP; nada é implementado, nenhum commit ou merge é feito por ela.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "A sequência de onze etapas é preservada sem saltos para este work item.",
      "status": "PASS"
    },
    {
      "evidence": [
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "O handoff declara os critérios executáveis que verify precisa exercer antes de qualquer ship.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0102.md"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Documento divergente é preservado e sinalizado, nunca sobrescrito em silêncio: a ambiguidade bloqueia a substituição em vez de autorizá-la.",
      "status": "PASS"
    },
    {
      "evidence": [
        "DECISION-FRONTIER.md",
        "ROUND-LOG.jsonl",
        "ROADMAP.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Cada DQ aponta o ADR que a encerrou; ROADMAP, mapa de entrega e handoff compartilham os mesmos identificadores.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker Orca foi despachado nesta sessão de entrevista. A cláusula volta a valer em implement-parallel.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "PLAN-CONTEXT.md#FASE-001"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "A entrega altera plugin/**, e o plano fixa o bump MINOR sobre a 5.0.0 publicada, sincronizado nos oito pontos travados, antes de merge ou push.",
      "status": "PASS"
    },
    {
      "evidence": [
        "PLAN-CONTEXT.md#FASE-001"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "A release da versão nova é criada pelo pipeline no merge para main, ancorada no mesmo commit da tag; nenhuma release é criada à mão.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#constitution.sha256"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição foi lida em UTF-8 e preservada; seu SHA-256 está fixado no metadata. Nenhum ADR desta sessão dispensa ou reinterpreta cláusula alguma.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
