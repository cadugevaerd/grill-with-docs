# Feature Specification: Contrato do goal.md

**Feature Branch**: `feature/goal-instruct`

**Created**: 2026-08-22

**Status**: Draft

**Input**: Handoff `FASE-001-SPECIFY-HANDOFF.md` do work item `feature-goal-autopilot-6f0eaefce4064eebb6bc16d5734bee0c`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conduzir a trilha de preparação sem supervisão contínua (Priority: P1)

O operador formula um objetivo a partir do template que o documento fornece e o
entrega ao laço autônomo. O laço cria o item de trabalho, verifica pré-requisitos,
mapeia a governança e avança pela entrevista de decisões. Ao chegar na primeira
pergunta que exige julgamento humano, ele emite a sinalização de parada, com o
motivo em uma frase, e devolve o controle. O operador responde e relança.

**Why this priority**: É a trilha onde nasce todo o trabalho e onde hoje o
operador acompanha turno a turno, inclusive os inteiramente mecânicos. Sem ela, o
documento não elimina atrito nenhum.

**Independent Test**: Pode ser testada isoladamente entregando o objetivo a um
laço autônomo num projeto que ainda não tem item de trabalho, e observando que o
primeiro retorno de controle acontece exatamente numa pergunta material, com
motivo declarado, e não antes nem depois.

**Acceptance Scenarios**:

1. **Given** um projeto sem item de trabalho e o objetivo da trilha de preparação colado no laço, **When** o laço executa, **Then** ele cria o item, reporta o estado dos pré-requisitos e para na primeira pergunta material, emitindo a sinalização de parada como última linha da resposta, com motivo em uma frase.
2. **Given** um laço parado numa pergunta material, **When** o operador responde e relança com o mesmo objetivo, **Then** o laço retoma do ponto registrado sem repetir decisões já seladas e sem recriar o item de trabalho.
3. **Given** a entrevista concluída e a auditoria aprovada, **When** o laço alcança a fronteira que separa preparação de execução, **Then** ele para e entrega o caminho do handoff selecionado, sem atravessar a fronteira por conta própria.

---

### User Story 2 - Conduzir a execução até a autorização final (Priority: P2)

Com a preparação aprovada, o operador entrega ao laço o objetivo da trilha de
execução. O laço percorre a sequência de etapas, invocando a etapa registrada em
cada passo, e para quando alcança a etapa que exige autorização humana explícita
ou quando qualquer etapa devolve bloqueio.

**Why this priority**: É onde está o maior volume de trabalho mecânico e, portanto,
o maior ganho por turno; depende da trilha anterior ter produzido um handoff.

**Independent Test**: Pode ser testada com um handoff pronto, observando que o laço
percorre as etapas em ordem e que o primeiro retorno de controle é a autorização
final ou um bloqueio legítimo, nunca uma etapa pulada.

**Acceptance Scenarios**:

1. **Given** um handoff aprovado e o objetivo da trilha de execução, **When** o laço executa, **Then** ele percorre as etapas na ordem canônica, sem saltos, e para ao alcançar a etapa que exige autorização humana.
2. **Given** uma etapa que devolve bloqueio, **When** o laço a encontra, **Then** ele para imediatamente, nomeia o bloqueio e não tenta produzir o resultado da etapa por outro meio.
3. **Given** uma etapa cuja capacidade registrada está ausente, ambígua ou abaixo do mínimo exigido, **When** o laço tenta avançar, **Then** ele para e reporta, em vez de substituir a etapa por trabalho equivalente.

---

### User Story 3 - Parar diante do que ninguém previu (Priority: P3)

O laço encontra uma situação que não consta em nenhuma lista: evidência que falta,
duas leituras possíveis do mesmo estado, ou um passo cujo efeito não é reversível.
Ele para do mesmo jeito, nomeando o que o impediu de decidir sozinho.

**Why this priority**: Fecha o flanco que transformaria toda situação não prevista
em autorização implícita. É a diferença entre um documento que descreve casos e um
documento que estabelece um contrato.

**Independent Test**: Pode ser testada apresentando ao laço um estado ambíguo que
não corresponde a nenhum ponto enumerado, e verificando que ele para em vez de
escolher uma das leituras.

**Acceptance Scenarios**:

1. **Given** um estado ambíguo fora de qualquer ponto enumerado, **When** o laço o encontra, **Then** ele para, nomeia a ambiguidade e não escolhe uma das leituras possíveis.
2. **Given** uma ação cujo efeito é irreversível e que não consta na lista, **When** o laço a alcança, **Then** ele para antes de executá-la.

