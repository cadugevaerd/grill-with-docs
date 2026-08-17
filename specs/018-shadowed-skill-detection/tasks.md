# Tasks: Detecção de skill sombreada

- [x] T001 Definir os nomes publicados e as raízes de busca em `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py`
- [x] T002 Implementar a detecção, com `is_symlink()` antes de `exists()` para não perder atalho quebrado
- [x] T003 Implementar a remoção que tira apenas o atalho e preserva o destino
- [x] T004 Ligar ao `preflight`, reportando por padrão e removendo sob `--allow-install`
- [x] T005 Onze casos em `tests/validate_dependencies_contract.py`, com diretórios sintéticos e `HOME` injetado
- [x] T006 Atualizar `SKILL.md` e `CHANGELOG.md`
- [x] T007 Bump `3.0.0` para `3.1.0` nos oito lugares
- [x] T008 Suíte completa verde

## Resultado

Suíte 1007 para 1018, exit 0. `validate_dependencies_contract.py` de 21 para 32.

A detecção foi conferida contra a forma real do defeito desta sessão — atalho em `~/.claude/skills` apontando para `~/.agents/skills` — e reporta o atalho e o destino como sombras distintas, porque ambos ocupam o nome em raízes pesquisadas.

Os testes de atalho pulam quando a plataforma não suporta symlink, em vez de falhar; é o mesmo tratamento que o validador de workspace já dá ao caso.
