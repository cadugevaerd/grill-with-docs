# Tasks — FASE-003

## T-001 — Workflow próprio do gate
**Arquivo**: `.github/workflows/bump-gate.yml` (novo)
Move o job, sem `paths:`, preservando `fetch-depth: 0` e a base vinda do payload.

## T-002 — Remover o job do workflow da matriz
**Arquivo**: `.github/workflows/ci.yml`
O `ci.yml` fica só com a matriz, o filtro e a guarda de deduplicação.

## T-003 — Contrato executável
**Arquivo**: `tests/validate_bump_gate_contract.py`
Cobre CHK-001 a CHK-009 lendo os dois YAMLs.

## T-004 — Declarar o ato humano
**Arquivo**: `CLAUDE.md`
O que precisa ser marcado como required na proteção da linha principal, e por quê.
