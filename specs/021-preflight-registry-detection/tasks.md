# Tasks: Detecção de extensão pelo registro

Ordem é dependência real, não preferência. T001 primeiro porque um teste que falha antes da correção é a única prova de que ele testa o defeito e não o código.

- [x] T001 Escrever `tests/validate_extension_detection.py` cobrindo A1-A4, B1-B4, C1-C8, D1 — vermelho contra o código atual
- [x] T002 Acrescentar `spec-kit-extension-registry` ao manifest e o campo `enable` às entradas `ext:*`
- [x] T003 Trocar a fonte: `extension_registry()` lendo `.registry`, com as três formas de ilegibilidade convergindo em `None`
- [x] T004 Avaliar `enabled` e preencher `version`/`source` a partir do registro
- [x] T005 Status `undetermined` e supressão de remediação quando a presença não foi observada
- [x] T006 Remediação por motivo observado (`enable` vs `add`) e `install()` pulando `undetermined`
- [x] T007 `schema_check` no ramo `kind: path`, para o registro não ficar `present` com schema não reconhecido
- [x] T008 Remover `installed_extensions` na forma antiga (F1) — sem parser em paralelo
- [x] T009 Reescrever os três testes que codificavam o comportamento antigo, com caso adversarial (E3)
- [x] T010 Bump 3.3.0 → 3.3.1 nos oito lugares e entrada `## 3.3.1` no CHANGELOG
- [x] T011 Suíte completa verde, contagem >= 1066, exit 0
- [x] T012 Verificação manual D2: `preflight .` no repositório real retorna `OK` e exit 0

## Dependências

- T003 depende de T002 (o manifest declara o que o código lê)
- T004, T005 dependem de T003
- T006 depende de T002 (campo `enable`) e T005 (motivo observado)
- T008 depende de T003 a T007 estarem verdes — remover antes deixaria a suíte sem fonte
- T011 depende de T009
- T012 depende de T011 e não é reproduzível no CI (o ambiente da matriz não tem `specify`)

## Resultado

Suíte final: **1087 testes, 21 validadores, exit 0** — 1066 de baseline mais os 21 do contrato novo. Nenhum teste preexistente quebrou além dos três previstos pelo `analyze`, e nenhum outro.

T012, a verificação que originou SGD-16, no repositório real:

```
preflight verdict: OK
dependencies verdict: OK
missing_required: []
  spec-kit-extension-registry      present
  ext:git                          present   version=1.0.0
  ext:agent-assign                 present   version=1.0.0
  ext:bugfix                       present   version=1.0.0
  ext:verify-review-ship           present   version=0.4.2
```

Antes: `MISSING-DEPENDENCY` com `ext:git`, `ext:agent-assign` e `ext:verify-review-ship` falsamente ausentes, `ext:bugfix` falsamente presente, e `version` nula nas quatro.

### O que a fase encontrou e o plano não previa

O `analyze` acertou os três testes que quebrariam, mas o achado que importa é **por que** eles existiam na forma antiga. `test_installed_extension_is_detected` alimentava `git (v1.0.0)\nverify-review-ship (v0.4.2)\n` — texto limpo, slug no início da linha. O terminal nunca emite isso. A fixture tinha sido escrita a partir da leitura do código, não da saída real, então herdou a suposição que deveria desafiar.

Esse é o motivo de um defeito de detecção sobreviver a 1066 testes. Não foi falta de cobertura: a linha estava coberta. Foi cobertura contra um mundo inventado. As regressões agora carregam os escapes reais e uma descrição-isca, e `test_slug_inside_a_description_is_not_a_match` reprova qualquer patch que só remova ANSI.

### Escopo que cresceu durante a execução

`_UNREAD` como sentinela foi necessidade descoberta na implementação, não no plano: `None` virou estado significativo do registro, então não podia continuar servindo de "ainda não lido" — senão um registro ilegível seria relido uma vez por extensão. Custo: um objeto sentinela e um comentário. Sem isso o comportamento seria correto e o desempenho silenciosamente pior.
