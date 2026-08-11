# Analyze — consistência entre artefatos, riscos e dependências

Análise não destrutiva de `spec.md`, `plan.md` e `tasks.md` após a geração de tarefas.

## Cobertura de requisitos por tarefa

| Requisito | Tarefas | Situação |
|---|---|---|
| FR-001 detectar mudança em conteúdo distribuído | T-001, T-002 | coberto |
| FR-002 exigir aumento estrito contra a base de merge | T-001, T-002 | coberto |
| FR-003 aprovar quando não há mudança de conteúdo | T-001 | coberto |
| FR-004 mensagem nomeia as duas versões e a exigência | T-002 | coberto |
| FR-005 versão ausente ou incomparável reprova | T-001, T-002 | coberto |
| FR-006 não reimplementar coerência de distribuição | decisão de projeto | coberto por `research.md`; verificado em `checklists/acceptance.md` |
| FR-007 rodar em pull request e bloquear integração | T-004 | coberto |

Nenhum requisito órfão. Nenhuma tarefa sem requisito de origem.

## Consistência entre artefatos

- Os cinco códigos de `data-model.md#Verdict` aparecem em `contracts/cli.md` e nos aceites de T-001 e T-003. Sem divergência.
- Os quatro cenários do handoff aparecem em `spec.md` (histórias 1 a 3 mais o caso de regressão nas Edge Cases), em `checklists/acceptance.md` (CEN-1 a CEN-4) e em T-003. Sem divergência.
- `plan.md#Structure Decision` e `research.md` concordam sobre `check_version_bump.py` ficar fora do glob `validate_*.py`; T-003 e T-005 verificam isso na prática.
- `spec.md#Assumptions` fixa comparação contra a base de merge; `research.md` escolhe `git diff a...b`, que é a forma que usa base de merge. Coerente.

## Riscos

1. **Histórico raso no CI.** `actions/checkout` faz clone raso por padrão; sem `fetch-depth: 0` o commit da base de merge não existe localmente e `git show base:arquivo` falha. Mitigação em T-004, verificada em `checklists/acceptance.md#Integração de CI`. Se a mitigação falhar, o modo de falha é exit `2`, ou seja, reprovação — fail-closed, não aprovação silenciosa.
2. **Primeira pull request do próprio gate.** A pull request que introduz o gate não altera `plugin/`, então cai em `NO-PLUGIN-CHANGE` e passa. Consequência esperada, não defeito: o gate só passa a exigir bump a partir da próxima mudança de plugin.
3. **Duas pull requests concorrentes com o mesmo bump.** Ambas passam isoladamente e conflitam textualmente no merge. Já registrado como risco aceito em `PLAN-CONTEXT.md#FASE-001`; sem mitigação automática nesta fase.
4. **Branch de merge do GitHub.** Em `pull_request`, o Actions faz checkout de um merge commit efêmero, não do HEAD da branch. A base precisa vir de `github.event.pull_request.base.sha`, não de um nome de branch. T-004 precisa usar o SHA, e T-005 exercita o caminho real.

## Dependências

`T-001 → T-002 → T-004 → T-005`, com `T-003` dependendo apenas de `T-001` e podendo correr em paralelo a `T-002` e `T-004`. Nenhum ciclo. Nenhuma dependência externa ao repositório: sem rede, sem pacote de terceiros.

## Veredito

Artefatos consistentes. Nenhum bloqueio para `agent-assign`.
