# Feature Specification: Virada de fase auditada

**Feature Branch**: `004-phase-turn`

**Created**: 2026-08-12

**Status**: Draft

**Input**: Handoff `.grill/work-items/fix-high-defects-f03b31bb4b194b0683eee8f3a62493d0/handoffs/FASE-001-SPECIFY-HANDOFF.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A segunda fase de um work item consegue começar (Priority: P1)

Quem conduz um work item com roteiro de várias fases termina a primeira e começa a segunda, sem editar arquivo de estado à mão.

**Why this priority**: É o objetivo inteiro. Hoje não existe caminho: concluída a primeira fase, a matriz fica cheia e a transição seguinte é recusada por construção.

**Independent Test**: Rodar um ciclo completo de 11 passos, pedir a virada, e iniciar o primeiro passo da fase seguinte.

**Acceptance Scenarios**:

1. **Given** um work item com todos os 11 passos concluídos, **When** a virada é pedida com razão, **Then** o registro de progresso volta ao início e o primeiro passo da fase seguinte pode ser iniciado.
2. **Given** a virada aplicada, **When** a trilha é lida, **Then** ela permite reconstruir por quais passos a fase encerrada passou.

---

### User Story 2 - A virada é recusada quando destruiria progresso (Priority: P1)

Pedir a virada no meio de uma fase não apaga o que já foi feito.

**Why this priority**: Um reset que aceita rodar a qualquer momento troca um travamento por perda silenciosa de estado, o que é pior — o travamento é visível, a perda não.

**Independent Test**: Pedir a virada com a fase em andamento e observar recusa, com o estado intacto.

**Acceptance Scenarios**:

1. **Given** uma fase com passos ainda pendentes ou em andamento, **When** a virada é pedida, **Then** ela é recusada e nenhum passo muda de estado.
2. **Given** uma virada recusada, **When** a trilha é lida, **Then** a recusa não deixou entrada, porque nada transicionou.

---

### User Story 3 - Quem esbarra na recusa descobre a saída (Priority: P2)

Quem tentar iniciar a fase seguinte sem virar recebe uma recusa que diz o que fazer.

**Why this priority**: É o que impede o defeito de voltar disfarçado. Sem isso, o operador que esquecer a virada vê exatamente o erro de hoje e conclui que o problema continua.

**Independent Test**: Com os 11 passos concluídos, tentar iniciar o primeiro passo sem virar e ler a saída.

**Acceptance Scenarios**:

1. **Given** todos os passos concluídos, **When** o primeiro passo é iniciado sem virada prévia, **Then** a recusa nomeia a virada como caminho.

---

### Edge Cases

- Virada sem razão declarada: recusada, porque a razão é o que torna a transição auditável.
- Virada pedida duas vezes seguidas sem trabalho no meio: a segunda não produz mudança.
- Virada num work item de fase única, já concluído: permitida, e o resultado é um registro pronto para uma fase que talvez nunca venha; não há como saber daqui quantas fases o roteiro terá.
- Work item cujo registro de progresso nunca foi iniciado: a virada não é o caminho; não há o que virar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST oferecer uma operação explícita que devolva o registro de progresso ao estado inicial.
- **FR-002**: A operação MUST exigir razão declarada e MUST registrá-la na trilha, junto com a transição.
- **FR-003**: A operação MUST ser recusada enquanto houver passo não concluído, sem alterar estado algum.
- **FR-004**: A operação MUST ser idempotente: aplicada sobre um registro já reiniciado, não produz mudança.
- **FR-005**: A recusa de iniciar um passo cujo registro já está concluído MUST nomear a operação de virada.
- **FR-006**: A operação MUST NOT alterar a forma do arquivo de estado, de modo que nenhum work item existente precise de migração.
- **FR-007**: A trilha MUST permitir reconstruir, depois da virada, por quais passos a fase encerrada passou.

### Key Entities

- **Registro de progresso**: o mapa dos 11 passos com o estado corrente de cada um. Vive por work item.
- **Trilha**: a lista append-only de transições, com passo, estado, razão e evidência. É o histórico.
- **Virada**: a transição que encerra uma fase e devolve o registro de progresso ao início.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um work item de três fases completa as três com registro por passo em cada uma, sem edição manual de estado.
- **SC-002**: Nenhum work item existente precisa ser migrado, e o que já foi projetado no global continua válido.
- **SC-003**: Uma virada pedida no meio da fase não altera nenhum estado.
- **SC-004**: A recusa por registro concluído indica a operação de virada em sua mensagem.
- **SC-005**: A trilha, lida após duas viradas, distingue as três fases.

## Assumptions

- A trilha já é append-only e já cobre todos os passos: 22 entradas no work item anterior, para 11 passos de uma fase. É isso que permite reiniciar o registro sem perder histórico.
- O work item `feature-release-repo-sync-97a2bb32d4884a129ec2e845b76894b7` está terminal e projetado no global, com recibo determinístico. Qualquer mudança que o invalide quebra a projeção — daí FR-006.
- A distinção entre fases dentro da trilha vem da razão declarada em cada virada, não de um campo de fase. Introduzir um campo de fase seria mudança de forma, excluída por FR-006.
