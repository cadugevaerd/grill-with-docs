# Feature Specification: Suspensão e reativação da apresentação local no core

**Feature Branch**: `cadugevaerd/feat-new-subagents`

**Created**: 2026-09-24

**Status**: Draft

**Input**: Handoff `FASE-001-SPECIFY-HANDOFF.md` do work item `fix-presentation-suspension-d97e4c3d7b434c119477ec59d56ecbd5`; decisões ADR-0001, ADR-0002 e ADR-0003 do mesmo work item

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Suspender a apresentação e continuar trabalhando (Priority: P1)

Quem conduz um fluxo GWD diz `stop adhd mode` e segue trabalhando sem a apresentação local, inclusive depois de compactar o contexto da sessão. O fluxo deixa de pedir a recarga da referência de apresentação enquanto a suspensão vale.

**Why this priority**: hoje a frase não tem efeito verificável; depois de compactar, o fluxo exige justamente a recarga que a suspensão proíbe, e só a disciplina da sessão evita violar o contrato.

**Independent Test**: registrar uma sessão com a frase dita pelo usuário, antes e depois de uma compactação, e verificar que o estado de apresentação exposto libera o trabalho sem pedir recarga.

**Acceptance Scenarios**:

1. **Given** uma sessão com apresentação ativa, **When** o usuário diz `stop adhd mode`, **Then** a apresentação fica suspensa, o trabalho segue liberado e nenhuma recarga é pedida.
2. **Given** uma sessão suspensa, **When** o contexto é compactado na mesma sessão, **Then** a apresentação continua suspensa, o trabalho segue liberado e nenhuma recarga é pedida.
3. **Given** uma suspensão aceita, **When** o estado de apresentação é auditado, **Then** ele identifica a mensagem de usuário que originou a suspensão.

---

### User Story 2 - Reativar a apresentação na mesma sessão (Priority: P1)

Quem suspendeu diz `start adhd mode` e a apresentação volta ao padrão ativo, com nova leitura integral da referência antes do uso.

**Why this priority**: o contrato promete reativação explícita; sem ela, a única volta seria abrir outra sessão.

**Independent Test**: registrar uma suspensão seguida da frase de reativação e verificar que o estado volta a ativo e exige leitura antes do uso.

**Acceptance Scenarios**:

1. **Given** uma sessão suspensa, **When** o usuário diz `start adhd mode`, **Then** a apresentação volta a ativa e o uso só é liberado depois de uma leitura integral posterior à reativação.
2. **Given** várias alternâncias entre as duas frases, **When** o estado é calculado, **Then** vale a frase mais recente dita pelo usuário.

---

### User Story 3 - Ignorar frases que não vêm do usuário (Priority: P1)

A frase dita pelo próprio agente, ou presente apenas no resumo gerado por uma compactação, não muda o estado da apresentação.

**Why this priority**: sem isso, o agente poderia suspender a si mesmo por autorrelato, o que o contrato proíbe.

**Independent Test**: registrar sessões com a frase apenas em fala do agente e apenas em resumo de compactação, e verificar que a apresentação segue ativa.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa, **When** a frase aparece só em fala do agente, **Then** nada muda.
2. **Given** uma sessão ativa, **When** a frase aparece só no resumo de uma compactação, **Then** nada muda.

---

### User Story 4 - Atualizar o plugin ou a configuração durante a suspensão (Priority: P2)

Com a apresentação suspensa, uma atualização do plugin ou mudança de configuração da sessão não trava o fluxo; a leitura da versão nova acontece quando o usuário reativar.

**Why this priority**: hoje essa combinação trava o trabalho pedindo a leitura que a suspensão proíbe; é menos frequente que as histórias P1.

**Independent Test**: registrar uma sessão suspensa, mudar a configuração observada e verificar que o fluxo segue suspenso e liberado.

**Acceptance Scenarios**:

1. **Given** uma sessão suspensa, **When** o plugin ou a configuração da sessão mudam, **Then** a apresentação segue suspensa e o trabalho liberado, com o estado novo registrado.
2. **Given** uma sessão suspensa, **When** mudam a sessão, o runtime, o escopo ou a política, **Then** a recusa por conflito de escopo continua como hoje.

---

### User Story 5 - Compactação sem suspensão continua exigindo leitura (Priority: P2)

