# Feature Specification: Destravar a ponte com o backlog operacional

**Feature Branch**: `feat/backlog-ssot`

**Created**: 2026-08-17

**Status**: Draft

**Input**: FASE-001 do work item `feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4`. Handoff canônico: `.grill/work-items/feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4/handoffs/FASE-001-SPECIFY-HANDOFF.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Espelhar decisões de um trabalho já em andamento (Priority: P1)

Um operador conduziu uma sessão de decisão, registrou decisões adiadas no trabalho e quer que elas apareçam no backlog operacional do repositório. Hoje o espelho recusa o trabalho inteiro assim que qualquer registro é escrito, que é exatamente quando ele teria serviço a fazer.

**Why this priority**: É o defeito raiz. Enquanto o espelho recusar trabalhos com registro escrito, nenhuma outra correção desta fase tem como ser exercitada, e a migração planejada para fases posteriores também não conseguiria escrever.

**Independent Test**: Conduzir um trabalho, registrar uma decisão adiada e pedir a prévia do espelho. Entrega valor sozinho: o operador passa a enxergar o que seria enviado ao backlog.

**Acceptance Scenarios**:

1. **Given** um trabalho cujos registros de decisão foram escritos depois da criação, **When** o operador pede a prévia do espelho, **Then** o sistema responde com a lista de decisões a espelhar em vez de recusar o trabalho.
2. **Given** o mesmo trabalho, **When** o operador autoriza a aplicação, **Then** cada decisão vira um item no backlog vinculado ao repositório.
3. **Given** um trabalho cujo bloco de identidade foi adulterado, **When** o operador pede a prévia, **Then** o sistema recusa de forma nomeada.

---

### User Story 2 - Espelhar decisões já encerradas (Priority: P1)

Um operador fecha um marco. Para fechá-lo, precisou resolver todas as decisões adiadas. Hoje o espelho só considera decisões em aberto, então no momento em que o trabalho fica apresentável nada mais é espelhável.

**Why this priority**: Junto com a história 1, é o que explica o resultado observado em campo: de oito registros existentes, apenas um chegou ao backlog. Sem isso, o espelho continua sendo uma função que só funciona enquanto o trabalho está bloqueado.

**Independent Test**: Tomar um trabalho cujas decisões estão todas encerradas e pedir a prévia. Hoje o resultado é lista vazia; o esperado é a lista completa.

**Acceptance Scenarios**:

1. **Given** um trabalho com decisões em estado encerrado, **When** o operador pede a prévia, **Then** essas decisões aparecem na lista.
2. **Given** um trabalho com decisões abertas e encerradas misturadas, **When** o operador aplica, **Then** todas viram item e cada uma carrega o estado correspondente.
3. **Given** uma decisão marcada como substituída, **When** o operador aplica, **Then** o item correspondente fica em estado de cancelamento, não de conclusão.

---

### User Story 3 - Reexecutar sem duplicar (Priority: P2)

Um operador roda o espelho duas vezes, por engano ou porque um passo anterior falhou no meio. O armazenamento do backlog aceita itens idênticos sem reclamar, então nada além do próprio espelho impede a duplicata.

**Why this priority**: Não bloqueia as histórias 1 e 2, mas sem isso a correção introduz um modo de falha novo: quanto mais o espelho funciona, mais fácil poluir o backlog. Precisa entrar junto, não depois.

**Independent Test**: Aplicar duas vezes seguidas sobre o mesmo trabalho e comparar o backlog antes e depois da segunda execução.

**Acceptance Scenarios**:

1. **Given** um trabalho já espelhado, **When** o operador aplica de novo, **Then** nenhum item novo é criado e cada decisão é relatada como já existente.
2. **Given** duas decisões de trabalhos diferentes que compartilham o mesmo identificador local, **When** ambas são espelhadas, **Then** as duas viram itens distintos, sem uma ser confundida com a outra.

---

### Edge Cases

- Repositório sem backlog vinculado: o espelho continua recusando de forma nomeada, sem criar vínculo por conta própria.
- Backlog indisponível ou respondendo fora do contrato: recusa nomeada, sem deixar o trabalho em estado parcial.
- Trabalho sem nenhuma decisão registrada: prévia devolve lista vazia e a aplicação não altera nada.
- Falha depois de criar um item e antes de concluir o restante: a execução seguinte reconhece o que já existe e completa o que falta, sem duplicar.
- Decisão cujo item correspondente foi apagado à mão do backlog: a execução seguinte recria o item.
- Decisão que muda de estado entre duas execuções: a segunda execução leva o item ao estado novo quando o caminho for permitido, e relata reconciliação recusada quando não for, sem tocar o item.
- Decisão cujo item já está concluído e cuja decisão volta a um estado anterior: caminho não permitido, portanto reconciliação recusada e relato explícito, nunca alteração silenciosa.
- Item vinculado cujos marcadores foram removidos à mão: o vínculo deixa de ser recuperável e a decisão é tratada como não espelhada, o que pode gerar um item novo; o relato deve deixar isso visível.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O espelho MUST operar sobre trabalhos cujos registros de decisão foram escritos após a criação, deixando de tratar a alteração desses registros como perda de integridade.
- **FR-002**: O espelho MUST continuar recusando, de forma nomeada, um trabalho cujo bloco de identidade tenha sido adulterado.
- **FR-003**: O espelho MUST considerar decisões adiadas em qualquer estado, e não apenas as que estiverem em aberto.
- **FR-004**: O sistema MUST criar cada item já no estado que corresponde ao estado da decisão de origem, sem passar por estados intermediários que não ocorreram.
- **FR-005**: O sistema MUST traduzir decisão resolvida para conclusão e decisão substituída para cancelamento, respeitando as transições que o backlog admite.
- **FR-006**: O sistema MUST identificar unicamente cada decisão pela combinação do trabalho de origem com o identificador local da decisão.
- **FR-007**: O sistema MUST reconhecer decisões já espelhadas e relatá-las como existentes, sem criar item novo.
- **FR-008**: O sistema MUST tratar a prévia como comportamento padrão, alterando o backlog apenas sob autorização explícita.
- **FR-009**: O sistema MUST recusar de forma nomeada quando o repositório não tiver backlog vinculado, sem criar o vínculo por iniciativa própria.
- **FR-010**: O sistema MUST relatar, por decisão, qual foi o desfecho: proposta, criada, já existente e correta, estado reconciliado, reconciliação recusada, ou estado de origem não reconhecido.
- **FR-011**: O sistema MUST falar com o backlog apenas pela interface pública dele, nunca acessando o armazenamento diretamente.
- **FR-012**: A cobertura automatizada MUST exercitar todos os caminhos acima sem exigir o backlog real instalado.
- **FR-013**: Quando o estado desejado não for alcançável a partir do estado atual do item, o sistema MUST relatar a decisão como reconciliação recusada, sem tentar a transição e sem alterar o item.
- **FR-014**: O sistema MUST calcular o conjunto completo de propostas antes de emitir qualquer mutação, de modo que toda recusa de pré-condição ocorra com o backlog intacto.
- **FR-015**: Quando o estado declarado de uma decisão não pertencer ao vocabulário conhecido, o sistema MUST recusar de forma nomeada, sem criar nem transicionar item, e MUST nomear o valor ofensor. Presumir um estado padrão relataria decisão resolvida como em curso.

### Key Entities

- **Trabalho**: unidade isolada de decisão, com identidade própria e um conjunto de registros de decisão adiada.
- **Decisão adiada**: registro pertencente a um trabalho, com identificador local, título e estado entre aberto, resolvido e substituído.
- **Item de backlog**: unidade do backlog operacional do repositório, com identificador atribuído por ele e estado próprio.
- **Vínculo**: correspondência entre uma decisão adiada e o item que a representa, estável entre execuções e legível por quem inspeciona o item.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para um trabalho com decisões registradas, a prévia do espelho conclui com sucesso em vez de recusar, em 100% dos casos em que a identidade está íntegra.
- **SC-002**: Decisões em estado encerrado passam a ser espelhadas; sobre o acervo atual, a cobertura sai de 1 de 8 registros para 8 de 8.
- **SC-003**: Executar o espelho duas vezes seguidas sobre o mesmo trabalho não cria nenhum item adicional.
- **SC-004**: Cada item criado permite identificar, sem ambiguidade, de qual trabalho e de qual decisão veio.
- **SC-005**: A verificação automatizada completa passa nos três sistemas operacionais suportados sem o backlog real instalado.
- **SC-006**: Nenhuma recusa de pré-condição chega a alterar o backlog: falha de vínculo, de identidade ou de disponibilidade ocorre antes da primeira mutação, em 100% dos casos.
- **SC-007**: Uma interrupção no meio da aplicação não exige reparo manual: a execução seguinte reconhece o que já existe, completa o que falta e não duplica nada.
- **SC-008**: Toda resposta do comando nomeia o backlog que foi alvo, inclusive as recusas, de modo que a cobertura automatizada obtenha o mesmo resultado com e sem o binário do backlog instalado.

## Assumptions

- O repositório já está vinculado a um backlog; criar ou vincular backlog pertence a outra fase e permanece fora daqui.
- A geração do registro versionado de decisões e a migração de trabalhos antigos pertencem a fases posteriores e não são afetadas aqui, exceto por dependerem de FR-001.
- O estado intermediário do backlog é usado como estado inicial dos itens, decisão registrada em ADR-0003 e derivada das transições que o backlog admite; a alternativa de gravar um estado transitório inexistente foi descartada.
- A tradução de estados assume que decisão resolvida e decisão substituída são terminais do lado do trabalho, ainda que o backlog admita reabertura de itens cancelados.
- O vínculo entre decisão e item é registrado no próprio item, em campo de texto livre, por ser o único lugar disponível na interface pública de criação.
- A verificação automatizada usa um substituto para o backlog, pelo ponto de injeção já existente, porque o ambiente de verificação não tem o binário real e isso não vai mudar.
