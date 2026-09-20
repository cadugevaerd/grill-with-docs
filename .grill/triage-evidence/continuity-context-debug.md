# Relatório de debug

## Status
- causa raiz comprovada

## Sintoma reproduzido
- Comando/cenário ao vivo: sessão Codex nova executando `$grill-with-docs retomar ROOT --work-id feature-t029-c1-v2` (dispatch `ctx_52aa51512a16`, T029 de 2026-09-19), depois de a sessão criadora (`ctx_2d70a6015640`) ter encerrado com `worker_done`.
- Resultado observado: `code=CONTEXT-FENCED`, `error=existing leader observation differs`; nenhum trabalho liberado. O mesmo ocorreu em 2026-09-19 com o bundle `feature-claude-matrix-ensaio-…` numa sessão Claude (`ctx_b8e445392178`), e o `gauntlet-orchestration-adopt` devolveu `PREVIEW` e recusou no apply com `CONTEXT-FENCED: existing context has different runtime or session`.
- Reprodução offline: `python3 -B repro_fence.py` chamando `grill_workspace._bind_orchestration` com documento sintético.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| `mesma sessao, lider ACTIVE -> OK`; `sessao nova, lider anterior ACTIVE -> CONTEXT-FENCED` | reprodução offline | O vínculo só aceita observação de líder idêntica |
| `sessao nova, lider anterior RELEASED -> CONTEXT-FENCED` e `sessao nova, contexto RELEASED -> CONTEXT-FENCED` | reprodução offline | A recusa não depende de o líder anterior estar vivo: **não existe caminho de tomada**, em estado algum |
| `_same_observed_leader` exige `current["state"] == "ACTIVE"`, `leader.state == "ACTIVE"` e igualdade de `session_ref`, `incarnation`, `observation_ref` e `observation_sha256` | `plugin/skills/grill-with-docs/scripts/grill_workspace.py:1640-1645` | Local exato da condição |
| `_bind_orchestration` levanta `CONTEXT-FENCED` quando a comparação falha | `grill_workspace.py:1636` | Mapeia a condição ao código observado |
| No `adopt`, a mesma comparação roda **apenas** no caminho de `--apply` (dentro de `mutate`), enquanto o preview monta o payload sem verificá-la | `grill_workspace.py:1648-1695` | Explica o `PREVIEW` seguido de recusa no apply |
| `gauntlet-prepare-switch` recusa `CONTINUITY-CHECKPOINT-MISSING` quando `item["checkpoint_head"]` não é um checkpoint conhecido | `grill_workspace.py:3295-3305` | O caminho ordenado de troca não existe antes do primeiro checkpoint confirmado |
| `checkpoint_head` só é escrito ao confirmar uma etapa com `--operation-id` | `grill_workspace.py:1861` | Um item recém-criado nunca tem checkpoint |
| `LeaderBoundary.observe` já exige `dispatch.status in ("dispatched","running")`, `capabilityRevokedAt is None` e liveness `live` vinda de `agent_status` | `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py:755-790` | O adapter já sabe distinguir dispatch vivo de terminal; o que falta é usar isso para autorizar a tomada |

## Caminho de investigação/Hipóteses eliminadas
1. "O bloqueio é do estado do líder anterior; encerrar a sessão liberaria o item" → refutada: com `leader.state=RELEASED` e com o contexto inteiro `RELEASED`, a recusa é a mesma.
2. "O `adopt` é o caminho de tomada" → refutada: ele reaproveita um contexto igual ou cria um novo; diante de contexto de outra sessão, recusa no apply (`:1691`).
3. "`gauntlet-resume` resolve" → refutada: exige `--checkpoint` emitido por `prepare-switch` na origem.
4. "`prepare-switch` pode ser feito depois, pela sessão nova" → refutada: ele roda no contexto atual e, sem `checkpoint_head`, recusa (`:3303`).
5. "Falta prova de que o líder anterior morreu" → confirmada como a lacuna real: o core tem a prova disponível no adapter (`agent_runtime.py:755-790`) e não a consulta em nenhum caminho de tomada.

## Causa raiz
O ciclo de vida do contexto de orquestração não tem transição de saída: `_bind_orchestration` (`grill_workspace.py:1624-1645`) só aceita continuidade quando a observação de líder é idêntica e `ACTIVE`, e nenhum verbo — `init`, `gauntlet-orchestration-adopt` ou `gauntlet-resume` — consulta o estado real do dispatch anterior para autorizar uma sessão nova. Como `gauntlet-prepare-switch` exige um `checkpoint_head` que só existe depois da primeira etapa confirmada (`:3303`, `:1861`), um work item cujo líder encerra antes disso fica permanentemente inalcançável. O preview do `adopt` agrava o diagnóstico porque não executa a verificação que o apply executa, prometendo um resultado que não se confirma.

## Cadeia causal
Sessão A cria o contexto e encerra sem `prepare-switch` (impossível antes do primeiro checkpoint) → o contexto permanece registrado com a observação de líder de A → sessão B chama a entrada canônica → `_bind_orchestration` compara a observação de B com a de A e falha (`:1640-1645`) → `CONTEXT-FENCED` (`:1636`) → nenhum trabalho GWD é liberado, e nenhum verbo existente muda esse vínculo.

## Arquivos envolvidos
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py`: vínculo e recusa (`:1624-1645`), adopt e a assimetria preview/apply (`:1648-1695`), emissão do checkpoint de troca (`:1808-1815`), recusa `CONTINUITY-CHECKPOINT-MISSING` (`:3295-3305`), escrita de `checkpoint_head` (`:1861`).
- `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`: adapter que já observa se o dispatch está vivo (`:755-790`).
- `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`: contrato do checkpoint de continuidade (`:27`, `:671-680`).

## Limitações/incertezas
- A reprodução offline exercita `_bind_orchestration` diretamente, com documento sintético; a rota ao vivo foi observada nas duas sessões citadas, mas não foi reexecutada dentro de um teste automatizado.
- Não foi investigado o comportamento para um líder que nunca foi dispatch observável (sessão fora da orquestração); esse caso segue fora do escopo desta correção.

Diagnóstico encerrado. Nenhuma correção foi executada.
