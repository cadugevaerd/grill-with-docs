# Feature Specification: Gate de bump de versão

**Feature Branch**: `001-bump-gate`

**Created**: 2026-08-11

**Status**: Draft

**Input**: Handoff `.grill/work-items/feature-release-repo-sync-97a2bb32d4884a129ec2e845b76894b7/handoffs/FASE-001-SPECIFY-HANDOFF.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mudança de plugin sem bump é barrada (Priority: P1)

Alguém abre uma pull request que altera o conteúdo distribuído do plugin mas esquece de subir a versão declarada. A verificação automática reprova a pull request e diz qual versão está declarada e que ela precisa aumentar.

**Why this priority**: É a razão de existir da funcionalidade. Sem ela, conteúdo diferente é publicado sob uma versão já distribuída, e quem tem aquela versão instalada nunca recebe a mudança.

**Independent Test**: Abrir uma pull request que altere um arquivo do conteúdo do plugin sem tocar na versão, e observar a reprovação com a mensagem esperada. Entrega valor sozinha: já impede a classe inteira de erro.

**Acceptance Scenarios**:

1. **Given** uma pull request que altera um arquivo do conteúdo distribuído do plugin e mantém a versão declarada, **When** a verificação roda, **Then** a pull request é reprovada e a mensagem nomeia a versão declarada e a exigência de aumentá-la.
2. **Given** uma pull request que altera o conteúdo do plugin e **reduz** a versão declarada, **When** a verificação roda, **Then** a pull request é reprovada.

---

### User Story 2 - Mudança de plugin com bump passa (Priority: P1)

Alguém abre uma pull request que altera o conteúdo do plugin e sobe a versão. A verificação aprova sem atrito adicional.

**Why this priority**: Sem este caminho a funcionalidade bloquearia todo trabalho legítimo. É a contraparte inseparável da história 1 e tem a mesma prioridade.

**Independent Test**: Abrir uma pull request que altere o conteúdo do plugin e suba a versão, e observar aprovação.

**Acceptance Scenarios**:

1. **Given** uma pull request que altera o conteúdo do plugin e aumenta a versão declarada, **When** a verificação roda, **Then** a pull request é aprovada pela verificação.

---

### User Story 3 - Mudança fora do plugin não exige bump (Priority: P2)

Alguém abre uma pull request que mexe apenas em testes, documentação de repositório ou automação, sem tocar no conteúdo distribuído. A verificação não exige bump.

**Why this priority**: Evita fricção falsa. Sem isso, toda correção de teste exigiria uma versão nova, quebrando a correspondência entre versão e conteúdo no sentido inverso — versões novas sem mudança no que é distribuído.

**Independent Test**: Abrir uma pull request que altere apenas um arquivo de teste e observar aprovação sem bump.

**Acceptance Scenarios**:

1. **Given** uma pull request que não altera nenhum arquivo do conteúdo distribuído do plugin, **When** a verificação roda, **Then** a pull request é aprovada sem exigir mudança de versão.

---

### Edge Cases

- Pull request que **remove** arquivos do conteúdo do plugin sem alterar nenhum outro: conta como alteração de conteúdo e exige bump.
- Pull request que altera o conteúdo do plugin e também arquivos fora dele: exige bump, porque houve alteração de conteúdo distribuído.
- Pull request cuja única mudança no conteúdo do plugin é a própria versão: é um bump, portanto aprovada.
- Pull request aberta a partir de uma base desatualizada, onde a versão da base já é menor que a atual da linha principal: a comparação é contra a base de merge da pull request, não contra a linha principal, para que o autor não seja reprovado por trabalho de terceiros.
- Versão declarada em formato inválido ou ausente: reprovar, porque não é possível decidir se aumentou.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A verificação MUST determinar se a pull request altera o conteúdo distribuído do plugin, considerando adição, modificação e remoção de arquivos.
- **FR-002**: Quando houver alteração do conteúdo distribuído, a verificação MUST exigir que a versão declarada do plugin seja estritamente maior que a versão declarada na base de merge da pull request.
- **FR-003**: Quando não houver alteração do conteúdo distribuído, a verificação MUST aprovar sem exigir mudança de versão.
- **FR-004**: Ao reprovar, a verificação MUST informar a versão declarada na base, a versão declarada na pull request e a exigência de que a versão aumente.
- **FR-005**: A verificação MUST reprovar quando a versão declarada estiver ausente ou em formato que impeça comparação de ordem.
- **FR-006**: A verificação MUST NOT reimplementar as checagens de coerência interna de versão que a validação de distribuição já executa.
- **FR-007**: A verificação MUST rodar como parte da validação automática de pull request, e seu resultado MUST bloquear a integração quando reprovar.

### Key Entities

- **Conteúdo distribuído do plugin**: o conjunto de arquivos que compõem o pacote entregue aos consumidores; alterações nele são o que torna o bump obrigatório.
- **Versão declarada**: o número de versão do plugin, comparável por ordem, usado pelos consumidores para identificar o que instalaram.
- **Base de merge**: o ponto de partida da pull request, contra o qual a versão é comparada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os quatro cenários do handoff — alteração fora do plugin sem bump, alteração no plugin sem bump, alteração no plugin com bump, alteração no plugin com versão reduzida — produzem, cada um, o resultado esperado, verificável de forma repetível.
- **SC-002**: Nenhuma pull request que altere o conteúdo distribuído consegue ser integrada mantendo a versão anterior.
- **SC-003**: A mensagem de reprovação permite a quem a lê corrigir sem consultar outra fonte: ela nomeia as duas versões comparadas e o que se espera.
- **SC-004**: Pull requests que não tocam o conteúdo distribuído não sofrem nenhuma exigência nova em relação ao comportamento atual.

## Assumptions

- A comparação de versões é feita contra a base de merge da pull request, e não contra a linha principal, porque só a base é estável do ponto de vista do autor.
- A verificação se aplica a pull requests. Integração direta na linha principal, sem pull request, não oferece base de comparação confiável e fica fora do alcance desta verificação.
- Mudanças exclusivamente em testes não alteram o conteúdo distribuído, porque o pacote entregue não os contém.
- A validação de distribuição já existente continua responsável por garantir que a versão esteja declarada de forma coerente em todos os pontos onde aparece; esta verificação apenas compara ordem entre duas revisões.
- Não há mecanismo de exceção: não existe forma de aprovar uma alteração de conteúdo sem bump.
