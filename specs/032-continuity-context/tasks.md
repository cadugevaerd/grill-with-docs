---

description: "Task list for 032 — continuidade de contexto sem líder vivo"
---

# Tasks: Continuidade de contexto sem líder vivo

**Input**: Design documents from `/specs/032-continuity-context/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: obrigatórios (FR-011). A recusa atual é total: nem contexto encerrado libera o work item. Sem os casos novos, nada prova que a tomada só acontece com prova, nem que a recusa continua firme sem ela.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos disjuntos, sem dependência pendente)
- **[Story]**: US1..US5 do `spec.md`
- Todo caminho é repo-relativo e explícito, porque o `partition` só fenceia o que a linha nomeia; nenhuma outra palavra das linhas de tarefa contém barra

## Path Conventions

Repositório existente, sem estrutura nova. Arquivos tocados (10): o CLI do core, o contrato do checkpoint, dois validadores, os quatro manifests, o validador de distribuição e os dois headings sob `plugin/`; mais `README.md` e `CHANGELOG.md` na raiz.

**Fronteira conhecida do `partition`**: `README.md` e `CHANGELOG.md` estão na raiz e são infenceáveis para um worker. A fase final os entrega ao **leader**, nomeando um caminho de evidência de coordenador.

---

## Phase 1: Contrato do checkpoint e prova de encerramento

**Purpose**: As duas bases que as demais tarefas consomem. Arquivos disjuntos.

- [X] T001 [P] [US5] Em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, acrescentar a versão seguinte do schema de checkpoint de continuidade ao lado da atual: as mesmas chaves obrigatórias, com `workflow_sha256` renomeada para `context_inputs_sha256` e `constitution_sha256` para `origin_metadata_sha256`; a validação escolhe o conjunto de chaves pelo valor de `schema` no próprio documento, aceita as duas versões e nunca tenta uma e depois a outra; documentar no docstring qual valor cada campo carrega (FR-008, FR-009, ADR-0002, Contract continuity-checkpoint-v2)
- [X] T002 [P] [US1] [US2] Em `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, expor uma observação de encerramento reaproveitando o adapter existente: a partir da resposta de `worker-show` do dispatch anterior, devolver terminal somente quando `dispatch.status` estiver fora de `dispatched` e `running`, ou `capabilityRevokedAt` não for nulo, ou a liveness do host for `exited` com origem `agent_status`; resposta ausente, ilegível, não correlacionada ao dispatch pedido ou com liveness `unverifiable` devolve indeterminado, nunca terminal; não alterar `LeaderBoundary.observe` nem nenhum caminho existente (FR-001, FR-002, Research R1)

**Checkpoint**: `python3 tests/validate_agent_orchestration_contract.py` continua passando sem edição de teste.

---

## Phase 2: Tomada, troca e paridade da prévia

**Purpose**: O verbo novo e as duas correções de caminho existente. Todas no mesmo arquivo, serializadas de propósito.

- [X] T003 [US1] [US2] Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, acrescentar o verbo `gauntlet-context-takeover` com `--work-id`, `--session-ref`, `--expected-sha256` e `--apply`: sem `--apply` executa todas as verificações e devolve `TAKEOVER-PREVIEW` com o hash das entradas relidas, ou a recusa que o apply devolveria, sem escrever byte algum; com `--apply` exige hash coincidente, senão `TAKEOVER-INPUTS-STALE`; recusa `TAKEOVER-LEADER-ACTIVE` quando a observação do dispatch anterior não for terminal por estar vivo, `TAKEOVER-EVIDENCE-UNPROVEN` quando a observação não concluir e `TAKEOVER-NOT-OBSERVABLE` quando o líder registrado não for um dispatch observável; repetição idêntica já aplicada devolve `TAKEOVER-REUSED`; a mutação usa o mesmo compare-and-swap por revisão do store (FR-001, FR-002, FR-003, FR-010, Contract context-takeover, Research R2, R3, R6)
- [X] T004 [US1] Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, gravar a sucessão ao aplicar a tomada: contexto anterior passa a encerrado, contexto novo nasce na época seguinte e carrega o bloco de sucessão com o contexto e a sessão de origem, o motivo, a referência e o digest da observação usada como prova, e o instante; `development`, campanha, resultados aceitos e escopo declarado permanecem byte a byte iguais (FR-004, FR-005, Data model)
- [X] T005 [US3] Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no comando de preparação de troca perto da linha 3300: quando o item não tiver checkpoint corrente conhecido, emitir o checkpoint inicial a partir do estado corrente em vez de recusar com `CONTINUITY-CHECKPOINT-MISSING`; manter a recusa para checkpoint declarado porém desconhecido (FR-006, Research R4)
- [X] T006 [US4] Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no comando de adoção: executar na prévia a mesma verificação de contexto existente que hoje só roda no caminho de aplicação, devolvendo a recusa em vez de prévia quando a aplicação recusaria; a prévia continua sem escrever nada (FR-007, US4)

