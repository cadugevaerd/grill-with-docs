# plan-author-003 — correção do plano (Findings 1-5 + nits de plan-reviewer-002)

- payload lido por inteiro: sha256 `f6febfe75cfad6206352af3ccae51fb0ddcab43900b9f3288a22587051bbaadd` (confere)
- input manifest `plan-author-003.input.json`: 32/32 sha256 conferidos, zero divergência
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `2fc26a0`; `git diff --stat 39380f7 HEAD -- plugin tests` vazio (código idêntico ao 39380f7/4cad807/0eadd3a)
- escrita só nos cinco arquivos do grant; nenhum commit; nada em `.grill/`
- diff: 5 arquivos, +21/−21; `git diff --check` limpo
- DQ-0001..DQ-0014 intocadas; decisão de saltos (`CLOSED`, salto derivado do estado) intocada

## sha256 finais

| Arquivo | sha256 |
|---|---|
| `specs/034-fence-autorizado-atividade/plan.md` | `9710cb5ccd81648ffec72b6688e3955feb10c40c26406031291366765ef2b6a6` |
| `specs/034-fence-autorizado-atividade/research.md` | `f1b6fde6784037777fca08923782e8e348709c0c6a7aa0de1da9718686f0bdac` |
| `specs/034-fence-autorizado-atividade/data-model.md` | `837705fd1854a95cd205dee5b270cfba257d6ec868441175e382f87cb6fcc1ef` |
| `specs/034-fence-autorizado-atividade/quickstart.md` | `60c04d3fa6f4d04e77480736de2e69fd44aa9157f2c1570f21da55bef2fdc7e3` |
| `specs/034-fence-autorizado-atividade/contracts/activity-fence.md` | `5bdbc1b4d3e91efd9251c5d52a3dc817cb2059f1f865099a0c70c80bba079a53` |

## Findings — onde cada um foi aplicado