---

### User Story 4 - Aproveitar coordenação paralela quando ela existe (Priority: P3)

Havendo um coordenador de agentes disponível, o laço mantém-se como responsável
único pela evidência e distribui trabalho decomponível por subdomínio a
trabalhadores paralelos, em qualquer etapa. Não havendo, ele executa a mesma
etapa sequencialmente, com o mesmo resultado.

**Why this priority**: É ganho de tempo, não de correção. Nenhuma etapa passa a
depender do coordenador.

**Independent Test**: Pode ser testada rodando a mesma etapa duas vezes, uma com o
coordenador disponível e outra sem, e comparando o resultado atestado, que deve ser
equivalente.

**Acceptance Scenarios**:

1. **Given** o coordenador disponível e uma etapa decomponível por subdomínio, **When** o laço a executa, **Then** ele distribui o trabalho a trabalhadores paralelos e monta o resultado atestado da etapa ele mesmo.
2. **Given** o coordenador indisponível, **When** o laço alcança a mesma etapa, **Then** ele a executa sequencialmente, sem parar e sem reduzir o que a etapa entrega.
3. **Given** um trabalhador paralelo em execução, **When** ele conclui, **Then** nenhuma evidência de coordenação foi escrita por ele e nenhum resultado de etapa foi declarado por ele.

---

### Edge Cases

