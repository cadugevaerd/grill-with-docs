## Ship Report

Status: MERGED
Source fingerprint: tree c85b04c9eda75dae2ca672b3e9a8990222d15155de7d29da8021ed56a76681cd / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan ac49cbc2c8496efb1077406d34bb3fae1f195f05f27c0d28360967c402f16c68
source_head: fd1bb5f89b6c1823854d9280f9519cfa07a1fd02

### Phase A — Evidence Freshness

| Report | Result | Fingerprint |
|---|---|---|
| Converge | CONVERGED (4ª passagem) | casa |
| Verify | PASS | casa |
| Review | APPROVE | casa |

Quatro passagens de Converge foram necessárias. A primeira e a terceira retornaram `tasks_appended`; ambas foram implementadas antes de prosseguir. Nenhum achado Critical ou Important permanece aberto.

Rollback: reverter o commit de merge `68adb0d` restaura `main` a `e75de41`. Nada foi publicado, então não há tag nem entrada de marketplace a retirar. Monitoramento: a matriz de CI é o próximo sinal e ainda não rodou nesta árvore.

### Phase B — Learning Gate

Configuração ausente no arquivo ativo (`ship.learning_gate.auto_commit_versioned_changes`), o que é `BLOCKED` por invariante. Resolvido acrescentando o bloco `ship`, **adaptado** e não copiado do template: `allow_targets` exclui `adr-docs` e `backlog` porque este repositório não tem destino estático válido para nenhum dos dois — o backlog é externo (`backlogctl`/SGD, sem `BACKLOG.md`) e os ADRs vivem por work item, não num `docs/adr` de raiz. Rotear para os caminhos do template escreveria no lugar errado.

| ID | Aprendizado | Evidência | Rota | Decisão |
|---|---|---|---|---|
| LRN-001 | `open → done` é ilegal na FSM do backlog | 25 pares medidos em banco descartável | discard | duplicado de ADR-0003 |
| LRN-002 | A matriz de CI não tem `backlogctl`; cobertura não pode consultar store real | restrição declarada do projeto | discard | duplicado do CLAUDE.md |
| LRN-003 | Um gate não deve validar artefato mutável contra hash do momento da criação | defeito `BUNDLE-INTEGRITY`, insatisfazível por construção | agent-context | **DEFERRED** |
| LRN-004 | Falha sobre escrita já persistida também existe em `checkpoint` e `phase-turn` | SGD-14 | discard | já rastreado no backlog |

LRN-003 é o único candidato novo e é decisão de política do operador. Deferido: nada foi aplicado, nenhuma regra foi enfraquecida, e o candidato fica registrado aqui para decisão futura. Nenhuma mudança versionada foi aplicada pelo gate, portanto nenhuma revalidação de B4 foi disparada por ele.

### Phase C — Git Pre-flight

Worktree limpo, branch de trabalho `feat/backlog-ssot` distinta da primária `main`, nenhuma operação em curso, remote `origin` descoberto, `main` idêntica a `origin/main` no início, estratégia `no-ff` conforme configuração.

### Phase D — Integration

Merge `no-ff` produziu `68adb0d`, com dois pais: `e75de41` (main anterior) e `fd1bb5f` (ponta do trabalho). Gates reexecutados sobre o resultado do merge: 972 testes exit 0, `distribution: OK` em 2.9.0, worktree limpo.

**Push não executado, por decisão explícita do operador.** `main` local está à frente de `origin/main` em 20 commits. A consequência que motivou a decisão: `publish.yml` dispara em `push` para `main` filtrando `paths: plugin/**`, e esta fase toca `plugin/**`, então o push criaria a tag `v2.9.0` e atualizaria dois marketplaces públicos. O ROADMAP já concentra a publicação na FASE-005, que fecha o marco em 3.0.0.

### Phase E — Memory and Cleanup

`memory.mode` é `propose-only`, e a escrita depende de verificação do ref remoto, que não ocorreu. Permanece pendente, corretamente.

Branch `feat/backlog-ssot` preservada, não removida: o work item continua vinculado a ela e as fases seguintes correm no mesmo trabalho.

### Phase F — Consequência aberta

Uma ressalva do Verify permanece aberta e só o push a fecha: SC-005 exige a suíte verde nos três sistemas operacionais, e apenas a matriz de CI verifica isso. Enquanto a branch não subir, a portabilidade desta fase está verificada em um único sistema.

### Resume

- Para publicar: `git push origin main`, que dispara a release 2.9.0.
- Para validar sem publicar: `git push origin feat/backlog-ssot` e abrir PR; `publish.yml` não dispara em branch.
