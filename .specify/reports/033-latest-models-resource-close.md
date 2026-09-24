# Achado operacional da etapa specify: sessão especialista legada

- Work item: `feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec`.
- Recurso: `session-3f7c7f9cdc0acbb500d2b820`, atividade `specify-reviewer-r2-latest-models`, estado `REGISTERED` no takeover para `ctx-abe82e929ba403bc2dc10449` (época 3).
- Evidência: checkpoint `cp-f78b6444beed6f53c3554435171f070e55c431ec6140939e924875088baed065` e receipt `TAKEOVER-APPLIED` na revisão 3248 do Store. O dispatch de origem `ctx_c37c6c5fe82c` terminou; sua revisão documental foi aprovada, mas o bootstrap de apresentação falhou.
- Causa no core selecionado: `grill_workspace.py` preserva sessões registradas sem transporte de fechamento em `gauntlet-cleanup` (comentário junto à linha 4448). Não há operação pública de close para esse recurso. Os gates `gauntlet-step-enter`, `checkpoint` e `gauntlet-attest` não consomem recursos apenas `REGISTERED`; `gauntlet-prepare-switch` os considera.
- Tratamento neste ciclo: preservar o recurso e não fabricar fechamento. Prosseguir com a revisão R3 e registrar um defeito de core separado antes de uma futura troca de runtime. A decisão do coordenador é que este achado não é HOLD desta etapa.

## HOLD-V4-02 após a revisão R3

A revisão `specify-reviewer-r3-latest-models` foi aceita como `APPROVED` na revisão 3254 do Store. `attest` gerou `agent-orchestration/attestations/specify.json` para `specs/033-latest-models/spec.md`, mas `checkpoint --state complete` recusou `ORCHESTRATOR_INVALID: successor context has no campaign bridge`; nenhuma conclusão de etapa foi persistida.

O takeover ocorreu antes da primeira campanha e gravou `campaign_bridge=null`. Ao tentar concluir `specify`, o checkpoint atribui a primeira campanha ao contexto sucessor. `agent_orchestration.py:1394` exige então um bridge que não existia no momento do takeover. O coordenador confirmou que não há operação pública determinística para criar esse bridge e que a correção do core exige work item e autorização próprios. Nenhum Store, receipt ou código do core foi editado para contornar o gate. Estado final: `specify` em progresso, atestação disponível, ciclo em `GOAL-HOLD: HOLD-V4-02`.
