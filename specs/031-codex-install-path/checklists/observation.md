# Observation Requirements Checklist: Observar a instalação Codex do i-have-adhd

**Purpose**: Validar a qualidade dos requisitos da spec 031 antes de tasks: fail-closed, fronteira com a verificação de conteúdo existente, segurança do caminho composto, não regressão Claude e fixture real.
**Created**: 2026-09-19
**Feature**: [spec.md](../spec.md)

**Público**: revisor de PR. **Profundidade**: padrão. Itens marcados `[x]` passaram na avaliação; os gaps encontrados foram corrigidos na spec (sucessora r3) antes do fechamento.

## Requirement Completeness

- [x] CHK001 - Estão especificadas todas as condições cumulativas para reconhecer a instalação no Codex (declarado instalado, identificação completa, cópia existente, conteúdo aprovado)? [Completeness, Spec §FR-001]
- [x] CHK002 - Está definido o resultado para cada condição de FR-001 que falha, sem condição órfã? [Completeness, Spec §FR-002, §US2]
- [x] CHK003 - A regra de localização do cache inclui o diretório de configuração declarado pelo ambiente? [Completeness, Spec §FR-003]
- [x] CHK004 - A obrigação de versão e release está explicitada como requisito de entrega? [Completeness, Spec §FR-008]
- [x] CHK005 - Existe requisito que restrinja os dados de identificação a nomes simples, impedindo que a localização saia do cache? [Gap → corrigido, Spec §FR-009]

## Requirement Clarity

- [x] CHK006 - A fronteira entre "instalação indeterminada" e "conteúdo incompatível" está nomeada sem ambiguidade? [Clarity, Spec §FR-002, §SC-002]
- [x] CHK007 - Está claro que habilitação e confiança não vêm da listagem nativa (eixos separados), e que "instalado e habilitado" na US1 descreve o estado do ambiente, não um requisito sobre a listagem? [Clarity, Spec §US1, contracts/codex-plugin-list.md]
- [x] CHK008 - Está definido o que acontece quando a listagem informa um caminho inválido, e se o caminho composto pode substituí-lo? [Gap → corrigido, Spec §FR-004]
- [x] CHK009 - "Saída real da listagem nativa" está delimitada quanto ao que entra na fixture (entrada do componente, sem entradas de terceiros)? [Clarity, Spec §FR-007, research.md R5]

## Requirement Consistency

- [x] CHK010 - FR-001 (reconhecimento com conteúdo aprovado) e FR-002 (divergência vira incompatível) são consistentes com a verificação de conteúdo única já aplicada ao Claude? [Consistency, Spec §FR-001, §FR-002, research.md R2]
- [x] CHK011 - A precedência de um caminho informado (FR-004) é consistente com o edge case de versão futura do Codex que passe a informar o caminho? [Consistency, Spec §FR-004, §Edge Cases]
- [x] CHK012 - O escopo excluído da spec (demais lacunas do T029, runtime Claude) é consistente com o handoff e o REQUEST do work item? [Consistency, Spec §Assumptions]

## Acceptance Criteria Quality

- [x] CHK013 - SC-001 e SC-002 são mensuráveis por contagem de casos, com linha de base explícita (0% hoje)? [Measurability, Spec §SC-001, §SC-002]
- [x] CHK014 - SC-005 está explicitamente fora do aceite desta entrega, evitando critério dependente de ambiente live? [Measurability, Spec §SC-005]
- [x] CHK015 - SC-003 (zero diferença no Claude) tem base verificável nos casos existentes? [Measurability, Spec §SC-003, §FR-005]

## Scenario & Edge Case Coverage

- [x] CHK016 - Estão cobertos os cenários primário (instalada), exceções (não instalada, cópia ausente, identificação faltante, conteúdo divergente) e o alternativo (caminho informado)? [Coverage, Spec §US1-§US3]
- [x] CHK017 - Estão cobertos entrada duplicada, home não padrão e versão diferente da aprovada? [Edge Case, Spec §Edge Cases]
- [x] CHK018 - A repetição sem mudança (idempotência da observação) está especificada? [Coverage, Spec §US1.2]

## Non-Functional Requirements

- [x] CHK019 - Está proibido processo adicional e rede na decisão, com o comando nativo inalterado? [Non-Functional, Spec §FR-006]
- [x] CHK020 - A validação automatizada está proibida de depender de Codex, Claude, node ou rede reais, em linha com a matriz de CI? [Non-Functional, Spec §FR-007]

## Dependencies & Assumptions

- [x] CHK021 - As premissas sobre a forma da listagem 0.154.0 e o layout do cache estão documentadas e rastreadas até evidência (ADR-0001, laudo)? [Assumption, Spec §Assumptions]
- [x] CHK022 - A dependência de uma mudança futura de layout do Codex está tratada como degradação fail-closed, não como aceite falso? [Assumption, plan.md, ADR-0001 §Consequências]

## Notes

- CHK005 e CHK008 falharam na primeira avaliação e foram corrigidos na spec (FR-009 novo; FR-004 ampliado), com specify sucessor r3.
