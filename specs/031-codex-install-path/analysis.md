# Specification Analysis Report — 031 observar a instalação Codex

**Date**: 2026-09-19 · **Inputs**: spec.md (r3), plan.md (r2), tasks.md, research.md, data-model.md, contracts/, quickstart.md, `.specify/memory/constitution.md` · **Partition preview**: `partition-emit --groups 3` (read-only): 5 nós, 2 fases, T008 em `deferred_to_leader`, `unmapped_task_ids` vazio

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| U1 | Underspecification | MEDIUM | spec.md FR-009; tasks.md T002 | "Separador de diretório" não diz se a contrabarra conta em POSIX. Um `version` com contrabarra passaria no Linux e mudaria de sentido no Windows (matriz CI tem os três SOs). | No T002, recusar os dois separadores (barra e contrabarra) em qualquer SO, não só `os.sep`; cobrir no T003. Não exige mudança de spec: FR-009 já pede "nomes simples". |
| C1 | Coverage | LOW | spec.md FR-006; tasks.md T002 | Nenhum teste automatizado prova a ausência de subprocesso ou rede na decisão. | Aceitar pela revisão do diff (verify/review); o observer continua recebendo a listagem já lida do transcript. |
| U2 | Underspecification | LOW | tasks.md T003 | O caso de conteúdo divergente (US2-S3) precisa atravessar a avaliação de apresentação, não só o observer, para chegar a `STYLE-CONTENT-INCOMPATIBLE`. | Usar no T003 o mesmo caminho dos testes existentes de apresentação (`approved_presentation_reference` via a avaliação completa), com a política aprovada. |
| I1 | Inconsistency | LOW | partition preview p02-a | O nó de T003 recebe grant de escrita na fixture criada por T001, porque a linha de T003 nomeia o caminho; T003 só lê. | Aceitar: é efeito léxico conhecido do partition 5.4.1 e o grant extra não conflita (fases diferentes). |
| E1 | Coverage | LOW | spec.md Edge Cases (versão diferente da aprovada) | Sem tarefa própria. | Correto por escopo: a política de compatibilidade não muda; o caso já é coberto pelos testes existentes de apresentação. |

Nenhum achado CRITICAL ou HIGH.

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | Sim | T002, T003 | US1 |
| FR-002 | Sim | T002, T003 | US2-S1..S4 |
| FR-003 | Sim | T002, T003 | T003 usa `CODEX_HOME` temporário |
| FR-004 | Sim | T002, T003 | inclui `installPath` relativo sem fallback |
| FR-005 | Sim | T002, T003 | casos Claude existentes + caso novo |
| FR-006 | Sim | T002 | sem teste automatizado (C1) |
| FR-007 | Sim | T001, T003 | fixture real 0.154.0 |
| FR-008 | Sim | T004, T005, T006, T007, T008 | oito pontos: 4 manifests + VERSION + 2 headings em `plugin/` + README |
| FR-009 | Sim | T002, T003 | ver U1 |
| SC-001..SC-003 | Sim | T003 | |
| SC-004 | Sim | T008 | suíte completa |
| SC-005 | — | — | fora do aceite desta entrega, por definição |

## Constitution Alignment

Sem conflitos. Bump obrigatório coberto pelos oito pontos (FR-008); release pelo pipeline no push para main; tier do worker derivado pelo binding; fail-closed preservado (FR-002, FR-004, FR-009); rastreabilidade FR→tarefa completa.

## Unmapped Tasks

Nenhuma.

## Metrics

- Total Requirements: 9 FR + 5 SC
- Total Tasks: 8 (7 despacháveis, 1 do leader)
- Coverage: 100% dos FR com ≥1 tarefa
- Ambiguity Count: 1 (U1)
- Duplication Count: 0
- Critical Issues Count: 0

## Next Actions

Somente MEDIUM/LOW: seguir para `partition`. U1 e U2 entram como instrução explícita no payload dos workers de T002 e T003 (aplicáveis sem mudar spec, plan ou tasks).
