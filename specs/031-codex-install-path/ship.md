## Ship Report

Status: MERGED
Source head: `e25cfe900d9cde9be7bbdfa15439c925e77bcd8e`
Source fingerprint: tree dc5dec79246a11c46c22e0440cf6d53ae88c700b42afbbb4e09f68e5aa88aafc / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 15e0cee81a10cb63b7cb3e8b1c8d43580db5b77c59726b1c616329944fb2449f

### Fase A — evidência consumida
- Converge r5: CONVERGED, zero findings.
- Verify r4: PASS na árvore final — suíte 30 validadores e 1477 testes (`exit 0`, 1 skip de macOS), smoke de portabilidade, bump `6.0.1 -> 6.0.2`, `git diff --check`.
- Review: APPROVE na R3 mais o adendo da árvore final; três rodadas independentes (R1 REQUEST CHANGES, R2 REQUEST CHANGES, R3 APPROVE), cada uma com revisor distinto do líder e dos workers.
- Autorização humana: `SHIP-AUTHORIZATION.json` do work item, decisão `APPROVED`, escopo `ship`.

### Fase B — gate de aprendizados
| ID | Destino | Resultado |
|---|---|---|
| LRN-001 | backlog `SGD` | item `SGD-34` (high): ensaio em worktree do mesmo repo gravou `agent_orchestration` no store compartilhado e quebrou o CLI 5.4.1 fixado |
| LRN-002 | backlog `SGD` | item `SGD-35` (medium): run sucessora obriga reconfirmar todos os nós anteriores |
| LRN-003 | memória do projeto | segmento com drive reancora o `Path`; recusar com `PureWindowsPath(v).name == v` |
| LRN-004 | agent-context | parágrafo em `CLAUDE.md` sobre a observação da instalação por runtime |

Commits do gate: `91904e1` (aplicação) e `fff13a3` (precisão de prosa após revisão independente do próprio commit). Revalidação: gates reexecutados na árvore final, verify r4 e review re-atestados.

### Fase C/D — integração
- Pré-flight: worktree limpa, branch de trabalho distinta da primária, `origin/main` contida no HEAD, merge `--no-ff`.
- Transação isolada: worktree temporária a partir de `origin/main` (`74d2968924335176ae31144682c098b3230dcac8`), merge de `e25cfe90`, gates de distribuição, bump e contrato de orquestração reexecutados na árvore mesclada.
- Merge: `f77958166e9ed6347bbee082735daaddbae66153` (pais `74d29689` e `e25cfe90`).
- Push direto para `refs/heads/main`, sem PR, sem force. Leitura de volta: `origin/main == f7795816`.

### Fase E — release e limpeza
- Pipeline `publish to marketplaces` disparado no push; tag `v6.0.2` = `21ac1ae3c9cc4b13ddca69d6f8728aa0eba7a335`; GitHub Release `v6.0.2` publicada como Latest.
- Worktree de integração removida; as worktrees dos workers deste ciclo foram limpas em cada convergência (`CLEANED`).
- Aviso de limpeza: permanecem 16 worktrees `wt-run-*` e suas branches, de campanhas anteriores do work item `feature-new-subagents-unified`. Não pertencem a este ciclo e não foram tocadas.

### Pendências fora deste ciclo
- Reexecutar a matriz T029 com a 6.0.2 instalada nos dois runtimes; `functional_verified` do work item de origem segue `false`.
- Work items abertos: `fix-continuity-context` e `fix-presentation-suspension`.
