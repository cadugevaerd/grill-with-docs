---

description: "Task list for 027 — sucessão explícita de escopo reconciliado"
---

# Tasks: Sucessão explícita de escopo reconciliado

**Input**: Design documents from `/specs/027-reconcile-scope-succession/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: obrigatórios. FR-012 exige casos negativos dedicados, e SC-002/SC-003
só são verificáveis por teste. Não são opcionais aqui.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos disjuntos, sem dependência pendente)
- **[Story]**: US1..US4 do `spec.md`
- Todo caminho é repo-relativo e explícito, porque o `partition` só fenceia o que
  a linha nomeia

## Path Conventions

Repositório existente, sem estrutura nova. Escopo fechado no `WORK-ITEM.json`
(11 caminhos). Nenhum arquivo fora dele é criado ou alterado.

**Fronteira conhecida do `partition`**: um token só é reconhecido como caminho
quando contém `/`. `README.md` e `CHANGELOG.md` estão na raiz e são, por
construção, infenceáveis para um worker. Eles são trabalho do **leader**, e a
Phase 3 os declara como tal nomeando um caminho de evidência de coordenador —
não é contorno, é a única atribuição honesta que a ferramenta permite.

---

## Phase 1: Fundação — a regra de autorização

**Purpose**: Uma única regra, escrita uma vez, consultada pelos dois caminhos.
As três tarefas tocam o mesmo arquivo e formam um grupo de conflito único: são
serializadas de propósito, não por falta de paralelismo.

- [X] T001 Implementar em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, ao lado de `scopes_overlap`, o predicado puro de autorização que recebe os dois identificadores e o mapa `work_id → conjunto de dependências diretas` e devolve se o par está autorizado, sem calcular nenhum fechamento transitivo (FR-003, FR-008, Contract §C-005, Data model §Relação)
- [X] T002 [US1] Consultar o predicado no laço de sobreposição do caminho completo, em `validate_reconciliation` de `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, suprimindo apenas a anotação `SCOPE-OVERLAP` do par autorizado e reaproveitando o mapa de dependências que a função já constrói (FR-002, FR-004, FR-005, Contract §C-002)
- [X] T003 [US1] Mover a leitura e a validação de `depends-on-work` para **antes** do laço de sobreposição em `reconcile_command` de `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, e consultar o predicado contra o `prior_id` de cada recibo; declaração malformada mapeia para conjunto vazio e não autoriza nada (FR-001, FR-006, Contract §C-001, §C-006, Research §R-001)

**Checkpoint**: os dois caminhos compartilham a mesma regra; nenhuma outra
recusa mudou de linha.

---

## Phase 2: Cobertura e distribuição

**Purpose**: Travar o comportamento e sincronizar a versão. Quatro grupos de
conflito disjuntos — o `partition` empacota em bins paralelos.

- [X] T004 [P] [US1] Acrescentar em `tests/validate_workspace_contract.py` os casos positivos de sucessão: dependência direta declarada atravessa no caminho targeted e no completo, nas duas direções de declaração (FR-001, FR-002, SC-001, Contract §C-001, §C-002)
- [X] T005 [P] [US2] Acrescentar em `tests/validate_workspace_contract.py` os três casos negativos dedicados — ausência de dependência, dependência de terceiro e relação apenas transitiva `A→B→C` — cada um afirmando que a anotação `SCOPE-OVERLAP` permanece (FR-003, FR-004, FR-005, FR-012, SC-002, Contract §C-003, §C-004, §C-005)
- [X] T006 [P] [US3] Acrescentar em `tests/validate_workspace_contract.py` os casos de preservação, cada recusa no caminho que a emite: `DEPENDENCY-SCHEMA` sem conceder autorização, `DEPENDENCY-MISSING` no caminho completo, `DEPENDENCY-NOT-RECONCILED` no targeted, `DEPENDENCY-SELF` no targeted, `DEPENDENCY-CYCLE` com par mutuamente declarado **no caminho completo** — o targeted não tem detecção de ciclo e não deve ser cobrado por ela — e `ADR-CONFLICT` com dependência direta presente (FR-006, FR-007, SC-003, Contract §C-006, §C-007, Analyze §F1, §F4)
- [X] T007 [P] [US4] Acrescentar em `tests/validate_workspace_contract.py` os casos de invariante: preview não altera nenhum byte com par autorizado, apply autorizado é `APPLIED` seguido de `REUSED` byte-idêntico sem churn de `mtime`, e recibo gravado antes da mudança é lido sem conversão (FR-009, FR-010, SC-004, Contract §C-008, §C-009, §C-010)
- [X] T008 [P] Atualizar a constante `VERSION` para `5.2.1` em `tests/validate_distribution.py` (FR-011, SC-005, Contract §C-011)
- [X] T009 [P] Atualizar a versão para `5.2.1` nos quatro manifests: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json` e `.agents/plugins/marketplace.json` (FR-011, SC-005)
- [X] T010 [P] Atualizar os headings de versão para `5.2.1` em `plugin/skills/grill-with-docs/SKILL.md` e `plugin/skills/grill-with-docs/references/session-protocol.md`, mantendo exatamente uma ocorrência de cada prefixo (FR-011, SC-005)

