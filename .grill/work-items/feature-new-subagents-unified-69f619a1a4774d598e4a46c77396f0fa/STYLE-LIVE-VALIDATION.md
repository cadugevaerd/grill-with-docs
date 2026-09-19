# GWD 6.0.0 — validação live no Claude Code (commit ab52268)

**Veredito: PASS**

- Runtime: `claude` (Orca dispatch `ctx_0938a03dafa2`, terminal `term_f3cb57dc-a2a9-4279-b312-cb1ec4448cdc`, task `task_adcba677ea02`)
- HEAD: `ab522684d536ac3222d25dce6b20160025066da6` (branch `cadugevaerd/gwd-live-claude-validation-v3`)
- Plugin: `grill-with-docs` 6.0.0 (`plugin/.claude-plugin/plugin.json`)
- ROOT: `/home/carlosaraujo/orca/workspaces/grill-with-docs/gwd-live-claude-validation-v3`
- Data: 2026-09-15
- Código: não editado. Sessão read-only sobre o repositório.

## Sequência executada (cada evidência como tool call isolada, exigência de `_tool_results`)

0. Observação nativa de plugins (eixo `installation` de `_orca_presentation_axes`):
   `/home/carlosaraujo/.local/bin/claude plugin list --json`
   → `i-have-adhd@i-have-adhd` 0.3.0, `enabled: true`, `installPath=/home/carlosaraujo/.claude/plugins/cache/i-have-adhd/i-have-adhd/0.3.0`.

1. Preflight canônico #1:
   `/usr/bin/python3 -B <ROOT>/plugin/skills/grill-with-docs/scripts/grill_workspace.py preflight <ROOT> --runtime claude --session-ref orca:ctx_0938a03dafa2`
   → exit 2, `verdict=BLOCKED`, `code=STYLE-LOAD-UNCONFIRMED`, `presentation.loading=unconfirmed`, `use_ready=false`, `work_ready=false`, `presentation.load_request` presente.

2. `load_request` lido:
   - `skill_ref`: `/home/carlosaraujo/.claude/plugins/cache/i-have-adhd/i-have-adhd/0.3.0/skills/i-have-adhd/SKILL.md`
   - `skill_sha256`: `3170b16ace00aecb0dd7feb54c0b5aa642e7502acda06ecd24fd89a11c7127e9`
   - `body_sha256`: `7ab4bd4e805d08e56358964eea1194364a7da2a54d638c1ebb934657425bedcf`
   - `policy_sha256`: `c30b3cecf9c5cc4949c8c3d14eca050608d773f4ffa690fc2c9e72e7a95a3553`
   - `gwd_skill_sha256`: `e886c365f23324995850a5ddfdb1af27185f4ebb91203c4364974006333d342e`
   - `config_fingerprint`: `bb79f4e30d370ceac08bb7ee908e4b4c0debe46330bc78b7fcc31740dc6f515c`
   - `scope`: `{"kind":"gwd","root":"<ROOT>","work_id":null}`

3. Leitura integral exata do `skill_ref` (comando canônico `[shutil.which("cat"), "--", skill_ref]`):
   `/usr/bin/cat -- /home/carlosaraujo/.claude/plugins/cache/i-have-adhd/i-have-adhd/0.3.0/skills/i-have-adhd/SKILL.md`
   → corpo completo (10 regras, 6 exceções, pre-send check). Hash do arquivo em disco confere com a policy aprovada (`sha256sum` = `3170b16a…27e9`).

4. Preflight canônico #2 (mesmo comando de 1):
   → exit 0, `verdict=OK`, `dependencies.verdict=OK` (13 deps `present`, `missing_required=[]`), `backlog.verdict=OK` (`SGD` BOUND), `workflow.status=REUSED` (`d2c4ea08…0ab5`).

## Estado final de `presentation` (preflight #2)

| campo | valor |
|---|---|
| `compatibility` | `approved` |
| `enablement` | `enabled` |
| `trust` | `ready` |
| `loading` | **`loaded`** |
| `use_ready` | **`true`** |
| `work_ready` | **`true`** |
| `application` | `active` |
| `behavior` | `not_tested` |
| `functional_verified` | `false` |
| `load_request` | `null` |
| `diagnostics` | `[]` |

Evidência de carga (`evidence.loading`): `evidence_kind=full_read`, `event_ref=orca:ctx_0938a03dafa2:958f1c77-1dd1-41e2-a482-1029e141e6c5`, `event_sha256=3170b16a…27e9`, `session_identity`/`config_fingerprint`/`scope` iguais ao `load_request`.

## Observações

- Transporte: Orca `worker-read` devolveu `contentComplete=false` com `clipping=[message_limit_or_scan_window, transcript_payload]`; o core recuperou pelo fallback `_local_transcript` (jsonl nativo em `~/.claude/projects`, pinado pelo cursor `owr1_…` e `sourceIdentity`). Caminho previsto no código; funcionou.
- Hook rtk não reescreveu os comandos de evidência (input gravado no transcript = comando literal). Confirmado por sondagem prévia com `/usr/bin/cat -- /etc/hostname`.
- `behavior=not_tested` / `functional_verified=false` é o esperado: só amostra live + revisão independente comprovam comportamento. Fora do escopo desta tarefa.
- Critério da tarefa (`loading=loaded` ∧ `use_ready=true` ∧ `work_ready=true`) satisfeito integralmente no preflight #2.

## Codex runtime

- Instalação efetiva: `~/.codex/plugins/cache/i-have-adhd/i-have-adhd/0.3.0`, plugin `i-have-adhd@i-have-adhd`, versão `0.3.0`.
- `SKILL.md` SHA-256: `3170b16ace00aecb0dd7feb54c0b5aa642e7502acda06ecd24fd89a11c7127e9`, igual ao Claude.
- Preflight local sem sessão retorna `LEADER-AUTHORITY-UNPROVEN` por desenho; não é prova live de enablement/configuração.
- Ensaio live Codex não concluído: `codex exec --json` recusado pela quota do runtime até `2026-09-19 08:01` (`You've hit your usage limit`). Não declarar PASS live Codex sem nova sessão autorizada pelo runtime.
- Reteste em 2026-09-15: `codex exec --json --sandbox read-only --cd <worktree> 'Respond with exactly QUOTA_PROBE.'` abriu thread `01a0a58e-6b56-7eb0-a93e-7db018299664`, mas falhou antes do primeiro turno com o mesmo `usage_limit_exceeded`; a causa permanece externa e reproduzível.
- Reteste explícito com modelo Luna em 2026-09-15: `codex exec --json --sandbox read-only --cd <worktree> -m gpt-5.6-luna 'Respond with exactly LUNA_CODEX_PROBE.'` abriu thread `01a0a591-ab94-7c22-9c1d-c58c103b90a2`, mas falhou antes do primeiro turno com `You've hit your usage limit` e reset em `2026-09-19 08:01`; trocar o modelo não contorna a quota da conta.
- Reteste com a forma interativa usada pelo harness em 2026-09-15: `codex exec --ephemeral --skip-git-repo-check -s read-only --model gpt-5.6-luna -c model_reasoning_effort=low 'Respond with exactly LUNA_EPHEMERAL_PROBE.'` criou a sessão `01a0a592-4aab-7fe1-9a1d-82cec3574c32`, executou os hooks de sessão/prompt e falhou antes do turno do modelo com o mesmo limite de uso; hooks não equivalem a evidência live do Codex.
- Ensaio separado com provider OSS local em 2026-09-15: `codex exec --json --oss --local-provider ollama -m qwen3:4b --sandbox read-only --cd <worktree> 'Respond with exactly LOCAL_CODEX_PROBE.'` criou a sessão Codex `01a0a58f-ad1f-7853-9498-44fe0ef4be11` e respondeu `LOCAL_CODEX_PROBE`; o transcript nativo registra `model_provider=ollama`, `task_complete` e uso de tokens. Não conta como C1/C2/T029: não houve entrada canônica `$grill-with-docs`, nem a matriz de quatro prompts, compactação, suspensão, controle externo ou revisão independente; o modelo local também não substitui a política hospedada do runtime.

