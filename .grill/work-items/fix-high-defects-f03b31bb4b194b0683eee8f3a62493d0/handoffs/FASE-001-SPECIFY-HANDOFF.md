# FASE-001 — Virada de fase auditada

- phase: FASE-001
- state: complete
- roadmap: ROADMAP.md#FASE-001
- context-refs: Matriz de etapas, Trilha de checkpoint, Virada de fase
- ADRs: ADR-0001
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

Resultado observável: um work item cujo roteiro tem mais de uma fase consegue começar a segunda, e cada fase deixa registro de por quais passos passou.

Atores: quem conduz o ciclo de desenvolvimento de um work item multi-fase; quem audita depois o que foi feito em cada fase.

Cenários:
- fase concluída e próxima iniciada — o ciclo recomeça do primeiro passo, sem edição manual de arquivo de estado;
- virada pedida com a fase ainda em andamento — recusada, porque encerrar uma fase incompleta apagaria o progresso que ainda vale;
- virada pedida sem razão declarada — recusada, porque a razão é o que torna a transição auditável;
- segunda fase iniciada sem a virada — continua recusada, mas a recusa passa a dizer o que fazer;
- fase virada duas vezes seguidas sem trabalho no meio — a segunda não produz mudança.

Escopo: o comando de virada, sua exigência de razão, seu registro na trilha, e a mensagem da recusa que hoje não indica saída.

Fora de escopo: mudar a forma do arquivo de estado; migrar work items existentes; alterar o pino de identidade.

Critérios de aceite: a segunda fase inicia sem que ninguém edite estado à mão; a trilha permite reconstruir por quais passos cada fase passou; o work item já concluído e projetado no global continua válido, sem migração; e quem esbarrar na recusa descobre pela própria mensagem como prosseguir.

## WHY
O roteiro admite várias fases, mas o registro de progresso é um só por work item. Concluída a primeira fase, ele fica cheio, e a segunda não tem por onde começar — não por decisão, mas porque não existe caminho de volta.

O custo já foi pago e é medível: no work item anterior, das três fases entregues apenas a primeira tem registro por passo. As outras duas foram executadas inteiras sem deixar trilha, porque não havia como registrá-las. O que se perdeu não foi conveniência, foi a evidência de que a sequência obrigatória foi seguida — exatamente o que o registro existe para provar.

Esta fase vem primeiro porque o próprio trabalho depende dela: as fases seguintes deste work item só existem se ela funcionar.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
