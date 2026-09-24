# FASE-002 — Encerramento do work item de origem por fence autorizado

- phase: FASE-002
- state: planned
- roadmap: ROADMAP.md#FASE-002
- context-refs: sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, resultado não aceito
- ADRs: ADR-0001
- BLs: BL-0001

## WHAT
- delivery-units: DU-002
- development-type: platform-devops

### Resultado
O work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d deixa de ser um bundle auto-bloqueado e passa a `superseded`, apontando para este work item como sucessor das suas decisões. Sua atividade `interview-author-001` (sessão retida) é encerrada pelo fence autorizado publicado na 6.0.31, sem aceite do resultado retido; o milestone de origem fecha.

### Atores
- **Líder GWD deste work item**: pede a prévia e a aplicação do fence sobre o work item de origem, depois registra o encerramento no bundle de origem.
- **Humano autorizador**: assina a autorização exata para o work item de origem, seu contexto `ctx-0c0155ef5a94` e a atividade `interview-author-001`.

### Cenários
1. **Fence do work item de origem**: prévia mostra `interview-author-001` (`RESULT_RECORDED`, recurso `CLOSE_PENDING`), o veredicto terminal do especialista `ctx_2923e0218c89`, o veredicto do líder `orca:ctx_ad48e72ddf4c` e o hash; aplicação com o hash e a autorização exata leva a atividade a estado terminal não aceito e fecha o recurso com recibo.
2. **Encerramento do bundle de origem**: a fase de origem passa a `superseded`, o milestone de origem fecha como completo e o ADR de origem aponta `superseded-by` para o ADR-0001 deste work item; a auditoria do bundle de origem devolve `MILESTONE-COMPLETE`.
3. **Negativo — aceite tardio**: qualquer tentativa de aceitar `interview-author-001` de origem depois do fence é recusada.
4. **Negativo — fence antes da 6.0.31**: sem o verbo instalado, nada é executado e o BL permanece aberto.

### Critérios de aceite
- A aplicação do fence devolve o veredicto de aplicado (ou de reuso no replay) com recibo e autorização verbatim rastreáveis ao work item de origem.
- A quiescência do work item de origem fica vazia; nenhuma atividade ativa resta.
- A auditoria do bundle de origem devolve `MILESTONE-COMPLETE` sem BL nem DQ material aberto.
- Nenhum byte fora dos bundles `.grill/` e do Store deste repositório muda.

## WHY
- **Valor**: o bundle de origem ficou preso pelo defeito que ele mesmo diagnosticou; deixá-lo `in-progress` para sempre é ruído em toda auditoria e status, e cercá-lo é o primeiro uso real do verbo, no próprio repositório.
- **Evidência**: recusa `TAKEOVER-WORK-ACTIVE` com `activity:interview-author-001` observada pelo coordenador; `interview-author-001` `RESULT_RECORDED` com recurso `CLOSE_PENDING`, dispatch `completed` e capability revogada; decisão humana do coordenador (plano E) de migrar e marcar `superseded` depois do ship.
- **Restrições**: depende da FASE-001 shipada e publicada como 6.0.31 (BL-0001); autorização humana exata e prova terminal Orca continuam obrigatórias; o resultado retido nunca é aceito nem reexecutado; sem edição manual do Store.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