## Luna Reserve — prova interativa de carregamento

- Sessão TUI nativa em 2026-09-15: `codex -m gpt-5.6-luna -s read-only -C <worktree>`. A conta atingiu o limite do Luna primário e a interface ofereceu `Continue with Luna Reserve`; após a seleção, a sessão aplicou `model_provider_id=openai`, modelo efetivo `gpt-reserve` (Luna Reserve), esforço `medium`.
- Probe de turno real: prompt `Respond with exactly LUNA_TUI_PROBE.` → resposta exata `LUNA_TUI_PROBE`; transcript `~/.codex/sessions/2026/09/15/rollout-2026-09-15T12-05-33-01a0a59a-1370-7372-b4b5-1e9cfe680c26.jsonl`, sessão `01a0a59a-1370-7372-b4b5-1e9cfe680c26`, `task_complete`, proveniência `gpt-5.6-luna`.
- Probe direto adicional: `codex exec --json --model gpt-reserve --sandbox read-only --cd <worktree> 'Respond with exactly RESERVE_EXEC_PROBE.'` → sessão `01a0a5a8-ec4e-7b03-b9cb-289bc10bb947`, resposta exata `RESERVE_EXEC_PROBE`, exit 0 e `turn.completed`; confirma o fallback Luna Reserve também no CLI não interativo.
- Tentativa supervisionada Orca adicional: task `task_951c5e9c310d`, dispatch `ctx_eca4f50c6767`, requested/effective `gpt-reserve/low`, worktree descartável `gwd-live-evidence`; falhou antes do turno em `agent_readiness: codex-interactive-prompt`. O terminal residual foi liberado (`worker-release`, archive capturado); não há evidência de payload nem de bootstrap nessa tentativa.
- Na mesma sessão, prompt canônico `$grill-with-docs iniciar <worktree>` carregou `grill-with-docs` e `i-have-adhd` e executou o bootstrap. O fluxo encerrou corretamente sem criar work item por `LEADER-ADAPTER-UNSUPPORTED` (sem `session_ref` `orca:ctx-*`), `BACKLOG-UNAVAILABLE` e diretório temporário indisponível; portanto a prova confirma o caminho Luna/Codex e o carregamento do stack, mas não satisfaz C1/C2, T028 ou T029.
- Conclusão: Luna Reserve permite turno Codex funcional e carregamento GWD; `functional_verified` continua `false` até uma sessão Orca com adapter, backlog JSON e a matriz C1/C2 completos.

### Reteste de inicialização supervisionada Luna Reserve — 2026-09-15

Foi criado o dispatch `ctx_6297e262c85f` (`task_3726d7cda3b4`) reutilizando o terminal Codex `term_1f904333-8a16-4a51-901e-48b37926800e` já aberto com `codex -m gpt-reserve`. A interface exibiu `Continue with Luna Reserve`, porém o envio Orca para selecionar a opção retornou `agent_prompt_blocked` (request `1ffcfcac-afd9-4677-b3e1-9f9b7b5079c0` também recusado no retry); o dispatch terminou em `agent_readiness: codex-interactive-prompt`, sem turno, bootstrap ou matriz GWD, e o terminal foi fechado.

Este reteste confirma que o bloqueio é do transporte de prompt interativo supervisionado, não da inferência Luna Reserve já comprovada por `LUNA_TUI_PROBE` e `RESERVE_EXEC_PROBE`. Não há nova evidência C1/C2 ou T029; `functional_verified` permanece `false`.

### Claude A2 — carga supervisionada aprovada — 2026-09-15

O dispatch `ctx_c091ed30a3cc` (`task_22d826d4ade4`, terminal `term_38bcdf93-10c1-4927-a340-1422ee672e3d`, Claude Opus/medium) executou a retomada canônica em sessão nova. A sequência correlacionada foi `/home/carlosaraujo/.local/bin/claude plugin list --json`, primeiro preflight `STYLE-LOAD-UNCONFIRMED`, `/usr/bin/cat -- /home/carlosaraujo/.claude/plugins/cache/i-have-adhd/i-have-adhd/0.3.0/skills/i-have-adhd/SKILL.md` integral e o mesmo preflight novamente; o segundo retornou `verdict=OK`, `loading=loaded`, `evidence_kind=full_read`, `use_ready=true`, `work_ready=true`, `diagnostics=[]`, backlog `SGD BOUND` e `WORKFLOW REUSED d2c4ea08…ab5.`, com evento `orca:ctx_c091ed30a3cc:b4bcc736-1d55-42e3-bc5b-a6bde34e4d8a`.

O worker enviou `worker_done` com outcome `succeeded` e foi liberado com archive capturado. A prova cobre a carga A2; `behavior=not_tested` e `functional_verified=false` permanecem até a matriz de prompts, compactação, suspensão e revisão high independente.

### Reteste direto Luna Reserve — 2026-09-15

`codex exec --json --model gpt-reserve --sandbox read-only --cd <ROOT> 'Respond with exactly LUNA_FINAL_PROBE.'` concluiu com exit 0, resposta exata `LUNA_FINAL_PROBE` e `turn.completed`; thread `01a0a5be-1098-7a72-996d-34fae8176016`, transcript nativo `/home/carlosaraujo/.codex/sessions/2026/09/15/rollout-2026-09-15T12-44-51-01a0a5be-1098-7a72-996d-34fae8176016.jsonl`. Isto reforça que o Codex funciona no modelo Luna Reserve via CLI direto; não substitui a sessão Orca autorizada nem a matriz T029.

### Reteste direto do transporte Orca — 2026-09-15

Uma aba descartável no worktree `gwd-live-evidence` foi aberta com `codex -m gpt-reserve -s read-only -C <ROOT>`. A UI confirmou `model: Luna Reserve medium`, mas `orca terminal send --terminal term_c99514c6-8758-462c-855a-b6f265a3b2fd --text '2' --enter --wait-submit 5` falhou com `agent_prompt_blocked` (request `0b2b4ae4-8d4e-4980-aee5-b5d8c4b68043`); o retry exigido pelo mesmo ID falhou novamente com o mesmo código. A aba foi fechada com `ptyKilled=true`. Isso isola o bloqueio no transporte de entrada Orca, antes de qualquer turno, e não no modelo Luna Reserve.

### Reteste direto Orca com entrada canônica GWD — 2026-09-15

O terminal `term_c052473b-5d6e-412f-8c24-df0a8b9fffd8` foi iniciado oficialmente com `codex -m gpt-reserve -s read-only -C <ROOT> --no-alt-screen`. O terminal mostrou `model: Luna Reserve medium`, respondeu exatamente `ORCA_RESERVE_INITIAL_PROBE` e `ORCA_RESERVE_SECOND_PROBE`, e `orca terminal send` observou `input_accepted` + `turn_started` para o segundo prompt (`requestId=d4e283a0-5c90-41bd-a68e-ffeb6ef1703e`).

