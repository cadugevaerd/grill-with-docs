# Specification Quality Checklist: Projeção versionada e determinística das decisões

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-17
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

Duas iterações.

Primeira passagem, reprovações corrigidas:

- nomes de arquivo e de comando apareciam nos requisitos (`DECISION-BACKLOG.md`, `backlogctl`, `resolve_cli`); substituídos por **registro de decisões**, **autoridade** e **ponto de injeção**. Os nomes concretos permanecem no handoff e no PLAN-CONTEXT do work item, que são os lugares do HOW.
- FR-006 dizia "fingerprint", termo de implementação; virou **marca de origem**, e FR-007 passou a declarar a propriedade que importa — insensibilidade a mudança fora do trabalho — em vez do algoritmo.
- SC-002 e SC-003 eram afirmações qualitativas de determinismo; ganharam a condição concreta que as torna verificáveis, reordenar a resposta e alterar decisão de outro trabalho.

Segunda passagem: todos os itens passam.

Zero marcadores de clarificação. As três decisões que poderiam gerar pergunta já estavam tomadas e registradas antes desta fase: separação entre autoridade e evidência em ADR-0001, auditoria offline em ADR-0002, e a rejeição do contador de revisão como marca. Foram transcritas como premissas.

Lacuna conhecida e declarada, fora do escopo: um registro obsoleto pode passar na auditoria. É consequência aceita de ADR-0002 e a mitigação é a história 3.
