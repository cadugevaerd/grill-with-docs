# Research: Contrato do goal.md

**Fase 0** | **Data**: 2026-08-22

Nenhum marcador `NEEDS CLARIFICATION` restou no spec. As oito decisões materiais
foram investigadas e seladas durante a entrevista que produziu o handoff; este
documento consolida o que foi pesquisado, a conclusão e o que foi descartado.

---

## R-01 — Quais runtimes de goal loop existem e como diferem

**Decisão**: o documento é neutro em relação ao runtime. Nenhuma instrução pode
assumir orçamento próprio, transição de status persistida ou armazenamento local.

**Rationale**: dois runtimes distintos estão instalados no ambiente do operador e
têm semânticas de parada opostas.

- Codex CLI — `~/.codex/goals_1.sqlite`, tabela `thread_goals`, com status
  persistido em `active | paused | blocked | usage_limited | budget_limited |
  complete` e `token_budget` por goal. Há execuções do protocolo já concluídas
  por essa via, com objetivos formulados à mão.
- Hermes — `~/.hermes/hermes-agent/hermes_cli/goals.py`, laço Ralph: um modelo
  juiz responde, a cada turno, se o objetivo foi satisfeito pela última resposta.
  `DEFAULT_MAX_TURNS = 20`. Falha do juiz é **fail-OPEN**: na dúvida, continua.

Um documento que se apoiasse em `status=blocked` seria robusto no primeiro e
inerte no segundo.

**Alternativas consideradas**: mirar só o Codex CLI (parada mais robusta,
documento inútil no Hermes); mirar só o Hermes (sinal frágil e sem uso
comprovado).

**Fonte**: ADR-0001.

---

## R-02 — Como fazer o laço parar sem que a parada seja lida como fracasso

**Decisão**: o objetivo declarado é o ciclo inteiro, e a parada é sinalizada por
`GOAL-HOLD: <motivo>`. Para que a parada não dependa de o juiz obedecer a uma
instrução avulsa, o documento fornece **templates de objetivo** que embutem a
condição de parada na própria formulação julgada: "…até `<conclusão>` **ou** até
que a resposta contenha a linha `GOAL-HOLD:`".

**Rationale**: o juiz responde a uma pergunta só — "o objetivo foi satisfeito?".
Com o objetivo formulado como "termine o ciclo", chegar a um ponto de interação
produz `done=false`, o laço reinjeta a continuação, e o agente passa a ser
pressionado a decidir sozinho aquilo que deveria perguntar. Embutindo a
alternativa na formulação, `GOAL-HOLD` **satisfaz** o objetivo, e o juiz decide
`done` pelo mesmo raciocínio que usaria para a conclusão normal.

**Alternativas consideradas**: declarar o objetivo como "avançar até o próximo
ponto de interação" — judge-safe sem depender de formulação alguma, porque chegar
ao ponto satisfaz o objetivo literalmente, mas exige relançamento manual a cada
trecho; e contrato híbrido por trilha, que colocaria dois mecanismos de parada
distintos no mesmo documento.

**Fonte**: ADR-0004.

---

## R-03 — Backstop para o juiz que ignora a sinalização

**Decisão**: o documento instrui o operador a declarar um orçamento de turnos
curto e explícito na trilha de entrevista, em vez de herdar o padrão do runtime,
e exige que a linha `GOAL-HOLD:` seja a última da resposta, isolada.

**Rationale**: o comentário do módulo de goals do Hermes registra que modelos com
raciocínio já truncaram o JSON do veredito sob cap apertado, e que a falha do
juiz é fail-OPEN. Sob esse regime o único freio efetivo é o número de turnos, que
por padrão é 20 — alto demais para uma trilha cheia de perguntas. Um orçamento
declarado transforma o freio em decisão consciente do operador.

**Alternativas consideradas**: deixar o risco aberto como decisão adiada, que
travaria a fase por depender de evidência que só existe depois do documento;
e tratar o risco como bloqueio, que impediria qualquer avanço.

**Fonte**: BL-0001, ADR-0004.

---

## R-04 — Quais paradas são estruturalmente obrigatórias

**Decisão**: `PLAN_ONLY_STOP` e `ship` são paradas obrigatórias e não
configuráveis. O restante é enumerado por trilha, e a enumeração fecha com
cláusula residual fail-closed.

