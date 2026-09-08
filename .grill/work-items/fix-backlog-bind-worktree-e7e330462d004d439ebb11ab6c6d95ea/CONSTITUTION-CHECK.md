# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "docs/adr/ADR-0001.md#Contexto",
        "docs/adr/ADR-0002.md#Contexto",
        "ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada ADR cita arquivo e linha lidos nesta sessao (backlog_bridge.py:114-142, grill_workspace.py:257-264, store.py:497-521, validate_backlog_contract.py:40-61,95-145) e a reproducao foi executada de fato: preflight nesta worktree devolveu NEEDS-CREATE CFB e backlogctl backlog list mostrou SGD vinculado a outro caminho. Cada round do ROUND-LOG carrega a evidencia que sustentou a decisao.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json#work_id",
        "git status: unico caminho nao rastreado e .grill/work-items/fix-backlog-bind-worktree-e7e330462d004d439ebb11ab6c6d95ea/"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "O trabalho vive em bundle proprio com identidade imutavel fix-backlog-bind-worktree-e7e330462d004d439ebb11ab6c6d95ea, em worktree e branch dedicadas (cadugevaerd/chore-fix-backlog). Nenhum byte foi escrito fora do bundle nem no diretorio de outro work item.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git status --porcelain",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Trabalho do tipo fix. Nenhum arquivo de produto ou de teste foi alterado: o unico caminho tocado e o proprio bundle. O conteudo decidido e plano, entregue por handoff, e a sessao encerra em PLAN_ONLY_STOP sem specify, plan, commit ou merge.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "state.json#development.workflow_version=v4"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "O bundle declara a sequencia v4 canonica completa, de specify a ship, sem salto, e esta em current_step=specify com todas as demais etapas pending. A entrega deste ciclo e o handoff que alimenta specify.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "verify e review estao pending e precedem ship na sequencia declarada. O handoff carrega ao ciclo executor a suite verde (python3 tests/run_validators.py) e a prova manual de preflight BOUND como criterios de aceite.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md#Decisão",
        "DECISION-FRONTIER.md#DQ-0005"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "A ambiguidade entre dois backlogs do mesmo repositorio e recusa nomeada, nao escolha; binds existentes nunca sao re-apontados em silencio; o caso de vinculo obsoleto foi declarado out-of-scope em DQ-0005 com evidencia de que o comportamento atual nao muda, nao dispensado em silencio. O proprio bundle nasceu com backlog_skipped e o carimbo fica visivel ate o backlog-adopt pos-ship registrado em PLAN-CONTEXT.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "DECISION-FRONTIER.md",
        "ROADMAP.md",
        "PLAN-CONTEXT.md",
        "DELIVERY-MAP.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Seis rounds ligam cada DQ ao seu ADR ou round final; a fronteira registra final-ref por decisao; ROADMAP, DELIVERY-MAP, PLAN-CONTEXT e o handoff referenciam o mesmo conjunto ADR-0001 e ADR-0002, sem BL, ancorados neste work_id.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "ausencia de qualquer chamada a orca orchestration worker-start nesta sessao"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker foi criado via Orca Orchestration: a entrevista e a leitura de codigo correram na sessao principal. A clausula governa o despacho de worker e volta a valer se o ciclo executor despachar worker para implementar o plano.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "git status --porcelain: nenhum caminho sob plugin/** modificado",
        "PLAN-CONTEXT.md#Obrigações carregadas ao ciclo executor"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "A clausula condiciona-se a alteracao em plugin/**, e este work item nao alterou byte algum ali. O plano prescreve mudanca em plugin/**, entao a obrigacao de bump (leitura patch, 5.4.0 -> 5.4.1) foi registrada em PLAN-CONTEXT e no handoff como pre-requisito de merge do ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "git status --porcelain",
        "state.json#status=in-progress"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Nenhuma versao e publicada por um trabalho plan-only: nao ha tag, release nem push neste work item. A clausula sera exercida pelo pipeline no merge para main do ciclo executor, junto com o bump.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json#constitution.sha256=54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
        "CONSTITUTION-CHECK.md#constitution_sha256"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituicao foi lida somente leitura e preservada byte a byte: o hash gravado no work item coincide com o do arquivo em disco. Nenhuma alteracao constitucional foi proposta e nenhum ADR deste bundle pede waiver.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
