# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| Repositório canônico | `cadugevaerd/grill-with-docs`, onde o plugin é desenvolvido e versionado. Fonte da verdade do conteúdo. | "repo de release", "origem" | README.md; `.claude-plugin/marketplace.json` com `source: ./plugin` |
| Marketplace | Repositório monorepo que agrega vários plugins e é o que o usuário final adiciona no agente. Hoje `cadugevaerd/claude-skills` (Claude) e `cadugevaerd/codex-skills` (Codex). | "repositório de release", "repositório de plugin" | `~/.claude/plugins/marketplaces/claude-skills/.claude-plugin/marketplace.json`, 16 plugins |
| Cópia vendorizada | Conteúdo do plugin materializado dentro do marketplace em `plugins/grill-with-docs/`, e não referenciado por link. É o que o agente instala. | "submódulo", "link" | `plugins/grill-with-docs/.claude-plugin/plugin.json` versão 2.4.0 |
| Manifesto do plugin | `plugin.json` que declara nome, versão, descrição e autor do plugin. Existe no canônico e na cópia vendorizada. | "manifest" genérico | `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json` |
| Entrada de marketplace | Registro do plugin dentro do `marketplace.json` do agregador, com `name`, `source`, `version` e `description` próprios. Duplica a versão declarada no manifesto. | "índice" | entrada `grill-with-docs` em `claude-skills/.claude-plugin/marketplace.json` |
| Publicação | Ato de tornar uma versão do plugin disponível para instalação, atualizando cópia vendorizada e entrada de marketplace nos dois agregadores. | "deploy", "release" solto | drift atual: canônico 2.5.0, marketplace 2.4.0 |
| Drift de publicação | Divergência entre a versão do repositório canônico e a versão disponível nos marketplaces. | "atraso" | canônico 2.5.0 vs `claude-skills` 2.4.0 |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.
