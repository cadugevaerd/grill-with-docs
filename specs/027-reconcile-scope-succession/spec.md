# Feature Specification: Sucessão explícita de escopo reconciliado

**Feature Branch**: `fix/reconcile-scope-succession`

**Created**: 2026-08-26

**Status**: Draft

**Input**: User description: ".grill/work-items/fix-reconcile-scope-succession-60acbf5d02f244a48207ce55aa48f245/handoffs/FASE-001-SPECIFY-HANDOFF.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sucessor declarado reutiliza escopo do antecessor (Priority: P1)

O autor de um trabalho novo precisa tocar arquivos que um trabalho anterior já
concluiu e reconciliou. Ele declara, no próprio trabalho, que depende
diretamente daquele trabalho anterior. Ao pedir a reconciliação — tanto a de um
alvo único quanto a que avalia todos os trabalhos juntos — a sobreposição entre
os dois é reconhecida como sucessão legítima e não bloqueia a operação.

**Why this priority**: É o defeito que motiva o trabalho. Sem isso, um recibo
concluído vira ownership perpétuo sobre os caminhos que ele cobriu, e nenhum
trabalho posterior consegue tocá-los por mais honesta que seja a declaração.

**Independent Test**: Reconciliar um trabalho que declara dependência direta de
um trabalho anterior já reconciliado, com escopos sobrepostos, e observar que a
operação não reporta conflito de sobreposição para esse par.

**Acceptance Scenarios**:

1. **Given** um trabalho anterior já reconciliado cujo escopo preservado inclui
   um caminho P, **When** um trabalho posterior que declara dependência direta
   daquele trabalho é reconciliado isoladamente e também declara P,
   **Then** a operação não reporta sobreposição de escopo para esse par.
2. **Given** dois trabalhos avaliados na mesma reconciliação completa, em que um
   deles declara diretamente o outro como dependência, **When** os escopos dos
   dois se sobrepõem, **Then** a operação não reporta sobreposição de escopo
   para esse par, e a direção da declaração identifica qual é o sucessor.
3. **Given** a mesma sobreposição autorizada, **When** a reconciliação é
   aplicada, **Then** o resultado aplicado é idêntico ao que a pré-visualização
   anunciou.

---

### User Story 2 - Sobreposição sem dependência direta continua bloqueada (Priority: P1)

O revisor do recibo global precisa da garantia de que a autorização não virou um
waiver. Dois trabalhos que apenas coincidem em arquivos, sem nenhuma declaração
entre eles, continuam sendo recusados. Uma declaração que aponta para um
terceiro trabalho não serve. Uma relação que só existe por cadeia indireta
também não serve.

**Why this priority**: A proteção contra colisão de trabalhos não relacionados é
o motivo de a verificação existir. Se a autorização vazar para além da
declaração direta, a correção troca um defeito por outro pior e silencioso.

**Independent Test**: Reconciliar, em três execuções separadas, um par sem
qualquer dependência, um par em que a dependência declarada aponta para um
terceiro trabalho, e um par ligado apenas por cadeia indireta; observar que
todas as três continuam bloqueadas por sobreposição de escopo.

**Acceptance Scenarios**:

1. **Given** dois trabalhos com escopos sobrepostos e nenhuma dependência
   declarada entre eles, **When** a reconciliação avalia o par, **Then** a
   sobreposição de escopo é reportada e a operação é recusada.
2. **Given** um trabalho que declara dependência de um terceiro trabalho, e cujo
   escopo se sobrepõe ao de um trabalho que ele não declarou, **When** a
   reconciliação avalia esse par, **Then** a sobreposição de escopo é reportada.
3. **Given** uma cadeia em que A declara B e B declara C, e o escopo de A se
   sobrepõe ao de C sem que A declare C, **When** a reconciliação avalia o par
   A–C, **Then** a sobreposição de escopo é reportada.

---

### User Story 3 - Recusas independentes permanecem intactas (Priority: P2)

O operador de reconciliação precisa que a autorização de escopo não interfira em
nenhuma outra verificação. Dependência que aponta para um trabalho inexistente
ou ainda não reconciliado, trabalho que declara a si mesmo, ciclo de
dependências e conflito declarado com uma decisão registrada continuam com os
mesmos resultados e as mesmas identificações de sempre.

