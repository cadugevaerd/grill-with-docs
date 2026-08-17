# Specification Quality Checklist: Pré-requisito fail-closed

**Created**: 2026-08-17 · **Feature**: [spec.md](../spec.md)

## Content Quality
- [x] No implementation details · [x] Focused on user value · [x] Non-technical readable · [x] Mandatory sections complete

## Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers · [x] Testable and unambiguous · [x] Measurable success criteria
- [x] Technology-agnostic criteria · [x] Acceptance scenarios defined · [x] Edge cases identified
- [x] Scope bounded · [x] Dependencies and assumptions identified

## Feature Readiness
- [x] Every FR has acceptance criteria · [x] Scenarios cover primary flows · [x] Meets measurable outcomes · [x] No implementation leak

## Notes

Uma iteração, com um achado que virou requisito.

O caso de borda "trabalho criado com a saída e depois vinculado" expôs uma armadilha que nenhuma versão anterior do plano tinha: sem caminho para limpar o registro, o trabalho ficaria **permanentemente** bloqueado — a saída de emergência viraria uma cela. Virou FR-008, e SC-005 o torna verificável.

Também ficou explícito que a exigência é de **vínculo**, não de presença do binário. Ter `backlogctl` instalado e não estar vinculado é o caso comum num repositório novo, e é exatamente o que precisa recusar.

Zero marcadores de clarificação: a política da saída explícita já fora decidida e registrada antes desta fase.
