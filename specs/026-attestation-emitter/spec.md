# Feature Specification: Emissor da cadeia de atestação

**Feature Branch**: `feature/goal-instruct`

**Created**: 2026-08-24

**Status**: Draft

**Input**: Handoff `FASE-001-SPECIFY-HANDOFF.md` do work item `feature-attestation-emitter-2a51feec6ce84a7fb1b7ebe1b6c1aa25`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Concluir uma etapa sem inventar nada (Priority: P1)

Alguém conduz uma etapa do ciclo, produz o artefato dela e quer registrá-la como
concluída. Hoje o registro é recusado: exige um conjunto de documentos
correlacionados que nada no sistema produz. Passa a existir um caminho que monta
esses documentos a partir do que já é conhecido e do artefato entregue.

**Why this priority**: Sem isso nenhuma etapa de nenhum projeto na versão
corrente pode ser concluída. É o bloqueio inteiro.

**Independent Test**: Conduzir uma etapa, apontar o artefato produzido, pedir a
emissão e verificar que o registro de conclusão passa a ser aceito.

**Acceptance Scenarios**:

1. **Given** uma etapa conduzida e seu artefato no projeto, **When** a emissão é pedida, **Then** os documentos correlacionados são produzidos e o registro de conclusão é aceito.
2. **Given** a emissão concluída, **When** alguém compara o resumo registrado com o arquivo em disco, **Then** eles correspondem.
3. **Given** um artefato alterado depois da emissão, **When** a correlação é verificada, **Then** ela não confere.

---

### User Story 2 - Não atestar isolamento que não houve (Priority: P1)

A etapa de execução paralela protege o trabalho por isolar cada executor e
fechar o conjunto de arquivos que ele pode tocar. Quem conduz o ciclo tenta
registrá-la como se a tivesse executado diretamente, e o sistema recusa.

**Why this priority**: Mesma prioridade da anterior porque é o que separa uma
permissão de uma brecha. Sem essa recusa, o caminho novo vira rota de escape do
isolamento — e o isolamento é a proteção, não a formalidade.

**Independent Test**: Pedir emissão para a etapa de execução paralela declarando
que quem conduz o ciclo a executou, e verificar que é recusado nomeando a
exigência.

**Acceptance Scenarios**:

1. **Given** a etapa de execução paralela, **When** a emissão é pedida como conduzida diretamente, **Then** é recusada nomeando a exigência de executor isolado.
2. **Given** qualquer outra etapa do ciclo, **When** a emissão é pedida da mesma forma, **Then** é aceita.
3. **Given** uma etapa que ninguém classificou, **When** a emissão é pedida, **Then** é recusada nomeando a decisão que falta, em vez de assumir o caso permissivo.

---

### User Story 3 - Saber o que o registro afirma (Priority: P2)

Alguém audita um registro aprovado meses depois e precisa saber o que ele
garante. Encontra a resposta declarada, não inferida: houve artefato, ele foi
lido no momento do registro, e alterá-lo depois quebra a correlação. Não há
afirmação de que a capacidade registrada foi executada.

**Why this priority**: Não bloqueia ninguém hoje, mas uma garantia mal
compreendida é pior que uma garantia ausente — quem confia demais num registro
para de olhar o que ele não cobre.

**Independent Test**: Ler a documentação do mecanismo e verificar que o limite
está declarado em texto, sem eufemismo.

**Acceptance Scenarios**:

1. **Given** a documentação do mecanismo, **When** alguém procura o que o registro prova, **Then** encontra a afirmação e o limite lado a lado.
2. **Given** um registro aprovado, **When** alguém pergunta se ele prova execução da capacidade, **Then** a resposta documentada é não.

---

### Edge Cases