| Finding | Arquivo | Seção / linha | O que mudou |
|---|---|---|---|
| 1 (n9 pelo seam de revisão) | research.md | R11, caso (n9) | única forma válida: `read_snapshot` mockada com `revision - 1` (T:2630-2633) → `FENCE-CAS-CONFLICT` na guarda do salto 1; escrita real interposta não é CAS (apply relê em 4140, guarda em 4309-4310) — coberta por n8/n8b (estado) e n7 (hash) |
| 1 | research.md | R11, Rationale | cita plan-reviewer-002 Findings 1 e 4 |
| 1 | quickstart.md | item 1 | "`transact` interposto" → "`read_snapshot` stale (`revision - 1`) no apply → `FENCE-CAS-CONFLICT`" |
| 2a (nenhum verbo move `CLOSE_PENDING` de atividade `FAILED`) | research.md | R7, Salto 2 | texto substituído: cleanup só reporta (4450-4455); `gauntlet-activity` 6104/6147 exige `DISPATCHED|RESULT_RECORDED` (6074-6075); prepare-switch 3934/3950; nenhum verbo escreve `UNKNOWN`; divergência = corrida no salto 1, crash ou edição externa |
| 2a | contracts/activity-fence.md | bullet Recusas (linha 14) | "movido por outro verbo" → "divergente por corrida no salto 1, crash ou edição externa — nenhum verbo do core move…" |
| 2b (`preserved_resources` → `retained`) | research.md | R7, Rationale | `retained` do resume e do takeover (4064, 4281-4282); `_cleanup_checkpoint_projection` 1869-1881 projeta só workers |
| 2b | research.md | R7, Alternatives ("Um salto para `PRESERVED`") | resíduo `retained`/`preserved_resources` → só `retained` (4064, 4281-4282) |
| 3 (zero bytes; sem "exceção a FR-013") | research.md | R7, Salto 2 | texto do payload aplicado literalmente; menção a "única recusa com estado alterado / FR-013 não vale" removida |
| 3 | research.md | R7, Salto 1 | no `except`, `_fence_recorded` com solicitante divergente (corrida) → `FENCE-CAS-CONFLICT`, não "passo 3" |
| 3 | research.md | R2, passo 2 | frase: dentro do `except` de um salto, operação sob outro solicitante → `FENCE-CAS-CONFLICT` |
| 3 | contracts/activity-fence.md | bullet Recusas (linha 14) | "deixa o Store bit a bit igual, com uma exceção" → "escreve zero bytes; `FENCE-CAS-CONFLICT` pós-salto 1 reporta … o efeito já aplicado pelo salto 1 (próprio ou do solicitante vencedor)"; + frase do `except` |
| 3 | data-model.md | Transições, bullet 4 (linha 84) | mesmo texto do payload |
| 4 (retomada reexecuta prova do solicitante) | research.md | R2, passo 2 | apply da retomada reexecuta só a prova conforme `intended_after.requester.role`: `successor` → `_session_readiness` (1612-1655); `current-leader` → `_require_current_leader` (1658-1671); prova recusada → sem escrita; replay continua read-only |
| 4 | research.md | R11, caso novo (n10) + p5 | n10: seed `(FAILED, CLOSE_PENDING)` + operação, `_session_readiness` mockada para levantar → recusa, Store igual; variante `current-leader` → `LEADER-AUTHORITY-UNPROVEN`; contraprova: replay com readiness mockada continua `FENCE-REUSED`. p5 menciona a prova reexecutada |
| 4 | plan.md | Technical Context, Performance Goals (linha 25) | "a retomada faz só a prova do solicitante e o replay não observa" |
| 4 | plan.md | Source Code, nó B (linha 79) | `n1..n9` → `n1..n10` |
| 4 | data-model.md | Transições, bullet 6 (linha 86) | retomada → prova do solicitante por `role`, depois salto 2; prova recusada → nenhum byte |
| 4 | quickstart.md | item 1 | "retomada sem prova do solicitante" na lista de recusas; "retomado com a prova do solicitante reexecutada" |
| 4 | contracts/activity-fence.md | Ordem (linha 13) e Idempotência (linha 17) | retomada reexecuta a prova antes do salto 2 (sucessor → readiness; líder corrente → reobservação estrita); replay read-only e sem observação |
| 5 (`owner_dispatch` nulo) | research.md | R3 | `session_ref = "orca:" + od if isinstance(od, str) else None` (guarda de 3697) → adapter `not_observable` (1267-1268) → `FENCE-NOT-OBSERVABLE` (n6); `"orca:" + None` seria `TypeError` |
| nit HEAD | plan.md:39, research.md:3 | Constitution Check; cabeçalho | `ad42a65` → `2fc26a0`; `plan-reviewer-002` em `0eadd3a`; 32 arquivos do manifest 003 |
| nit `_require_current_leader` | research.md R4(b); data-model.md:48 | — | `1658-1670` → `1658-1671` (última linha é o `raise` em 1671) |
| nit `_session_readiness` | — | — | **não alterado, de propósito**: a função vai de 1612 a 1655 (`return` em 1654-1655; a linha 1656 é vazia, conferido com `cat -A`). A citação atual `1612-1655` em plan.md:93 e research R4(a), e `1654-1655` para o `requester`, já estão corretas; o nit do revisor ("termina em 1656, retorno em 1655-1656") está ele próprio uma linha fora |

## Citações reconferidas no HEAD `2fc26a0` (todas as tocadas)

`ws`: 1612-1655 (`_session_readiness`), 1658-1671 (`_require_current_leader`), 1869-1881 (`_cleanup_checkpoint_projection`, chaves `run_id:worker_id`), 3697 (`isinstance(dispatch, str)`), 3934, 3950, 4064, 4140, 4281-4282, 4309-4310, 4340-4343, 4450-4455, 6074-6075, 6104, 6147. `ar`: 1267-1268. `st`: 1616-1631. `T`: 2620-2637 (2630-2633 = mock `revision - 1`).

## Fora do grant (registro para o líder, sem ação)

- PLAN-CONTEXT.md continua atrás do plano nos quatro pontos listados pelo revisor (`:13`, `:21`, `:23`, `:25`); não é meu grant.

## DQs propostas

Nenhuma. Os cinco findings e os nits são precisão de HOW ou de prosa derivada de decisões já seladas (DQ-0006, DQ-0008, DQ-0009, DQ-0013, DQ-0014).
