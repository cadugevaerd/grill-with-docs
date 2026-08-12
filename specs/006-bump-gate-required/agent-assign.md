# Agent assignment — FASE-003

Sequencial, dono único: dois arquivos de workflow e um contrato.

| Dono | Tasks | Arquivos |
|---|---|---|
| Sessão primária | T-001, T-002 | `.github/workflows/bump-gate.yml`, `.github/workflows/ci.yml` |
| Sessão primária | T-003 | `tests/validate_bump_gate_contract.py` |
| Sessão primária | T-004 | `CLAUDE.md` |

Modo de falha a caçar: **ficar sem gate sem perceber**. A migração remove o job de um lugar e o recria em outro; se o segundo estiver errado, nada reclama até alguém mergear conteúdo distribuído sem bump.
