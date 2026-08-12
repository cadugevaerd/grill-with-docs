# Feature Specification: Deriva viva precisa

**Feature Branch**: `005-live-drift`

**Created**: 2026-08-12

**Status**: Draft

**Input**: Handoff `.grill/work-items/fix-high-defects-f03b31bb4b194b0683eee8f3a62493d0/handoffs/FASE-002-SPECIFY-HANDOFF.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A consulta de situação volta a significar algo (Priority: P1)

Quem consulta a situação de um work item em andamento, a partir do ramo dele, não recebe alarme só por ter feito commits.

**Why this priority**: É o objetivo inteiro. Hoje o alarme dispara a partir do primeiro commit que contenha o próprio registro, para todo work item, sempre — e o veredito global vai junto.

**Independent Test**: Criar um work item, commitar o bundle, consultar a situação a partir do mesmo ramo.

**Acceptance Scenarios**:

1. **Given** um work item em andamento com vários commits no seu ramo, **When** a situação é consultada, **Then** não há alarme de deriva e o veredito não é reprovado por esse motivo.
2. **Given** o mesmo work item com um bloqueio real registrado, **When** a situação é consultada, **Then** o bloqueio aparece e reprova.

---

### User Story 2 - Ler o registro do ramo errado continua alarmando (Priority: P1)

Quem consulta a situação de um work item em andamento a partir de outro ramo recebe alarme.

**Why this priority**: É o único sinal verdadeiro que a comparação carregava. Perdê-lo trocaria ruído por silêncio.

**Independent Test**: Criar o work item num ramo, trocar de ramo, consultar.

**Acceptance Scenarios**:

1. **Given** um work item em andamento cujo ramo registrado não é o ramo vivo, **When** a situação é consultada, **Then** há alarme de deriva.

---

### User Story 3 - Work item encerrado não alarma (Priority: P1)

Quem consulta um work item já concluído, a partir da linha principal, não recebe alarme.

**Why this priority**: Depois do ship o ramo de trabalho é mergeado e apagado, então a diferença passa a ser permanente e esperada. Sem este recorte, todo work item concluído vira alarme eterno — que é o estado de hoje.

**Independent Test**: Concluir um work item, marcá-lo terminal, consultar a partir de outro ramo.

**Acceptance Scenarios**:

1. **Given** um work item terminal lido de um ramo diferente do registrado, **When** a situação é consultada, **Then** não há alarme de deriva.

---

### Edge Cases

- Work item terminal lido do próprio ramo: sem alarme, pelos dois motivos.
- Work item em andamento cujo ramo registrado não existe mais: **sem alarme**. O protocolo entrega uma fase por ramo, então o ramo da criação morre no primeiro ship e a comparação volta a ser insatisfazível — o mesmo defeito, um nível acima. Corrigido durante a implementação, ver Assumptions.
- Registro de situação ausente ou de outra forma: o alarme de forma inválida continua valendo e é independente deste.
- Estado sem os campos de conclusão: tratado como não terminal, que é o comportamento conservador.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A comparação de commit vivo contra o commit registrado MUST NOT produzir alarme, porque o valor registrado é anterior ao próprio registro existir e nenhum estado posterior pode igualá-lo.
- **FR-002**: A comparação de ramo vivo contra o ramo registrado MUST produzir alarme enquanto o work item não for terminal **e** o ramo registrado ainda existir.
- **FR-003**: Um work item terminal MUST NOT produzir alarme de deriva, qualquer que seja o ramo de leitura.
- **FR-004**: A ausência dos campos que indicam conclusão MUST ser tratada como não terminal.
- **FR-005**: O commit registrado e o commit vivo MUST continuar visíveis na saída, para que quem precise da diferença possa calculá-la.
- **FR-006**: Os demais alarmes MUST permanecer inalterados, em especial os de forma inválida e de divergência de governança.

### Key Entities

- **Registro de identidade**: ramo e commit gravados na criação do work item, protegidos contra adulteração.
- **Estado vivo**: ramo e commit do repositório no momento da leitura.
- **Work item terminal**: aquele cujo trabalho está concluído e cujo marco foi fechado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um work item em andamento com muitos commits no próprio ramo não produz alarme de deriva.
- **SC-002**: O mesmo work item lido de outro ramo produz alarme.
- **SC-003**: Um work item terminal não produz alarme, lido de qualquer ramo.
- **SC-004**: Um bloqueio real continua reprovando o veredito.
- **SC-005**: O work item concluído na milestone anterior deixa de aparecer como bloqueado.

## Assumptions

- O commit registrado é o do instante da criação, anterior ao bundle existir; nenhum commit que contenha o bundle pode igualá-lo. Comprovado por experimento registrado em SGD-2.
- O ramo registrado é comparável enquanto o trabalho corre nele, e deixa de ser assim que o ramo é mergeado e apagado.
- A noção de terminal já existe no auditor, que exige trabalho concluído e marco fechado para emitir seu veredito final. A leitura de situação passa a usar a mesma fonte.
- O registro de identidade e o hash que o protege não são alterados por esta fase.

### Correção descoberta na implementação

A primeira versão desta spec recortava a comparação de ramo apenas por "não terminal". Ao aplicar a mudança e consultar a situação real, o work item **em andamento** continuou alarmando: o ramo da criação, `fix/high-defects`, foi apagado no ship da primeira fase, e o trabalho seguiu em outro ramo.

O protocolo entrega uma fase por ramo. Logo, para qualquer work item multi-fase, o ramo registrado morre na primeira entrega e a comparação passa a ser insatisfazível da segunda fase em diante — reproduzindo o defeito que esta fase existe para eliminar, um nível acima.

FR-002 ganhou a condição de o ramo registrado ainda existir. A regra final é: alarmar quando o ramo da criação está vivo, o work item não terminou, e a leitura acontece de outro lugar. Aí, e só aí, ler o bundle do lugar errado é anomalia.
