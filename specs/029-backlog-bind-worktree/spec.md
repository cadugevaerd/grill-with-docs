# Feature Specification: Backlog vinculado de qualquer worktree

**Feature Branch**: `cadugevaerd/chore-fix-backlog`

**Created**: 2026-09-08

**Status**: Draft

**Input**: Handoff `FASE-001-SPECIFY-HANDOFF.md` do work item `fix-backlog-bind-worktree-e7e330462d004d439ebb11ab6c6d95ea`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trabalhar numa worktree e encontrar o backlog já vinculado (Priority: P1)

Quem abre uma worktree dedicada para um work item roda a verificação prévia, a
criação do work item e os verbos de backlog a partir dessa worktree, e encontra o
mesmo backlog vinculado que encontraria no checkout principal do repositório —
com o mesmo código, sem precisar contornar o pré-requisito com a opção de pular
o backlog nem esperar o merge para vincular depois.

**Why this priority**: É o defeito relatado. O fluxo oficial é um work item por
worktree e o backlog é pré-requisito da criação do work item; hoje os dois
contratos se contradizem e todo work item criado em worktree nasce carimbado
como "sem backlog".

**Independent Test**: Num repositório já vinculado a um backlog, abrir uma
worktree adicional e rodar a verificação prévia nela; conferir que o resultado é
"vinculado" com o mesmo código que o checkout principal reporta.

**Acceptance Scenarios**:

1. **Given** um repositório cujo backlog está vinculado ao caminho do checkout principal, **When** a verificação prévia roda numa worktree adicional desse repositório, **Then** o relatório reporta o backlog como vinculado, com o mesmo código, sem propor criação.
2. **Given** o mesmo repositório, **When** a criação do work item roda na worktree adicional sem a opção de pular o backlog, **Then** o work item é criado sem recusa por backlog ausente e sem o carimbo de backlog pulado.
3. **Given** um repositório cujo backlog está vinculado ao caminho de uma worktree adicional (e não ao principal), **When** a verificação prévia roda no checkout principal ou em outra worktree adicional, **Then** o backlog é reportado como vinculado e o caminho do vínculo permanece o que era.
4. **Given** um work item criado com a opção de pular o backlog, numa worktree adicional de repositório vinculado, **When** a adoção do backlog roda nessa mesma worktree, **Then** o carimbo é limpo sem exigir merge prévio.
5. **Given** um work item numa worktree adicional de repositório vinculado, **When** os verbos de espelhar, projetar, verificar e migrar decisões rodam nela, **Then** todos encontram o backlog vinculado e operam sobre ele.

---

### User Story 2 - Vincular um repositório novo a partir de uma worktree (Priority: P1)

Quem começa a usar o backlog num repositório ainda não vinculado, rodando a
verificação prévia a partir de uma worktree adicional, recebe uma proposta de
criação cujo nome e código derivam do repositório — não do nome da worktree — e,
ao autorizar o vínculo, o caminho registrado é o do checkout principal, para que
qualquer worktree futura o reconheça.

**Why this priority**: Sem isso, o vínculo feito de dentro de uma worktree grava
o nome da branch como nome do repositório e um caminho efêmero como caminho do
vínculo, o que reproduz o defeito na primeira worktree seguinte.

**Independent Test**: Num repositório sem backlog, rodar a verificação prévia
numa worktree adicional e conferir que a proposta usa o nome do checkout
principal; autorizar o vínculo e conferir que o caminho registrado é o do
checkout principal.

**Acceptance Scenarios**:

1. **Given** um repositório sem backlog vinculado, **When** a verificação prévia roda numa worktree adicional, **Then** a proposta de criação usa o nome e o código derivados do checkout principal, e o caminho proposto é o do checkout principal.
2. **Given** a mesma situação com a autorização de instalação concedida, **When** o vínculo é aplicado, **Then** o backlog fica vinculado ao caminho do checkout principal, e uma verificação prévia seguinte em qualquer worktree do repositório o reporta como vinculado.
3. **Given** um backlog existente com o nome do repositório e ainda sem vínculo, **When** a verificação prévia roda numa worktree adicional, **Then** a proposta é vincular esse backlog ao caminho do checkout principal, sem criar outro.
4. **Given** um código de backlog informado explicitamente que já está vinculado a outro repositório, **When** a verificação roda em qualquer worktree deste repositório, **Then** a recusa continua explícita, como hoje.

---

### User Story 3 - Falhar fechado diante de ambiguidade ou degradação (Priority: P2)

Quando dois backlogs de códigos distintos apontam a worktrees do mesmo
repositório, quem roda a verificação prévia recebe uma recusa que nomeia os dois,
e nada é alterado. Quando a lista de worktrees do repositório não pode ser
obtida, o comportamento é o de hoje, sem erro inesperado.

**Why this priority**: A ponte nunca escolhe nem re-vincula por conta própria;
essa regra já existe e precisa sobreviver à mudança. A degradação existe para
que a mudança não introduza recusa nova onde hoje há resposta.

**Independent Test**: Registrar dois backlogs de códigos diferentes vinculados a
duas worktrees do mesmo repositório e rodar a verificação prévia; conferir a
recusa nomeando ambos e a ausência de mutação. Simular a lista de worktrees
indisponível e conferir que o resultado é o atual.

**Acceptance Scenarios**:

1. **Given** dois backlogs de códigos distintos vinculados a duas worktrees do mesmo repositório, **When** a verificação prévia roda em qualquer worktree dele, **Then** a resposta é uma recusa que nomeia os dois códigos e os dois caminhos, e nenhum vínculo muda.
2. **Given** a lista de worktrees do repositório indisponível, **When** a verificação prévia roda, **Then** o vínculo é resolvido comparando apenas o caminho corrente, como hoje, sem exceção não tratada.
3. **Given** um backlog vinculado ao caminho de uma worktree que já foi removida, **When** a verificação prévia roda numa worktree viva do repositório, **Then** o resultado é o de hoje: proposta de criação, sem re-apontar o vínculo.

---

### Edge Cases

- Caminhos com atalho simbólico ou grafia diferente para o mesmo diretório: o vínculo casa pelo caminho real, não pela grafia.
- Repositório com uma única worktree: o comportamento é idêntico ao atual em todos os cenários.
- Worktree adicional cujo diretório tem o mesmo nome de outro repositório: a derivação de nome e código usa o checkout principal, então o nome da worktree nunca vira código de backlog.
- Backlog vinculado a worktree adicional que continua existindo: permanece vinculado a ela; nenhum comando o move para o checkout principal.
- Verbos que iteram muitas decisões: a lista de worktrees é consultada uma vez por comando, não uma vez por decisão.
- Verificação prévia rodando fora de um repositório: continua recusada antes de qualquer consulta ao backlog, como hoje.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A resolução do backlog MUST considerar um repositório vinculado quando o caminho do vínculo corresponder a qualquer worktree registrada desse repositório, não apenas à worktree em que o comando roda.
- **FR-002**: A comparação de caminhos MUST usar o caminho real de ambos os lados, de modo que atalhos simbólicos e grafias distintas do mesmo diretório sejam tratados como iguais.
- **FR-003**: Quando o repositório não estiver vinculado, a proposta de criação ou vínculo MUST derivar nome, código e caminho do checkout principal do repositório, nunca da worktree corrente.
- **FR-004**: Ao aplicar um vínculo novo, o caminho registrado no backlog MUST ser o do checkout principal.
- **FR-005**: Um vínculo já existente, esteja no checkout principal ou numa worktree adicional, MUST NOT ser alterado ou re-apontado por nenhum comando desta mudança.
- **FR-006**: Quando dois backlogs de códigos distintos corresponderem a worktrees do mesmo repositório, a resolução MUST recusar nomeando os códigos e caminhos envolvidos, sem escolher e sem mutar.
- **FR-007**: Quando a lista de worktrees não puder ser obtida, a resolução MUST recair na comparação com o caminho corrente, mantendo o comportamento atual.
- **FR-008**: A verificação prévia, a criação do work item e os verbos de adoção, espelhamento, projeção, verificação e migração do backlog MUST compartilhar a mesma resolução e, portanto, o mesmo resultado em qualquer worktree do repositório.
- **FR-009**: Os códigos e formatos de resposta já publicados MUST permanecer idênticos; a recusa por ambiguidade MUST usar o código de indisponibilidade já existente, com o detalhe nomeando o conflito.
- **FR-010**: A lista de worktrees MUST ser consultada no máximo uma vez por comando.
- **FR-011**: A suíte de validação MUST conter ao menos um caso em que o comando roda numa worktree adicional e o vínculo aponta ao checkout principal, com resultado "vinculado", e ao menos um caso exercitando uma worktree adicional real criada pela ferramenta de versionamento.
- **FR-012**: Toda alteração publicada MUST vir com incremento de versão compatível refletido em todos os pontos de versão que o validador de distribuição fixa.

### Key Entities

- **Repositório**: unidade de identidade para o vínculo; possui um checkout principal e zero ou mais worktrees adicionais, todos com caminho próprio.
- **Checkout principal**: a worktree que hospeda o repositório; origem canônica de nome, código e caminho para vínculos novos.
- **Worktree adicional**: checkout paralelo do mesmo repositório, em caminho próprio, criado para um work item.
- **Vínculo**: associação entre um código de backlog e um único caminho de diretório, mantida pela ferramenta de backlog; um por código.
- **Resolução do backlog**: resultado de consultar os vínculos a partir de um repositório: vinculado, precisa vincular, precisa criar, ou recusa nomeada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em um repositório vinculado, a verificação prévia produz o resultado "vinculado" com o mesmo código em 100% das worktrees do repositório, principal ou adicionais.
- **SC-002**: A criação de um work item numa worktree adicional de repositório vinculado é concluída sem a opção de pular o backlog e sem carimbo de backlog pulado.
- **SC-003**: Nenhum vínculo registrado antes da mudança muda de código ou de caminho após ela (comparação antes/depois idêntica da lista de backlogs).
- **SC-004**: A suíte de validação completa passa na matriz de integração (três sistemas operacionais, duas versões de Python) sem acesso à rede e sem a ferramenta de backlog real.
- **SC-005**: Nenhum código de resposta público muda de forma; consumidores existentes continuam interpretando as respostas sem ajuste.

## Assumptions

- A ferramenta de backlog continua mantendo um único caminho por código; mudar essa chave para uma identidade independente de caminho é outro repositório e fica fora do escopo.
- Backlogs já vinculados a worktrees adicionais que ainda existem são válidos e permanecem como estão; re-apontá-los para o checkout principal é decisão humana e não é feita por esta mudança.
- Um vínculo que aponta a worktree já removida continua sendo tratado como repositório sem vínculo; um verbo explícito de re-vinculação com confirmação humana é trabalho futuro, registrado no work item.
- A ferramenta de versionamento está presente na matriz de integração e é dependência obrigatória já declarada; um caso de teste pode criar uma worktree real com ela sem tocar a rede.
- A leitura de versão proposta é patch: a mudança corrige comportamento sem alterar contrato público. Confirmar no ciclo executor.
