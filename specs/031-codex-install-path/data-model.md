# Data Model: Observar a instalação Codex do i-have-adhd

## Entrada nativa Codex (lida)

| Campo | Tipo | Uso |
|---|---|---|
| `pluginId` | string | seleção: igual a `i-have-adhd@i-have-adhd`; exatamente uma entrada |
| `installed` | bool | precisa ser `true` |
| `marketplaceName` | string | segmento 1 do caminho |
| `name` | string | segmento 2 do caminho |
| `version` | string | segmento 3 do caminho e versão observada |
| `installPath` | string (ausente no 0.154.0) | se presente e absoluto, tem precedência (comportamento atual) |

## Evidência `installation` (produzida)

Sem mudança de schema: `{"status": "present", "version", "install_root", "skill_ref"}`, com `install_root = <home Codex>/plugins/cache/<marketplaceName>/<name>/<version>` e `skill_ref = install_root/skills/i-have-adhd/SKILL.md`. Qualquer condição falha → `{}` (vira `undetermined` em `agent_runtime.py:204`).

## Transições

`{}` → `present` somente com todas as condições de `research.md` R4; conteúdo é julgado depois, por `approved_presentation_reference`.
