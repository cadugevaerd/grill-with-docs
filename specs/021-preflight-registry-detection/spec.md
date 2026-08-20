# Feature Specification: Detecção de extensão pelo registro

**Feature Branch**: `worktree-fix-preflight-ansi`

**Created**: 2026-08-20

**Status**: Draft

**Input**: Handoff auditado `GO` em `.grill/work-items/fix-preflight-ansi-09d77024258a45ecbe612a8d22ffea95/handoffs/FASE-001-SPECIFY-HANDOFF.md` (WHAT/WHY integral, 7 critérios de aceitação). Decisões em ADR-0001 a ADR-0004 do mesmo work item. Origem no backlog: SGD-16.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ambiente íntegro deixa de ser reprovado (Priority: P1)

O operador tem todas as extensões exigidas pelo workflow instaladas e habilitadas. Hoje o preflight afirma que três estão ausentes e uma está presente — e a única "presente" também está errada, porque foi reconhecida por uma palavra solta em texto descritivo, não pelo identificador. O operador precisa que o preflight aprove um ambiente que está de fato correto.

**Why this priority**: É o defeito de origem e o único que trava o ciclo. Sob verificação estrita, o trabalho não começa com o ambiente íntegro. Sem isto, nada mais importa.

**Independent Test**: Com as quatro extensões exigidas registradas e habilitadas, executar o preflight e conferir que o desfecho é aprovação e que nenhuma extensão aparece na lista de pendências obrigatórias.

**Acceptance Scenarios**:

1. **Given** as quatro extensões exigidas registradas e habilitadas, **When** o preflight é executado, **Then** o desfecho é aprovação e nenhuma extensão consta como pendência obrigatória.
2. **Given** o mesmo ambiente, **When** o relatório é lido, **Then** cada extensão traz a versão registrada, e não um valor nulo.
3. **Given** o mesmo ambiente, **When** o preflight é executado com verificação estrita, **Then** ele não bloqueia.

---

### User Story 2 - A causa relatada corresponde ao que foi observado (Priority: P1)

Quando algo está de fato errado, o operador precisa que o relatório diga qual é o problema e qual ação o resolve. Uma extensão registrada porém desabilitada não é uma extensão ausente, e mandar reinstalá-la desperdiça o tempo do operador e não corrige nada.

**Why this priority**: É metade do dano do defeito original. Um relatório que aponta a ação errada é pior que um relatório omisso, porque induz a agir errado com confiança.

**Independent Test**: Registrar uma extensão exigida como desabilitada, executar o preflight, e conferir que ela bloqueia com motivo de estado e com a ação de habilitar — nunca a de instalar.

**Acceptance Scenarios**:

1. **Given** um identificador exigido ausente do registro, **When** o preflight é executado, **Then** o item é reportado como não utilizável, com motivo de ausência e ação de instalação.
2. **Given** um identificador exigido presente no registro porém desabilitado, **When** o preflight é executado, **Then** o item bloqueia, o motivo declara que está registrada porém desabilitada, e a ação proposta é habilitar.
3. **Given** qualquer texto descritivo que contenha por acaso o nome de uma extensão, **When** o preflight é executado, **Then** nenhuma extensão é dada como presente por esse texto.

---

### User Story 3 - "Não sei" é diferente de "não está" (Priority: P2)

Quando a fonte de verdade não pode ser lida, o operador precisa saber que a verificação não aconteceu — não receber uma lista de extensões falsamente declaradas ausentes, com instruções para reinstalar coisas que podem estar perfeitamente instaladas.

**Why this priority**: É o modo de falha que a mudança de fonte introduz. Sem tratamento explícito, a correção trocaria um relato falso por outro.

**Independent Test**: Remover, corromper e versionar de forma desconhecida a fonte de verdade, em três execuções, e conferir que os três casos convergem no mesmo desfecho e que nenhuma extensão é declarada ausente.

**Acceptance Scenarios**:

1. **Given** a fonte de verdade ausente, **When** o preflight é executado, **Then** nenhuma extensão é declarada ausente e a causa aparece uma única vez como pendência própria.
2. **Given** a fonte de verdade corrompida ou com versão de contrato não reconhecida, **When** o preflight é executado, **Then** o desfecho é idêntico ao do caso anterior.
3. **Given** qualquer um desses casos, **When** o preflight é executado com verificação estrita, **Then** ele bloqueia.
4. **Given** qualquer um desses casos, **When** os itens de extensão são lidos, **Then** eles não trazem ação de instalação.