Na mesma sessão, `orca terminal send` aceitou a entrada canônica `$grill-with-docs:grill-with-docs iniciar <ROOT>` (`requestId=bb083101-c589-442e-87f9-7122819d3fa5`). A sessão leu `SKILL.md`, `session-protocol.md` e `agent-orchestration.md`, executou o preflight e encerrou sem criar work item: `LEADER-AUTHORITY-UNPROVEN`, seguido de `LEADER-ADAPTER-UNAVAILABLE`, porque a sessão manual não tinha Dispatch/worker Orca observável nem `session_ref=orca:ctx-*` válido.

Tentativa de anexar esse terminal ao fluxo supervisionado (`ctx_a7061ff9904b`, `worker-start --terminal ... --worktree current`) falhou em `agent_readiness: codex-interactive-prompt`; o registro marcou `exactWorker=false`. A prova confirma inferência Luna Reserve e entrada canônica GWD pelo transporte de terminal, além do gate de autoridade, mas não satisfaz C1/C2, T028 ou T029: continua faltando worker Orca gerenciado com `orca:ctx-*`, matriz de prompts, compactação, suspensão, controles externos e revisão high.

Observação: a sessão exibiu `Hook failed: hook returned invalid session start JSON output` para o hook upstream de `i-have-adhd`; o fluxo GWD continuou pelo carregamento referencial aprovado e não executou o hook upstream como parte do protocolo.

### Rota estruturada Orca com Luna Reserve — 2026-09-15

As preferências persistentes do Orca foram atualizadas pela API de settings para `experimentalNativeChat=true`, `openAgentTabsInChatByDefault=true` e `experimentalStructuredNativeChat=true`; a leitura posterior do perfil confirmou os três valores persistidos. Com essa rota, `worker-start` gerenciado aceitou um worker Codex com `requested/effective=codex/gpt-reserve/low`, `stage=input_accepted`, `turnStart=observed`, `mode=structured` e `exactWorker=true` (`ctx_8d4ae24700ee`), que respondeu exatamente `ORCA_STRUCTURED_RESERVE_PROBE`.

O dispatch canônico `ctx_b7ad00251c64` (`task_b8e73b6f01c6`) executou `$grill-with-docs:grill-with-docs iniciar <ROOT>` no mesmo modo estruturado e com `requested/effective=codex/gpt-reserve/low`. O Codex leu os artefatos GWD, executou o preflight e retornou `LEADER-AUTHORITY-UNPROVEN`; a tentativa obrigatória de `worker_done` falhou dentro do worker com `runtime_unavailable` porque o subprocesso não encontrou o runtime Orca. A rota estruturada e o turno Luna Reserve estão comprovados, mas a autoridade Orca exigida por C1/C2/T029, a matriz de quatro combinações, compactação, suspensão e controle externo continuam pendentes.

Reteste final do transporte após habilitar a rota estruturada: um terminal criado pelo próprio Orca (`term_dfea2ac7-6613-40a5-8b2f-3a96456846e7`) iniciou `codex -m gpt-reserve`, exibiu o selector `Continue with Luna Reserve` e confirmou `Luna Reserve medium`; o envio da opção `2` falhou com `agent_prompt_blocked` e o retry pelo mesmo request repetiu o código. O anexo desse terminal ao dispatch (`ctx_44cfed4f4286`) encerrou em `agent_readiness: codex-interactive-prompt`, e a aba foi fechada com `ptyKilled=true`.

Sondagem adicional no worker estruturado (`ctx_89a0841d05d4`) carregou o endpoint de hook persistido antes de executar `orca status --json`; o resultado nativo continuou `app.running=false`, `runtime.state=stale_bootstrap`, `reachable=false`, `connectionState=disconnected` e `runtimeId=none`. O worker foi parado e liberado, sem arquivo alterado; isso confirma que o subprocesso não alcança o runtime local mesmo com o endpoint de hook disponível.

### Desbloqueio do transporte Orca e novo bloqueio de cota Codex — 2026-09-16

O bloqueio registrado em 2026-09-15 (`agent_prompt_blocked`, `app.running=false`, `runtime.state=stale_bootstrap`) tinha duas causas distintas, agora separadas por evidência:

1. **Shim de CLI obsoleto.** `/home/carlosaraujo/.local/bin/orca` apontava por caminho absoluto para o build `7f9c0f2efa39b02dbfc6151b`, removido pela atualização do Orca; qualquer `orca ...` falhava com `No such file or directory` antes de alcançar o runtime. O shim foi repontado para o launcher estável `/home/carlosaraujo/.cache/orca/appimage/launcher/installed` (mesmo alvo já usado por `orca-ide`); backup do arquivo anterior em `orca.bak.20260916`. Após o reparo, `orca status --json` retorna `runtime.state=ready`, `reachable=true`, `connectionState=connected`, `appVersion=1.4.204`, `runtimeId=6a50b4af-426a-42ad-93c5-f4918ff8590e`.

2. **Transporte de prompt supervisionado agora funciona.** No Orca 1.4.204 as capacidades `terminal.prompt-delivery.v1`, `agent-session.structured.v1` e `orchestration.worker-launch-preferences.v1` estão anunciadas. Run `run_4b5cd3b5215c` (objetivo T029/T030) e `worker-start --agent codex --model gpt-reserve --effort low --worktree current` produziram `state=ready`, `stage=input_accepted`, `turnStart=observed`, `mode=structured` (`reason=user_default`), `exactWorker=true` e `launch.effective == launch.requested` (`codex/gpt-reserve/low`) no dispatch `ctx_c01ea9c44806` (`task_74727ed765d5`). Nenhum `agent_prompt_blocked` ocorreu. Em 2026-09-17 o transporte foi reconfirmado fora da orquestração: `terminal create --command claude` no root de ensaio, `terminal wait --for tui-idle` satisfeito e `terminal send --wait-submit 20` com estágios `input_accepted` + `turn_started` (`requestId=4c158935-adf9-4cd6-9eb6-d9df6fc417dd`, provider `claude`, `observation=supported`), respondido exatamente `CLAUDE_TRANSPORT_PROBE_1`. Isso encerra o `HOLD-V4-02` de 2026-09-15 pelo fato observado — a entrada supervisionada agora é aceita. **A causa do bloqueio anterior não está provada**: o shim quebrado foi detectado só em 2026-09-16 e as chamadas `orca` de 2026-09-15 retornavam receipts normais, logo o shim não pode explicar o `agent_prompt_blocked` daquela data. As hipóteses restantes são a atualização do Orca para 1.4.204 (que anuncia `terminal.prompt-delivery.v1`) e o próprio selector interativo do Codex; nenhuma foi isolada.

3. **Novo impedimento externo: cota Codex esgotada.** O turno do worker falhou no provider, não no transporte: `codexErrorInfo=usageLimitExceeded`, `willRetry=false`, thread `01a0aa2e-4233-7032-b0cc-cd9c0912be78`, mensagem `You've hit your usage limit. ... try again at Sep 19th, 2026 8:01 AM.` A falha foi reproduzida fora do Orca com `codex exec --json --sandbox read-only 'Respond with exactly CODEX_QUOTA_PROBE.'`, que retornou `turn.failed` com a mesma mensagem — logo a cota é da conta, não do modelo `gpt-reserve` nem da rota estruturada. O dispatch foi encerrado com `worker-stop` (`state=stopped`, `processAction=closed_agent_terminal`) sob prova positiva de parada: última volta do transcript é a notificação de erro, sem `worker_done`.

Consequência para T029: a metade Codex da matriz (C1 e C2) fica pendente até 2026-09-19 08:01 por impedimento externo de cota, registrado como impedimento e não como PASS. A metade Claude (A1 e A2) não depende dessa cota. `functional_verified` permanece `false`.

