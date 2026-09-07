# Feature Specification: Ponytail na stack oficial

**Feature Branch**: `cadugevaerd/chore-add-ponytail`

**Created**: 2026-09-07

**Status**: Draft

**Input**: Handoff `FASE-001-SPECIFY-HANDOFF.md` do work item `feature-add-ponytail-d8c0bd7e8ffd4442a806b2e1067ed06c`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saber se o ponytail está presente antes de começar (Priority: P1)

Quem conduz uma sessão do grill-with-docs roda a verificação prévia de dependências e
quer saber, junto com o Spec Kit e o backlog, se o ponytail está instalado no
harness ativo, em qual versão e de onde essa informação veio. Se estiver ausente
ou abaixo da versão mínima, o relatório nomeia exatamente o que falta e como
remediar no harness em uso — sem que ninguém precise lembrar os comandos.

**Why this priority**: É o núcleo da feature. Hoje a presença do ponytail é
invisível: depende da máquina de quem conduz a sessão, e ninguém descobre a
falta até sentir a diferença de comportamento.

**Independent Test**: Rodar a verificação prévia em um ambiente com o ponytail
instalado e em outro sem ele; conferir que o relatório distingue os dois casos e
nomeia a remediação no segundo.

**Acceptance Scenarios**:

1. **Given** o ponytail instalado na versão mínima ou superior no harness ativo, **When** a verificação prévia roda, **Then** o relatório lista o ponytail como presente, com a versão e a origem da leitura.
2. **Given** o ponytail ausente no harness ativo, **When** a verificação prévia roda sem autorização de instalação, **Then** o relatório lista o ponytail como ausente, com a sequência de remediação do harness ativo, e a criação do work item segue, com o ponytail listado entre os obrigatórios ausentes.
3. **Given** o ponytail instalado abaixo da versão mínima, **When** a verificação prévia roda, **Then** o relatório lista o ponytail como desatualizado, com a versão encontrada e a remediação de reinstalar.
4. **Given** a verificação prévia executada com a exigência fail-closed de dependências, **When** o ponytail está ausente, **Then** a verificação recusa nomeando a dependência ausente, como faz com qualquer outra dependência obrigatória.
5. **Given** a detecção de dependências desligada por ambiente isolado, **When** a verificação prévia roda, **Then** o ponytail é tratado como as demais dependências: não verificado e nunca reportado como presente.

---

### User Story 2 - Instalar pelo dono do artefato, com autorização explícita (Priority: P1)

Quem conduz a sessão recebe o relatório de ausência, pergunta ao humano se pode
instalar, e reexecuta a verificação com a autorização de instalação. A instalação
é feita pela ferramenta do próprio harness (registrar a fonte do plugin e
instalá-lo), nunca pelo núcleo do grill-with-docs, e o relatório final mostra o
ponytail presente.

**Why this priority**: Sem isso a detecção aponta o problema mas obriga o humano
a executar comandos à mão, o que é exatamente o que a autorização delegada já
evita para as demais dependências.

**Independent Test**: Em ambiente sem o ponytail, reexecutar a verificação com a
autorização de instalação e observar que a ferramenta do harness é chamada na
sequência declarada e que, ao final, o ponytail é reportado como presente.

**Acceptance Scenarios**:

1. **Given** o ponytail ausente e a autorização de instalação concedida, **When** a verificação prévia roda, **Then** a fonte do plugin é registrada e o plugin é instalado pela ferramenta do harness ativo, nessa ordem, e o relatório final reporta o ponytail presente.
2. **Given** o ponytail ausente e nenhuma autorização de instalação, **When** a verificação prévia roda, **Then** nenhuma instalação é executada e o relatório apenas nomeia a remediação.
3. **Given** o harness ativo é o Codex, **When** a instalação é autorizada, **Then** a sequência executada é a da ferramenta do Codex, não a do Claude Code.
4. **Given** a instalação delegada falha, **When** a verificação prévia termina, **Then** o relatório mostra a falha nomeada e o ponytail continua ausente, sem o núcleo tentar outro caminho.

---

### User Story 3 - Encontrar o ponytail documentado neste repositório (Priority: P2)

Alguém que abre este repositório em Claude Code ou Codex lê as instruções do
agente e encontra o ponytail declarado como parte da stack: o que ele é, o que a
verificação prévia confere e como instalar. No Claude Code, o plugin já vem
habilitado para o projeto sem configuração manual.

**Why this priority**: Fecha o dogfooding — o repositório que publica a exigência
precisa ser o primeiro a cumpri-la — mas não altera o comportamento do plugin
para consumidores.

**Independent Test**: Abrir o repositório num clone limpo, ler as instruções do
agente para Claude Code e para Codex e confirmar que ambas declaram o ponytail; no
Claude Code, confirmar que o plugin aparece habilitado para o projeto.

**Acceptance Scenarios**:

1. **Given** um clone deste repositório, **When** as instruções do agente para Claude Code são lidas, **Then** existe uma seção que declara o ponytail na stack, o que o preflight verifica e como instalar.
2. **Given** o mesmo clone, **When** as instruções do agente para Codex são lidas, **Then** elas existem e declaram o mesmo conteúdo essencial mais o modo de trabalho do ponytail.
3. **Given** o mesmo clone aberto em Claude Code, **When** os plugins do projeto são consultados, **Then** o ponytail está habilitado por configuração versionada.
4. **Given** a documentação pública do plugin, **When** a seção de dependências é lida, **Then** o ponytail aparece entre as dependências declaradas, com o limite de que no Codex "instalado" não prova "habilitado".

