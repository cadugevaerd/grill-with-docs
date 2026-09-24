# Research: Continuidade de contexto sem líder vivo

## R1 — O que conta como prova de que o condutor anterior encerrou

- **Decision**: observação do dispatch anterior pelo mesmo adapter Orca já usado em `LeaderBoundary`, aceitando apenas: `dispatch.status` fora de `dispatched|running`; ou `capabilityRevokedAt` não nulo; ou `projection.liveness.verdict == "exited"` com `source == "agent_status"`. A observação normalizada já carrega `activity` em `{active, idle, exited, unknown}` e `close` em `{not_requested, pending, closed, unknown, preserved}` (`agent_runtime.py:900-975`).
- **Rationale**: é a mesma fonte que hoje autoriza o líder a agir; usar outra fonte criaria duas verdades sobre o mesmo fato.
- **Alternatives considered**: confiar em flag do operador (a prova viraria a palavra de quem chama); inferir de silêncio ou timeout (silêncio é ausência, não prova).

## R2 — Onde a tomada entra

- **Decision**: verbo próprio (`gauntlet-context-takeover`), preview-first, com `--expected-sha256` sobre as entradas relidas e `--session-ref` da sessão que assume. `_bind_orchestration` ganha o caminho de sucessão apenas quando a tomada já foi autorizada e registrada; o caminho comum continua exigindo observação idêntica.
- **Rationale**: ato excepcional com nome próprio é auditável; embutir no `init` ou no `adopt` esconderia a exceção dentro de um caminho comum.
- **Alternatives considered**: estender `adopt` com flag (mistura adoção de legado com sucessão de condutor, dois fatos diferentes).

## R3 — Códigos de recusa

- **Decision**: `TAKEOVER-LEADER-ACTIVE` (condutor vivo), `TAKEOVER-EVIDENCE-UNPROVEN` (observação inconclusiva, ausente ou não correlacionada) e `TAKEOVER-NOT-OBSERVABLE` (condutor anterior não é dispatch observável). `CONTEXT-FENCED` permanece para o caminho comum, sem mudar de significado.
- **Rationale**: FR-002 e FR-010 exigem distinguir os casos e dizer qual prova faltou; reusar um código só tornaria as três causas indistinguíveis.

## R4 — Troca antes do primeiro checkpoint

- **Decision**: quando `item["checkpoint_head"]` não aponta para checkpoint conhecido, `gauntlet-prepare-switch` emite o checkpoint inicial a partir do estado corrente, em vez de recusar (`grill_workspace.py:3295-3305`).
- **Rationale**: o checkpoint é uma projeção do estado; não existe motivo para exigir etapa confirmada antes de projetá-lo.
- **Alternatives considered**: exigir uma etapa confirmada artificial (falsificaria progresso).

## R5 — Renomeação dos campos e compatibilidade

- **Decision**: `workflow_sha256` vira `context_inputs_sha256` e `constitution_sha256` vira `origin_metadata_sha256`, em `grill-continuity-checkpoint/v2`; a leitura aceita v1 e v2 e escolhe as chaves pelo schema declarado. Nada é reescrito.
- **Rationale**: ADR-0002; o conjunto obrigatório de chaves é validado por schema (`agent_orchestration.py:671-680`), então versionar é a forma barata de manter selado o que já existe.

## R6 — Concorrência

- **Decision**: a tomada usa o mesmo compare-and-swap por revisão do store; duas tomadas simultâneas terminam com uma aceita e a outra recusada por estado alterado.
- **Rationale**: é a garantia que o store já oferece; não introduzir lock novo.
