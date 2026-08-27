# Implementation Plan: Falso positivo de timeout no status do workspace

**Branch**: `025-status-timeout-false-positive` | **Date**: 2026-08-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/025-status-timeout-false-positive/spec.md`

## Summary

O comando público `status` (JSON e Markdown) reportava `STATUS-TIMEOUT` falso porque
`STATUS_TIMEOUT_SECONDS` era fixo em 5s enquanto a projeção real, num workspace com
múltiplos work items espalhados por múltiplos worktrees, levava 10,56s — custo que
crescia O(items) porque cada work item disparava suas próprias chamadas `git` para
resolver estado vivo (`branch`/`head`/`dirty`) e branches locais. A correção de código
está **commitada** no baseline `7b3c3fe` (`fix(status): prevent false timeout on
accumulated workspaces`), materializado antes da partition desta feature (ADR-0001):
os probes Git passam a ser resolvidos uma vez por worktree/repositório (não por item),
e o timeout público sobe de 5s para 30s, com margem sobre os 10,56s medidos. Nada dessa
correção depende de working tree sujo — o que cada worker herda é o commit. Esta fase de
plano cobre o que falta: teste de regressão de escopo (commitado no mesmo baseline,
auditado abaixo), bump
SemVer obrigatório (patch 5.2.0 → 5.2.1), sincronização dos oito locais de distribuição,
CHANGELOG, e verificação real de timing antes do ship. O contrato `grill-status/v1`
não muda.

## Technical Context

**Language/Version**: Python ≥3.10, apenas biblioteca padrão (sem dependência externa)

**Primary Dependencies**: nenhuma (core do plugin é stdlib-only); testes usam `unittest` + `unittest.mock`

**Storage**: N/A — leitura de árvore de arquivos (`.grill/work-items/`) e chamadas `git` via `subprocess`

**Testing**: `python3 tests/run_validators.py` (glob de `validate_*.py`, 27 validadores, baseline 1303 testes); `tests/validate_status_contract.py` cobre o contrato `grill-status/v1`; `tests/validate_distribution.py` e `tests/check_version_bump.py` cobrem distribuição/bump

**Target Platform**: CLI multiplataforma (matriz CI: ubuntu/windows/macos × Python 3.10/3.13); nenhum teste pode tocar rede ou exigir `specify`/`node`/`backlogctl` reais

**Project Type**: single project — plugin CLI (`plugin/skills/grill-with-docs/scripts/`) + validadores (`tests/`)

**Performance Goals**: `status` (JSON e Markdown) completa sem `STATUS-TIMEOUT` em workspace real de pior caso (10,56s medidos); custo Git por worktree/repositório, não por work item

**Constraints**: timeout público (`STATUS_TIMEOUT_SECONDS`) MUST ser 30s — mantém margem sobre 10,56s sem cair abaixo disso e é o teto que evita mascarar travamento real; contrato `grill-status/v1` (schema, códigos, Markdown) MUST permanecer inalterado; bump SemVer obrigatório em `plugin/**` antes de merge/push (Constituição, cláusula "Bump obrigatório do plugin"); fail-closed nos dois gates de distribuição (`bump-gate.yml`, `ci.yml`) sobre o mesmo SHA de topo, exigido por FR-008/SC-006 — ver seção dedicada abaixo

**Scale/Scope**: correção cirúrgica em 2 scripts (`grill_status.py`, `grill_workspace.py`) + 1 arquivo de teste (`validate_status_contract.py`), já commitados no baseline `7b3c3fe`; escopo desta fase é bump de versão + distribuição + validação, não nova lógica

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Status | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | `.grill/evidence/grill-status-timeout-debug-report.md` prova causa raiz (10,56s real, 9,03s contrafactual com 30s) |
| Work item isolado e ownership | PASS | `fix-status-timeout-false-positive-79cd99681a234f65a93a092b678e39b3` |
| Feature/fix plan-only | PASS | Este comando é `speckit-plan`; termina em artefatos de plano, sem merge/push |
| Sequência obrigatória do desenvolvimento | PASS | specify (feito) → plan (este) → checklist → tasks → analyze → partition → implement-parallel → converge → verify → review → ship |
| Verify/review antes de ship | N/A nesta fase | Gate aplicável nas fases `verify`/`review`, não em `plan` |
| Fail-closed sem waiver | PASS | Timeout não pode cair abaixo de 10,56s; ambiguidade de escopo (FR-005) é tratada como bloqueio, não suposição; divergência entre `bump-gate.yml` e `ci.yml` bloqueia ship até ambos passarem na mesma revisão, agora normatizado como FR-008/SC-006 (ver seção dedicada) |
| Rastreabilidade | PASS | ADR-0001, triagem selada (`tri-status-timeout-false-positive.json`), PLAN-CONTEXT.md referenciam o mesmo work item; a regra fail-closed dos dois gates tem requisito próprio (FR-008/SC-006) e tarefa própria (`tasks.md` T020/T022), sem regra órfã de plano |
| Tier de modelo e esforço do worker Orca | N/A nesta fase | Não há despacho de worker Orca neste comando |
| Bump obrigatório do plugin | PASS (planejado) | Este plano declara o bump patch 5.2.0 → 5.2.1 e os 8 locais como tarefa obrigatória da fase de implementação |
| Release obrigatória por versão | N/A nesta fase | Aplicável ao pipeline `publish.yml` no merge para `main`, fora do escopo de `plan` |

Nenhuma violação sem justificativa. Complexity Tracking não se aplica.

## Fail-Closed: `bump-gate.yml` × `ci.yml`

Os dois workflows avaliam a mesma PR por ângulos diferentes (bump de versão vs. matriz de
portabilidade) e podem divergir ou falhar independentemente. **Regra fail-closed**: falha
ou divergência de veredito em qualquer um dos dois — `bump-gate.yml` (`check_version_bump.py`)
ou `ci.yml` (`tests/run_validators.py` na matriz) — bloqueia o ship até que **ambos** passem
verde na **mesma revisão** (mesmo SHA de topo da PR). Não há waiver: uma re-execução verde
de um gate após nova alteração invalida qualquer aprovação anterior do outro gate para
aquele SHA, exigindo que os dois sejam reavaliados juntos antes de liberar. Isso fecha a
lacuna de CHK025: sem essa regra, um gate poderia aprovar uma árvore que o outro reprovaria,
e nada no plano determinava qual veredito prevalecia. A regra deixou de ser só de plano:
está normatizada em `spec.md` como **FR-008** (regra) e **SC-006** (critério mensurável).

**Estado pré-bump: `MISSING-BUMP`.** `check_version_bump.py` decide sobre *blobs commitados*
(`git diff --no-renames --name-only base...head` e `git show <rev>:plugin/.claude-plugin/plugin.json`).
Como o baseline `7b3c3fe` já alterou `plugin/**` **sem** bump, o veredito **atual** do gate
nesta branch é literalmente `MISSING-BUMP`, com `verdict: FAIL`, `base_version: "5.2.0"` e
`head_version: "5.2.0"`. Esse é o ponto de partida real desta feature — o gate já reprova, e a
tarefa de bump existe para virá-lo. `NO-PLUGIN-CHANGE` permanece enumerado apenas como
**código residual rejeitado**: descreve a árvore hipotética em que `plugin/**` não mudou no SHA
avaliado, o que deixou de ser possível a partir de `7b3c3fe`; se aparecer, é sinal de
`--base-ref`/HEAD errados e é **falha**, nunca aprovação. O único veredito aceito é literalmente
`BUMPED`, lido do campo `code` de `check_version_bump.py --json`.

**Mesmo estado de árvore.** A confirmação local dos dois gates exige o mesmo `git rev-parse HEAD`
antes e depois das duas execuções, sobre árvore **tracked-limpa**. Sem isso, a igualdade de SHA
entre as rodadas não significa igualdade de árvore avaliada, e a verificação não prova o que FR-008
pede.

**Topologia real do gauntlet: barreira entre Phase 6 e Phase 7 (N1-A).** As tarefas de bump
(`tasks.md` T010–T018) formam a **Phase 6**: file-disjuntas, `[P]`, despachadas em worktrees de
worker distintos. As tarefas de gate (T019–T022) formam a **Phase 7**, e a fronteira entre as duas
fases **é** a barreira de convergência — a Phase 7 só é despachada quando **todos** os nós de bump
mergearem no HEAD do coordenador. Gate sobre árvore parcialmente bumpada avalia uma versão que não
existe.

**Um nó único de gate.** T019–T022 não se distribuem entre workers: as quatro rodam no **mesmo nó**,
num worktree **isolado de gate** criado a partir do HEAD do coordenador depois dessa convergência.
Para que o particionador as mantenha no mesmo *conflict component*, cada uma declara os **três
inputs comuns** `tests/validate_distribution.py`, `tests/check_version_bump.py` e
`tests/run_validators.py`, e **nenhuma leva `[P]`**. Dentro desse nó **não há commit nem merge** entre
T019 e T022: o HEAD é imóvel por construção, e é por isso que a igualdade de `git rev-parse HEAD`
exigida por T022 é uma invariante verificável em vez de uma coincidência a torcer.

**Limpeza é tracked-only (N1-B).** A pré-condição verificável é
`git status --porcelain --untracked-files=no` **vazio**: nenhuma modificação, adição ou remoção
pendente de path **versionado**. Scratch não versionado do próprio nó — sidecar de reconciliação,
arquivos de controle do gauntlet, saídas de execução — **não entra no gate**: `check_version_bump.py`
decide sobre blobs commitados e `validate_distribution.py`/`run_validators.py` leem paths
versionados. Untracked, portanto, não é achado, não suja a checagem e **não funciona como waiver** da
exigência tracked-vazio. Estado alheio do workspace principal (`.specify/feature.json` modificado,
bundles não versionados de work items irmãos, atestações não commitadas) tampouco participa: ele não
existe no worktree isolado de gate.

**Reconciliação é posterior aos gates.** `gauntlet-tasks-reconcile` ocorre **somente depois** da
convergência do nó de gate, nunca antes de T019. Não existe obrigação de commitar `state.json` ou
`tasks.md` antes dos gates — fazê-lo moveria o HEAD dentro da janela avaliada e quebraria a
invariante do parágrafo anterior.

**Obrigação do leader antes de despachar.** Para que todo worker parta da mesma árvore: (a) o leader
**commita os artefatos relacionados** desta feature — `specs/025-status-timeout-false-positive/`, o
bundle do work item `fix-status-timeout-false-positive-79cd99681a234f65a93a092b678e39b3` e as
atestações das etapas já fechadas — **antes da partition**; (b) o leader commita o **Execution DAG e
o relatório de partition antes do primeiro worker** ser despachado. Worker despachado sobre base que
ainda não contém esses artefatos herda árvore divergente, e a igualdade de árvore avaliada pelo nó de
gate deixa de significar o que FR-008 pede.

## Project Structure

### Documentation (this feature)

```text
specs/025-status-timeout-false-positive/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
│   └── grill-status-v1.md
├── checklists/           # /speckit-checklist output
│   ├── release.md        # unit tests dos requisitos — 37/37, nenhum item aberto
│   └── requirements.md   # checklist de requisitos — nenhum item aberto
├── analysis.md           # /speckit-analyze, 1ª rodada — SUPERSEDED, preservada como histórico
├── analysis-final.md     # /speckit-analyze — relatório final vigente (a emitir; substitui analysis.md)
└── tasks.md              # Phase 2 output (/speckit-tasks — NOT created here)
```

**Artefato gerado, fora do produto**: `.specify/feature.json` aparece modificado no working
tree (`specs/026-attestation-emitter` → `specs/025-status-timeout-false-positive`). Ele é
**estado de seleção da feature ativa**, escrito pelos scripts do Spec Kit
(`setup-plan.sh`/`check-prerequisites.sh`), não superfície de produto nem de distribuição:
não está entre os 8 locais travados por `tests/validate_distribution.py`, não entra em
`plugin/**` e portanto não dispara o gate de bump. Nenhuma tarefa desta feature o edita à
mão; ele é contabilizado aqui apenas para que sua presença no diff não seja lida como escopo
não declarado (finding S1 do `analysis.md`).

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/scripts/
├── grill_status.py       # build_status(): probes Git escopados por worktree/repositório (commitado em 7b3c3fe)
└── grill_workspace.py    # status_command / status_markdown_command: STATUS_TIMEOUT_SECONDS=30 (commitado em 7b3c3fe)

tests/
├── validate_status_contract.py   # contrato grill-status/v1 + regressão de escopo por worktree (commitado em 7b3c3fe)
├── validate_distribution.py      # trava os 8 locais de distribuição + constante VERSION
└── check_version_bump.py         # gate de bump SemVer (bump-gate.yml)

# 8 locais de distribuição a sincronizar no bump patch 5.2.0 → 5.2.1:
plugin/.claude-plugin/plugin.json
plugin/.codex-plugin/plugin.json
.claude-plugin/marketplace.json
.agents/plugins/marketplace.json
tests/validate_distribution.py            # constante VERSION
plugin/skills/grill-with-docs/SKILL.md              # heading "# Grill with Docs vX.Y.Z"
plugin/skills/grill-with-docs/references/session-protocol.md  # heading "# Protocolo de sessão vX.Y.Z"
README.md                                  # heading "**vX.Y.Z"

CHANGELOG.md   # nova entrada ## 5.2.1
```

**Structure Decision**: Single project já existente. Nenhuma estrutura nova. A fase de
implementação subsequente toca os 8 locais de distribuição, o `CHANGELOG.md` e — para fechar
FR-007 com gate real em vez de conferência humana — estende `tests/validate_distribution.py`
com a asserção de heading `## {VERSION}` no `CHANGELOG.md` (mesmo arquivo do bump da constante
`VERSION`, portanto sem novo local a sincronizar). A lógica de correção (`grill_status.py`,
`grill_workspace.py`, `validate_status_contract.py`) já está **commitada** no baseline `7b3c3fe`
e é preservada byte a byte por este plano — nenhuma tarefa a reescreve; T002–T009 apenas a
auditam.

## Complexity Tracking

*Não se aplica — nenhuma violação da Constitution Check.*