### Preparação da metade Claude (A1/A2) e orçamento dos runtimes — 2026-09-17

Root de ensaio: o `gwd-live-claude-validation-v3` usado em 2026-09-15 **não existe mais**. O root descartável corrente é `/home/carlosaraujo/orca/workspaces/grill-with-docs/gwd-claude-matrix` (worktree Orca `73370200-23ff-4ab0-ac89-5bbd64fc6c00::…/gwd-claude-matrix`, branch `cadugevaerd/gwd-claude-matrix`, HEAD `fb4494eeb416c2da4d7a5821ef0222d13457fa64`, plugin 6.0.0), que já contém o bundle de ensaio `feature-claude-matrix-ensaio-24e485a9d1c94192a2ff8303c2761e6a` (`status=in-progress`, `current_step=specify`, `audit_verdict=pending`, WORKFLOW `d2c4ea08…0ab5`, Constituição `54d5522b…7569`).

Transporte de entrada para Claude confirmado nesta data, fora da orquestração: `terminal create --command claude` no root de ensaio (`term_2290a1ac-0626-45d6-a794-1f26e2150346`, incarnation `ad522e7d-0002-4a4b-81e6-10ac1a17adad`), `terminal wait --for tui-idle` com `satisfied=true`, e `terminal send --enter --wait-submit 20` com estágios `input_accepted` + `turn_started` (`requestId=4c158935-adf9-4cd6-9eb6-d9df6fc417dd`, `provider=claude`, `observation=supported`). A sessão respondeu exatamente `CLAUDE_TRANSPORT_PROBE_1`. Isso prova a conversa multi-turno dirigida pelo líder, que é o mecanismo exigido pela matriz de quatro prompts fixos. O terminal foi fechado (`ptyKilled=true`). Este probe **não** é caso A1/A2: não houve entrada canônica GWD nem os prompts da matriz.

Ambiente registrado na mesma sessão (`/status` e `/usage` nativos): Claude Code `2.1.274`, sessão `330c8224-663d-4353-96c6-50d9bd91a38d`, kind `interactive`, modelo `opus (claude-opus-5)`, login `Claude Max account`, cwd igual ao root de ensaio. `claude plugin list --json` confirma `i-have-adhd@i-have-adhd` 0.3.0, `scope=user`, `enabled=true`, `installPath=/home/carlosaraujo/.claude/plugins/cache/i-have-adhd/i-have-adhd/0.3.0` — corrige a anotação local de que o plugin estaria ausente neste root.

**Orçamento dos dois runtimes, medido e não inferido:**

| Runtime | Estado | Reset |
|---|---|---|
| Codex | cota da conta esgotada (`usageLimitExceeded`) | 2026-09-19 08:01 |
| Claude | 88% da semana consumidos (`/usage`, semana corrente, todos os modelos) | 2026-09-18 19:59 (America/Sao_Paulo) |

Consequência: os 12% restantes de Claude não cobrem com folga a metade A completa (A1 e A2, quatro prompts fixos por caso, compactação com recarga, ensaio `stop adhd mode`, dois controles externos e revisão high independente), e gastá-los agora também consumiria o orçamento do líder. A partir de 2026-09-19 08:01 as duas cotas estão simultaneamente renovadas, o que permite executar C1/C2/A1/A2 na mesma janela e sob condições comparáveis — que é o que a matriz exige. Nenhum caso da matriz foi executado nesta data.

### Abertura da janela da matriz e novo impedimento de transporte Claude — 2026-09-19

Orçamento medido: Codex liberado (`codex exec` respondeu exatamente `CODEX_QUOTA_PROBE_0919`, thread `01a0ba59-1864-7132-98c0-18d3397beff8`); Claude com 5% da semana e 11% da sessão (`/usage` em terminal descartável, fechado sem conversa). Versões correntes: Claude Code `2.1.278`, codex-cli `0.154.0`, Orca `1.4.205`. A candidata instalada é a fonte: `plugin/` sem diff desde `ab52268`, e os caches `~/.claude/plugins/cache/grill-with-docs/grill-with-docs/6.0.0` e `~/.codex/plugins/cache/grill-with-docs/grill-with-docs/6.0.0` são idênticos a `plugin/skills` fora de `__pycache__`. i-have-adhd 0.3.0 `enabled` nos dois runtimes, SKILL.md `3170b16a…27e9` igual ao aprovado; nenhuma flag `.i-have-adhd-always` em `~/.claude` nem `~/.codex`.

Digests de configuração antes do ensaio: `~/.claude/settings.json` `0f559d7d…24fb`, `~/.claude/plugins/installed_plugins.json` `b3ced039…d4d5`, `~/.codex/config.toml` `b96c77e2…d28d`, `~/.claude/CLAUDE.md` `5bd90f0a…db8`.

**Controle externo ANTES** (root git vazio no scratchpad da sessão, sem CLAUDE.md/AGENTS.md/WORKFLOW.md/.grill/.specify nos ancestrais; primeiro prompt fixo, sem invocar GWD nem i-have-adhd):

- Claude `claude -p` (sessão `3aafc892-2d15-472c-b82f-bc7daeed937c`, `claude-opus-5`, 1 turno): nenhuma tool call, nenhuma invocação GWD, nenhuma leitura do SKILL.md do i-have-adhd. Resposta conserva os seis fatos.
- Codex `codex exec` (thread `01a0ba5a-e693-7c50-9871-ec001f48d3b5`): **o modelo leu por conta própria o `SKILL.md` do GWD** (invocação implícita pelo tema do prompt: bundle, receipt, WORKFLOW) e fez duas buscas `rg` no cache GWD. Não leu o SKILL.md do i-have-adhd. É o comportamento de base, antes do ensaio; fica registrado como desvio a julgar pelo revisor, porque o critério do controle é "ausência de evento de carga GWD" e o GWD é invocável implicitamente no Codex.

**Tentativas A1 — nenhum caso executado.**

1. Sessão Claude interativa comum em ROOT (`term_227941fd…`, `/grill-with-docs:grill-with-docs iniciar ROOT`): recusa correta `LEADER-AUTHORITY-UNPROVEN`, porque o adapter só aceita `--session-ref orca:ctx_<dispatch>` (`agent_runtime.py:754`). Terminal fechado.
2. Run `run_4c1e68222164`. `worker-start --agent claude --model opus --effort medium` (dispatch `ctx_afd141e79408`, e de novo `ctx_aa82af47d0dc`): `launch.effective == launch.requested`, mas o modo é `structured` (`reason=user_default`) e as duas tentativas terminaram em `outcome_unknown`, `failedStage=dispatch_input`, `dispatch preamble was submitted but not acknowledged`. O transcript nativo da segunda (`ce6be9df-fd06-427c-aadd-b14e2a9cc4b8`) tem o preâmbulo como único turno de usuário e nenhum turno do assistente; `worker-show` reporta `observation.status=exited`. `worker-stop` devolveu `stop_unknown` (`processAction=none`, processo já encerrado). Causa não isolada: nenhum registro no `daemon.log` nem no trace do Orca.
3. Terminal Claude próprio + `worker-start --terminal` (dispatch `ctx_e1c826948095`): o worker nasceu `ready` em modo terminal, mas `launch.requested` e `launch.effective` ficam `null` quando o terminal é reutilizado. O worker invocou GWD e o preflight recusou corretamente com `LEADER-AUTHORITY-UNPROVEN`: o adapter exige `effective.agent == runtime == terminal.agentIdentity == projection.provider.id`. `worker_done --outcome failed` aceito; worker liberado (`retained`, `external_terminal`) e terminal fechado.

