# Feature Specification: Orquestração, continuidade e escopo dos agentes

**Feature Branch**: `cadugevaerd/feat-new-subagents`

**Created**: 2026-09-13

**Status**: Draft

**Input**: Handoff aprovado [FASE-001 — Orquestração, continuidade e escopo dos agentes](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/handoffs/FASE-001-SPECIFY-HANDOFF.md).

**Work item**: `feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa`; fase `FASE-001`; unidade de entrega `DU-001`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Encerrar agentes sem perder trabalho (Priority: P1)

Como operador, quero limpeza automática dos recursos elegíveis ao fechar uma etapa ou wave e antes de trocar de CLI, preservando trabalho e evidências pendentes.

**Why this priority**: A limpeza atual deixa resíduos após convergência; remover sem verificar elegibilidade poderia perder trabalho.

**Independent Test**: Fechar waves integradas e com falha, inclusive após conclusão da run; conferir separadamente sessões, worktrees, branches e motivos de preservação.

**Acceptance Scenarios**:

1. **Given** resultado persistido pelo líder, recursos de identidade comprovada, trabalho integrado, árvore limpa e nenhuma evidência exclusiva, **When** a etapa ou wave fecha, **Then** sessões, worktrees e branches elegíveis são limpas com resultado verificável.
2. **Given** uma run concluída ou intervalo entre waves elegíveis, **When** a limpeza ocorre, **Then** o estado da run não impede limpar os recursos elegíveis.
3. **Given** worker que falhou com trabalho ou evidência pendente, **When** o líder persiste seu diagnóstico e a etapa fecha, **Then** sua sessão é encerrada, mas trabalho e evidência pendentes são preservados e cada recurso retido consta do checkpoint com motivo.
4. **Given** especialista somente leitura com resultado ou diagnóstico persistido, **When** a etapa fecha, **Then** sua sessão também é encerrada com confirmação registrada.
5. **Given** identidade não comprovada ou tentativa de encerramento sem confirmação, **When** a limpeza é avaliada, **Then** não há remoção baseada em suposição nem declaração falsa de limpeza concluída; a incerteza aparece no diagnóstico.

### User Story 2 - Conceder escrita somente aos arquivos declarados (Priority: P1)

Como líder, quero que cada tarefa declare os arquivos que pode alterar, para impedir permissões acidentais da prosa e omissões de arquivos da raiz.

**Why this priority**: Grants incompletos ou espúrios comprometem execução e controle de escrita.

**Independent Test**: Particionar tarefas com arquivos novos, da raiz e de subdiretórios e referências adicionais na prosa; comparar o grant com a lista declarada.

**Acceptance Scenarios**:

1. **Given** declaração de `.gitignore`, `build-dist.sh`, um arquivo novo e um arquivo em subdiretório, **When** partition produz o grant, **Then** todos e somente os arquivos declarados recebem autorização de escrita.
2. **Given** as variantes `./.gitignore` e `./build-dist.sh`, **When** o grant é formado, **Then** elas identificam os mesmos arquivos da raiz que suas formas sem `./`.
3. **Given** descrição contendo `ACTIVE/FREE` ou referência a arquivo não declarado, **When** a tarefa é processada, **Then** essas referências não concedem escrita.
4. **Given** declaração ausente, inválida ou que tente autorizar escrita fora do escopo permitido, **When** a tarefa é processada, **Then** há diagnóstico e nenhum grant é inferido da prosa.
5. **Given** tarefas antigas ou DAG já selado, **When** o novo contrato é adotado, **Then** as tarefas exigem adaptação explícita e o DAG selado não é reescrito silenciosamente.

### User Story 3 - Retomar o mesmo trabalho em outro CLI (Priority: P1)

Como operador, quero trocar entre Codex e Claude na mesma worktree pelo último checkpoint persistido, preservando resultados aceitos e impedindo execução concorrente.