### Edge Cases

- Fonte de verdade legível mas sem nenhuma extensão registrada: todas as exigidas são ausentes, com ação de instalação — é ausência observada, não indeterminação.
- Fonte de verdade contendo extensões além das exigidas: são ignoradas; o veredito cobre apenas o que o workflow exige.
- Extensão exigida registrada, habilitada, porém sem versão: presença é afirmada; a versão ausente não invalida a observação.
- Verificação desligada por ambiente restrito: continua nunca sendo reportada como aprovação.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST determinar a presença de cada extensão exigida a partir do registro de extensões, e não de saída formatada para leitura humana.
- **FR-002**: O sistema MUST identificar cada extensão por seu identificador exato, de modo que nenhum texto livre possa satisfazer a verificação.
- **FR-003**: O sistema MUST declarar presente somente a extensão que esteja registrada **e** habilitada.
- **FR-004**: O sistema MUST reportar extensão registrada porém desabilitada como não utilizável, com motivo próprio e com ação de habilitar.
- **FR-005**: O sistema MUST tratar registro ausente, ilegível e de versão de contrato não reconhecida como o mesmo desfecho: presença não observada.
- **FR-006**: O sistema MUST distinguir presença não observada de ausência observada, e MUST NOT propor instalação no primeiro caso.
- **FR-007**: O sistema MUST reportar a impossibilidade de ler o registro uma única vez, como pendência própria, e não replicada por extensão.
- **FR-008**: O sistema MUST bloquear, sob verificação estrita, tanto a ausência observada quanto a presença não observada.
- **FR-009**: O sistema MUST expor a versão registrada de cada extensão presente.
- **FR-010**: O sistema MUST manter o veredito reproduzível sem rede e sem depender das ferramentas externas verificadas.
- **FR-011**: O sistema MUST incrementar a versão publicada e mantê-la idêntica em todos os pontos fixados pelo contrato de distribuição, com registro correspondente no changelog.

### Key Entities

- **Registro de extensões**: fonte de verdade sobre o que está instalado. Declara uma versão de contrato e, por identificador exato, a versão e o estado de habilitação de cada extensão.
- **Item de dependência**: unidade do relatório. Carrega identificador, situação observada, motivo quando não utilizável, ação proposta e versão quando aplicável.
- **Situação observada**: presente, não utilizável ou não observada. As três são mutuamente exclusivas e a terceira nunca é afirmação de ausência.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em ambiente com as quatro extensões exigidas registradas e habilitadas, o preflight aprova em 100% das execuções, incluindo sob verificação estrita.
- **SC-002**: Nenhuma extensão pode ser dada como presente sem que seu identificador exato conste do registro — zero falsos positivos por texto livre.
- **SC-003**: Para cada situação não utilizável, a ação proposta resolve a causa relatada — zero instruções de instalação para item já instalado.
- **SC-004**: As três formas de registro não legível produzem desfecho idêntico e nenhuma delas declara extensão ausente.
- **SC-005**: A suíte cobre os cenários acima e conclui sem rede e sem exigir as ferramentas externas verificadas, nos três sistemas operacionais e nas duas versões de linguagem da matriz de integração.
- **SC-006**: A versão publicada é idêntica em todos os pontos fixados pelo contrato de distribuição — divergência reprovada pelo gate.

## Assumptions

- O registro de extensões é mantido pela ferramenta que instala as extensões e é atualizado por ela em instalação, remoção, habilitação e desabilitação. O sistema apenas lê.
- Depender desse registro é depender de um contrato interno da ferramenta externa. A dependência é assumida deliberadamente (ADR-0001) e declarada de forma visível e revisável (ADR-0002), em vez de implícita no código.
- Desabilitar uma extensão exigida pelo workflow é divergir do workflow declarado. Quem quiser operar sem ela altera o workflow, que é versionado e revisável — não o estado local invisível (ADR-0003).
- O conjunto de situações observadas cresce sem trocar o identificador de versão do contrato de relatório; o custo é absorvido pela suíte interna, e o consumidor que compara com "presente" permanece correto (ADR-0004).
- O parser da saída formatada é removido, não mantido em paralelo.
