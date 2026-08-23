# PLAN-CONTEXT

## FASE-001 — Alinhar o gate do Gauntlet e a CLI à frontier ativa
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0007, ADR-0008
- BLs: BL-0001
- delivery-units: DU-001
- development-type: platform-devops

### HOW

**Causa raiz.** `grill_workspace.py` não importa `workflow_v4` e injeta `workflow_v3` nos
quatro pontos de entrada do Gauntlet (2388, 2458, 2532, 2542). `workflow_v3.execution_gate`
recusa marcador diferente de `v3` (`workflow_v3.py:441-444`), então um `WORKFLOW.md` v4 —
o que a frontier ativa materializa — reprova com `WORKFLOW-INCOMPATIBLE`. Causa estrutural
por trás disso: a CLI duplica as tabelas de versão do SSOT em vez de lê-lo, e por isso
declara `ACTIVE_WORKFLOW_VERSION = "v4"` (2166) no mesmo arquivo em que injeta o gate v3.

**Superfície de mudança, em ordem de dependência.**

1. `grill_core/workflow_versions.py` — introduzir `KNOWN_VERSIONS = ("v3", "v4")` e
   encolher `EXECUTABLE_VERSIONS` para `("v4",)`; remover o comentário que promete
   execução v3. Acrescentar `DEVELOPMENT_SCHEMAS` (schema → versão) como literal congelado
   próprio, **não** derivado de `DEVELOPMENT_SCHEMA_BY_VERSION`: o `None` do
   `grill-development/v2` significa "leia o `workflow_version` declarado", e uma inversão
   calculada perderia isso. (ADR-0003, ADR-0004, ADR-0005)
2. `grill_core/gauntlet.py` — renomear o parâmetro `workflow_v3` para `workflow_gate` nas
   três assinaturas (459, 541, 631) e nas duas chamadas internas (547, 646). (ADR-0001,
   DQ-0002/R-0006)
3. `grill_workspace.py` — carregar `workflow_versions` por `grill_core_module`, apagar as
   quatro cópias literais (2155-2166), e passar `workflow_gate=workflow_v4` nos quatro
   pontos. Acrescentar nota em LD-010 item 4 registrando por que este módulo é exceção à
   regra do literal local. (ADR-0001, ADR-0005)
4. `grill_workspace.py:691` + `audit_decisions.py:801` — `workflow.version` vira
   `workflow.schema`, valor `"v2"` inalterado; o reader aceita `schema` com fallback para
   `version`. Sem migração de bundle. (ADR-0006)

**Restrições que o plano não pode violar.**

- As cinco tabelas por versão (`SEQUENCE_BY_VERSION`, `TIER_POLICY_BY_VERSION`,
  `EXECUTOR_STEP_BY_VERSION`, `REGISTRY_FILENAME_BY_VERSION`,
  `DEVELOPMENT_SCHEMA_BY_VERSION`) **mantêm a chave `"v3"`** e passam a ser amarradas a
  `KNOWN_VERSIONS` em `validate_workflow_versions_contract.py:174-183`. Perder essa chave
  levanta `KeyError` em `gauntlet.py:415,501,505,513,615-617`, que indexam pela versão do
  activation record imutável, e desfaz o dual-read entregue em `a188157` (4.0.1).
- Nenhuma tabela pode ser derivada de outra — regra do CLAUDE.md, e a razão pela qual
  `DEVELOPMENT_SCHEMAS` entra como literal.
- `workflow_v4` não expõe `CLI_CODE_ALIASES`, mas `gauntlet.py:465,468` já leem a tabela
  por `getattr(..., {})` e caem em `_public_code`. Verificado: os 13 aliases do v3 são
  todos a transformação mecânica `_`→`-`, idêntica a `_public_code`. Nenhum código de erro
  muda de string.

**Cobertura exigida.** Um teste que lê `workflow_versions.ACTIVE_VERSION`, materializa o
`WORKFLOW.md` daquela versão via `TEMPLATE_FILENAME_BY_VERSION` (`workflow_versions.py:143`)
e exige `gauntlet-init` bem-sucedido — sem literal de versão na asserção. Hoje a suíte não
tem nenhuma ocorrência de `workflow_v4` e as cinco suítes que exercitam `gauntlet-init`
geram a própria fixture com `workflow_v3.py migrate`, então writer e reader concordam por
construção. Mais: um caso para a invariante `EXECUTABLE_VERSIONS ⊆ KNOWN_VERSIONS` e um
caso que prova o fallback de leitura de `workflow.version`. (ADR-0002, ADR-0004, ADR-0006)

### Obrigações carregadas ao ciclo executor

- **Bump obrigatório**: o plano altera `plugin/**`, então a versão precisa subir nos oito
  lugares que `tests/validate_distribution.py` fixa, antes de merge.
- **Assunção declarada sobre a leitura SemVer**: `EXECUTABLE_VERSIONS = ("v4",)` remove uma
  capacidade que consumidor v3 tinha, o que lê como **major** — 4.0.1 → 5.0.0. Fica como
  assunção a confirmar no ciclo executor, não como decisão selada aqui.
- **Suíte verde**: baseline atual 1233 testes em 26 validadores; `verify` só passa com
  `python3 tests/run_validators.py` em exit 0.
- **`backlog_skipped`**: este bundle nasceu sem backlog vinculado, porque o bind do SGD é
  por caminho e não segue worktree. Rodar `backlog-adopt ROOT --work-id <id> --apply` após
  o merge para limpar o carimbo.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