**Why this priority**: Regressão silenciosa em qualquer uma dessas recusas seria
descoberta tarde, já com recibos gravados. A separação entre "escopo autorizado"
e "dependência válida" precisa ser explícita e testada.

**Independent Test**: Executar a reconciliação em cada uma das situações —
dependência ausente, autorreferência, ciclo e conflito de decisão — e comparar
as recusas obtidas com as recusas atuais.

**Acceptance Scenarios**:

1. **Given** um trabalho que declara dependência de um trabalho que não existe
   ou ainda não foi reconciliado, **When** a reconciliação o avalia, **Then** a
   recusa por dependência não satisfeita permanece, mesmo que os escopos se
   sobreponham.
2. **Given** um trabalho que declara a si mesmo como dependência, **When** a
   reconciliação o avalia, **Then** a recusa por autorreferência permanece e não
   autoriza escopo algum.
3. **Given** um ciclo de dependências entre trabalhos, **When** a reconciliação
   os avalia, **Then** a recusa por ciclo permanece.
4. **Given** um trabalho que declara conflito com uma decisão registrada em um
   trabalho já reconciliado, **When** a reconciliação o avalia, **Then** a recusa
   por conflito de decisão permanece, independentemente de haver dependência
   direta declarada entre os dois.

---

### User Story 4 - Recibos existentes continuam válidos (Priority: P2)

O revisor precisa que a correção não force migração. Os recibos gravados antes
da mudança continuam sendo lidos e avaliados sem qualquer conversão, e o formato
gravado depois da mudança continua sendo o mesmo.

**Why this priority**: Uma mudança de formato transformaria uma correção
delimitada em uma migração de frota, com todos os recibos históricos precisando
ser reescritos.

**Independent Test**: Avaliar recibos gravados antes da mudança e confirmar que
são lidos sem conversão e que a avaliação produz o mesmo resultado de antes nos
casos não afetados pela autorização.

**Acceptance Scenarios**:

1. **Given** recibos gravados antes desta mudança, **When** a reconciliação os
   lê, **Then** eles são aceitos sem migração e sem alteração de formato.
2. **Given** a operação em modo de pré-visualização, **When** ela é executada,
   **Then** nada é gravado e o resultado descreve exatamente o que a aplicação
   faria.
3. **Given** a operação aplicada duas vezes sobre o mesmo estado, **When** a
   segunda execução ocorre, **Then** o resultado é o mesmo da primeira e nenhum
   estado parcial é deixado para trás.

---

### Edge Cases

- Um trabalho declara dependência direta de um trabalho anterior, mas os escopos
  não se sobrepõem: nada muda, porque não havia recusa a dispensar.
- Os dois trabalhos de um par declaram dependência direta um do outro. O
  mecanismo de recusa difere por forma de reconciliação, e o requisito é sobre o
  resultado, não sobre um mecanismo único: na reconciliação completa, a recusa
  por ciclo continua valendo; na reconciliação de um alvo único, a declaração
  recíproca é invisível — o registro do trabalho anterior não preserva as
  dependências que ele declarou — e o par é barrado antes, porque o anterior
  teria sido recusado por dependência ainda não reconciliada quando foi a vez
  dele. Em nenhuma das duas formas o par mutuamente declarado é aceito.
- A mesma dependência é declarada mais de uma vez pelo autor: a repetição não
  amplia nem enfraquece a autorização.
- A declaração de dependência não é uma lista de identificadores: a recusa por
  formato inválido permanece e nenhuma autorização é concedida.
- O escopo de um recibo anterior cobre um diretório que contém o caminho
  declarado pelo sucessor: a autorização depende da declaração de dependência,
  não do formato do caminho sobreposto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A reconciliação de um alvo único MUST deixar de recusar por
  sobreposição de escopo quando o alvo declara diretamente, como dependência, o
  trabalho anterior cujo recibo contém o escopo sobreposto.
- **FR-002**: A reconciliação completa MUST deixar de recusar por sobreposição
  de escopo entre dois trabalhos quando pelo menos um dos dois declara
  diretamente o outro como dependência.
- **FR-003**: A autorização MUST ser concedida somente por dependência direta
  declarada; relação obtida por encadeamento de dependências MUST NOT autorizar.
- **FR-004**: Sobreposição entre trabalhos sem dependência declarada entre eles
  MUST continuar sendo recusada.
