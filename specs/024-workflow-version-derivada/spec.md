# Feature Specification: Versão de workflow derivada do documento

**Feature Branch**: `fix/audit`

**Created**: 2026-08-22

**Status**: Draft

**Input**: `.grill/work-items/fix-audit-workflow-version-2a9e7a7ba01f42dcb24b3bb83d801b03/handoffs/FASE-001-SPECIFY-HANDOFF.md` (FASE-001, WHAT/WHY)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Repositório que preserva uma declaração anterior (Priority: P1)

Quem cria um work item num repositório que preserva uma declaração de workflow anterior recebe um registro que diz essa versão anterior, e o restante do sistema passa a julgar o work item pela sequência que ele efetivamente declara.

**Why this priority**: É onde o defeito causa veredito errado, não apenas atrito. A projeção de status já foi corrigida para julgar cada work item pela sequência que ele declara; enquanto o registro for um literal congelado, essa correção erra pela outra ponta e o problema reaparece com sinal trocado.

**Independent Test**: Criar um work item num repositório com declaração anterior preservada e verificar qual sequência a projeção de status aplica a ele. Entrega valor sozinha: elimina uma classe inteira de veredito errado.

**Acceptance Scenarios**:

1. **Given** um repositório que preserva uma declaração de workflow anterior, **When** um work item é criado, **Then** o registro declara essa versão anterior, não a corrente.
2. **Given** esse work item, **When** a projeção de status o classifica, **Then** ela usa a sequência da versão declarada.
3. **Given** esse work item, **When** uma etapa exclusiva da versão corrente é solicitada, **Then** a recusa é explícita, em vez de a etapa ser tentada em silêncio.

---

### User Story 2 - Declaração ausente ou ambígua recusada na origem (Priority: P2)

Quem tenta criar um work item num repositório cujo documento de workflow não declara exatamente uma versão gerenciada — nenhuma, ou mais de uma — recebe uma recusa que nomeia o que foi encontrado e o que era esperado, e nenhum work item é criado.

**Why this priority**: Depende da primeira ter estabelecido que o registro é derivado; sem isso não existe momento em que a declaração precise resolver. Ainda assim é valiosa sozinha, porque hoje esse repositório produz um work item que nasce condenado e só descobre o problema na auditoria, longe da causa.

**Independent Test**: Tentar criar um work item sobre um documento sem declaração e sobre outro com duas declarações; conferir a mensagem e conferir que nada foi criado.

**Acceptance Scenarios**:

1. **Given** um documento de workflow sem nenhuma declaração de versão gerenciada, **When** a criação de um work item é tentada, **Then** ela é recusada e nenhum artefato do work item existe depois.
2. **Given** um documento com mais de uma declaração, **When** a criação é tentada, **Then** ela é recusada pelo mesmo motivo e com a mesma clareza.
3. **Given** qualquer uma dessas recusas, **When** a mensagem é lida, **Then** ela nomeia quantas declarações foram encontradas e quais são aceitas.

---

### User Story 3 - Work items já publicados não mudam de veredito (Priority: P1)

Quem audita os work items já existentes obtém exatamente o mesmo veredito de antes da mudança.

**Why this priority**: É restrição de sobrevivência, não melhoria. Uma correção que altere o veredito de trabalho já publicado deixa de ser correção e vira queda de frota, sem prévia e sem caminho de migração — o custo que o próprio projeto já recusou pagar em outras ocasiões.

**Independent Test**: Auditar cada work item existente antes e depois da mudança e comparar os vereditos, que devem ser idênticos.

**Acceptance Scenarios**:

1. **Given** os work items existentes, que registram uma versão anterior sobre um documento corrente, **When** cada um é auditado depois da mudança, **Then** o veredito é idêntico ao de antes.
2. **Given** esses mesmos work items, **When** a mudança é aplicada, **Then** nenhum arquivo deles é reescrito, migrado ou renumerado.

---

### Edge Cases