- O laço emite a sinalização de parada e o juiz do laço mesmo assim decide continuar: o orçamento de turnos declarado pelo operador limita quantas continuações são possíveis antes do laço encerrar sozinho.
- A sinalização de parada aparece no meio de uma resposta longa em vez de isolada na última linha: o documento exige a forma isolada exatamente para que esse caso não ocorra por descuido de quem conduz.
- O operador cola um objetivo próprio, sem usar os templates: a parada deixa de estar embutida na formulação julgada, e o documento precisa dizer, em texto, que essa é a condição sem a qual nada garante a parada.
- O mesmo objetivo é relançado depois de o operador responder: o laço precisa distinguir decisão já selada de decisão nova, para não reabrir o que já foi respondido.
- Um runtime de laço não persiste estado entre turnos: o documento não pode assumir persistência, e a retomada precisa apoiar-se apenas no que está gravado no projeto.
- O projeto de destino não tem alguma das capacidades registradas exigidas por uma etapa: o laço para em vez de improvisar o resultado.
- O orçamento de turnos se esgota antes de qualquer sinalização de parada: o laço encerra sem aviso, e o que garante a continuidade é o avanço já registrado no projeto, não o runtime.
- O coordenador de agentes some no meio de uma etapa já distribuída: a sessão condutora termina o restante sozinha, aproveitando o que já foi concluído.
- Dois trabalhadores da mesma etapa devolvem resultados que se contradizem: quem resolve é a sessão condutora, e o que ela não conseguir resolver de forma determinística vira parada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O documento MUST cobrir duas trilhas — preparação e execução — e nomear explicitamente a fronteira que as separa.
- **FR-002**: O documento MUST fornecer um template de objetivo por trilha, e cada template MUST embutir a condição de parada na própria formulação a ser julgada, de modo que alcançar uma parada satisfaça o objetivo em vez de contrariá-lo.
- **FR-003**: O documento MUST declarar que os templates são normativos e que, sem eles, nada garante a parada.
- **FR-004**: O documento MUST definir uma sinalização de parada única, emitida como linha própria e isolada, a última da resposta, acompanhada de um motivo em uma frase.
- **FR-005**: O documento MUST instruir o operador a declarar, na trilha de preparação, um orçamento de no máximo cinco turnos, com três como valor recomendado, em vez de herdar o padrão do runtime. O teto é derivado do comportamento esperado da trilha: ela para na primeira decisão que exige julgamento, o que ocorre tipicamente em um a três turnos; margem maior só multiplica continuações caso a sinalização de parada não seja honrada.
- **FR-006**: O documento MUST enumerar, por trilha, os pontos em que o laço para, e cada ponto enumerado MUST ser rastreável a uma fonte de uma destas cinco classes: cláusula da governança do projeto; seção do contrato de fluxo de trabalho; código de recusa emitido pelo núcleo, citável por string literal; limite declarado no estado do próprio work item; ou regra do protocolo publicada na skill. Restringir as fontes às três primeiras deixaria sem fonte válida pontos que existem de fato — a pergunta material da entrevista e os limites de segurança da entrevista são os casos observados.
- **FR-007**: O documento MUST fechar a enumeração com uma cláusula residual que manda parar também fora da lista sempre que a próxima ação deixar de ser determinística e reversível.
- **FR-008**: O documento MUST tratar a travessia da fronteira entre as trilhas e a autorização da etapa final como paradas obrigatórias e não configuráveis.
- **FR-009**: O documento MUST NOT depender de qualquer recurso exclusivo de um runtime de laço específico, incluindo orçamento próprio, transição de estado persistida ou armazenamento local.
- **FR-010**: O documento MUST descrever a delegação a trabalhadores paralelos como interna à etapa, estabelecendo que a sessão condutora permanece a única responsável pela evidência e a única que declara o resultado de cada etapa.
- **FR-011**: O documento MUST proibir que um trabalhador paralelo declare resultado de etapa ou escreva evidência de coordenação.
- **FR-012**: O documento MUST exigir que cada trabalhador paralelo seja despachado com o par modelo/esforço correspondente à natureza do trabalho, com conferência do que foi efetivamente aplicado e bloqueio do despacho em caso de divergência.
- **FR-013**: O documento MUST registrar a exceção em que o modelo do trabalhador é derivado de um vínculo versionado em vez de escolhido.
- **FR-014**: O documento MUST definir um critério determinístico de disponibilidade do coordenador de agentes e descrever o caminho degradado, sequencial, que vale quando ele não está disponível.
- **FR-015**: O caminho degradado MUST NOT bloquear o laço nem reduzir o que a etapa entrega.
- **FR-016**: O documento MUST citar nominalmente os comandos de orientação já existentes que o laço consulta para descobrir em que ponto do trabalho está.
- **FR-017**: O documento MUST declarar que reproduzir o resultado de uma etapa por meio próprio, em vez de invocar a capacidade registrada, não avança a sequência.
- **FR-018**: O documento MUST instruir o laço a nomear, ao parar, qual ponto enumerado ou qual condição residual motivou a parada.
- **FR-019**: Cada ponto de interação enumerado MUST ter um identificador estável, e a sinalização de parada MUST citá-lo, para que duas execuções que param pelo mesmo motivo sejam comparáveis. Ponto que já corresponde a um código de recusa emitido pelo núcleo MUST usar esse código como identificador; ponto que não tem código próprio MUST receber identificador no formato `HOLD-<TRILHA>-<NN>`, com `<TRILHA>` em `PRE` ou `V4`.
- **FR-020**: O documento MUST instruir o laço a deixar o avanço registrado no projeto antes de encerrar o turno, de modo que o esgotamento do orçamento de turnos — que ocorre sem sinalização — não perca trabalho e a retomada não dependa de estado do runtime.
- **FR-021**: O documento MUST definir o comportamento quando o coordenador de agentes fica indisponível no meio de uma etapa já paralelizada: a sessão condutora assume sequencialmente o trabalho restante, sem parada adicional e sem descartar o que os trabalhadores já concluíram.
- **FR-022**: O documento MUST definir que resultados conflitantes entre trabalhadores da mesma etapa são resolvidos pela sessão condutora, e que um conflito cuja resolução não seja determinística cai na cláusula residual.
- **FR-024**: A ordem das duas trilhas no documento MUST ser fixa — preparação, depois execução — e o documento MUST dizer como o laço determina em qual delas está, a partir do estado gravado no projeto e não da memória do turno.
- **FR-025**: Cada template de objetivo MUST declarar, para cada valor que o operador preenche, de onde esse valor vem.
- **FR-026**: O documento MUST declarar um orçamento de turnos para **cada** trilha, e não apenas para a preparação: a trilha de execução MUST usar teto de no máximo quarenta turnos, derivado de ela ter onze etapas e parar por autorização apenas na última.
- **FR-027**: O documento MUST enumerar o que **não** é ponto de interação, nomeando as classes de avanço que o laço executa sozinho por serem determinísticas e reversíveis, para que a cláusula residual não seja lida como "pare sempre que houver dúvida".
- **FR-028**: "Decomponível por subdomínio" MUST ter critério aplicável sem julgamento: existe partição do trabalho em conjuntos de arquivos disjuntos, e nenhum desses conjuntos escreve evidência de coordenação.
- **FR-029**: "Evidência de coordenação" MUST ser enumerada de forma fechada, por caminho, e "coordenador disponível" MUST ser decidido por saída determinística de comando, nunca por interpretação de texto livre.
- **FR-030**: A resposta que contém a sinalização de parada MUST terminar nela. Texto posterior que anuncie continuação MUST ser tratado como violação do contrato, porque contradiz para o juiz o que a linha afirma.
- **FR-031**: O documento MUST definir o comportamento quando a governança ou o contrato de fluxo de trabalho não estão materializados no projeto de destino: o laço para e nomeia o que falta, em vez de criar qualquer um dos dois.
- **FR-023**: O documento MUST permitir que a decisão de parar seja tomada sem abrir nenhum outro arquivo — esse é o teste de autocontenção, e ele é objetivamente verificável. O documento MUST NOT exceder 400 linhas, teto derivado de ele ser lido íntegro a cada turno do laço.

