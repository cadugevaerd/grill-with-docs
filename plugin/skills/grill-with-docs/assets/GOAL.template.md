<!-- grill-with-docs-goal:v1 -->
# Loop de objetivo — grill-with-docs

Este documento é a única fonte que o laço precisa ler para saber quando parar.
Ele cobre duas trilhas — pré-ciclo e ciclo v4 — e nomeia a fronteira entre elas:
`PLAN_ONLY_STOP`. A ordem é fixa: pré-ciclo sempre antes de ciclo v4.

## Contrato de parada

Forma única, emitida como linha própria, isolada, a última da resposta:

```text
GOAL-HOLD: <motivo em uma frase>
```

- **Última linha, isolada.** É o que o juiz do laço pesa ao decidir se a resposta
  concluiu o objetivo.
- **Motivo em uma frase.** Nomeia a causa, não narra o percurso.
- **Cita o identificador do ponto.** Código de recusa do núcleo quando existir;
  `HOLD-<TRILHA>-<NN>` (com `<TRILHA>` em `PRE` ou `V4`) quando não existir; ou a
  expressão `cláusula residual` quando a parada não corresponde a nenhum ponto
  enumerado. Sem identificador, duas paradas pelo mesmo motivo não são
  agrupáveis.
- **Uma por resposta.** Duas linhas `GOAL-HOLD:` na mesma resposta tornam
  ambíguo o que devolveu o controle.
- **A resposta termina na sinalização.** Texto posterior que anuncie
  continuação (“...e enquanto isso vou preparando o próximo passo”) é violação
  do contrato: contradiz para o juiz o que a linha afirma.

`GOAL-HOLD` **satisfaz** o objetivo — os dois templates abaixo o declaram como
alternativa de conclusão. Não é erro nem bloqueio de trabalho; é o contrato
funcionando.

### Registro de avanço

Antes de encerrar cada turno, o laço deixa o avanço gravado no projeto —
decisão selada, receipt escrito, fase atualizada — e não apenas na resposta.
O esgotamento do orçamento de turnos ocorre **sem** sinalização; é o avanço
gravado no projeto, não o estado do turno, que permite retomar sem repetir
trabalho já concluído.

## Templates de objetivo

Os templates são **normativos**, não exemplo. Sem eles nada garante a parada:
a alternativa de parada precisa entrar na formulação **julgada** pelo juiz do
laço, não numa instrução separada. Cada template tem quatro partes na mesma
ordem: alvo, conclusão, alternativa de parada, fecho.

### Template A — trilha pré-ciclo

```text
Conduza a trilha pré-ciclo do grill-with-docs no repositório <ROOT>, para o work
item <WORK_ID>, seguindo goal.md na raiz. A trilha termina quando a auditoria
retornar GO e o path do handoff selecionado for entregue
— ou quando a resposta contiver a linha GOAL-HOLD:. Qualquer um dos dois cumpre este objetivo.
```

Origem dos valores: `<ROOT>` é o caminho do Git root real do projeto;
`<WORK_ID>` é a identidade do work item, como aparece em `.grill/work-items/`.

**Orçamento**: nesta trilha o operador declara, no próprio runtime, um limite
de no máximo **cinco turnos, com três como recomendado**, em vez de herdar o
padrão do runtime. A trilha para na primeira decisão que exige julgamento, o
que ocorre tipicamente em um a três turnos; margem maior só multiplica
continuações caso `GOAL-HOLD` não seja honrado.

### Template B — trilha ciclo v4

```text
Conduza o ciclo externo de onze etapas do WORKFLOW.md no repositório <ROOT>, para
o work item <WORK_ID>, a partir do handoff <HANDOFF_PATH>, seguindo goal.md na
raiz. O ciclo termina quando ship concluir
— ou quando a resposta contiver a linha GOAL-HOLD:. Qualquer um dos dois cumpre este objetivo.
```

Origem dos valores: `<ROOT>` e `<WORK_ID>` como acima; `<HANDOFF_PATH>` é o path
do handoff selecionado, entregue ao fim da trilha pré-ciclo.

**Orçamento**: teto de no máximo **quarenta turnos**, derivado de o ciclo ter
onze etapas e parar por autorização apenas na última.

O Template B nunca é colado antes de a trilha pré-ciclo ter entregue o
handoff: atravessar `PLAN_ONLY_STOP` é ato humano.

## Trilha pré-ciclo

**Início**: projeto sem work item. **Conclusão**: auditoria `GO` e path do
handoff entregue. **Etapas**, nesta ordem: `init`, `preflight`, `triage`, gate
constitucional, entrevista, `audit`.