**Rationale**: a cláusula constitucional **Feature/fix plan-only** diz que
"feature e fix terminam em PLAN_ONLY_STOP; nenhum plano autoriza alteração ou
publicação" — o laço não pode atravessar a fronteira por conta própria. O
`WORKFLOW.md` diz que, em `ship`, "a autorização humana permite **invocar** a
skill registrada; nunca a substitui". Uma lista sem residual trataria toda
situação não prevista como autorizada, que é o waiver implícito proibido pela
cláusula **Fail-closed sem waiver**.

**Alternativas consideradas**: lista fechada sem residual (mais autônoma, abre
waiver implícito); critério puro sem enumeração (documento curto e resistente a
versão, mas não auditável — duas execuções parariam em lugares diferentes).

**Fonte**: ADR-0005.

---

## R-05 — Qual é o papel do coordenador de agentes

**Decisão**: a sessão principal é orquestrador e permanece leader e única
Evidence Boundary. Workers paralelizam por subdomínio dentro de **qualquer**
etapa. Nenhum worker produz `step-output` nem escreve em `.grill/` ou
`.specify/reports/`.

**Rationale**: `orca orchestration` expõe `run-create`, `task-create`,
`worker-start`, `dispatch`, `ask` e `gate-create`. O `WORKFLOW.md` já prevê
paralelismo em `implement-parallel`, mas restringe: "tarefa que escreve evidência
de coordenador nunca é despachada a worker algum". Saída de worker sem a cadeia
`skill-resolution → dispatch-intent → skill-invocation → step-output` é
`UNATTESTED_STEP_OUTPUT`. Despachar worker para *ser* a etapa é emulação
semântica, explicitamente proibida.

O tier segue a cláusula constitucional **Tier de modelo e esforço do worker
Orca**: `--model` sempre, `--effort` quando suportado, conferência de
`launch.effective` contra `launch.requested`, bloqueio na divergência, e nada de
reusar `--terminal`. Em `implement-parallel` o modelo não vem dessa regra: é
derivado do tier do nó via `assets/workflow-tier-models.json`.

**Alternativas consideradas**: usar `orca orchestration ask --timeout-ms` como
canal de pergunta, o que evitaria encerrar o laço a cada pergunta mas tiraria a
interação do transcript e faria a autorização de ação irreversível depender do
runtime Orca estar vivo; e restringir Orca a `implement-parallel`, alinhado ao
`WORKFLOW.md` mas desperdiçando decomposição por subdomínio nas etapas de leitura
e análise.

**Fonte**: ADR-0006, ADR-0007.

---

## R-06 — Como o laço descobre onde está

**Decisão**: o documento cita nominalmente os verbos já existentes —
`status --format markdown`, `gauntlet-status --work-id`, `checkpoint` e
`phase-turn` — em vez de introduzir um verbo agregador.

**Rationale**: a CLI do core já expõe esses quatro. Um verbo `goal` que os
reembalasse criaria um quinto ponto de verdade sobre o mesmo estado, sem fonte
nova, e um enforcement próprio duplicaria a cadeia de attestation que já cerca
etapa não atestada.

**Alternativas consideradas**: verbo agregador (leitura mais cômoda, SSOT em
risco); verbo mais enforcement (dois enforcements sobre a mesma sequência, com
risco alto de divergirem).

**Fonte**: ADR-0008.

---

## R-07 — Onde o documento vive e como chega ao consumidor

**Decisão**: asset gerenciado, template em
`plugin/skills/grill-with-docs/assets/`, materializado na raiz do projeto
consumidor pelo `init`, no-clobber, com marcador de versão próprio no formato
`<!-- grill-with-docs-goal:v1 -->` e tupla `ESSENTIAL` própria e congelada.

**Rationale**: um documento que só existe no repositório de origem não automatiza
projeto nenhum. O `WORKFLOW.md` já resolve exatamente esse problema pela mesma
máquina. O marcador é independente da versão SemVer do plugin porque atrelá-lo ao
SemVer marcaria como incompatível, a cada bump, todo documento já materializado —
sem mudança de contrato alguma. A tupla nunca é derivada da tupla de nenhuma
versão do `WORKFLOW.md`: derivá-la faria um typo reescrever o contrato em vez de
reprovar um teste.

**Alternativas consideradas**: asset distribuído sem materialização (sem código
novo, mas deriva silenciosa no consumidor); documento só na raiz deste
repositório (zero impacto em distribuição, automatiza apenas o dogfooding).

**Fonte**: ADR-0003.

**Nota de fase**: a materialização em si é entrega da FASE-002. Esta fase apenas
cria o arquivo no caminho de asset e reserva o marcador.
