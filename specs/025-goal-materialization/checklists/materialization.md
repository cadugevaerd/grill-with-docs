# Materialization Requirements Quality Checklist: Materialização e validação do goal.md

**Purpose**: Validar a qualidade dos requisitos de materialização no-clobber antes de `tasks` — completude, clareza, consistência, mensurabilidade e cobertura de cenários
**Created**: 2026-08-26
**Feature**: [spec.md](../spec.md)

Estes itens testam **os requisitos escritos**, não a implementação. Cada um
pergunta se algo está especificado, quantificado ou consistente — nunca se algo
funciona.

## Requirement Completeness

- [x] CHK001 Está especificado o caminho exato onde o documento é fixado, sem admitir subdiretório alternativo? [Completeness, Spec §FR-001]
- [x] CHK002 Estão definidos os três estados da fixação por nome, e não apenas descritos em prosa? [Completeness, Spec §FR-003]
- [x] CHK003 Está especificado *quando* o hash é computado — antes ou depois da escrita — de modo a distinguir bytes esperados de bytes materializados? [Completeness, Spec §FR-005]
- [x] CHK004 Estão definidos os requisitos para o caso em que o próprio template embutido no bundle não casa o contrato? [Gap]
- [x] CHK005 Está especificado se o relatório de pré-verificação de ambiente também reporta o documento, ou se isso é deliberadamente fora de escopo? [Gap, Contracts §materialization-cli]
- [x] CHK006 Estão documentados os requisitos para leitura de documento que não decodifica como UTF-8? [Gap, Spec §Edge Cases]
- [x] CHK007 Está especificado onde o caminho e o hash são registrados, distinguindo o registro reportável do selo de identidade imutável? [Completeness, Spec §FR-004]

## Requirement Clarity

- [x] CHK008 O termo "corresponde ao contrato" está definido por uma regra única e citável, ou admite mais de uma leitura? [Clarity, Spec §FR-003]
- [x] CHK009 Está quantificado o que torna um documento "conforme" — presença de partes, ordem, ausência de acréscimos — sem deixar as três dimensões implícitas? [Clarity, Spec §FR-014]
- [x] CHK010 Está claro que o marcador de versão é do contrato do documento e não da versão publicada do plugin, sem que o leitor precise inferir? [Clarity, Spec §FR-011]
- [x] CHK011 A expressão "único lugar" está definida de forma verificável (busca textual sobre quais diretórios?) e não como intenção de design? [Clarity, Spec §FR-009, §SC-006]
- [x] CHK012 Está explícito que "preservado por divergência" não é sucesso, e que o consumidor permanece sem o documento gerenciado? [Ambiguity, Spec §FR-003]
- [x] CHK013 O termo "impedimento de escrita" está delimitado (permissão, disco cheio, caminho ocupado por diretório) ou fica como categoria aberta? [Clarity, Spec §FR-016]

## Requirement Consistency

- [x] CHK014 O vocabulário de estado usado para este documento é consistente com o já usado para os outros artefatos project-wide do mesmo comando? [Consistency, Contracts §materialization-cli]
- [x] CHK015 A regra de conformidade declarada na spec concorda com a declarada no contrato do documento, sem que uma seja mais permissiva que a outra? [Consistency, Contracts §goal-document]
- [x] CHK016 A exigência de não sobrescrever (FR-002) e a de reportar reuso sob concorrência (FR-015) são conciliáveis sem exceção implícita? [Consistency, Spec §FR-002, §FR-015]
- [x] CHK017 A proibição de backup (FR-007) é consistente com a exigência de preservar bytes (FR-006), sem deixar espaço para "preservar copiando"? [Consistency, Spec §FR-006, §FR-007]
- [x] CHK018 As decisões seladas em ADR concordam com os requisitos numerados, sem que um ADR autorize o que um FR proíbe? [Consistency, ADR-0101, ADR-0102]

## Acceptance Criteria Quality

