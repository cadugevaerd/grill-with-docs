# Implementation Plan: Observar a instalação Codex do i-have-adhd

**Branch**: `cadugevaerd/feat-new-subagents` | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/031-codex-install-path/spec.md`

## Summary

No runtime Codex, o observer de instalação (`_orca_presentation_axes`, `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py:512-515`) só promove `installation=present` a partir de `installPath`, que o `codex plugin list --json` 0.154.0 não emite. A correção compõe o caminho a partir de campos da própria entrada nativa (`marketplaceName`, `name`, `version`) sob `<CODEX_HOME ou ~/.codex>/plugins/cache/`, exige `installed=true` e a existência do diretório e do `skills/i-have-adhd/SKILL.md`, e deixa a verificação de conteúdo para `approved_presentation_reference`, que já é comum aos dois runtimes (ADR-0001 do work item). O Claude e o caminho com `installPath` não mudam. Bump 6.0.1 → 6.0.2.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão

**Primary Dependencies**: nenhuma nova

**Storage**: leitura do sistema de arquivos (cache de plugins do Codex); nenhuma escrita

**Testing**: `unittest` via `python3 tests/run_validators.py`; validador `tests/validate_agent_orchestration_contract.py`

**Target Platform**: Linux, macOS e Windows (matriz CI: 3 SOs × Python 3.10 e 3.13)

**Project Type**: plugin CLI / biblioteca do core GWD

**Performance Goals**: um `stat` de diretório e um de arquivo por observação; sem subprocesso

**Constraints**: fail-closed; sem rede; sem `codex`, `claude` ou `node` reais nos testes; o comando nativo exigido não muda

**Scale/Scope**: 1 função alterada em 1 arquivo de produção; 1 fixture nova; testes no validador existente; 8 pontos de versão

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Situação | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | laudo `code-debug` de causa raiz comprovada (`tri-codex-install-path`); contrafactual de uma variável |
| Work item isolado e ownership | PASS | bundle `fix-codex-install-path-693af70e…`; toca só `agent_runtime.py`, o validador, uma fixture e os 8 pontos de versão |
| Feature/fix plan-only | PASS | a mudança de produto só ocorre em `implement-parallel` pelo worker |
| Sequência obrigatória | PASS | specify atestado e aceito; plan em andamento |
| Verify/review antes de ship | PASS | etapas pending, precedem ship |
| Fail-closed sem waiver | PASS | toda condição ausente mantém `undetermined`; conteúdo divergente cai em `STYLE-CONTENT-INCOMPATIBLE` pela verificação existente |
| Rastreabilidade | PASS | FR-001..FR-008 → tarefas; ADR-0001; triagem selada |
| Tier de modelo do worker Orca | PASS | tier derivado do nó pelo binding; nenhum modelo de fronteira como worker |
| Bump obrigatório | PASS | FR-008: 6.0.1 → 6.0.2 nos 8 pontos |
| Release por versão | PASS | publicada pelo pipeline no push para main |
| Governance | PASS | Constituição `54d5522b…` lida, sem emenda |

Re-check pós-design: sem mudança.

## Project Structure

### Documentation (this feature)

```text
specs/031-codex-install-path/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── codex-plugin-list.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py   # observer: ramo Codex sem installPath
tests/validate_agent_orchestration_contract.py                      # casos das histórias 1-3
tests/fixtures/orchestration/codex-plugin-list-0.154.0.json         # entrada real do Codex 0.154.0
plugin/.claude-plugin/plugin.json                                   # 6.0.2
plugin/.codex-plugin/plugin.json                                    # 6.0.2
.claude-plugin/marketplace.json                                     # 6.0.2
.agents/plugins/marketplace.json                                    # 6.0.2
tests/validate_distribution.py                                      # VERSION = 6.0.2
plugin/skills/grill-with-docs/SKILL.md                              # heading v6.0.2
plugin/skills/grill-with-docs/references/session-protocol.md       # heading v6.0.2
README.md                                                           # heading v6.0.2
```

**Structure Decision**: mudança local no observer existente, reaproveitando a resolução do home do Codex já usada no mesmo arquivo (`agent_runtime.py:440`, `:700`) e a verificação de conteúdo existente (`approved_presentation_reference`). Nenhum módulo novo.

## Complexity Tracking

Sem violações.
