# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "docs/adr/ADR-0001.md#contexto",
        "ROUND-LOG.jsonl#R-0001",
        "CONTEXT.md#glossario"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada decisão cita fonte verificável e reexecutável: o parser em ensure_dependencies.py:160, a saída crua de specify 0.15.1 sob cat -v, o registro .specify/extensions/.registry com schema_version 1.0 e o item SGD-16. A tabela de medição em ADR-0001 registra os quatro slugs com o resultado observado, e não inferido. A própria decisão de projeto aplica a cláusula ao produto: ADR-0002 separa presença não observada de ausência observada, para que o relatório não afirme o que não mediu.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json#work_id",
        ".grill/work-items/fix-preflight-ansi-09d77024258a45ecbe612a8d22ffea95/"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "O trabalho vive em bundle próprio sob work_id fix-preflight-ansi-09d77024258a45ecbe612a8d22ffea95, criado por init com identidade imutável e hash canônico, em branch e worktree dedicadas (worktree-fix-preflight-ansi). Nenhum artefato decisório foi gravado no root legado nem no diretório de outro work_id.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md#FASE-001",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md",
        "PLAN-CONTEXT.md#FASE-001"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Trabalho de tipo fix. Nenhuma linha de ensure_dependencies.py, dependencies.json, manifest ou validador foi alterada nesta sessão; a fase termina em PLAN_ONLY_STOP com handoff ready-for-specify. O plano descreve o que deve ser construído e não autoriza construção, alteração ou publicação.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "state.json#development.current_step",
        "WORKFLOW.md"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "A sequência de onze passos está registrada em state.json na ordem exigida, com current_step em specify e todos os demais pendentes. Nenhum passo foi saltado ou marcado fora de ordem; o handoff entrega precisamente a entrada do passo specify.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "ROADMAP.md#FASE-001"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhum ship é iniciado nesta sessão e nenhum passo posterior a specify foi marcado. Os passos verify, review e ship permanecem pending em state.json, portanto a cláusula não tem ato correspondente a governar neste ciclo; ela volta a incidir quando o ciclo executável avançar.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "docs/adr/ADR-0002.md#decisao",
        "docs/adr/ADR-0003.md#decisao",
        "DECISION-FRONTIER.md"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Nenhuma DQ material ficou aberta e nenhum BL foi aberto; a fronteira está vazia e a fase só é declarada ready-for-specify por isso. No produto, a cláusula é aplicada e não contornada: registro não legível bloqueia sob --require-dependencies, extensão desabilitada bloqueia, e as três formas de ilegibilidade do registro convergem no mesmo desfecho para que nenhuma delas escape por omissão. Nenhum waiver, explícito ou implícito, foi usado.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "docs/adr/ADR-0001.md#relacoes",
        "DELIVERY-MAP.md#DU-001"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "As quatro rodadas estão em ROUND-LOG.jsonl com DQ, evidência, artefatos alterados e delta de escopo. Cada DQ aponta o ADR que a fecha, cada ADR referencia SGD-16 como origem, e ROADMAP, PLAN-CONTEXT, DELIVERY-MAP e handoff declaram o mesmo conjunto ADR-0001..ADR-0004 e a mesma DU-001. O work item roda em branch dedicada, então cada artefato é rastreável ao commit.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0004.md",
        "ROADMAP.md#FASE-001",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhum arquivo sob plugin/** foi alterado nesta sessão, então não há bump devido ainda. O bump que a fase exigirá está decidido e justificado por precedente em ADR-0004 — 3.3.0 para 3.3.1 —, está no escopo declarado do ROADMAP e é critério de aceitação explícito do handoff, incluindo a identidade da versão nos oito lugares fixados pelo validador de distribuição. Nenhuma tag publicada é reutilizada e nenhum marketplace é editado para contornar bump.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#constitution.sha256",
        "WORK-ITEM.json"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição foi lida somente para leitura e preservada byte a byte; o init reportou PRESERVED e o SHA-256 38b899e2c10157e0eb37f6968d90af32ec735b6269771e604aa3e013b89976d6 confere entre o arquivo, o state.json e este registro. Nenhuma alteração constitucional é proposta por este work item, e nenhum ADR aqui pretende dispensar ou enfraquecer cláusula.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "38b899e2c10157e0eb37f6968d90af32ec735b6269771e604aa3e013b89976d6",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