- [x] CHK019 O critério "entrega o documento em 100% das execuções" nomeia a condição sob a qual vale (projeto limpo), evitando ser lido como absoluto? [Measurability, Spec §SC-001]
- [x] CHK020 O critério de bytes inalterados é verificável por comparação objetiva antes/depois, e não por inspeção? [Measurability, Spec §SC-002]
- [x] CHK021 O critério "o conjunto aparece em exatamente um lugar" define o que conta como ocorrência — declaração versus leitura? [Measurability, Spec §SC-006]
- [x] CHK022 O critério de correspondência entre hash registrado e bytes no disco especifica qual dos dois é a fonte da verificação? [Measurability, Spec §SC-004]
- [x] CHK023 O critério de a suíte passar "sem rede e sem ferramenta externa" nomeia as plataformas e versões que a integração cobre? [Measurability, Spec §SC-007]
- [x] CHK024 Cada requisito funcional tem pelo menos um critério de sucesso ou cenário de aceitação que o exercite? [Traceability, Spec §Requirements]

## Scenario Coverage

- [x] CHK025 Estão definidos requisitos para o fluxo primário — projeto limpo recebendo o documento pela primeira vez? [Coverage, Spec §US1]
- [x] CHK026 Estão definidos requisitos para o fluxo alternativo — documento gerenciado já presente e conforme? [Coverage, Spec §US1]
- [x] CHK027 Estão definidos requisitos para o fluxo de exceção — documento homônimo escrito por uma pessoa? [Coverage, Spec §US2]
- [x] CHK028 Estão definidos requisitos para o fluxo de degradação do contrato — documento gerenciado que perdeu uma parte exigida? [Coverage, Spec §US3]
- [x] CHK029 Está especificado se existe caminho de recuperação para o consumidor em estado preservado, ou se a ausência dele é deliberada e declarada? [Gap, Recovery Flow, ADR-0102]
- [x] CHK030 Estão definidos requisitos para o cenário em que o documento é editado depois de fixado, e a deriva precisa ser detectável? [Coverage, Spec §FR-004]

## Edge Case Coverage

- [x] CHK031 Está definido o tratamento de arquivo existente porém vazio, distinguindo-o de arquivo ausente? [Edge Case, Spec §Edge Cases]
- [x] CHK032 Está definido o tratamento de link simbólico no destino, incluindo a exigência de não escrever no alvo apontado? [Edge Case, Spec §FR-008]
- [x] CHK033 Está definido o tratamento de documento conforme com conteúdo adicional após as partes exigidas? [Edge Case, Spec §Edge Cases]
- [x] CHK034 Está definido o tratamento de partes exigidas presentes em ordem diferente da canônica? [Edge Case, Spec §FR-014]
- [x] CHK035 Está definido o desfecho de duas criações concorrentes no mesmo projeto, incluindo qual estado cada uma reporta? [Edge Case, Spec §FR-015]
- [x] CHK036 Está definido o comportamento quando a raiz do projeto não permite escrita, incluindo a exigência de nomear o impedimento? [Edge Case, Spec §FR-016]
- [x] CHK037 Está definido o tratamento de destino ocupado por diretório em vez de arquivo regular? [Gap, Edge Case]
- [x] CHK038 Está definido o efeito de alterar o conjunto exigido sem trocar o marcador, e a consequência sobre documentos já materializados? [Edge Case, Spec §Edge Cases]

## Non-Functional Requirements

- [x] CHK039 Está especificada a restrição de que o teste do contrato roda sem rede e sem ferramenta externa instalada? [Coverage, Spec §FR-013]
- [x] CHK040 Estão especificadas as restrições de portabilidade que a materialização precisa respeitar nas três plataformas cobertas? [Completeness, Spec §SC-007]
- [x] CHK041 Está especificado que a materialização nunca escreve fora da raiz do projeto de destino? [Completeness, Spec §FR-008]
- [x] CHK042 Está especificada a exigência de bump sincronizado como parte da entrega, e não como trabalho posterior? [Completeness, Spec §FR-017]

## Dependencies & Assumptions

