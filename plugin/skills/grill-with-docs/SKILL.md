---
name: grill-with-docs
description: Entrevista decisões arquiteturais por work item isolado, mantém feature plan-only e oferece hotfix-fast executável com HOTFIX-GO fail-closed.
argument-hint: "iniciar|retomar|pausar|auditar|conciliar|migrar|status|checkpoint <git-root>"
---
# Grill with Docs v9.3.1

Protocolo **plan-only** para uma feature, fix ou hotfix em worktree/branch dedicada. Cada trabalho possui identidade e artefatos próprios; o estado global é somente uma projeção de trabalhos concluídos.

```text
worktree A ──> .grill/work-items/<work-id-A>/ ─┐
worktree B ──> .grill/work-items/<work-id-B>/ ─┼─> reconcile ─> .grill/global/
worktree C ──> .grill/work-items/<work-id-C>/ ─┘
```

## Regras invioláveis

1. Nunca grave artefatos decisórios no root legado durante um trabalho novo.
2. Nunca escreva no diretório de outro `work_id`.
3. `WORKFLOW.md` e `.specify/memory/constitution.md` são project-wide.
4. A Constituição é criada no-clobber somente pelo bootstrap `init`; depois é read-only. Ausência no init é bootstrap pendente, não `not-present`.
5. Nenhum ADR, decisão local ou reconciliação pode dispensar, enfraquecer ou violar a Constituição.
6. Hooks são read-only e nunca criam work items automaticamente.
7. Hotfix-fast é uma exceção operacional fechada: exige escopo, reprodução/evidência, teste de correção, rollback e evidência constitucional; não depende de ROADMAP, BL, DQ ou reconciliação para ser seguro.
8. Feature e fix permanecem plan-only; hotfix só entrega HOTFIX-GO para ship externo. Depois do ship, `hotfix-close` prova o commit na branch de integração e sela o fechamento; só então vêm a reconciliação e a auditoria documental completa.
9. A sessão de entrevista termina em `PLAN_ONLY_STOP`; nela não se implementa código, não se executa `specify|plan` e não se faz commit/merge. O ciclo externo é outra trilha, aberta por ato humano.

## Bootstrap de apresentação obrigatório

Em toda entrada GWD (`iniciar`, `retomar`, reentrada após compactação e sessão de especialista), aplique `i-have-adhd@i-have-adhd` como referência de apresentação **local deste fluxo** antes da primeira resposta de trabalho. Resolva a instalação efetiva do runtime, confirme habilitação e confiança por observações separadas, leia integralmente o `SKILL.md` aprovado indicado pelo `load_request` e registre o evento correlacionado à mesma sessão, configuração e escopo GWD. Não peça ao usuário para invocar a skill upstream, não execute seu hook e não crie flag/configuração global.

Instalado, enabled, saída zero, catálogo, hash impresso ou autorrelato não comprovam `loaded` nem comportamento. Só `work_ready` permite entrada ou despacho: normalmente exige `use_ready`; `stop adhd mode` documentado na mesma sessão/incarnation/escopo mantém apenas `work_ready` após compactação, com `use_ready=false`, sem reinjetar o corpo. Nova sessão, troca de runtime/incarnation e reativação explícita voltam ao padrão ativo e exigem nova leitura. Preserve Ponytail, instruções superiores, conteúdo solicitado, exceções upstream, arquivos/grants e o escopo local; saída do fluxo GWD é `out_of_scope`.

## Orquestração por versão

A versão do work item seleciona o contrato: v3/v4 conservam a policy v1 e o
[suplemento histórico](references/agent-orchestration.md); v5 usa
`assets/agent-orchestration.v2.json` e o [suplemento v2](references/agent-orchestration.v2.md).
Novos projetos materializam v5; projetos existentes conservam seu WORKFLOW.md.
Não migrar trabalho ativo implicitamente nem reinterpretar DAGs, catálogos ou receipts.

