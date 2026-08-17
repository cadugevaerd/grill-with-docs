# Bridge Requirements Quality Checklist: Destravar a ponte com o backlog operacional

**Purpose**: Validar a qualidade dos requisitos da FASE-001 antes da implementação — completude, clareza, consistência e mensurabilidade do que está escrito, não o comportamento do código
**Created**: 2026-08-17
**Feature**: [spec.md](../spec.md)

**Parâmetros aplicados**: profundidade padrão; audiência revisor de PR; foco nas duas áreas de maior risco, que são reconciliação de estado e integridade sob falha parcial. Perguntas de clarificação foram substituídas por defaults, porque a sessão corre sob diretiva de não pausar.

## Requirement Completeness

- [ ] CHK001 A origem do valor de `criticality` está especificada, dado que o template de decisão adiada não tem esse campo? [Gap, Spec §FR-004]
- [ ] CHK002 Existe requisito para o caso de um item vinculado ter sido apagado à mão do backlog entre duas execuções? [Completeness, Spec §Edge Cases]
- [ ] CHK003 Existe requisito para o caso de os marcadores de vínculo terem sido removidos ou corrompidos na descrição de um item existente? [Gap]
- [ ] CHK004 A ordenação da lista de desfechos relatada por execução está especificada, ou é livre? [Gap, Spec §FR-010]
- [ ] CHK005 Está especificado o que acontece com uma decisão cujo bloco existe mas não declara `state`? [Gap, Spec §Key Entities]
- [ ] CHK006 As obrigações de release decorrentes de tocar o plugin estão refletidas em algum requisito verificável, ou vivem apenas no plano? [Traceability, Gap]

## Requirement Clarity

- [ ] CHK007 "Respeitando as transições que o backlog admite" é preciso o bastante, ou depende de conhecimento externo não citado na spec? [Ambiguity, Spec §FR-005]
- [ ] CHK008 O mapa exato entre estado de decisão e estado de item é recuperável a partir da spec, ou só do ADR referenciado nas premissas? [Clarity, Spec §Assumptions]
- [ ] CHK009 "Sem passar por estados intermediários que não ocorreram" é objetivamente verificável a partir do texto? [Measurability, Spec §FR-004]
- [ ] CHK010 "De forma nomeada" está definido com critério observável para as recusas? [Clarity, Spec §FR-002, §FR-009]
- [ ] CHK011 A expressão "interface pública" do backlog está delimitada o suficiente para excluir acesso direto ao armazenamento sem ambiguidade? [Clarity, Spec §FR-011]

## Requirement Consistency

- [x] CHK012 **FR-010 enumera três desfechos — criada, já existente, proposta — enquanto o modelo de dados define quatro, incluindo o de estado reconciliado. Os dois documentos estão em conflito.** [Conflict, Spec §FR-010 vs data-model.md §Desfecho]
- [ ] CHK013 O requisito de espelhar decisão em qualquer estado é consistente com o requisito de criar item no estado correspondente, sem lacuna para estados não previstos? [Consistency, Spec §FR-003, §FR-004]
- [ ] CHK014 A premissa de que decisão resolvida e substituída são terminais é consistente com o requisito de reconciliar estado entre execuções? [Consistency, Spec §Assumptions vs §Edge Cases]
- [ ] CHK015 A chave de unicidade em FR-006 é consistente com o cenário de dois work items compartilhando identificador local de decisão? [Consistency, Spec §FR-006, §User Story 3]

## Acceptance Criteria Quality

- [ ] CHK016 SC-002 fixa a métrica no acervo atual, de 1 para 8 registros; o critério continua verificável quando o acervo mudar? [Measurability, Spec §SC-002]
- [x] CHK017 **SC-006 afirma que nenhuma recusa deixa o backlog parcialmente alterado, mas não existe transação entre criação de itens sucessivos. O critério é alcançável como escrito, ou precisa ser reformulado para falha após a primeira mutação?** [Conflict, Spec §SC-006 vs contracts §Idempotência]
- [ ] CHK018 SC-004 exige identificar origem "sem ambiguidade"; existe critério objetivo para essa verificação? [Measurability, Spec §SC-004]
- [ ] CHK019 Todos os requisitos funcionais têm critério de aceite correspondente, ou algum fica sem verificação declarada? [Traceability, Spec §Requirements vs §Success Criteria]

