# Feature Specification: Detecção de skill sombreada no preflight

**Feature Branch**: `feat/backlog-ssot`

**Created**: 2026-08-17

**Status**: Draft

**Input**: FASE-006 do work item `feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4`. Handoff canônico: `.grill/work-items/feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4/handoffs/FASE-006-SPECIFY-HANDOFF.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A sombra deixa de ser silenciosa (Priority: P1)

Um operador instala o plugin numa máquina que já tem uma skill pessoal com o mesmo nome. O comando de sessão resolve para a pessoal, que não tem os subcomandos do protocolo. Nada avisa: a descoberta vem de um argumento não fazer sentido para quem respondeu.

**Why this priority**: é o defeito inteiro. Um operador menos atento conclui que o plugin está quebrado, e não que está sombreado.

**Independent Test**: montar um diretório de skills com um nome do plugin duplicado, rodar a inspeção de ambiente e obter o relato.

**Acceptance Scenarios**:

1. **Given** um ambiente onde um nome publicado pelo plugin também existe como skill pessoal, **When** o operador inspeciona o ambiente, **Then** o relato nomeia a skill sombreada e onde ela está.
2. **Given** o mesmo ambiente, **When** a sombra é por atalho para outro lugar, **Then** o relato mostra também o destino resolvido.
3. **Given** um ambiente limpo, **When** o operador inspeciona, **Then** nenhum alarme é emitido.
4. **Given** um nome duplicado que **não** pertence ao plugin, **When** o operador inspeciona, **Then** nada é reportado, porque o plugin não opina sobre nomes de terceiros.

---

### User Story 2 - Remover exige autorização (Priority: P2)

Um operador quer desfazer a sombra sem sair do fluxo.

**Why this priority**: sem isso, cada ambiente novo exige intervenção manual. Mas remover apaga arquivo fora do repositório, então não pode ser efeito colateral de um diagnóstico.

**Independent Test**: rodar a inspeção com a autorização e conferir que a cópia sombreadora desapareceu e a remoção foi confirmada no relato.

**Acceptance Scenarios**:

1. **Given** um ambiente com sombra, **When** o operador inspeciona sem autorização, **Then** a sombra é reportada e nada é apagado.
2. **Given** o mesmo ambiente, **When** o operador inspeciona com a autorização explícita, **Then** a cópia sombreadora é removida e a remoção aparece no relato.
3. **Given** uma sombra por atalho, **When** a remoção é autorizada, **Then** apenas o atalho é removido, e não o destino que ele aponta.

---

### Edge Cases

- Atalho quebrado com nome do plugin: contado como sombra, porque continua ocupando o nome.
- Sombra existente em mais de um lugar ao mesmo tempo: todas são reportadas, não apenas a primeira.
- Diretório de skills inexistente: não é erro, é ausência de sombra.
- Remoção autorizada mas sem permissão de escrita: recusa nomeada, e o relato continua mostrando a sombra.
- Nome do plugin presente apenas como skill do próprio plugin: não é sombra.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A inspeção de ambiente MUST detectar quando um nome publicado pelo plugin também existe como skill pessoal ou de projeto.
- **FR-002**: A detecção MUST cobrir apenas os nomes que o próprio plugin publica.
- **FR-003**: O relato MUST nomear cada sombra e o caminho onde ela está.
- **FR-004**: Quando a sombra for um atalho, o relato MUST incluir o destino resolvido.
- **FR-005**: Um atalho quebrado com nome do plugin MUST ser contado como sombra.
- **FR-006**: A detecção MUST reportar todas as sombras encontradas, não apenas a primeira.
- **FR-007**: Por padrão a inspeção MUST apenas reportar, sem remover e sem impedir.
- **FR-008**: A remoção MUST exigir autorização explícita.
- **FR-009**: Quando a sombra for um atalho, a remoção MUST remover apenas o atalho, preservando o destino.
- **FR-010**: A ausência do diretório de skills MUST ser tratada como ausência de sombra, não como erro.
- **FR-011**: Falha ao remover MUST ser reportada de forma nomeada, sem interromper o restante da inspeção.
- **FR-012**: A cobertura automatizada MUST usar diretórios sintéticos e nunca tocar o ambiente real do operador.

### Key Entities

- **Nome publicado**: nome de skill que o plugin distribui.
- **Sombra**: presença do mesmo nome fora do plugin, num lugar que vence a resolução.
- **Destino resolvido**: para onde um atalho aponta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Toda sombra de nome publicado é reportada, em 100% dos casos montados.
- **SC-002**: Nenhum nome fora do conjunto publicado gera relato.
- **SC-003**: A inspeção padrão não remove nada, em 100% das execuções.
- **SC-004**: Com autorização, a sombra é removida e o destino de um atalho permanece.
- **SC-005**: A suíte automatizada passa nos três sistemas suportados sem tocar diretórios reais.

## Assumptions

- O defeito foi observado nesta sessão: um atalho em `~/.claude/skills` apontando para `~/.agents/skills` venceu a skill homônima do plugin, e o comando de sessão resolveu para a versão sem os subcomandos do protocolo.
- O alcance fica nos nomes do próprio plugin porque é sobre eles que ele tem autoridade. Varrer o ambiente atrás de duplicata qualquer produziria falso positivo e obrigaria a acompanhar o layout de skill de cada agente hospedeiro.
- Remoção automática está descartada: destruiria uma skill pessoal que o operador talvez quisesse apenas renomear.
- A inspeção não decide qual cópia vence a resolução do agente hospedeiro; ela reporta a coexistência, que é o fato verificável.