Sem suspensão, depois de compactar, a leitura anterior à compactação não conta, como já acontece; o marcador nativo de compactação dos dois runtimes é reconhecido.

**Why this priority**: garante que a mudança não afrouxa o caso padrão e fecha a lacuna de teste do marcador nativo.

**Independent Test**: registrar uma sessão ativa com leitura seguida de compactação, com o marcador no formato real de cada runtime, e verificar que a recarga é exigida.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa que leu a referência e depois compactou, **When** o estado é calculado, **Then** a leitura anterior não conta e uma nova leitura é exigida.
2. **Given** o marcador de compactação no formato real do Claude Code e no do Codex, **When** a sessão é observada, **Then** ambos são reconhecidos como compactação.

---

### Edge Cases

- Nova sessão, troca de runtime ou de incarnation: começa ativa e não herda suspensão.
- Frase com espaços extras ao redor: reconhecida; frase com outro texto na mesma mensagem: não reconhecida.
- Sessão despachada por coordenador de agentes: a mensagem de usuário recebida pelo worker conta como fonte não-agente da sessão (ADR-0001).
- Suspensão dita antes da primeira leitura da sessão: suspende sem exigir leitura.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST reconhecer `stop adhd mode` como suspensão somente quando dito em mensagem de usuário da própria sessão, com a frase como conteúdo único da mensagem.
- **FR-002**: Com suspensão vigente, o sistema MUST liberar o trabalho, marcar o uso da apresentação como indisponível e não pedir recarga, antes e depois de compactação na mesma sessão, incarnation e escopo.
- **FR-003**: O sistema MUST reconhecer `start adhd mode`, nas mesmas condições de fonte, como reativação quando posterior à última suspensão; após a reativação, o uso só é liberado com leitura integral posterior a ela.
- **FR-004**: O sistema MUST ignorar as duas frases quando vierem de fala do agente, de resumo de compactação ou de mensagem sintética.
- **FR-005**: O registro de suspensão MUST identificar a mensagem de origem e a sessão, configuração e escopo em que foi observada.
- **FR-006**: Nenhum verbo MUST aceitar suspensão informada pelo chamador; a suspensão só é produzida a partir da observação da sessão.
- **FR-007**: Com suspensão vigente na mesma sessão e escopo, mudança de configuração ou de versão do GWD MUST NOT exigir leitura; o estado novo é registrado mantendo a suspensão. Mudança de sessão, runtime, escopo ou política MUST continuar recusada como hoje.
- **FR-008**: Sem suspensão, leituras anteriores ao último marcador de compactação MUST continuar sem valor, com o marcador nativo do Claude Code e do Codex reconhecido.
- **FR-009**: Nova sessão, runtime ou incarnation MUST começar com apresentação ativa, sem herdar suspensão.
- **FR-010**: Nenhum código de recusa existente MUST mudar de significado.
- **FR-011**: Toda validação desta entrega MUST rodar sem runtime real, rede ou processo externo, com eventos no formato real do harness.

### Key Entities

- **Estado de apresentação**: aplicação (ativa ou suspensa pelo usuário), prontidão para trabalho e para uso, pedido de leitura e registro de suspensão.
- **Registro de suspensão**: comando, referência da mensagem de origem, digest do texto, sessão, configuração e escopo.
- **Marcador de compactação**: evento nativo da sessão que invalida leituras anteriores.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os sete cenários do handoff passam em validação automatizada, 7 de 7.
- **SC-002**: Em 100% dos casos de teste com a frase fora de mensagem de usuário, o estado de apresentação não muda.
- **SC-003**: Uma sessão suspensa atravessa compactação e mudança de configuração sem nenhuma recusa de leitura.
- **SC-004**: A suíte completa do projeto termina sem falhas e o diff fica limpo.

## Assumptions

- A frase é comparada exatamente, após remover apenas espaços nas pontas; variações de caixa ou texto adicional não contam.
- A mensagem de usuário recebida por um worker despachado conta como fonte não-agente da sessão; o coordenador pode suspender a apresentação de um worker (consequência declarada no ADR-0001).
- Conformidade das respostas do modelo (achado F1) e reexecução da matriz T029 ficam fora desta entrega.
- A versão publicada no momento do ship determina o bump patch, nos oito pontos de versão, com a release correspondente.
