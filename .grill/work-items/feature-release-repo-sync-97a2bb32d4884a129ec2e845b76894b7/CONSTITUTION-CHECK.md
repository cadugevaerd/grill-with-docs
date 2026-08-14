# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "docs/adr/ADR-0001.md#sources",
        "docs/adr/ADR-0002.md#sources",
        "docs/adr/ADR-0003.md#sources",
        "docs/adr/ADR-0004.md#sources",
        "ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada ADR cita a fonte inspecionada com repositorio, commit e secao; o ROUND-LOG registra a evidencia de cada rodada. Nenhuma afirmacao verificavel foi registrada sem fonte.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        ".grill/work-items/feature-release-repo-sync-97a2bb32d4884a129ec2e845b76894b7/"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Todos os artefatos decisorios estao no diretorio do work item, com identidade imutavel em WORK-ITEM.json; BL-0001 declara responsavel nominal.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md#Delivery First",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Trabalho do tipo feature. A sessao produziu apenas planejamento: nenhum workflow foi criado, nenhum arquivo fora do work item foi alterado e a sessao encerra em PLAN_ONLY_STOP.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "state.json#development.current_step"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "A matriz de 11 passos permanece intacta e current_step segue em specify; nenhum passo foi pulado ou marcado fora de ordem.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "ROADMAP.md#execution-order"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhuma fase chegou a ship nesta sessao; todos os 11 passos seguem pending. A clausula so vincula no ciclo externo de execucao, fora do escopo plan-only.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "docs/adr/ADR-0002.md#Decisao",
        "docs/adr/ADR-0004.md#Consequencias",
        "DECISION-BACKLOG.md#BL-0001"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "O gate de bump reprova em vez de publicar em duvida. O risco de credencial de ADR-0004 foi registrado como consequencia explicita e como BL com gatilho, nao como dispensa: nenhum ADR concede waiver.",
      "status": "PASS"
    },
    {
      "evidence": [
        "DECISION-FRONTIER.md",
        "ROUND-LOG.jsonl",
        "ROADMAP.md",
        "PLAN-CONTEXT.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "As seis DQ estao ligadas a ADR ou fase por final-ref; ROADMAP, PLAN-CONTEXT e handoffs referenciam os mesmos ADRs e BLs; cada rodada tem uma linha no log append-only.",
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
        ".specify/memory/constitution.md#38b899e2",
        "WORK-ITEM.json"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição 1.1.0 foi revalidada com a nova regra de publicação e seu SHA-256 está fixado no metadata e neste check.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "38b899e2c10157e0eb37f6968d90af32ec735b6269771e604aa3e013b89976d6",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
