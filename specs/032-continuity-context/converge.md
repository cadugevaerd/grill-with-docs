# Converge Report — 032 continuidade de contexto sem líder vivo

**Data**: 2026-09-19 · **Entradas**: spec.md, plan.md, tasks.md (T001–T013), `.specify/memory/constitution.md` (11 cláusulas) · **Desfecho**: `tasks_appended` (Phase 6, T014–T015)

## Contexto

`implement-parallel` fechou com T001–T013 pela run `run-27d4a4df4c0ec78046f8c430` (4 waves, 8 workers, fase 5 do leader) e `python3 tests/run_validators.py` em exit 0. As duas lacunas trazidas do `AUDIT.md` foram confirmadas no código; nenhuma outra apareceu.

## Findings

| ID | Gap Type | Severidade | Origem | Evidência | Trabalho restante |
|----|----------|------------|--------|-----------|-------------------|
| F1 | contradicts | HIGH | FR-002, FR-004, FR-010 | `_takeover_observation` (`plugin/skills/grill-with-docs/scripts/grill_workspace.py:1526`) faz `json.loads(raw)` e lê `show.get("dispatch")`/`show.get("projection")` no nível de topo; o transporte devolve `{ok, result}`, que é o que `_object` exige e desembrulha antes de `observe_predecessor_termination` ler os mesmos campos | T014 |
| F2 | partial | HIGH | FR-008 | `CHECKPOINT_SCHEMA_V2` e o par `context_inputs_sha256`/`origin_metadata_sha256` existem, e a validação escolhe as chaves pelo `schema` do documento (`grill_core/agent_orchestration.py:680-681`), mas os dois pontos de emissão (`grill_workspace.py:1869` e `:3354`) gravam `CHECKPOINT_SCHEMA` (v1) com os nomes antigos | T015 |

Nenhum achado CRITICAL. Nada `missing`. Nada `unrequested`.

### F1 em detalhe

Contra a resposta real do adapter, `status` e `liveness` saem sempre `None` de `_takeover_observation`. Duas consequências:

1. **Código de recusa errado para líder vivo.** Em `:3663-3666` o ramo `status in {"dispatched", "running"}` nunca dispara, então um líder ainda ativo é recusado como `TAKEOVER-EVIDENCE-UNPROVEN` em vez de `TAKEOVER-LEADER-ACTIVE`. Fail-closed está preservado — a tomada continua recusada —, mas FR-002 exige um código próprio e distinto por caso, e FR-010 exige dizer qual prova faltou.
2. **Prova vazia no registro de sucessão.** `evidence.dispatch_status` e `evidence.liveness` (`:3684`) nascem `None`, degradando exatamente o que FR-004 manda gravar.

Os testes de T007 passaram porque o fixture `takeover_show()` espelha **as duas** formas de propósito, documentando a inconsistência em vez de reprová-la — a correção em T007 estava fora do grant do worker. É o padrão conhecido de fixture mais permissiva que a realidade: o caso sintético cobre um formato que o mundo não produz.

### F2 em detalhe

FR-008 pede que os campos de digest tenham nomes correspondentes ao conteúdo **e** que a mudança venha em versão nova do formato. A metade de leitura está pronta e travada por teste; a metade de escrita não migrou, então todo ponto de retomada novo continua nascendo com `workflow_sha256`/`constitution_sha256`. FR-009 e SC-005 seguem satisfeitos de qualquer modo: a versão anterior continua legível e utilizável sem reescrita, e assim deve permanecer depois de T015.

## Cobertura verificada

| Item | Situação |
|---|---|
| FR-001, FR-003, FR-005, FR-006, FR-007, FR-011 | satisfeitos |
| FR-002, FR-004, FR-010 | F1 |
| FR-008 | F2 |
| FR-009 | satisfeito (validação aceita as duas versões, sem reescrita) |
| FR-012 | oito pontos em 6.0.3, `validate_distribution` OK; a release é ato do `ship` |
| SC-001 a SC-006 | cobertos pela suíte; SC-006 em exit 0 |
| SC-007 | fora do aceite desta entrega, por definição da própria spec |

## Constituição

Sem violação. O bump obrigatório está completo nos oito pontos. A cláusula de release por versão é cumprida no `ship`, pelo pipeline do push para `main`.

## Métricas

- Requisitos/critérios verificados: 12 FR + 6 SC aplicáveis
- Decisões de plano verificadas: 5 fases, 10 arquivos nomeados
- Cláusulas constitucionais verificadas: 11
- Achados: missing 0 · partial 1 · contradicts 1 · unrequested 0
- Severidade: CRITICAL 0 · HIGH 2 · MEDIUM 0 · LOW 0

## Próxima ação

Duas tarefas anexadas em `## Phase 6: Convergence` (T014, T015). Executar `implement-parallel` sobre elas e reconvergir; uma segunda passagem deve encontrar zero achados.
