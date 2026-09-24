# Feature Specification: Fence autorizado de atividade órfã

**Feature Branch**: `cadugevaerd/fix-leader`

**Created**: 2026-09-24

**Status**: Draft

**Input**: Handoff `FASE-001-SPECIFY-HANDOFF.md` do work item `fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24` (decisões DQ-0001..DQ-0012, migradas de `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` sem reabertura)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Destravar a sucessão presa por uma atividade órfã (Priority: P1)

Um work item fica preso quando uma atividade de especialista despachada nunca terminou do ponto de vista do registro: o especialista já encerrou, o líder que a despachou também, e ninguém consegue levar a atividade a um estado final. Enquanto ela conta como trabalho ativo, nenhuma sessão nova consegue assumir o work item. Com a autorização humana exata para aquele work item, aquele contexto e aquela atividade, o líder sucessor encerra a atividade sem aceitar nada dela, assume o work item e refaz a autoria como uma atividade nova.

**Why this priority**: é o caso X7 observado em produção. Hoje a única saída seria editar o registro à mão, o que a Constituição trata como contorno.

**Independent Test**: montar um work item com uma atividade despachada cujo especialista e cujo líder estão comprovadamente encerrados, pedir a prévia, aplicar com o hash da prévia e a autorização exata, e confirmar que a tomada do work item passa a ser admitida.

**Acceptance Scenarios**:

1. **Given** uma atividade despachada sem resultado, com especialista e líder comprovadamente encerrados, **When** o sucessor pede a prévia do encerramento, **Then** a prévia lista a atividade, as duas observações terminais, o solicitante e um hash, e nada é gravado.
2. **Given** a prévia do cenário anterior, **When** o sucessor aplica com o mesmo hash e a autorização humana exata, **Then** a atividade termina não aceita, a sessão dela é fechada com recibo e a tomada do work item passa a ser admitida.
3. **Given** a tomada admitida, **When** o sucessor refaz a autoria, **Then** ela nasce como atividade nova, e nada do trabalho encerrado migra para ela.

---

### User Story 2 - Encerrar atividade de sessão retida (Priority: P1)

Uma atividade gravou resultado, mas a sessão do especialista ficou retida pelo ambiente e nunca vai provar fechamento. Por isso o resultado não pode ser aceito, e a atividade conta como ativa para sempre. O mesmo encerramento autorizado leva essa atividade a um estado final não aceito. O resultado gravado continua registrado, mas nunca é aceito nem herdado. Quando o líder da atividade ainda está vivo, só esse líder exato pode pedir o encerramento. Quando o líder já terminou, pede o sucessor, com prova do encerramento do líder e da própria sessão.

**Why this priority**: o próprio work item de origem desta correção caiu nesse caso e deixou de admitir sucessor. Sem essa variante, a correção não destrava nem o caso que a originou.

**Independent Test**: montar uma atividade com resultado gravado e sessão retida, pedir e aplicar o encerramento pelo líder corrente e, em outro teste, pelo sucessor com o líder terminal. Nos dois casos, confirmar que a atividade deixa de contar como ativa para a tomada e para a troca de runtime.

**Acceptance Scenarios**:

1. **Given** uma atividade com resultado gravado e sessão retida, com líder vivo, **When** o próprio líder corrente pede e aplica o encerramento com a autorização exata, **Then** a atividade termina não aceita e o resultado nunca é aceito.
2. **Given** a mesma atividade com o líder já terminal, **When** um sucessor com a própria sessão comprovada pede e aplica o encerramento, **Then** o efeito é o mesmo e o registro nomeia o sucessor como solicitante.
3. **Given** a atividade encerrada, **When** alguém tenta aceitá-la depois, **Then** a tentativa é recusada.

---

### User Story 3 - Recusar encerramento sem prova ou sem autorização exata (Priority: P1)

Quem pede o encerramento sem a autorização humana exata, com uma autorização emitida para outro alvo ou sem prova terminal do ambiente é recusado. O estado fica exatamente como estava, e a recusa nomeia o que falta.

**Why this priority**: o encerramento descarta trabalho e libera a sucessão. Ele só pode abrir quando a prova e a autorização são exatas.

**Independent Test**: repetir o pedido variando uma condição por vez (autorização, alvo da autorização, estado do líder, estado do especialista, legibilidade das observações) e confirmar recusa e estado idêntico ao anterior.

**Acceptance Scenarios**:

1. **Given** qualquer atividade elegível, **When** o encerramento é pedido sem autorização, **Then** prévia e aplicação recusam com o mesmo código e nada muda.
2. **Given** uma autorização emitida para outro contexto, outra atividade ou outro run, **When** o encerramento é pedido, **Then** a recusa é idêntica à da ausência de autorização e nada muda.
3. **Given** um líder da atividade ainda ativo que não é o solicitante, **When** o encerramento é pedido, **Then** a recusa é própria desse caso e nada muda.
4. **Given** um especialista cujo dispatch ainda está ativo, **When** o encerramento é pedido, **Then** a recusa é própria desse caso e nada muda.
5. **Given** uma observação ausente, ilegível, não correlacionada ou sem veredicto terminal, inclusive a da própria sessão do sucessor, **When** o encerramento é pedido, **Then** a recusa é por prova não comprovada e nada muda.

---

### User Story 4 - Aplicação idempotente e protegida contra prévia desatualizada (Priority: P2)

Quem repete a aplicação com os mesmos insumos recebe reuso, sem segundo efeito. Quem aplica com um hash que não corresponde mais ao estado é recusado.

**Why this priority**: sem isso, uma nova tentativa depois de timeout vira um segundo efeito ou um estado meio aplicado.

