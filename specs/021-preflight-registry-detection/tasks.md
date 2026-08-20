# Tasks: Detecção de extensão pelo registro

Ordem é dependência real, não preferência. T001 primeiro porque um teste que falha antes da correção é a única prova de que ele testa o defeito e não o código.

- [ ] T001 Escrever `tests/validate_extension_detection.py` cobrindo A1-A4, B1-B4, C1-C8, D1 — vermelho contra o código atual
- [ ] T002 Acrescentar `spec-kit-extension-registry` ao manifest e o campo `enable` às entradas `ext:*`
- [ ] T003 Trocar a fonte: `extension_registry()` lendo `.registry`, com as três formas de ilegibilidade convergindo em `None`
- [ ] T004 Avaliar `enabled` e preencher `version`/`source` a partir do registro
- [ ] T005 Status `undetermined` e supressão de remediação quando a presença não foi observada
- [ ] T006 Remediação por motivo observado (`enable` vs `add`) e `install()` pulando `undetermined`
- [ ] T007 `schema_check` no ramo `kind: path`, para o registro não ficar `present` com schema não reconhecido
- [ ] T008 Remover `installed_extensions` na forma antiga (F1) — sem parser em paralelo
- [ ] T009 Atualizar validadores que enumeram status exaustivamente (E3)
- [ ] T010 Bump 3.3.0 → 3.3.1 nos oito lugares e entrada `## 3.3.1` no CHANGELOG
- [ ] T011 Suíte completa verde, contagem >= 1066, exit 0
- [ ] T012 Verificação manual D2: `preflight .` no repositório real retorna `OK` e exit 0

## Dependências

- T003 depende de T002 (o manifest declara o que o código lê)
- T004, T005 dependem de T003
- T006 depende de T002 (campo `enable`) e T005 (motivo observado)
- T008 depende de T003 a T007 estarem verdes — remover antes deixaria a suíte sem fonte
- T011 depende de T009
- T012 depende de T011 e não é reproduzível no CI (o ambiente da matriz não tem `specify`)

## Resultado

<!-- preenchido na etapa converge -->
