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
