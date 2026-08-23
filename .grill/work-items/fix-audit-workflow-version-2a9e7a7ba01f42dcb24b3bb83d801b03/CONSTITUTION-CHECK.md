# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "grill_workspace.py:691 (literal \"v2\" carimbado)",
        "audit_decisions.py:801 (literal \"v2\" exigido)",
        "assets/state.template.json:5 (literal \"v4\" congelado)",
        "audit_decisions.py:70 e :366 (marcador real já aceito)",
        "ROUND-LOG.jsonl R-0001..R-0004"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada afirmação deste work item aponta arquivo e linha verificáveis; as quatro decisões registram no ROUND-LOG a evidência que as sustenta. Nenhuma afirmação sobre o comportamento do plugin foi feita sem leitura do sítio correspondente.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json (work_id fix-audit-workflow-version-5ff06e6e523c485dbfdcd28d0f5b0538)",
        "state.json:work_id",
        "DECISION-FRONTIER.md (quatro DQ locais a este work item)"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Todos os artefatos decisórios vivem sob o diretório deste work_id; nenhum outro bundle, nem o root legado, foi escrito. A identidade imutável foi gerada pelo init e as decisões registradas pertencem exclusivamente a ele.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md FASE-001 state: ready-for-specify",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md (WHAT/WHY, sem HOW)",
        "state.json:development.current_step = specify"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Work item do tipo fix: a sessão termina em PLAN_ONLY_STOP. Nenhum arquivo sob plugin/ foi alterado, nenhum comando specify|plan foi executado, nenhum commit ou merge feito. O HOW técnico está confinado ao PLAN-CONTEXT, que é insumo de planejamento e não autorização.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json:development.sequence (11 etapas v4, intacta)",
        "state.json:development.steps (todas pending)",
        "state.json:development.current_step = specify"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "A sequência gravada pelo init é a ordem canônica v4 completa, sem salto e sem edição. O work item está na primeira etapa, specify, e nenhuma etapa posterior foi marcada como cumprida.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json:development.steps.verify = pending",
        "state.json:development.steps.review = pending",
        "state.json:development.steps.ship = pending"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Ship não foi iniciado nem autorizado por este work item, que é plan-only e para em specify. A cláusula governa a transição para ship; não há transição a avaliar nesta sessão. Ela volta a ser exigível no ciclo de implementação, que é externo a este bundle.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "docs/adr/ADR-0002.md (init recusa quando o marcador não resolve)",
        "docs/adr/ADR-0001.md (fallback ACTIVE_VERSION e cross-check ambos avaliados e rejeitados, com razão)",
        "DECISION-BACKLOG.md (vazio: nenhuma decisão foi adiada para escapar de um gate)"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "A decisão de DQ-0003 é explicitamente fail-closed: marcador ausente ou duplicado recusa a criação antes de qualquer escrita, sem bundle parcial. O fallback silencioso para ACTIVE_VERSION foi considerado e rejeitado por reintroduzir a constante disfarçada de detecção. O custo aceito em ADR-0001 está declarado na seção Consequências do próprio ADR, junto da alternativa rejeitada e da razão — não foi convertido em dívida pendurada para contornar o gate que reprova fase ready com BL open.",
      "status": "PASS"
    },
    {
      "evidence": [
        "DECISION-FRONTIER.md DQ-0001..DQ-0005 com final-ref",
        "ROUND-LOG.jsonl R-0001..R-0005",
        "ROADMAP.md FASE-001 (ADRs, delivery-units)",
        "DELIVERY-MAP.md MOD-001/DU-001",
        "WORK-ITEM.json (head commit e base ref)"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Cada DQ aponta o ADR que a fecha; cada ADR é referenciado pelo ROADMAP, pelo handoff e pelo PLAN-CONTEXT com os mesmos identificadores. O ROUND-LOG registra as cinco rodadas em ordem monotônica, com a evidência de cada uma. O bundle registra HEAD e base ref, ligando as decisões ao commit.",
      "status": "PASS"
    },
    {
      "evidence": [
        "Nenhuma invocação de orca orchestration worker-start nesta sessão",
        "ROUND-LOG.jsonl (quatro rodadas conduzidas em sessão única, sem despacho a worker)"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Nenhum worker foi criado via Orca Orchestration neste work item: a entrevista e a redação dos artefatos correram na própria sessão. A cláusula governa o despacho de workers e não há despacho a conferir. Ela volta a ser exigível se o ciclo de implementação for paralelizado por workers.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "grill_workspace.py:691 e audit_decisions.py:801 (par writer/reader sobre o mesmo literal \"v2\")",
        "assets/state.template.json:5 (versão ativa congelada no asset)",
        "grill_workspace.py:2269/2346/2431/2514/3016 (gate v3 chamado sobre documento v4)",
        "grill_core/workflow_v4.py:247 (gate v4 correto, existente e nunca chamado)",
        "docs/adr/ADR-0001.md, docs/adr/ADR-0002.md",
        "specs/024-workflow-version-derivada/spec.md FR-001, FR-002, FR-003"
      ],
      "heading": "Versão resolvida, nunca embutida",
      "id": "vers-o-resolvida-nunca-embutida",
      "justification": "Este work item existe para eliminar exatamente a falha que a cláusula proíbe, e a cumpre em cada decisão que tomou. ADR-0001 troca o literal por resolução a partir da declaração do documento nos dois campos do registro de estado, e troca a asserção da auditoria de igualdade a um literal por pertencimento a tabela. ADR-0002 recusa explicitamente o fallback silencioso para a versão ativa, que seria o default proibido pelo terceiro parágrafo. A equivalência declarada de FR-002 é entrada própria justificada por identidade de sequências, não fallback. A enumeração exigida na introdução de versão nova está feita: os três pontos de despacho por versão encontrados hoje estão nomeados na evidência acima, e o terceiro — o gate de elegibilidade — está declarado fora do escopo deste work item e sem correção aqui, portanto registrado como ponto conhecido e não como ponto omitido.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git status: nenhuma alteração sob plugin/**",
        "PLAN-CONTEXT.md, seção Governança de distribuição",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md, WHY (restrições)"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Este work item é plan-only e não alterou byte algum sob plugin/**, então a cláusula não é acionada agora. A obrigação foi registrada como restrição explícita do handoff e do PLAN-CONTEXT, nomeando os oito sítios travados por tests/validate_distribution.py, para que o ciclo de implementação não possa tratá-la como opcional.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "Nenhuma versão publicada por este work item",
        "Nenhuma tag criada nesta sessão"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Nenhuma versão foi publicada e nenhuma tag foi criada por este work item, que termina em PLAN_ONLY_STOP. A cláusula governa publicação; não há publicação a avaliar. Ela é exigível no merge para main que carregar o bump planejado.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json:constitution.sha256 = 54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
        "init: constitution PRESERVED",
        "CONSTITUTION-CHECK.md constitution_sha256 (idêntico)"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição preexistente foi preservada byte a byte pelo init, que reportou PRESERVED, e seu SHA-256 está registrado no metadata e neste check com o mesmo valor. Nenhum ADR ou decisão deste work item pretende alterar, enfraquecer ou dispensar qualquer cláusula.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "ab07e134c87b01f897135df31294269a52b4a76e145006af36ade7e2ed4623f2",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
