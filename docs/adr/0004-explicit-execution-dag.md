# Explicit Execution DAG

A Canonical Skill `tasks` produzirá um Execution DAG versionado e legível por máquina, com nós, dependências, escopo, artefatos esperados e Model Tier mínimo. O Gauntlet Loop só despacha em paralelo nós declarados sem dependências pendentes; dependências não são inferidas de texto livre. A primeira versão automatiza exclusivamente as onze macroetapas canônicas V3 e não permite reordená-las ou substituí-las pela configuração.
