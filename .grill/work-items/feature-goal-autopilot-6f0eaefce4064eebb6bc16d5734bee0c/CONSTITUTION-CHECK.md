# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "ROUND-LOG.jsonl (campo evidence de cada rodada)",
        "docs/adr/ADR-0001-runtime-neutro.md",
        "docs/adr/ADR-0004-contrato-de-parada-goal-hold.md",
        "DECISION-BACKLOG.md#BL-0001"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada decisão registra a fonte que a sustenta: os dois runtimes de goal loop foram inspecionados diretamente (tabela thread_goals e hermes_cli/goals.py), o contrato de parada cita o fail-OPEN do juiz e o limite de turnos, e o risco residual entrou como BL com evidência em vez de virar afirmação.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        ".grill/work-items/feature-goal-autopilot-6f0eaefce4064eebb6bc16d5734bee0c/",
        "DECISION-BACKLOG.md#BL-0001 (owner)"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Todo artefato decisório foi gravado somente sob o work item próprio, criado por init com identidade collision-resistant; nenhum diretório de outro work id e nenhum root legado foi tocado, e o BL aberto declara owner.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0002-duas-trilhas.md",
        "docs/adr/ADR-0005-pontos-de-interacao.md",
        "ROADMAP.md#FASE-001 (scope-out)"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "A sessão termina em PLAN_ONLY_STOP sem executar specify/plan, sem editar código e sem commit ou merge. A travessia da fronteira entre as trilhas foi decidida como parada obrigatória e não configurável, exatamente para que o documento planejado não possa autorizar o que a cláusula proíbe.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "docs/adr/ADR-0006-orca-paralelizacao-por-subdominio.md",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "O plano preserva a sequência de onze etapas sem saltos e o documento planejado a reproduz integralmente. A delegação a workers é interna à etapa: nenhum worker produz step-output, o que impediria a etapa de avançar sem a cadeia de atestação.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0005-pontos-de-interacao.md",
        "WORKFLOW.md#ciclo-externo-de-execucao-11-etapas"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "A lista fechada de pontos de interação preserva ship como parada obrigatória com autorização humana explícita, e mantém os retornos when-blocked de verify e review como paradas. Nada no plano permite alcançar ship sem verify e review completos.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0005-pontos-de-interacao.md (cláusula residual)",
        "docs/adr/ADR-0004-contrato-de-parada-goal-hold.md",
        "DECISION-BACKLOG.md#BL-0001"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "A lista de pontos de interação fecha com cláusula residual: situação não prevista para o loop em vez de autorizá-lo, o que era justamente o waiver implícito da alternativa rejeitada. O risco de o juiz ignorar a parada foi declarado como BL aberto, não absorvido em silêncio.",
      "status": "PASS"
    },
    {
      "evidence": [
        "DECISION-FRONTIER.md",
        "ROUND-LOG.jsonl",
        "ROADMAP.md",
        "DELIVERY-MAP.md",
        "PLAN-CONTEXT.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Cada DQ aponta para o ADR que a encerrou, cada rodada tem linha própria no log, e fases, módulos e delivery units estão amarrados aos mesmos identificadores no roadmap, no mapa de entrega e nos handoffs.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0006-orca-paralelizacao-por-subdominio.md",
        "PLAN-CONTEXT.md#FASE-001",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "O plano exige que todo worker-start declare --model, e --effort quando suportado, com tier correspondente à natureza do trabalho, confira launch.effective contra launch.requested e bloqueie o despacho na divergência, sem reuso de terminal. A exceção de implement-parallel, onde o modelo é derivado do binding versionado e não escolhido, está declarada. Nenhum worker foi despachado nesta sessão.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0003-goal-md-asset-gerenciado.md",
        "ROADMAP.md#FASE-003",
        "PLAN-CONTEXT.md#FASE-003"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "A decisão de o documento ser asset gerenciado altera plugin/**, e o plano trata o bump SemVer sincronizado nos oito lugares travados como entrega obrigatória da FASE-003, não como consequência opcional. Esta sessão é plan-only e não alterou plugin/**.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md#FASE-003",
        "PLAN-CONTEXT.md#FASE-003"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "O plano exige tag anotada imutável e release ancorada no mesmo commit, criadas pelo pipeline no merge para main; release criada à mão está explicitamente registrada como contorno, não como conformidade.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#constitution.sha256",
        "CONSTITUTION-CHECK.md#constitution_sha256"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição foi lida em UTF-8, preservada byte a byte, e seu SHA-256 está fixado no metadata do work item e neste registro. Nenhum ADR desta sessão dispensa, enfraquece ou reinterpreta cláusula alguma.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
