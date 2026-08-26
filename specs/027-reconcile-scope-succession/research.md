# Phase 0 — Research: sucessão explícita de escopo reconciliado

Nenhum `NEEDS CLARIFICATION` restou do spec: ADR-0001 já fixa a decisão de
projeto. O que sobra é a pesquisa de código — onde o defeito está, o que é
seguro mudar e o que precisa continuar exatamente igual.

## R-001 — Onde a classificação acontece hoje

**Decision**: Existem dois laços de sobreposição, um por caminho de
reconciliação, e nenhum dos dois consulta `depends-on-work`.

- Caminho **full** (`validate_reconciliation`, `grill_workspace.py:1774-1780`):
  compara todo par ordenado de bundles e todo par de caminhos. As dependências
  já foram coletadas em `dependencies` (linhas 1744-1749) e usadas apenas para
  `DEPENDENCY-MISSING` e `DEPENDENCY-CYCLE` — o dado está à mão, e mesmo assim
  o laço de escopo não o consulta.
- Caminho **targeted** (`reconcile_command`, `grill_workspace.py:1997-2016`):
  compara o escopo do alvo com o escopo preservado em cada recibo histórico. Aqui
  o dado **não** está à mão: `dependencies` só é lido na linha 2008, depois do
  laço. Essa ordem é literalmente o defeito que SGD-24 reproduziu.

**Rationale**: A leitura confirma o diagnóstico do handoff e mostra que a
correção é assimétrica: no full basta consultar um mapa já construído; no
targeted é preciso mover a leitura das dependências para antes do laço.

**Alternatives considered**: procurar a causa no cálculo de sobreposição
(`scopes_overlap`, linha 1630). Descartado: a função é uma comparação de prefixo
de caminho, correta e sem noção de trabalho; o defeito é de ordem e de dado
ausente, não de comparação.

## R-002 — Qual relação autoriza

**Decision**: Somente dependência direta declarada, conforme ADR-0001. No
targeted, `target["depends-on-work"]` precisa conter exatamente o `prior_id` dono
do recibo sobreposto. No full, o par é autorizado quando um dos dois declara
diretamente o outro; a direção da declaração identifica o sucessor.

**Rationale**: É a autorização mínima rastreável. Não exige fechamento
transitivo, não inventa relação que o autor não escreveu, e cada dispensa tem um
campo declarado apontando para ela.

**Alternatives considered**:

- *Dependência transitiva.* Rejeitada em ADR-0001: exigiria fechamento do grafo e
  ampliaria a autorização para relações não declaradas. Também não resolve o caso
  concreto que motivou o trabalho, cuja cadeia não alcança o recibo em questão.
- *Qualquer recibo concluído.* Rejeitada em ADR-0001: remove o ownership
  perpétuo mas transforma o recibo em waiver global, deixando trabalhos não
  relacionados colidirem em silêncio.

## R-003 — Interação com as outras recusas

**Decision**: A autorização atua **exclusivamente** sobre a anotação
`SCOPE-OVERLAP`. Nenhuma outra recusa consulta o resultado dela.

- `DEPENDENCY-SCHEMA`: quando a declaração não é uma lista de strings, o mapa de
  dependências daquele trabalho é tratado como vazio. Declaração malformada não
  autoriza nada — fail-closed.
- `DEPENDENCY-MISSING` / `DEPENDENCY-NOT-RECONCILED`: inalteradas. Uma dependência
  que não existe no conjunto avaliado não pode autorizar sobreposição contra um
  recibo que também não está lá.
- `DEPENDENCY-SELF`: inalterada. No targeted o próprio `work_id` já é pulado no
  laço; no full os pares são distintos por construção. Autorreferência nunca
  chega a produzir autorização.
- `DEPENDENCY-CYCLE`: inalterada. Um par que se declara mutuamente tem o escopo
  autorizado **e** continua reprovado pelo ciclo — o resultado agregado segue
  fail-closed.
- `ADR-CONFLICT` / `ADR-CONFLICT-SCHEMA`: inalteradas, em laço próprio, sem
  consulta à autorização.

**Rationale**: Manter as recusas ortogonais é o que permite afirmar, com teste,
que a correção destrava um caso e não afrouxa nenhum outro.

**Alternatives considered**: tratar a autorização como uma dispensa geral do par
(pulando também ADR e ciclo). Rejeitada: seria exatamente o waiver que ADR-0001
recusa, e transformaria uma correção em um buraco de governança.

## R-004 — Compatibilidade de recibos

**Decision**: Nenhuma mudança de formato. A autorização é decidida com dados que
já existem: o `work_id` de cada recibo (chave do arquivo) e o `depends-on-work`
do bundle-alvo, que já é lido hoje.

**Rationale**: O recibo histórico não precisa saber quem virá depois. Quem
declara a relação é sempre o sucessor, e o sucessor é sempre o bundle que está
sendo avaliado agora. Por isso a correção não exige campo novo no recibo e não
força migração de nada gravado.

**Alternatives considered**: gravar no recibo uma lista de sucessores
autorizados. Rejeitada: mudaria o schema, obrigaria reescrever recibos
históricos e colocaria a autorização sob controle do trabalho anterior, que é
justamente quem não pode decidir sobre trabalho futuro.

## R-005 — Onde os testes moram

**Decision**: `tests/validate_workspace_contract.py`. Nenhum arquivo de teste
novo.

**Rationale**: O validador já é o dono do contrato de `reconcile` — tem os
helpers `_set_scope`, `_set_dependencies`, `_set_adr_conflicts`, `_mark_complete`
e `invoke`, e já cobre `SCOPE-OVERLAP`, `DEPENDENCY-CYCLE`,
`DEPENDENCY-MISSING`, `DEPENDENCY-NOT-RECONCILED` e `ADR-CONFLICT`. Além disso
ele é o único arquivo de teste dentro do escopo declarado, junto de
`validate_distribution.py`. Criar `validate_reconcile_succession_contract.py`
seria escopo não declarado e partiria o contrato em dois donos.

**Alternatives considered**: arquivo de contrato dedicado. Rejeitada pelos dois
motivos acima. `tests/run_validators.py` faz glob, então um arquivo novo entraria
sozinho na suíte — o obstáculo não é mecânico, é de ownership e de escopo.

## R-006 — Superfície do bump

**Decision**: 5.2.0 → 5.2.1 (patch: correção de comportamento sobre base
publicada, sem mudança de formato nem remoção de capacidade), em oito pontos.

Os oito, todos fixados por `tests/validate_distribution.py`:
`plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, a
constante `VERSION` do próprio validador, o heading de
`plugin/skills/grill-with-docs/SKILL.md`, o heading de
`plugin/skills/grill-with-docs/references/session-protocol.md` e o heading de
`README.md`.

**Rationale**: A base foi sincronizada com `origin/main` em v5.2.0; o incremento
tem que partir da base atual. O `WORK-ITEM.json` foi selado quando a base era
5.0.x, então preservar aquele número produziria uma versão já publicada — o que a
cláusula *Bump obrigatório do plugin* proíbe explicitamente.

**Alternatives considered**: bump minor. Rejeitada: nenhuma capacidade nova,
nenhum campo novo, nenhum código novo na superfície pública — apenas uma recusa
que deixa de ser emitida em um caso declarado.