**Checkpoint**: `python3 tests/validate_agent_orchestration_contract.py` e `python3 tests/validate_orchestrator_store_contract.py` fecham em exit 0.

---

## Phase 3: Cobertura

**Purpose**: Travar comportamento novo e o que não pode regredir. Dois arquivos disjuntos.

- [X] T007 [P] [US1] [US2] [US4] Em `tests/validate_agent_orchestration_contract.py`, acrescentar casos com observação sintética do adapter: dispatch terminal por status, por capacidade revogada e por liveness `exited` liberam a tomada; dispatch vivo recusa com `TAKEOVER-LEADER-ACTIVE`; observação ausente, ilegível, não correlacionada e `unverifiable` recusam com `TAKEOVER-EVIDENCE-UNPROVEN`; líder sem dispatch observável recusa com `TAKEOVER-NOT-OBSERVABLE`; prévia e aplicação concordam no veredito em cada caso; prévia não escreve; hash divergente devolve `TAKEOVER-INPUTS-STALE`; repetição idêntica devolve `TAKEOVER-REUSED`; prévia de adoção diante de contexto de outra sessão devolve a mesma recusa da aplicação; nenhum caso usa runtime real ou rede (FR-001, FR-002, FR-003, FR-007, FR-010, FR-011, SC-002, SC-004)
- [X] T008 [P] [US1] [US3] [US5] Em `tests/validate_orchestrator_store_contract.py`, acrescentar casos de estado: tomada aplicada encerra o contexto anterior, abre a época seguinte e preserva `development`, campanha, resultados aceitos e escopo; o bloco de sucessão contém origem, motivo, prova e instante; duas tomadas concorrentes sobre a mesma revisão terminam com uma aceita e a outra recusada por estado alterado; preparação de troca logo após a criação do work item produz ponto de retomada e a retomada por ele funciona; checkpoint da versão anterior continua legível e utilizável, sem reescrita (FR-004, FR-005, FR-006, FR-009, FR-011, SC-001, SC-003, SC-005)

**Checkpoint**: os dois validadores fecham em exit 0 e nenhum caso existente foi editado para passar.

---

## Phase 4: Distribuição

**Purpose**: Sincronizar a versão. Arquivos disjuntos.

- [X] T009 [P] Atualizar a constante `VERSION` para `6.0.3` em `tests/validate_distribution.py` (FR-012)
- [X] T010 [P] Atualizar a versão para `6.0.3` nos quatro manifests: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json` e `.agents/plugins/marketplace.json` (FR-012)
- [X] T011 [P] Atualizar o heading para `# Grill with Docs v6.0.3` em `plugin/skills/grill-with-docs/SKILL.md` e acrescentar, na seção de identidade e inicialização, uma frase de que a tomada de contexto existe como ato explícito, autorizada por observação de dispatch terminal (FR-012, ADR-0001)
- [X] T012 [P] Atualizar o heading para `# Protocolo de sessão v6.0.3` em `plugin/skills/grill-with-docs/references/session-protocol.md` (FR-012)