Leia o [protocolo de sessão](references/session-protocol.md) para admissão, capabilities,
cleanup, continuidade e recuperação. O líder invoca as onze skills canônicas na sessão
ativa e persiste seus retornos. Sol no Codex e Opus no Claude são recomendações,
não trocas automáticas. Autoria especializada continua xhigh; revisão independente high.
O coordenador Orca inicia o líder com `worker-start`, mantém seu próprio terminal aberto e, após o relatório final e `worker_done` aceito, executa `worker-release` com read-back do Dispatch. Pausa conserva a sessão. Workers e especialistas também encerram por settlement, release e read-back antes de declarar cleanup concluído; `terminal close` não substitui esse fluxo.
No v5, somente plan/review exigem revisão fixa; risco material exige revisão extra.
`gauntlet-step-enter` entrega a classificação e seu hash, atividades e suplementos exigidos.
Ausência de evidência bloqueia; entrega de contexto não atesta execução.

Antes de novo despacho, aproveite resultados aceitos via `gauntlet-tasks-import` ou
`gauntlet-tasks-rebase`, conforme o protocolo. Não repita trabalho aceito para resolver
cleanup pendente ou resultado desconhecido. `PLAN_ONLY_STOP` continua encerrando a entrevista.

## Entrada e entrevista

Antes de iniciar trabalho, leia no [protocolo de sessão](references/session-protocol.md)
o bootstrap, a seleção de policy e o contrato de entrevista da versão correspondente.
Antes de executar cada operação, leia sua seção no [manual de work items](references/work-item-operations.md):
triagem, init, dependências/backlog, Constituição, auditoria, atestação, reconciliação ou migração.
O manual mantém os argumentos e recusas completos; não inferir flags nem emular handlers.

Para a entrevista, carregar Constituição, WORKFLOW, CONTEXT, ADRs, ROADMAP,
DECISION-BACKLOG, PLAN-CONTEXT e handoff selecionado, somente do work item atual.
Classificar cenário, registrar evidência e selecionar DQs materiais com dependências satisfeitas.
V3/v4: uma pergunta atômica por rodada. V5: até três independentes; respostas parciais
mantêm DQs sem resposta pendentes. Registrar transição por DQ, impact scan e log append-only.
Duas rodadas sem progresso, três expansões consecutivas ou 25 perguntas materiais exigem
checkpoint e SAFETY_STOP. Pausa humana grava PAUSED_USER; contradições são preservadas.
Após auditoria GO e handoff, emitir PLAN_ONLY_STOP e parar; sem implementação ou ship.

## Decisões tipadas via Jev

`OPENROUTER_API_KEY` é obrigatória: sem ela `init` e `preflight` recusam com
`OPENROUTER-KEY-REQUIRED`. Antes de decidir em prosa, rode
`grill_workspace.py decide ROOT --kind K[,K2] --file ... [--context JSON] --work-id ID`.
Kinds do mesmo momento vão numa chamada só (`--kind triage,bug-type`).
Use `decided` sem deliberar e responda só as `pending` (`decided_by` = `jev|partial|agent`).
Quando: `step-assessment` antes de cada etapa (`--step --apply`); `round-record` após cada
resposta de DQ; `dq-batch` e `human-or-author` ao montar o lote; `triage`, `bug-type`;
`delivery-classification` (`context.proposed`, divergência = pergunte ao humano);
`constitution-check` (só antecipa VIOLATION); `partition-groups` (só sugere o teto
`--groups` do `partition-emit`; o agrupamento segue determinístico em código); `finding-severity`
após analyze/converge/review (`context.findings` com `proposed`; só confirma ou sobe);
`spec-coverage` e `diff-hygiene` no verify (só NO-GO/sinalização); `learning-route` no ship.
Depois de decidir as pendentes, registre a resposta final com `decide-label`.
Entre etapas use `advance` (fecha a corrente, classifica e abre a seguinte); depois de
supersessão ou integração da main, `attest --rechain` recunha a cadeia stale de uma vez.
Falha de API é fail-closed (`JEV-UNAVAILABLE`, `OPENROUTER-*`): pare e reporte.
O Jev nunca substitui skill canônica nem review obrigatório.

## Status humano canônico

Para status, execute `python3 .../grill_workspace.py status ROOT --format markdown`
e reproduza stdout literalmente, sem resumir, traduzir ou acrescentar explicações.
Status, hooks e diagnóstico são read-only. Falha de bootstrap permite diagnóstico,
nunca declarar apresentação funcional sem prova correlacionada.