Consequência: com o default do Orca em sessão estruturada, não existe hoje um caminho que entregue ao core um worker Claude com `launch.effective` preenchido **e** vivo. Os bloqueios do core estão corretos e não devem ser afrouxados. O dispatch de 2026-09-15 que passou (`ctx_0938a03dafa2`) era worker de terminal. A matriz continua não executada; `functional_verified` permanece `false`.

### Matriz T029 executada — 2026-09-19

Transporte destravado pelo operador: em Settings → Experimental, desligou "Use updated structured native chat" (`experimentalStructuredNativeChat=false`). Com isso o Orca decide `mode=terminal` (`reason=user_default`), porque o modo estruturado exige as três chaves `experimentalNativeChat`, `openAgentTabsInChatByDefault` e `experimentalStructuredNativeChat`. A terceira tentativa estruturada (`ctx_f4b6c2d1cd5c`) falhou do mesmo jeito que as duas anteriores e foi parada. Todos os workers abaixo são de terminal, com `launch.effective == launch.requested`. Run `run_4c1e68222164`. ROOT de ensaio: `gwd-claude-matrix` (HEAD `fb4494e`).

**A1 — Claude novo, `/grill-with-docs:grill-with-docs iniciar ROOT`** (dispatch `ctx_b8e445392178`, terminal `term_3e3fa442-d93a-4f86-a827-39da43caebaa`, claude/opus/medium, transcript `bb37d5f5-8145-4530-a8de-404a03c62954`, sha256 `32cc08a8…6177`):

- O preflight fechou com `loading=loaded`, `use_ready=true` e `work_ready=true` antes da primeira resposta de trabalho (evento `orca:ctx_b8e445392178:fa4aa6fc…`).
- O `init --work-id` no bundle antigo `feature-claude-matrix-ensaio-…` recusou `CONTEXT-FENCED` ("existing leader observation differs"). O `gauntlet-orchestration-adopt` deu `PREVIEW` (`0e6c7aa5…`) e o apply recusou `CONTEXT-FENCED` ("existing context has different runtime or session"). Por decisão do coordenador, a sessão abriu um work item novo, `feature-t029-a1-ensaio-7abd6d1962e14619855632d4117384ab` (`CREATED`, store_revision 918), com carga correlacionada (`orca:ctx_b8e445392178:e07dfc34…`). O bundle antigo ficou intocado.
- A sessão respondeu aos quatro prompts fixos.
- `/compact` nativo (boundary em 16:39:27Z) → retomada GWD → releitura integral por `/usr/bin/cat --` do SKILL.md às 16:40:10Z → prompt 2 respondido.
- `stop adhd mode` (16:41) → `/compact` (16:42:04Z) → retomada GWD sem nenhuma releitura (a única tool call pós-boundary foi plugin list + preflight) e trabalho continuado com `work_ready=true`.
- A etapa `specify` foi fechada pelo fluxo canônico com autor `fable/xhigh` (`ctx_b8c79e00bb97`, `succeeded`, `spec.md` `7670362a…dab4`) e revisor independente `fable/high` (`ctx_11bf56e05fa7`, `APPROVED`). Os dois foram lançados pelo coordenador, porque o worker recebeu `consumer_fenced` ao tentar criar workers, e fechados com `worker-release` (`closed_agent_terminal`) e read-back `exited`.
- Troca de sessão preparada: `cp-switch-b9ab5c9b4e73616f5adb2737`.

**A2 — Claude novo, `/grill-with-docs:grill-with-docs retomar ROOT`** (dispatch `ctx_b0677ebdf3ff`, terminal `term_655bbc13-dfcd-4781-ae91-354072cd6421`, claude/opus/medium, transcript `68b4bf22-c4d5-42a0-bb84-d98873bb09e2`, sha256 `5f438761…`):

- `gauntlet-resume` terminou `RESUMED` (contexto `ctx-7823e006d5e0abf6716dfaba`, época 2, preview `605559b5…2af7f`). Carga própria: `full_read`, evento `orca:ctx_b0677ebdf3ff:3861bafc…`.
- O aceite do `specify` ficou intacto (`7670362a…`), sem repetição.
- Os quatro prompts fixos foram respondidos.
- Troca Claude→Codex preparada: `cp-switch-ab3b9bdd36464e6fe0ad34db`. O contexto de origem ficou `RELEASED`.
- Antes do preview passar, a sessão recebeu `STYLE-DEPENDENCY-UNDETERMINED` e `STYLE-LOAD-UNCONFIRMED`, e resolveu os dois com os comandos literais exigidos pelo observer (`/home/carlosaraujo/.local/bin/claude plugin list --json` sem prefixo `cd`, e `/usr/bin/cat --` com caminho absoluto).

**C1 — Codex novo, `$grill-with-docs iniciar ROOT`** (dispatch `ctx_dc4fd5fc4d91`, terminal `term_8646b54c-1b9c-49a4-accc-66e2f6d1b3d9`, codex/gpt-5.6-sol/medium, rollout `01a0baa3-7e61-7142-b940-d467bc08d1d9`, sha256 `f91ad4d2…`): **FAIL**.

- Primeiro desvio: `init` recusa `STYLE-DEPENDENCY-UNDETERMINED`. O `codex plugin list --json` (codex-cli 0.154.0) lista `i-have-adhd@i-have-adhd` 0.3.0 com `installed=true` e `enabled=true`, mas sem `installPath`: a entrada traz só `source.url` e `ref`. O observer (`agent_runtime.py:511-514`) só promove a instalação a partir de `installPath`, então `installation` fica `undetermined`. É a primeira entrada GWD real no Codex; nenhuma sondagem anterior tinha chegado a esse ponto.
- `worker_done --outcome failed` aceito e worker liberado.
- Desvio lateral: antes do bootstrap o modelo iniciou `python3 tests/run_validators.py` no ROOT, fora do escopo, e parou quando o coordenador pediu.
- **C2 não foi executado**, porque depende de C1 e da correção do observer.

**Controle externo DEPOIS** (mesmo root externo e mesmo prompt 1): Claude `06d5c4be-5fde-474e-9c94-a812a94f51ce` sem tool call e sem GWD ou i-have-adhd; Codex thread `01a0bab0-acc1-7980-ad22-14d97c3583ff` sem nenhum comando. Nenhum dos dois carregou i-have-adhd. A leitura implícita do GWD pelo Codex, vista no controle ANTES, não se repetiu, logo é estocástica e anterior ao ensaio. Digests de configuração antes e depois **idênticos**. Nenhuma flag `.i-have-adhd-always`. A única configuração alterada no período foi a preferência Orca do operador, descrita acima, que não é configuração de estilo.

**Lacunas do core observadas** (candidatas a correção, nenhuma contornada):

1. Nenhum verbo permite que uma sessão nova assuma um work item cujo líder morreu: `init`, `adopt` e `resume` recusam com `CONTEXT-FENCED`, ou exigem `prepare-switch` feito pela origem.
2. O preview do `gauntlet-orchestration-adopt` devolve `PREVIEW` para um apply que recusará `CONTEXT-FENCED`.
3. `gauntlet-prepare-switch` recusa `CONTINUITY-CHECKPOINT-MISSING` antes da primeira etapa com checkpoint. Um work item recém-criado não pode trocar de sessão.
4. O preflight não observa compactação nem `stop adhd mode`. Depois de stop+compactação ele continuou reportando `application=active` e `use_ready=true` com base na leitura anterior à compactação. Quem manteve o contrato foi a sessão; o core não impôs.
5. O observer de instalação Codex exige `installPath`, que o `codex plugin list --json` 0.154.0 não emite. Esta lacuna bloqueia C1/C2.
6. Suspeita, não verificada: o checkpoint de troca de A1 gravou em `constitution_sha256` e `workflow_sha256` valores que não são os hashes da Constituição e do WORKFLOW.

