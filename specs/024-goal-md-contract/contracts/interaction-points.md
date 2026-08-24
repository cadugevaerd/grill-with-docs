# Fontes dos pontos de interação (T001)

Levantamento par ponto → fonte para as duas tabelas de
`specs/024-goal-md-contract/data-model.md` §Ponto de interação. Fontes
permitidas por T001: código de recusa em `plugin/skills/grill-with-docs/scripts/`
(arquivo + linha), cláusula em `.specify/memory/constitution.md` (heading exato)
ou seção de `WORKFLOW.md` (heading exato). Quando a fonte declarada em
data-model.md não cai em nenhuma das três categorias, ou não existe no
repositório, isso está registrado como achado — nunca inventado.

---

## Trilha `pre-ciclo`

| id | fonte verificada | observação |
|---|---|---|
| `HOLD-PRE-01` | **Não verificável nas três categorias.** Texto real em `plugin/skills/grill-with-docs/SKILL.md:156` ("Faça exatamente uma pergunta atômica...") e `plugin/skills/grill-with-docs/references/session-protocol.md:79`. | ACHADO: `data-model.md` declara fonte "protocolo GWD", que não é código de recusa do core, nem cláusula constitucional, nem seção do `WORKFLOW.md`. Não existe string desse ponto em `scripts/`. |
| `SAFETY_STOP` | Token presente em `plugin/skills/grill-with-docs/scripts/grill_core/store.py:159` (membro de enum de status, sem os limites numéricos). | ACHADO: os limites declarados em data-model.md ("duas rodadas sem progresso, três expansões consecutivas ou 25 perguntas materiais") não aparecem em nenhum arquivo de `scripts/`, `constitution.md` ou `WORKFLOW.md`. Só o próprio token `SAFETY_STOP` é verificável no core. |
| `BLOCKED-CONSTITUTION` | `plugin/skills/grill-with-docs/scripts/grill_workspace.py:427,530,551,560,562,568,608,610,614,618,620,633,636,639,642,647,650,653,663,1549`; exit code `EXIT_CONSTITUTION = 3` em `grill_workspace.py:31`; também `plugin/skills/grill-with-docs/scripts/grill_status.py:135`. | Confirmado — código de recusa do core, com exit `3` como declarado. |
| `HOLD-PRE-02` | `plugin/skills/grill-with-docs/scripts/audit_decisions.py:842-858` (verdict `NO-GO`, `return 1` nas três ramificações: `INVALID-UTF8`, `FILESYSTEM`, `ARTIFACT-INVALID`). | Confirmado — `audit`, exit `1`, como declarado. |
| `BACKLOG-REQUIRED` | `plugin/skills/grill-with-docs/scripts/grill_workspace.py:1348,1443`. | Confirmado — código de recusa do `init`. |
| `MISSING-DEPENDENCY` | `plugin/skills/grill-with-docs/scripts/grill_workspace.py:1430`; verdict correspondente em `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py:403`. | Confirmado — código de recusa do `preflight`. |
| `HOLD-PRE-03` | **Sem código de recusa no core.** Não há string de "catálogo de terceiros"/"confiança" em `plugin/skills/grill-with-docs/scripts/`. O mecanismo real (`--from <archive-url>`, aviso interativo, `.specify/extension-catalogs.yml`, `install_allowed: true`) pertence ao instalador do próprio Spec Kit, fora deste core, e só está documentado em `CLAUDE.md` (raiz do projeto), seção "Extensões do Spec Kit". | ACHADO: fonte declarada em data-model.md ("confiança em catálogo de terceiros") não existe em nenhuma das três categorias permitidas — o mecanismo é externo ao core e não está em `scripts/`, `constitution.md` nem `WORKFLOW.md`. |
| `ROOT-CAUSE-UNPROVEN` | Minted como `ROOT_CAUSE_UNPROVEN` em `plugin/skills/grill-with-docs/scripts/grill_core/triage.py:184`. Tradução SCREAMING_SNAKE → SCREAMING-KEBAB automática em `plugin/skills/grill-with-docs/scripts/grill_workspace.py:172-179` (`translate_v3_code`), via `raise_from_triage_error` (linha 200-212). | Confirmado — código de recusa do `triage`, id final `ROOT-CAUSE-UNPROVEN` após a tradução de fronteira. |
| `HOLD-PRE-04` | **Sem código de recusa próprio.** Princípio de design documentado em `plugin/skills/grill-with-docs/scripts/grill_core/triage.py:4-11` (docstring do módulo: "the public CLI is deterministic stdlib Python and cannot classify natural language... The classification is a *skill* output"). | ACHADO PARCIAL: a regra existe no core como comentário/docstring, não como código de recusa citável por string literal — não cai estritamente em nenhuma das três categorias da própria definição de "fonte" em data-model.md §Ponto de interação. |
| `PLAN_ONLY_STOP` | Cláusula constitucional: heading `### Feature/fix plan-only` em `.specify/memory/constitution.md:40`. Código: `plugin/skills/grill-with-docs/scripts/audit_decisions.py:380`, `plugin/skills/grill-with-docs/scripts/grill_core/workflow_v4.py:110`, `plugin/skills/grill-with-docs/scripts/grill_core/workflow_v3.py:89`, `plugin/skills/grill-with-docs/scripts/ensure_workflow.py:73`. Também `WORKFLOW.md:44` (heading `## Limite desta skill: PLAN_ONLY_STOP`). | Confirmado — obrigatório, como declarado. |

