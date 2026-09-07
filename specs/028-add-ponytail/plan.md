# Implementation Plan: Ponytail na stack oficial

**Branch**: `cadugevaerd/chore-add-ponytail` | **Date**: 2026-09-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/028-add-ponytail/spec.md`; HOW selado no work item `feature-add-ponytail-d8c0bd7e8ffd4442a806b2e1067ed06c` (`PLAN-CONTEXT.md`, ADR-0001..ADR-0004).

## Summary

Declarar o plugin ponytail como dependência obrigatória do preflight, com um kind novo `harness-plugin` cuja detecção lê apenas o registro de plugins em disco do harness ativo (Claude Code: `installed_plugins.json`; Codex: cache `plugins/cache/<marketplace>/<plugin>/<versão>/`), sem subprocesso; a remediação e a instalação delegada (`--allow-install`) executam, pela CLI do próprio harness, `marketplace add` + `install`/`add`, declaradas por runtime no manifesto. Este repositório documenta o ponytail em `CLAUDE.md`, ganha `AGENTS.md` e `.claude/settings.json` versionado; o plugin sobe para 5.4.0.

## Technical Context

**Language/Version**: Python >= 3.10, somente biblioteca padrão (`json`, `pathlib`, `os`)

**Primary Dependencies**: nenhuma nova; `ensure_dependencies.py` (detector), `dependencies.json` (manifesto), `Toolchain` (seam de ambiente e subprocesso)

**Storage**: leitura de arquivos do usuário: `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/installed_plugins.json`; `${CODEX_HOME:-$HOME/.codex}/plugins/cache/ponytail/ponytail/<versão>/.codex-plugin/plugin.json`

**Testing**: `python3 tests/run_validators.py` (unittest, glob `validate_*.py`); casos novos em `tests/validate_dependencies_contract.py` com `StubToolchain` e `HOME` temporário

**Target Platform**: Linux, macOS, Windows (matriz de CI: 3 SOs × Python 3.10/3.13), sem rede, sem `claude`/`codex` instalados

**Project Type**: plugin/CLI (scripts do skill grill-with-docs)

**Performance Goals**: detecção sem subprocesso; custo de I/O = 1 leitura de JSON (Claude) ou 1 `iterdir` + 1 leitura de JSON (Codex)

**Constraints**: core nunca baixa bytes; instalação só sob `--allow-install` via `tools.run` com `INSTALL_TIMEOUT`; hooks read-only inalterados; kinds existentes byte-idênticos em comportamento e relatório; bump SemVer minor obrigatório nos oito pontos de `validate_distribution.py`

**Scale/Scope**: 1 entrada nova no manifesto, 1 kind novo, ~60 linhas no detector, ~8 casos de teste, 6 arquivos de documentação/configuração, 8 pontos de versão

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Estado | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | Caminhos de registro e CLIs verificados em sessão (ADR-0003, ADR-0004); research.md cita fonte por decisão |
| Work item isolado e ownership | PASS | Tudo sob `feature-add-ponytail-d8c0bd7e8ffd4442a806b2e1067ed06c`, branch `cadugevaerd/chore-add-ponytail` |
| Feature/fix plan-only | PASS | Este plano é artefato da etapa `plan` do ciclo executor; o PLAN_ONLY_STOP da entrevista já foi atravessado por ato humano (`/goal`) |
| Sequência obrigatória do desenvolvimento | PASS | `specify` atestada e selada (`.grill/attestations/028-specify.json`); `plan` em andamento |
| Verify/review antes de ship | PASS | Sem ship neste plano; ordem canônica mantida |
| Fail-closed sem waiver | PASS | Registro ilegível → `undetermined`, nunca `missing`; `--require-dependencies` recusa; sem gate novo nem escape |
| Rastreabilidade | PASS | FR-001..FR-015 ↔ US1..US3 ↔ ADR-0001..0004; cada tarefa citará FR |
| Tier de modelo e esforço do worker Orca | NOT-APPLICABLE ainda | Sem worker até `implement-parallel`; lá o modelo é derivado do binding versionado |
| Bump obrigatório do plugin | PASS | 5.3.4 → 5.4.0 em oito pontos (FR-015) |
| Release obrigatória por versão | PASS | Release é do pipeline no merge; nenhuma tag manual |
| Governance | PASS | Constituição, `WORKFLOW.md` e registry não são tocados |

Sem violações → Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/028-add-ponytail/
├── plan.md              # este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── dependency-manifest-entry.md   # forma da entrada harness-plugin no manifesto
│   └── dependency-report.md           # forma do relatório por dependência e do resultado de instalação
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/
├── assets/dependencies.json                 # + entrada "ponytail" (kind harness-plugin)
├── scripts/ensure_dependencies.py           # + KINDS, plugin_registry_state(), declared_install(), ramo em detect()
├── SKILL.md                                 # § Dependências e backlog: menção ao ponytail e ao limite Codex
└── references/session-protocol.md           # heading de versão (bump)
plugin/.claude-plugin/plugin.json            # bump
plugin/.codex-plugin/plugin.json             # bump
.claude-plugin/marketplace.json              # bump
.agents/plugins/marketplace.json             # bump
tests/
├── validate_dependencies_contract.py        # + casos harness-plugin por runtime, install por runtime, manifest shape
└── validate_distribution.py                 # VERSION = "5.4.0"
README.md                                    # heading de versão + menção ao ponytail
CHANGELOG.md                                 # entrada 5.4.0
CLAUDE.md                                    # + seção "Ponytail na stack"
AGENTS.md                                    # novo (Codex)
.claude/settings.json                        # novo: enabledPlugins ponytail@ponytail
```

