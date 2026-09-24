# Implementation Plan: Continuidade de contexto sem líder vivo

**Branch**: `cadugevaerd/feat-new-subagents` | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/032-continuity-context/spec.md`

## Summary

O ciclo de vida do contexto de orquestração não tem transição de saída: `_bind_orchestration` (`grill_workspace.py:1624-1645`) só aceita observação de líder idêntica e `ACTIVE`, e nenhum verbo consulta o estado real do dispatch anterior. A entrega acrescenta uma **tomada de contexto** explícita, autorizada por observação de dispatch terminal vinda do host (reaproveitando o adapter que já normaliza `activity` e `close`, `grill_core/agent_runtime.py:900-975`), libera `gauntlet-prepare-switch` antes do primeiro checkpoint, dá ao preview do `gauntlet-orchestration-adopt` a mesma verificação do apply e renomeia os dois campos de digest do checkpoint em schema novo (ADR-0001, ADR-0002). Bump 6.0.2 → 6.0.3.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão

**Primary Dependencies**: nenhuma nova

**Storage**: store JSON do orquestrador em `.git/grill/orchestrator.json`, por CAS com revisão

**Testing**: `unittest` via `python3 tests/run_validators.py`; validadores de orquestração e de continuidade

**Target Platform**: Linux, macOS e Windows (matriz CI: 3 SOs × Python 3.10 e 3.13)

**Project Type**: plugin CLI / biblioteca do core GWD

**Performance Goals**: uma observação do host por tomada; nenhuma leitura adicional no caminho quente

**Constraints**: fail-closed; ausência de prova nunca autoriza; nenhum checkpoint selado é reescrito; sem rede e sem processo novo no core

**Scale/Scope**: 4 pontos de mudança no core, 1 contrato de checkpoint versionado, testes nos validadores existentes, 8 pontos de versão

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Situação | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | laudo `tri-continuity-context` com reprodução offline de quatro variantes |
| Work item isolado e ownership | PASS | bundle próprio; toca o core, os validadores e os 8 pontos de versão |
| Feature/fix plan-only | PASS | mudança de produto só em `implement-parallel`, por worker |
| Sequência obrigatória | PASS | specify aceito; plan em andamento |
| Verify/review antes de ship | PASS | etapas pending, precedem ship |
| Fail-closed sem waiver | PASS | tomada exige prova do host; ativo, inconclusivo e não observável recusam com códigos distintos (FR-002) |
| Rastreabilidade | PASS | FR-001..FR-012 → tarefas; ADR-0001, ADR-0002; BL-0001 adiado com resolução |
| Tier de modelo do worker Orca | PASS | tier derivado do nó; nenhum modelo de fronteira como worker |
| Bump obrigatório | PASS | FR-012: 6.0.2 → 6.0.3 nos 8 pontos |
| Release por versão | PASS | publicada pelo pipeline no push para main |
| Governance | PASS | Constituição `54d5522b…` lida, sem emenda |

Re-check pós-design: sem mudança.

## Project Structure

### Documentation (this feature)

```text
specs/032-continuity-context/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── context-takeover.md
│   └── continuity-checkpoint-v2.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/scripts/grill_workspace.py            # vínculo, tomada, adopt, prepare-switch, checkpoint
plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py  # schema e validação do checkpoint
plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py   # observação de dispatch terminal (leitura)
tests/validate_agent_orchestration_contract.py                      # observação, tomada, troca e checkpoint
tests/validate_orchestrator_store_contract.py                       # transições e invariantes do store
plugin/.claude-plugin/plugin.json                                   # 6.0.3
plugin/.codex-plugin/plugin.json                                    # 6.0.3
.claude-plugin/marketplace.json                                     # 6.0.3
.agents/plugins/marketplace.json                                    # 6.0.3
tests/validate_distribution.py                                      # VERSION = 6.0.3
plugin/skills/grill-with-docs/SKILL.md                              # heading v6.0.3 e verbo novo
plugin/skills/grill-with-docs/references/session-protocol.md        # heading v6.0.3
README.md                                                           # heading v6.0.3
```

**Structure Decision**: mudanças locais nos pontos já existentes, sem módulo novo. O verbo de tomada entra ao lado dos demais verbos `gauntlet-*` do mesmo CLI, e a prova de encerramento vem do adapter existente, não de código novo de transporte.

## Complexity Tracking

Sem violações.
