# Revisão independente (high) — STYLE-LIVE-VALIDATION.md e requisito i-have-adhd (spec 030)

- Revisor: Orca dispatch `ctx_7ab98d94b908`, task `task_b1c7f6de4b5a`, terminal `term_8fb5de14-3a40-4455-b6d9-ac43c09c0e34`, runtime Claude Code 2.1.272 (claude-fable-5-1).
- Objeto: `.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/STYLE-LIVE-VALIDATION.md` (sha256 `28665523a2304c40ad44b160009150a10a332ec9803cedfbf60943820a9373ba`, commit `49d63e5`), sobre a candidata `ab52268` (GWD 6.0.0).
- Escopo: US8 / FR-021..FR-024 / SC-008 / T029 de `specs/030-agent-orchestration`. Código não editado. Nenhum `codex exec` invocado nesta revisão.
- Data: 2026-09-15.

## Veredito

| Pergunta | Resposta |
|---|---|
| O laudo é fiel à fonte nativa? | **Sim.** Cada passo reproduzido no transcript Claude. |
| Evidência Claude é suficiente para o critério da task que gerou o laudo (`loading=loaded ∧ use_ready ∧ work_ready`)? | **Sim.** |
| Evidência Claude é suficiente para FR-024 / SC-008 / Result de T029? | **Não.** É amostra parcial do eixo *carregamento* (A1 mecânico). Comportamento, retomada, compactação, suspensão e controle externo não foram ensaiados. |
| Codex live? | **Bloqueado por quota do runtime.** Confirmado em rollout nativo. Zero evidência live Codex. |
| T029 pode ser aceita? | **Não.** Permanece pendente nos dois CLIs, como o próprio dossiê já registra. |

## 1. Verificação do laudo contra a fonte nativa

Transcript: `~/.claude/projects/-home-carlosaraujo-orca-workspaces-grill-with-docs-gwd-live-claude-validation-v3/0e93d92b-2df7-4270-926c-7892aa59eab0.jsonl` (300 linhas, 1 turno humano = o TASK do dispatch `ctx_0938a03dafa2`).

| Passo do laudo | Fonte | Confere |
|---|---|---|
| 0. `claude plugin list --json` | tool_use `0d4ed583…`, 14:21:10Z; `i-have-adhd@i-have-adhd` 0.3.0 `enabled:true`, `installPath …/0.3.0` | ✔ (reproduzido hoje: mesmo estado) |
| 1. Preflight #1 | tool_use `7499a50a…`, 14:21:25Z; `Exit code 2`, `verdict=BLOCKED`, `code=STYLE-LOAD-UNCONFIRMED`, `loading=unconfirmed`, `use_ready=false`, `work_ready=false`, diagnóstico `full read not observed for this session` | ✔ |
| 2. `load_request` | presente no preflight #1; `skill_sha256=3170b16a…27e9`, `body_sha256=7ab4bd4e…edcf`, `scope.work_id=null` | ✔ |
| 3. `cat -- <skill_ref>` | tool_use `5f9238e9…`, result uuid `958f1c77-1dd1-41e2-a482-1029e141e6c5`, 14:21:32Z; corpo = arquivo em disco menos o `\n` final (7206/7207 bytes); `sha256(result+"\n") = 3170b16a…27e9` = arquivo | ✔ leitura integral real |
| 4. Preflight #2 | tool_use `bb6d208e…`, 14:21:36Z; `verdict=OK`, `loading=loaded`, `use_ready=true`, `work_ready=true`, `behavior=not_tested`, `functional_verified=false`, `diagnostics=[]`, `evidence.loading.evidence_kind=full_read`, `event_ref=orca:ctx_0938a03dafa2:958f1c77…`, `event_sha256=3170b16a…27e9` | ✔ |
| HEAD `ab52268`, plugin 6.0.0 | tool_use `cdc602a8…`; worktree `gwd-live-claude-validation-v3` ainda em `ab52268` | ✔ |
| Comandos não reescritos pelo hook rtk | input gravado no transcript = comando literal | ✔ |

Semântica dos campos bate com o core: `agent_runtime.py:258` só marca `loaded` com `evidence_kind == "full_read"`; `:292` `functional_verified = use_ready and behavior == "conformant"`; `agent_orchestration.py:1123` recusa `functional_verified` sem `conformant`. O laudo não infla nenhum eixo.

Hashes independentes hoje: Claude e Codex `SKILL.md` 0.3.0 = `3170b16a…27e9` (iguais). `dependencies.json` declara `i-have-adhd` `harness-plugin`, `required:true`, `min 0.3.0`, argv delegados por runtime. Consistente com plan.md §Apresentação local.

## 2. Suficiência frente ao requisito

### O que a evidência Claude prova
- FR-021 (parcial, só Claude): componente instalado e habilitado; a GWD candidata pede carga e reconhece leitura real da mesma sessão, sem invocar `/i-have-adhd`.
- FR-023: os quatro eixos aparecem separados (`installation/enablement/trust/loading/behavior`); exit 0 e `loaded` não viraram `functional`. Diagnóstico específico no bloqueio.
- Mecânica de correlação sessão↔evento↔hash funciona com transporte Orca degradado (`worker-read` clipado → fallback `_local_transcript`), como o docstring do core prevê.

