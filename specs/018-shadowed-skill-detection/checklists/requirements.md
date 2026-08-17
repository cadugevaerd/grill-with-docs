# Specification Quality Checklist: Detecção de skill sombreada

**Created**: 2026-08-17 · **Feature**: [spec.md](../spec.md)

## Content Quality
- [x] No implementation details · [x] User value · [x] Non-technical readable · [x] Sections complete

## Requirement Completeness
- [x] No clarification markers · [x] Testable · [x] Measurable criteria · [x] Technology-agnostic
- [x] Acceptance scenarios · [x] Edge cases · [x] Scope bounded · [x] Assumptions identified

## Feature Readiness
- [x] FRs have acceptance criteria · [x] Scenarios cover flows · [x] Meets outcomes · [x] No implementation leak

## Notes

Uma iteração. Dois pontos ganharam requisito próprio depois de examinar os casos de borda:

- **FR-005**, atalho quebrado conta como sombra. É o caso que uma implementação ingênua perde, porque `exists()` é falso para ele.
- **FR-009**, remover o atalho e não o destino. Sem isso, "remover a sombra" poderia destruir a skill pessoal que o operador só queria renomear.

A premissa final também foi acrescentada por precisão: a inspeção não decide qual cópia vence a resolução do agente hospedeiro. Ela reporta a coexistência, que é o fato verificável sem reimplementar a lógica de cada hospedeiro.
