# Feature Specification: Verificação e publicação da milestone

**Feature Branch**: `feat/backlog-ssot`

**Created**: 2026-08-17

**Status**: Draft

**Input**: FASE-005 do work item `feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4`. Handoff canônico: `.grill/work-items/feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4/handoffs/FASE-005-SPECIFY-HANDOFF.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A portabilidade deixa de ser suposição (Priority: P1)

Cada uma das cinco fases anteriores fechou com a mesma ressalva: a suíte foi verificada num único sistema operacional, e o critério que exige três só pode ser verificado pela integração contínua. A ressalva se acumulou cinco vezes sem nunca ser resolvida.

**Why this priority**: é a única dívida técnica que atravessa a milestone inteira. Todo o resto foi verificado; isto foi adiado por impossibilidade local, não por escolha.

**Independent Test**: a branch subir e a matriz reportar verde nos três sistemas e nas duas versões de linguagem.

**Acceptance Scenarios**:

1. **Given** a branch empurrada, **When** a matriz executa, **Then** a suíte passa nos três sistemas operacionais e nas duas versões de linguagem.
2. **Given** a mesma execução, **When** o gate de versão avalia, **Then** ele reporta, porque roda em toda proposta de integração.
3. **Given** um sistema onde atalho não é suportado, **When** a suíte executa, **Then** os casos dependentes pulam em vez de falhar.

---

### User Story 2 - A publicação é um ato deliberado (Priority: P1)

A integração na branch principal dispara publicação para dois destinos públicos consumidos por terceiros.

**Why this priority**: é a única ação da milestone que não é reversível por reverter um commit. Uma vez publicado, outras pessoas consomem.

**Independent Test**: conferir, antes de publicar, que a versão é consistente nos oito lugares e que a matriz aprovou.

**Acceptance Scenarios**:

1. **Given** a matriz verde, **When** o operador autoriza a publicação, **Then** a versão publicada é a mesma nos oito lugares.
2. **Given** ausência de autorização, **When** o ciclo termina, **Then** nada é publicado e o trabalho permanece íntegro e revertível.
3. **Given** a milestone concluída, **When** o estado é consultado, **Then** ele descreve o que foi entregue e o que ficou pendente.

---

### Edge Cases

- Matriz reprovando em um único sistema: bloqueia a publicação; não há publicação parcial.
- Versão divergente entre os oito lugares: o contrato de distribuição reprova antes de qualquer publicação.
- Proposta de integração que não toca os caminhos filtrados pela matriz: o gate de versão continua reportando, porque mora em fluxo próprio sem esse filtro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A suíte completa MUST passar nos três sistemas operacionais suportados e nas duas versões de linguagem.
- **FR-002**: A versão MUST ser idêntica nos oito lugares fixados pelo contrato de distribuição.
- **FR-003**: Casos dependentes de recurso não suportado pela plataforma MUST pular, e não falhar.
- **FR-004**: Nenhuma publicação MUST ocorrer sem autorização explícita do operador.
- **FR-005**: O estado terminal da milestone MUST descrever o que foi entregue e o que permanece pendente.
- **FR-006**: Os defeitos corrigidos ao longo da milestone MUST ter regressão que reprovaria o comportamento anterior.

### Key Entities

- **Matriz de portabilidade**: execução da suíte por sistema operacional e versão de linguagem.
- **Contrato de distribuição**: conjunto dos oito lugares onde a versão precisa coincidir.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A suíte passa em seis combinações de sistema e versão de linguagem.
- **SC-002**: A versão coincide nos oito lugares, verificado por gate automatizado.
- **SC-003**: Cada um dos defeitos corrigidos na milestone tem ao menos uma regressão nomeada.
- **SC-004**: Nenhum artefato público é alterado sem autorização registrada.

## Assumptions

- A publicação é disparada pela integração na branch principal, filtrada pelos caminhos do plugin, e cria a etiqueta de versão e as entradas nos dois destinos públicos.
- O gate de versão vive em fluxo próprio, sem filtro de caminho, justamente para reportar em toda proposta de integração; um gate obrigatório que fica mudo prende a proposta para sempre.
- Registrar o gate de versão como verificação obrigatória na proteção da branch é ato humano de configuração de serviço, fora do alcance de qualquer commit. Permanece declarado como pendência.
- A verificação local já cobriu tudo que dispensa a matriz; o que resta depende de a branch subir.
