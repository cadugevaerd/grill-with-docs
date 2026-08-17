# Feature Specification: Projeção versionada e determinística das decisões

**Feature Branch**: `feat/backlog-ssot`

**Created**: 2026-08-17

**Status**: Draft

**Input**: FASE-002 do work item `feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4`. Handoff canônico: `.grill/work-items/feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4/handoffs/FASE-002-SPECIFY-HANDOFF.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - O registro de decisões deixa de ser escrito à mão (Priority: P1)

Um operador conduz uma sessão de decisão. Hoje ele escreve o registro de decisões adiadas à mão, e esse arquivo é a única fonte. Depois da FASE-001 o registro também vive no backlog operacional, e os dois podem divergir sem que nada perceba.

**Why this priority**: É a inversão de autoridade que dá nome ao trabalho. Enquanto o arquivo for autoral, existem duas fontes concorrentes para o mesmo fato e nenhuma regra dizendo qual vence.

**Independent Test**: Pedir a geração do registro num trabalho cujas decisões já estão no backlog e conferir que o conteúdo saiu da autoridade, não do que estava escrito antes.

**Acceptance Scenarios**:

1. **Given** um trabalho cujas decisões existem no backlog, **When** o operador pede a geração, **Then** o registro passa a refletir o que a autoridade diz, incluindo o estado de cada decisão.
2. **Given** o mesmo trabalho sem nenhuma mudança, **When** a geração é pedida de novo, **Then** o arquivo resultante é idêntico byte a byte ao anterior.
3. **Given** um trabalho cujo registro foi editado à mão depois da geração, **When** a verificação é executada, **Then** a edição é detectada e nomeada.

---

### User Story 2 - A auditoria continua funcionando em qualquer clone (Priority: P1)

Um revisor clona a branch para avaliar a mudança. A máquina dele não tem o backlog do autor, e o backlog que ele porventura tenha é outro, porque esse registro é global por máquina e compartilhado entre repositórios.

**Why this priority**: É a razão de a projeção existir. Se a auditoria precisar da autoridade para concluir, a evidência deixa de ser portátil e o trabalho volta ao problema que a decisão de arquitetura resolveu.

**Independent Test**: Executar a auditoria numa máquina sem o backlog instalado e obter um veredito, não uma recusa.

**Acceptance Scenarios**:

1. **Given** uma máquina sem o backlog instalado, **When** a auditoria é executada sobre um trabalho com registro gerado, **Then** ela conclui e emite veredito sem consultar processo externo.
2. **Given** o mesmo trabalho e o mesmo commit em duas máquinas diferentes, **When** a auditoria roda nas duas, **Then** o veredito é o mesmo.
3. **Given** um registro sem a marca de origem, **When** a auditoria é executada, **Then** ela reprova de forma nomeada, porque não pode confirmar que o arquivo é derivado.

---

### User Story 3 - Frescor é verificável sob demanda (Priority: P2)

Um operador quer saber se o registro versionado ainda corresponde ao que a autoridade diz. A auditoria deliberadamente não responde isso, então precisa existir um caminho explícito que responda.

**Why this priority**: Sem ele, o custo aceito na história 2 — um registro obsoleto passar no portão — não teria mitigação alguma. Não bloqueia as duas primeiras histórias, mas é o que torna o risco administrável.

**Independent Test**: Alterar uma decisão no backlog sem regenerar e pedir a verificação; ela precisa apontar a divergência.

**Acceptance Scenarios**:

1. **Given** um registro gerado e nada alterado desde então, **When** a verificação é executada com o backlog disponível, **Then** ela reporta que o registro está fresco.
2. **Given** uma decisão que mudou de estado no backlog após a geração, **When** a verificação é executada, **Then** ela reporta a divergência e diz qual decisão divergiu.
3. **Given** uma máquina sem o backlog disponível, **When** a verificação é executada, **Then** ela recusa de forma nomeada, em vez de afirmar frescor que não pode comprovar.

---

### Edge Cases

- Trabalho sem nenhuma decisão: a geração produz um registro válido e vazio, não um arquivo ausente, e a reexecução continua idêntica.
- Trabalho cujo backlog contém decisões de outros trabalhos: apenas as do trabalho corrente entram no registro.
- Decisão presente no registro e ausente da autoridade: a verificação aponta como divergência; a geração remove a entrada.
- Decisão presente na autoridade e ausente do registro: a verificação aponta; a geração acrescenta.
- Ordem em que a autoridade devolve as decisões muda entre duas execuções: o registro gerado não pode mudar por isso.
- Registro gerado sob um conjunto de decisões e depois um item é apagado à mão do backlog: a verificação aponta, sem tentar reparar sozinha.
- Interrupção durante a escrita do registro: o arquivo não pode ficar em estado meio escrito.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O registro de decisões adiadas MUST ser produzido a partir da autoridade, e não escrito à mão.
- **FR-002**: O registro MUST permanecer versionado no repositório, para servir de evidência no commit.
- **FR-003**: Duas gerações consecutivas sem mudança na autoridade MUST produzir arquivos idênticos byte a byte.
- **FR-004**: A ordem das entradas no registro MUST ser determinada por um critério estável do próprio conteúdo, nunca pela ordem em que a autoridade respondeu.
- **FR-005**: O registro MUST conter apenas decisões do trabalho corrente.
- **FR-006**: O registro MUST carregar uma marca que identifique a fatia de autoridade da qual foi derivado.
- **FR-007**: A marca MUST depender somente das decisões deste trabalho, de modo que mudança em decisão de outro trabalho, ou de outro repositório que compartilhe o mesmo registro, não a altere.
- **FR-008**: A auditoria MUST validar o registro sem consultar a autoridade e sem executar processo externo.
- **FR-009**: A auditoria MUST reprovar, de forma nomeada, um registro sem a marca de origem.
- **FR-010**: MUST existir um comando explícito que compare o registro com a autoridade e relate frescor ou divergência.
- **FR-011**: O comando de verificação MUST nomear cada decisão divergente e o tipo de divergência.
- **FR-012**: O comando de verificação MUST recusar de forma nomeada quando a autoridade não estiver disponível, em vez de afirmar frescor.
- **FR-013**: A escrita do registro MUST ser atômica, de modo que interrupção não deixe arquivo parcial.
- **FR-014**: A geração MUST ser a única forma suportada de alterar o registro; edição manual passa a ser detectável, não suportada.
- **FR-015**: A cobertura automatizada MUST exercitar todos os caminhos acima sem exigir a autoridade real instalada.

### Key Entities

- **Registro de decisões**: artefato versionado do trabalho, derivado da autoridade, que serve de evidência no commit.
- **Fatia de autoridade**: o subconjunto de decisões do backlog operacional que pertence a este trabalho.
- **Marca de origem**: valor gravado no registro que identifica a fatia de autoridade que o originou, estável contra mudança externa ao trabalho.
- **Divergência**: diferença entre o registro e a fatia de autoridade, por presença, ausência ou estado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Gerar duas vezes seguidas, sem mudança na autoridade, produz arquivos idênticos em 100% das execuções.
- **SC-002**: Reordenar a resposta da autoridade não altera nenhum byte do registro gerado.
- **SC-003**: Alterar uma decisão de outro trabalho não altera a marca de origem deste trabalho.
- **SC-004**: A auditoria conclui com veredito em máquina sem a autoridade instalada, em 100% dos casos.
- **SC-005**: O mesmo commit auditado em duas máquinas diferentes produz o mesmo veredito.
- **SC-006**: Toda divergência introduzida deliberadamente é apontada pela verificação, com a decisão nomeada.
- **SC-007**: Nenhuma interrupção durante a escrita deixa o registro em estado inválido.
- **SC-008**: A suíte automatizada completa passa sem a autoridade instalada.

## Assumptions

- O trabalho já está vinculado a um backlog e o espelho da FASE-001 já opera; esta fase consome esse resultado e não o refaz.
- A autoridade sobre o ciclo de vida das decisões é o backlog operacional, e a evidência no commit é este registro. A separação foi decidida em ADR-0001 e não é reaberta aqui.
- A auditoria não consulta a autoridade por decisão registrada em ADR-0002; o risco aceito é um registro obsoleto passar no portão, e o comando de verificação é a mitigação declarada.
- A marca de origem cobre apenas a fatia deste trabalho. O contador de revisão que o backlog mantém por registro não serve, porque avança a cada mudança em qualquer decisão, inclusive de outros repositórios que compartilham o mesmo armazenamento, o que produziria divergência falsa constante.
- Não há transação entre o armazenamento da autoridade e o sistema de arquivos. A garantia oferecida é convergência por regeneração, não atomicidade entre os dois.
- A migração dos registros hoje autorais para o formato derivado pertence a uma fase posterior e não acontece aqui.
- A verificação automatizada usa um substituto para a autoridade, pelo ponto de injeção existente, porque o ambiente de verificação não tem o binário real.
