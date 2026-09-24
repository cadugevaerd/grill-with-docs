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

1. **Given** uma sessão com apresentação ativa e instalação, compatibilidade, habilitação e confiança comprovadas, **When** o usuário diz `stop adhd mode`, **Then** a apresentação fica suspensa, o trabalho segue liberado e nenhuma recarga é pedida.
2. **Given** uma sessão suspensa, **When** o contexto é compactado na mesma sessão, **Then** a apresentação continua suspensa, o trabalho segue liberado e nenhuma recarga é pedida.
3. **Given** uma suspensão aceita, **When** o estado de apresentação é auditado, **Then** ele identifica a mensagem de usuário que originou a suspensão.
4. **Given** uma suspensão válida, **When** o plugin de apresentação está desabilitado, ausente ou sem confiança comprovada, **Then** o trabalho não é liberado e o diagnóstico nomeia o pré-requisito que falta.

---

### User Story 2 - Reativar a apresentação na mesma sessão (Priority: P1)

Quem suspendeu diz `start adhd mode` e a apresentação volta ao padrão ativo, com nova leitura integral da referência antes do uso.

**Why this priority**: o contrato promete reativação explícita; sem ela, a única volta seria abrir outra sessão.

**Independent Test**: registrar uma suspensão seguida da frase de reativação e verificar que o estado volta a ativo e exige leitura antes do uso.

**Acceptance Scenarios**:

1. **Given** uma sessão suspensa, **When** o usuário diz `start adhd mode`, **Then** a apresentação volta a ativa e o uso só é liberado depois de uma leitura integral posterior à reativação.
2. **Given** várias alternâncias entre as duas frases, **When** o estado é calculado, **Then** vale a frase mais recente dita pelo usuário.
3. **Given** uma sessão suspensa, **When** outra sessão, outro runtime ou outra incarnation observa a apresentação, **Then** ela começa ativa e exige leitura antes do uso.

---

### User Story 3 - Ignorar frases que não vêm do usuário (Priority: P1)

A frase dita pelo próprio agente, ou presente apenas no resumo gerado por uma compactação, não muda o estado da apresentação.

**Why this priority**: sem isso, o agente poderia suspender a si mesmo por autorrelato, o que o contrato proíbe.

**Independent Test**: registrar sessões com a frase apenas em fala do agente e apenas em resumo de compactação, e verificar que a apresentação segue ativa.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa, **When** a frase aparece só em fala do agente, **Then** nada muda.
2. **Given** uma sessão ativa, **When** a frase aparece só no resumo de uma compactação, **Then** nada muda.
3. **Given** uma sessão ativa, **When** a frase aparece só em mensagem sintética, **Then** nada muda.

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

