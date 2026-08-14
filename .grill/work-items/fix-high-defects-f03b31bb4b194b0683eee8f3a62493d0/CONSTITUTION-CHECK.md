# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "SGD-2 traz o trecho de grill_status.py:87 e o experimento que refutou a hipótese do worktree dedicado",
        "SGD-6 traz reprodução com código de erro: checkpoint --step specify --state in-progress retorna INVALID-TRANSITION (grill_workspace.py:1808-1810)",
        "SGD-4 e SGD-7 nomeiam FR-007 e o filtro on.pull_request.paths do ci.yml como origem"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Os quatro itens em escopo carregam reprodução ou referência de código com linha. Nenhuma afirmação deste work item se apoia em suposição não marcada; onde faltar evidência, o registro será EVIDENCE GAP explícito.",
      "status": "PASS"
    },
    {
      "evidence": [
        "work_id fix-high-defects-f03b31bb4b194b0683eee8f3a62493d0, identidade gerada pelo core",
        "branch dedicada fix/high-defects, criada antes do init",
        "bundle próprio em .grill/work-items/fix-high-defects-f03b31bb4b194b0683eee8f3a62493d0/"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Bundle isolado, identidade imutável registrada em WORK-ITEM.json e ownership único (Carlos Araujo). O work item anterior, feature-release-repo-sync, está complete e reconciliado; nenhum artefato dele é reaproveitado ou reescrito aqui.",
      "status": "PASS"
    },
    {
      "evidence": [
        "type=fix registrado em WORK-ITEM.json",
        "esta sessão não executa specify/plan, não edita código de produção e não faz commit ou merge"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Trilha fix, portanto plan-only. A sessão termina em PLAN_ONLY_STOP entregando o handoff da primeira fase; a correção dos defeitos é executada por ciclo externo.",
      "status": "PASS"
    },
    {
      "evidence": [
        "SGD-6 documenta que a matriz de 11 passos não reseta entre fases, o que impede a segunda fase deste próprio work item de iniciar",
        "a ordem das fases será declarada em execution-order no ROADMAP"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "A sequência das 11 etapas é obrigatória e será seguida sem saltos em cada fase. Registro de risco material: SGD-6 é exatamente o defeito que impede a transição entre fases neste protocolo, então a estrutura de fases deste work item precisa ser decidida com essa restrição à vista, e não assumida.",
      "status": "PASS"
    },
    {
      "evidence": [
        "nenhuma fase deste work item declara ship antes de verify e review",
        "o ciclo externo aplica os mesmos gates que a milestone anterior aplicou, com evidência registrada em specs/"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Ship só inicia após verify e review completos com evidência. Aplicável e planejado; a milestone anterior demonstrou o padrão, incluindo review adversarial independente.",
      "status": "PASS"
    },
    {
      "evidence": [
        "SGD-2 propõe alterar um finding que dispara sempre, por construção, e portanto não carrega informação"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Nenhuma correção em escopo concede waiver. Ponto que exige cuidado e ficará registrado como decisão: alterar o finding LIVE-VS-RECORDED pode parecer enfraquecer o fail-closed, mas o pino comparado é insatisfazível por construção — o finding é ruído que mascara bloqueio real, não sinal. Se a decisão escolhida remover o finding sem substituto, isso precisa ser justificado como remoção de falso positivo, com evidência, e não como waiver.",
      "status": "PASS"
    },
    {
      "evidence": [
        "cada fase referenciará o item SGD correspondente e o commit que a entrega",
        "o backlog SGD está vinculado a este repositório por bound_path"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Cada fase liga-se a um ou mais itens SGD, ao ADR que registra a decisão e ao commit de entrega. O vínculo entre work item e backlog externo já existe e é bidirecional.",
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
