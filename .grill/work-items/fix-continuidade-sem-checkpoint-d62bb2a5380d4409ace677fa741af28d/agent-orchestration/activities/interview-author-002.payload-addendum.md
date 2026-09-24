# Adendo ao payload — interview-author-002

Nova decisão humana (coordenador Orca, msg_ff60609e12bb, 2026-09-24), registrada pelo líder como **DQ-0007 resolved**. Ainda não está nos arquivos do bundle: o líder grava depois do seu aceite, para preservar o `input_sha256` desta atividade.

**Decisão:** a variante `RESULT_RECORDED` com sessão retida ou `CLOSE_PENDING` **entra no escopo** do fix. A rota de fence autorizado (DQ-0006 opção A) cobre:

1. atividade `DISPATCHED` órfã: especialista encerrado, resultado nunca gravado, líder liberado. Caso X7: `converge-final-author-x7-3`.
2. atividade `RESULT_RECORDED` cuja sessão do especialista não foi liberada pelo Orca. O recurso fica em `CLOSE_PENDING`, e o terminal fica `releaseState=retained`/`ownershipState=user_owned`/`retainedReason=user_takeover`, com liveness `unverifiable`. Por isso `accept_activity` recusa `SESSION-CLOSE-UNPROVEN` (`grill_core/agent_orchestration.py`, `accept_activity`; `grill_core/agent_runtime.py:1206-1231`). Não há verbo que leve a atividade a `FAILED`, porque `--diagnostic` só vale em `DISPATCHED` (`grill_workspace.py:6078-6080`). Evidência viva neste mesmo work item: `interview-author-001` (dispatch `ctx_2923e0218c89`) está `RESULT_RECORDED` com recurso `CLOSE_PENDING`, e `_continuity_quiescence` passa a contá-la como ativa.

**Mantém:** o resultado não é aceito (nem na variante 2, mesmo já gravado); autorização humana exata `work_id + context_id + activity_id`; prova terminal Orca; testes negativos (sem autorização; autorização de outro contexto/atividade/run; líder vivo; especialista vivo).

**Pontos de HOW a cobrir no seu texto, sem decidir nada fora disto:**
- A prova terminal do especialista na variante 2. O release não existe (`retained/user_takeover`); o que o Orca comprova é o dispatch `settled/succeeded` com liveness `unverifiable`. Defina a prova mínima, fail-closed, e diga explicitamente o que conta como "especialista vivo" nesse estado.
- Líder vivo **versus** líder liberado. Na variante 2 o líder corrente pode estar vivo e ser quem pede o fence (caso `interview-author-001`), enquanto no X7 o líder está liberado. O teste negativo "líder vivo" foi decidido para a variante órfã. Não resolva o conflito por conta própria: se a variante 2 exigir outra regra de autoridade, liste como **DQ proposta** com opções e recomendação.
- Arestas de estado: `RESULT_RECORDED → FAILED` e `CLOSE_PENDING → CLOSED` (confira em `agent_orchestration.py` se são arestas válidas; se não forem, diga o que falta, sem mudar schema por conta própria).

Inclua a DQ-0007 nas seções do seu relatório onde couber (ROADMAP, handoff, PLAN-CONTEXT, ADR-0001, DELIVERY-MAP e CONTEXT).
