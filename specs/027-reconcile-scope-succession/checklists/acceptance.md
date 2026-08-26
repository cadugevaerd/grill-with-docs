# Acceptance Checklist: Sucessão explícita de escopo reconciliado

**Purpose**: Validar a **qualidade dos requisitos** desta correção antes de
`analyze` — completude, clareza, consistência, mensurabilidade e cobertura. Não
testa a implementação; testa se o que está escrito é implementável e verificável
sem adivinhação.
**Created**: 2026-08-26
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [contracts/reconcile-scope-authorization.md](../contracts/reconcile-scope-authorization.md)

**Depth**: gate de release (alimenta `analyze` → `verify` → `review` → `ship`)
**Audience**: revisor
**Focus areas**: autorização por dependência direta · casos negativos
fail-closed · invariantes de preview/apply · compatibilidade de recibos ·
sincronização de versão

## Requirement Completeness

- [x] CHK001 Os requisitos definem a autorização para **ambos** os caminhos de reconciliação, sem deixar um deles implícito? [Completeness, Spec §FR-001, §FR-002]
- [x] CHK002 Está especificado o que acontece quando há dependência direta declarada **e** os escopos **não** se sobrepõem? [Coverage, Spec §Edge Cases]
- [x] CHK003 Está especificado o resultado quando os dois trabalhos de um par declaram um ao outro? [Edge Case, Spec §Edge Cases]
- [x] CHK004 Os requisitos declaram o que acontece quando a mesma dependência é declarada em duplicidade? [Edge Case, Spec §Edge Cases]
- [x] CHK005 Está definido o comportamento quando a declaração de dependência não é uma lista de identificadores? [Completeness, Spec §Edge Cases, Contract §C-006]
- [x] CHK006 Os requisitos cobrem o caso em que o escopo preservado é um diretório que **contém** o caminho declarado pelo sucessor? [Coverage, Spec §Edge Cases]
- [x] CHK007 Existe requisito explícito de que nenhum documento de governança é alterado por esta mudança? [Completeness, Spec §Assumptions, Plan §Constitution Check]
- [x] CHK008 Os requisitos nomeiam **todos** os pontos onde a versão precisa concordar, ou deixam a contagem aberta? [Completeness, Spec §FR-011, Research §R-006]

## Requirement Clarity

- [x] CHK009 O termo "dependência direta" está definido de forma que distinga inequivocamente de "dependência transitiva"? [Clarity, Spec §FR-003, ADR-0001]
- [x] CHK010 Está claro **quem** declara a relação — o sucessor, o antecessor, ou qualquer um dos dois — em cada um dos dois caminhos? [Clarity, Spec §FR-001, §FR-002]
- [x] CHK011 "A direção da declaração identifica o sucessor" é uma afirmação verificável, ou depende de interpretação? [Ambiguity, Spec §User Story 1 cenário 2]
- [x] CHK012 O que constitui "sobreposição" entre dois caminhos está definido sem ambiguidade de formato (barra final, prefixo parcial, mesmo caminho)? [Clarity, Data model §Entidades]
- [x] CHK013 "Autorização" está claramente delimitada como permissão de escopo, e não como coordenação de conteúdo entre os trabalhos? [Ambiguity, Spec §Assumptions]
- [x] CHK014 Os requisitos distinguem "dependência ausente do conjunto avaliado" de "dependência ainda não reconciliada", que são recusas diferentes? [Clarity, Contract §C-007]
- [x] CHK015 Está explícito que o incremento de versão parte da base **atual** e não do valor selado no work item? [Clarity, Research §R-006]

## Requirement Consistency

- [x] CHK016 FR-001 (targeted) e FR-002 (full) descrevem a **mesma** regra, sem divergência de condição entre elas? [Consistency, Spec §FR-008]
- [x] CHK017 Os cenários de aceite das User Stories 1 e 2 são mutuamente exclusivos, sem par que satisfaça os dois? [Consistency, Spec §User Story 1, §User Story 2]
- [x] CHK018 O spec e a ADR-0001 concordam sobre transitividade, ou há divergência de redação entre eles? [Consistency, Spec §FR-003, ADR-0001]
- [x] CHK019 Os requisitos do spec e os contratos C-001…C-011 cobrem o mesmo conjunto de casos, sem contrato órfão nem FR sem contrato? [Consistency, Traceability]
- [x] CHK020 A afirmação de que ciclo continua bloqueando é consistente com a de que um par mutuamente declarado tem escopo autorizado? [Conflict, Spec §Edge Cases, Data model §Efeito]

## Acceptance Criteria Quality

- [x] CHK021 SC-002 ("100% das combinações sem dependência direta") enumera quais são essas combinações, ou deixa o conjunto indefinido? [Measurability, Spec §SC-002]
- [x] CHK022 SC-003 ("permanecem inalteradas em relação ao comportamento atual") define contra qual baseline a comparação é feita? [Measurability, Spec §SC-003]
- [x] CHK023 Cada FR tem pelo menos um cenário de aceite ou contrato que o torna objetivamente verificável? [Traceability, Spec §Requirements]
- [x] CHK024 SC-005 ("sem nenhuma divergência") pode ser verificado por um gate existente, ou exige inspeção manual? [Measurability, Spec §SC-005]
- [ ] CHK025 SC-006 ("verificação automatizada completa termina sem falhas") declara o que conta como falha, incluindo o skip dependente de ambiente? [Clarity, Spec §SC-006, Quickstart §1]
- [x] CHK026 FR-012 especifica quais casos negativos são obrigatórios, de modo que a ausência de um deles seja detectável na revisão? [Measurability, Spec §FR-012]

