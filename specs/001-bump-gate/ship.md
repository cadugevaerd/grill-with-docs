# Ship Report — FASE-001

## A. Aprendizados aprovados

Registrados em `specs/001-bump-gate/learnings.md`. O principal: detecção de rename esconde remoção de escopo, e isso vale para qualquer gate futuro baseado em prefixo de caminho — inclusive o de publicação da FASE-002.

## B. Revalidação

| Item | Resultado |
|---|---|
| Constituição | sha256 `789b55f4…` inalterado |
| Auditoria do work item | `GO`, FASE-002 selecionada, zero findings |
| Suíte | 237 testes, exit `0`, 1 skip dependente de ambiente |
| O próprio gate sobre este merge | `NO-PLUGIN-CHANGE` — a mudança não toca `plugin/`, logo não exige bump |

A última linha é dogfooding: a primeira decisão que o gate tomou foi sobre o merge que o introduz.

## C. Merge

`git merge --no-ff 001-bump-gate` em `main`. Merge commit `9699b1c` com dois parents (`8f72cef`, `4670da7`). Gates reexecutados após o merge: verdes.

## D. Push

Push direto em `origin/main`, sem PR. Ref relida após o push: local e remoto em `9699b1c`. Confere.

## E. Limpeza

Removidas: `001-bump-gate`, `feat/release-repo-sync`. Worktree único, sem worktree temporária pendente. Clone descartável de teste removido.

**Aviso de limpeza, não suprimido**: quatro branches de trabalhos anteriores permanecem no repositório, todas já mergeadas em `main` — `chore/version-speckit-stack`, `feat/backlog-code-override`, `feat/init-dependency-bootstrap`, `fix/version-headings`. Não foram removidas por não pertencerem a esta fase.

## Follow-ups registrados no backlog externo

| Item | Origem | Criticidade |
|---|---|---|
| `SGD-3` — migrar a credencial de publicação para escopo mínimo | ADR-0004 / BL-0001 | herdada do BL |
| `SGD-4` — registrar `bump-gate` como required status check | achado do revisor sobre FR-007 | high |
| `SGD-5` — gate não redispara ao retargetar a PR | achado do revisor | low |

`SGD-4` é o que impede FR-007 de estar plenamente satisfeito: o job reprova, mas só bloqueia a integração se a branch protection exigir o check.

## Fim do ciclo

FASE-001 `complete`. FASE-002 `ready-for-specify`, com handoff próprio. BL-0001 `resolved` com `final-ref: ADR-0004`, e o acompanhamento vive em `SGD-3`.
