# Relatório de debug

Work item: `fix-presentation-suspension-d97e4c3d7b434c119477ec59d56ecbd5` (achado F2 do T029).
Código: branch `cadugevaerd/feat-new-subagents`, HEAD `43b5f78`, versão 6.0.28 (inclui `6ed8c90` 6.0.1 e `758454e`, ambos ancestrais do HEAD). Árvore limpa antes e depois do diagnóstico; nenhum arquivo do repositório foi editado. Script de reprodução: `/tmp/claude-1000/-home-carlosaraujo-orca-workspaces-grill-with-docs-feat-new-subagents/3964958d-682f-460e-bb2b-45936becea51/scratchpad/repro_suspension.py` (offline, usa `tests/orchestration_fixture.py`).

## Status

- **Q1 (suspensão)**: causa raiz comprovada.
- **Q2 (compactação nativa Claude)**: refutado como defeito — a tradução `compact_boundary → compaction` existe e a correção da 6.0.1 se aplica ao fallback local. Lacuna real é só de teste.
- **Q3 (fonte humana)**: comprovado que hoje nenhuma fonte é aceita, porque nenhum caminho produz `suspension`; a função pura aceita qualquer dict com o formato certo, sem vínculo ao transcript.

## Sintoma reproduzido

- Comando/cenário: `python3 repro_suspension.py` (fixture offline `orchestration_fixture.boundary`, runtime `claude`, referência aprovada `tests/fixtures/orchestration/SKILL.md`).
- Resultado observado (Exp A, caminho de produção `project_leader_presentation`):

| Caso | Transcript | Resultado do core | Contrato (SKILL.md §Bootstrap, session-protocol.md l.9) |
|---|---|---|---|
| A0 | preflight BLOCKED + `cat -- SKILL.md` | `loading=loaded application=active use_ready=true work_ready=true` | ok |
| A1 | A0 + mensagem `user` "stop adhd mode" + confirmação do assistente | **`application=active use_ready=true suspension=None`** | `application=suspended_by_user`, `use_ready=false`, `work_ready=true` |
| A2 | A1 + bloco `compaction` + novo preflight (sem releitura) | **`work_ready=false`, `STYLE-LOAD-UNCONFIRMED`, `load_request` presente** (exit 2) | `work_ready=true`, `use_ready=false`, "sem reinjetar o corpo" |

- A1 reproduz o F2 do T029 (`use_ready=True`, `stop=None` após stop). A2 mostra o efeito da 6.0.1 sobre o mesmo cenário no HEAD: em vez de liberar o trabalho suspenso, o core agora **bloqueia** e pede recarga, que o contrato proíbe durante suspensão. O ensaio A1 do T029 rodou com 6.0.0, por isso lá saiu `use_ready=true`; no HEAD o mesmo ensaio sairia exit 2.

## Evidências

