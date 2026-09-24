# Pedido e escopo único

Owner: Carlos Araújo. Sessão condutora: Claude Code (Opus). Branch: cadugevaerd/feat-new-subagents.
Origem: T029 do work item `feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa` (2026-09-19); registro em `STYLE-LIVE-VALIDATION.md`, commit `3d177d9`. Triagem: tri-continuity-context (bugfix, high, triage_sha256 23e82b8f…; laudo `.grill/triage-evidence/continuity-context-debug.md`).

## Requisitos solicitados

Corrigir o ciclo de vida do contexto de orquestração GWD 6.0.0 nas quatro lacunas observadas no ensaio live:

1. **Líder morto.** Nenhum verbo deixa uma sessão nova assumir um work item cujo líder não existe mais. `init --work-id` recusa com `CONTEXT-FENCED` ("existing leader observation differs"), `gauntlet-orchestration-adopt` recusa com `CONTEXT-FENCED` ("existing context has different runtime or session", `grill_workspace.py:1691`), e `gauntlet-resume` exige checkpoint de `gauntlet-prepare-switch`, que só a sessão de origem pode emitir. O bundle `feature-claude-matrix-ensaio-24e485a9…` do ROOT de ensaio ficou preso a um líder de 2026-09-15.
2. **Preview do adopt.** O preview de `gauntlet-orchestration-adopt` devolveu `PREVIEW` com `expected_sha256=0e6c7aa5…`, e o apply com esse hash recusou `CONTEXT-FENCED`. O preview não detecta a recusa que o apply aplicará.
3. **Troca antes do primeiro checkpoint.** `gauntlet-prepare-switch` recusa com `CONTINUITY-CHECKPOINT-MISSING` enquanto nenhuma etapa foi confirmada com `--operation-id` (`grill_workspace.py:3301-3303`, `:1861`). Um work item recém-criado não pode ser passado a outra sessão nem a outro runtime. Foi preciso fechar `specify` inteiro, com autor e revisor, só para habilitar a troca.
4. **Rótulos do checkpoint de continuidade.** Em `grill_workspace.py:1812-1813`, o checkpoint grava `workflow_sha256 = context.inputs_sha256` e `constitution_sha256 = origin.metadata_sha256`, e não os digests de `WORKFLOW.md` e da Constituição que os nomes sugerem (observado: `e0a30cb8…` e `4786e719…` contra `d2c4ea08…` e `54d5522b…`). `data-model.md:87` da spec 030 não define a semântica. A retomada funcionou porque os dois lados usam as mesmas derivações. O que falta decidir é se o nome ou o conteúdo está errado, e se uma mudança de WORKFLOW ou da Constituição entre a troca e a retomada é detectada.

## Restrições conhecidas

- Fail-closed sem waiver: assumir um item de outro líder exige prova de que o líder anterior não está ativo, nunca por silêncio.
- Sem forjar identidade nem editar o store à mão.
- Stdlib apenas; testes offline pelos seams injetáveis.

## Fora do escopo

Instalação Codex (`fix-codex-install-path-693af70e…`) e suspensão da apresentação (`fix-presentation-suspension-d97e4c3d…`).
