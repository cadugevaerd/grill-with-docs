# Checklist: requisitos do fix de metadados da constituição

- [x] CHK-001 Cada FR do spec tem teste que falha sem o fix — FR-001 (três formas), FR-002
      (governança por heading), FR-003 (comentário), FR-004 (precedência), FR-005 (bold obrigatório),
      FR-006 (fail-closed).
- [x] CHK-002 FR-007 verificado por ausência de diff: `FIELD` e `TOP_FIELD` inalterados no patch.
- [x] CHK-003 FR-008 verificado por ausência de diff: nenhuma constituição foi escrita.
- [x] CHK-004 Fixtures derivadas dos artefatos shipados, não do parser.
- [x] CHK-005 Strings dos findings preservadas byte a byte.
- [x] CHK-006 Nenhum teste toca rede, `specify`, `node` ou `backlogctl`.
- [x] CHK-007 Somente biblioteca padrão; nada além de `re`, `json`, `hashlib`, `shutil`, `subprocess`,
      `tempfile`, `unittest`, `pathlib` no validador novo.
- [x] CHK-008 `audit` continua read-only.
- [x] CHK-009 Bump aplicado nos oito lugares e validado.
- [x] CHK-010 Baseline do `CLAUDE.md` atualizado com o número real medido, não estimado.