| Evidência | Fonte | O que comprova |
|---|---|---|
| `presentation_state(..., suspension=None, application="active", ...)` tem defaults e é a única função que calcula `valid_suspension` / `work_ready` | `grill_core/agent_runtime.py:180-313` (l.187-188 defaults; l.275-287 cálculo) | O core sabe representar suspensão; depende de o chamador passar `suspension` e `application`. |
| `kwargs = dict(policy=..., installation=..., enablement=..., trust=...)` e `presentation_state(**kwargs)` / `presentation_state(**kwargs, loading=loading)` | `agent_runtime.py:1121-1128` (`project_leader_presentation`) | Único caminho de observação nunca passa `suspension` nem `application`. |
| `grep -n suspension grill_workspace.py` → 0 linhas; `_session_readiness` só chama `project_leader_presentation` | `grill_workspace.py:1610-1656` | Afirmação do revisor do T029 continua verdadeira no HEAD, e vale também para `project_leader_presentation`. |
| `grep -rn "stop adhd"` nos scripts → só `agent_runtime.py:275` (comparação de shape) | grep | Nenhum código lê o texto humano do transcript para derivar suspensão. |
| Exp A1/A2 (tabela acima) | `repro_suspension.py` | Sintoma reproduzido no caminho de produção com fixture oficial. |
| Exp A3: `presentation_state(**kwargs, application="suspended_by_user", loading={"stale": True}, suspension={...bound...})` → `loading=stale application=suspended_by_user use_ready=false work_ready=true load_request=None` | `repro_suspension.py`; mesmo cenário em `tests/validate_agent_orchestration_contract.py:786-796` | Contrafactual: a projeção contratual já é produzível pela função pura; falta só o produtor. |
| `_presentation()` valida `loading in {required,loaded,stale,unconfirmed}`, `application in {...suspended_by_user...}` e aceita `work_ready` com `suspension is not None` | `agent_orchestration.py:1109-1147`, `require_presentation_work_ready` l.1151 | Consumidores a jusante (init, step-enter, adopt) já aceitam a projeção suspensa; nenhum bloqueio adicional. |
| `elif kind == "system" and record.get("subtype") == "compact_boundary": role, blocks = "system", [{"type": "compaction"}]` (Claude) e `elif kind == "compacted"` (Codex) | `agent_runtime.py:682-683` e `:637-638`, introduzidos em `758454e` (2026-09-15, mesma data da 6.0.1) | Tradução nativa → bloco `compaction` existe para os dois runtimes. |
| `_full_read` corta `messages[last_compaction+1:]` | `agent_runtime.py:1074-1079` (`6ed8c90`) | Correção da 6.0.1 opera sobre blocos `compaction`, logo cobre o que `_native_messages` traduz. |
| Forma real do evento: `{"type":"system","subtype":"compact_boundary","sessionId":…,"uuid":…,"content":…,"compactMetadata":{"trigger":"manual|auto","preTokens":…,"postTokens":…}}`; resumo pós-compactação é `type=user` com `isCompactSummary=true` e `message.content` string | leitura de chaves em `~/.claude/projects/*/*.jsonl` (53 eventos, 5 variantes de chaves, todas com `type=system` + `subtype=compact_boundary`); só a forma foi copiada | Transcript sintético do Exp B segue o formato real (Claude Code 2.1.219). |
| Exp B0/B1/B2 via `LeaderBoundary.transcript()` com `contentComplete=false` + cursor `owr1_` pinado sobre JSONL em `CLAUDE_CONFIG_DIR/projects/proj/<session>.jsonl`: B1 (leitura só antes do boundary) → `compaction idx=[7]`, `_full_read → None`, projeção `use_ready=false STYLE-LOAD-UNCONFIRMED`; B2 (preflight + `cat` repetidos depois do boundary) → `_full_read → event_ref …:t4`, projeção `loading=loaded use_ready=true` | `repro_suspension.py` Exp B | O fallback local (`_local_transcript` → `_native_messages`) traduz `compact_boundary` e a 6.0.1 se aplica ao caminho observado no T029. `isCompactSummary` vira `system` e não conta como leitura. Texto humano "stop adhd mode" (`u2`) chega ao normalizado como `role=user`. |
| `grep -n "_native_messages\|compact_boundary\|_local_transcript\|isCompactSummary" tests/*.py` → 0; `grep "compacted" tests/*.py` → 0; único teste de compactação usa bloco abstrato (`validate_agent_orchestration_contract.py:490-492`) | tests/ | A tradução nativa não tem teste; a evidência acima é a primeira execução desse caminho com formato real. |
| Exp A4: `suspension={"command":"stop adhd mode","source_ref":"agent-said-so","source_sha256":"0"*64, identidade/fingerprint/scope corretos}` → `work_ready=true` | `repro_suspension.py` | `presentation_state` verifica só o formato (`agent_runtime.py:275-280`): qualquer chamador poderia forjar. Hoje não há chamador, então o risco é latente, não explorável pelo CLI. |
| Baseline `python3 tests/validate_agent_orchestration_contract.py` → `Ran 57 tests … OK` | execução | Suíte verde no HEAD; o defeito não é coberto por teste. |
| `plugin/hooks/hooks.json` só tem `SessionStart`/`SubagentStart` → `ensure_workflow.py --hook` | arquivo | Nenhum hook observa compactação ou suspensão; caminho é só o transcript. |

