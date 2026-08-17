# Specification Quality Checklist: Migração de bundles legados

**Created**: 2026-08-17 · **Feature**: [spec.md](../spec.md)

## Content Quality
- [x] No implementation details · [x] User value · [x] Non-technical readable · [x] Sections complete

## Requirement Completeness
- [x] No clarification markers · [x] Testable · [x] Measurable criteria · [x] Technology-agnostic
- [x] Acceptance scenarios · [x] Edge cases · [x] Scope bounded · [x] Assumptions identified

## Feature Readiness
- [x] FRs have acceptance criteria · [x] Scenarios cover flows · [x] Meets outcomes · [x] No implementation leak

## Notes

Um achado durante a redação virou FR-011: estado inválido recusa o bundle **inteiro**. A formulação natural seria pular a decisão problemática e migrar o resto, mas isso deixaria o registro meio autoral e meio projetado, sem sinal que distinguisse o que já moveu. A recusa total é recuperável; a migração parcial não.

FR-009 e FR-010 dividem o comportamento sobre bundle autoral entre mutação, que recusa, e leitura, que conclui e aponta. Sem essa divisão, o operador perderia o diagnóstico exatamente quando precisa dele.