Resultado da matriz: metade Claude executada (A1, A2, compactação, suspensão, controles), à espera da revisão high independente; metade Codex em FAIL no C1 por lacuna do observer. `functional_verified` permanece `false`. FR-024/SC-008 **não** podem ser aceitos.

### Revisão high independente da metade Claude — 2026-09-19

Revisor `claude/fable/high` (dispatch `ctx_fd4529792b16`, `launch.effective == launch.requested`, sessão distinta do líder, dos autores das respostas e dos especialistas do ensaio), read-only sobre os transcripts. Veredito do revisor: **FAIL**. O líder não reverte o julgamento. Relatório integral abaixo (sha256 `7634bfafa0b840fcee5bad2a56f4e2a69d6fb033da6aeff51b7dde388ec877e8`).

<details><summary>REVIEW-A-HALF.md</summary>

#### REVIEW-A-HALF — revisão independente da metade Claude (T029, A1 e A2)

- Data: 2026-09-19
- Revisor: worker Orca `task_9235d5e78c5a` / dispatch `ctx_fd4529792b16`, sessão distinta das sessões A1/A2, read-only.
- Contrato: `specs/030-agent-orchestration/quickstart.md` §8.
- Referência aprovada: `~/.claude/plugins/cache/i-have-adhd/i-have-adhd/0.3.0/skills/i-have-adhd/SKILL.md`, sha256 recalculado `3170b16ace00aecb0dd7feb54c0b5aa642e7502acda06ecd24fd89a11c7127e9` (bate com o informado).
- Fontes: `A1.readable.md`, `A2.readable.md`, conferidos contra `A1.transcript.jsonl` (sessão `bb37d5f5-…`) e `A2.transcript.jsonl` (sessão `68b4bf22-…`); `prompt1..4.txt`; `ext-{before,after}-claude.json`; `ext-{before,after}-codex.jsonl`; `config-{before,after}.sha256`.
- Método: leitura integral das respostas; ordem de eventos, corpo dos `cat` e presença dos nomes dos fatos verificados por script sobre o JSONL bruto. Nenhum julgamento de estilo por regex.

##### Veredito da metade Claude: **FAIL**

Dois critérios explícitos do §8 não ficam comprovados pela evidência:

1. **F1 — A2, prompt 3: três dos seis fatos perdem o nome.** A resposta cita `hash da Constituição`, `último receipt aceito` e `recurso preservado` apenas por ordinal: "Os fatos 4, 5 e 6 continuam pendentes, nenhum descartado." O critério é "zero perda dos seis fatos" em cada resposta. A pendência não foi descartada, mas o conteúdo saiu da tela; é exatamente o que a premissa 1 e a regra 5 da referência proíbem.
2. **F2 — A1, ensaio stop+compactação: a suspensão não fica registrada.** O preflight pós-compactação devolveu `{'loading': 'loaded', 'work_ready': True, 'use_ready': True, 'behavior': 'not_tested', 'application': 'active', 'stop': None}` e ainda trouxe `load_request`. O §8 exige registro com `use_ready` false e fonte humana vinculada. O comportamento do agente foi correto (não releu, tratou `use_ready` como false por conta própria); o registro do core não.

Tudo o mais passa: carga antes da primeira resposta de trabalho em A1 e A2, recarga após a compactação ativa, nenhuma releitura após stop+compactação, 8 das 9 respostas avaliadas conformes às dez regras e seis exceções, controles externos Claude sem carga GWD/i-have-adhd e configurações byte a byte iguais.

O que inverte o veredito, por decisão do líder: aceitar referência ordinal como preservação (F1) **e** tratar o registro de suspensão como defeito do core fora desta metade (F2). Sem as duas decisões, o caminho é repetir o prompt 3 em sessão A2 nova e corrigir o registro de stop antes de repetir o ensaio de suspensão.

##### 1. Ordem de carga (JSONL bruto)

Todos os `cat` devolveram 7206 caracteres, `is_error=false`, corpo idêntico ao arquivo de referência (comparação literal).

| Sessão | Evento | idx | Horário (UTC) |
|---|---|---|---|
| A1 | `/usr/bin/cat -- …/SKILL.md` (1ª carga) | 230 | 16:32:30 |
| A1 | `/usr/bin/cat --` (novo escopo de work_id) | 271 | 16:32:49 |
| A1 | **Primeira resposta de trabalho** ("Próximo passo: coordenador escolhe…") | 318 | 16:33:26 |
| A1 | `/usr/bin/cat --` (work item novo, opção B) | 419 | 16:36:19 |
| A1 | Prompts 1–4 | 466–505 | 16:36:57–16:38:15 |
| A1 | `compact_boundary` manual (217580 → 33046 tokens) | 521 | 16:39:27 |
| A1 | `/usr/bin/cat --` (**recarga pós-compactação**) | 631 | 16:40:10 |
| A1 | Resposta de retomada; prompt 2 repetido | 655; 660–665 | 16:40:31; 16:40:48 |
| A1 | `stop adhd mode` → confirmação | 675–680 | 16:41:07 |
| A1 | `compact_boundary` manual (144309 → 31299) | 691 | 16:42:04 |
| A1 | Pós-stop até o fim (idx 692–1882): **zero** `tool_use` com `i-have-adhd` + `SKILL.md` | — | até 17:02:04 |
| A2 | `cat -- …/SKILL.md` (não absoluto; corpo entregue, core não contou) | 185 | 17:03:29 |
| A2 | `/usr/bin/cat --` (canônico) | 240 | 17:03:50 |
| A2 | **Primeira resposta de trabalho** ("Próximo passo: me mande o próximo turno…") | 286 | 17:04:28 |
| A2 | Prompts 1–4 | 291–335 | 17:04:38–17:05:55 |

Conclusões:
- Carga antes da primeira resposta de trabalho: **sim** em A1 e A2. Antes da carga só há narração curta de ferramenta ("Now preflight with session-ref."), não resposta de trabalho.
- Recarga após compactação ativa: **sim** (A1 idx 631), com motivo declarado: "Corpo não está no contexto atual → releitura integral."
- O resumo da 1ª compactação (idx 522, 10457 chars) não carrega os títulos das regras; histórico com hash não substituiu o corpo.
- Após stop+compactação: **nenhuma releitura**. O resumo (idx 692) registra "the SKILL.md body is not re-injected". A sessão disse: "Mantenho o modo ADHD desligado nesta sessão, sem reler a skill, e trato `use_ready` como `false`."
- A2 não herdou `loaded` de A1: carga própria, sessão e `session-ref` novos (`orca:ctx_b0677ebdf3ff`).
- Prompts: os quatro textos de `prompt1..4.txt` aparecem literais nos turnos; nenhum turno de prompt menciona estilo ou i-have-adhd. Nenhuma invocação manual da skill i-have-adhd.

##### 2. Matriz caso × regra/exceção

Códigos: **C** conformant · **NC** non_conformant · **NA** not_applicable · **EX** regra sobreposta por exceção aplicada corretamente. Casos: P1–P4 = prompts fixos; P2c = prompt 2 após compactação.