**Checkpoint**: `python3 tests/validate_distribution.py` ainda reprova em `README.md` até a fase seguinte.

---

## Phase 5: Fechamento do leader

**Purpose**: Os arquivos da raiz que nenhum worker pode fencear e o registro da conferência.

- [ ] T013 Sincronizar o heading `**v6.0.3` em README.md, abrir a entrada `## 6.0.3` em CHANGELOG.md (tomada de contexto autorizada por observação de dispatch terminal, com recusas distintas para líder vivo, prova inconclusiva e líder não observável; preparação de troca possível desde a criação do work item; prévia de adoção com o mesmo veredito da aplicação; campos do checkpoint renomeados em versão nova, com a anterior ainda legível), e registrar a conferência dos oito pontos de distribuição e o resultado de `python3 tests/run_validators.py` em `.grill/work-items/fix-continuity-context-2babd3080cc84b59a4404d6514f948c2/AUDIT.md` (FR-012, SC-006, quickstart 2 e 3)

**Checkpoint**: os oito pontos concordam; `python3 tests/run_validators.py` fecha em exit 0; `git diff --check` limpo.

---

## Dependencies

```
Phase 1 (T001 ∥ T002)   barreira
        ↓
Phase 2 (T003 → T004 → T005 → T006, serial por arquivo)   barreira
        ↓
Phase 3 (T007 ∥ T008)   barreira
        ↓
Phase 4 (T009 ∥ T010 ∥ T011 ∥ T012)   barreira
        ↓
Phase 5 (T013, leader)
```

- T003 depende de T002 (observação de encerramento) e T004 do estado que T003 aplica.
- T007 e T008 dependem da Phase 2 inteira.
- T001 é independente, mas T008 depende dele para o caso de compatibilidade.

## Parallel opportunities

- Phase 1: T001 e T002 em arquivos disjuntos.
- Phase 3: T007 e T008 em validadores disjuntos.
- Phase 4: as quatro tarefas em arquivos disjuntos.

## Independent test criteria

- **US1**: tomada aceita com dispatch terminal, sucessão registrada, estado preservado (T007, T008).
- **US2**: cada variação sem prova recusa com seu código (T007).
- **US3**: troca preparada logo após a criação e retomada por ela (T008).
- **US4**: prévia e aplicação com o mesmo veredito (T007).
- **US5**: checkpoint novo com nomes corrigidos e checkpoint antigo ainda legível (T001, T008).

## Implementation strategy

MVP = Phase 1 mais Phase 2 mais T007: a tomada existe, é recusada sem prova e a prévia para de mentir. A Phase 3 completa a rede de proteção de estado e a Phase 4 acompanha por obrigação constitucional de bump.

---

## Phase 6: Convergence

- [X] T014 Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, em `_takeover_observation`: ler `dispatch` e `projection` do mesmo nível desembrulhado que o adapter já consome, em vez do nível de topo da resposta crua — hoje `json.loads` devolve o envelope e `show.get` não acha campo algum, então `status` e `liveness` são sempre nulos contra a resposta real, o líder vivo é recusado com o código de prova inconclusiva em vez do código de líder ativo, e a prova gravada na sucessão nasce vazia; manter o retorno nulo para resposta ausente, ilegível ou não correlacionada; e em `tests/validate_agent_orchestration_contract.py`, corrigir o fixture sintético para produzir somente a forma real (envelopada), acrescentando o caso de líder vivo que exige o código de líder ativo e o caso que exige os dois campos de prova preenchidos no registro de sucessão per FR-002, FR-004, FR-010 (contradicts)
- [X] T015 Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, nos dois pontos de emissão de ponto de retomada (o do comando de confirmação de etapa e o da projeção do estado corrente na preparação de troca): emitir a versão nova do formato, com os campos de digest renomeados, em vez da versão anterior; e em `tests/validate_checkpoint_contract.py`, acrescentar o caso que exige a versão nova na emissão, preservando intocado o caso existente que exercita um documento da versão anterior, porque a versão anterior continua legível e utilizável sem reescrita per FR-008, FR-009 (partial)

