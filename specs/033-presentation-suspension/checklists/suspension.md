# Suspension Requirements Checklist: Suspensão e reativação da apresentação local no core

**Purpose**: Validar a qualidade dos requisitos da spec 033 antes de tasks: fonte das frases de controle, pré-requisitos sob suspensão, compactação nativa nos dois runtimes, upgrade durante a suspensão e contrato publicado.
**Created**: 2026-09-24
**Feature**: [spec.md](../spec.md)

**Público**: revisor de PR. **Profundidade**: padrão. Itens `[x]` passaram na leitura da spec r2; observações ao fim.

## Requirement Completeness

- [x] CHK001 - A spec define qual fonte pode suspender e reativar, excluindo explicitamente fala do agente, resumo de compactação e mensagem sintética? [Completeness, Spec §FR-001, §FR-003, §FR-004]
- [x] CHK002 - Os pré-requisitos que continuam exigidos sob suspensão (instalação, compatibilidade, habilitação, confiança) estão enumerados? [Completeness, Spec §FR-002, §US1.4]
- [x] CHK003 - O conteúdo mínimo do registro de suspensão está definido (mensagem de origem, sessão, escopo, configuração)? [Completeness, Spec §FR-005, §Key Entities]
- [x] CHK004 - A spec exige que suspensão nunca venha do chamador de um verbo? [Completeness, Spec §FR-006]
- [x] CHK005 - A obrigação de atualizar o contrato publicado está expressa como requisito? [Completeness, Spec §FR-012]
- [x] CHK006 - A exposição do estado de apresentação está exigida em todo ponto que hoje o reporta? [Completeness, Spec §FR-013]
- [x] CHK007 - A obrigação de versão e release está registrada? [Completeness, Spec §Assumptions]

## Requirement Clarity

- [x] CHK008 - A regra de comparação da frase é exata e sem ambiguidade (espaços nas pontas, caixa, texto adicional)? [Clarity, Spec §FR-001]
- [x] CHK009 - "Vale a mais recente" está definido para alternâncias entre as duas frases? [Clarity, Spec §FR-003, §US2.2]
- [x] CHK010 - "Mensagem sintética" e "incarnation" estão definidos? [Clarity, Spec §Key Entities]
- [x] CHK011 - "Leitura integral posterior à reativação" deixa claro que leituras anteriores não contam? [Clarity, Spec §FR-003, §US2.1]
- [x] CHK012 - A configuração identificada pelo registro após um upgrade está dita sem ambiguidade? [Clarity, Spec §FR-005, §FR-007]

## Requirement Consistency

- [x] CHK013 - FR-007 (runtime muda dentro de contexto aberto: recusa) e FR-009 (runtime novo: começa ativo) estão distinguidos sem contradição? [Consistency, Spec §FR-007, §FR-009]
- [x] CHK014 - FR-002 (libera trabalho sob suspensão) é consistente com o contrato de pré-requisitos do bootstrap? [Consistency, Spec §FR-002, §US1.4]
- [x] CHK015 - As decisões dos ADR-0001..0003 aparecem nos requisitos sem divergência? [Consistency, Spec §Input]
- [x] CHK016 - FR-010 (nenhum código muda de significado) é compatível com FR-007 (upgrade suspenso deixa de ser recusado)? [Consistency, Spec §FR-007, §FR-010]

## Acceptance Criteria Quality

- [x] CHK017 - SC-001 mapeia os sete cenários do handoff a cenários de aceite concretos? [Measurability, Spec §SC-001]
- [x] CHK018 - SC-002 e SC-003 são verificáveis sem conhecer a implementação? [Measurability, Spec §SC-002, §SC-003]
- [x] CHK019 - O requisito de formato real dos eventos é verificável (fonte capturada, não derivada do código)? [Measurability, Spec §FR-011]

## Scenario & Edge Case Coverage

- [x] CHK020 - Estão cobertos fluxo primário (suspender), alternativo (reativar), exceção (fonte inválida, pré-requisito ausente) e recuperação (nova sessão)? [Coverage, Spec §US1-§US3, §US2.3]
- [x] CHK021 - A compactação está coberta com e sem suspensão, nos dois runtimes? [Coverage, Spec §US1.2, §US5]
- [x] CHK022 - `start adhd mode` sem suspensão anterior e suspensão antes da primeira leitura estão especificados? [Edge Case, Spec §Edge Cases]
- [x] CHK023 - O caso de worker despachado por coordenador está tratado explicitamente? [Edge Case, Spec §Edge Cases, §Assumptions]

## Non-Functional, Dependencies & Assumptions

- [x] CHK024 - Restrições de stdlib, sem rede e sem processo novo estão registradas? [Non-Functional, Spec §Assumptions, §FR-011]
- [x] CHK025 - A disponibilidade de amostras reais dos dois runtimes está registrada como premissa? [Assumption, Spec §Assumptions]
- [x] CHK026 - O que fica fora (F1, matriz T029) está explícito? [Scope, Spec §Assumptions]

## Observações

- CHK006: FR-013 diz "todo ponto que hoje reporta o estado" sem enumerar os pontos na spec; a enumeração vive em `contracts/presentation-suspension.md` e no R9 do plano. Aceito: é detalhe de COMO, e a spec já foi atestada.
- CHK023: a consequência (coordenador pode suspender worker) está declarada; é aceita por decisão do ADR-0001, não lacuna.
- Nenhum gap exige alterar a spec atestada.
