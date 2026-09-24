## Ship Report

Status: MERGED
Source head: `5931d43` · Merge: `e1e46fae6410d5e7edaee966d8dbac4a3432ec4b` (pais `657e2baf` e `5931d43`) · Versão **6.0.28**
Source fingerprint (antes da quinta integração): tree `6ffdccda…` / work `e3b0c442…` / plan `84fd7c67…`

### Fase A — evidência consumida
- Converge rodada 25: CONVERGED, zero findings (rodada 24 consumiu o R12).
- Verify rodada 13: PASS — 31 validadores, 1536 testes, 0 falhas (skipped=1); distribuição em 6.0.28; 0 commits atrás da `main`.
- Review R12 independente (`claude-fable-5-1`/`high`, `ctx_8c5fd0a45053`): APPROVE, 0 Critical/0 Important, 3 Minor diferidos. Fecha as ressalvas r1/r2 da R11.
- Autorização humana: `SHIP-AUTHORIZATION.json` do work item, decisão `APPROVED`, escopo `ship`. O documento cita "release v6.0.25"; a versão publicada é **6.0.28** porque a `main` publicou 6.0.25–6.0.27 durante a transação. O escopo autorizado (merge `--no-ff`, push direto, release desta entrega) é o mesmo.

### Fase B — gate de aprendizados
| ID | Destino | Resultado |
|---|---|---|
| LRN-001 | backlog `SGD` | `SGD-36` (low): Minors m1–m3 do R12 diferidos |
| LRN-002 | memória do projeto | `status-timeout-journal-o-n`: `read_snapshot` é O(journal); ler uma vez por status; limpar worktrees não resolve |

Nenhuma mudança versionada no gate; sem revalidação adicional.

### Fase C/D — integração
- Primeira transação (base `657e2ba` ainda não integrada): **BLOCKED** por conflito com três publicações concorrentes da `main`; abortada sem push, worktree removida.
- Quinta integração na branch (`merge: integra origin/main 6.0.27; bump 6.0.28`), suíte verde, converge r25/verify r13/review r2 re-atestados.
- Segunda transação: worktree temporária a partir de `origin/main` `657e2baf`, merge `--no-ff` de `5931d43`, árvore idêntica à testada; `validate_distribution` e `validate_status_contract` reexecutados.
- Push direto para `refs/heads/main`, sem PR, sem force. Leitura de volta: `origin/main == e1e46fae`.

### Fase E — release e limpeza
- `publish to marketplaces` (run `35940471664`): success. Tag `v6.0.28` → `e1e46fae`; GitHub Release `v6.0.28` publicada.
- Worktree de integração removida. As 16 worktrees `wt-run-*` do work item `feature-new-subagents-unified` não pertencem a este ciclo e não foram tocadas.
- Portabilidade: a run da `main` em `657e2ba` (anterior ao push) falhou só em `macos-26 / Python 3.13`, `test_eight_concurrent_eligible_resumes…` com `STATE-DIVERGENCE` — flake conhecido do macOS, não regressão.

### Rollback
`git revert -m 1 e1e46fae` na `main` e nova versão acima de 6.0.28; consumidores podem fixar `v6.0.27`.

### Pendências fora deste ciclo
- `fix-presentation-suspension` (pré-requisito da feature) e o `converge` bloqueado de `feature-new-subagents-unified` (matriz T029 com 6.0.28 nos dois runtimes).