- [x] CHK043 Está declarada a suposição de que o texto normativo do documento já foi entregue e não é reaberto nesta feature? [Assumption, Spec §Assumptions]
- [x] CHK044 Está declarada a suposição de que a raiz é gravável no caso normal, com o caso contrário tratado como falha nomeada? [Assumption, Spec §Assumptions]
- [x] CHK045 Está declarada a dependência em relação ao mecanismo de fixação já usado para o outro artefato project-wide, e o que dele é reusado? [Dependency, Spec §Assumptions, ADR-0101]
- [x] CHK046 Está declarado que o conjunto exigido é tratado como congelado, e qual é o caminho legítimo para mudá-lo? [Assumption, Spec §Assumptions]

## Ambiguities & Conflicts

- [x] CHK047 Existe conflito entre "a criação MUST fixar o documento" (FR-001) e "MUST NOT sobrescrever" (FR-002) quando há arquivo homônimo, ou a precedência está explícita? [Conflict, Spec §FR-001, §FR-002]
- [x] CHK048 A frase "corresponde aos bytes efetivamente materializados" (FR-005) exclui sem ambiguidade o hash calculado do conteúdo de origem? [Ambiguity, Spec §FR-005]
- [x] CHK049 A exigência de que "nenhum consumidor redeclare o conjunto" (FR-010) deixa claro se ler-e-copiar em tempo de execução conta como redeclaração? [Ambiguity, Spec §FR-010]
- [x] CHK050 Está estabelecido um esquema de identificação para requisitos e critérios que permita rastrear cada item desta checklist até a sua origem? [Traceability]

## Validation log — analyze, 2026-08-26

Os 50 itens foram avaliados contra `spec.md`, `plan.md`, `tasks.md`, os dois
contratos, `data-model.md`, `research.md`, `quickstart.md` e os ADR-0101/0102 do
work item. Seis itens reprovaram na primeira passada e foram fechados por
emenda dos documentos, não por reinterpretação:

| Item | O que reprovou | Emenda aplicada |
|---|---|---|
| CHK005 | A exclusão do relatório de pré-verificação vivia só no contrato; a spec silenciava. | `spec.md` §Assumptions passou a declarar a exclusão. |
| CHK007 | FR-004 não delimitava o alcance: work item reencontrado não recebe registro, e nada dizia isso. | FR-004 ganhou a delimitação; `data-model.md` §E4 e T016b a tornaram executável. |
| CHK010 | FR-011 exigia o marcador na primeira linha, mas nada verificava a posição onde a conformidade é decidida. | FR-011 passou a exigir a verificação; T006, T025b e o contrato do documento a travam. |
| CHK011 | SC-006 media "o repositório", e o próprio contrato cita a tupla por extenso — critério e teste mediam coisas diferentes. | SC-006 passou a medir a árvore de fontes; o bloco do contrato foi marcado como citação. |
| CHK037 | Destino ocupado por diretório não constava em lugar nenhum. | Acrescentado aos Edge Cases, à tabela de transições, ao contrato do CLI e a T028b. |
| CHK050 | Duas tarefas eram puramente verificatórias, sem produzir evidência própria. | T017 virou invariante com asserção em T031b; T002 permanece precondição do leader. |

Um sétimo achado não é de requisito e por isso não tem item nesta checklist:
T001 mandava escrever dentro de `tasks.md`, que o contrato de execução v4
reserva ao leader. Corrigido na origem — a nota de versão passou para
`CHANGELOG.md`.

## Notes

- Marque `[x]` conforme cada item for validado contra a spec, os ADRs e os contratos.
- Um item que reprove exige **atualização do documento de requisitos**, não da implementação — é o que estes itens medem.
- Itens marcados `[Gap]` apontam ausência suspeita: podem ser exclusão deliberada, e nesse caso a exclusão precisa estar escrita.
- Profundidade: gate formal, porque `checklist` é etapa obrigatória da sequência e antecede `tasks`. Audiência: revisor da etapa `review`.