## Caminho de investigação/Hipóteses eliminadas

1. H1 "o core registra suspensão mas o CLI descarta" → refutada: nenhum produtor em `grill_workspace.py` nem em `project_leader_presentation`; `presentation_state` só recebe o que o chamador passa (default `None`/`active`).
2. H2 "a 6.0.1 não alcança o transcript nativo do Claude porque `compact_boundary` não vira bloco `compaction`" → refutada por Exp B (tradução em `agent_runtime.py:682`, comprovada com JSONL no formato real via `_local_transcript`).
3. H3 "o Orca entrega o transcript já com bloco `compaction`, e o fallback local nunca é usado" → não testável offline; irrelevante para a conclusão, porque os dois caminhos convergem em `_full_read` e o fallback foi comprovado.
4. H4 "hook de compactação/suspensão existe fora do core" → refutada (`hooks.json`).
5. H5 "consumidores a jusante rejeitariam `application=suspended_by_user`" → refutada (`agent_orchestration._presentation` l.1142 aceita `work_ready` com `suspension`).

## Causa raiz

**Causa raiz comprovada (Q1).** `project_leader_presentation` (`agent_runtime.py:1121-1128`) constrói `kwargs` apenas com instalação, habilitação, confiança e (depois) `loading`, e nunca deriva `suspension`/`application` do transcript observado. Como `presentation_state` tem default `application="active"` e `suspension=None`, toda projeção sai `active`; após compactação, a 6.0.1 descarta a leitura antiga e o resultado é `work_ready=false` + `STYLE-LOAD-UNCONFIRMED`, quando o contrato exige `work_ready=true`/`use_ready=false` sem recarga. Não existe nenhum produtor de `suspension` no core nem no CLI.

**Q2**: não há defeito. `_native_messages` traduz `compact_boundary` (Claude) e `compacted` (Codex) para `{"type":"compaction"}`; `_full_read` já corta antes do último bloco. Falta apenas um teste que exercite `_native_messages`/`_local_transcript` com o formato nativo.

**Q3**: nenhuma fonte humana é aceita hoje (não há produtor). Na função pura, a "prova" é só forma: `command == "stop adhd mode"`, `source_ref` string, `source_sha256` hex, identidade/fingerprint/escopo iguais — sem vínculo a evento do transcript. Autorrelato do agente não é aceito hoje porque nada é aceito; mas nada impediria um chamador de fabricar o dict.

## Cadeia causal

Humano digita `stop adhd mode` (registro `type=user`, chega ao normalizado como `role=user`) → `project_leader_presentation` observa o transcript só para `_full_read` e para os eixos de plugin (`_orca_presentation_axes`) → `presentation_state(**kwargs)` recebe `application="active"`, `suspension=None` → `valid_suspension=False`, `use_ready = prerequisites and loaded and active` → sem compactação: `use_ready=true` (F2 do T029, 6.0.0 e HEAD); com compactação (HEAD ≥ 6.0.1): `loaded=False` → `use_ready=false`, `work_ready = prerequisites and (use_ready or (suspended and valid))` = `false` → `_session_readiness` (`grill_workspace.py:1649`) levanta `STYLE-LOAD-UNCONFIRMED` exit 2 com `load_request` → sessão suspensa é obrigada a reler o corpo ou fica bloqueada.

## Arquivos envolvidos

