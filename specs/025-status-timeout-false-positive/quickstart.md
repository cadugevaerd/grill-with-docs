# Quickstart: validar a correção do falso positivo de STATUS-TIMEOUT

## Pré-requisitos

- Python ≥3.10 (sem dependência externa)
- Git disponível no `PATH`
- Branch `025-status-timeout-false-positive` no baseline commitado `7b3c3fe`
  (`fix(status): prevent false timeout on accumulated workspaces`), que já detém
  `grill_status.py`, `grill_workspace.py` e `validate_status_contract.py` com a correção.
  As mudanças **não** vivem em working tree sujo — são blobs commitados, e é isso que os
  passos abaixo leem.
- Os passos 4 e 6 (gates) rodam **no nó único de gate da Phase 7** — um worktree isolado criado a
  partir do HEAD do coordenador **depois** que todos os nós de bump da Phase 6 (T010–T018)
  convergiram. As quatro tarefas de gate compartilham esse mesmo worktree e **não** há commit nem
  merge entre elas, então o HEAD não se move da primeira à última. A pré-condição de limpeza é
  **somente tracked**: `git status --porcelain --untracked-files=no` vazio; scratch não versionado do
  próprio nó (sidecar de reconciliação, arquivos de controle) não participa e não é waiver.
  `gauntlet-tasks-reconcile` roda **depois** da convergência desse nó, nunca antes do passo 4. Os
  passos 1–3 podem rodar em qualquer checkout dessa branch.

## 1. Suíte completa de validadores

```bash
python3 tests/run_validators.py
```

**Esperado**: exit 0, todos os validadores passam, incluindo `validate_status_contract.py`
com o novo teste `test_live_git_state_is_resolved_once_per_worktree_not_per_item`. Nenhum
teste deve tocar rede nem exigir `specify`/`node`/`backlogctl` reais (ver `CLAUDE.md`).

## 2. Contrato de status isolado

```bash
python3 -m unittest tests.validate_status_contract -v
```

**Esperado**: todos os casos passam, incluindo os que cobrem `STATUS-TIMEOUT`,
`WORK-ITEM-MISSING`, o schema `grill-status/v1` e a regressão de escopo por worktree.

## 3. Timing real do pior caso (contra a árvore real do repositório, não fixture)

O subcomando `status` tem um argumento posicional **obrigatório** `root` (o caminho do
workspace). Rode a partir da raiz do repositório, passando `.` como root, e **uma medição de
cada vez** — as duas chamadas concorrentes disputariam CPU e I/O de disco e contaminariam a
grandeza medida (tempo de parede):

```bash
# serial, nunca em paralelo: a segunda só começa depois de a primeira terminar
time python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py status .
time python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py status . --format markdown
```

**Esperado**:
- Nenhuma das duas chamadas retorna `STATUS-TIMEOUT`.
- Tempo de parede consistente com o pior caso medido no laudo de evidência
  (`.grill/evidence/grill-status-timeout-debug-report.md`: 10,56s real / 9,03s
  contrafactual), com margem confortável sob o timeout público de 30s.

