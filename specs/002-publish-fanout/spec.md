# Feature Specification: Publicação fan-out nos marketplaces

**Feature Branch**: `002-publish-fanout`

**Created**: 2026-08-11

**Status**: Draft

**Input**: Handoff `.grill/work-items/feature-release-repo-sync-97a2bb32d4884a129ec2e845b76894b7/handoffs/FASE-002-SPECIFY-HANDOFF.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Merge que muda o plugin publica nos dois marketplaces (Priority: P1)

Alguém faz merge na linha principal alterando o conteúdo distribuído do plugin. Sem nenhuma ação manual, os dois marketplaces passam a servir a mesma versão e o mesmo conteúdo do repositório canônico.

**Why this priority**: É o objetivo inteiro. Hoje a atualização é manual: o Claude serve `v2.4.1` enquanto o canônico está em `2.5.0`, e o Codex não serve nada.

**Independent Test**: Publicar e observar, em cada índice, `version`, `source.ref` e `source.sha` correspondendo ao commit publicado.

**Acceptance Scenarios**:

1. **Given** um merge que altera o conteúdo distribuído, **When** a publicação roda, **Then** existe uma tag no canônico para a versão declarada e a entrada de cada marketplace aponta para essa tag e esse commit, com a versão sincronizada.
2. **Given** um merge que não altera o conteúdo distribuído, **When** a publicação é avaliada, **Then** nada é publicado.

---

### User Story 2 - Publicação é idempotente e reexecutável (Priority: P1)

Uma execução repetida sobre um estado já publicado não produz mudança, e uma execução após falha parcial converge.

**Why this priority**: Sem isso, a decisão de jobs independentes por marketplace fica insegura: o re-run precisa ser inofensivo.

**Independent Test**: Rodar a publicação duas vezes seguidas e observar que a segunda não altera nada.

**Acceptance Scenarios**:

1. **Given** um marketplace já em dia, **When** a publicação roda, **Then** nada muda e a execução termina limpa.
2. **Given** um marketplace atrasado e outro em dia, **When** a publicação roda, **Then** só o atrasado muda.

---

### User Story 3 - Entrada ausente é criada, não ignorada (Priority: P1)

Um marketplace que ainda não conhece o plugin passa a conhecê-lo, com entrada no formato que aquele marketplace usa.

**Why this priority**: Evidência colhida durante a especificação: `codex-skills` não tem nenhuma entrada para este plugin. Sem esta história, a publicação no Codex simplesmente não aconteceria, e o silêncio pareceria sucesso.

**Independent Test**: Publicar contra um marketplace sem a entrada e observar entrada criada com os campos que os vizinhos usam.

**Acceptance Scenarios**:

1. **Given** um marketplace sem entrada para o plugin, **When** a publicação roda, **Then** a entrada é criada com `source` do tipo `git-subdir` e os campos exigidos por aquele índice.
2. **Given** um marketplace com entrada existente, **When** a publicação roda, **Then** apenas `version`, `source.ref` e `source.sha` mudam, e o texto descritivo curado é preservado.

---

### Edge Cases

- Tag já existente apontando para outro commit: reprovar, porque uma tag publicada é imutável e reescrevê-la mudaria o que já foi distribuído.
- Tag já existente apontando para o mesmo commit: seguir, é reexecução legítima.
- Um marketplace indisponível: o outro é publicado; a falha é reportada por alvo.
- Marketplace cuja entrada existe mas aponta para caminho diferente do convencionado: reprovar em vez de adivinhar.
- Conteúdo idêntico ao já publicado: nenhum commit é criado, para não gerar ruído de histórico.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A publicação MUST criar, no repositório canônico, uma tag imutável `vX.Y.Z` correspondente à versão declarada, apontando para o commit publicado.
- **FR-002**: A publicação MUST atualizar, na entrada de marketplace de cada agregador, a versão e a referência (`ref` e `sha`) para a tag e o commit publicados.
- **FR-003**: A publicação MUST preservar os demais campos da entrada de marketplace, incluindo o texto descritivo, que é curado por marketplace.
- **FR-004**: A publicação MUST criar a entrada quando ela não existir, usando o schema observado naquele marketplace.
- **FR-005**: A publicação MUST ser idempotente: aplicada sobre um estado já correto, não produz mudança nem commit.
- **FR-006**: A publicação MUST tratar cada marketplace de forma independente, de modo que a falha em um não impeça o outro.
- **FR-007**: A publicação MUST rodar após merge na linha principal, e somente quando o conteúdo distribuído mudou.
- **FR-008**: A publicação MUST poder ser disparada manualmente, sem depender de um merge.
- **FR-009**: A publicação MUST falhar de forma explícita quando não puder determinar onde escrever, em vez de adivinhar caminho ou schema.

### Key Entities

- **Release**: a tag imutável `vX.Y.Z` no repositório canônico, apontando para um commit específico. É o que os marketplaces referenciam.
- **Entrada de marketplace**: o registro do plugin no índice de cada agregador. Carrega `version` e um `source` do tipo `git-subdir` com `url`, `path`, `ref` e `sha`.
- **Marketplace alvo**: um repositório agregador, identificado por repositório e caminho do índice.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após um merge que altera o conteúdo distribuído, ambos os marketplaces declaram a mesma versão do canônico, sem intervenção manual.
- **SC-002**: Uma segunda execução imediata não produz nenhum commit nos marketplaces.
- **SC-003**: A referência publicada em cada marketplace resolve para o commit exato que foi publicado, e não para um ramo móvel.
- **SC-004**: O marketplace que hoje não conhece o plugin passa a conhecê-lo, com entrada válida segundo o formato dos seus vizinhos.
- **SC-005**: Nenhuma execução consegue escrever em destino que não seja um dos marketplaces declarados.

## Assumptions

Estas premissas substituem as que a fase carregava antes. A evidência anterior vinha de um checkout local 70 commits à frente do `origin` e não empurrado; foi corrigida por inspeção dos repositórios publicados.

- Este plugin **não é vendorizado**. A entrada publicada em `claude-skills` usa `source` do tipo `git-subdir`, apontando para o repositório canônico, subdiretório `plugin`, fixado por `ref` e `sha`. É o único dos 16 plugins de lá que usa esse mecanismo; os outros 15 vendorizam.
- `codex-skills` não tem entrada alguma para este plugin, e seus 15 plugins vendorizam.
- O formato de marketplace do Codex aceita `git-subdir`: o binário `codex-cli` 0.139.0 declara as variantes `RawMarketplaceManifestPluginSourceObject::{Local, GitSubdir, Url}`, com `GitSubdir` de quatro elementos — o mesmo shape `{url, path, ref, sha}` em uso no Claude.
- Publicar, portanto, é criar a tag no canônico e atualizar `version`, `ref` e `sha` em dois arquivos de índice. Nenhum conteúdo é copiado para os agregadores.
- A credencial decidida em ADR-0004 é fornecida como segredo do repositório. Sua instalação é ato humano e não pertence a esta fase.
- Enquanto o segredo não existir, a publicação real não pode ser exercitada; a prova nesta fase é local, contra clones dos dois marketplaces.
