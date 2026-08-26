# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "docs/adr/ADR-0202.md",
        "specs/010-execution-attestation/spec.md"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Esta é a cláusula que motiva o work item: o estado atual obriga a fabricar receipts para avançar. ADR-0202 ancora o receipt num artefato lido e verificado, e declara sem eufemismo o que ele NÃO prova.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "ROADMAP.md#Origem"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Identidade própria; o ROADMAP declara a origem em BL-0101 do work item feature-goal-materialization, em vez de absorver o bloqueio em silêncio.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md#FASE-001"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "A sessão termina em PLAN_ONLY_STOP; nada é implementado nem commitado por ela.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0203.md"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "A entrega restaura a possibilidade de cumprir a sequência sem saltos, que hoje está inalcançável; a tabela de classes é declarada ao lado da ordem canônica e nunca derivada dela.",
      "status": "PASS"
    },
    {
      "evidence": [
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Os critérios de aceite são executáveis e serão exercidos por verify antes de qualquer ship.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0203.md",
        "docs/adr/ADR-0202.md"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Etapa sem entrada na tabela é recusa nomeada, e artefato ausente ou ilegível é recusa, nunca emissão com digest vazio. A alternativa rejeitada — registrar e auditar depois — foi recusada exatamente por atravessar por default.",
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
      "justification": "Três DQs, três ADRs, cada DQ apontando o ADR que a encerrou; ROADMAP, mapa de entrega e handoff compartilham os identificadores.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker Orca foi despachado nesta entrevista. A cláusula volta a valer quando a entrega for executada.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "PLAN-CONTEXT.md#FASE-001"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "A entrega altera plugin/**, e o plano fixa o bump SemVer sincronizado nos oito pontos travados antes de merge ou push.",
      "status": "PASS"
    },
    {
      "evidence": [
        "PLAN-CONTEXT.md#FASE-001"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "A release é criada pelo pipeline no merge para main, ancorada no mesmo commit da tag; nenhuma release à mão.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#constitution.sha256"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "Constituição lida em UTF-8 e preservada; SHA-256 fixado no metadata. Nenhum ADR desta sessão dispensa ou reinterpreta cláusula alguma — ADR-0201 amplia quem pode ser executor, sem afrouxar o que o executor precisa provar.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
