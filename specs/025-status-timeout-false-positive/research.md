# Research: Falso positivo de timeout no status do workspace

Nenhum item ficou marcado `NEEDS CLARIFICATION` no Technical Context — o spec, o ADR-0001
e o PLAN-CONTEXT.md já resolvem as decisões técnicas relevantes. Este documento registra
essas decisões no formato Decision/Rationale/Alternatives para rastreabilidade, mais a
verificação de timing real exigida pelo escopo do plano.

## Decisão 1 — Escopo dos probes Git: por worktree/repositório, não por work item

**Decision**: `live()` (branch/head/dirty) é resolvido uma vez por worktree percorrido; a
lista de branches locais (`git for-each-ref --format=%(refname:short) refs/heads`) é
resolvida uma vez por repositório. Ambos os valores são passados para `item_payload()`
via os parâmetros `live_state` e `local_branches`, em vez de cada work item disparar suas
próprias chamadas `git`.

**Rationale**: o custo O(items) era a causa raiz do estouro em workspaces reais (múltiplos
work items por worktree). Escopar por worktree/repositório reduz o custo Git ao número de
worktrees, que não cresce com o número de work items — exatamente o que FR-002 exige.

**Alternatives considered**:
- Cache com TTL por processo: adiciona estado mutável e invalidação sem necessidade —
  cada invocação do `status` já é um processo curto e isolado; um cache intra-processo é
  suficiente e é o que a mudança já faz.
- Paralelizar as chamadas Git por item (threads/subprocessos concorrentes): não reduz o
  número de chamadas Git, só as sobrepõe; mantém custo binário por item e adiciona
  complexidade de concorrência sem necessidade.

## Decisão 2 — Timeout público: 5s → 30s

**Decision**: `STATUS_TIMEOUT_SECONDS = 30` em `grill_workspace.py`, usado tanto por
`status_command` quanto por `status_markdown_command`.

**Rationale**: o laudo de evidência mede 10,56s no pior caso real e 9,03s no contrafactual
isolado com os probes já escopados por worktree. 30s dá margem sobre ambos os números sem
ser tão largo a ponto de mascarar um travamento real (ADR-0001, alternativa rejeitada:
"Timeout muito acima de 30s").

**Alternatives considered**:
- Manter 5s: falsifica a própria evidência (10,56s > 5s) — rejeitado pelo spec (edge case).
- 15s: sem margem segura sobre o pior caso medido (10,56s); qualquer variância de máquina
  reintroduziria o falso positivo.
- 120s ou sem timeout: mascara travamento real por tempo excessivo antes de reportar
  `STATUS-TIMEOUT`, sem evidência que justifique a folga.

## Decisão 3 — Regressão trava o escopo, não só o valor do timeout

**Decision**: `test_live_git_state_is_resolved_once_per_worktree_not_per_item` cria dois
work items no mesmo worktree e usa `mock.patch.object(module, "live", wraps=module.live)`
para afirmar `assert_called_once_with(self.r.resolve())` — ou seja, `live()` é chamado
exatamente uma vez por worktree, independente do número de work items.

**Rationale**: um teste que só medisse tempo de execução (`elapsed < N segundos`) seria
frágil (dependente de hardware/CI) e não pegaria a regressão antes do timeout de 30s
absorvê-la de novo. Travar a contagem de chamadas ao probe é determinístico e imune a
variância de máquina — é o que FR-004/SC-003 exigem.

**Alternatives considered**:
- Assert só de tempo (`elapsed < 5s`): flaky em CI compartilhado; não reprova a
  reintrodução do custo O(items) se a máquina de CI for rápida o suficiente.
- Contar `subprocess.run` globalmente em vez de mockar `live()`: mistura probes de estado
  vivo com outras chamadas Git do módulo (ex.: leitura de metadata), perdendo
  especificidade sobre qual custo está sendo travado.

## Decisão 4 — Bump SemVer: patch (5.3.0 → 5.3.1)

**Decision**: bump PATCH, não MINOR/MAJOR.

**Rationale**: FR-005 declara que o contrato público `grill-status/v1` (schema, códigos,
formato Markdown) permanece inalterado. A mudança é correção de bug de comportamento
interno (custo de probes, valor de timeout) sem adicionar, remover ou alterar campos do
payload nem introduzir capacidade nova — critério padrão de PATCH em SemVer.

**Alternatives considered**:
- MINOR: seria correto se `STATUS_TIMEOUT_SECONDS` fosse exposto como capacidade nova
  configurável pelo consumidor; não é o caso — é constante interna do wrapper.
- MAJOR: exigiria quebra de contrato; FR-005 proíbe isso explicitamente.

## Verificação — timing real do pior caso

**Decision**: revalidar antes do ship que o workspace real de pior caso (múltiplos work
items, múltiplos worktrees) completa dentro do timeout público de 30s, medindo o tempo de
parede de `status_command`/`status_markdown_command` sobre a árvore real do repositório
(não um fixture sintético reduzido).

**Rationale**: a fixture sintética usada pelo teste de regressão de escopo prova a
propriedade estrutural (uma chamada por worktree), mas não prova sozinha que o tempo de
parede real fica dentro do timeout — isso é o que o laudo de evidência já mediu
(10,56s reais, 9,03s no contrafactual) e o que este plano exige revalidar como parte da
fase de implementação, antes do ship, para não fechar a correção só na propriedade
estrutural sem confirmar o número absoluto contra a árvore real atual (que pode ter
crescido desde a medição original).

**Alternatives considered**:
- Confiar apenas no laudo de evidência já medido: o laudo tem timestamp de 2026-08-26;
  se o workspace real acumular mais work items/worktrees entre a medição e o ship, o
  número pode mudar. Revalidar no momento do ship é barato (é a mesma chamada pública) e
  fecha essa lacuna temporal.
