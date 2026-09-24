# Continuity Requirements Checklist: Continuidade de contexto sem líder vivo

**Purpose**: Validar a qualidade dos requisitos da spec 032 antes de tasks: prova de encerramento, distinção entre recusas, idempotência e concorrência, compatibilidade de pontos de retomada antigos e fronteira com o que foi adiado.
**Created**: 2026-09-19
**Feature**: [spec.md](../spec.md)

**Público**: revisor de PR. **Profundidade**: padrão. Itens `[x]` passaram; os gaps encontrados foram corrigidos na spec antes do fechamento.

## Requirement Completeness

- [x] CHK001 - A spec define o que conta como prova de encerramento do condutor anterior, sem depender de declaração de quem pede? [Completeness, Spec §FR-001]
- [x] CHK002 - Estão definidos os três casos de recusa (condutor ativo, observação inconclusiva, condutor não observável), cada um com código próprio? [Completeness, Spec §FR-002, §US2]
- [x] CHK003 - A spec exige que a recusa diga qual prova faltou? [Completeness, Spec §FR-010]
- [x] CHK004 - O que a tomada NÃO pode alterar está enumerado? [Completeness, Spec §FR-005]
- [x] CHK005 - A obrigação de versão e release está explicitada como requisito de entrega? [Completeness, Spec §FR-012]
- [x] CHK006 - Existe requisito sobre o que o registro de sucessão precisa conter para a auditoria ser possível? [Gap → corrigido, Spec §FR-004, §US1.3]

## Requirement Clarity

- [x] CHK007 - "Comprovadamente encerrado" está amarrado a uma fonte observável, e não a um julgamento do agente? [Clarity, Spec §FR-001, §Assumptions]
- [x] CHK008 - A diferença entre "observação inconclusiva" e "condutor não observável" está clara o bastante para gerar códigos distintos? [Clarity, Spec §FR-002, §US2.2, §US2.3]
- [x] CHK009 - "Prévia" está definida como não escrevendo nada, em todos os caminhos? [Clarity, Spec §FR-003, §FR-007, §US4]
- [x] CHK010 - O critério de idempotência está dito em termos de entrada, e não de tempo? [Clarity, Spec §FR-003, §US1.2]

## Requirement Consistency

- [x] CHK011 - FR-001 (aceitar com prova) e FR-002 (recusar sem prova) cobrem o espaço sem sobreposição nem lacuna? [Consistency]
- [x] CHK012 - A tomada (US1) e a troca preparada (US3) estão descritas como caminhos distintos, sem que um dependa do outro? [Consistency, Spec §US1, §US3]
- [x] CHK013 - O escopo excluído da spec concorda com o handoff e com o backlog adiado? [Consistency, Spec §Assumptions, BL-0001]

## Acceptance Criteria Quality

- [x] CHK014 - Os critérios de sucesso são contáveis e têm linha de base explícita? [Measurability, Spec §SC-001, §SC-003]
- [x] CHK015 - O critério que depende de ambiente live está explicitamente fora do aceite desta entrega? [Measurability, Spec §SC-007]
- [x] CHK016 - "Zero divergências entre prévia e comando efetivo" é verificável sem conhecer a implementação? [Measurability, Spec §SC-004]

## Scenario & Edge Case Coverage

- [x] CHK017 - Estão cobertos o fluxo primário, os três de exceção e o de recuperação por troca preparada? [Coverage, Spec §US1-§US3]
- [x] CHK018 - A concorrência entre duas tomadas simultâneas está especificada? [Coverage, Spec §Edge Cases]
- [x] CHK019 - O caso de atividade de especialista em andamento no work item está tratado? [Edge Case, Spec §Edge Cases]
- [x] CHK020 - O caso de o condutor "ressuscitar" depois da tomada está tratado, ao menos quanto a quem detém autoridade? [Edge Case, Spec §Edge Cases]
- [x] CHK021 - O ponto de retomada já consumido está coberto? [Edge Case, Spec §Edge Cases]

## Non-Functional Requirements

- [x] CHK022 - A compatibilidade com pontos de retomada antigos está declarada como requisito, incluindo a proibição de reescrita? [Non-Functional, Spec §FR-009, §US5.2]
- [x] CHK023 - A validação automatizada está proibida de depender de runtime real, rede ou processo externo? [Non-Functional, Spec §FR-011]

## Dependencies & Assumptions

- [x] CHK024 - A premissa de que o ambiente distingue trabalho vivo de encerrado está declarada e rastreada a evidência? [Assumption, Spec §Assumptions, ADR-0001]
- [x] CHK025 - O que foi adiado (comparar digests reais na retomada) está nomeado na spec, e não só no backlog? [Assumption, Spec §Assumptions, BL-0001]

## Notes

- CHK006 falhou na primeira avaliação: FR-004 exigia registrar a sucessão, mas não dizia o que o registro precisa conter para ser auditável. A spec foi ajustada antes do fechamento desta etapa.
