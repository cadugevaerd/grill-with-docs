# Implementation Plan: Destravar a ponte com o backlog operacional

**Branch**: `feat/backlog-ssot` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-backlog-bridge-unlock/spec.md`

## Summary

FASE-001 do work item `feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4`. Três defeitos independentes mantêm `backlog_sync_command` inoperante; esta fase corrige os três e acrescenta a deduplicação que o armazenamento não oferece.

Abordagem: trocar o gate de integridade errado por um gate de identidade em `grill_workspace.py`, remover o filtro de estado em `backlog_bridge.py`, introduzir o mapa de estados de ADR-0003 e transformar o conjunto de deduplicação num índice que também permita reconciliar estado de item já existente.

Nenhum arquivo novo de produção. A mudança é cirúrgica em duas funções e uma constante.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão. Sem dependência externa, por restrição do core.

**Primary Dependencies**: nenhuma em runtime. O `backlogctl` é processo externo, alcançado apenas por `Toolchain.run`, e o contrato falado é `backlogctl --json ... --db PATH` com envelope `result=ok` e `contract_version=2`.

**Storage**: nenhum armazenamento próprio. O estado dos itens vive no backlog operacional e é acessado exclusivamente pela interface pública; ler o SQLite direto é proibido.

**Testing**: `unittest` da stdlib, executado por `tests/run_validators.py`, que faz glob de `tests/validate_*.py`. O alvo é `tests/validate_backlog_contract.py`, que já tem os dois seams necessários: `StubToolchain`, que grava chamadas e responde por tabela roteirizada, e a substituição de `MODULE.resolve_cli`.

**Target Platform**: matriz de CI com ubuntu, windows e macos, em Python 3.10 e 3.13. Nenhum dos runners tem `backlogctl`, `specify` ou `node`.

**Project Type**: plugin de CLI, consumido pelo próprio repositório em dogfooding.

**Performance Goals**: não aplicável. O número de decisões por work item é da ordem de unidades; o custo é dominado por chamadas de processo externo.

**Constraints**: preview é o padrão e nada muta sem `--apply`; toda recusa é nomeada e não deixa estado parcial; a ponte nunca acessa o armazenamento diretamente; nenhum teste pode exigir binário externo real.

**Scale/Scope**: duas funções alteradas em `backlog_bridge.py`, uma linha de gate em `grill_workspace.py`, uma constante de mapa nova. Acervo atual de referência: 8 decisões em 4 work items, das quais 1 já espelhada.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Status | Evidência / justificativa |
|---|---|---|
| Evidência antes de afirmação | PASS | Cada defeito tem reprodução registrada: `BUNDLE-INTEGRITY` observado nos três work items, FSM medida em 25 pares, duplicata confirmada em banco descartável. As correções ganham regressão que reprova o comportamento antigo. |
| Work item isolado e ownership | PASS | Trabalho conduzido em `feat/backlog-ssot`, com identidade fixada no bloco imutável do work item. Nenhum artefato escrito em diretório de outro work id. |
| Feature/fix plan-only | PASS | A sessão de entrevista terminou em `PLAN_ONLY_STOP`. Esta fase corre no ciclo externo do Spec Kit, que é onde a implementação é autorizada. |
| Sequência obrigatória do desenvolvimento | PASS | `specify` concluído, `plan` em curso. Nenhum passo saltado; checkpoint gravado no work item. |
| Verify/review antes de ship | PASS | Planejado: `verify` e `review` precedem `ship`, conforme a sequência. |
| Fail-closed sem waiver | PASS | Nenhuma recusa existente é afrouxada. FR-002 preserva a recusa por adulteração de identidade, e FR-009 preserva a recusa sem backlog vinculado. O que muda é a recusa **errada**, que reprovava alteração legítima de artefato. |
| Rastreabilidade | PASS | Fase, ADR e decisões referenciadas no ROADMAP, PLAN-CONTEXT e handoff do work item, e citadas nesta spec. |
| Bump obrigatório do plugin | PASS | Esta fase toca `plugin/**`, portanto exige bump antes de merge. Alvo desta fase: **2.8.0 → 2.9.0**, incremento menor, porque corrige defeito e amplia comportamento sem quebrar contrato publicado. A inversão de autoridade que justifica 3.0.0 chega em fases posteriores. |

Nenhuma violação. Seção de Complexity Tracking omitida.

**Recheck pós-design (Fase 1)**: os artefatos de design não introduziram violação. O desfecho `TRANSITIONED`, novo em `data-model.md`, amplia o relato sem afrouxar recusa; o contrato registra explicitamente que `BUNDLE-INTEGRITY` deixa de ser alcançável **apenas** neste comando, permanecendo válido onde bundle intocado é exigência legítima. A cláusula de bump continua endereçada com alvo 2.9.0, verificável por `tests/validate_distribution.py`.

## Project Structure

### Documentation (this feature)

```text
specs/015-backlog-bridge-unlock/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   └── backlog-sync-cli.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Gerado por /speckit-tasks
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/
├── scripts/
│   ├── backlog_bridge.py       # parse_deferred, sync_items, mapa de estados
│   └── grill_workspace.py      # backlog_sync_command: gate de identidade
├── SKILL.md                    # heading de versão
└── .claude-plugin/plugin.json  # versão
   .codex-plugin/plugin.json    # versão

tests/
├── validate_backlog_contract.py  # regressões desta fase
└── validate_distribution.py      # constante VERSION

.claude-plugin/marketplace.json
.agents/plugins/marketplace.json
README.md
```

**Structure Decision**: repositório existente, sem estrutura nova. A mudança concentra-se em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`, com uma alteração pontual em `grill_workspace.py` e as regressões em `tests/validate_backlog_contract.py`. Os oito lugares de versão listados acima são fixados por `tests/validate_distribution.py` e precisam mudar juntos.