---

### Edge Cases

- Ponytail instalado em um harness e ausente no outro: só o harness ativo da sessão é consultado; o relatório não mistura os dois.
- Registro de plugins do harness ilegível ou malformado: o ponytail é reportado como indeterminado, nunca como ausente, e nada é proposto para instalar.
- Mais de uma versão do ponytail no cache do Codex: a maior versão presente é a reportada.
- Ponytail instalado mas desabilitado no Claude Code: reportado como presente; a feature verifica instalação, não habilitação.
- Ferramenta do harness ausente do PATH durante a instalação autorizada: a instalação falha nomeada e o ponytail permanece ausente.
- Detecção desligada por ambiente isolado: o ponytail segue a regra geral e nunca é reportado como presente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A verificação prévia de dependências MUST declarar o ponytail como dependência obrigatória, ao lado das demais, com versão mínima 4.9.0.
- **FR-002**: A verificação prévia MUST reportar o ponytail como presente, desatualizado ou ausente para o harness ativo (Claude Code ou Codex), informando versão encontrada e origem da leitura quando houver.
- **FR-003**: A detecção MUST ler apenas os registros em disco do harness ativo, sem executar processo algum, e MUST reportar indeterminado quando o registro for ilegível.
- **FR-004**: Quando o ponytail estiver ausente ou desatualizado, o relatório MUST nomear a sequência de remediação do harness ativo: registrar a fonte do plugin e instalá-lo.
- **FR-005**: Com a autorização de instalação, a verificação prévia MUST executar a sequência de remediação pela ferramenta do harness ativo, na ordem declarada, e MUST NOT baixar bytes por conta própria.
- **FR-006**: Sem a autorização de instalação, a verificação prévia MUST NOT executar instalação alguma.
- **FR-007**: A criação do work item MUST reportar o estado do ponytail no mesmo relatório de dependências das demais.
- **FR-008**: Sob a exigência fail-closed de dependências, o ponytail ausente MUST recusar a operação como qualquer dependência obrigatória ausente.
- **FR-009**: Com a detecção desligada por ambiente isolado, o ponytail MUST NOT ser reportado como presente.
- **FR-010**: As dependências já declaradas MUST manter comportamento e formato de relatório idênticos aos atuais.
- **FR-011**: As instruções do agente deste repositório para Claude Code MUST declarar o ponytail na stack, o que a verificação prévia confere e como instalar.
- **FR-012**: Este repositório MUST passar a ter instruções do agente para Codex com o mesmo conteúdo essencial e o modo de trabalho do ponytail.
- **FR-013**: Este repositório MUST habilitar o ponytail para o projeto no Claude Code por configuração versionada.
- **FR-014**: A documentação pública do plugin MUST mencionar o ponytail entre as dependências e declarar que no Codex "instalado" não prova "habilitado".
- **FR-015**: Toda alteração publicada MUST vir com incremento de versão compatível (minor) refletido em todos os pontos de versão que o validador de distribuição fixa.

### Key Entities

- **Dependência declarada**: item da stack oficial com identificador, obrigatoriedade, versão mínima, motivo e remediação por harness.
- **Registro de plugins do harness**: fonte em disco, própria de cada harness, que lista plugins instalados e suas versões.
- **Relatório de dependências**: saída da verificação prévia e da criação do work item; por dependência, estado, versão, origem e remediação.
- **Autorização de instalação**: decisão explícita do humano que permite à verificação prévia delegar instalações ao dono de cada artefato.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em ambiente com o ponytail instalado e em ambiente sem ele, a verificação prévia produz relatórios distintos e corretos em 100% das execuções, para cada um dos dois harnesses.
- **SC-002**: Em ambiente sem o ponytail, uma única reexecução autorizada deixa o ponytail presente, sem intervenção manual além da autorização.
- **SC-003**: A suíte de validação completa passa na matriz de integração (três sistemas operacionais, duas versões de Python) sem acesso à rede e sem as ferramentas dos harnesses instaladas.
- **SC-004**: Nenhuma dependência já existente muda de estado ou de formato no relatório após a mudança (comparação antes/depois idêntica).
- **SC-005**: Um leitor das instruções do agente, em qualquer dos dois harnesses, localiza o que é o ponytail e como instalá-lo em uma única seção.

## Assumptions

- O harness ativo é sempre informado explicitamente (Claude Code ou Codex); o default salvo no projeto não substitui essa escolha.
- A fonte do plugin é o marketplace público do autor do ponytail; confiar nela é decisão declarada no manifesto de dependências e revisável no diff, como já ocorre com o catálogo community do Spec Kit.
- A instalação ocorre no escopo do usuário do harness; nenhum arquivo do projeto consumidor é escrito pela instalação.
- Verificar se o plugin está habilitado fica fora do escopo; no Codex não há registro em disco conhecido que distinga instalado de habilitado.
- Outros harnesses suportados pelo ponytail (Copilot, Cursor etc.) ficam fora do escopo; a stack do grill-with-docs cobre Claude Code e Codex.
- Os hooks do ponytail dependem de `node` no PATH para ativação automática; sem `node` as skills continuam disponíveis. Isso é documentado, não verificado.
- A versão mínima 4.9.0 é a única verificada nos dois harnesses nesta sessão.
