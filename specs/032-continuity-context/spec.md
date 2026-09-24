# Feature Specification: Continuidade de contexto sem líder vivo

**Feature Branch**: `cadugevaerd/feat-new-subagents`

**Created**: 2026-09-19

**Status**: Draft

**Input**: Handoff `FASE-001-SPECIFY-HANDOFF.md` do work item `fix-continuity-context-2babd3080cc84b59a4404d6514f948c2`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assumir um work item cujo condutor anterior encerrou (Priority: P1)

Quem perde a sessão que conduzia um work item — porque ela terminou, caiu ou foi fechada — abre uma sessão nova, pede a tomada do trabalho e volta a conduzir o ciclo com a própria identidade, sem perder decisões, receipts, campanha nem escopo já registrados.

**Why this priority**: hoje esse work item fica inalcançável para sempre, e é o que bloqueia a metade Codex da matriz de estilo do work item de origem.

**Independent Test**: registrar um contexto cujo condutor esteja comprovadamente encerrado, pedir a tomada por uma sessão nova e verificar que o trabalho segue, com o registro mostrando a sucessão.

**Acceptance Scenarios**:

1. **Given** um work item cujo condutor anterior está comprovadamente encerrado, **When** uma sessão nova pede a tomada, **Then** a tomada é aceita, o contexto anterior fica encerrado, o novo assume com a época seguinte e o estado técnico permanece idêntico.
2. **Given** a mesma situação, **When** a tomada é repetida com a mesma entrada, **Then** o resultado é o mesmo e nada é duplicado.
3. **Given** uma tomada aceita, **When** o registro de contexto é auditado, **Then** ele mostra quem entregou, quem assumiu e o motivo.

---

### User Story 2 - Recusar tomada sem prova (Priority: P1)

Quem pede a tomada de um work item cujo condutor ainda pode estar vivo é recusado, e a recusa diz o que falta.

**Why this priority**: dois condutores simultâneos quebrariam a garantia que todo o mecanismo existe para dar.

**Independent Test**: variar a evidência sobre o condutor anterior e confirmar que só o encerramento comprovado autoriza.

**Acceptance Scenarios**:

1. **Given** o condutor anterior ainda ativo, **When** a tomada é pedida, **Then** é recusada e o trabalho continua com o condutor atual.
2. **Given** que a consulta sobre o condutor anterior não conclui — sem resposta, resposta parcial ou ambígua, **When** a tomada é pedida, **Then** é recusada por ausência de prova, com código próprio.
3. **Given** um condutor anterior que nunca foi um trabalho observável, **When** a tomada é pedida, **Then** é recusada com código próprio que nomeia esse limite.

---

### User Story 3 - Preparar a troca desde a criação do work item (Priority: P1)

Quem quer passar o trabalho a outra sessão consegue preparar a troca ordenada a qualquer momento, inclusive antes de qualquer etapa do ciclo ter sido confirmada.

**Why this priority**: é o caminho preferido, e hoje ele só existe depois da primeira etapa confirmada, o que deixa a janela inicial descoberta.

**Independent Test**: criar um work item, preparar a troca imediatamente e retomar por ela em outra sessão.

**Acceptance Scenarios**:

1. **Given** um work item recém-criado, sem nenhuma etapa confirmada, **When** a troca é preparada, **Then** ela é aceita e produz o ponto de retomada.
2. **Given** essa preparação, **When** outra sessão retoma por ela, **Then** assume o trabalho com o estado preservado.

---

### User Story 4 - Prévia que diz a verdade (Priority: P2)

Quem pede a prévia de uma adoção recebe o mesmo veredito que o comando efetivo daria.

**Why this priority**: uma prévia que promete sucesso e depois recusa custa tempo e confiança.

**Independent Test**: pedir a prévia diante de um contexto de outra sessão e comparar com o resultado do comando efetivo.

**Acceptance Scenarios**:

1. **Given** um contexto pertencente a outra sessão, **When** a prévia é pedida, **Then** ela devolve a mesma recusa que o comando efetivo devolveria, sem escrever nada.
2. **Given** um contexto compatível, **When** a prévia é pedida, **Then** ela descreve o que o comando efetivo faria, sem escrever nada.

---

### User Story 5 - Registro honesto do ponto de retomada (Priority: P2)

Quem audita um ponto de retomada encontra campos cujo nome corresponde ao conteúdo, e pontos criados antes desta entrega continuam utilizáveis.

**Why this priority**: o registro é evidência; nome que engana desfaz o propósito.

**Independent Test**: criar um ponto de retomada novo e conferir os nomes; retomar por um ponto antigo e confirmar que funciona.

**Acceptance Scenarios**:

1. **Given** um ponto de retomada criado após esta entrega, **When** ele é lido, **Then** cada campo de digest tem nome correspondente ao valor que carrega.
2. **Given** um ponto de retomada criado antes desta entrega, **When** uma sessão retoma por ele, **Then** a retomada funciona e nada é reescrito nem re-selado.

---

### Edge Cases

- Tomada pedida enquanto existe atividade de especialista em andamento no work item: recusa, porque o trabalho não está quiescente.
- Duas sessões pedem a tomada ao mesmo tempo: no máximo uma assume; a outra recebe recusa por estado alterado.
- Consulta ao condutor anterior responde encerramento e, na sequência, o trabalho reaparece: a época nova e o registro de sucessão tornam a divergência visível, e a autoridade fica com quem assumiu.
- Retomada por um ponto de retomada já consumido: recusa, como hoje.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que uma sessão nova assuma um work item quando o encerramento do condutor anterior estiver provado por observação do ambiente que hospeda o trabalho, e não por declaração de quem pede.
- **FR-002**: O sistema DEVE recusar a tomada quando o condutor anterior estiver ativo, quando a observação não concluir, e quando o condutor anterior não for um trabalho observável; cada caso DEVE ter código de recusa próprio e distinto.
- **FR-003**: A tomada DEVE ser prévia por padrão, exigir confirmação explícita da entrada relida para efetivar e ser idempotente para a mesma entrada.
- **FR-004**: A tomada DEVE registrar a sucessão de forma auditável: identificação do contexto anterior e de quem o conduzia, identificação do contexto novo e da época seguinte, o motivo, a referência e o digest da observação que serviu de prova, e o instante da tomada.
- **FR-005**: A tomada NÃO DEVE alterar estado do ciclo, campanha, resultados já aceitos nem escopo declarado do work item.
- **FR-006**: O sistema DEVE permitir preparar a troca ordenada mesmo quando nenhuma etapa do ciclo foi confirmada, produzindo um ponto de retomada a partir do estado corrente.
- **FR-007**: A prévia da adoção DEVE aplicar as mesmas verificações do comando efetivo e devolver a mesma recusa quando houver, sem escrever nada.
- **FR-008**: Os campos de digest do ponto de retomada DEVEM ter nomes que correspondam ao conteúdo que carregam, e a mudança DEVE vir em versão nova do formato.
- **FR-009**: Pontos de retomada criados antes desta entrega DEVEM continuar válidos e utilizáveis, sem reescrita, migração ou nova selagem.
- **FR-010**: O sistema NÃO DEVE recusar por ausência de prova sem dizer qual prova faltou.
- **FR-011**: A validação automatizada DEVE cobrir os cenários das histórias 1 a 5 sem depender de runtime real, rede ou processo externo.
- **FR-012**: A entrega DEVE incrementar a versão do plugin de 6.0.2 para 6.0.3 em todos os pontos de versão do contrato de distribuição e publicar a release correspondente.

### Key Entities

- **Contexto de orquestração**: registro, por work item, de quem conduz, em que época, com que atividades e pontos de retomada.
- **Observação de condutor**: conjunto de identificadores do condutor produzido a partir do trabalho vivo; é o que hoje precisa ser idêntico para a continuidade ser aceita.
- **Ponto de retomada**: documento imutável que carrega o estado necessário para outra sessão continuar.
- **Tomada de contexto**: ato explícito que encerra o contexto anterior e abre a época seguinte sob outro condutor.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos work items cujo condutor está comprovadamente encerrado voltam a ser trabalháveis por uma sessão nova, contra 0% hoje.
- **SC-002**: 100% das tentativas sem prova suficiente (condutor ativo, observação inconclusiva, condutor não observável) continuam recusadas, cada uma com seu código.
- **SC-003**: A troca ordenada é possível em 100% dos work items, inclusive no instante seguinte à criação, contra 0% antes da primeira etapa confirmada.
- **SC-004**: Zero divergências entre o veredito da prévia de adoção e o do comando efetivo, nos mesmos insumos.
- **SC-005**: 100% dos pontos de retomada criados antes desta entrega continuam utilizáveis, sem reescrita.
- **SC-006**: A suíte completa de validadores do projeto passa sem nenhum validador desativado ou afrouxado.
- **SC-007**: Reexecutado o caso de retomada da matriz de estilo do work item de origem, uma sessão nova retoma o trabalho criado por outra. Essa evidência pertence ao work item de origem e não é critério de aceite desta entrega.

## Assumptions

- O ambiente que hospeda o trabalho distingue, de forma observável, trabalho vivo de trabalho encerrado, e o sistema já consome essa distinção em outro ponto do fluxo (ADR-0001 do work item).
- A comparação, na retomada, dos digests do documento de workflow e da Constituição fica fora desta entrega (BL-0001).
- A versão publicada corrente é 6.0.2.
- Observação de compactação e de suspensão de estilo pertence a outro work item.