**Checkpoint**: `python3 tests/validate_agent_orchestration_contract.py`, `python3 tests/validate_checkpoint_contract.py` e `python3 tests/validate_orchestrator_store_contract.py` fecham em exit 0; nenhum caso existente editado para passar.

---

## Phase 7: Convergence

- [X] T016 CRITICAL Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no comando de tomada de contexto: observar a sessão entrante antes de mutar e gravar, no líder do contexto sucessor, a encarnação, a referência e o digest dessa observação, em vez dos nulos de hoje; recusar quando a observação da sessão entrante não concluir; usar a mesma fonte de prontidão de sessão que o comando de retomada já usa, para que a sessão nova passe na verificação de liderança corrente que todo comando autorizado aplica per FR-001, FR-003 (contradicts)
- [X] T017 Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no bloco de mutação da tomada: recusar quando a revisão do documento lido sob o lock diferir da revisão do snapshot em que o veredito foi calculado, exatamente como o comando de retomada já faz, para que quiescência, ponto de retomada corrente e campanha não possam mudar entre a decisão e a escrita per FR-002, FR-003 (contradicts)
- [X] T018 Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no cálculo do hash de entradas relidas da tomada: digerir a decisão, não os bytes crus da resposta do coordenador — trocar a observação inteira pelo veredito, pela referência e pela revisão do snapshot, mantendo o digest da resposta apenas no registro de sucessão, onde ele é prova; sem isso qualquer campo volátil da resposta viva torna a aplicação inalcançável e a recusa por entradas defasadas mente sobre a causa per FR-003, FR-010 (contradicts)
- [X] T019 Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no resultado da tomada aplicada: projetar e devolver os recursos retidos e as operações a reconciliar do contexto encerrado, como o comando de retomada já devolve, porque a verificação de autoridade exige contexto corrente e ativo e o contexto encerrado pela tomada nunca mais aceita o verbo de limpeza per FR-005 (partial)
- [X] T020 [P] Em `tests/validate_orchestrator_store_contract.py`, nos casos de tomada: a prova de comportamento deve exercitar o produto, não a fixture que reimplementa a mutação à mão — os casos existentes passariam com a mutação real inteiramente revertida; manter os casos como aceitação de formato do validador de bloco, deixando isso explícito no nome e no comentário, e mover a prova de comportamento para o caso que invoca o CLI; o caso dito de concorrência não concorre, porque a transação serializa sob lock e quem recusa é a guarda da própria fixture, então ou passa a invocar o CLI duas vezes com o mesmo hash esperado e exige o código real de conflito, ou é renomeado para o que de fato prova e roda sequencial; e o caso do ponto de retomada sintetizado deve usar a versão nova do formato, que é a que o produto emite, em vez da anterior per FR-011, SC-002, SC-004 (partial)
- [X] T021 Em `tests/validate_agent_orchestration_contract.py`: acrescentar o caso que hoje falta e que deixaria passar a falha corrigida em T016 — após aplicar a tomada, executar um comando autorizado como a sessão entrante e exigir que ele seja aceito; asserir também, no contexto sucessor e na operação de sucessão realmente persistidos, a identidade de worktree e a apresentação herdadas do predecessor e os campos de motivo, runtime de destino, prova e instante; e completar o caminho novo da preparação de troca, verificando que o ponto de retomada sintetizado foi gravado, que está na versão nova do formato, que não tem predecessor e que os dois digests conferem com suas fontes per FR-001, FR-004, FR-011 (partial)
- [X] T022 [P] Em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, no comentário que acompanha as constantes de versão do ponto de retomada: dizer o que vale hoje — a versão anterior permanece aceita somente para leitura de documentos já materializados, e a emissão usa a versão nova —, porque o texto atual afirma o contrário e convida a reverter a entrega per FR-008 (contradicts)