- O artefato declarado não existe: recusa nomeada, nunca registro com resumo vazio.
- O artefato é um link simbólico: a leitura não o segue, e a recusa diz isso.
- O caminho do artefato aponta para fora do projeto: recusado antes de qualquer leitura.
- O caminho está vazio ou só com espaços: recusado antes de qualquer leitura.
- A etapa não consta na tabela de classes: recusa nomeando a decisão ausente.
- Uma versão de ciclo desconhecida é informada: recusa nomeando a versão.
- O artefato muda entre a leitura e o registro: o resumo registrado é o do momento da leitura, e a divergência aparece na verificação seguinte.
- Duas emissões para a mesma etapa: a segunda substitui a primeira apenas se declarar explicitamente o que substitui; caso contrário é recusada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada etapa do ciclo MUST ter, por versão, uma classe de execução declarada: exige executor isolado, ou admite execução por quem conduz o ciclo.
- **FR-002**: A tabela de classes MUST ser literal congelado, nunca derivada da ordem das etapas.
- **FR-003**: Etapa ausente da tabela MUST produzir recusa nomeando a decisão que falta, nunca assumir o caso permissivo.
- **FR-004**: Versão de ciclo desconhecida MUST produzir recusa nomeando a versão.
- **FR-005**: A etapa de execução paralela MUST ser classificada como exigindo executor isolado.
- **FR-006**: A emissão MUST recusar produzir registro de execução direta para etapa que exige executor isolado.
- **FR-007**: Quem conduz o ciclo MUST poder declarar-se executor das etapas que admitem isso, obtendo concessão de execução pelo mesmo mecanismo já usado para executores isolados.
- **FR-008**: Nenhum campo do registro MUST ser preenchido com valor de conveniência; o índice de onda de uma execução por quem conduz o ciclo MUST ser o valor que significa "fora de onda", e esse significado MUST estar declarado.
- **FR-009**: A emissão MUST produzir o conjunto completo de documentos correlacionados que o registro de conclusão exige.
- **FR-010**: A emissão MUST ancorar o registro no resumo criptográfico do artefato declarado.
- **FR-011**: A leitura do artefato MUST usar a fronteira segura já existente no sistema, sem seguir link simbólico, sem caminho absoluto e sem travessia de diretório.
- **FR-012**: O componente que emite MUST NOT fazer leitura de disco própria; ele MUST receber a fronteira de leitura de quem o chama.
- **FR-013**: Artefato ausente, ilegível, com caminho vazio, ou cuja leitura não devolva bytes MUST produzir recusa nomeada.
- **FR-014**: A recusa de emissão MUST ser distinguível, por código próprio, tanto de uma capacidade irresolúvel quanto de uma saída não atestada.
- **FR-015**: A recusa de emissão MUST ser tratável por quem já trata falhas de atestação, sem que uma falha de emissão escape como erro não relacionado.
- **FR-016**: O caminho de emissão MUST ser acessível pela interface de linha de comando do sistema, para que conduzir uma etapa e registrá-la não exija programar contra o núcleo.
- **FR-017**: A documentação do mecanismo MUST declarar o que o registro prova e o que ele não prova, sem eufemismo.
- **FR-018**: A suíte de testes MUST travar a totalidade da tabela de classes, a recusa de etapa não classificada, a recusa para etapa que exige executor isolado, e a detecção de artefato alterado.
- **FR-019**: O teste MUST rodar sem rede e sem exigir ferramenta externa instalada.
- **FR-020**: A versão publicada MUST refletir a mudança em todos os pontos onde a distribuição a exige.

### Key Entities

- **Classe de execução**: a declaração de quem pode executar uma etapa — executor isolado, ou quem conduz o ciclo.
- **Cadeia**: o conjunto de documentos correlacionados que o registro de conclusão exige.
- **Âncora**: o resumo criptográfico do artefato produzido pela etapa, selado no registro.
- **Concessão de execução**: identificador e contador que autorizam alguém a executar, já emitidos hoje para executores isolados.
- **Recusa de emissão**: desfecho nomeado quando a cadeia não pode ser produzida a partir de entradas verdadeiras.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma etapa conduzida e com artefato produzido pode ser registrada como concluída, sem que qualquer campo do registro seja inventado.
- **SC-002**: Toda etapa de toda versão conhecida tem classe declarada — verificável por comparação entre a ordem das etapas e a tabela.
- **SC-003**: A etapa que exige executor isolado é exatamente aquela que despacha executores, em cada versão — verificável por comparação entre as duas tabelas.
- **SC-004**: Tentar registrar execução direta da etapa que exige executor isolado é recusado em 100% das tentativas.
- **SC-005**: Alterar o artefato após a emissão faz a verificação da correlação falhar em 100% dos casos.
- **SC-006**: Artefato ausente, ilegível, com caminho vazio ou leitura inválida produz recusa nomeada, e nunca registro emitido.
- **SC-007**: A suíte completa passa sem rede e sem ferramenta externa nas plataformas e versões de linguagem que a integração cobre.
- **SC-008**: Quem lê a documentação do mecanismo encontra, no mesmo lugar, o que o registro prova e o que ele não prova.

## Assumptions

- A resolução da capacidade registrada para cada etapa já existe no sistema e produz o primeiro documento da cadeia; a emissão o consome em vez de reimplementá-lo.
- A concessão de execução com identificador e contador já é emitida hoje para executores isolados, e o mesmo mecanismo serve para quem conduz o ciclo.
- Proveniência criptográfica, defesa contra executor malicioso e acoplamento ao formato de rastro de qualquer runtime de agente estão fora de escopo — o desenho original da atestação já os declarou assim.
- O sistema é biblioteca padrão da linguagem, sem dependência externa, e a integração não dispõe de runtime de agente.
- A primeira entrega deste mecanismo não pode ser registrada por ele mesmo; a ordem é implementar, depois registrar, e isso é bootstrap declarado, não exceção permanente.
