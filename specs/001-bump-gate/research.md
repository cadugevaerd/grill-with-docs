# Research — Gate de bump de versão

Nenhum `NEEDS CLARIFICATION` sobreviveu ao spec. As decisões abaixo são as que o plano precisava fechar, todas verificadas no próprio repositório.

## Onde a versão canônica é lida

- **Decisão**: `plugin/.claude-plugin/plugin.json`, campo `version`.
- **Rationale**: é o manifesto do bundle distribuído. `tests/validate_distribution.py` já exige que ele concorde com `plugin/.codex-plugin/plugin.json`, com os dois `marketplace.json`, com a constante `VERSION` do validador e com os headings de `SKILL.md`, `references/session-protocol.md` e `README.md`. Ler um único ponto é suficiente porque a coerência dos demais já é garantida — e FR-006 proíbe reimplementar essa checagem.
- **Alternativas**: ler os cinco pontos e exigir acordo — rejeitada por duplicar validação existente; ler a constante do validador — rejeitada porque é artefato de teste, não manifesto.

## Como decidir se o conteúdo distribuído mudou

- **Decisão**: `git diff --name-only <base>...<head>` filtrado pelo prefixo `plugin/`.
- **Rationale**: `plugin/` é exatamente o que a publicação espelha, conforme ADR-0003. `..` de três pontos usa a base de merge, que é o que o spec exige nas Assumptions.
- **Alternativas**: usar a lista de paths de `on.push.paths` do CI — rejeitada porque inclui `tests/**` e os `marketplace.json`, que não compõem o bundle; comparar árvores por hash — rejeitada por não distinguir remoção de arquivo com clareza no relatório.

## Qual comparação de versão

- **Decisão**: comparar como tupla de inteiros de três componentes, exigindo `head > base` estritamente.
- **Rationale**: o repositório usa SemVer simples sem pré-lançamento; `tests/validate_distribution.py` fixa a versão como literal `X.Y.Z`. Tupla de inteiros ordena corretamente `2.10.0 > 2.9.0`, que comparação textual erraria.
- **Alternativas**: comparação de string — rejeitada por ordenar `2.10.0 < 2.9.0`; `packaging.version` — rejeitada por ser dependência externa, proibida no repositório.

## Onde o gate roda

- **Decisão**: job dedicado no workflow existente, disparado apenas em `pull_request`, com `fetch-depth: 0`.
- **Rationale**: a base de merge só existe com histórico completo; `actions/checkout` faz clone raso por padrão e não teria o commit base. Em `push` direto na main não há base confiável, conforme registrado em `PLAN-CONTEXT.md#FASE-001`.
- **Alternativas**: rodar dentro da matriz de validadores — rejeitada porque a matriz roda em três sistemas e duas versões de Python, e o gate é uma decisão única que não depende de plataforma; rodar em `push` — rejeitada por falta de base de comparação.

## Por que o script fica fora do glob `validate_*.py`

- **Decisão**: nomear `tests/check_version_bump.py` e cobrir a lógica pura em `tests/validate_bump_gate_contract.py`.
- **Rationale**: `tests/run_validators.py:10` faz glob de `validate_*.py`. Um validador que exigisse contexto de pull request falharia ou precisaria de no-op silencioso em toda execução local e na matriz — exatamente o tipo de degradação silenciosa que a cláusula "Fail-closed sem waiver" desaconselha.
- **Alternativas**: um único `validate_bump_gate.py` com no-op fora de PR — rejeitada por esconder ausência de verificação atrás de sucesso.
