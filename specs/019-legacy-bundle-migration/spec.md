# Feature Specification: Migração de bundles legados para o modelo projetado

**Feature Branch**: `feat/backlog-ssot`

**Created**: 2026-08-17

**Status**: Draft

**Input**: FASE-004 do work item `feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4`. Handoff canônico: `.grill/work-items/feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4/handoffs/FASE-004-SPECIFY-HANDOFF.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Um trabalho antigo entra no modelo novo (Priority: P1)

Um operador atualiza o plugin num repositório que já tem trabalhos. Os registros de decisão desses trabalhos foram escritos à mão e não existem na autoridade. Sem caminho de migração, esses registros ficariam órfãos: referenciados nos artefatos de plano e sem contraparte.

**Why this priority**: é a fase que fecha o ciclo. Sem ela, dois formatos de trabalho conviveriam para sempre e a inversão de autoridade valeria só para trabalhos novos.

**Independent Test**: rodar a migração sobre um trabalho autoral e conferir que cada decisão passou a existir na autoridade e que o registro virou projeção.

**Acceptance Scenarios**:

1. **Given** um trabalho no formato autoral, **When** o operador pede a prévia da migração, **Then** o sistema lista o que seria criado sem alterar nada.
2. **Given** o mesmo trabalho, **When** o operador autoriza, **Then** cada decisão vira item na autoridade e o registro passa a ser projeção marcada.
3. **Given** um trabalho já migrado, **When** a migração roda de novo, **Then** nada é criado nem alterado.
4. **Given** um trabalho já no modelo novo, **When** a migração roda, **Then** ela reporta que não há o que fazer.

---

### User Story 2 - O estado histórico sobrevive (Priority: P1)

As decisões dos trabalhos antigos estão quase todas encerradas. Migrar precisa preservar o estado que cada uma tinha.

**Why this priority**: uma migração que reabrisse decisões resolvidas reintroduziria trabalho concluído e poderia bloquear marcos já fechados.

**Independent Test**: migrar um trabalho com decisões resolvidas e substituídas e conferir o estado de cada item resultante.

**Acceptance Scenarios**:

1. **Given** uma decisão resolvida, **When** a migração é aplicada, **Then** o item nasce já no estado correspondente a resolvido.
2. **Given** uma decisão substituída, **When** a migração é aplicada, **Then** o item nasce já no estado correspondente a substituído.
3. **Given** uma decisão que já tem contraparte na autoridade, **When** a migração é aplicada, **Then** nenhuma segunda contraparte é criada.

---

### User Story 3 - Nada muta sem o operador mandar (Priority: P1)

Migrar cria itens no backlog do operador, que é compartilhado entre repositórios.

**Why this priority**: o contrato do componente que governa esse backlog exige confirmação explícita para qualquer mutação. Migração automática ao atualizar o plugin violaria isso.

**Independent Test**: rodar qualquer comando sobre um trabalho autoral e conferir que nada foi criado na autoridade sem autorização.

**Acceptance Scenarios**:

1. **Given** um trabalho autoral, **When** qualquer comando de leitura é executado, **Then** nada é criado na autoridade.
2. **Given** um trabalho autoral, **When** um comando que muta a projeção é executado sem migração prévia, **Then** ele recusa de forma nomeada.
3. **Given** um trabalho autoral, **When** um comando de leitura é executado, **Then** ele conclui e aponta a pendência, em vez de abortar.

---

### Edge Cases

- Trabalho autoral sem decisão alguma: migra para o modelo novo produzindo projeção vazia e marcada.
- Registro autoral com decisão cujo estado é inválido: recusa nomeada, sem migrar parcialmente aquele trabalho.
- Autoridade indisponível: recusa nomeada; a migração não pode ser feita offline porque precisa criar itens.
- Interrupção no meio: a reexecução reconhece o que já foi criado e completa, sem duplicar.
- Trabalho cujo registro tem decisão já presente na autoridade e outras não: só as ausentes são criadas.
- Repositório sem backlog vinculado: recusa, porque não há autoridade onde criar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O modo do registro de decisões MUST ser detectável, distinguindo autoral de projetado.
- **FR-002**: MUST existir um comando que migre um trabalho autoral para o modelo projetado.
- **FR-003**: A migração MUST ser prévia por padrão e MUST exigir autorização explícita para alterar qualquer coisa.
- **FR-004**: A migração MUST criar, na autoridade, uma contraparte para cada decisão que ainda não tenha uma.
- **FR-005**: Cada contraparte criada MUST nascer no estado correspondente ao estado histórico da decisão.
- **FR-006**: A migração MUST ser idempotente: reexecutar não cria nem altera nada.
- **FR-007**: Um trabalho já no modelo projetado MUST ser reportado como nada a fazer.
- **FR-008**: Depois de migrar, o registro MUST passar a ser projeção marcada, gerada da autoridade.
- **FR-009**: Comandos que mutam a projeção MUST recusar, de forma nomeada, sobre trabalho ainda autoral.
- **FR-010**: Comandos de leitura MUST concluir sobre trabalho autoral, apontando a pendência sem abortar.
- **FR-011**: Estado inválido no registro autoral MUST produzir recusa nomeada, sem migração parcial daquele trabalho.
- **FR-012**: A cobertura automatizada MUST exercitar todos os caminhos sem exigir a autoridade real instalada.

### Key Entities

- **Modo do registro**: autoral ou projetado.
- **Decisão histórica**: entrada do registro autoral, com estado já definido.
- **Contraparte**: item da autoridade que representa uma decisão.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Todo trabalho autoral é reconhecido como tal, e todo trabalho projetado também, sem falso positivo.
- **SC-002**: Migrar duas vezes o mesmo trabalho não cria nenhum item adicional.
- **SC-003**: Todo estado histórico é preservado na contraparte criada.
- **SC-004**: Nenhuma execução sem autorização explícita altera a autoridade.
- **SC-005**: Comandos de leitura concluem sobre trabalho autoral em 100% dos casos.
- **SC-006**: A suíte automatizada passa sem a autoridade instalada.

## Assumptions

- As três fases anteriores já operam: espelho, projeção e pré-requisito.
- O acervo real deste repositório, no momento desta fase, tem quatro trabalhos autorais, dos quais três têm decisões — quatro, duas e duas — e uma dessas oito já tem contraparte criada em fase anterior.
- A ausência da marca de origem é o sinal de modo autoral. A gate de auditoria já foi construída de forma condicional a esse sinal na fase da projeção, então nada precisa ser ligado aqui.
- Migração automática está descartada por contrato do componente que governa o backlog, que exige confirmação explícita para mutação.
- A migração não pode ser feita offline, porque precisa criar itens na autoridade. Isso a distingue da auditoria, que é deliberadamente offline.
