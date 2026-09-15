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