| Regra / exceção | A1-P1 | A1-P2 | A1-P3 | A1-P4 | A1-P2c | A2-P1 | A2-P2 | A2-P3 | A2-P4 |
|---|---|---|---|---|---|---|---|---|---|
| R1 ação primeiro | C | C | C | EX | C¹ | C | C | C | EX |
| R2 passos numerados | C | C | C | NA | C | C | C | C | NA |
| R3 fecha com uma ação | C | C | C | C | C | C | C | C | C |
| R4 sem tangentes | C | C | C | C | C | C | C | C | C |
| R5 reafirma estado | C | C | C | C | C | C | C | **NC** | C |
| R6 estimativa em unidades | C | C | C | C | C | C | C | C | C |
| R7 trabalho concluído visível | NA | C | NA | NA | C | NA | C | NA | NA |
| R8 erro factual | NA | NA | C | C | NA | NA | NA | C² | C |
| R9 listas ≤5 por grupo | C | C | C | C³ | C | C | C | C | C |
| R10 sem preâmbulo/recap/fecho | C | C | C | C | C | C | C | C | C |
| E1 "explique" | NA | NA | C | C | NA | NA | NA | C⁴ | C |
| E2 ação destrutiva | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| E3 espiral de debug | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| E4 ambiguidade real | NA | NA | C | NA | NA | NA | NA | C | NA |
| E5 regra contra a tarefa | C | NA | NA | C | NA | C | NA | NA | C |
| E6 regra contra o harness | C | C | C | C | C | C | C | C | C |

###### Motivos e citações

**R1.** Todas as respostas P1–P3 abrem com ação executável pelo operador. A1-P1: "Primeiro passo (cerca de 2 minutos): rode este comando…" seguido do bloco de comando. A2-P2: "Próximo passo: rode `sha256sum WORKFLOW.md` e compare…". P4 é pedido de explicação; a exceção 1 libera o corpo e a ação vai no fecho (A1-P4 abre com a tese "Os seis fatos juntos provam que o bundle conferido é o certo…"; A2-P4 abre com título e estado).
¹ A1-P2c: a primeira frase é estado e a ação vem na segunda frase da mesma linha ("…2 de 6 fatos conferidos. O próximo passo é rodar `sha256sum …`"). O prompt pede "onde estou e o próximo passo" nessa ordem; aceito como conforme, marginal.

**R2.** Fatos numerados 1–6 (ou 3–6 quando dois já foram conferidos), uma ação por item. A1-P3 e A2-P3 usam marcadores para ramos condicionais, que não são sequência. NA em P4: explicação, não procedimento.

**R3.** Todas fecham com uma ação única de menos de dois minutos. A1-P3: "Próximo passo: rode o `sha256sum` e diga qual linha não bate." A2-P4: "Próximo: rode `sha256sum WORKFLOW.md` e cole a saída aqui (1 minuto)."

**R4.** Nenhum "a propósito". As menções laterais sustentam o fato em discussão (A1-P4 cita o bundle antigo `CONTEXT-FENCED` para justificar o work_id; A2-P4 cita "quatro work items ativos" pelo mesmo motivo).

**R5.** Estado presente em todas: "2 de 6 fatos conferidos" (A1-P2, A1-P2c, A2-P2, A2-P3, A2-P4), "Estado: entrada GWD concluída…" (A1-P1), "Estado: retomada `RESUMED`…" (A2-P1), seção "Onde você está" (A1-P3, A1-P4).
**NC em A2-P3:** o estado é reafirmado só por ordinal — "Os fatos 4, 5 e 6 continuam pendentes, nenhum descartado." O leitor precisa lembrar o que são 4, 5 e 6. Ver F1. A ferramenta de tarefas do harness não se aplica: os passos são do operador ("sem executar ações"), não do agente.

**R6.** Minutos concretos em todas. A1-P1: "cerca de 8 minutos, ou de 15 a 20 minutos se precisar procurar o store do fato 6". A2-P1: "Leva uns 2 minutos. A conferência inteira leva de 10 a 15 minutos."

**R7.** NA quando nada foi concluído no turno (o prompt proíbe ações; A1-P1 diz "nenhuma ação executada neste turno"). C em P2/P2c: "Work_id e branch estão OK."; "Conferidos (não repetir): 1. work_id 2. branch".

**R8.** Tom factual, sem "Uh oh", sem causa inventada. A1-P3: "Um digest observado difere de um digest registrado. Não dá para saber ainda se é só um deles ou os dois." e "Não sei qual ferramenta o emitiu".
² A2-P3 atribui a divergência ao fato 3 ("O fato 3, hash do WORKFLOW, está **divergente e não conferido**"). O prompt não diz qual digest divergiu; a inferência vem do passo anterior, que pedia só `sha256sum WORKFLOW.md`. Não é causa afirmada, e a própria resposta lista "Qual artefato divergiu" como não concluível. Conforme, com tensão interna leve (O3).

**R9.** Grupos de no máximo quatro itens: A1-P1 agrupa 4+2 ("Grupo A… Grupo B"), A2-P1 e A2-P4 agrupam 3+3.
³ A1-P4 usa seis seções planas de mesmo nível, sem o agrupamento 4+2 de P1. A regra fala em "aim for" e manda nunca omitir quando completude importa; o prompt exige os seis. Conforme, com observação O1.

**R10.** Nenhum abridor ou fecho proibido nas nove respostas (busca por "vou", "deixe-me", "espero que", "qualquer dúvida", "uh oh" e equivalentes: zero ocorrências). A1-P4 termina na ação, sem recap.

**E1.** P3 e P4 pedem "Explique". A1-P3, A1-P4 e A2-P4 usam cabeçalhos ("## O que o resultado permite concluir", "## 3. hash do WORKFLOW", "### 5. Último receipt aceito — pendente").
⁴ A2-P3 usa rótulos em negrito em vez de cabeçalhos. Cumpre a função de releitura; marginal (O4).

**E2, E3.** NA: os prompts proíbem ação e não há sequência de três "ainda quebrado".

**E4.** Em P3 não se sabe qual digest divergiu. As duas sessões não chutaram: deram a verificação que resolve a dúvida. Conforme ao princípio; nenhuma pergunta foi necessária.

**E5.** Os seis fatos excedem o teto de cinco. A tarefa venceu e a forma ficou: agrupamento em P1/P4, nenhum fato cortado.

**E6.** Estimativas apontam para quem executa (o operador), como o prompt pede ("para eu fazê-lo"). Nenhuma ação executada contra a ordem do turno. Nenhum conflito de harness impediu comportamento exigido.

###### A1 — `stop adhd mode` e pós-compactação

| Item | Resultado | Citação |
|---|---|---|
| Confirmação em uma linha (seção Persistence) | C | "Modo ADHD desligado a partir de agora. O trabalho GWD continua liberado (`work_ready`) e as respostas voltam ao estilo padrão." |
| Trabalho continua | C | "Retomada OK. O item `feature-t029-a1-ensaio-…` está liberado para trabalho." |
| Sem releitura do corpo | C | zero leituras do SKILL.md em idx 692–1882; "sem reler a skill" |
| Dez regras / seis exceções | NA | modo desligado pelo leitor; a suspensão não é caso positivo |
| Registro `use_ready=false` + fonte humana | **não comprovado** | preflight: `'use_ready': True, 'application': 'active', 'stop': None` (F2) |
| Atividade autorizada seguinte no GWD | C | `specify` fechado com autor/revisor aceitos, checkpoint `cp-switch-b9ab5c9b4e73616f5adb2737` |

##### 3. Preservação dos seis fatos

Presença do **nome** do fato em cada resposta (verificado no JSONL):