**Why this priority**: Continuidade exige evitar perda de resultados e duplicação de efeitos.

**Independent Test**: Interromper um trecho após aceitar resultados anteriores, persistir checkpoint, encerrar atividade e retomar no outro CLI; repetir nos dois sentidos.

**Acceptance Scenarios**:

1. **Given** checkpoint coerente e ausência de atividade concorrente, **When** o operador retoma no outro CLI na mesma worktree, **Then** mantém identidade e resultados aceitos, repete somente o trecho interrompido e não duplica efeitos já registrados.
2. **Given** workers ou outro executor ainda ativos, **When** há tentativa de troca, **Then** ela bloqueia com diagnóstico da atividade impeditiva; workers ativos não são transferidos.
3. **Given** checkpoint ausente, contraditório ou insuficiente para distinguir resultado aceito de trecho interrompido, **When** há tentativa de retomada, **Then** ela bloqueia sem usar memória privada da sessão anterior como autoridade.
4. **Given** recursos remanescentes, **When** a troca é preparada, **Then** a limpeza dos elegíveis ocorre antes da troca e os preservados constam do checkpoint; encerramento de sessão não confirmado impede afirmar ausência de concorrência.

### User Story 4 - Receber orientação para o chat principal (Priority: P2)

Como operador, quero recomendação consistente de modelo para coordenação, distinguindo-a da seleção obrigatória de especialistas.

**Why this priority**: Facilita iniciar e retomar sem confundir os papéis do líder e dos especialistas.

**Independent Test**: Iniciar e retomar nos dois CLIs, conferindo recomendação e preservação do modelo ativo.

**Acceptance Scenarios**:

1. **Given** início ou retomada no Codex, **When** a orientação é apresentada, **Then** recomenda Sol para a sessão principal.
2. **Given** início ou retomada no Claude, **When** a orientação é apresentada, **Then** recomenda Opus para a sessão principal.
3. **Given** modelo ativo diferente do recomendado, **When** a recomendação é exibida, **Then** não há troca silenciosa nem relaxamento da política dos especialistas.

### User Story 5 - Planejar com especialistas verificados (Priority: P1)

Como operador, quero que todo julgamento sobre COMO seja feito por especialistas topo de linha, enquanto o líder coordena a etapa canônica e responde pela evidência.

**Why this priority**: A política precisa alcançar também tasks e design frontend, onde ocorrem decisões de implementação.

**Independent Test**: Solicitar elaboração de plano, tarefas e design; verificar autor, modelo e esforço efetivos; repetir com capacidade ausente ou divergente.

**Acceptance Scenarios**:

1. **Given** julgamento sobre COMO no Codex, **When** ele é despachado, **Then** o especialista usa `gpt-6-astra` com esforço `xhigh`, inclusive em plan, tasks e design frontend.
2. **Given** a mesma necessidade no Claude, **When** o julgamento é despachado, **Then** o especialista usa `fable` com esforço `xhigh`.
3. **Given** capacidade ausente ou modelo/esforço efetivos divergentes ou não comprovados, **When** o despacho é preparado, **Then** ele bloqueia com diagnóstico antes do trabalho especializado, sem substituição silenciosa nem julgamento pelo líder.
4. **Given** especialista apto, **When** a elaboração ocorre, **Then** o líder invoca a skill canônica e mantém coordenação, registro e atestação; o especialista não declara resultado da macroetapa nem escreve evidência de coordenação.

### User Story 6 - Revisar com independência em todo o fluxo (Priority: P1)

Como operador, quero especialista distinto do autor para toda revisão que exige julgamento sobre requisitos, planos, tarefas, design, código ou segurança.

**Why this priority**: A independência deve alcançar decisões anteriores à macroetapa review e impedir autoavaliação apresentada como revisão externa.

**Independent Test**: Revisar cada classe de artefato e conferir identidade distinta, modelo e esforço; diferenciar revisão de verificações determinísticas.

**Acceptance Scenarios**:

