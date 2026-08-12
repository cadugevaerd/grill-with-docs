# Feature Specification: Gate de bump bloqueante

**Feature Branch**: `006-bump-gate-required`

**Created**: 2026-08-12

**Status**: Draft

**Input**: Handoff `.grill/work-items/fix-high-defects-f03b31bb4b194b0683eee8f3a62493d0/handoffs/FASE-003-SPECIFY-HANDOFF.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A verificação se pronuncia em toda proposta (Priority: P1)

Quem propõe qualquer mudança recebe veredito da verificação de versão, mesmo quando a proposta não toca o conteúdo distribuído.

**Why this priority**: É o que permite exigir a verificação sem prender propostas. Hoje ela cala nas que não casam o filtro, e exigir uma verificação que cala trava essas propostas para sempre.

**Independent Test**: Abrir proposta que muda só documentação e observar veredito presente.

**Acceptance Scenarios**:

1. **Given** proposta que não altera o conteúdo distribuído, **When** a verificação roda, **Then** ela aprova por não haver o que exigir, e o veredito vem de execução real.
2. **Given** proposta que altera o conteúdo distribuído sem subir a versão, **When** a verificação roda, **Then** ela reprova.
3. **Given** proposta que altera o conteúdo distribuído com a versão subida, **When** a verificação roda, **Then** ela aprova.

---

### User Story 2 - A bateria cara continua restrita (Priority: P1)

A matriz de portabilidade continua rodando apenas quando o que ela cobre muda.

**Why this priority**: Fazer a verificação sempre se pronunciar não pode custar rodar quatro jobs em toda proposta de documentação. Seria desfazer a deduplicação recém-entregue.

**Independent Test**: Proposta que muda só documentação não aciona a matriz.

**Acceptance Scenarios**:

1. **Given** proposta que muda só documentação, **When** os workflows são avaliados, **Then** a matriz de portabilidade não roda e a verificação de versão roda.

---

### Edge Cases

- Aprovação por ausência de execução: proibida. Aprovado tem de significar verificado.
- Proposta que toca conteúdo distribuído e documentação junto: a verificação roda e a matriz também.
- Merge na linha principal: a verificação é de proposta e não se pronuncia ali; a matriz segue a regra de deduplicação já vigente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A verificação de versão MUST reportar veredito em toda proposta, independentemente dos caminhos alterados.
- **FR-002**: O veredito MUST vir de execução real; aprovação por workflow pulado é proibida.
- **FR-003**: A bateria de portabilidade MUST continuar restrita aos caminhos que a justificam.
- **FR-004**: A verificação MUST continuar comparando contra a base da proposta, e não contra nome de ramo.
- **FR-005**: A verificação MUST continuar exigindo histórico suficiente para encontrar a base de comparação.
- **FR-006**: A configuração que transforma a reprovação em bloqueio MUST ser declarada para quem administra o repositório, por ser ato externo ao código.

### Key Entities

- **Verificação de versão**: o gate que exige subir a versão quando o conteúdo distribuído muda.
- **Bateria de portabilidade**: a matriz de sistemas e versões de linguagem.
- **Filtro de caminhos**: declaração no nível do workflow que decide se ele roda.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Proposta que muda só documentação recebe veredito da verificação de versão.
- **SC-002**: A mesma proposta não aciona a bateria de portabilidade.
- **SC-003**: Proposta que altera o conteúdo distribuído sem subir a versão é reprovada.
- **SC-004**: Nenhum veredito de aprovação é produzido sem execução.
- **SC-005**: O que precisa ser exigido no repositório está declarado por escrito.

## Assumptions

- Filtros de caminho são declarados no nível do workflow, não do job. Um workflow pulado não reporta status algum, e é por isso que a verificação precisa sair do workflow que carrega a matriz.
- A verificação já responde que nada é exigido quando o conteúdo distribuído não muda, então rodá-la sempre produz aprovação real, não simulada.
- A verificação custa segundos; a matriz custa quatro jobs, um deles no runner mais caro.
- Registrar a verificação como obrigatória na proteção da linha principal é ato humano no serviço, fora do alcance de qualquer commit.
