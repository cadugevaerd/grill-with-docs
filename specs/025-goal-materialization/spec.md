# Feature Specification: Materialização e validação do goal.md

**Feature Branch**: `feature/goal-instruct`

**Created**: 2026-08-24

**Status**: Draft

**Input**: Handoff `FASE-001-SPECIFY-HANDOFF.md` do work item `feature-goal-materialization-c29d98e49a524ca8a482615d8d528dab`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receber o documento ao criar um work item (Priority: P1)

Uma pessoa executa a criação de work item num projeto que consome o plugin. Além
do que já recebe hoje, o documento de instruções que conduz o laço autônomo passa
a ser fixado na raiz do projeto. O retorno da criação diz em que estado o
documento foi encontrado e registra o hash do que foi fixado.

**Why this priority**: É a entrega inteira do ponto de vista de quem consome. Sem
ela o documento existe apenas no repositório de origem e não automatiza projeto
nenhum.

**Independent Test**: Executar a criação num projeto limpo e verificar que o
documento aparece na raiz, que o retorno o reporta como recém-criado e que o hash
registrado corresponde aos bytes no disco.

**Acceptance Scenarios**:

1. **Given** um projeto sem o documento na raiz, **When** a criação de work item é executada, **Then** o documento é fixado, o retorno o reporta como recém-criado e o hash registrado corresponde aos bytes materializados.
2. **Given** um projeto que já tem o documento conforme, **When** a criação é executada de novo, **Then** o arquivo não é reescrito, o retorno o reporta como reusado e o hash permanece o mesmo.
3. **Given** a criação concluída, **When** alguém inspeciona o estado do work item, **Then** encontra o caminho e o hash do documento registrados, sem precisar recalcular nada.

---

### User Story 2 - Não perder arquivo humano na raiz (Priority: P1)

Alguém já tinha, na raiz do projeto, um arquivo com o mesmo nome, escrito à mão
para outra finalidade. A criação de work item encontra esse arquivo e o deixa
exatamente como está, dizendo que ele não corresponde ao contrato.

**Why this priority**: Mesma prioridade da anterior porque o custo de errar é
assimétrico: falhar em entregar o documento adia um ganho; destruir arquivo alheio
perde trabalho que ninguém recupera.

**Independent Test**: Colocar um arquivo qualquer com esse nome na raiz, executar
a criação e verificar que os bytes não mudaram e que o retorno o sinaliza como
divergente.

**Acceptance Scenarios**:

1. **Given** um arquivo homônimo escrito à mão na raiz, **When** a criação é executada, **Then** os bytes permanecem idênticos e o retorno o reporta como preservado.
2. **Given** esse mesmo arquivo, **When** a criação termina, **Then** nenhum backup, cópia ou renomeação foi criada em lugar algum.
3. **Given** um documento preservado, **When** o retorno é lido, **Then** o estado preservado é distinguível de sucesso sem interpretar prosa.

---

### User Story 3 - Impedir que o contrato do documento se perca (Priority: P2)

Alguém edita o documento e remove, sem perceber, uma das partes que o contrato
exige. A suíte de testes do projeto reprova a mudança e nomeia o que faltou.

**Why this priority**: Protege a entrega ao longo do tempo, mas depende de a
materialização existir primeiro.

**Independent Test**: Remover uma parte exigida do documento, rodar a suíte e
verificar que ela reprova apontando a parte ausente.

**Acceptance Scenarios**:

1. **Given** o documento íntegro, **When** a suíte roda, **Then** ela aprova.
2. **Given** o documento sem uma das partes exigidas, **When** a suíte roda, **Then** ela reprova e nomeia a parte ausente.
3. **Given** o conjunto de partes exigidas, **When** alguém procura onde ele está declarado, **Then** encontra **um** lugar, e o materializador e o validador leem desse mesmo lugar.

---

### Edge Cases

