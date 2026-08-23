# Contract Requirements Checklist: Versão de workflow derivada do documento

**Purpose**: Unit tests for the requirements themselves — completude, clareza, consistência e mensurabilidade do contrato de versão antes de qualquer implementação
**Created**: 2026-08-22
**Feature**: [spec.md](../spec.md)

**Escopo desta lista**: qualidade do que está escrito em `spec.md`, `plan.md`, `research.md`, `data-model.md` e `contracts/cli.md`. Não valida comportamento — isso é `quickstart.md` e a suíte de validadores.

## Requirement Completeness

- [ ] CHK001 Os requisitos definem o que conta como "artefato do work item" para efeito da recusa antes de qualquer escrita — diretório de staging, lock e entrada em `.grill/` estão todos cobertos ou só o bundle final? [Gap, Spec §FR-004]
- [ ] CHK002 Está especificado se a criação por **migração** de bundle legado está sujeita às mesmas regras da criação nova, ou se "criação de um work item" nomeia apenas uma delas? [Gap, Spec §FR-001, Research §R1]
- [x] CHK003 Existe requisito para o caso de o documento de workflow ser reapontado depois da criação por um ato explícito de rebind, que hoje atualiza a impressão digital e nada mais? [Gap, Research §R2] — **EXCLUÍDO DE ESCOPO** (analyze 2026-08-22): registrado em `docs/adr/ADR-0001.md` do work item. Mesma classe do custo já aceito, não regressão nova — hoje o campo é literal e já não acompanha rebind algum.
- [x] CHK004 Os requisitos definem comportamento de rollback caso a mudança precise ser revertida depois de publicada, dado que bundles novos já terão nascido com o registro derivado? [Gap, Exception Flow] — **EXCLUÍDO DE ESCOPO** (analyze 2026-08-22): registrado em `docs/adr/ADR-0001.md`. A Constituição só exige rollback na trilha de hotfix. Assimetria conhecida documentada: reverter só o reader reprovaria bundles novos, então a reversão é das duas fases juntas.
- [x] CHK005 Está documentado o que acontece quando duas criações concorrem sobre o mesmo repositório e o documento muda entre elas? [Gap, Coverage] — **EXCLUÍDO DE ESCOPO** (analyze 2026-08-22): lock, staging e rename atômico preexistentes cobrem, e esta mudança não os altera.
- [ ] CHK006 Os requisitos nomeiam explicitamente todos os campos que passam a ser derivados, ou apenas descrevem "os dois campos" sem enumerá-los na spec? [Completeness, Spec §FR-002]
- [ ] CHK007 Há requisito declarando que nenhum requisito não-funcional se aplica — desempenho, memória, concorrência — em vez de o silêncio ser interpretado como omissão? [Gap, Non-Functional]

## Requirement Clarity

- [ ] CHK008 O termo "versão gerenciada reconhecida" é definido em algum lugar da spec, ou depende de o leitor conhecer a constante do código? [Clarity, Spec §FR-004]
- [ ] CHK009 "Antes de qualquer artefato do work item ser escrito" é verificável a partir do texto, ou exige inspeção da implementação para saber onde está essa fronteira? [Measurability, Spec §FR-004]
- [ ] CHK010 O conteúdo mínimo da mensagem de recusa está especificado com precisão suficiente para ser testado — quantidade encontrada e conjunto aceito são os dois únicos elementos exigidos? [Clarity, Spec §FR-005]
- [ ] CHK011 "A resolução usada na criação e a verificação usada na auditoria MUST concordar sobre todo documento" delimita "todo documento", ou o universo de teste fica implícito? [Ambiguity, Spec §FR-006]
- [ ] CHK012 "Documento real materializado" está definido de modo a excluir sem margem um texto escrito à mão que por acaso contenha a declaração? [Clarity, Spec §FR-009]
- [ ] CHK013 "Manter o veredito" está definido como o veredito apenas, ou inclui a lista de findings — um bundle pode manter NO-GO e mudar de motivo sem violar o requisito? [Ambiguity, Spec §FR-007]
- [ ] CHK014 A spec quantifica em quantos pontos a versão precisa ser idêntica, ou remete a "todos os pontos que o validador fixa" sem número? [Clarity, Spec §FR-010]

## Requirement Consistency

- [x] CHK015 **FR-002 exige que os dois campos recebam "o valor resolvido em FR-001", mas o mapa de derivação faz um documento `v2` produzir valores diferentes nos dois campos. Os dois textos são conciliáveis como estão?** [Conflict, Spec §FR-002, Data Model §Mapa de derivação, Research §R3] — **RESOLVIDO**: não eram conciliáveis. FR-002 foi emendado para declarar que os dois campos respondem perguntas diferentes e admitir equivalência entre versões de sequência idêntica, exigindo justificativa por identidade comprovada. Edge case correspondente e SC-007 acrescentados.
- [x] CHK016 A equivalência que sustenta esse mapa está registrada na spec, ou existe apenas nos artefatos de design, deixando o requisito normativo sem a exceção que ele precisa admitir? [Consistency, Research §R3] — **RESOLVIDO** junto com CHK015: a exceção agora é normativa, não apenas de design.
- [ ] CHK017 FR-008 exige classificação pela versão que o work item registra; isso é consistente com haver dois campos de versão no registro, ou o requisito precisa dizer qual deles governa a classificação? [Ambiguity, Spec §FR-008]
- [ ] CHK018 Os domínios declarados para os dois campos são consistentes entre `data-model.md` e os requisitos da spec, que não distinguem domínios? [Consistency, Data Model §Entidades]
- [ ] CHK019 O escopo negativo da spec — não alterar ordens canônicas — é consistente com a alternativa que `research.md` registra como preferível tecnicamente e recusa por escopo? [Consistency, Spec §Assumptions, Research §R3]
- [ ] CHK020 A ordem de fases do plano (reader antes de writer) está refletida em algum requisito, ou é decisão de plano sem contraparte normativa que impeça a ordem inversa? [Consistency, Plan §Fases]
- [ ] CHK021 Os requisitos e o contrato de CLI concordam sobre a string do finding de auditoria permanecer inalterada? [Consistency, Contracts §audit]

