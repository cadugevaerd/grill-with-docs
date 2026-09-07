# Ship Report — 027 sucessão explícita de escopo reconciliado

Status: **MERGED_WITH_CLEANUP_WARNINGS**

## Hashes

| Item | Valor |
|---|---|
| `source_head` | `a3af1c766846d6b4ab1a517afe31279dfeda777d` |
| Merge commit | `ca0a75eef0a6366a131955af7f2ed7dcf4533535` |
| `origin/main` antes | `070bb29d15ea25207d46266405aaa40534a45d91` |
| `origin/main` depois | `ca0a75eef0a6366a131955af7f2ed7dcf4533535` |
| Source fingerprint | tree `1c39f65b4dad…` / work `e3b0c44298fc…` / plan `fb440b73d378…` |

`work` é o sha do vazio: nada pendente no escopo medido no momento da decisão.

## Phase A — Frescor da evidência

| Evidência | Resultado | Fingerprint |
|---|---|---|
| Converge | `CONVERGED` (segunda passada, zero findings) | fonte inalterada desde `7cb6529` |
| Verify | `PASS` | tree `1c39f65b` / work `e3b0c442` / plan `fb440b73` |
| Review | `APPROVE` | idêntico, nos três componentes |

Rollback e monitoração: presentes em
`.specify/reports/verify-review-ship/rollback-and-monitoring.md`, exigidos por
`require_rollback_plan` e `require_monitoring_notes`.

Findings Critical ou Important em aberto: nenhum.

### Primeira tentativa de ship, recusada

A primeira invocação retornou `BLOCKED` / `STALE-EVIDENCE` em Phase A, e a recusa
estava correta: `verify`, `review` e a árvore reportavam três fingerprints
diferentes.

A causa não era o código. `converge.fingerprint_exclude` declarava
`.grill/attestations/**`, caminho que não existe sob o protocolo grill — os
bundles ficam em `.grill/work-items/<work_id>/attestations/`. Cada etapa de gate
cunha o próprio receipt ali, então `verify` e `review` moviam o fingerprint entre
as medições. Reexecutar não resolvia: produzia outro bundle e outro valor. Era o
laço que o comentário da própria config descreve, acontecendo de fato.

O ciclo parou e devolveu o código exato ao humano em vez de contornar. A correção
foi autorizada explicitamente e é a mais estreita que resolve — acrescenta o
padrão correto, não uma exclusão cega de `.grill/**`, preservando detecção sobre
`WORK-ITEM.json`, evidência de triagem e `gauntlet.yaml`. `verify` e `review`
foram então **reexecutados** sob a regra corrigida; nenhum relatório medido sob a
regra defeituosa foi reaproveitado.

Estabilidade comprovada antes de reexecutar: cunhar um bundle no diretório de
atestações e medir de novo devolve `tree` e `work` idênticos.

## Phase B — Learning gate

`--approve all`. `allow_targets`: `agent-context`, `memory`, `discard`.
`memory.mode: propose-only`.

| ID | Evidência | Destino | Estado |
|---|---|---|---|
| LRN-001 | `fingerprint_exclude` apontava caminho inexistente; `ship` recusou por `STALE-EVIDENCE` | `discard` | Já aplicado — a correção versionada é o próprio aprendizado |
| LRN-002 | O leitor da config para na primeira linha não-item; comentário interleaved descarta o resto em silêncio. A primeira tentativa de correção caiu nisso | `memory` | PENDING |
| LRN-003 | `gauntlet-partition-brief` não declara o schema que `gauntlet-tasks-reconcile` lê (`document["completed"]`); os quatro workers inventaram formatos e a reconciliação marcou zero tarefas | `memory` | PENDING |
| LRN-004 | A barreira de fase não propaga conteúdo: o worktree da wave 2 nasceu do `base_commit` fixado, sem o merge de `p01-a` | `memory` | PENDING |
| LRN-005 | `partition` só reconhece token de caminho contendo `/`; arquivo de raiz é infenceável por worker | `memory` | PENDING |
| LRN-006 | Core recusa re-selar artefato byte-idêntico (`SUPERSEDE_WITHOUT_CHANGE`) | `discard` | Duplicata de memória existente |

Nenhum candidato justifica emenda constitucional, e `constitution` não está em
`allow_targets` de todo modo. **Nenhuma mudança versionada aplicada em B3**, logo
B4 não disparou e a evidência permaneceu fresca até o merge.

## Phase C — Git pre-flight

Worktree nomeado e limpo (0 pendências), branch de trabalho
`fix/reconcile-scope-succession` distinta da primária `main`, nenhuma operação em
progresso, remoto `origin` e base `main` descobertos da config, estratégia
`no-ff`. `origin/main` (`070bb29`) contido no HEAD de trabalho: sem divergência,
sem mudança concorrente na primária.

## Phase D — Transação de integração isolada

Worktree de integração destacado, criado a partir de `origin/main` recém-buscado
— o checkout principal não foi tocado, e nenhuma branch foi trocada nele.

1. `git merge --no-ff a3af1c7` — limpo, sem conflito.
2. Gates reexecutados **na árvore integrada**, não na de trabalho: 27
   validadores exit 0, `distribution: OK`, bump `BUMPED` 5.2.0 → 5.2.1.
3. `git push origin HEAD:main`, sem force: `070bb29..ca0a75e`.
4. Leitura de volta do remoto: `git ls-remote origin refs/heads/main` devolve
   `ca0a75ee…`, **igualdade exata** com o commit local.

## Phase E — Memória e limpeza

Memória: quatro candidatos `PENDING` sob `propose-only`. Não escritos por este
gate; `memory.required: false`, então não há falha pós-merge.

Limpeza:

- Worktree de integração: **removido**.
- Worktrees dos quatro workers: **não removidos**. `gauntlet-cleanup` recusa com
  `BLOCKED / run is not eligible for worker preparation` — o run está `COMPLETE`
  e o verbo só opera em run elegível para preparação. Não foram removidos à mão:
  a skill proíbe deletar trabalho sem lease, e forçar aqui trocaria um aviso
  visível por uma remoção silenciosa fora do protocolo.

Caminhos remanescentes, todos com o conteúdo já integrado em `main`:

```
.git/grill/wt-run-dce0a5f093cd802b34084842-p01-a   f853341
.git/grill/wt-run-dce0a5f093cd802b34084842-p02-a   1f5b804
.git/grill/wt-run-dce0a5f093cd802b34084842-p02-b   835622c
.git/grill/wt-run-dce0a5f093cd802b34084842-p02-c   567832a
```

Nenhum trabalho é perdido por deixá-los: cada commit acima é ancestral de
`ca0a75ee`. O aviso é sobre disco e higiene, não sobre dados. Removê-los exige
`git worktree remove` manual ou um verbo de limpeza que aceite run terminal.

Falha de limpeza **nunca** reverte um merge verificado, e este relatório não
esconde o aviso.

## Resultado

`MERGED_WITH_CLEANUP_WARNINGS`. O merge está verificado no remoto; a única
pendência é a remoção dos quatro worktrees de worker.

Ação segura de continuação, se desejado: remover cada worktree com
`git worktree remove <caminho>`, ou `git worktree prune` depois de conferir que
nenhum tem trabalho não integrado — o que já está conferido acima.
