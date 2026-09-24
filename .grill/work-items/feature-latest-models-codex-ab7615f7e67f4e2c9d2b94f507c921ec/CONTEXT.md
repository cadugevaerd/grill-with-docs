# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| família de modelo | Linha de modelo Codex identificada pelo sufixo do slug (`luna`, `terra`, `sol`, `astra`), estável entre gerações | alias, apelido, versão | ADR-0001; `codex debug models` |
| catálogo local do Codex | Arquivo `models_cache.json` sob o home do Codex, com os slugs listados, `visibility` e `priority` | registry, lista de modelos | `~/.codex/models_cache.json` |
| slug resolvido | Id explícito de modelo (ex. `gpt-6-sol`) escolhido para uma família: o listado de menor `priority` | modelo atual, latest | ADR-0001 |
| tier | Nível abstrato do nó (`small`, `medium`, `large`) mapeado para uma família | tamanho, classe | `assets/workflow-tier-models.json`; decisão de projeto `docs/adr/0013-worker-model-floor.md` |
| alias de modelo Claude | Nome curto de linha de modelo Claude (`haiku`, `sonnet`, `opus`) que o harness resolve para o modelo mais recente da linha; `opus` resolve hoje para `claude-opus-5-5` | slug fixo, versão | ADR-0002; `assets/workflow-tier-models.json` |
| papel de especialista | Autor ou revisor de julgamento da policy de orquestração, com modelo e esforço exigidos por runtime | subagente, reviewer genérico | `assets/agent-orchestration.v1.json` |

## Proveniência desta entrevista

- Triagem vinculada: `.grill/triage/tri-latest-models.json`; laudo: `.grill/triage/latest-models-debug.md`.
- Decisões de DQ-0001..DQ-0005 vieram de `feature-latest-models-dbf134a84fc14114a438bddf1da709b6` no commit `1af890b`; humano via coordenador Orca, 2026-09-23, reconfirmado 2026-09-24.
- Runtime do novo work item: Codex; sessão líder `orca:ctx_721188de91bf`.