Se `.specify/memory/constitution.md` ou `WORKFLOW.md` não estiverem
materializados no projeto de destino, o laço para e nomeia o que falta — não
cria nenhum dos dois.

**Retomada**: o laço distingue decisão já selada (registrada no work item —
ADR, DQ, cobertura constitucional já respondida) de decisão nova. Relançar o
mesmo objetivo depois de o operador responder não reabre o que já foi
respondido. O laço determina em qual trilha está a partir do estado gravado no
projeto (existência e fase do work item em `.grill/work-items/`), nunca da
memória do turno.

**Orientação**: para descobrir a pendência corrente, o laço invoca

```text
python3 "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/grill-with-docs/scripts/grill_workspace.py" \
  status ROOT --format markdown
```

e reproduz o stdout literalmente. `all good` significa nenhuma pendência; caso
contrário, a tabela `Item | Status | Pendência` nomeia a próxima ação.

Cada ponto abaixo é rastreável a uma de cinco classes de fonte: cláusula
constitucional; seção do `WORKFLOW.md`; código de recusa do núcleo, citável por
string literal; limite declarado no `state.json` do work item; ou regra do
protocolo publicada na `SKILL.md`.

| id | condição | fonte |
|---|---|---|
| `HOLD-PRE-01` | pergunta material da entrevista | `SKILL.md` §Entrevista incremental — uma pergunta atômica por rodada |
| `SAFETY_STOP` | duas rodadas sem progresso, três expansões consecutivas ou 25 perguntas materiais | token em `grill_core/store.py`; limites em `state.json` §limits (`max_no_progress_rounds`, `max_scope_growth_streak`, `max_questions_per_run`) |
| `BLOCKED-CONSTITUTION` | cobertura ausente/duplicada, `PENDING`, `UNMAPPED`, hash stale | gate constitucional, exit `3` |
| `HOLD-PRE-02` | auditoria `NO-GO` | `audit`, exit `1` |
| `BACKLOG-REQUIRED` | backlog não resolvido nem vinculado | `init` |
| `MISSING-DEPENDENCY` | dependência exigida ausente sob `--require-dependencies` | `preflight` |
| `HOLD-PRE-03` | decisão de usar `--allow-install` | `SKILL.md` §Dependências e backlog — mecanismo de confiança do instalador do Spec Kit, externo ao core |
| `ROOT-CAUSE-UNPROVEN` | laudo não prova causa raiz | `triage` |
| `HOLD-PRE-04` | escolha de rota na triagem | `grill_core/triage.py`, docstring do módulo — o core não classifica linguagem natural |
| `PLAN_ONLY_STOP` | fronteira entre as trilhas | cláusula constitucional **Feature/fix plan-only** — **obrigatório, não configurável** |

## Trilha ciclo v4

**Início**: handoff aprovado e auditoria `GO`. **Conclusão**: `ship` concluído.
**Etapas**, ordem canônica: `specify → plan → checklist → tasks → analyze →
partition → implement-parallel → converge → verify → review → ship`.

Reproduzir o resultado de uma etapa por meio próprio — shell, tool genérica,
raciocínio direto — em vez de invocar a capacidade registrada **não avança a
sequência**; é `POLICY_VIOLATION/DIRECT_STEP_EXECUTION` ou `UNATTESTED_STEP_OUTPUT`.

| id | condição | fonte |
|---|---|---|
| `HOLD-V4-01` | autorização de `ship` | `WORKFLOW.md` — a autorização humana permite invocar, nunca substitui — **obrigatório, não configurável** |
| `BLOCKED_CAPABILITY` | skill ausente, ambígua, abaixo da versão mínima, hash divergente ou catálogo não confiável | registry de step-skills |
| `UNATTESTED_STEP_OUTPUT` | saída sem a cadeia de atestação completa | contrato de invocação canônica |
| `POLICY_VIOLATION/DIRECT_STEP_EXECUTION` | tentativa de emulação semântica | proibição explícita do `WORKFLOW.md` |
| `GRANT-SCOPE-VIOLATION` | worker escreveu fora do grant | `gauntlet_runs.py`, em `converge_wave`; regra em `WORKFLOW.md` §Execução paralela |
| `DIRTY-WORKTREE` | árvore suja fora de `.grill/global/` | `reconcile` |
| `INTEGRATION-CONFLICT` | conflito de merge em `converge` | `gauntlet_runs.py`, em `converge_wave` |
| `HOLD-V4-02` | retorno *when blocked* de qualquer etapa não coberto acima | `WORKFLOW.md` — tabela das onze etapas, coluna Return when blocked |