## Acceptance Criteria Quality

- [ ] CHK022 SC-001 é objetivamente verificável sem inspecionar implementação — a comparação entre registro e documento é observável a partir dos artefatos? [Measurability, Spec §SC-001]
- [ ] CHK023 SC-002 tem linha de base declarada de modo verificável, ou "a totalidade dos criados sobre documento cuja declaração não é a versão fixa" precisa ser contada antes para que a métrica exista? [Measurability, Spec §SC-002]
- [ ] CHK024 SC-003 define o método de comparação um a um com precisão suficiente — o que exatamente é comparado antes e depois? [Clarity, Spec §SC-003]
- [ ] CHK025 SC-005 identifica a matriz de casos sobre a qual os 100% são medidos, ou a matriz vive apenas em `research.md`? [Traceability, Spec §SC-005, Research §R5]
- [ ] CHK026 Todo FR tem pelo menos um SC ou cenário de aceitação que o cubra, sem requisito órfão? [Traceability, Spec §Requirements]
- [ ] CHK027 Os critérios de sucesso permanecem agnósticos de implementação, sem nomear campo, constante ou arquivo? [Measurability, Spec §Success Criteria]

## Scenario Coverage

- [ ] CHK028 Existe requisito para o fluxo primário de cada uma das quatro user stories, sem que nenhuma dependa de outra para ser verificável? [Coverage, Spec §User Scenarios]
- [ ] CHK029 O cenário de exceção — declaração ausente, múltipla ou não reconhecida — tem requisito próprio para cada variante, ou as três estão fundidas num requisito só? [Coverage, Spec §FR-004]
- [ ] CHK030 Existe requisito cobrindo work item criado antes de o segundo campo existir, ou isso aparece apenas como edge case sem contraparte normativa? [Coverage, Spec §Edge Cases]
- [x] CHK031 O cenário de recuperação está endereçado: o que um operador faz depois de uma recusa, além de ler a mensagem? [Gap, Recovery Flow] — **EXCLUÍDO DE ESCOPO** (analyze 2026-08-22): a recuperação é corrigir o documento, e FR-005 já obriga a mensagem a nomear o encontrado e o esperado.

## Edge Case Coverage

- [ ] CHK032 Duas declarações do **mesmo** valor estão explicitamente cobertas como caso distinto de duas declarações diferentes? [Edge Case, Spec §Edge Cases, Research §R5]
- [ ] CHK033 A declaração que aparece em texto ilustrativo do corpo do documento — e não como declaração do documento — tem requisito que force criação e auditoria à mesma leitura? [Edge Case, Spec §Edge Cases]
- [ ] CHK034 Está coberto o caso de o documento de workflow não existir no momento da resolução, ou a spec assume sua presença sem requisito que a garanta? [Assumption, Spec §Assumptions]

## Dependencies & Assumptions

- [ ] CHK035 A suposição de que o documento já está materializado quando a versão é resolvida está validada contra o comportamento atual da criação, e não apenas afirmada? [Assumption, Spec §Assumptions]
- [ ] CHK036 A dependência entre este trabalho e a duplicação da tabela de sequências está documentada como risco, com efeito declarado caso alguém acrescente uma entrada em apenas um dos dois lugares? [Dependency, Research §R8]
- [ ] CHK037 A suposição de que o conjunto de versões aceitas não muda por esta feature está declarada e é verificável no diff? [Assumption, Spec §Assumptions]
- [ ] CHK038 O desvio de processo registrado — hook de branch pulado por conflito com a identidade selada do work item — está documentado onde uma revisão futura o encontre? [Assumption, Spec §Assumptions]

## Notes

- Marque com `[x]` conforme cada item for resolvido; anote a resolução inline.
- **CHK015 e CHK016 resolvidos na emenda de FR-002** (2026-08-22), antes de `tasks`. Era contradição real: uma implementação fiel a `FR-002` e outra fiel a `data-model.md` divergiam no caso `v2`. Os 36 itens restantes seguem abertos para `analyze`.
- CHK003, CHK004, CHK005 e CHK031 eram ausências reais de requisito. Foram decididas no `analyze` e excluídas de escopo com justificativa — nenhuma por silêncio. CHK001 segue aberto: T027 o cobre parcialmente, mas a spec não define a fronteira do "antes de qualquer escrita".
- Traceability: 37 dos 38 itens carregam referência a seção, marcador `[Gap]`/`[Conflict]`/`[Assumption]` ou ambos.