- Frase com espaços extras ao redor: reconhecida; frase com outro texto na mesma mensagem: não reconhecida.
- Sessão despachada por coordenador de agentes: a mensagem de usuário recebida pelo worker conta como fonte não-agente da sessão (ADR-0001).
- Suspensão dita antes da primeira leitura da sessão: suspende sem exigir leitura; os demais pré-requisitos (instalação, compatibilidade, habilitação, confiança) continuam exigidos.
- `start adhd mode` sem suspensão anterior na sessão: nenhum efeito; a leitura vigente permanece.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST reconhecer `stop adhd mode` como suspensão somente quando dito em mensagem de usuário da própria sessão, com a frase como conteúdo único da mensagem; a comparação é exata após remover apenas espaços nas pontas, e variações de caixa ou texto adicional não contam.
- **FR-002**: Com suspensão vigente, o sistema MUST liberar o trabalho **desde que instalação, compatibilidade, habilitação e confiança sigam comprovadas na observação corrente**, marcar o uso da apresentação como indisponível e não pedir recarga, antes e depois de compactação na mesma sessão, incarnation e escopo.
- **FR-003**: O sistema MUST reconhecer `start adhd mode`, nas mesmas condições de fonte e comparação do FR-001, como reativação; após a reativação, o uso só é liberado com leitura integral posterior a ela. Entre as duas frases, em mensagem de usuário da própria sessão, vale a mais recente.
- **FR-004**: O sistema MUST ignorar as duas frases quando vierem de fala do agente, de resumo de compactação ou de mensagem sintética.
- **FR-005**: O registro de suspensão MUST identificar a mensagem de origem e a sessão, o escopo e a configuração da observação corrente.
- **FR-006**: Os verbos MUST NOT aceitar suspensão informada pelo chamador: a suspensão só é produzida a partir da observação da sessão.
- **FR-007**: Com suspensão vigente na mesma sessão e escopo, mudança de configuração ou de versão do GWD MUST NOT exigir leitura; o estado novo é registrado, o registro de suspensão passa a identificar a configuração nova e a suspensão se mantém. Mudança de sessão, runtime, escopo ou política dentro de um contexto já aberto MUST continuar recusada como hoje.
- **FR-008**: Sem suspensão, leituras anteriores ao último marcador de compactação MUST continuar sem valor, com o marcador nativo do Claude Code e do Codex reconhecido.
- **FR-009**: Nova sessão, runtime ou incarnation MUST começar com apresentação ativa, sem herdar suspensão.
- **FR-010**: Os códigos de recusa existentes MUST NOT mudar de significado.
- **FR-011**: Toda validação desta entrega MUST rodar sem runtime real, rede ou processo externo, com eventos cuja forma foi capturada de sessões reais de cada harness (Claude Code e Codex), nunca derivada do código sob teste.
- **FR-012**: O contrato de apresentação publicado (bootstrap da skill e protocolo de sessão) MUST declarar que suspensão e reativação exigem fonte não-agente da própria sessão e nomear `start adhd mode` como a reativação explícita.
- **FR-013**: Todo ponto que hoje reporta o estado de apresentação MUST expor a aplicação (ativa ou suspensa), a prontidão para trabalho e para uso e, quando houver, o registro de suspensão.

### Key Entities

- **Estado de apresentação**: aplicação (ativa ou suspensa pelo usuário), prontidão para trabalho e para uso, pedido de leitura e registro de suspensão.
- **Registro de suspensão**: comando, referência da mensagem de origem, digest do texto, sessão, configuração e escopo.
- **Marcador de compactação**: evento nativo da sessão que invalida leituras anteriores.
- **Mensagem sintética**: mensagem inserida pelo harness ou pelo próprio runtime sem ter sido digitada pelo usuário, marcada como tal no transcript nativo.
- **Incarnation**: instância concreta de uma sessão de agente; reiniciar o processo ou trocar de runtime cria outra incarnation, mesmo com o mesmo identificador de sessão.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os sete cenários do handoff passam em validação automatizada, 7 de 7, pelo mapa: 1→US1.1, 2→US1.2, 3→US2.1, 4→US3.1–3, 5→US4.1, 6→US5.1, 7→US2.3.
- **SC-002**: Em 100% dos casos de teste com a frase fora de mensagem de usuário, o estado de apresentação não muda.
- **SC-003**: Uma sessão suspensa atravessa compactação e mudança de configuração sem nenhuma recusa de leitura.
- **SC-004**: A suíte completa do projeto termina sem falhas e o diff fica limpo.

## Assumptions

- A entrega usa somente biblioteca padrão, sem processo novo e sem rede (restrição do repositório).
- Existem rollouts Codex locais com o registro nativo de compactação, de onde a forma do evento pode ser capturada sem copiar conteúdo sensível.
- A mensagem de usuário recebida por um worker despachado conta como fonte não-agente da sessão; o coordenador pode suspender a apresentação de um worker (consequência declarada no ADR-0001).
- Conformidade das respostas do modelo (achado F1) e reexecução da matriz T029 ficam fora desta entrega.
- A versão publicada no momento do ship determina o bump patch, nos oito pontos de versão, com a release correspondente.
