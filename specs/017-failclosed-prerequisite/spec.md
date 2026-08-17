# Feature Specification: Pré-requisito fail-closed do backlog operacional

**Feature Branch**: `feat/backlog-ssot`

**Created**: 2026-08-17

**Status**: Draft

**Input**: FASE-003 do work item `feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4`. Handoff canônico: `.grill/work-items/feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4/handoffs/FASE-003-SPECIFY-HANDOFF.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - O pré-requisito passa a valer (Priority: P1)

Um operador instala o plugin num repositório novo e cria um trabalho. Hoje o backlog operacional é anunciado como pré-requisito e não é exigido: é a única dependência declarada opcional, e a vinculação só acontece sob uma autorização que raramente é passada. O resultado é um repositório que parece configurado e nunca fica vinculado.

**Why this priority**: é a razão de ser da fase. Enquanto a exigência viver só no discurso, todo o trabalho das fases anteriores continua opcional na prática.

**Independent Test**: criar um trabalho num repositório sem backlog vinculado e obter recusa nomeada em vez de sucesso.

**Acceptance Scenarios**:

1. **Given** um repositório sem backlog vinculado, **When** o operador cria um trabalho, **Then** o sistema recusa de forma nomeada e não cria o trabalho.
2. **Given** um repositório com backlog vinculado, **When** o operador cria um trabalho, **Then** a criação prossegue normalmente.
3. **Given** um relatório de ambiente, **When** o operador o consulta, **Then** o backlog aparece como exigido, não como opcional.

---

### User Story 2 - A saída explícita continua existindo e fica visível (Priority: P1)

Um operador precisa criar um trabalho num ambiente que não tem o backlog: verificação automatizada, máquina isolada, ou avaliação inicial do plugin.

**Why this priority**: sem a saída, a exigência quebra a verificação automatizada do próprio projeto e todo consumidor que crie trabalho em ambiente sem o backlog. Com ela mas sem registro, um trabalho criado pela saída fica indistinguível de um conforme, e o portão passa a mentir sobre o próprio pré-requisito.

**Independent Test**: criar um trabalho com a saída explícita e conferir que o trabalho carrega o registro de que ela foi usada.

**Acceptance Scenarios**:

1. **Given** um ambiente sem o backlog, **When** o operador cria um trabalho com a saída explícita, **Then** a criação prossegue e o uso fica registrado no trabalho.
2. **Given** um trabalho criado com a saída explícita, **When** a auditoria é executada, **Then** ela não concede aprovação enquanto o backlog não for vinculado.
3. **Given** um trabalho criado normalmente, **When** a auditoria é executada, **Then** o registro da saída está ausente e nada é impedido por ele.

---

### Edge Cases

- Backlog instalado mas repositório não vinculado: recusa, porque a exigência é de vínculo e não só de presença do binário.
- Backlog vinculado e depois desvinculado: a criação de um trabalho novo recusa; trabalhos já existentes não são invalidados retroativamente.
- Saída explícita usada num ambiente que **tem** o backlog: permitida e registrada do mesmo jeito, porque o registro descreve como o trabalho foi criado, não o que a máquina tinha.
- Desligamento global de detecção de dependências: continua não sendo reportado como conforme, e não substitui a saída explícita.
- Trabalho criado com a saída explícita e depois vinculado ao backlog: precisa existir caminho para limpar o registro, senão o trabalho fica permanentemente bloqueado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O backlog operacional MUST ser declarado dependência exigida, e não opcional.
- **FR-002**: A contagem de dependências faltantes MUST incluir o backlog quando ele estiver ausente.
- **FR-003**: A criação de um trabalho MUST recusar, de forma nomeada, quando não houver backlog resolvido e vinculado.
- **FR-004**: A vinculação MUST deixar de depender da autorização de instalação para acontecer.
- **FR-005**: MUST existir exatamente uma saída explícita que permita criar um trabalho sem o backlog.
- **FR-006**: O uso da saída MUST ficar registrado no próprio trabalho.
- **FR-007**: Um trabalho que carregue o registro da saída MUST ter esse registro reportado em toda auditoria, sem possibilidade de silenciá-lo. O registro **não** bloqueia a aprovação por si só: bloquear tornaria inauditável todo trabalho criado em ambiente isolado ou em verificação automatizada, que é falha pior do que a prevenida.
- **FR-008**: MUST existir um caminho para remover o registro da saída depois que o backlog for vinculado, para que o trabalho não fique bloqueado para sempre.
- **FR-009**: O desligamento global de detecção de dependências MUST NOT ser reportado como conforme e MUST NOT substituir a saída explícita.
- **FR-010**: A cobertura automatizada MUST exercitar a recusa e a saída sem exigir o backlog real instalado.

### Key Entities

- **Dependência exigida**: item do preflight cuja ausência entra na contagem de faltantes.
- **Vínculo**: correspondência entre o repositório e um backlog do armazenamento.
- **Registro da saída**: marca gravada no trabalho dizendo que ele foi criado sem backlog vinculado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Criar um trabalho sem backlog vinculado recusa em 100% dos casos, sem traceback.
- **SC-002**: O relatório de ambiente lista o backlog como exigido, e sua ausência aparece na contagem de faltantes.
- **SC-003**: Todo trabalho criado pela saída explícita carrega o registro, sem exceção.
- **SC-004**: Todo trabalho com o registro presente tem o registro visível na saída da auditoria, em 100% dos vereditos que chegam a montar o envelope.
- **SC-005**: Depois de vincular o backlog e limpar o registro, o mesmo trabalho alcança aprovação.
- **SC-006**: A suíte automatizada completa passa sem o backlog instalado.

## Assumptions

- A ponte e a projeção das fases anteriores já operam; esta fase só torna o pré-requisito exigível.
- A cláusula constitucional proíbe waiver **implícito**. Uma saída nomeada, versionada e registrada no trabalho não é implícita, e há precedente no projeto para uma opção de desligamento que nunca é reportada como conforme.
- Remover a saída por completo foi descartado: quebraria a verificação automatizada do próprio projeto e todo consumidor que crie trabalho em ambiente sem o backlog.
- Esta é a mudança que torna o marco incompatível com consumidores existentes, porque a criação passa a recusar onde antes prosseguia.
- Trabalhos criados antes desta fase não são invalidados; a exigência vale para criação nova.