### O que ela NÃO prova (lacunas contra quickstart §8 / T029)
1. **Invocação canônica ausente.** A sessão não abriu `/grill-with-docs iniciar ROOT`; executou `grill_workspace.py preflight` por instrução explícita da task. FR-021 exige "skill GWD atualizada aplica por padrão ao iniciar/retomar". Prova de bootstrap pela skill não existe.
2. **Sem bundle.** `scope.work_id=null`; T029 exige work item com checkpoint (C2/A2 retomam "o mesmo checkpoint").
3. **Nenhum dos quatro prompts fixos** (`seis fatos…`) foi enviado. Zero respostas reais; `behavior=not_tested`. FR-024: "instalação, configuração ou teste isolado MUST NOT substituir essa prova".
4. **A2 (retomar) não executado.** Só a mecânica de A1.
5. **Compactação, `stop adhd mode`→compactação→trabalho, nova sessão pós-suspensão, saída explícita do GWD**: não ensaiados.
6. **Controle externo** (root sem GWD, antes/depois) e **digests de configuração** antes/depois: ausentes. FR-022/SC-008 "zero alteração do padrão externo" sem evidência.
7. `claude --version` não registrado no laudo (quickstart pede). Hoje: 2.1.272.
8. `plugin list` foi a observação nativa, mas o laudo não registra `installedAt/lastUpdated` nem digest do registro; menor.

Conclusão: o PASS do laudo é honesto para o critério estreito da task de origem e o próprio texto delimita ("`behavior=not_tested` … fora do escopo"). Não pode ser lido como PASS de FR-024/SC-008. Peso correto: **amostra positiva do eixo loading em Claude, pré-condição de A1, não A1 completo**.

## 3. Codex — bloqueio por quota (confirmado)

Fonte nativa: `~/.codex/sessions/2026/09/15/rollout-2026-09-15T11-03-50-01a0a561-92e8-7b61-bb4e-33db41d14dd8.jsonl`.

- `session_meta`: `originator=codex_exec`, `cli_version=0.154.0`, `cwd=/home/carlosaraujo/orca/workspaces/grill-with-docs/feat-new-subagents`, sandbox `read-only`, 2026-09-15T14:03:50Z (11:03 BRT).
- `task_complete` 4,7 s depois com `error.codex_error_info=usage_limit_exceeded`: "You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at Sep 19th, 2026 8:01 AM." `last_agent_message=null`: nenhum turno do modelo ocorreu.
- Instalação Codex: `~/.codex/plugins/cache/i-have-adhd/i-have-adhd/0.3.0`, `SKILL.md` hash igual ao Claude. Instalação ≠ habilitação ≠ carga ≠ comportamento (FR-023); nada disso foi observado live no Codex.
- Preflight offline retorna `LEADER-AUTHORITY-UNPROVEN` por desenho; não substitui sessão.

**Registro:** C1/C2 (Codex) **bloqueados por quota do runtime até 2026-09-19 08:01 (America/Sao_Paulo)**. Impedimento de ambiente, não falha da candidata nem PASS. Quickstart §8: "não rebaixar o escopo para um CLI".

## 4. Consistência do dossiê

- `tasks.md`: T028/T029/T030 continuam `- [ ]`. ✔
- `IMPLEMENTATION-INTEGRATION.md` (sha `7c802f86…63aa`, igual ao selado em `state.json`): T029 listada como pendente, "não criar esse arquivo como parte desta proposta". ✔ Sem alegação de PASS live.
- `state.json` em `49d63e5`: `implement-parallel=complete`, `current_step=converge`. Não afirma aceite de estilo. Sem conflito com este veredito.
- Nenhum arquivo do dossiê declara FR-024/SC-008 satisfeito. Sem over-claim.

## 5. Recomendações (sem editar código)

1. Manter T029 **pendente**. Anotar no dossiê o laudo Claude como "amostra loading/A1-mecânica, Claude only, sem comportamento".
2. Após 2026-09-19 08:01 BRT, rodar a matriz §8 **inteira numa campanha só**, nos dois CLIs, a partir de sessão nova que invoque GWD canonicamente com work item real: C1/C2/A1/A2 + quatro prompts + compactação + `stop adhd mode` + controle externo + digests de config antes/depois + `codex --version`/`claude --version`. Repetir só o loading não fecha nada.
3. Persistir prompts/respostas com IDs de mensagem do transcript nativo (como o laudo fez para o `cat`); o revisor high julga as dez regras/exceções sobre esse texto.
4. Se a quota Codex voltar antes, priorizar Codex: hoje é o CLI com zero evidência.

## Anexo — o que esta revisão executou
- Leitura integral: laudo, spec.md (US8, FR-020..024, SC-008), plan.md §Apresentação local, quickstart §7/§8, tasks.md T029/T030, checklists, IMPLEMENTATION-INTEGRATION.md.
- Reprodução independente: `sha256sum` dos dois `SKILL.md`; `claude plugin list --json`; `claude --version`; `codex --version`; parse do transcript Claude e do rollout Codex; grep do core (`agent_runtime.py`, `agent_orchestration.py`); `git show 49d63e5`; `git worktree list`.
- Não executado: `codex exec`, preflight novo, qualquer escrita no repositório.
