# Evidência de validação — FASE-001

- data: 2026-08-21
- branch: feat/status-markdown
- escopo: status JSON/Markdown, skill, distribuição e regressões

## Comandos aprovados

- `PYTHONDONTWRITEBYTECODE=1 python3 tests/validate_status_contract.py` — 44 testes OK.
- `PYTHONDONTWRITEBYTECODE=1 python3 tests/validate_distribution.py` — `distribution: OK` na versão 3.4.0.
- `PYTHONDONTWRITEBYTECODE=1 python3 tests/run_validators.py` — todos os validadores concluíram com exit 0; um teste de alias macOS foi skipped pela ausência do alias no host Linux.
- `git diff --check` — sem erro de whitespace.
- Integração em `main` no commit `b5f4ffe1bc9d3b5d7b34dd9ed954acad15efd0d0` — a suíte completa foi repetida após o merge e concluiu com exit 0.

## Revisão local

O JSON padrão continua `grill-status/v1`. A nova projeção Markdown é invocada por `status --format markdown`, é read-only, omite apenas itens coerentemente fechados e produz `all good` somente quando não há pendência. A mudança foi revisada contra os oito critérios do handoff FASE-001.