1. **Given** revisão de julgamento em qualquer etapa, **When** ela é despachada, **Then** o revisor é `gpt-6-astra` no Codex ou `fable` no Claude, com esforço `high`, distinto do autor.
2. **Given** atividade mista de elaboração e revisão, **When** ela é organizada, **Then** elaboração usa autor `xhigh` e revisão usa outro especialista `high`.
3. **Given** revisor ausente ou modelo/esforço efetivos divergentes ou não comprovados, **When** a revisão seria iniciada, **Then** há bloqueio com diagnóstico e nenhum substituto silencioso produz aprovação.
4. **Given** verificação determinística, **When** ela é executada, **Then** continua sendo verificação executável e seu sucesso não é apresentado como revisão de julgamento.

### User Story 7 - Aprovar prévia visual antes das tarefas frontend (Priority: P2)

Como operador de trabalho frontend, quero avaliar uma prévia visual revisável durante plan e aprová-la antes de tasks.

**Why this priority**: Permite avaliar o resultado visual antes de decompor sua implementação em tarefas.

**Independent Test**: Conduzir plan de trabalho frontend com Impeccable; testar entrada em tasks com prévia ausente, pendente, rejeitada e aprovada; comparar com trabalho sem frontend.

**Acceptance Scenarios**:

1. **Given** escopo frontend, **When** plan é executada, **Then** existe subfase de design integrada a Impeccable, com prévia visual revisável, autor especializado `xhigh` e revisão independente `high`.
2. **Given** apenas brief textual ou prévia ausente, pendente, rejeitada ou alterada após aprovação, **When** há tentativa de iniciar tasks, **Then** a transição bloqueia até existir aprovação humana da prévia corrente.
3. **Given** prévia revisada e aprovada pelo operador, **When** os demais pré-requisitos estão satisfeitos, **Then** tasks pode iniciar sem criar macroetapa adicional.
4. **Given** trabalho sem frontend, **When** plan termina, **Then** a ausência de prévia frontend não cria impedimento; a sequência permanece com onze macroetapas.

### Edge Cases