## Scenario Coverage

- [ ] CHK020 Requisitos de fluxo primário, criação e reconciliação, estão completos para as três histórias? [Coverage, Spec §User Stories]
- [ ] CHK021 Requisitos de fluxo de exceção estão definidos para cada modo de indisponibilidade do backlog, distinguindo binário ausente de resposta fora do contrato? [Coverage, Spec §Edge Cases]
- [x] CHK022 **Requisitos de recuperação estão definidos para falha ocorrida depois da primeira mutação e antes da última?** [Gap, Exception Flow, Spec §Edge Cases]
- [x] CHK023 Existe requisito para transição desejada que seja ilegal na máquina de estados, por exemplo item já concluído cuja decisão volta a aberta? [Gap, Recovery]
- [ ] CHK024 O cenário de work item sem nenhuma decisão registrada tem requisito explícito de não mutação? [Coverage, Spec §Edge Cases]

## Edge Case Coverage

- [ ] CHK025 Está especificado o comportamento quando o mesmo identificador de decisão aparece duas vezes no mesmo work item? [Gap]
- [ ] CHK026 Está especificado o limite de tamanho ou caractere aceito no título e na descrição enviados ao backlog? [Gap]
- [ ] CHK027 Estão cobertos os casos de encoding e de conteúdo multilinha na descrição, que carrega os marcadores de vínculo? [Coverage, data-model.md §Vínculo]

## Dependencies & Assumptions

- [ ] CHK028 A premissa de que o repositório já está vinculado está declarada como pré-condição verificável, e não apenas como texto? [Assumption, Spec §Assumptions, §FR-009]
- [ ] CHK029 A dependência do contrato de versão do backlog está documentada com o comportamento esperado quando essa versão mudar? [Dependency, Gap]
- [ ] CHK030 A premissa de que o ambiente de verificação nunca terá o binário real está registrada como restrição permanente e não como conveniência? [Assumption, Spec §Assumptions, §FR-012]

## Notes

Três itens exigem decisão antes de implementar, e dois deles são defeitos reais na própria documentação:

- **CHK012** é conflito confirmado entre `spec.md` §FR-010 e `data-model.md`. Um dos dois está errado; a spec precisa ganhar o quarto desfecho, ou o modelo precisa perdê-lo.
- **CHK017** é conflito entre um critério de sucesso absoluto e a ausência de transação. Não há como garantir zero mutação parcial criando N itens em chamadas sucessivas sem compensação; o critério precisa ser reescrito para o que é de fato alcançável.
- **CHK022** e **CHK023** apontam a mesma lacuna por ângulos diferentes: o que fazer quando a reconciliação encontra um estado de onde não há transição legal.

Os demais itens são de completude e clareza, e podem ser resolvidos no `analyze` ou aceitos como fora de escopo com registro explícito.

## Resolução aplicada nesta iteração

- **CHK012 resolvido**: `spec.md` §FR-010 passou a enumerar os cinco desfechos, alinhando-se ao modelo de dados.
- **CHK017 resolvido**: SC-006 foi reescrito para o que é alcançável — recusa de pré-condição antes da primeira mutação — e SC-007 foi acrescentado para cobrir convergência após interrupção. O contrato agora declara explicitamente que a garantia é de convergência, não de atomicidade.
- **CHK022 e CHK023 resolvidos**: FR-013 e FR-014 acrescentados, mais três casos de borda. Transição inalcançável vira `TRANSITION-REFUSED`, sem tocar o item e sem usar o reparo administrativo do backlog.

Itens restantes não bloqueiam a implementação e seguem para `analyze`.
