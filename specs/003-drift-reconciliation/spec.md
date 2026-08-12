# Feature Specification: Reconciliação do drift existente

**Feature Branch**: `003-drift-reconciliation`

**Created**: 2026-08-12

**Status**: Draft

**Input**: Handoff `.grill/work-items/feature-release-repo-sync-97a2bb32d4884a129ec2e845b76894b7/handoffs/FASE-003-SPECIFY-HANDOFF.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Um disparo manual acaba com o atraso acumulado (Priority: P1)

Quem opera a publicação dispara o workflow uma única vez, sem inventar um commit no plugin. Os dois marketplaces param de servir o estado antigo e passam a servir a versão corrente do canônico.

**Why this priority**: É o objetivo inteiro da fase. A publicação automática só reage a mudanças em `plugin/`, e o trabalho que a introduziu não é uma dessas mudanças — sem disparo manual o atraso sobrevive por tempo indeterminado.

**Independent Test**: Disparar manualmente e observar, em cada índice publicado, `version`, `source.ref` e `source.sha` correspondendo à versão e ao commit do canônico.

**Acceptance Scenarios**:

1. **Given** os dois destinos atrasados em relação ao canônico, **When** o disparo manual roda, **Then** existe tag para a versão corrente no canônico e cada índice aponta para ela.
2. **Given** o destino que já conhece o plugin e o destino que não conhece, **When** o disparo manual roda, **Then** o primeiro é atualizado e o segundo ganha entrada nova, na mesma execução.

---

### User Story 2 - A execução prova o que publicou (Priority: P1)

A execução não termina verde por ter escrito num arquivo local: ela relê o estado publicado no destino e falha se ele não corresponder à release.

**Why this priority**: Esta é a primeira execução real da automação. Sem releitura, "publiquei" significa apenas "editei e o push não retornou erro" — um push que vai para o lugar errado, um commit vazio ou uma entrada com o pin trocado passariam como sucesso. A fase existe justamente para que a automação deixe de ser não-exercitada, então ela precisa terminar com evidência, não com ausência de erro.

**Independent Test**: Adulterar a versão do índice de um clone e observar a verificação reprovar; corrigir e observar aprovar.

**Acceptance Scenarios**:

1. **Given** um destino cujo índice publicado corresponde à release, **When** a verificação roda, **Then** ela aprova e nomeia versão, ref e sha conferidos.
2. **Given** um destino cujo índice publicado diverge em qualquer um dos quatro campos do pin ou na versão, **When** a verificação roda, **Then** ela reprova nomeando cada divergência.
3. **Given** uma referência publicada que não resolve para o commit publicado no canônico, **When** a verificação roda, **Then** ela reprova.

---

### User Story 3 - O disparo manual continua disponível depois (Priority: P2)

Depois da reconciliação, o gatilho manual permanece como saída de emergência: republicar não exige inventar um commit.

**Why this priority**: A reconciliação é única, o gatilho não. Quando uma execução automática falhar e o merge correspondente já tiver passado, não há reexecução automática — o disparo manual é o único caminho que sobra.

**Independent Test**: Após a reconciliação, o workflow continua listando o disparo manual e uma segunda execução termina limpa, sem mudança.

**Acceptance Scenarios**:

1. **Given** a reconciliação concluída, **When** o disparo manual é usado de novo, **Then** nada muda em nenhum destino e a execução termina limpa.

---

### Edge Cases

- Um destino indisponível: o outro é reconciliado e a falha é reportada por destino, sem impedir o que deu certo.
- Credencial de publicação ausente: a execução falha no primeiro passo que precisa dela, com erro nomeado, e nada é escrito em nenhum destino.
- Tag da versão corrente já existente apontando para outro commit: reprovar, porque tag publicada é imutável.
- Estado já reconciliado: nenhum commit é criado em nenhum destino.
- Push aceito mas conteúdo divergente do planejado: reprovar na releitura, em vez de reportar sucesso.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A publicação MUST poder ser disparada manualmente, sem depender de mudança no conteúdo do plugin.
- **FR-002**: Uma única execução manual MUST levar ambos os destinos à versão corrente do canônico, criando a entrada onde ela não existir e atualizando onde existir.
- **FR-003**: A execução MUST reler o estado publicado no destino, a partir do repositório remoto, e MUST falhar quando ele não corresponder exatamente à release em `version` e nos quatro campos do pin.
- **FR-004**: A execução MUST verificar que a referência publicada resolve, no canônico, para o commit publicado.
- **FR-005**: A verificação MUST nomear cada divergência encontrada, em vez de reportar apenas reprovação.
- **FR-006**: A reconciliação MUST NOT republicar versões históricas que nunca chegaram aos destinos.
- **FR-007**: O gatilho manual MUST continuar disponível depois da reconciliação.

### Key Entities

- **Drift de publicação**: a distância entre o que o canônico declara e o que cada destino serve. No claude é uma versão atrasada; no codex é a ausência completa da entrada.
- **Verificação de estado publicado**: a releitura do índice a partir do remoto, comparada campo a campo com a release.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Depois da execução manual, os dois destinos declaram a versão corrente do canônico e apontam para o mesmo commit.
- **SC-002**: A execução que publica termina tendo relido o estado publicado, e essa releitura é o que autoriza o verde.
- **SC-003**: Uma segunda execução manual imediata não produz commit em nenhum destino.
- **SC-004**: A verificação reprova, em teste, cada uma das divergências possíveis: versão, cada campo do pin, entrada ausente e entrada duplicada.
- **SC-005**: O disparo manual continua listado e utilizável depois da reconciliação.

## Assumptions

Estas premissas corrigem, com evidência coletada em 2026-08-12, o que o handoff e o ROADMAP registravam.

- **O handoff descreve critérios do modelo antigo.** Ele pede a versão corrente "tanto no manifesto vendorizado quanto na entrada de marketplace" e "o diretório de testes ausente da cópia publicada". Os dois critérios pressupõem o espelhamento de conteúdo abandonado em ADR-0006: não existe cópia publicada, logo não existe manifesto vendorizado nem diretório de testes a excluir. O critério equivalente sob o modelo vigente é a entrada apontar, por `git-subdir`, para a tag e o commit publicados — é o que esta spec exige em FR-003.
- **O drift do claude é `2.4.1`, não `2.4.0`.** A entrada publicada em `cadugevaerd/claude-skills` declara `version: 2.4.1` com `source.ref: v2.4.1` e `source.sha: c6a9b0708f737dd9f13a3ca98c3b5fa2a00c4cbf`. O ROADMAP registrava `2.4.0`.
- **O codex não tem entrada alguma.** `cadugevaerd/codex-skills` tem 15 plugins e nenhum chamado `grill-with-docs`; a reconciliação cria a entrada lá.
- **O canônico está em `2.5.0`** e a maior tag publicada é `v2.4.1`. A tag da versão corrente ainda não existe e será criada pela própria execução.
- **A automação nunca rodou.** O workflow de publicação está registrado e tem zero execuções.
- **A credencial não está instalada.** O repositório canônico não tem o segredo de publicação. Instalá-lo é ato humano, decidido em ADR-0004, e a execução real depende dele; sem ele o workflow falha no primeiro passo que o consome, com erro nomeado, sem escrever em destino nenhum.
- **O gatilho manual já existe.** Foi entregue em FASE-002 e é verificado, não reimplementado, nesta fase.
