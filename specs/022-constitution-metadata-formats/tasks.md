# Tasks: Metadados da constituição em suas três formas reais

- [x] **T001** Reproduzir o defeito: copiar `tests/fixtures/go-project`, trocar só a constituição pela
      forma oficial do Spec Kit, confirmar `GO` antes e `NO-GO` com quatro findings depois.
- [x] **T002** Vendorizar a fixture real: gerar `tests/fixtures/constitutions/spec-kit-filled.md` a
      partir de `.specify/templates/constitution-template.md`, preenchendo placeholders e preservando
      os comentários HTML.
- [x] **T003** Adicionar `HTML_COMMENT`, `HEADING`, `FOOTER_LINE`, `FOOTER_PAIR` e `GOVERNANCE_NAMES`
      em `audit_decisions.py`, sem tocar em `FIELD`/`TOP_FIELD`.
- [x] **T004** Implementar `footer_fields`, `section_body` e `constitution_metadata`.
- [x] **T005** Trocar `values = {**fields(text), **top_fields(text)}` por
      `values = constitution_metadata(text)` no bloco de validação.
- [x] **T006** Escrever `tests/validate_constitution_metadata.py` com as três formas, os casos de
      fail-closed e os casos de borda, exercitando o CLI real por subprocess.
- [x] **T007** Confirmar que o defeito reproduzido em T001 desaparece e que `tests/fixtures/go-project`
      continua `GO`.
- [x] **T008** Rodar a suíte completa: `python3 tests/run_validators.py`.
- [x] **T009** Bump 3.3.1 → 3.3.2 nos oito lugares e validar com `tests/validate_distribution.py`.
- [x] **T010** Atualizar a linha de baseline do `CLAUDE.md` (1088/22 → 1102/23).
- [x] **T011** Verify: gates executáveis, prova de que o teste testa o defeito, higiene de diff.
- [x] **T012** Review: risco técnico, escopo, regressão.

## Dependências

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012.
T002 é pré-requisito de T006: a fixture precisa existir antes do teste que a lê.

## Resultado

Suíte de 1088 para 1102 testes, 22 para 23 validadores, exit 0 com 1 skip de ambiente.
Os quatro findings falsos deixam de ocorrer; a falta real de metadado continua reprovando.

### O que a fase encontrou e o plano não previa

O laudo precisa de uma seção `## Status` explícita — `triage` recusa com `TRIAGE-REPORT-INVALID` um
relatório que declare o status como linha solta. Formato corrigido, triagem selada em
`tri-9981372e1dbc4d7ebfcf532f09d9573a`.

### Escopo que cresceu durante a execução

Nenhum. A correção ficou nos limites do laudo: um leitor novo, um call site trocado, um validador
novo, uma fixture nova, bump e baseline.