**Structure Decision**: mudança pontual no plugin existente; nenhum módulo novo. Detecção e instalação vivem no mesmo arquivo que já detecta e instala as demais dependências, porque a seam `Toolchain` e o laço de `install()` já existem lá.

## Design

### Manifesto

Entrada nova, ver [contracts/dependency-manifest-entry.md](contracts/dependency-manifest-entry.md). Campos: `id`, `kind: harness-plugin`, `required: true`, `plugin`, `marketplace`, `min: 4.9.0`, `owner`, `reason`, `install_by_runtime`. O campo `install` (lista única) permanece para os kinds existentes; `install_by_runtime` é dicionário `runtime → lista de argv`, e `load_manifest` valida a forma dos dois.

### Detector

- `KINDS` ganha `"harness-plugin"`.
- `plugin_registry_state(entry, tools, runtime) -> (status, version, source, reason)`:
  - `claude`: raiz `tools.environ["CLAUDE_CONFIG_DIR"]` ou `HOME/.claude`; lê `plugins/installed_plugins.json`; chave `plugins["<plugin>@<marketplace>"]`, lista cujo primeiro item traz `version`. Arquivo ausente ou chave ausente → `missing`; JSON inválido ou forma inesperada → `undetermined`.
  - `codex`: raiz `tools.environ["CODEX_HOME"]` ou `HOME/.codex`; diretório `plugins/cache/<marketplace>/<plugin>/`; entre os subdiretórios que contêm `.codex-plugin/plugin.json`, escolhe a maior versão por `parse_version`; versão lida do `plugin.json` (fallback: nome do diretório). Diretório ausente → `missing`; `plugin.json` ilegível → `undetermined`.
  - `present` se `meets(found, min)`, senão `outdated`; `source` = caminho lido.
- Ramo em `detect()`: preenche `status`, `version`, `source`; o pós-processamento existente já anexa `remediation`/`reason` quando `status != present` e trata `undetermined`.
- `declared_install(entry, runtime)`: retorna `entry["install_by_runtime"][runtime]` quando existe, senão `entry.get("install") or []`. `remediation()` e `install()` passam a usar o helper; nenhum outro comportamento muda.

### Instalação delegada

Sequência por runtime (ADR-0004): Claude `["claude","plugin","marketplace","add","DietrichGebert/ponytail"]` → `["claude","plugin","install","ponytail@ponytail"]`; Codex `["codex","plugin","marketplace","add","DietrichGebert/ponytail"]` → `["codex","plugin","add","ponytail@ponytail"]`. Executadas por `tools.run` na ordem; falha interrompe e reporta `FAILED` com o argv (contrato já existente em `install()`).

### Documentação e configuração deste repositório

- `CLAUDE.md`: seção "Ponytail na stack" — o que é, o que o preflight verifica (instalado + versão mínima, não "habilitado"), comandos por harness, dependência de `node` para os hooks.
- `AGENTS.md`: mesmo conteúdo essencial + o texto de modo do ponytail (fonte: `AGENTS.md` do plugin 4.9.0, MIT).
- `.claude/settings.json`: `{"enabledPlugins": {"ponytail@ponytail": true}}`.
- `SKILL.md` § Dependências e backlog e `README.md`: uma frase cada declarando o ponytail e o limite do Codex.

### Bump

`5.3.4 → 5.4.0` nos oito pontos de `CLAUDE.md#Distribuição`; `CHANGELOG.md` com entrada `## 5.4.0`.

## Constitution Check (pós-design)

Sem alteração: nenhuma cláusula é tocada pelo design; `undetermined` fail-closed preserva "Fail-closed sem waiver"; a confiança no marketplace fica explícita no manifesto (Evidência antes de afirmação, Rastreabilidade).

## Complexity Tracking

Sem violações.
