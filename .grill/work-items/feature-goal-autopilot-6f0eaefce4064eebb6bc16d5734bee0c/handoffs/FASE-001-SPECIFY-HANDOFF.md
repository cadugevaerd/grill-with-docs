# FASE-001 — Contrato do goal.md

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: goal.md, goal loop, ponto de interação, ciclo v4, GWD
- ADRs: ADR-0001, ADR-0002, ADR-0004, ADR-0005, ADR-0006, ADR-0007
- BLs: BL-0001

## WHAT
- delivery-units: DU-001
- development-type: documentation

O resultado é um documento único que um goal loop consegue seguir para conduzir
o protocolo de ponta a ponta sem supervisão contínua.

Atores: o operador humano, que formula o objetivo e responde nas paradas; a
sessão agente, que lê o documento e conduz; o juiz do goal loop, que decide a
cada turno se o objetivo foi satisfeito.

O documento cobre duas trilhas, separadas por uma fronteira nomeada:

1. **Pré-ciclo** — da criação do work item até a auditoria `GO` e a entrega do
   path do handoff selecionado.
2. **Ciclo externo de onze etapas** — de `specify` a `ship`.

Escopo incluído:

- Os dois **templates de objetivo**, um por trilha, que o operador cola no goal
  loop. Cada template embute a condição de parada na própria formulação
  julgada, de modo que chegar a uma parada satisfaça o objetivo em vez de
  contrariá-lo.
- A forma da sinalização de parada: uma linha própria e isolada, a última da
  resposta, com motivo em uma frase.
- A instrução de orçamento: o operador declara um limite de turnos curto na
  trilha de entrevista, em vez de herdar o default do runtime.
- A **lista fechada de pontos de interação** por trilha, e a cláusula residual
  que manda parar também fora da lista sempre que a próxima ação deixar de ser
  determinística e reversível.
- A seção de delegação: quando um coordenador de agentes está disponível, a
  sessão principal permanece leader e única fronteira de evidência, e o
  trabalho decomponível por subdomínio vai para trabalhadores paralelos, em
  qualquer etapa. Nenhum trabalhador produz o resultado atestado da etapa nem
  escreve evidência de coordenador.
- O critério determinístico de disponibilidade desse coordenador e o caminho
  degradado, sequencial, que vale quando ele não está disponível — degradar
  nunca bloqueia e nunca reduz conformidade.
- A citação nominal dos comandos de orientação já existentes que o loop
  consulta para saber onde está.

Escopo excluído: materialização do documento no projeto consumidor, validação
automatizada, versionamento e qualquer superfície nova de linha de comando.

Critérios de aceite:

- O documento não depende de nenhum recurso exclusivo de um runtime de goal
  loop específico — nem orçamento, nem transição de estado, nem armazenamento.
- As duas paradas obrigatórias, a fronteira entre as trilhas e a autorização da
  etapa final, aparecem como não negociáveis e não configuráveis.
- Cada ponto de interação enumerado é rastreável a uma fonte: a Constituição, o
  contrato de workflow do projeto ou um código de recusa do núcleo.

## WHY

Hoje o protocolo exige presença humana contínua mesmo em trechos inteiramente
mecânicos, e nada distingue, para quem conduz, o passo que exige julgamento do
passo que só exige execução. A consequência prática é atrito: o operador
acompanha turnos que não precisavam dele, e a autonomia acaba sendo obtida
afrouxando gates.

Evidência de que o uso já existe sem contrato: há execuções do protocolo
conduzidas por goal loop registradas no armazenamento do runtime, com objetivos
formulados à mão, uma por vez, sem garantia de parada.

Evidência do modo de falha que o documento precisa derrotar: em pelo menos um
dos runtimes conhecidos, a falha do juiz é *fail-open* — na dúvida, o laço
continua — e o único freio é o orçamento de turnos. Sob esse regime, um
objetivo formulado como "termine o ciclo" transforma cada gate numa pressão
para o agente decidir sozinho o que deveria perguntar.

Restrições: a cláusula que mantém feature e fix plan-only proíbe atravessar a
fronteira entre as trilhas sem autorização; a cláusula fail-closed proíbe
tratar situação não prevista como autorizada a seguir; e o contrato de workflow
reserva a autorização humana para permitir a invocação da etapa final, nunca
para substituí-la.

Risco tratado: o juiz pode não honrar a sinalização de parada. O documento
fecha esse flanco por instrução — orçamento de turnos declarado e curto na
trilha de entrevista, em vez do default do runtime, e sinalização isolada na
última linha da resposta.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
