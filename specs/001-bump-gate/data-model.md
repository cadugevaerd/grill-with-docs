# Data Model — Gate de bump de versão

Não há persistência. As entidades abaixo existem apenas durante uma execução.

## Version

Versão declarada, comparável por ordem.

- **componentes**: `major`, `minor`, `patch` — inteiros não negativos
- **origem**: campo `version` de `plugin/.claude-plugin/plugin.json`
- **regra de validação**: precisa casar exatamente `^\d+\.\d+\.\d+$`. Ausente, malformada ou não decodificável é erro, não zero.
- **ordem**: comparação lexicográfica sobre a tupla de inteiros

## ChangeSet

O que a pull request altera, do ponto de vista do bundle distribuído.

- **campos**: `paths` — lista de caminhos alterados entre base de merge e HEAD
- **derivado**: `touches_plugin` — verdadeiro quando algum caminho começa com `plugin/`
- **regra**: adição, modificação e remoção contam igualmente

## Verdict

Resultado da verificação.

- **valores**: `PASS`, `FAIL`
- **campos**: `code`, `base_version`, `head_version`, `message`
- **códigos**: `NO-PLUGIN-CHANGE`, `BUMPED`, `MISSING-BUMP`, `VERSION-REGRESSION`, `VERSION-UNREADABLE`
- **transições**: `NO-PLUGIN-CHANGE` e `BUMPED` produzem `PASS`; os três demais produzem `FAIL`