- Repetição de limpeza distingue recurso já ausente de estado desconhecido, sem remover recurso de outra identidade nem inventar sucesso.
- Trabalho integrado com árvore suja, evidência exclusiva ou identidade incerta continua preservado; integração sozinha não autoriza exclusão.
- Falha ao encerrar sessão é diagnosticada separadamente da elegibilidade de worktree ou branch.
- Interrupção entre produção e aceitação de resultado não permite promovê-lo por suposição na retomada.
- Confirmar o nome `fable` não comprova disponibilidade nem esforço efetivo; incapacidade de comprovar impede despacho especializado.
- Aceitar prefixo `./` não autoriza caminhos que escapem do projeto nem escrita de worker em evidência reservada ao líder.
- Tarefa que altera evidência de coordenação continua reservada ao líder, mesmo com arquivos explicitamente declarados.
- Aprovação antiga não cobre prévia visual modificada; é necessária aprovação correspondente à nova prévia antes de tasks.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST executar limpeza automática dos recursos elegíveis ao fechar cada etapa ou wave e antes da troca de CLI, incluindo runs concluídas e intervalos entre waves elegíveis. Aceite: US1.1–2, US3.4.
- **FR-002**: Sessões MUST ser encerradas após o líder persistir resultado ou diagnóstico, incluindo especialistas somente leitura. Aceite: US1.3–4.
- **FR-003**: Worktrees e branches MUST ser removidas somente com identidade comprovada, trabalho integrado, árvore limpa e ausência de evidência exclusiva; workers que falharam MUST conservar trabalho e evidências pendentes. Aceite: US1.1, US1.3, US1.5.
- **FR-004**: O checkpoint MUST identificar cada recurso preservado e seu motivo; encerramentos MUST ter resultado verificável, sem apresentar tentativa não confirmada como limpeza concluída. Aceite: US1.3–5, US3.4.
- **FR-005**: A orientação da sessão principal MUST recomendar Sol no Codex e Opus no Claude em todo início e retomada, distinguindo coordenação de especialistas e sem trocar silenciosamente o modelo ativo. Aceite: US4.1–3.
- **FR-006**: O operador MUST poder retomar o mesmo work item na mesma worktree entre Codex e Claude, nos dois sentidos, pelo último checkpoint persistido coerente, preservando resultados aceitos e repetindo somente o trecho interrompido sem duplicar efeitos. Aceite: US3.1.
- **FR-007**: A troca MUST exigir checkpoint coerente e ausência de trabalho ativo concorrente, sem transferir workers ativos nem depender de transferência de memória privada; incerteza sobre essas condições MUST bloquear com diagnóstico. Aceite: US3.2–4.
- **FR-008**: Trabalho frontend MUST incluir design integrado a Impeccable dentro de plan, com prévia visual revisável; brief textual isolado MUST NOT satisfazer esse resultado. Aceite: US7.1–2.
- **FR-009**: Tasks de trabalho frontend MUST depender de aprovação humana da prévia visual corrente; ausência, rejeição, pendência ou modificação após aprovação MUST bloquear a transição. Aceite: US7.2–3.
- **FR-010**: A integração de design MUST preservar a sequência `specify → plan → checklist → tasks → analyze → partition → implement-parallel → converge → verify → review → ship`, sem nova macroetapa nem exigir prévia em trabalho sem frontend. Aceite: US7.3–4.
- **FR-011**: Todo raciocínio sobre COMO, incluindo plan, tasks e design frontend, MUST ser elaborado por especialista `gpt-6-astra` no Codex ou `fable` no Claude, com esforço `xhigh`. Aceite: US5.1–2.
- **FR-012**: O líder MUST invocar a skill canônica e manter coordenação, registro e atestação, sem substituir julgamento especializado; especialistas MUST NOT declarar resultado de macroetapa nem escrever evidência de coordenação. Aceite: US5.3–4.
- **FR-013**: Toda revisão de julgamento MUST usar especialista topo de linha do respectivo CLI, com esforço `high`, distinto do autor, abrangendo requisitos, planos, tarefas, design, código e segurança em todo o fluxo. Aceite: US6.1.
- **FR-014**: Atividades mistas MUST separar autor `xhigh` de revisor distinto `high`; validadores determinísticos MUST continuar como verificações executáveis, sem substituir revisão de julgamento. Aceite: US6.2, US6.4.
- **FR-015**: Antes de despachar especialistas, o sistema MUST verificar modelo e esforço efetivos contra os solicitados; capacidade ausente, evidência insuficiente ou divergência MUST bloquear com diagnóstico, sem substituição silenciosa. Aceite: US5.3, US6.3.
- **FR-016**: Cada tarefa MUST declarar explicitamente os arquivos que pode alterar; essa lista MUST ser a única autoridade para o grant e aceitar arquivos novos, da raiz e de subdiretórios, inclusive com prefixo `./`. Aceite: US2.1–2.
- **FR-017**: Referências na descrição MUST NOT conceder escrita; declaração ausente ou inválida MUST produzir diagnóstico, sem inferir grant da prosa. Aceite: US2.3–4.
- **FR-018**: A adoção do contrato de arquivos MUST exigir adaptação explícita das tarefas antigas e MUST NOT reescrever silenciosamente DAGs já selados. Aceite: US2.5.
- **FR-019**: A declaração de arquivos MUST preservar ownership e a reserva de evidência de coordenação ao líder, sem autorizar escrita fora do escopo permitido. Aceite: US2.4 e casos de caminhos fora do projeto e evidência reservada.
- **FR-020**: A entrega MUST abranger plugin, core CLI, contratos, integração das skills, documentação e verificações dos sete requisitos, com rastreabilidade ao work item e gates constitucionais de versão e publicação. Registros MUST ser descritos como evidência estrutural auditável, sem alegar prova criptográfica de execução de modelo ou skill. Aceite: auditoria de cobertura dos sete requisitos, distribuição e evidências de verify/review/ship.