**Independent Test**: aplicar duas vezes com os mesmos insumos; aplicar com hash desatualizado.

**Acceptance Scenarios**:

1. **Given** um encerramento já aplicado, **When** a aplicação é repetida com os mesmos insumos, **Then** o resultado é reuso e não há segundo evento.
2. **Given** um estado que mudou depois da prévia, **When** a aplicação usa o hash antigo, **Then** ela é recusada e nada muda.

### Edge Cases

- Atividade em estado que não é "despachada" nem "resultado gravado": o encerramento recusa, sem efeito.
- Autorização válida na forma, mas de decisão diferente de aprovação: tratada como ausência de autorização.
- Especialista com veredicto indeterminado (sem status terminal, sem revogação e sem liveness conclusiva): tratado como prova não comprovada, nunca como terminal.
- Mais de um solicitante concorrente: só um aplica; o outro recebe recusa ou reuso, nunca um segundo efeito.
- Troca de runtime depois do encerramento: a atividade encerrada não conta como trabalho ativo.
- Tomada depois do encerramento: a regra de herança de workers já existente continua igual.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST oferecer um único verbo de encerramento autorizado de atividade, com prévia por padrão e aplicação só com o hash exato da prévia.
- **FR-002**: A prévia MUST NOT gravar nada. O hash dela MUST cobrir atividade, contexto, solicitante, veredictos e referências das observações do especialista e do líder, e a autorização.
- **FR-003**: O encerramento MUST exigir autorização humana vinculada exatamente ao work item, ao contexto e à atividade. Ausência e alvo divergente MUST recusar com o mesmo código.
- **FR-004**: O encerramento MUST exigir prova terminal do dispatch do especialista, obtida do ambiente e nunca da alegação do chamador. Silêncio, expiração e observação inconclusiva MUST NOT contar como prova.
- **FR-005**: A autoridade MUST derivar da observação do líder da atividade. Com líder vivo, só o líder corrente exato pode pedir. Com líder terminal, o sucessor pode pedir se a própria sessão for observada e provada. Líder vivo com solicitante diferente MUST recusar com código próprio.
- **FR-006**: O encerramento MUST cobrir a atividade despachada sem resultado e a atividade com resultado gravado cuja sessão ficou retida.
- **FR-007**: A atividade encerrada MUST terminar em estado final não aceito, com motivo registrado. O resultado gravado, se houver, MUST NOT ser aceito nem herdado, e aceite posterior MUST ser recusado.
- **FR-008**: A sessão da atividade encerrada MUST ser fechada com recibo correlacionado à operação de encerramento.
- **FR-009**: Depois do encerramento, a atividade MUST NOT contar como trabalho ativo para a tomada nem para a troca de runtime. A regra existente de herança de workers MUST ficar inalterada.
- **FR-010**: A operação MUST ficar rastreável ao work item, ao contexto, à atividade, ao solicitante, aos digests observados e à autorização verbatim.
- **FR-011**: A nova autoria MUST nascer como atividade nova no contexto sucessor, ligada à encerrada só pelo registro da operação. Nada do resultado encerrado migra.
- **FR-012**: Repetir a aplicação com os mesmos insumos MUST devolver reuso sem segundo efeito. Hash divergente MUST recusar sem efeito.
- **FR-013**: Toda recusa MUST deixar o estado bit a bit igual ao anterior e nomear o dado faltante ou divergente.
- **FR-014**: A versão do plugin MUST ser incrementada nos oito pontos de distribuição.
- **FR-015**: A mudança MUST NOT alterar a Constituição, o WORKFLOW nem os registries e catálogos.

### Key Entities

- **Atividade de especialista**: trabalho de autoria ou revisão despachado a uma sessão. Tem estado, sessão associada e, às vezes, resultado gravado.
- **Operação de encerramento**: registro único e rastreável do encerramento. Guarda alvo, solicitante, observações, autorização e o hash da prévia.
- **Autorização humana exata**: decisão de aprovação vinculada a um work item, um contexto e uma atividade, com referência verificável ao recibo da decisão.
- **Observação terminal**: leitura do ambiente sobre o dispatch do especialista ou do líder, com veredicto terminal, ativo ou indeterminado.
- **Recibo de fechamento de sessão**: comprovante de que a sessão da atividade encerrada foi fechada pela operação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Na forma órfã e na forma de sessão retida, a tomada do work item passa de recusada a admitida depois de um único encerramento autorizado, sem edição manual do registro.
- **SC-002**: 100% dos cenários negativos (sem autorização, autorização de outro alvo, líder vivo que não é o solicitante, especialista vivo, prova inconclusiva e hash desatualizado) deixam o estado idêntico ao anterior.
- **SC-003**: Zero aceites de resultado de atividade encerrada, em qualquer rota posterior.
- **SC-004**: Repetir a aplicação produz zero efeitos adicionais.
- **SC-005**: A suíte de validadores do repositório fica verde nos três sistemas operacionais da matriz de integração, sem rede.

## Assumptions

- O ambiente de orquestração expõe status do dispatch, revogação de capability e liveness. Uma leitura que não traz nenhum desses sinais conclusivos é indeterminada.
- O recibo da decisão humana já existe antes do pedido: a autorização o referencia, não o produz.
- O encerramento do próprio work item de origem (`superseded`) é a FASE-002, depois do ship, e fica fora desta especificação.
- Transcript acima de 16 MiB (SGD-37), a falha de leitura com campanha e head nulo (SGD-38) e o aceite gravado pela troca de runtime (SGD-39) ficam fora do escopo.
- A prevenção por checkpoint automático fica fora do escopo (DQ-0002).