- **FR-005**: Dependência declarada sobre um trabalho diferente daquele com que
  há sobreposição MUST NOT autorizar essa sobreposição.
- **FR-006**: Autorreferência, ciclo e as duas formas distintas de dependência
  não satisfeita MUST manter cada uma a sua recusa própria e MUST NOT ser
  dispensadas pela autorização de escopo. As duas formas são distintas e não
  intercambiáveis: na reconciliação completa, dependência apontando para um
  trabalho ausente do conjunto avaliado; na reconciliação de um alvo único,
  dependência apontando para um trabalho que ainda não foi reconciliado. Cada
  uma pertence à sua forma de reconciliação e conserva a identificação que já
  emite hoje.
- **FR-007**: Conflito com decisão registrada MUST permanecer independente da
  autorização de escopo e MUST NOT ser dispensado por ela.
- **FR-008**: As duas formas de reconciliação MUST aplicar a mesma regra de
  autorização, sem divergência de comportamento entre elas.
- **FR-009**: A pré-visualização MUST permanecer sem efeitos colaterais, e a
  aplicação MUST preservar a atomicidade e a idempotência do baseline.
- **FR-010**: Recibos gravados antes desta mudança MUST continuar legíveis sem
  migração, e o formato gravado MUST permanecer o mesmo.
- **FR-011**: A versão publicada do produto MUST ser incrementada e MUST
  permanecer idêntica em todos os pontos de distribuição e na documentação que a
  fixa.
- **FR-012**: A verificação automatizada MUST cobrir, com casos negativos
  dedicados, a ausência de dependência, a dependência de terceiro e a relação
  apenas encadeada, de modo que uma simplificação futura que transforme
  dependência em dispensa geral seja reprovada.

### Key Entities

- **Trabalho**: unidade de trabalho com identidade própria, um conjunto
  declarado de caminhos que pretende tocar e uma lista declarada de trabalhos
  dos quais depende diretamente.
- **Recibo de reconciliação**: registro de um trabalho já reconciliado,
  preservando a identidade dele e o conjunto de caminhos que ele cobriu.
- **Sobreposição de escopo**: situação em que um caminho declarado por um
  trabalho e um caminho preservado em outro trabalho ou recibo se referem à
  mesma região da árvore.
- **Autorização de sucessão**: permissão para que uma sobreposição específica
  deixe de ser recusa, concedida exclusivamente pela declaração direta de
  dependência do trabalho posterior sobre o anterior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um trabalho que declara dependência direta de um trabalho anterior
  já reconciliado consegue reconciliar escopo sobreposto na primeira tentativa,
  sem intervenção manual e sem editar recibos históricos.
- **SC-002**: Em 100% das combinações sem dependência direta declarada —
  ausência, terceiro e relação apenas encadeada — a sobreposição continua sendo
  recusada.
- **SC-003**: 100% das recusas por dependência não satisfeita — nas duas formas
  —, autorreferência, ciclo e conflito de decisão permanecem inalteradas em
  relação ao baseline.
- **SC-004**: 100% dos recibos gravados antes da mudança continuam sendo lidos
  sem qualquer passo de conversão.
- **SC-005**: A versão publicada aparece idêntica em todos os pontos de
  distribuição que a fixam, sem nenhuma divergência.
- **SC-006**: A verificação automatizada completa termina sem falhas.

## Assumptions

- **Baseline.** Onde este documento diz "baseline", entenda a árvore em
  `origin/main` na versão 5.2.0, commit `f13c18ea487cdf0fe3ec070861cf799f8f49ceaf`
  — a base sincronizada deste trabalho. É contra ela que "inalterado" é medido.
- A declaração de dependência entre trabalhos já existe hoje como parte da
  identidade declarada de cada trabalho; esta mudança passa a lê-la também na
  decisão sobre escopo, sem criar um campo novo.
- Os recibos já preservam o conjunto de caminhos de cada trabalho reconciliado,
  o que basta para reconhecer a sobreposição sem informação adicional.
- Uma sobreposição autorizada não implica coordenação automática de conteúdo
  entre os dois trabalhos; a autorização é sobre permissão de escopo, e a
  correção de conteúdo continua sendo responsabilidade do autor.
- A mudança é uma correção de comportamento sobre uma base já publicada, e
  portanto exige apenas incremento de correção na versão, não uma versão nova de
  formato.
- Nenhum documento de governança do projeto é alterado por esta mudança.
