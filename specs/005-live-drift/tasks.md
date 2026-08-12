# Tasks — FASE-002

## T-001 — Separar as duas comparações
**Arquivo**: `plugin/skills/grill-with-docs/scripts/grill_status.py`

A comparação de commit deixa de emitir achado. A de ramo passa a valer apenas enquanto o work item não for terminal, com terminal derivado dos mesmos campos que o auditor usa.

**Pronto quando**: os quatro cenários da spec produzem o resultado declarado.

## T-002 — Contrato executável
**Arquivo**: `tests/validate_status_contract.py`

Cobre CHK-001 a CHK-011, incluindo a preservação do contrato de saída.

**Pronto quando**: a suíte passa e a contagem sobe.

## T-003 — Prova contra o work item real
**Depende de**: T-001

O work item concluído da milestone anterior, lido de `main`, deixa de produzir achado. É a evidência que motivou a fase.

**Pronto quando**: `status` devolve veredito não bloqueado por deriva.

## T-004 — Bump
**Arquivos**: os oito de `CLAUDE.md`

2.5.2 → 2.5.3.
