# Abandono autorizado do run run-aab4cf5224dbb4cbf563ba17

Work item: feature-goal-materialization-c29d98e49a524ca8a482615d8d528dab
Feature: 025-goal-materialization
Data: 2026-08-26

## O que este documento registra

Que o run `run-aab4cf5224dbb4cbf563ba17` é **irrecuperável** e é encerrado como
`BLOCKED`. Ele **não** convergiu. Registrar convergência aqui seria falso, e é
justamente por isso que o abandono existe como estado separado.

## Estado real do run no momento do abandono

Doze nós no Execution DAG fixado. Onze foram despachados, terminaram
`TERMINAL` e convergiram em seis waves, todas `COMPLETE`:

| Wave | Nós | Tasks |
|---|---|---|
| wave-0001 | p01-a, p01-b | T001, T002 |
| wave-0002 | p02-a | T003–T007 |
| wave-0003 | p03-a, p03-b | T008–T017 |
| wave-0004 | p04-a, p04-b | T018–T023 |
| wave-0005 | p05-a | T024–T031b |
| wave-0006 | p06-a, p06-b, p06-c | T032–T038 |

O décimo segundo nó, `p06-serial` (`parallel:false`), **nunca foi despachado**.
Suas tarefas — T039 (`README.md`), T040 (`CHANGELOG.md`), T041, T042 e T043 —
foram executadas pelo leader e estão mergeadas. T039 e T040 escrevem arquivos que
não constam do grant de nó algum, e o `partition-report.json` já as declarava em
`unmapped_task_ids`; T041 e T042 só têm sentido depois do merge dos oito pontos
de versão, que nesta wave viviam em três worktrees distintos.

Todo o trabalho do run está integrado em `main` e publicado na 5.3.0
(tag `v5.3.0`, Release, marketplaces `claude` e `codex`).

## Por que é irrecuperável

Depois que `main` foi integrada — ela trouxe a ativação do work item
`fix-reconcile-scope-succession-...`, da feature 027 — todo caminho mutável do
gauntlet passou a recusar com
`IDENTITY-STALE: current activation differs from run admission`.

A causa não é a ativação deste run ter mudado: comparada campo a campo contra a
gravada antes do merge, ela é **idêntica**. A admissão inclui
`config_sha256 = hash_bytes(config_bytes)`, e `config_bytes` são os bytes
**inteiros** de `.grill/gauntlet.yaml`, arquivo que carrega as ativações de todos
os work items. Acrescentar a ativação de outro work item muda o hash e derruba
todo run vivo.

`gauntlet-wave-declare`, `gauntlet-converge` e `gauntlet-resume` recusam do mesmo
modo. Não há verbo para re-admitir um run sob nova identidade. Só
`gauntlet-status`, que é read-only, ainda responde.

Havia dois modos de forçar o fechamento como convergido, e ambos foram recusados:
restaurar os bytes do `gauntlet.yaml` ao estado admitido apenas para satisfazer o
boundary, ou declarar convergência de um nó que nunca foi despachado. Os dois
gravariam falsidade na auditoria.

## Erro de sequenciamento que levou aqui

O nó `p06-serial` devia ter sido declarado, terminado e convergido **antes** de
integrar `main`. Não foi. A causa raiz de produto está registrada em SGD-27, com
o fix provável — derivar `config_sha256` apenas da entrada de ativação do próprio
work item — e a mitigação de processo.

## Decisão

APPROVED. Encerrar o run como `BLOCKED`, sem afirmar convergência.