**Checkpoint**: `python3 tests/validate_workspace_contract.py` e
`python3 tests/validate_distribution.py` fecham em exit 0.

---

## Phase 3: Fechamento do leader

**Purpose**: Os pontos de versão que nenhum worker pode fencear, e o registro da
conferência. Tarefa de evidência de coordenador — `partition` a devolve em
`deferred_to_leader` e nenhum worker a executa.

- [X] T011 Sincronizar a versão `5.2.1` no heading de README.md e abrir a entrada `## 5.2.1` em CHANGELOG.md, e registrar a conferência dos oito pontos de distribuição em `.grill/work-items/fix-reconcile-scope-succession-60acbf5d02f244a48207ce55aa48f245/AUDIT.md` (FR-011, SC-005, Contract §C-011)

**Checkpoint**: os oito pontos concordam; `python3 tests/run_validators.py`
fecha em exit 0.

---

## Dependencies

```
Phase 1 (T001 → T002, T003)        barreira
        ↓
Phase 2 (T004..T010, paralelas)    barreira
        ↓
Phase 3 (T011, leader)
```

- T002 e T003 dependem de T001: consomem o predicado.
- T004..T007 dependem da Phase 1: exercitam o comportamento novo.
- T008..T010 não dependem da correção, mas ficam na Phase 2 para que o gate de
  bump e a suíte fechem no mesmo checkpoint.
- T011 depende de T008..T010: a conferência só faz sentido com os outros sete
  pontos já no valor novo.

## Parallel opportunities

Dentro da Phase 2, quatro grupos de conflito disjuntos:

| Grupo | Arquivo(s) | Tarefas |
|---|---|---|
| A | `tests/validate_workspace_contract.py` | T004, T005, T006, T007 |
| B | `tests/validate_distribution.py` | T008 |
| C | os quatro manifests JSON | T009 |
| D | `SKILL.md` + `references/session-protocol.md` | T010 |

Phase 1 é um grupo único por construção — as três tarefas escrevem o mesmo
arquivo. Phase 3 é serial e do leader.

## Independent test criteria

| Story | Critério independente |
|---|---|
| US1 | Reconciliar um sucessor com dependência direta declarada contra um recibo sobreposto e obter `PREVIEW`/exit 0 (T004) |
| US2 | Remover a declaração, ou apontá-la para um terceiro, ou ligá-la só por cadeia, e obter `SCOPE-OVERLAP`/exit 1 nos três (T005) |
| US3 | Cada recusa independente permanece com a mesma anotação, inclusive com dependência direta presente (T006) |
| US4 | Preview não grava; apply é idempotente; recibo legado é lido sem conversão (T007) |

## Implementation strategy

MVP = Phase 1 + T004 + T005. Isso já entrega o comportamento corrigido **e** a
prova de que ele não virou waiver — que são as duas metades inseparáveis desta
correção. Entregar T004 sem T005 seria pior que não entregar: um destravamento
sem cerca.

T006 e T007 fecham a regressão. T008..T011 são a obrigação de distribuição da
cláusula *Bump obrigatório do plugin* e não podem faltar no merge.

---

## Phase 4: Convergence

**Purpose**: Fechar as lacunas que a avaliação do código contra spec, plan e
tasks encontrou. Todas as três são de cobertura: a correção está implementada e
nada no código contraria a intenção declarada.

- [X] T012 Commitar a árvore antes do `reconcile --apply` em `test_reconcile_succession_targeted_dependency_authorizes_scope_overlap`, em `tests/validate_workspace_contract.py`, para que o caso exercite a autorização de sucessão em vez de parar em `DIRTY-WORKTREE`; o teste irmão `test_reconcile_succession_targeted_apply_is_byte_idempotent_and_reuses_prior_receipt` já faz isso e é o padrão a seguir per SC-006, US1/AC1 (partial)
- [X] T013 Acrescentar em `tests/validate_workspace_contract.py` o caso em que `depends-on-work` declara **vários** ids e um deles é o `prior_id` sobreposto — autoriza — mais o controle em que a lista multi-id **não** contém o `prior_id` — não autoriza per FR-001, FR-012 (partial)
- [X] T014 Acrescentar em `tests/validate_workspace_contract.py` o caso de apply do caminho **completo** com par autorizado, afirmando `APPLIED` seguido de `REUSED` byte-idêntico e sem churn de `mtime`, fechando a simetria que FR-008 exige entre os dois caminhos per FR-008, FR-009, C-009 (partial)

**Checkpoint**: `python3 tests/run_validators.py` fecha em exit 0, com o único
skip dependente de ambiente preservado.
