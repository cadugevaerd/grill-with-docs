# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "plugin/skills/grill-with-docs/scripts/grill_core/step_skills.py:428-439,1011-1093",
        "plugin/skills/grill-with-docs/scripts/grill_workspace.py:3178-3223,3787",
        "docs/adr/ADR-0001.md",
        "docs/adr/ADR-0002.md",
        "ROUND-LOG.jsonl R-0001..R-0004"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "As decisões apontam para sítios verificáveis do loader, cadeia de atestação e fronteira do CLI; cada resposta está registrada com evidência no ROUND-LOG. O conflito de escopo foi confirmado contra o recibo global antes de ser registrado.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json (work_id fix-attestation-registry-anchor-bb476677b2de4f2aadd7cffa28b70d01)",
        "WORK-ITEM.json scope.paths",
        "state.json:work_id"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Todos os artefatos decisórios estão no namespace deste work_id. O escopo e a dependência sobre o work item 024 estão declarados explicitamente; nenhum diretório de outro work item foi alterado.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json immutable.type = fix",
        "ROADMAP.md FASE-001 state: blocked",
        "state.json development.current_step = specify",
        "git status: somente artefatos .grill deste work item"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "A sessão apenas cria o contrato decisório. Nenhum arquivo de produto, teste ou distribuição foi implementado; nenhum comando specify|plan, commit, merge ou ship foi executado.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json development.sequence",
        "state.json development.steps (todas pending)",
        "state.json development.current_step = specify"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "A sequência v4 completa permanece intacta e nenhuma etapa foi pulada. O ciclo está na primeira etapa e bloqueado antes de specify por dependência externa declarada.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json development.steps.verify = pending",
        "state.json development.steps.review = pending",
        "state.json development.steps.ship = pending"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhuma transição para ship ocorreu ou foi autorizada. A cláusula volta a ser exigível no ciclo externo de implementação.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md (versão obrigatória sem default)",
        "docs/adr/ADR-0002.md (código previsto preservado)",
        "DECISION-BACKLOG.md#BL-0001",
        "ROADMAP.md FASE-001 state: blocked"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "A versão não pode cair no default ativo, a exceção prevista não pode ser mascarada e o escopo não foi esvaziado para atravessar o reconciliador. O conflito histórico permanece bloqueio explícito em BL-0001/SGD-24.",
      "status": "PASS"
    },
    {
      "evidence": [
        "DECISION-FRONTIER.md DQ-0001..DQ-0004",
        "ROUND-LOG.jsonl R-0001..R-0004",
        "ROADMAP.md FASE-001",
        "DELIVERY-MAP.md MOD-001/DU-001",
        "DECISION-BACKLOG.md BL-0001 espelhado em SGD-24"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Cada DQ aponta ADR, metadata ou BL final; ROADMAP, PLAN-CONTEXT, handoff e DELIVERY-MAP usam os mesmos IDs. O bloqueio local foi sincronizado ao backlog operacional como SGD-24.",
      "status": "PASS"
    },
    {
      "evidence": [
        "Nenhuma invocação de Orca Orchestration worker-start nesta sessão",
        "ROUND-LOG.jsonl R-0001..R-0004"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker Orca foi criado; não há launch.effective a conferir. A obrigação volta a ser exigível se a implementação despachar workers.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "plugin/skills/grill-with-docs/scripts/grill_core/step_skills.py:428-439,1011-1093",
        "plugin/skills/grill-with-docs/scripts/grill_workspace.py:3178-3223",
        "docs/adr/ADR-0001.md",
        "PLAN-CONTEXT.md FASE-001"
      ],
      "heading": "Versão resolvida, nunca embutida",
      "id": "vers-o-resolvida-nunca-embutida",
      "justification": "A decisão remove o default ativo da cadeia de atestação: a autoridade é development.workflow_version do item e o parâmetro é obrigatório até load_registry(workflow_version=...). Registry injetado continua testável sem permitir que o receipt escolha o próprio juiz.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git status: nenhuma alteração implementada sob plugin/** nesta sessão",
        "WORK-ITEM.json scope.paths inclui todos os pontos de distribuição",
        "PLAN-CONTEXT.md seção Distribuição"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "O fluxo atual é plan-only e ainda não alterou plugin/**. O handoff exige bump patch 5.0.1 sincronizado nos oito pontos validados antes de merge ou push.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "Nenhuma tag ou versão publicada por este work item",
        "PLAN-CONTEXT.md seção Distribuição"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Nenhuma publicação ocorreu. O contrato exige que o futuro merge com 5.0.1 produza tag e release no mesmo commit pelo pipeline.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json constitution.sha256 = ab07e134c87b01f897135df31294269a52b4a76e145006af36ade7e2ed4623f2",
        "WORK-ITEM.json immutable.constitution.sha256",
        "CONSTITUTION-CHECK.md constitution_sha256"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição preexistente foi preservada byte a byte e seu hash coincide nos três registros. Nenhuma decisão a altera ou dispensa; BL-0001 bloqueia precisamente para evitar waiver implícito.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "ab07e134c87b01f897135df31294269a52b4a76e145006af36ade7e2ed4623f2",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
