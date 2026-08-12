# Converge — FASE-003

## O que entrou

`.github/workflows/bump-gate.yml` novo, sem `paths:`, com `fetch-depth: 0` e a base vinda do payload do evento. O job saiu do `ci.yml`, que fica só com a matriz, seu filtro e a guarda de deduplicação.

`tests/validate_bump_gate_contract.py` ganhou a classe `WorkflowWiring`: 35 → 42 testes. Ela existe pelo risco declarado no plano — errar o arquivo novo deixaria o repositório sem gate sem sintoma.

## Prova na própria fase

Esta proposta muda `.github/`, `tests/`, `specs/`, `.grill/` e `CLAUDE.md`. Nada em `plugin/`, confirmado por diff. Sob a configuração anterior ela casaria o filtro do `ci.yml` (por `tests/**` e `.github/workflows/ci.yml`) e o gate reportaria — mas uma proposta que mudasse só `README.md` ou `specs/**` não casaria nada, e o gate ficaria mudo. É esse buraco que fecha aqui.

Como não toca `plugin/`, o merge também não publica: é a fase que exercita o caso negativo do pipeline.

## Suíte

316 testes, exit 0. `validate_bump_gate_contract` 35 → 42.
