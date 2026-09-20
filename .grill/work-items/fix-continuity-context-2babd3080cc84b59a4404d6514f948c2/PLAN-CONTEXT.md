# PLAN-CONTEXT

## FASE-001 — Continuidade de contexto sem líder vivo
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002
- BLs: BL-0001
- delivery-units: DU-001
- development-type: platform-devops

### HOW
- Pontos de mudança, todos em `plugin/skills/grill-with-docs/scripts/`: o vínculo de contexto (`grill_workspace.py:1624-1645`, `_bind_orchestration` e `_same_observed_leader`), o `adopt` (`:1686-1695`), a emissão do checkpoint de troca (`:1808-1815`), a recusa `CONTINUITY-CHECKPOINT-MISSING` (`:3295-3305`) e o contrato do checkpoint (`grill_core/agent_orchestration.py:27` e `:671-680`).
- A prova de líder terminal reaproveita o adapter existente (`grill_core/agent_runtime.py`, `LeaderBoundary`), que já observa `dispatch.status`, `capabilityRevokedAt` e a liveness do host; a tomada aceita somente os estados terminais e recusa `unverifiable` com código nomeado.
- Preview do `adopt` passa a executar a mesma verificação de líder do apply, devolvendo a recusa em vez de `PREVIEW` quando o apply iria recusar. Preview continua sem escrever byte algum.
- `gauntlet-prepare-switch` sem `checkpoint_head` emite o checkpoint inicial do estado corrente, em vez de recusar.
- Renomeação dos dois campos sobe o schema do checkpoint; o leitor aceita os dois schemas e escolhe as chaves pelo schema declarado, sem tentativa e erro, e nenhum checkpoint selado é reescrito.
- Somente biblioteca padrão; sem processo novo; sem rede. Testes offline pelos seams já usados nos validadores de orquestração e continuidade, com fixtures derivadas de saída real do adapter, nunca do código.
- Risco: afrouxar a prova de líder abriria dois líderes simultâneos; por isso a ausência de resposta do host nunca autoriza a tomada.