## Cláusula residual

Fora de qualquer ponto enumerado, o laço para sempre que a **próxima ação
deixar de ser determinística e reversível**:

- **Determinística**: o mesmo estado de entrada produz sempre o mesmo
  resultado, sem escolha de valor do laço.
- **Reversível**: a ação pode ser desfeita sem perda, ou não deixa side effect
  que sobreviva ao turno.

Gatilhos: ambiguidade entre duas leituras do mesmo estado, evidência faltante,
decisão de valor, side effect irreversível. Efeito: `GOAL-HOLD` mesmo sem
constar em nenhuma tabela, citando `cláusula residual` como identificador.

A ausência do coordenador de agentes **não** é caso da cláusula residual: o
caminho degradado (ver Delegação) é determinístico e reversível por
construção, então o laço segue sequencialmente, sem parar.

**O que não é ponto de interação** — o laço executa sozinho, sem parar:

- invocar a próxima etapa da sequência quando os predecessores estão
  terminais;
- consultar comandos de orientação (status, leitura de auditoria);
- registrar avanço no projeto ao fim do turno;
- despachar e coletar workers dentro de uma etapa já decidida como
  decomponível;
- resolver divergência entre workers da mesma etapa quando a resolução é
  determinística (um resultado é claramente inválido e o outro não).

## Delegação

A sessão condutora é o **leader** e a única **Evidence Boundary**. A
delegação a trabalhadores paralelos é interna à etapa, válida em qualquer
etapa: a sessão condutora permanece a única responsável pela evidência e a
única que declara o resultado de cada etapa.

**Decomponível por subdomínio** (critério aplicável, sem julgamento): existe
partição do trabalho em conjuntos de arquivos disjuntos, e nenhum desses
conjuntos escreve evidência de coordenação.

**Proibições do worker**: não declara resultado de etapa (`step-output`); não
escreve evidência de coordenação — enumerada de forma fechada: `.grill/` e
`.specify/reports/`; não é despachado para *ser* a etapa.

**Tier**: todo worker é despachado com `--model` sempre, `--effort` quando o
agente/modelo suportar, com o par correspondente à natureza do trabalho.
`launch.effective` é conferido contra `launch.requested`; divergência bloqueia
o despacho. `--terminal` nunca é reusado quando modelo ou esforço precisam ser
definidos. **Exceção**: em `implement-parallel`, o modelo do worker é
**derivado** do tier do nó via binding versionado, não escolhido.

**Disponibilidade do coordenador**: critério determinístico, decidido por
saída de comando, nunca por interpretação de texto livre — binário `orca`
resolvível **e** `orca status` reportando runtime pronto. Falha em qualquer
das duas condições aciona o **caminho degradado**: execução sequencial pelo
mecanismo nativo do runtime. O caminho degradado não bloqueia o laço e não
reduz o que a etapa entrega.

Se o coordenador some no meio de uma etapa já distribuída, a sessão condutora
assume o restante sozinha, sequencialmente, sem parada adicional e sem
descartar o que os workers já concluíram. Resultados conflitantes entre
workers da mesma etapa são resolvidos pela sessão condutora; o que ela não
conseguir resolver de forma determinística cai na cláusula residual.

## Orientação

Verbos existentes que o laço consulta para descobrir em que ponto do trabalho
está, com seus argumentos obrigatórios:

- `grill_workspace.py status ROOT --format markdown` — pendência corrente do
  work item, na trilha pré-ciclo.
- `grill_workspace.py audit ROOT --work-id WORK_ID` — verdict `GO`/`NO-GO` da
  entrevista, antes de `PLAN_ONLY_STOP`.
- `grill_workspace.py checkpoint ROOT --work-id WORK_ID --step STEP --state
  in-progress|complete|blocked [--evidence PATH] [--reason TEXTO]` — sela a
  etapa e move `current_step`. O retorno nomeia a etapa seguinte.
- `grill_workspace.py gauntlet-status ROOT --work-id WORK_ID [--run-id RUN]` —
  estado da ativação e da run corrente, na trilha ciclo v4.
- `grill_workspace.py phase-turn ROOT --work-id WORK_ID [--reason TEXTO]` —
  vira a fase do ROADMAP quando a atual fecha.
- A posição na trilha ciclo v4 também é legível pela cadeia de atestação já
  registrada (`skill-resolution → dispatch-intent → skill-invocation →
  step-output`, conforme `WORKFLOW.md` §Invocação canônica): a próxima etapa é
  a primeira da ordem canônica sem `step-output` terminal.
