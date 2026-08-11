# Agent Assign — ownership e escopo de arquivos

Dois executores, escopos de arquivo disjuntos, sem worktree isolada por não haver interseção.

## AG-1 — Verificador e seus testes
- **tasks**: T-001, T-002, T-003
- **file scope (exclusivo)**: `tests/check_version_bump.py`, `tests/validate_bump_gate_contract.py`
- **proibido tocar**: `plugin/**`, `.github/**`, qualquer validador existente
- **contrato de entrada**: `contracts/cli.md`, `data-model.md`
- **contrato de saída**: suíte verde localmente; os cinco códigos de verdict exercitados

## AG-2 — Job de CI
- **tasks**: T-004
- **file scope (exclusivo)**: `.github/workflows/ci.yml`
- **proibido tocar**: `tests/**`, `plugin/**`
- **contrato de entrada**: `contracts/cli.md` fixa invocação e exit codes, então AG-2 não depende do código de AG-1 estar pronto
- **contrato de saída**: job novo apenas em `pull_request`, matriz existente inalterada

## Paralelismo

AG-1 e AG-2 correm em paralelo. A dependência T-002 → T-004 é satisfeita pelo contrato de linha de comando já congelado, não pelo código.

T-005 é sequencial, executada pelo orquestrador após os dois, e valida a integração real.
