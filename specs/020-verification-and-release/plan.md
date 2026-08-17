# Implementation Plan: Verificação e publicação

**Branch**: `feat/backlog-ssot` | **Spec**: [spec.md](./spec.md)

## Summary

Fase de fechamento. Quase nada a construir; o valor está em verificar o que as cinco anteriores afirmaram, e em não deixar a ressalva de portabilidade morrer por acumulação — ela apareceu em cinco relatórios seguidos.

A verificação encontrou dois defeitos reais, o que já justifica a fase por si só.

## Constitution Check

| Cláusula | Status | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | FR-006 conferido caso a caso: os treze defeitos da milestone têm regressão nomeada, verificado por busca e não presumido pela contagem de testes. |
| Work item isolado | PASS | Sem escrita fora do bundle. |
| Feature/fix plan-only | PASS | Ciclo externo. |
| Sequência obrigatória | PASS | Matriz resetada por `phase-turn`. |
| Verify/review antes de ship | PASS | É o tema da fase. |
| Fail-closed sem waiver | PASS | A publicação exige autorização explícita e não ocorreu. |
| Rastreabilidade | PASS | As cinco fases anteriores estão referenciadas no ROADMAP e no PLAN-CONTEXT. |
| Bump obrigatório | PASS | **3.2.0 → 3.2.1**, correção. |

## Project Structure

Sem estrutura nova. As correções desta fase tocaram `grill_workspace.py`, `backlog_bridge.py` e o validador da ponte.
