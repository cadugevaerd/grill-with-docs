# PLAN-CONTEXT

## FASE-001 — Gate de bump no CI
- phase: FASE-001
- ADRs: ADR-0002
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
O critério de "tocou `plugin/`" já existe em `.github/workflows/ci.yml`, em `on.pull_request.paths` e `on.push.paths`: `plugin/**`, `tests/**` e os dois `marketplace.json`. Para o gate, o subconjunto relevante é apenas `plugin/**` — mudança só em `tests/**` não altera o bundle publicado e não deve exigir bump.

A versão vive em cinco lugares e `tests/validate_distribution.py` já exige que todos concordem entre si e com os headings de `SKILL.md`, `references/session-protocol.md` e `README.md`. O gate não precisa reverificar coerência interna; precisa apenas comparar a versão do `plugin/.claude-plugin/plugin.json` no merge base contra a do HEAD e exigir que tenha aumentado quando houver diff em `plugin/**`.

Restrição: o gate roda em `pull_request`, onde o merge base está disponível. Em `push` direto na main não há base confiável, então o gate é de PR, não de push.

Risco: duas PRs concorrentes que bumpem para a mesma versão conflitam em `plugin.json` e nos dois `marketplace.json`. O conflito é textual e visível; não há mitigação automática nesta fase.

## FASE-002 — Publicação fan-out nos dois marketplaces
- phase: FASE-002
- ADRs: ADR-0001, ADR-0004, ADR-0005, ADR-0006
- BLs: BL-0001
- delivery-units: DU-002
- development-type: platform-devops

### HOW
Layout de destino confirmado por inspeção: `claude-skills` tem `.claude-plugin/marketplace.json` na raiz e a cópia em `plugins/grill-with-docs/`; `codex-skills` tem `.agents/plugins/` e `plugins/`, espelhando a mesma convenção do canônico, que mantém `.claude-plugin/marketplace.json` e `.agents/plugins/marketplace.json`.

A cópia é substituição total do diretório de destino pelo conteúdo de `plugin/` mais o `README.md` da raiz, e não merge incremental — caso contrário arquivos removidos no canônico sobrevivem no destino. A cópia atual em `claude-skills` contém `tests/`, que desaparece na primeira publicação por consequência direta de ADR-0003.

Na entrada de marketplace, sincronizar apenas `version`. O campo `description` da entrada em `claude-skills` é editorial e diverge do `plugin.json` de propósito — "reconciliação incremental **por work item** com receipts fail-closed" contra a descrição mais curta do manifesto. Sobrescrevê-lo destruiria texto curado. Esta é uma decisão de baixo impacto tomada por derivação, não por entrevista.

Autenticação por PAT classic em secret, conforme ADR-0004. O `GITHUB_TOKEN` do Actions não serve: é escopado ao repositório do workflow. Um job por marketplace, em matrix, conforme ADR-0005; a idempotência do espelho garante convergência no re-run.

Restrição de portabilidade: o canônico é público e sem forks, então secrets não são expostos a PRs de fork por padrão. Qualquer workflow que chegue à main executa com o PAT.

## FASE-003 — Reconciliação do drift existente
- phase: FASE-003
- ADRs: ADR-0007
- BLs: none
- delivery-units: DU-003
- development-type: platform-devops

### HOW
O workflow de publicação declara `workflow_dispatch` além do gatilho de merge. O merge que traz o próprio workflow não toca `plugin/` e, por ADR-0002, não publica — daí a necessidade de uma execução manual única para levar a versão corrente aos dois marketplaces.

O `workflow_dispatch` permanece depois da reconciliação como escape hatch: permite republicar sem inventar um commit, útil quando um job falha e o re-run já expirou.

Verificação: por ADR-0007, cada destino é relido de um clone novo tirado do remoto, e a entrada precisa declarar a versão corrente e os cinco campos do pin `git-subdir`, com a referência resolvendo no canônico para o commit publicado.

O texto anterior deste parágrafo pedia a mesma versão no `plugin.json` vendorizado e o desaparecimento de `plugins/grill-with-docs/tests/` do `claude-skills`. Os dois critérios pressupõem o espelho de conteúdo abandonado em ADR-0006: não existe cópia publicada, logo não há manifesto vendorizado nem diretório de testes a remover.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