## Scenario Coverage

- [x] CHK027 O fluxo primário (sucessor declarado atravessa) tem requisitos para as duas formas de reconciliação **e** para preview e apply? [Coverage, Spec §User Story 1]
- [x] CHK028 Os fluxos de exceção — ausência, terceiro, transitividade — têm requisito próprio cada um, e não apenas um requisito agregado? [Coverage, Spec §FR-003, §FR-004, §FR-005]
- [x] CHK029 As recusas independentes (self, ciclo, dependência não satisfeita, conflito de decisão) têm requisito de preservação explícito? [Coverage, Spec §FR-006, §FR-007]
- [x] CHK030 Existem requisitos de recuperação para apply interrompido no meio, ou isso está deliberadamente fora de escopo? [Gap, Recovery, Spec §FR-009]
- [x] CHK031 O cenário de reaplicação sobre estado já aplicado tem requisito de resultado definido? [Coverage, Spec §User Story 4 cenário 3, Contract §C-009]

## Non-Functional Requirements

- [x] CHK032 Há requisito de que a mudança não altere a classe de complexidade do laço de sobreposição? [Gap, Plan §Performance Goals]
- [x] CHK033 A restrição de somente-stdlib e Python >=3.10 está declarada como requisito, e não apenas como contexto? [Completeness, Plan §Technical Context]
- [x] CHK034 Há requisito de que os testes não toquem a rede nem exijam ferramentas externas, dado o alcance da matriz de CI? [Completeness, Plan §Target Platform]
- [x] CHK035 A propriedade read-only do preview está expressa como requisito verificável, e não como expectativa? [Measurability, Spec §FR-009, Contract §C-008]

## Dependencies & Assumptions

- [x] CHK036 A premissa de que `depends-on-work` já existe hoje está declarada e é verificável na árvore? [Assumption, Spec §Assumptions]
- [x] CHK037 A premissa de que os recibos já preservam o escopo — e que isso basta, sem campo novo — está validada? [Assumption, Spec §Assumptions, Research §R-004]
- [x] CHK038 A dependência declarada deste work item sobre `feature-workflow-v3-…` está registrada e é coerente com o escopo que ele reutiliza? [Dependency, ADR-0001 §Consequências]
- [x] CHK039 A premissa de que patch é o incremento correto está justificada contra a definição de SemVer usada pelo projeto? [Assumption, Research §R-006]
- [x] CHK040 A decisão de alojar os testes no validador existente está justificada, incluindo a consequência de escopo? [Assumption, Research §R-005, Plan §Structure Decision]

## Ambiguities & Conflicts

- [x] CHK041 Existe algum requisito que possa ser lido como "recibo concluído dispensa escopo", que é exatamente a alternativa rejeitada? [Conflict, ADR-0001 §Alternativas rejeitadas]
- [x] CHK042 Os requisitos deixam claro que a autorização **não** se propaga para `ADR-CONFLICT` em nenhuma circunstância? [Ambiguity, Spec §FR-007, Contract §C-007]
- [x] CHK043 Há requisito que possa ser satisfeito calculando fechamento transitivo sem violar a letra do spec? [Conflict, Spec §FR-003]
- [x] CHK044 O escopo declarado no work item cobre todos os arquivos que os requisitos implicam alterar, sem sobra nem falta? [Traceability, Plan §Project Structure]

## Resultado da avaliação

Avaliada no preflight de `implement-parallel`, contra `spec.md`, `plan.md`,
`research.md`, `data-model.md`, `contracts/` e `analysis.md`.

**43 de 44 aprovados. 1 aberto: CHK025.**

Dezoito itens só passaram por causa das remediações que o `analyze` produziu
(F1 → CHK003, CHK020; F3 → CHK022; F4 → CHK014; F2 → CHK044; F6 → guia de
validação). Antes delas teriam reprovado.

### CHK025 — aberto, dívida declarada

`SC-006` afirma que "a verificação automatizada completa termina sem falhas" sem
definir o que conta como falha, e sem dizer que o skip dependente de ambiente em
`tests/validate_workspace_contract.py` é esperado e não é falha.

Decisão humana no gate `CHECKLIST-INCOMPLETE`, tomada uma vez antes de qualquer
worker existir: **aceitar como dívida declarada**, sem emendar o spec.

Razão: `SC-006` é gate de `verify`, não trabalho construível. A suíte já existe,
o valor esperado é exit `0`, e o skip é conhecido e nomeado em
`quickstart.md §1`. Emendar o spec para formalizá-lo custaria uma cascata de
re-atestação em seis etapas para ganhar precisão de redação em um critério que o
gate já mede sem ambiguidade operacional.

O que fica em aberto é a redação, não a verificação. Rastreado como `F5` em
[`analysis.md`](../analysis.md).

## Notes

- Check items off as completed: `[x]`
- Um item que reprove é entrada para `analyze`, não para implementação direta.
- CHK020 e CHK043 são os dois itens de maior risco: são as formas pelas quais a
  correção poderia virar waiver sem que nenhum teste positivo reprovasse.
- Traceability: 44/44 itens carregam referência ou marcador (100%, acima do
  mínimo de 80%).