- O arquivo na raiz existe mas está vazio: não corresponde ao contrato, então é preservado e sinalizado como divergente, e não recriado por cima.
- O arquivo na raiz é um link simbólico: não é seguido nem substituído; a criação recusa em vez de escrever no destino apontado.
- O arquivo existe com o contrato completo mas conteúdo adicional depois: continua conforme, porque o contrato exige presença de partes, não ausência de acréscimos.
- O arquivo tem as partes exigidas mas em ordem diferente: o contrato não fixa ordem; presença basta.
- Duas criações concorrentes no mesmo projeto: a segunda encontra o arquivo já criado pela primeira e reporta reuso, sem corromper nem duplicar.
- O projeto de destino não permite escrita na raiz: a criação falha nomeando o impedimento, e não segue como se tivesse fixado.
- O conjunto de partes exigidas é alterado sem mudar o marcador de versão: todo documento já materializado passa a divergir de uma vez, sem caminho de migração — por isso mudar o conjunto exige marcador novo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A criação de work item MUST fixar o documento na raiz do projeto de destino.
- **FR-002**: A fixação MUST NOT sobrescrever arquivo existente, em nenhuma circunstância.
- **FR-003**: A fixação MUST reportar o estado do documento em três valores distinguíveis sem interpretar prosa: recém-criado, reusado e preservado por divergência.
- **FR-004**: O caminho e o hash do documento fixado MUST ser registrados no estado do work item.
- **FR-005**: O hash registrado MUST corresponder aos bytes efetivamente materializados, não ao conteúdo esperado.
- **FR-006**: Documento existente que não corresponda ao contrato MUST permanecer byte a byte inalterado.
- **FR-007**: A fixação MUST NOT criar backup, cópia ou renomeação de arquivo preexistente.
- **FR-008**: A fixação MUST NOT seguir link simbólico nem escrever no destino apontado por um.
- **FR-009**: O conjunto de partes que o contrato exige MUST ser declarado num único lugar, do qual o materializador, o validador e qualquer consumidor futuro leem.
- **FR-010**: Nenhum consumidor MUST redeclarar esse conjunto, nem derivá-lo do conjunto de outro documento ou de outra versão.
- **FR-011**: O documento MUST carregar um marcador de versão próprio na primeira linha, independente da versão publicada do plugin.
- **FR-012**: A suíte de testes do projeto MUST reprovar um documento a que falte qualquer parte exigida pelo contrato, nomeando a parte ausente.
- **FR-013**: O teste do contrato MUST rodar sem acesso à rede e sem exigir ferramenta externa instalada.
- **FR-014**: A conformidade MUST ser decidida por presença das partes exigidas, não por ordem entre elas nem por ausência de conteúdo adicional.
- **FR-015**: A criação concorrente no mesmo projeto MUST resultar em um único documento íntegro, com a segunda execução reportando reuso.
- **FR-016**: Impedimento de escrita na raiz MUST fazer a criação falhar nomeando o impedimento, nunca prosseguir como se tivesse fixado.
- **FR-017**: A versão publicada do plugin MUST refletir esta mudança em todos os pontos onde a distribuição a exige, antes de qualquer merge ou publicação.

### Key Entities

- **Documento gerenciado**: o arquivo fixado na raiz do projeto de destino, identificado pelo marcador de versão na primeira linha.
- **Marcador de versão**: a declaração, na primeira linha, de qual versão do contrato aquele documento segue; independente da versão publicada do plugin.
- **Conjunto exigido**: as partes que precisam estar presentes para um documento ser considerado conforme; declarado uma única vez e congelado.
- **Estado da fixação**: um de três — recém-criado, reusado, preservado por divergência.
- **Registro no work item**: o caminho e o hash do documento fixado, gravados no estado para permitir detecção de deriva.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em um projeto limpo, a criação de work item entrega o documento na raiz em 100% das execuções.
- **SC-002**: Nenhuma execução, em nenhum cenário, altera os bytes de um arquivo preexistente na raiz — verificável comparando o conteúdo antes e depois.
- **SC-003**: Duas criações seguidas no mesmo projeto produzem exatamente um arquivo, e a segunda reporta reuso.
- **SC-004**: O hash registrado no estado do work item corresponde aos bytes no disco em 100% das execuções bem-sucedidas.
- **SC-005**: Remover qualquer parte exigida do documento faz a suíte reprovar, e a saída nomeia a parte ausente sem que o leitor precise procurá-la.
- **SC-006**: O conjunto de partes exigidas aparece declarado em exatamente um lugar do repositório — verificável por busca textual.
- **SC-007**: A suíte completa continua passando sem rede e sem ferramenta externa, nas três plataformas e nas duas versões de linguagem que a integração cobre.
- **SC-008**: A versão publicada é idêntica em todos os pontos que a distribuição trava, verificável pelo gate que já existe.

## Assumptions

- O texto normativo do documento já está entregue e não é reaberto aqui; esta entrega o transporta e o protege, não o escreve.
- O projeto de destino já tem a governança e o contrato de fluxo materializados; esta entrega acrescenta um terceiro artefato project-wide ao lado deles, não os substitui.
- A raiz do projeto de destino é gravável no caso normal; o caso contrário é tratado como falha nomeada, não como cenário comum.
- O mecanismo de fixação já usado para o contrato de fluxo é considerado adequado e serve de referência de comportamento, ainda que a organização interna do código difira.
- Mudar o conjunto de partes exigidas sem trocar o marcador invalidaria todo documento já materializado de uma vez; por isso o conjunto é tratado como congelado e uma mudança de contrato exige marcador novo.