Se o tempo se aproximar de 30s, revalidar antes do ship — pode indicar crescimento do
workspace desde a medição original (ver `research.md`, seção "Verificação — timing real
do pior caso").

## 4. Distribuição (8 locais) após o bump

**Pré-condição**: o bump precisa estar **commitado e convergido** — todos os nós da Phase 6
mergeados no HEAD do coordenador —, e este passo roda no **nó único de gate da Phase 7**, worktree
isolado criado desse HEAD. A limpeza exigida é **tracked-only**:
`git status --porcelain --untracked-files=no` vazio. Untracked do próprio nó (sidecar de
reconciliação, controle do gauntlet, saídas de execução) **não entra no gate** e **não** é waiver;
estado alheio do workspace principal (`.specify/feature.json`, bundles de work items irmãos,
atestações não commitadas) não existe nesse worktree. Nada de `state.json`/`tasks.md` commitados
antes deste passo: `gauntlet-tasks-reconcile` é posterior à convergência do nó.

`check_version_bump.py` decide sobre blobs commitados (`git diff base...head` e
`git show <rev>:plugin/.claude-plugin/plugin.json`). O baseline `7b3c3fe` já alterou `plugin/**`
sem bump, então o veredito **atual**, antes do bump, é `MISSING-BUMP` com `verdict: FAIL`
(`base_version` e `head_version` ambos `5.2.0`) — é esse estado que as tarefas de bump precisam
virar. `NO-PLUGIN-CHANGE` permanece só como **código residual rejeitado**: descreve a árvore em
que `plugin/**` não mudou no SHA avaliado, impossível a partir de `7b3c3fe`; se aparecer, é
`--base-ref`/HEAD errados, e é falha.

```bash
git status --porcelain --untracked-files=no   # precisa sair vazio: nada tracked pendente
python3 tests/validate_distribution.py
python3 tests/check_version_bump.py --base-ref main --json
```

**Esperado**: `distribution: OK` — incluindo a asserção do heading `## 5.2.1` em
`CHANGELOG.md`. E o gate de bump reportando **literalmente** `"code":"BUMPED"` no JSON
(`5.2.0` → `5.2.1`). Qualquer outro código é falha: `MISSING-BUMP` significa que o bump não
entrou no SHA avaliado; `NO-PLUGIN-CHANGE` significa base/HEAD errados. Os 8 locais listados em
`data-model.md` ("Versão do plugin") devem conter `5.2.1` de forma consistente.

## 5. CHANGELOG

A entrada `## 5.2.1` em `CHANGELOG.md` descreve a correção (falso positivo de timeout, escopo
dos probes por worktree, bump obrigatório), seguindo o mesmo formato de prosa das entradas
anteriores. A **existência** da entrada não depende de conferência humana: `validate_distribution.py`
exige exatamente uma linha `## 5.2.1`, casando a constante `VERSION`, e reprova a ausência
(passo 4). A leitura manual serve só para julgar a qualidade da prosa.

## 6. Gates fail-closed sobre o mesmo SHA (FR-008/SC-006)

Ainda no **mesmo nó de gate** do passo 4, sem commit e sem merge desde então — o HEAD não se moveu
entre os dois passos, e é essa invariante que a leitura dupla abaixo verifica.

```bash
git rev-parse HEAD                            # registrar o SHA
git status --porcelain --untracked-files=no   # precisa sair vazio (tracked-only)
python3 tests/check_version_bump.py --base-ref main --json
python3 tests/run_validators.py
git rev-parse HEAD                            # precisa ser o MESMO SHA da primeira leitura
```

**Esperado**: `"code":"BUMPED"` e exit 0 na suíte, ambos sobre o mesmo SHA e a mesma árvore
tracked-limpa do nó de gate. SHA divergente significa que algo commitou dentro da janela avaliada e
invalida as duas execuções, que são refeitas juntas sobre o novo SHA. Untracked scratch do nó não
invalida nada e não é waiver de nada — ele simplesmente não é avaliado. Rodar isso fora do nó de gate
é erro de execução, não motivo de waiver. A confirmação local não substitui `bump-gate.yml` e
`ci.yml` verdes na mesma revisão de topo da PR real.

## Critério de aceite (mapeado ao spec)

| Critério | Comando de verificação |
|---|---|
| SC-001 (sem falso bloqueio) | Passo 3 — nenhum `STATUS-TIMEOUT` |
| SC-002 (custo não escala por item) | Passo 2 — `test_live_git_state_is_resolved_once_per_worktree_not_per_item` |
| SC-003 (suíte completa passa) | Passo 1 |
| SC-004 (versão/distribuição coerentes) | Passo 4 — `distribution: OK` nos 8 locais |
| SC-005 (entrada de CHANGELOG antes do ship) | Passo 4 (gate: heading `## 5.2.1`) + Passo 5 |
| SC-006 (ambos os gates verdes no mesmo SHA) | Passo 6 — `BUMPED` + suíte exit 0, mesmo HEAD |
