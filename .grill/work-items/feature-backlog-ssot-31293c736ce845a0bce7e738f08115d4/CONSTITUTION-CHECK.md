# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "ADR-0003 deriva o mapa de estados de experimento medido: 25 pares da FSM em banco descartavel com backlogctl 2.4.0",
        "ADR-0001 registra que backlog.db nao e repositorio git, verificado por git rev-parse",
        "ROUND-LOG.jsonl carrega evidencia nomeada por rodada"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Toda decisao do plano cita fonte verificavel: linha de codigo, saida de comando ou documento oficial do plugin backlog. ADR-0003 rejeitou a opcao de gravar in_progress ficticio justamente por esta clausula.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json immutable.work_id feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4",
        "branch dedicada feat/backlog-ssot criada antes do init",
        "artefatos gravados somente sob .grill/work-items/feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4/"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "O trabalho tem identidade imutavel propria, branch dedicada e nenhum artefato foi escrito no root legado nem no diretorio de outro work id.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md declara as cinco fases como planejamento",
        "nenhum arquivo sob plugin/ ou tests/ foi alterado nesta sessao",
        "handoffs carregam a nota plan-only"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Trabalho do tipo feature. A sessao produziu somente artefatos decisorios e termina em PLAN_ONLY_STOP; a correcao dos quatro defeitos sera executada por ciclo externo.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json development.sequence lista os onze passos na ordem",
        "state.json development.current_step permanece specify",
        "cada fase do ROADMAP aponta handoff exclusivo para o ciclo externo"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "Nenhum passo foi saltado: a sessao entrega o handoff de specify e para. Os passos seguintes pertencem ao ciclo externo.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md FASE-005 cobre verificacao antes da publicacao",
        "DU-005 exige suite verde na matriz sem backlogctl real"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "NOT-APPLICABLE nesta sessao porque nenhum ship ocorre em fluxo plan-only. A clausula fica endereçada no plano: a publicacao 3.0.0 esta condicionada a FASE-005, que depende das quatro fases anteriores.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "DQ-0004 manteve --skip-backlog como saida explicita e carimbada, nao waiver implicito",
        "DQ-0006 definiu recusa de mutacao em bundle nao migrado",
        "ADR-0002 aceita risco de projecao obsoleta de forma declarada, com mitigacao nomeada"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "As tres decisoes de degradacao sao explicitas, nomeadas e registradas. A clausula proibe waiver implicito; nenhuma saida do plano e silenciosa, e o uso da unica saida existente fica carimbado no bundle para nao se confundir com conformidade.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ADR-0001 resolve exatamente esta clausula, separando autoridade de estado de evidencia no commit",
        "DECISION-BACKLOG.md permanece versionado e passa a ser projecao gerada",
        "ADR-0002 mantem a auditoria offline para que o veredito seja reproduzivel em qualquer clone"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "A inversao de autoridade colidia com esta clausula. A colisao foi resolvida antes de qualquer outra decisao: o registro de decisao continua rastreavel ao commit por artefato versionado, e a autoridade externa cuida apenas do ciclo de vida.",
      "status": "PASS"
    },
    {
      "evidence": [
        "PLAN-CONTEXT.md FASE-005 fixa 3.0.0 e o bump nos oito lugares",
        "DU-005 aceita apenas versao identica nos oito surfaces",
        "tests/validate_distribution.py e o gate citado"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhum arquivo sob plugin/ foi alterado nesta sessao, entao nenhum bump e devido agora. A clausula fica satisfeita no plano: a mudanca e incompativel e exige bump maior, declarado como criterio de aceite da FASE-005.",
      "status": "PASS"
    },
    {
      "evidence": [
        ".specify/memory/constitution.md lido em UTF-8 e nao modificado",
        "constitution_sha256 38b899e2c10157e0eb37f6968d90af32ec735b6269771e604aa3e013b89976d6 identico ao registrado em WORK-ITEM.json",
        "init reportou constitution PRESERVED"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituicao preexistente foi preservada byte a byte e permanece autoridade. Nenhum ADR desta sessao pede excecao: ADR-0001, ADR-0002 e ADR-0003 declaram exception none.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "38b899e2c10157e0eb37f6968d90af32ec735b6269771e604aa3e013b89976d6",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