### Key Entities *(include if feature involves data)*

- **Recurso de agente**: Sessão, worktree ou branch associada a agente e trabalho, com identidade, elegibilidade, resultado de limpeza ou motivo de preservação.
- **Checkpoint de continuidade**: Registro persistido da identidade, resultados aceitos, trecho interrompido, atividade impeditiva e recursos preservados.
- **Participação especializada**: Papel de autor ou revisor, identidade, modelo/esforço solicitados e efetivos, resultado ou diagnóstico preservado pelo líder.
- **Prévia visual**: Resultado revisável do design frontend, vinculado à revisão e decisão humana de aprovação.
- **Declaração de arquivos**: Lista explícita de arquivos autorizados de uma tarefa, independente das referências na descrição.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em todos os cenários de US1, cada recurso elegível é limpo com confirmação e cada recurso preservado possui motivo; zero trabalho ou evidência pendente é perdido e zero tentativa não confirmada é relatada como sucesso.
- **SC-002**: Em 100% das retomadas válidas testadas nos dois sentidos, identidade e resultados aceitos permanecem os mesmos, com zero efeito aceito duplicado; todas as tentativas com concorrência ou checkpoint incoerente bloqueiam antes de continuar.
- **SC-003**: As quatro combinações de início/retomada e ambiente apresentam a recomendação correspondente, com zero troca silenciosa do modelo ativo.
- **SC-004**: Todos os casos de elaboração sobre COMO e revisão de julgamento têm especialista com papel, modelo e esforço verificáveis; zero revisão é atribuída ao próprio autor e 100% das divergências impedem despacho.
- **SC-005**: Nos cenários frontend, zero entrada em tarefas ocorre sem prévia visual corrente aprovada; trabalhos sem frontend continuam sem esse impedimento e a sequência conserva onze macroetapas.
- **SC-006**: Para todas as tarefas válidas testadas, os arquivos autorizados coincidem exatamente com os declarados; zero referência apenas textual concede escrita, zero declaração inválida gera grant inferido e zero DAG selado é alterado silenciosamente.
- **SC-007**: A auditoria da entrega encontra cobertura verificável dos sete requisitos em comportamento, documentação e verificações, com gates constitucionais satisfeitos antes da publicação.

## Assumptions

- O handoff aprovado é a fonte de escopo. Os sete requisitos pertencem à mesma fase e entrega; prioridades das histórias não autorizam omitir requisitos.
- A troca mantém a mesma worktree. Migrar worktrees, transferir workers ativos e transferir memória privada estão fora do escopo.
- Sol e Opus são recomendações de coordenação. `gpt-6-astra`, `fable`, `xhigh` e `high` são seleções obrigatórias já decididas para especialistas, não sugestões de implementação; disponibilidade real exige verificação e pode bloquear a execução.
- A aprovação visual pertence ao operador; revisão independente do design não substitui aprovação humana.
- Plan definirá mecanismos de encerramento e comprovação de sessões, representação do checkpoint, integração de design e sintaxe da declaração de arquivos. Esta spec fixa resultados e recusas, sem escolher esses mecanismos.
- Evidência de coordenação mantém a reserva existente de `.grill/` e `.specify/reports/` ao líder. O contrato não libera modelos frontier indiscriminadamente para workers de implementação.
- Correções no site ou Terraform, encerramento de recursos reais durante diagnóstico e alterações na Constituição, no workflow ou na ordem canônica estão fora do escopo.
- Esta spec prepara plan e não autoriza pular etapas ou publicar. A entrega continua sujeita a bump SemVer consistente, verify, review e autorização humana para invocar ship, com tag imutável e release pelo pipeline canônico.
