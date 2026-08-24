# Data Model: Contrato do goal.md

**Fase 1** | **Data**: 2026-08-22

O artefato desta fase é um documento, não um esquema executável. O "modelo de
dados" aqui é a **estrutura normativa** do documento: quais blocos ele precisa
ter, o que cada um contém e quais regras de validação um leitor — humano ou
validador da FASE-003 — aplica sobre eles.

---

## Entidade: Documento

O arquivo inteiro, materializado como `goal.md` na raiz do projeto consumidor.

| Campo | Conteúdo | Regra |
|---|---|---|
| marcador | `<!-- grill-with-docs-goal:v1 -->` | Primeira linha do arquivo. Independente da versão SemVer do plugin. |
| título | Cabeçalho de nível 1 | Uma ocorrência. |
| trilhas | Uma seção por trilha | `## Trilha pré-ciclo` e `## Trilha ciclo v4`, nessa ordem. |
| templates de objetivo | Dois blocos citáveis | Um por trilha. |
| contrato de parada | Uma seção | Forma, posição e semântica do `GOAL-HOLD`. |
| pontos de interação | Uma tabela dentro de cada trilha | Mais `## Cláusula residual` em seção própria, depois das duas trilhas. |
| delegação | Uma seção | Regras de worker, tier e caminho degradado. |
| orientação | Uma lista | Verbos existentes que o laço consulta. |

**Invariante**: nenhum bloco pode citar recurso exclusivo de um runtime de goal
loop — orçamento próprio, transição de status persistida ou armazenamento local
(FR-009). A única menção admitida a orçamento é a instrução ao operador para
declarar o seu (FR-005).

---

## Entidade: Trilha

Um dos dois trechos de trabalho que o laço conduz.

| Campo | Valores |
|---|---|
| id | `pre-ciclo` \| `ciclo-v4` |
| início | `pre-ciclo`: projeto sem work item. `ciclo-v4`: handoff aprovado e auditoria `GO`. |
| conclusão | `pre-ciclo`: `PLAN_ONLY_STOP` com o path do handoff entregue. `ciclo-v4`: `ship` concluído. |
| etapas | `pre-ciclo`: `init`, `preflight`, `triage`, gate constitucional, entrevista, `audit`. `ciclo-v4`: as onze etapas, de `specify` a `ship`. |
| template de objetivo | Exatamente um, próprio (ver contrato). |
| pontos de interação | Tabela própria (ver abaixo). |

**Transição entre trilhas**: `pre-ciclo → ciclo-v4` **nunca** é automática.
`PLAN_ONLY_STOP` é ponto de interação obrigatório e não configurável (FR-008).

---

## Entidade: Template de objetivo

A formulação que o operador cola no goal loop. Normativa, não exemplo (FR-003).

| Campo | Regra |
|---|---|
| alvo | Nomeia a trilha e o work item. |
| conclusão | Descreve o que conclui a trilha. |
| alternativa de parada | `**ou** até que a resposta contenha a linha GOAL-HOLD:` — obrigatória e literal (FR-002). |
| fecho | Declara que qualquer uma das duas cumpre o objetivo. |
| orçamento | Na trilha `pre-ciclo`, instrui o operador a declarar limite de turnos curto (FR-005). |

**Invariante**: a alternativa de parada faz parte da formulação **julgada**, não
de uma instrução separada ao juiz. Sem ela, nada garante a parada — e o documento
precisa dizer isso em texto.

---

## Entidade: Ponto de interação

Uma condição enumerada em que o laço devolve o controle.

| Campo | Regra |
|---|---|
| id | Identificador estável. Quando o ponto corresponde a um código de recusa do core, o id **é** esse código. Quando não há código próprio, o id segue `HOLD-<TRILHA>-<NN>`, com `<TRILHA>` em `PRE` ou `V4`. |
| trilha | `pre-ciclo` \| `ciclo-v4`. |
| fonte | Uma das cinco classes de FR-006: cláusula constitucional, seção do `WORKFLOW.md`, código de recusa do core citável por string literal, limite declarado no `state.json` do work item, ou regra do protocolo publicada na `SKILL.md`. Obrigatória. |
| obrigatório | `true` apenas para `PLAN_ONLY_STOP` e `ship`; os demais são `false`. |

### Trilha `pre-ciclo`