- `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`: `presentation_state` (l.180-313) sabe representar suspensão; `project_leader_presentation` (l.1107-1129) nunca a produz; `_native_messages` (l.620-716) já traduz compactação; `_full_read` (l.1071-1104) já aplica o corte.
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py`: `_session_readiness` (l.1610-1656) só repassa a projeção; bloqueia em `work_ready=false` (l.1649). Linha 3472: mudança de `config_fingerprint`/`gwd_skill_sha256` com `use_ready=false` bloqueia — coerente com "troca de runtime/config exige nova leitura", mas vai disparar durante suspensão se a config mudar; comportamento a confirmar na correção.
- `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`: `_presentation` (l.1109-1147) e `require_presentation_work_ready` (l.1151) já aceitam a projeção suspensa.
- `tests/validate_agent_orchestration_contract.py`: cobre `presentation_state(suspension=...)` (l.786-796) e `_full_read` com bloco abstrato (l.490-492); não cobre produtor nem transcript nativo.
- `plugin/skills/grill-with-docs/SKILL.md` l.32 e `references/session-protocol.md` l.9: contrato (`stop adhd mode` → `work_ready=true`, `use_ready=false`, `loading=stale`, sem reinjeção; fonte humana da mesma sessão/incarnation/escopo).

## Proposta de correção (menor diff; não implementada)

Um único ponto: `project_leader_presentation` em `agent_runtime.py`.

1. Nova função pura `_suspension(observed, transcript, session_identity, config_fingerprint, scope)`: percorre `transcript["messages"]`, guarda a **última** mensagem com `role == "user"` e exatamente um bloco `text` cujo `text.strip() == "stop adhd mode"` (o normalizador já rebaixa `isMeta`/`isSynthetic`/`isCompactSummary` para `system`, então `user` é a origem humana disponível). Retorna `{"command": "stop adhd mode", "source_ref": observed["source_ref"] + ":" + message["id"], "source_sha256": sha256(text), "session_identity", "config_fingerprint", "scope"}` ou `None`. Não filtrar pelo último bloco `compaction`: a suspensão persiste na mesma sessão através da compactação (contrato l.32).
2. Em `project_leader_presentation`, após `presentation = presentation_state(**kwargs)`: se `_suspension(...)` for não-nulo, `presentation = presentation_state(**kwargs, application="suspended_by_user", loading={"stale": True}, suspension=...)` e **não** chamar `_full_read` (contrato: `loading=stale`, sem recarga). Caso contrário, fluxo atual.
3. Teste: no `validate_agent_orchestration_contract.py`, estender o cenário de l.486-492 com uma mensagem `user` "stop adhd mode" antes e depois de `compaction`, asserindo `application=suspended_by_user`, `loading=stale`, `work_ready=true`, `use_ready=false`, `load_request=None`, `suspension.source_ref` apontando ao id da mensagem; e um caso negativo com o mesmo texto em `role=assistant` (autorrelato) ou em resumo `isCompactSummary` → `active`. Acrescentar um teste de `_native_messages` com registro `compact_boundary` no formato acima (fecha a lacuna de Q2 em ~10 linhas).

Ordem de grandeza: ~20 linhas de produto, ~25 de teste, sem novo arquivo, stdlib apenas.

Decisões que a correção precisa fixar (fora do diff mínimo): (a) token de **reativação explícita** (SKILL.md l.32 fala em "reativação explícita" sem definir a frase; o menor diff só reconhece `stop adhd mode`, e qualquer mensagem `user` posterior que reative deve exigir nova leitura); (b) em despacho Orca, a mensagem `role=user` é o que o terminal recebeu — pode ser o coordenador, não um humano; o contrato "fonte humana" fica sendo "fonte não-agente da própria sessão", que é o máximo que o transcript prova; (c) `grill_workspace.py:3472` durante suspensão com mudança de config.

## Limitações/incertezas

- Não foi reproduzido o transporte Orca live (`worker-read` com `contentComplete=true`); só o fallback local. Os dois caminhos convergem em `_full_read`, então a conclusão de Q2 não depende disso.
- O transcript Codex (`compacted`) tem tradução no mesmo ponto (l.637) mas não foi exercitado com arquivo nativo aqui; a observação do C1 no T029 ("loaded sem releitura no Codex") não está coberta por esta reprodução.
- `source_sha256` proposto é do texto normalizado, não dos bytes do registro nativo; o adapter não expõe bytes por mensagem.

Diagnóstico encerrado. Nenhuma correção foi executada.