| Resposta | work_id | branch | hash do WORKFLOW | hash da Constituição | último receipt aceito | recurso preservado + motivo |
|---|---|---|---|---|---|---|
| A1-P1 | sim | sim | sim | sim | sim | sim |
| A1-P2 | sim | sim | sim | sim | sim | sim |
| A1-P3 | sim | sim | sim | sim | sim | sim |
| A1-P4 (detalhada) | sim | sim | sim | sim | sim | sim |
| A1-P2c | sim | sim | sim | sim | sim | sim |
| A2-P1 | sim | sim | sim | sim | sim | sim |
| A2-P2 | sim | sim | sim | sim | sim | sim |
| **A2-P3** | sim | sim | sim | **só "fato 4"** | **só "fato 5"** | **só "fato 6"** |
| A2-P4 (detalhada) | sim | sim | sim | sim | sim | sim |

Notas sem perda:
- A2-P1, A2-P2 e A2-P4 não dão o valor do hash da Constituição e dizem por quê: "ainda não observei esse valor nesta sessão". O fato fica preservado com três fontes de conferência; a incerteza é real e foi mantida.
- A1-P2c omite os valores literais dos hashes que A1-P2 trazia e aponta para `immutable.workflow.sha256` e `immutable.constitution.sha256`. Os seis fatos e o motivo do fato 6 seguem presentes.
- Fato 6 sempre acompanha o motivo: A1 "confira se tem motivo de preservação ou `UNKNOWN`"; A2 "o motivo dele precisa estar registrado; sem motivo, o fato não confere".
- A2-P4 recupera os seis nomes no turno seguinte a A2-P3.

##### 4. Controles externos

**Configuração.** `config-before.sha256` e `config-after.sha256` idênticos (`diff` vazio) para `~/.claude/settings.json`, `installed_plugins.json`, `~/.codex/config.toml` e `~/.claude/CLAUDE.md`. Nenhuma flag global nova.

**Claude (`ext-before-claude.json`, `ext-after-claude.json`).** Root `…/scratchpad/extctl`, modelo `claude-opus-5`, `output_style: default`, sessões `3aafc892-…` e `06d5c4be-…`.
- Zero `tool_use` nas duas sessões (`num_turns: 1`). Nenhuma leitura de `skills/i-have-adhd/SKILL.md`, nenhuma chamada a `grill_workspace.py`, nenhuma invocação de skill.
- As 9 ocorrências de "adhd" em cada arquivo vêm só do evento `init` (lista de plugins, skills e slash commands). Instalado não é carregado.
- As respostas não têm a forma injetada: abrem com contexto ("Nada foi executado. Não sei onde fica o manifesto…"; "Nada executado. Não li o bundle…"), põem o primeiro passo no meio ou no fim e não fecham com "Próximo passo". Antes e depois seguem o mesmo padrão. Contrato anterior preservado.
- Observação: as duas respostas citam um hook de sessão ("o hook informou que `WORKFLOW.md` não existe na raiz `extctl`"). É hook read-only do plugin GWD habilitado globalmente, igual antes e depois; não é evento de carga de estilo.
- Resultado: **intacto**.

**Codex (`ext-before-codex.jsonl`, `ext-after-codex.jsonl`)** — fora da metade Claude, avaliado por ordem da tarefa.
- `ext-after-codex`: nenhum comando executado, zero menções a "adhd" ou `grill_workspace`. Limpo.
- `ext-before-codex`: **F3.** A sessão leu o SKILL.md do GWD por iniciativa própria: "Vou usar `grill-with-docs` apenas como referência…", depois `sed -n '1,240p' …/grill-with-docs/6.0.0/skills/grill-with-docs/SKILL.md` e dois `rg` no cache do plugin. Não houve preflight nem leitura de `skills/i-have-adhd` (as 22 ocorrências de "adhd" vêm do texto do GWD lido). Não há injeção de estilo i-have-adhd, mas há evento de leitura do GWD num controle que o §8 quer sem carga GWD. Quem julga a metade Codex deve decidir se a linha de base vale.
- Os `.err` do Codex trazem só "Reading additional input from stdin...".

##### 5. Achados

| ID | Severidade | Caso | Achado | Evidência |
|---|---|---|---|---|
| F1 | bloqueante | A2-P3 | Três fatos citados só por ordinal; nomes fora da tela. Viola "zero perda" e R5. | "Os fatos 4, 5 e 6 continuam pendentes, nenhum descartado." (A2 idx 325) |
| F2 | bloqueante (core, não estilo) | A1 pós-stop | Suspensão não registrada: preflight devolve `application=active`, `use_ready=True`, `stop=None` e `load_request`. `grep suspension` em `grill_workspace.py` retorna zero linhas; `agent_runtime.py:271-283` aceita `suspension`, mas nenhum chamador do CLI a fornece. Causa raiz não investigada além disso. | A1 idx 739; resposta idx 753: "o preflight não registrou o seu pedido" |
| F3 | a decidir na metade Codex | ext-before-codex | Controle externo leu o SKILL.md do GWD antes do ensaio. | três `command_execution` sobre `…/grill-with-docs/6.0.0/skills/grill-with-docs/` |
| O1 | menor | A1-P4 | Seis seções planas; P1 agrupava 4+2. | cabeçalhos "## 1." a "## 6." |
| O2 | menor | A1-P2c | Estado antes da ação na primeira linha. | "No cenário, você está com 2 de 6 fatos conferidos. O próximo passo é…" |
| O3 | menor | A2-P3, A2-P4 | Atribui a divergência ao fato 3 sem o prompt dizer qual digest; a mesma resposta lista "Qual artefato divergiu" como não concluível. | "O fato 3, hash do WORKFLOW, está **divergente e não conferido**" |
| O4 | menor | A2-P3 | Rótulos em negrito no lugar de cabeçalhos num pedido de "Explique". | "**O que ele não permite concluir:**" |
| O5 | menor | A2-P4 | Expressões figuradas que o pre-send check manda trocar. | "o que ficou pendurado"; "bloqueia o trabalho de verdade" |
| O6 | menor | A2-P4 | Hash do WORKFLOW fica no grupo "Identidade", mas o resumo o junta ao fato 4 ("sob quais regras"). | "Os fatos 3 e 4 dizem **sob quais regras**…" |
| O7 | informativo | A2 | Primeiro `cat` não absoluto não conta para o core; o corpo chegou ao contexto duas vezes. Sem efeito no resultado. | A2 idx 185 e 240 |

##### 6. Resultado por critério do §8 (metade Claude)

| Critério | Resultado |
|---|---|
| A1: carga real pela GWD antes da primeira resposta de trabalho, sem chamada manual | PASS |
| A2: checkpoint do ensaio, carga própria, sem herança de `loaded`, outputs aceitos intactos | PASS ("Aceite preservado: `specify` complete… Nenhum resultado aceito foi repetido.") |
| Recarga após compactação ativa + prompt 2 repetido | PASS |
| Respostas conformes às dez regras e seis exceções | 8 de 9 PASS; A2-P3 NC em R5 |
| Zero perda dos seis fatos, inclusive na detalhada | **FAIL em A2-P3** (F1); detalhadas A1-P4 e A2-P4 completas |
| Stop+compactação: sem releitura, trabalho continua | PASS |
| Stop+compactação: registro `use_ready=false` com fonte humana | **não comprovado** (F2) |
| Controle externo Claude antes/depois sem carga, sem flag nova, config preservada | PASS |
| **Metade Claude** | **FAIL** — primeiro desvio: A2-P3 (F1); segundo: registro de suspensão em A1 (F2) |

</details>