---

## Trilha `ciclo-v4`

| id | fonte verificada | observação |
|---|---|---|
| `HOLD-V4-01` | `WORKFLOW.md:26` ("Em `ship`, a autorização humana permite **invocar** a skill registrada; nunca a substitui nem autoriza side effect direto."), sob o heading `### Proibição explícita de semantic emulation` (`WORKFLOW.md:18`). | Confirmado — obrigatório, como declarado. |
| `BLOCKED_CAPABILITY` | Código: `plugin/skills/grill-with-docs/scripts/grill_core/step_skills.py:127`. Regra de workflow: `WORKFLOW.md:24`, sob o heading `### Proibição explícita de semantic emulation`. | Confirmado — registry de step-skills, como declarado. |
| `UNATTESTED_STEP_OUTPUT` | Código: `plugin/skills/grill-with-docs/scripts/grill_core/step_skills.py:135`; `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py:106`. Regra de workflow: `WORKFLOW.md:12-16,22`, sob o heading `## Invocação canônica: invoke, do not emulate`. | Confirmado — contrato de invocação canônica, como declarado. |
| `POLICY_VIOLATION/DIRECT_STEP_EXECUTION` | Código: `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py:118-119,245`. Regra de workflow: `WORKFLOW.md:23`, sob o heading `### Proibição explícita de semantic emulation`. | Confirmado — proibição explícita do `WORKFLOW.md`, como declarado. |
| `GRANT-SCOPE-VIOLATION` | Código: `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py:2307`, dentro de `converge_wave` (`gauntlet_runs.py:2184`). Regra de workflow: `WORKFLOW.md:30-36`, heading `## Execução paralela: partition e implement-parallel` ("o diff de cada branch é verificado contra o grant antes do merge"). | Confirmado quanto à regra; ACHADO: o código de recusa reside fisicamente em `converge_wave` (etapa `converge`), não em código dedicado a `implement-parallel` — a fonte declarada ("`implement-parallel`") é a etapa que produz o grant violado, não a etapa que o core recusa. |
| `DIRTY-WORKTREE` | Código: `plugin/skills/grill-with-docs/scripts/grill_workspace.py:2079,2083`, dentro de `reconcile_apply` (linha 2043), chamada por `reconcile_command` (linha 1983), subcomando `reconcile` (registrado em `grill_workspace.py:3472`). | Confirmado — código de recusa do `reconcile`, como declarado. |
| `INTEGRATION-CONFLICT` | Código: `INTEGRATION_CONFLICT` em `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py:2318` (conflito repetido) e `2321` ("worker branch does not merge cleanly"), dentro de `converge_wave`. | ACHADO: existe código de recusa próprio (`INTEGRATION_CONFLICT`) para exatamente esta condição. Pela própria regra de data-model.md §Ponto de interação ("Quando o ponto corresponde a um código de recusa do core, o id **é** esse código"), o id correto seria `INTEGRATION-CONFLICT` (kebab), não `HOLD-V4-02` — o documento usa a forma `HOLD-<TRILHA>-<NN>` reservada para pontos **sem** código próprio. |
| `HOLD-V4-02` | `WORKFLOW.md:48-64`, heading `## Ciclo externo de execução (11 etapas)`, coluna "Return when blocked" da tabela das onze etapas. | Confirmado — tabela de onze etapas do `WORKFLOW.md`, como declarado. |

---

## Resumo dos achados

1. `HOLD-PRE-01` — fonte declarada ("protocolo GWD") não é código/cláusula/seção; está em `SKILL.md`/`session-protocol.md`, fora das três categorias e fora do escopo de leitura de T001.
2. `SAFETY_STOP` — só o token existe no core (`store.py:159`); os limites numéricos (2 rodadas, 3 expansões, 25 perguntas) não são verificáveis em `scripts/`, `constitution.md` ou `WORKFLOW.md`.
3. `HOLD-PRE-03` — mecanismo de confiança de catálogo é do instalador do Spec Kit, externo ao core; sem código correspondente em `scripts/`, sem cláusula constitucional, sem seção em `WORKFLOW.md`.
4. `HOLD-PRE-04` — regra existe apenas como docstring/comentário em `triage.py`, não como string de código de recusa citável.
5. `GRANT-SCOPE-VIOLATION` — código reside em `converge_wave` (etapa `converge`), não em código específico de `implement-parallel`; a regra de workflow confere, o comentário sobre "qual etapa" é impreciso.
6. `HOLD-V4-02` — existe código de recusa próprio (`INTEGRATION_CONFLICT`, `gauntlet_runs.py:2318,2321`); pela regra da própria entidade, o id deveria ser `INTEGRATION-CONFLICT`, não `HOLD-V4-02`.

Nenhuma fonte foi inventada. Onde a fonte declarada não existia na categoria exigida, isso está registrado acima em vez de citada como se existisse.


## Nota de sincronização (leader)

Este levantamento foi escrito antes de os seis achados serem aplicados ao
`data-model.md`. Os ids da trilha `ciclo-v4` foram sincronizados: o conflito de
merge em `converge` passa a usar `INTEGRATION-CONFLICT`, que é o código real do
core, e o retorno *when blocked* de qualquer etapa passa a ser `HOLD-V4-02`.
O achado que motivou a renomeação está preservado acima.

Os outros cinco achados foram aplicados ao `data-model.md` e ao `FR-006`, que
passou de três para cinco classes de fonte — a restrição era do requisito, não
ausência da fonte.
