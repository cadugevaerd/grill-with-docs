# Feature Specification: Metadados da constituição em suas três formas reais

**Work item**: `fix-constitution-metadata-a43184cce3ae4ae1be0e3bbcc0aa30b1`
**Rota**: bugfix
**Laudo**: `specs/022-constitution-metadata-formats/laudo.md`
**Origem**: relato de sessão consumidora rodando o plugin 3.3.0, reproduzido em 3.3.1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Constituição do Spec Kit deixa de ser reprovada (Priority: P1)

Um projeto inicializa o grill sobre uma constituição já existente, gerada pelo
`speckit-constitution`. O `init` a preserva byte a byte. O `audit` precisa auditá-la sem inventar
defeito.

**Por que P1**: hoje o veredito é sempre `NO-GO` / `ARTIFACT-INVALID` com quatro achados falsos, e
como qualquer finding bloqueia, o projeto inteiro fica travado por um defeito do plugin.

**Teste de aceitação**: uma constituição preenchida a partir do template oficial do Spec Kit,
com rodapé `**Version**: X | **Ratified**: Y | **Last Amended**: Z` e `## Governance` com prosa,
não produz nenhum finding de `constitution:`.

### User Story 2 - A forma que o próprio plugin escreve é auditada (Priority: P1)

O `init` materializa `assets/GRILL-CONSTITUTION.template.md`, que usa bullets `- version:`. Essa
forma nunca passou pelo `audit` em teste.

**Por que P1**: é a forma que o plugin gera em todo projeto novo. Sem cobertura, uma mudança no
template ou no parser quebra o caminho principal em silêncio.

**Teste de aceitação**: o asset shipado, com `{{RATIFIED}}`/`{{LAST_AMENDED}}` substituídos como
`grill_workspace.py` faz, audita sem nenhum finding de `constitution:`.

### User Story 3 - Falta real de metadado continua reprovando (Priority: P1)

Uma constituição sem versão, sem datas e sem governança não é auditável e precisa continuar
bloqueando.

**Por que P1**: a cláusula "Fail-closed sem waiver" da Constituição não admite que a correção do
falso positivo abra um falso negativo.

**Teste de aceitação**: constituição só com título e princípios produz os quatro findings.

### Edge Cases

- O template oficial traz um rodapé de exemplo dentro de comentário HTML
  (`<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 ... -->`). Não pode virar valor.
- `## Governance` presente mas sem prosa é governança vazia, não governança satisfeita.
- Constituição em português usa `## Governança`.
- Documento que declare o campo **e** tenha rodapé: o campo declarado prevalece.
- Prosa solta `Ratified: quando o conselho decidir` não é rodapé — sem bold, não é metadado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: o leitor MUST reconhecer as três formas reais — bullet `- chave: valor`, top-level
  `chave: valor` e rodapé `**Chave**: valor` separado por `|`.
- **FR-002**: o leitor MUST aceitar `## Governance` / `## Governança` com corpo não vazio como
  governança declarada, quando não existir o campo.
- **FR-003**: comentários HTML MUST ser descartados antes da extração de metadado.
- **FR-004**: campos declarados MUST prevalecer sobre o rodapé; o rodapé só preenche chave ausente.
- **FR-005**: o rodapé MUST exigir a marcação bold; `Chave: valor` sem bold já é coberto por
  `TOP_FIELD` e aceitá-lo solto abriria falso positivo em prosa.
- **FR-006**: ausência real de metadado MUST continuar produzindo os findings existentes, com as
  mesmas strings.
- **FR-007**: `FIELD` e `TOP_FIELD` MUST permanecer inalterados — parseiam ROADMAP, DECISION-BACKLOG,
  handoffs, PLAN-CONTEXT, DECISION-FRONTIER e descrições de work item.
- **FR-008**: nenhuma constituição, deste repo ou de consumidor, pode ser reescrita pela correção.

### Key Entities

- **Metadados da constituição**: `version`, `ratified`, `last-amended`, `governance`, normalizados
  em minúsculas com espaço convertido em hífen (`Last Amended` → `last-amended`).
- **Rodapé Spec Kit**: linha que contém ao menos um par `**Version|Ratified|Last Amended**: valor`.
- **Seção de governança**: primeiro H2/H3 cujo texto normalizado é `governance`, `governança` ou
  `governanca`; corpo até o próximo heading de nível igual ou superior, excluída a linha do rodapé.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: o cenário do relato reproduz `NO-GO` com quatro findings antes e nenhum finding de
  `constitution:` depois.
- **SC-002**: a suíte sobe de 1088 para 1102 testes, exit 0, sem regressão nos 22 validadores
  anteriores.
- **SC-003**: as duas formas antes sem cobertura (bullet shipado e rodapé Spec Kit) passam a ser
  exercitadas pelo CLI real, não só pela função pura.
- **SC-004**: `audit` deste repo continua `MILESTONE-COMPLETE`.

## Assumptions

- O rodapé usa as chaves em inglês (`Version`, `Ratified`, `Last Amended`) mesmo em constituição
  escrita em português — é o que o template oficial gera.
- O leitor continua morando em `audit_decisions.py`, não em `grill_core/`: o módulo é script
  standalone carregado por `backlog_bridge.py:184` via `sibling()`, e uma dependência de pacote
  quebraria esse caminho.
