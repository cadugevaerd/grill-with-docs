# Tasks: Migração de bundles legados

- [x] T001 Detectar o modo do bundle pela ausência da marca de origem
- [x] T002 Implementar `migrate`, prévia por padrão, semeando estado histórico por snapshot inicial
- [x] T003 Recusar o bundle inteiro em estado inválido, sem migração parcial
- [x] T004 Regenerar o registro como projeção marcada ao aplicar
- [x] T005 Recusar `backlog-project` sobre bundle autoral, com `BACKLOG-MIGRATION-REQUIRED`
- [x] T006 Ligar o subcomando `backlog-migrate`
- [x] T007 Nove casos em `tests/validate_backlog_contract.py`
- [x] T008 Atualizar `SKILL.md` e `CHANGELOG.md`; bump 3.1.0 para 3.2.0
- [x] T009 Suíte completa verde

## Resultado

Suíte 1018 para 1027, exit 0.

Prévia conferida contra os quatro bundles reais do repositório: sete contrapartes a criar e uma já existente, que aparece corretamente como `REUSED`. Isso confirma, de ponta a ponta, o diagnóstico que abriu o work item — dos oito registros de decisão, apenas um tinha chegado ao backlog.
