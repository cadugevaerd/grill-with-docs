# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Estado do ciclo de desenvolvimento
- module-kind: platform
- responsibility: Registrar em que passo e em que fase o work item está, e provar a trajetória
- boundary: `state.json` sob `development`, e os leitores desse estado
- depends-on: none

### DU-001 — Virada de fase auditada
- development-type: platform-devops
- phase: FASE-001
- scope-in: Comando de virada, razão obrigatória, transição registrada na trilha, erro de transição inválida apontando a saída
- scope-out: Schema do estado, migração de bundles, re-pino de identidade
- depends-on: none
- acceptance: A segunda fase de um work item multi-fase inicia sem edição manual, e a trilha registra a virada

### DU-002 — Deriva viva precisa
- development-type: platform-devops
- phase: FASE-002
- scope-in: Separação das duas comparações do pino, supressão do finding insatisfazível, escopo do finding restante ao work item não terminal
- scope-out: Alteração do pino ou do hash que o protege
- depends-on: DU-001
- acceptance: Um work item multi-commit em seu próprio branch não produz finding; lido de outro branch durante o trabalho, produz

## MOD-002 — Gates de integração
- module-kind: platform
- responsibility: Impedir que conteúdo distribuído chegue à linha principal sem a versão que o identifica
- boundary: Workflows de CI e a configuração de branch protection que os torna bloqueantes
- depends-on: none

### DU-003 — Gate de bump bloqueante
- development-type: platform-devops
- phase: FASE-003
- scope-in: Gate em workflow próprio sem filtro de paths; prova de que reporta em PR que hoje pula o workflow
- scope-out: Filtro da matriz de portabilidade; o ato humano de marcar o check como required
- depends-on: DU-001
- acceptance: O check reporta veredito em toda PR, incluindo as que só tocam documentação, e o veredito reflete execução real

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