- O documento declara uma versão gerenciada que o sistema não conhece: a criação é recusada como declaração não aceita, e não tratada como se fosse a corrente.
- O documento declara duas vezes a mesma versão: continua sendo mais de uma declaração e continua sendo recusa, porque a regra é sobre unicidade da declaração, não sobre valores distintos.
- A declaração aparece em texto que não é a declaração do documento — um exemplo citado no corpo, por exemplo: a resolução da criação precisa dar o mesmo resultado que a verificação de marcador já existente dá sobre o mesmo texto, senão as duas voltam a discordar.
- Work item criado antes de o campo de sequência existir: continua sendo classificado pelo que o esquema dele implica, sem exigir migração.
- O documento declara uma versão que o sistema aceita mas para a qual não existe sequência de etapas própria: o campo recebe a versão equivalente, conforme FR-002, justificada pela identidade das sequências. Sem essa equivalência o work item nasceria sem sequência reconhecível, que é pior do que o estado atual.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A criação de um work item MUST resolver, a partir do documento de workflow do repositório, qual versão gerenciada ele declara, e MUST usar essa resolução como origem do campo do registro de estado que declara a sequência de etapas. Isso vale para **toda** forma de criação de registro de estado, incluindo a criação por migração de um bundle anterior: nenhuma delas MAY produzir o campo por outro caminho.
- **FR-002**: Os campos do registro de estado que declaram a versão de workflow e a sequência de etapas correspondente MUST derivar, juntos e da mesma resolução, de FR-001, e MUST permanecer mutuamente coerentes: declarar uma versão e listar a sequência de outra é estado interno contraditório e MUST ser impossível de produzir. A derivação, e MUST NOT receber valor fixo independente do documento. A derivação MUST admitir equivalência declarada entre versões cuja sequência de etapas é idêntica, nos casos em que a versão declarada não possui sequência própria. Toda equivalência assim MUST estar registrada e justificada pela identidade das sequências, e MUST NOT ser introduzida para conveniência de implementação.
- **FR-003**: A criação MUST ser recusada quando o documento não declarar exatamente uma versão gerenciada reconhecida. A recusa MUST ocorrer antes de qualquer escrita em disco atribuível ao work item — o diretório do work item, qualquer área de preparação intermediária e qualquer marca de exclusão mútua. Depois da recusa, o repositório MUST estar indistinguível de antes da tentativa.
- **FR-004**: Existem dois caminhos de recusa, e o requisito vale para o segundo. O gate de compatibilidade preexistente barra documento que não satisfaz a fronteira da versão gerenciada, com o código que já usa hoje; o gate desta feature barra documento compatível que não declara exatamente uma versão aceita. Quando a recusa vem **deste** gate, a mensagem MUST nomear quantas declarações foram encontradas e quais versões são aceitas. Nenhum dos dois caminhos MAY deixar artefato: FR-003 vale para ambos.
- **FR-005**: A resolução estrita usada na criação e a verificação de marcador já existente no auditor MUST concordar — mesma quantidade de declarações reconhecida, mesma versão resolvida, mesma decisão de aceitar ou recusar — sobre cada documento da matriz definida em FR-008, que é o universo em que a concordância é medida.
- **FR-006**: Work items já publicados MUST manter o resultado de auditoria que tinham antes da mudança — tanto o veredito quanto o conjunto de apontamentos que o acompanha, porque manter o veredito e trocar o motivo esconderia uma regressão atrás de um resultado igual. Eles MUST NOT ser reescritos, migrados ou renumerados por ela.
- **FR-007**: A classificação de um work item por qualquer consumidor MUST usar a versão que o próprio work item registra, e não a versão corrente do sistema.
- **FR-008**: A cobertura de teste MUST exercitar declaração ausente, declaração única para cada versão reconhecida, declaração múltipla e declaração não reconhecida, tanto na criação quanto na auditoria, e MUST usar o documento real materializado como insumo, não um texto construído a partir da própria lógica de resolução.
- **FR-009**: A mudança MUST ser acompanhada do incremento de versão exigido para alterações do plugin publicado, com a versão idêntica em todos os pontos que o validador de distribuição fixa.

### Key Entities

- **Documento de workflow**: o artefato project-wide que declara qual contrato de ciclo o repositório cumpre. É a autoridade sobre a versão; tudo mais a descreve.
- **Declaração de versão gerenciada**: a marca que o documento carrega para dizer qual versão ele é. Sua unicidade é o que torna o documento não-ambíguo.
- **Registro de estado do work item**: o arquivo que descreve, entre outras coisas, o documento de workflow vigente na criação — caminho, impressão digital e versão. Caminho e impressão digital já são lidos do artefato; a versão é o campo que ainda não era.
- **Veredito de auditoria**: o resultado que aprova ou reprova um work item. É o observável que precisa permanecer estável para o trabalho já publicado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos work items criados sobre um documento com declaração única declaram a sequência de etapas que o documento efetivamente declara, verificável comparando registro e documento sem nenhuma edição manual.
- **SC-002**: Zero work items criados sobre documento cuja declaração não é a versão ativa do sistema são classificados por uma sequência que o documento deles não declara — hoje esse número é a totalidade deles.
- **SC-003**: Os work items já publicados mantêm veredito idêntico antes e depois da mudança, medido por comparação um a um: nenhuma diferença admitida.
- **SC-004**: 100% das tentativas de criação sobre documento sem declaração única são recusadas sem deixar artefato algum, e cada recusa nomeia o encontrado e o esperado.
- **SC-005**: A resolução da criação e a verificação de marcador do auditor concordam em 100% dos casos da matriz de declarações exercitada — ausente, única por versão reconhecida, múltipla e não reconhecida.
- **SC-006**: A suíte de validadores fecha sem falha, com a matriz de FR-008 coberta a partir do documento real materializado.
- **SC-007**: 100% das equivalências aplicadas na derivação são justificadas por identidade comprovada das sequências de etapas envolvidas; zero equivalências sem essa justificativa.

## Assumptions

- O documento de workflow já está materializado no repositório no momento em que a versão é resolvida; a criação de work item já garante isso hoje.
- O conjunto de versões gerenciadas reconhecidas pelo sistema é o que já está declarado no próprio sistema; esta mudança não o amplia nem o reduz.
- Detectar que um registro ficou obsoleto porque o documento migrou depois da criação está fora de escopo: a verificação mais forte foi avaliada e recusada por derrubar todo o trabalho já publicado, sem prévia e sem caminho de migração.
- Reescrever work items já publicados e alterar as ordens canônicas de qualquer versão de workflow estão fora de escopo.
- A execução permanece na branch dedicada que o work item declara; o hook de criação de branch do ciclo externo foi conscientemente pulado por conflitar com a identidade selada do work item.
- O campo do registro de estado que descreve a **forma** do bloco de workflow está fora de escopo. Ele foi renomeado e redefinido fora deste trabalho, e sob a definição nova não descreve artefato externo algum, o que torna legítimo o literal que carrega. A premissa do requisito que exigia a auditoria aceitar qualquer versão nesse campo deixou de valer, e o requisito foi removido.
- O gate de elegibilidade da camada executável foi corrigido fora deste work item e não faz parte deste escopo.
- Nenhum requisito não-funcional se aplica, e o silêncio sobre eles é deliberado, não omissão: a resolução é uma leitura única de um documento já em memória no momento da criação, fora de qualquer laço, sem alvo de desempenho, memória ou concorrência a declarar. A criação já é serializada por exclusão mútua preexistente, que esta mudança não altera.