**Checkpoint**: `python3 tests/validate_agent_orchestration_contract.py`, `python3 tests/validate_checkpoint_contract.py` e `python3 tests/validate_orchestrator_store_contract.py` fecham em exit 0; nenhum caso existente afrouxado; a suíte completa fecha em exit 0.

---

## Phase 8: Convergence

- [X] T023 CRITICAL Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no comando de tomada de contexto: derivar a identidade viva da árvore com o mesmo helper que o comando de retomada usa, recusar com código próprio quando ela divergir da identidade carimbada no contexto que está sendo encerrado, e gravar no sucessor a identidade derivada em vez da cópia do predecessor; hoje a cópia é cega, e como a identidade inclui a branch, trocar de branch depois que a sessão morre faz o sucessor herdar uma identidade que mente sobre a árvore, o que quebra toda retomada posterior sem que exista verbo de re-carimbo; aceitar o mesmo efeito colateral que a retomada já aceita, de recusar em HEAD destacado per FR-001, FR-005 (contradicts)
- [X] T024 Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no cálculo do hash de entradas relidas da tomada: remover a revisão do snapshot do conjunto digerido; ela é a revisão global do documento, então qualquer escrita de qualquer work item invalida a prévia — inclusive a que o próprio decorador de autorização faz ao refrescar a apresentação —, e a guarda de revisão dentro da mutação já garante o mesmo sob o lock, de forma mais forte e mais precisa per FR-003 (contradicts)
- [X] T025 Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no comando de limpeza de recursos: quando o ramo selecionado não produzir resultado algum, o veredito não pode ser sucesso; hoje a expressão avalia duas buscas sobre lista vazia e cai no caso de sucesso, devolvendo saída zero para uma limpeza que não limpou nada, o que faz o chamador acreditar que recursos ainda abertos foram encerrados per FR-010 (contradicts)
- [X] T026 Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no comentário que acompanha a projeção de recursos retidos e operações a reconciliar dentro da tomada: o texto afirma que eles são entregues ao sucessor para serem reconciliados sob a própria autoridade, e isso é falso — nenhum caminho do core os reconcilia, porque a verificação de autoridade exige contexto corrente e ativo, e o contexto que a tomada encerra deixa de ser ambos; reescrever dizendo que a projeção existe para auditoria e que a reconciliação não está implementada per FR-004 (contradicts)
- [X] T027 Em `tests/validate_agent_orchestration_contract.py`: cobrir as duas correções que hoje passam sem asserção alguma — registrar um recurso e uma operação em estado retido antes de aplicar a tomada e exigir que o resultado os contenha, porque reverter as projeções para vazio passa verde na suíte inteira; e cobrir a recusa por conflito de compare-and-swap da tomada, que hoje só existe citada em comentário, usando o mesmo padrão de substituição da leitura de snapshot que o arquivo já emprega para a recusa equivalente da retomada per FR-011 (partial)
- [X] T028 [P] Em `tests/validate_orchestrator_store_contract.py`: completar o cabeçalho da fixture de tomada com a divergência de tipo que falta — o campo de liveness dentro da prova é uma string na fixture e um mapa com veredito e origem, ou nulo, no produto —, já que o cabeçalho existe justamente para listar essas divergências, e nenhuma validação de bloco confere esse campo per FR-011 (partial)
- [X] T029 Em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py` e `tests/validate_orchestrator_store_contract.py`: mover para o núcleo o emissor do ponto de retomada inicial, recebendo as obrigações de limpeza e os recursos preservados já lidos pela fronteira do CLI, e fazer o contrato do store importar somente o núcleo; hoje o teste importa um helper privado do CLI que toca disco, o que exercita entrada e saída no contrato do store e trava esse helper como interface de facto per FR-011 (partial)

**Checkpoint**: `python3 tests/validate_agent_orchestration_contract.py`, `python3 tests/validate_orchestrator_store_contract.py` e `python3 tests/validate_checkpoint_contract.py` fecham em exit 0; nenhum caso existente afrouxado; a suíte completa fecha em exit 0.
