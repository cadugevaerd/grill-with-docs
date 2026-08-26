# Analyze — 027 sucessão explícita de escopo reconciliado

Análise cruzada read-only de `spec.md`, `plan.md` e `tasks.md` contra a
Constituição v2.1.0 (`54d5522b…5667569`). Executada após `tasks`, antes de
`partition`.

**Baseline**: `origin/main` v5.2.0, commit `f13c18ea487cdf0fe3ec070861cf799f8f49ceaf`.

## Veredito

**Sem CRITICAL. Sem HIGH.** 5 MEDIUM e 2 LOW. Cinco findings foram remediados
nesta mesma etapa, por decisão humana explícita; dois ficam registrados sem ação,
com a razão.

## Findings

| ID | Categoria | Severidade | Local | Resumo | Estado |
|----|-----------|------------|-------|--------|--------|
| F1 | Inconsistency | MEDIUM | spec §Edge Cases · contracts §C-007 | O spec afirmava que o par mutuamente declarado é barrado "por ciclo". Só a reconciliação **completa** detecta ciclo. Na targeted a aresta recíproca é invisível: o recibo não preserva `depends-on-work`. O par é barrado, mas por outro mecanismo — o antecessor teria colhido `DEPENDENCY-NOT-RECONCILED` na vez dele | **Remediado** |
| F2 | Underspecification | MEDIUM | tasks T011 · plan §Project Structure · WORK-ITEM.json §scope | T011 nomeia `.grill/work-items/<id>/AUDIT.md`, ausente da árvore do plan. É o gatilho deliberado de `deferred_to_leader`, mas não estava declarado | **Remediado** |
| F3 | Ambiguity | MEDIUM | spec §FR-009, §SC-003 | "atomicidade e idempotência **atuais**" e "inalteradas em relação ao comportamento **atual**" referenciavam baseline não fixado, deixando SC-003 não verificável | **Remediado** |
| F4 | Inconsistency | MEDIUM | spec §FR-006 · contracts §C-007 | FR-006 dizia "dependência não satisfeita" no singular, colapsando `DEPENDENCY-MISSING` (completo) e `DEPENDENCY-NOT-RECONCILED` (targeted) — códigos e caminhos distintos | **Remediado** |
| F5 | Coverage Gap | MEDIUM | spec §SC-006 · tasks | SC-006 ("verificação automatizada completa termina sem falhas") não tem task. Aparece só como linha de *Checkpoint*, que o `partition` não lê como tarefa | **Registrado** |
| F6 | Ambiguity | LOW | quickstart §4–§5 | §4 terminava em `rm -rf "$WS"` e §5 usava `$WS` depois disso | **Remediado** |
| F7 | Coverage Gap | LOW | spec §FR-007 · tasks T006 | FR-007 (conflito ADR independente) tem apenas task de teste, sem task de implementação | **Registrado** |

### Por que F5 e F7 ficam sem ação

**F5.** SC-006 é gate de `verify`, não trabalho construível. A suíte já existe e
passa; o critério afirma que ela continua passando, e quem afirma isso é a etapa
`verify` invocada, não uma tarefa de `implement-parallel`. Criar uma task
"rodar a suíte" colocaria no worker uma verificação que pertence ao leader e
produziria evidência de qualidade inferior à do gate. O que falta é o spec dizer
que SC-006 é gate — dívida de redação, registrada, sem efeito na execução.

**F7.** É requisito de **preservação**: FR-007 exige que o conflito ADR continue
independente. Preservação não tem task de implementação por definição — a
implementação correta é não tocar naquele laço. A cobertura certa é o teste, e
T006 a tem. Informativo.

## Cobertura

| Requisito | Task? | Task IDs |
|---|---|---|
| FR-001 | sim | T003, T004 |
| FR-002 | sim | T002, T004 |
| FR-003 | sim | T001, T005 |
| FR-004 | sim | T002, T005 |
| FR-005 | sim | T002, T005 |
| FR-006 | sim | T003, T006 |
| FR-007 | sim | T006 (só teste — F7) |
| FR-008 | sim | T001 |
| FR-009 | sim | T007 |
| FR-010 | sim | T007 |
| FR-011 | sim | T008, T009, T010, T011 |
| FR-012 | sim | T005 |
| SC-001 | sim | T004 |
| SC-002 | sim | T005 |
| SC-003 | sim | T006 |
| SC-004 | sim | T007 |
| SC-005 | sim | T008–T011 |
| SC-006 | **não** | — (F5, gate de verify) |

## Alinhamento constitucional

Nenhuma violação. As dez cláusulas foram avaliadas contra os três artefatos.

A mais exposta é *Bump obrigatório do plugin*: `plugin/**` muda, logo o bump
5.2.0 → 5.2.1 é obrigatório nos oito pontos, e T008–T011 o cobrem com
`tests/validate_distribution.py` como gate. *Fail-closed sem waiver* é a cláusula
que o próprio trabalho poderia ferir, e é por isso que FR-012 exige casos
negativos dedicados: a correção destrava um caso sem virar dispensa geral.

## Tarefas sem requisito

Nenhuma. As 11 tarefas mapeiam para pelo menos um FR.

## Métricas

| Métrica | Valor |
|---|---|
| Requisitos | 18 (12 FR + 6 SC) |
| Tarefas | 11 |
| Cobertura | 17/18 = 94% (FR 100%, SC 83%) |
| Ambiguidades | 2 (F3, F6) — ambas remediadas |
| Duplicações | 0 |
| Violações constitucionais | 0 |
| CRITICAL / HIGH / MEDIUM / LOW | 0 / 0 / 5 / 2 |

## Cascata de re-atestação

A remediação alterou `spec.md`, `plan.md` e `tasks.md`, todos já selados. Foi
emitida cadeia sucessora explícita, na ordem da sequência, cada elo nomeando o
que substitui:

| Etapa | Round | Razão |
|---|---|---|
| specify | 2 | F1, F3, F4 |
| plan | 2 | F2 |
| checklist | 2 | re-selagem por cascata; conteúdo inalterado |
| tasks | 2 | F1, F4 em T006 |

`chain_stale` fechou vazio. O recibo anterior de cada etapa permanece legível;
nenhum foi contradito por bytes que não casam com ele.

## Próxima ação

Prosseguir para `partition`. O `tasks.md` foi conferido contra o parser real do
particionador: 11 tarefas mapeadas, nenhuma não-mapeada, T011 devolvida em
`deferred_to_leader`, e a Phase 2 com quatro grupos de conflito disjuntos.