| id | condição | fonte |
|---|---|---|
| `HOLD-PRE-01` | pergunta material da entrevista | `SKILL.md` §Entrevista incremental — uma pergunta atômica por rodada |
| `SAFETY_STOP` | duas rodadas sem progresso, três expansões consecutivas ou 25 perguntas materiais | token em `grill_core/store.py`; os limites vivem em `state.json` §limits (`max_no_progress_rounds`, `max_scope_growth_streak`, `max_questions_per_run`) |
| `BLOCKED-CONSTITUTION` | cobertura ausente/duplicada, `PENDING`, `UNMAPPED`, hash stale | gate constitucional, exit `3` |
| `HOLD-PRE-02` | auditoria `NO-GO` | `audit`, exit `1` |
| `BACKLOG-REQUIRED` | backlog não resolvido nem vinculado | `init` |
| `MISSING-DEPENDENCY` | dependência exigida ausente sob `--require-dependencies` | `preflight` |
| `HOLD-PRE-03` | decisão de usar `--allow-install` | `SKILL.md` §Dependências e backlog — o mecanismo de confiança é do instalador do Spec Kit, externo ao core, e por isso não tem código de recusa próprio |
| `ROOT-CAUSE-UNPROVEN` | laudo não prova causa raiz | `triage` |
| `HOLD-PRE-04` | escolha de rota na triagem | `grill_core/triage.py`, docstring do módulo — o core é determinístico e não classifica linguagem natural; a classificação é saída de skill |
| `PLAN_ONLY_STOP` | fronteira entre as trilhas | cláusula **Feature/fix plan-only** — **obrigatório** |

### Trilha `ciclo-v4`

| id | condição | fonte |
|---|---|---|
| `HOLD-V4-01` | autorização de `ship` | `WORKFLOW.md` — a autorização humana permite invocar, nunca substitui — **obrigatório** |
| `BLOCKED_CAPABILITY` | skill ausente, ambígua, abaixo da versão mínima, hash divergente ou catálogo não confiável | registry de step-skills |
| `UNATTESTED_STEP_OUTPUT` | saída sem a cadeia de atestação | contrato de invocação canônica |
| `POLICY_VIOLATION/DIRECT_STEP_EXECUTION` | tentativa de emulação semântica | proibição explícita do `WORKFLOW.md` |
| `GRANT-SCOPE-VIOLATION` | worker escreveu fora do grant | código em `gauntlet_runs.py`, dentro de `converge_wave`; regra em `WORKFLOW.md` §Execução paralela. O grant nasce em `implement-parallel`, mas quem recusa é `converge` |
| `DIRTY-WORKTREE` | árvore suja fora de `.grill/global/` | `reconcile` |
| `INTEGRATION-CONFLICT` | conflito de merge em `converge` | código `INTEGRATION_CONFLICT` em `gauntlet_runs.py`, em `converge_wave` |
| `HOLD-V4-02` | retorno *when blocked* de qualquer etapa | tabela de onze etapas do `WORKFLOW.md` |

---

## Entidade: Cláusula residual

A regra que estende a parada ao que não foi enumerado (FR-007).

| Campo | Conteúdo |
|---|---|
| condição de avanço | A próxima ação é determinística **e** reversível. |
| gatilhos de parada | Ambiguidade, evidência faltante, decisão de valor, side effect irreversível. |
| efeito | `GOAL-HOLD` mesmo sem constar em nenhuma tabela. |

---

## Entidade: Sinalização de parada

| Campo | Regra |
|---|---|
| forma | `GOAL-HOLD: <motivo>` |
| posição | Última linha da resposta, isolada (FR-004). |
| motivo | Uma frase. |
| nomeação | Cita o identificador estável do ponto (FR-018, FR-019), ou declara a cláusula residual quando não houver ponto. |

**Modo de falha conhecido**: motivo enterrado no meio de um parágrafo longo é
material que o juiz pode não pesar. Daí a exigência de linha isolada e última.

---

## Entidade: Worker delegado

Trabalho paralelo despachado a partir da sessão condutora.

| Campo | Regra |
|---|---|
| escopo | Subdomínio, dentro de uma etapa. Qualquer etapa (FR-010). |
| modelo | Declarado em `--model`; `--effort` quando suportado; tier pela natureza do trabalho (FR-012). |
| verificação | `launch.effective` conferido contra `launch.requested`; divergência bloqueia o despacho. |
| terminal | Nunca reusar `--terminal` quando modelo ou esforço precisam ser definidos. |
| exceção | Em `implement-parallel`, o modelo é **derivado** do tier do nó via binding versionado, não escolhido (FR-013). |

**Proibições** (FR-011): worker não declara `step-output`; worker não escreve em
`.grill/` nem em `.specify/reports/`; worker não é despachado para *ser* a etapa.

---

## Entidade: Disponibilidade do coordenador

| Campo | Regra |
|---|---|
| critério | Binário `orca` resolvível **e** `orca status` reportando runtime pronto (FR-014). |
| falha em qualquer das duas | Caminho degradado. |
| caminho degradado | Execução sequencial pelo mecanismo nativo do runtime. |
| efeito do degradado | Não bloqueia e não reduz o que a etapa entrega (FR-015). |