### Key Entities

- **Trilha**: um dos dois trechos do trabalho que o laço conduz — preparação ou execução —, cada um com seu próprio critério de conclusão e seu próprio conjunto de pontos de parada.
- **Template de objetivo**: a formulação que o operador cola no laço, que descreve o alvo e embute a condição de parada; existe um por trilha.
- **Ponto de interação**: uma condição enumerada, rastreável a uma fonte, em que o laço devolve o controle ao humano.
- **Cláusula residual**: a regra que estende a parada a situações não enumeradas, sempre que a próxima ação deixar de ser determinística e reversível.
- **Sinalização de parada**: a linha isolada, ao fim da resposta, que comunica ao juiz e ao humano que o laço parou, o motivo e o identificador do ponto que a causou.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um operador que nunca leu o documento consegue, lendo-o uma vez, colar um objetivo e conduzir a trilha de preparação até a primeira pergunta material sem intervir em nenhum turno intermediário. Medição: contagem de turnos com intervenção humana no transcript da execução, que deve ser zero até a primeira parada.
- **SC-002**: Em execuções conduzidas pelo documento, 100% das paradas ocorrem em um ponto enumerado ou sob a cláusula residual, e nenhuma decisão de valor é tomada pelo laço sozinho.
- **SC-003**: A travessia da fronteira entre as trilhas e a autorização da etapa final nunca ocorrem sem retorno explícito de controle ao humano, em nenhuma execução.
- **SC-004**: O mesmo documento conduz o trabalho em pelo menos dois runtimes de laço distintos, sem nenhuma alteração de texto. Equivalência é medida por três observáveis: a trilha alcançada, o identificador do ponto que causou a parada e o conjunto de artefatos gravados no projeto.
- **SC-005**: Em execuções com coordenador de agentes indisponível, a etapa entrega o mesmo resultado atestado que entregaria com ele disponível, sem parada adicional. Comparação: o conjunto de arquivos alterados e o resultado registrado da etapa, ignorando ordem de execução e carimbos de tempo.
- **SC-006**: Cada ponto de parada enumerado no documento aponta para a fonte que o justifica, e um revisor consegue confirmar as duas pontas sem sair do repositório.
- **SC-007**: O número de turnos em que o operador precisa intervir cai para o número de decisões que efetivamente exigem julgamento, deixando de incluir turnos puramente mecânicos. Linha de base: a condução manual do mesmo ciclo, em que todo turno exige intervenção.
- **SC-008**: Duas execuções que param pelo mesmo motivo citam o mesmo identificador de ponto, permitindo agrupá-las sem interpretar texto livre.
- **SC-010**: A decisão de parar é tomada lendo apenas o documento, sem abrir nenhum outro arquivo, e o documento cabe em 400 linhas.
- **SC-009**: Um laço encerrado por esgotamento de orçamento, sem sinalização, é retomado do ponto registrado sem repetir trabalho já concluído.

## Assumptions

- O operador conhece o protocolo o suficiente para responder às perguntas materiais quando o laço para; o documento não ensina o protocolo, ele o conduz.
- O runtime de laço reinjeta um prompt de continuação após cada turno e consulta algum juiz para decidir se o objetivo foi satisfeito; nenhuma outra capacidade é assumida.
- O juiz pode errar. O orçamento de turnos declarado pelo operador é o freio, e o documento não promete resolver o caso em que o juiz ignora a sinalização de parada.
- O projeto de destino já tem a governança e o contrato de fluxo de trabalho materializados; o documento pressupõe esse estado, não o cria.
- A materialização do documento no projeto de destino e sua validação automatizada pertencem a fases seguintes e estão fora deste escopo.
- A sessão condutora tem acesso aos comandos de orientação existentes do projeto; nenhum comando novo é assumido.
