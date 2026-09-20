# Converge Report — 032 continuidade de contexto sem líder vivo

**Data**: 2026-09-19 · **Entradas**: spec.md, plan.md, tasks.md (T001–T013), `.specify/memory/constitution.md` (11 cláusulas) · **Desfecho**: `tasks_appended` (Phase 6, T014–T015)

## Contexto

`implement-parallel` fechou com T001–T013 pela run `run-27d4a4df4c0ec78046f8c430` (4 waves, 8 workers, fase 5 do leader) e `python3 tests/run_validators.py` em exit 0. As duas lacunas trazidas do `AUDIT.md` foram confirmadas no código; nenhuma outra apareceu.

## Findings

| ID | Gap Type | Severidade | Origem | Evidência | Trabalho restante |
|----|----------|------------|--------|-----------|-------------------|
| F1 | contradicts | HIGH | FR-002, FR-004, FR-010 | `_takeover_observation` (`plugin/skills/grill-with-docs/scripts/grill_workspace.py:1526`) faz `json.loads(raw)` e lê `show.get("dispatch")`/`show.get("projection")` no nível de topo; o transporte devolve `{ok, result}`, que é o que `_object` exige e desembrulha antes de `observe_predecessor_termination` ler os mesmos campos | T014 |
| F2 | partial | HIGH | FR-008 | `CHECKPOINT_SCHEMA_V2` e o par `context_inputs_sha256`/`origin_metadata_sha256` existem, e a validação escolhe as chaves pelo `schema` do documento (`grill_core/agent_orchestration.py:680-681`), mas os dois pontos de emissão (`grill_workspace.py:1869` e `:3354`) gravam `CHECKPOINT_SCHEMA` (v1) com os nomes antigos | T015 |

Nenhum achado CRITICAL. Nada `missing`. Nada `unrequested`.

### F1 em detalhe

Contra a resposta real do adapter, `status` e `liveness` saem sempre `None` de `_takeover_observation`. Duas consequências:

1. **Código de recusa errado para líder vivo.** Em `:3663-3666` o ramo `status in {"dispatched", "running"}` nunca dispara, então um líder ainda ativo é recusado como `TAKEOVER-EVIDENCE-UNPROVEN` em vez de `TAKEOVER-LEADER-ACTIVE`. Fail-closed está preservado — a tomada continua recusada —, mas FR-002 exige um código próprio e distinto por caso, e FR-010 exige dizer qual prova faltou.
2. **Prova vazia no registro de sucessão.** `evidence.dispatch_status` e `evidence.liveness` (`:3684`) nascem `None`, degradando exatamente o que FR-004 manda gravar.

Os testes de T007 passaram porque o fixture `takeover_show()` espelha **as duas** formas de propósito, documentando a inconsistência em vez de reprová-la — a correção em T007 estava fora do grant do worker. É o padrão conhecido de fixture mais permissiva que a realidade: o caso sintético cobre um formato que o mundo não produz.

### F2 em detalhe

FR-008 pede que os campos de digest tenham nomes correspondentes ao conteúdo **e** que a mudança venha em versão nova do formato. A metade de leitura está pronta e travada por teste; a metade de escrita não migrou, então todo ponto de retomada novo continua nascendo com `workflow_sha256`/`constitution_sha256`. FR-009 e SC-005 seguem satisfeitos de qualquer modo: a versão anterior continua legível e utilizável sem reescrita, e assim deve permanecer depois de T015.

## Cobertura verificada

| Item | Situação |
|---|---|
| FR-001, FR-003, FR-005, FR-006, FR-007, FR-011 | satisfeitos |
| FR-002, FR-004, FR-010 | F1 |
| FR-008 | F2 |
| FR-009 | satisfeito (validação aceita as duas versões, sem reescrita) |
| FR-012 | oito pontos em 6.0.3, `validate_distribution` OK; a release é ato do `ship` |
| SC-001 a SC-006 | cobertos pela suíte; SC-006 em exit 0 |
| SC-007 | fora do aceite desta entrega, por definição da própria spec |

## Constituição

Sem violação. O bump obrigatório está completo nos oito pontos. A cláusula de release por versão é cumprida no `ship`, pelo pipeline do push para `main`.

## Métricas

- Requisitos/critérios verificados: 12 FR + 6 SC aplicáveis
- Decisões de plano verificadas: 5 fases, 10 arquivos nomeados
- Cláusulas constitucionais verificadas: 11
- Achados: missing 0 · partial 1 · contradicts 1 · unrequested 0
- Severidade: CRITICAL 0 · HIGH 2 · MEDIUM 0 · LOW 0

## Próxima ação

Duas tarefas anexadas em `## Phase 6: Convergence` (T014, T015). Executar `implement-parallel` sobre elas e reconvergir; uma segunda passagem deve encontrar zero achados.

---

# Rodada 2 — 2026-09-19, após a Phase 6

**Entradas**: spec.md, plan.md, tasks.md (T001–T015), constituição (11 cláusulas) · **Desfecho**: `converged`

A Phase 6 foi entregue pelo nó `p06-a` da run `run-635a5d0f4a44bb793a1482fa` e integrada em `989f519`. `tasks.md` não foi tocado nesta rodada.

## Achados da rodada 1

| Achado | Situação | Prova |
|---|---|---|
| F1 — envelope duplo (contradicts, FR-002/FR-004/FR-010) | **fechado** | `_takeover_observation` passou a ler `dispatch` e `projection` do mapa desembrulhado, via `agent_runtime._object`, o mesmo caminho do adapter. O helper `takeover_show()` deixou de espelhar as duas formas e produz só a envelopada, que é a real — é o que torna o caso sensível à regressão: com a leitura antiga, `status` voltaria a ser nulo e falhariam tanto a asserção de `TAKEOVER-LEADER-ACTIVE` para líder vivo quanto a asserção nova de `liveness` no registro de sucessão |
| F2 — emissão na versão anterior (partial, FR-008) | **fechado** | Os dois pontos de emissão (`grill_workspace.py:1872` e `:3357`) gravam `CHECKPOINT_SCHEMA_V2` com `context_inputs_sha256` e `origin_metadata_sha256`, carregando os mesmos valores de antes. O caso novo em `validate_checkpoint_contract.py` exige a versão nova na emissão e nega a presença dos nomes antigos; `CommittedCheckpointContract`, que monta um documento da versão anterior, ficou byte a byte intocado, preservando FR-009 |

Nenhum achado novo: missing 0 · partial 0 · contradicts 0 · unrequested 0.

## Verificação

| Validador | Resultado |
|---|---|
| `validate_agent_orchestration_contract.py` | 36 OK |
| `validate_checkpoint_contract.py` | 80 OK (78 antes) |
| `validate_orchestrator_store_contract.py` | 136 OK |
| `python3 tests/run_validators.py` | **exit 0** — 30 validadores, 1488 testes, 0 falhas, 2 skips de macOS |

A suíte completa foi reexecutada de propósito: T015 mudou o schema que a emissão grava, e os três validadores do grant não provariam sozinhos que nenhum outro validador lê um ponto de retomada recém-emitido. SC-006 exige a suíte inteira, sem validador desativado ou afrouxado.

## Observação para o review

`_takeover_observation` chama `agent_runtime._object`, um helper privado de outro módulo. É o menor diff correto e reusa a validação do envelope em vez de reimplementá-la, mas acopla a um nome privado. Não é violação de requisito nem de cláusula; é ponto de julgamento técnico da etapa `review`.

## Próxima ação

Seguir para `verify`.

---

# Rodada 3 — 2026-09-20, consumindo o review R1

**Entradas**: spec.md, plan.md, tasks.md (T001–T015), review.md (R1), constituição (11 cláusulas) · **Desfecho**: `tasks_appended` (Phase 7, T016–T022)

O review R1 devolveu `REQUEST CHANGES` com 1 Critical e 7 Important. Esta rodada avaliou cada achado contra a intenção declarada e converteu em tarefa o que é lacuna real de requisito.

## Findings

| ID | Gap Type | Severidade | Origem | Evidência | Tarefa |
|----|----------|------------|--------|-----------|--------|
| G1 | contradicts | **CRITICAL** | FR-001, FR-003 (US1, P1) | `grill_workspace.py:3739-3741` grava o líder sucessor com encarnação, referência e digest de observação nulos; `_require_current_leader` (`:1629-1632`) compara esses campos contra observação fresca, então os 14 comandos com `@_gauntlet_authorized` recusam a sessão entrante com `LEADER-AUTHORITY-UNPROVEN`, sem saída | T016 |
| G2 | contradicts | HIGH | FR-002, FR-003 | O bloco de mutação (`:3722-3729`) revalida só identidade de contexto; quiescência (`:3672`), ponto de retomada corrente (`:3681`) e campanha são decididos sobre o snapshot de `:3643`, fora do lock | T017 |
| G3 | contradicts | HIGH | FR-003, FR-010 | O hash de entradas relidas (`:3693-3699`) inclui o digest dos bytes crus da resposta viva; campo volátil torna a aplicação inalcançável e a recusa mente sobre a causa | T018 |
| G4 | partial | HIGH | FR-011, SC-002, SC-004 | Os casos de tomada em `validate_orchestrator_store_contract.py` exercitam a fixture `CONTEXT_TAKEOVER`, que reimplementa a mutação; o produto nunca roda. O caso dito de concorrência não concorre, e o ponto de retomada sintetizado é testado na versão anterior do formato | T020 |
| G5 | partial | MEDIUM | FR-011 | Cobertura da preparação de troca deslocada para estado inalcançável em produção; o caminho novo só assere o veredito, sem verificar o documento gravado | T021 |
| G6 | partial | MEDIUM | Key Entity "Contexto de orquestração", FR-005 | Recursos do predecessor ficam inalcançáveis: a verificação de autoridade exige contexto corrente e ativo, e a tomada deixa o anterior encerrado | T019 |
| G7 | contradicts | LOW | FR-008 | O comentário em `agent_orchestration.py:28-32` afirma que a emissão ainda usa a versão anterior; falso desde T015, e convida a reverter a entrega | T022 |

## O que não virou tarefa

Débito de design registrado, sem requisito violado, portanto fora do escopo de tarefa desta rodada:

- `observe_predecessor_termination` devolver `dispatch_status` e `liveness`, eliminando o reparse, o canal lateral de captura e o acoplamento ao nome privado `_object`;
- extrair a leitura de transporte comum entre a observação de tomada e a fronteira de líder, removendo o parâmetro `runtime` morto;
- construtor único para o documento de ponto de retomada, hoje duplicado em dois emissores;
- mover a tabela decisória da tomada para `grill_core`, pelo critério que rege `triage.py`.

Os dois primeiros tocam exatamente a fronteira que T016 e T018 vão editar, então entram como orientação de implementação dessas tarefas — não como escopo novo.

## Ressalva sobre G6

É o único achado cujo trace de requisito é **inferido, não literal**: a spec não menciona limpeza de recursos em nenhum ponto. O vínculo vem da Key Entity declarar que o contexto registra as atividades do work item, e de FR-005 exigir que o estado sobreviva à tomada — um recurso preso num contexto encerrado é estado que não sobreviveu de forma utilizável. Se a leitura humana for de que isso é escopo novo, T019 deve sair desta entrega e virar work item próprio.

## Versão

A 6.0.3 ainda não foi publicada — `main` está em 6.0.2. Correções que entrem nesta mesma versão não exigem novo bump, e os oito pontos de distribuição seguem coerentes.

## Métricas

- Requisitos verificados: 12 FR + 6 SC aplicáveis
- Cláusulas constitucionais verificadas: 11 — sem violação
- Achados: missing 0 · partial 3 · contradicts 4 · unrequested 0
- Severidade: CRITICAL 1 · HIGH 3 · MEDIUM 2 · LOW 1

## Próxima ação

Sete tarefas anexadas em `## Phase 7: Convergence`. Executar `implement-parallel` e reconvergir; depois `verify` e `review` de novo.

---

# Rodada 4 — 2026-09-20, após a Phase 7

**Entradas**: spec.md, plan.md, tasks.md (T001–T022), constituição (11 cláusulas) · **Desfecho**: `converged`

A Phase 7 foi entregue pelos nós `p07-a`, `p07-b` e `p07-c` da run `run-dc0dc8ba5b7a8f9de176ddb2` e integrada até `6ed634a`. `tasks.md` não foi tocado nesta rodada.

## Achados da rodada 3

Cada um verificado no código integrado, não no relato dos workers.

| Achado | Situação | Prova |
|---|---|---|
| G1 — líder sucessor sem observação (CRITICAL) | **fechado** | `_session_readiness` da sessão entrante é chamado em `grill_workspace.py:3681`, antes do cálculo de `expected`, então vale para prévia e aplicação; os três campos são gravados no líder do sucessor em `:3768-3770`. A cobertura correspondente executa `gauntlet-step-enter` com o `--session-ref` da sessão entrante e exige saída 0, atravessando `_require_current_leader` |
| G2 — sem guarda de revisão | **fechado** | `grill_workspace.py:3750`, primeira linha do `mutate`, com o comentário nomeando a janela que fecha: um worker transicionando entre a leitura e o commit faria `TAKEOVER-APPLIED` sair onde `TAKEOVER-WORK-ACTIVE` era devido |
| G3 — digest da resposta viva | **fechado** | `expected` passou a digerir `verdict`, `reference` e `snapshot.revision`; o digest dos bytes crus permanece apenas em `evidence`, onde é prova de sucessão e não entrada de comparação |
| G4 — casos do store exercitando a fixture | **fechado** | Os que permanecem na fixture declaram no nome que são aceitação de formato do `validate_block`, e o cabeçalho da fixture lista as divergências em relação ao produto. O caso dito de concorrência virou `test_takeover_over_an_already_superseded_source_is_refused`, sequencial. O do ponto de retomada passou a chamar `grill_workspace._initial_continuity_checkpoint`, o emissor real |
| G5 — cobertura deslocada do prepare-switch | **fechado** | Depois do veredito, o caso relê o snapshot e assere `schema == CHECKPOINT_SCHEMA_V2`, `previous_checkpoint_id` nulo e os dois digests contra `context["inputs_sha256"]` e `item["origin"]["metadata_sha256"]` |
| G6 — recursos órfãos | **fechado** | `preserved_resources` e `operations_to_reconcile` projetados e devolvidos em `TAKEOVER-APPLIED` |
| G7 — comentário falso | **fechado** | Reescrito: desde T015 todo emissor usa v2, e v1 permanece apenas para leitura de documentos já materializados, nunca sendo emitida |

Nenhum achado novo: missing 0 · partial 0 · contradicts 0 · unrequested 0.

## Sensibilidade à regressão

O ponto que faltava nas rodadas anteriores, e que explicava o Critical ter atravessado 1488 testes verdes, foi atacado de frente. O worker de T021 verificou por reversão temporária, com o arquivo restaurado ao final:

- T016 revertido — líder com os três campos nulos: **3 subcasos reprovam**;
- T016 revertido **com as asserções de campo removidas**, deixando apenas o comando autorizado: **3 reprovam**, com `LEADER-AUTHORITY-UNPROVEN`. O caso sozinho reproduz o defeito ponta a ponta, sem depender de asserção sobre estrutura interna;
- `presentation` revertida para cópia do predecessor: **3 reprovam** — a asserção não é vácua, os dois valores divergem de fato na fixture;
- checkpoint inicial revertido para v1: **1 reprova**.

## Decisão sobre a apresentação do sucessor

A linha de T021 em `tasks.md` pedia asserir a apresentação "herdada do predecessor". Isso está errado e foi corrigido na condução, não no texto: apresentação é propriedade da sessão, e herdar a de uma sessão comprovadamente morta seria prova falsa. O sucessor grava a apresentação observada da sessão entrante, espelhando `continuity_resume_command`; `worktree_identity` segue herdada do predecessor. Quem levantou a contradição foi o próprio worker que implementou T016, antes de o caso errado ser escrito.

## Verificação

`python3 tests/run_validators.py` → **exit 0**: 30 validadores, 1488 testes, 0 falhas, 2 skips condicionados a macOS. A contagem não subiu porque as asserções novas entraram em casos existentes, via subTests, e o trabalho no store foi de renomeação e precisão, não de volume.

## Versão

A 6.0.3 continua sem publicar — `main` está em 6.0.2. As correções desta fase entram na mesma versão e não exigem novo bump; os oito pontos de distribuição seguem coerentes.

## Métricas

- Requisitos verificados: 12 FR + 6 SC aplicáveis
- Cláusulas constitucionais verificadas: 11 — sem violação
- Achados: missing 0 · partial 0 · contradicts 0 · unrequested 0
- Severidade: nenhuma

## Próxima ação

Seguir para `verify` e depois `review` R2.

---

# Rodada 5 — 2026-09-20, consumindo o review R2

**Entradas**: spec.md, plan.md, tasks.md (T001–T022), review.md (R2), constituição · **Desfecho**: `tasks_appended` (Phase 8, T023–T029)

## Correção de um erro da rodada 4

A rodada 4 declarou G6 **fechado**. Estava errado, e quem pegou foi o revisor de correção do R2. Verifiquei que `preserved_resources` e `operations_to_reconcile` passaram a ser devolvidos; não verifiquei que algum caminho os consome. Nenhum consome: `gauntlet_cleanup_command` filtra por contexto corrente e a verificação de autoridade exige corrente e ativo, condições que o contexto encerrado pela tomada não satisfaz mais.

Presença de código não é cumprimento de requisito. O registro fica, porque o erro é instrutivo: nas rodadas anteriores a verificação foi feita contra o diff, e não contra o comportamento que o diff deveria produzir.

## Findings

| ID | Gap Type | Severidade | Origem | Evidência | Tarefa |
|----|----------|------------|--------|-----------|--------|
| H1 | contradicts | **CRITICAL** | FR-001, FR-005 | `grill_workspace.py:3774` copia `worktree_identity` sem reverificar, enquanto o irmão de retomada deriva a identidade viva e recusa (`:3544-3546`). A identidade inclui a branch, então trocar de branch depois da morte da sessão faz o sucessor herdar identidade falsa, e toda retomada posterior falha sem verbo de re-carimbo | T023 |
| H2 | contradicts | HIGH | FR-003 | `snapshot.revision` no digest (`:3705-3708`) é a revisão global do documento; qualquer escrita invalida a prévia, inclusive a do próprio decorador de autorização (`:3227-3233`). A guarda sob lock (`:3749`) já cobre isso de forma mais forte | T024 |
| H3 | contradicts | HIGH | FR-010 | `gauntlet_cleanup_command:3862` avalia `any()` sobre lista vazia e devolve `CLEANED` com saída zero. Defeito **pré-existente**, não introduzido pela Phase 7 | T025 |
| H4 | partial | HIGH | FR-011 | As duas projeções não têm asserção alguma; revertê-las para vazio passa verde nos 1488 testes | T027 |
| H5 | partial | HIGH | FR-011 | `TAKEOVER-CAS-CONFLICT` só aparece em comentário | T027 |
| H6 | contradicts | MEDIUM | FR-004 | O comentário de T019 afirma entrega ao sucessor para reconciliação; nada reconcilia | T026 |
| H7 | partial | MEDIUM | FR-011 | O cabeçalho da fixture omite que `evidence.liveness` é string na fixture e `dict` ou `None` no produto | T028 |
| H8 | partial | LOW | FR-011 | O contrato do store importa um helper privado do CLI que toca disco | T029 |

## Decisão sobre a reconciliação de recursos

**Não implementar nesta entrega.** O trace de G6 sempre foi inferido, e está registrado como tal desde a rodada 3: a spec não menciona limpeza de recursos em ponto algum. Implementar a reconciliação agora seria escopo novo entrando sem passar pela spec.

O que entra é corrigir as duas mentiras que a entrega produziu: a afirmação falsa no comentário (H6) e o sucesso falso do verbo de limpeza (H3). A reconciliação de recursos de contexto encerrado fica registrada como trabalho próprio, a ser especificado.

Essa escolha é deliberada e revisável: a alternativa — fazer o cleanup aceitar recursos cuja origem esteja na cadeia de predecessores — está descrita em `review.md`, R2-2, opção (a).

## O que não virou tarefa

Preferência de design, sem requisito violado: derivar o identificador de operação a partir do hash de entradas em vez da observação; a prévia devolver a apresentação; o tamanho da função de tomada, hoje em 162 linhas contra o teto de 200; extrair a projeção de recursos para o núcleo; e os quatro itens de débito já registrados na rodada 3.

## Versão

A 6.0.3 continua sem publicar — `main` em 6.0.2. Sem novo bump.

## Métricas

- Requisitos verificados: 12 FR + 6 SC aplicáveis
- Cláusulas constitucionais: 11 — sem violação
- Achados: missing 0 · partial 4 · contradicts 4 · unrequested 0
- Severidade: CRITICAL 1 · HIGH 4 · MEDIUM 2 · LOW 1

## Próxima ação

Sete tarefas em `## Phase 8: Convergence`. Executar `implement-parallel` e reconvergir.

---

# Rodada 6 — 2026-09-20, após a Phase 8

**Entradas**: spec.md, plan.md, tasks.md (T001–T029), constituição · **Desfecho**: `converged`

Phase 8 entregue pelos nós `p08-a`, `p08-b` e `p08-c` da run `run-7b4f4d82ed49a5ead7c15c3e`, integrada até `9c43b96`. `tasks.md` não foi tocado nesta rodada.

## Achados da rodada 5

Cada um verificado no código integrado. Desta vez a verificação foi feita contra o **comportamento**, não contra a presença do diff — que foi o erro da rodada 4.

| Achado | Situação | Prova |
|---|---|---|
| H1 — identidade herdada sem verificar (CRITICAL) | **fechado** | `_continuity_identity` derivado em `grill_workspace.py:3716`; recusa `TAKEOVER-IDENTITY-DIVERGENT` quando diverge do carimbo do predecessor; a identidade derivada, e não a cópia, é gravada no sucessor. O caso sem carimbo prévio não recusa — carimba pela primeira vez, porque recusar tornaria a tomada impossível para sempre, já que não existe verbo de re-carimbo |
| H2 — `snapshot.revision` no digest | **fechado** | zero ocorrências dentro do comando de tomada; a guarda sob o lock permanece e é a proteção real |
| H3 — sucesso falso na limpeza | **fechado** | `if selected and candidates and not results` (`:3914`), com os candidatos contados **antes** dos filtros. Zero candidatos segue sendo no-op legítimo; candidatos sem resultado é falha de seleção |
| H4 e H5 — projeções e recusa de CAS sem teste | **fechado** | casos novos em `validate_agent_orchestration_contract.py`, com quatro reversões verificadas — inclusive a que remove os filtros das compreensões, provando que o filtro é testado e não só a presença da chave |
| H6 — comentário falso | **fechado** | passou a dizer que a projeção existe só para auditoria e que a reconciliação **não** está implementada |
| H7 — divergência de tipo na fixture | **fechado** | a fixture passou a emitir o mapa que o produto emite, eliminando a divergência em vez de documentá-la |
| H8 — import do CLI no contrato do store | **fechado** | o import foi removido; resta apenas a menção no comentário que explica a remoção |

Nenhum achado novo: missing 0 · partial 0 · contradicts 0 · unrequested 0.

## Duas intervenções do coordenador, registradas

**T025 voltou ao worker por ter pegado largo demais.** A primeira versão da guarda usava `selected and not results`, e `selected` é verdadeiro com qualquer `--context-id` — o que passou a recusar o caso legítimo de não haver nada a limpar. Um caso existente quebrou, e isso foi tratado como evidência do erro, não como dano colateral aceitável. Depois do estreitamento por contador de candidatos, aquele caso voltou a passar **sozinho**, sem que ninguém tocasse no arquivo de teste. Essa é a prova de que a guarda ficou no lugar certo.

**T029 não foi executada como escrita, por decisão do worker que eu endosso.** Mover o emissor do ponto de retomada para o núcleo exige editar `grill_workspace.py`, fora do grant daquele nó; obedecer ao pé da letra deixaria duas implementações do mesmo emissor no repositório. O worker optou por remover a dependência do helper privado dentro do que podia tocar, trocou asserções de shape por uma recusa real de cadeia para o caso não virar tautologia, e registrou a pendência. Verifiquei que nenhuma cobertura se perdeu: a fidelidade do emissor day-zero é exercida no nível do CLI, em `validate_agent_orchestration_contract.py`, onde o caso lê o checkpoint que o `prepare-switch` real gravou e confere schema, ausência de predecessor e os dois digests contra suas fontes.

## Débito acumulado desta entrega

Registrado, sem virar tarefa por não violar requisito:

- `observe_predecessor_termination` devolver `dispatch_status` e `liveness`, eliminando o reparse, o canal lateral e o acoplamento ao helper privado `_object`;
- extrair a leitura de transporte comum e remover o parâmetro `runtime` morto de `_takeover_observation`;
- mover o emissor do ponto de retomada inicial para o núcleo, recebendo as obrigações já lidas pela fronteira — exige um nó com `grill_workspace.py` e `agent_orchestration.py` no mesmo grant;
- extrair a projeção de recursos, que é lógica pura e duplicada entre a tomada e a retomada;
- reconciliação de recursos presos em contexto encerrado, que a spec nunca declarou e que precisa de especificação própria;
- o tamanho do comando de tomada, hoje acima do limiar prático e abaixo do teto.

## Verificação

`python3 tests/run_validators.py` → **exit 0**: 30 validadores, 1488 testes, 0 falhas, 2 skips condicionados a macOS.

## Métricas

- Requisitos verificados: 12 FR + 6 SC aplicáveis
- Cláusulas constitucionais verificadas: 11 — sem violação; 6.0.3 segue sem publicar, sem novo bump
- Achados: missing 0 · partial 0 · contradicts 0 · unrequested 0

## Próxima ação

Seguir para `verify` e depois `review` R3.

---

# Rodada 7 — 2026-09-20, consumindo o review R3

**Entradas**: spec.md, plan.md, tasks.md (T001–T029), review.md (R3), constituição · **Desfecho**: `tasks_appended` (Phase 9, T030–T033)

## O padrão desta rodada

A Phase 8 corrigiu os achados do R2 **fechando demais**. As duas guardas que acrescentou para impedir estados ruins passaram a impedir também estados legítimos, e de forma permanente, porque o core não tem verbo de re-carimbo nem de reconciliação. É a terceira rodada seguida em que a correção de um defeito cria outro na direção oposta.

| Achado | Gap Type | Severidade | Origem | Evidência | Tarefa |
|---|---|---|---|---|---|
| J1 | contradicts | **CRITICAL** | FR-001 | `grill_workspace.py:3716-3721` compara a identidade inteira; `phase` (`:3289`) avança a cada etapa do ciclo. Contexto criado em `implement-parallel`, ciclo em `converge`, sessão morta: a tomada recusa `TAKEOVER-IDENTITY-DIVERGENT` para sempre. Metade dos work items do repositório cai no fallback para `current_step` | T030 |
| J2 | contradicts | HIGH | FR-001 | `branch` no mesmo predicado faz a tomada recusar **exatamente** o cenário que o comentário de T023 declara curar. O deadlock mudou do `prepare-switch` para a tomada | T030 |
| J3 | contradicts | HIGH | FR-010 | `:3888` incrementa `candidates` antes do filtro de `origin_context_id`, contando recurso de outro contexto. Depois de uma tomada, a limpeza do sucessor recusa para sempre por um recurso que ele não pode fechar, e que o próprio T026 declara não reconciliável | T031 |
| J4 | partial | HIGH | FR-011 | A guarda de `candidates` não tem teste: removida, a suíte inteira passa | T032 |
| J5 | partial | MEDIUM | FR-011 | O comentário em `validate_orchestrator_store_contract.py:596` promete cobertura do estado projetado que não existe; a validação aceita `dict` ou `list` no campo, então regressão de formato passaria | T033 |

## Decisão sobre o predicado de identidade

**`phase` e `branch` saem da comparação.** Ficam como pinos `project_id`, `work_id`, `du`, `git_common_dir` e `real_path` — os campos que de fato identificam a árvore e o work item, e que não mudam por trabalho normal.

O raciocínio é que a tomada é o **caminho de recuperação**, e o sucessor já grava a identidade **derivada**. Tirando os dois campos voláteis do predicado, a tomada passa a recarimbar fase e branch em vez de recusar por causa delas — e o comentário que promete curar o caso da branch trocada passa a dizer a verdade, porque a cura passa a existir.

A alternativa, manter `branch` no predicado e acrescentar um verbo de re-selagem ao core, é escopo maior e não declarado pela spec. Fica registrada como caminho alternativo em `review.md`, R3-2.

## Uma falha de instrução do coordenador

J3 não é erro do worker. Na rodada anterior devolvi a guarda por estar larga demais e instruí que contasse "candidatos antes dos filtros". O worker seguiu ao pé da letra. A instrução é que estava errada: "antes dos filtros" inclui o filtro de contexto, que é justamente o que deveria filtrar. A guarda que pedi para eliminar um sucesso falso criou um bloqueio permanente na direção oposta.

Fica registrado porque o padrão é instrutivo: uma instrução imprecisa do coordenador produz um defeito que nenhum worker tem autoridade para questionar.

## Os Minor não viram tarefa

m1 é consequência de J1 e J2 e se resolve junto. m2 — `sealed is None` aceitar árvore que o predecessor nunca usou — é limitação conhecida, estreita e sem remédio barato. m3, m4 e m5 são polimento sem requisito violado. Todos registrados como débito em `review.md`.

## Versão

6.0.3 segue sem publicar, `main` em 6.0.2. Sem novo bump.

## Métricas

- Requisitos verificados: 12 FR + 6 SC aplicáveis
- Cláusulas constitucionais: 11 — sem violação
- Achados: missing 0 · partial 2 · contradicts 3 · unrequested 0
- Severidade: CRITICAL 1 · HIGH 3 · MEDIUM 1

## Próxima ação

Quatro tarefas em `## Phase 9: Convergence`. Executar `implement-parallel` e reconvergir.

---

# Rodada 8 — 2026-09-20, após a Phase 9

**Entradas**: spec.md, plan.md, tasks.md (T001–T033), constituição · **Desfecho**: `converged`

Phase 9 entregue pelos nós `p09-a` e `p09-b` da run `run-de9b8afd4321a379178c64fb`. `tasks.md` não foi tocado nesta rodada.

## Achados da rodada 7

| Achado | Situação | Prova |
|---|---|---|
| J1 e J2 — `phase` e `branch` no predicado (CRITICAL) | **fechado** | `grill_workspace.py:3730` compara apenas `("project_id", "work_id", "du", "git_common_dir", "real_path")`. A identidade derivada segue sendo gravada no sucessor, então a tomada **recarimba** fase e branch em vez de recusar |
| J3 — contador inflado por recurso de outro contexto | **fechado** | O filtro de `origin_context_id` foi separado e vem **antes** do incremento; o recurso de outro contexto vai para a lista `retained`, que rebaixa o veredito em vez de recusar a operação |
| J4 — guarda sem teste | **fechado** | Caso novo cobrindo os dois lados, com quatro reversões verificadas |
| J5 — estado projetado sem asserção | **fechado** | Asserções sobre sequência, etapa corrente e resultados aceitos, com verificação de que a sequência é lista |

Nenhum achado novo: missing 0 · partial 0 · contradicts 0 · unrequested 0.

## Duas decisões do worker que corrigiram o enunciado

**O texto de T032 estava desatualizado, e o worker percebeu.** A tarefa mandava semear, para o lado da recusa, "recurso cujo contexto de origem é outro". Mas isso **deixou de ser candidato** justamente por causa de T031, que entrou na mesma fase. O enunciado foi escrito antes de a correção existir. O worker usou o candidato que a guarda de fato protege hoje — recurso do próprio contexto sem atividade vinculada — e moveu o cenário original para os casos de relato. Ler o código em vez de obedecer à prosa é o comportamento correto, e fica registrado.

**O caso de recarimbo é fiel à produção.** `worktree_identity` é campo imutável no store, então não havia como alterar o carimbo. Em vez de forçar, o worker moveu a **árvore viva**: `git checkout -b` real e `active_phase` novo no `state.json`, que é exatamente o que acontece quando um humano troca de branch depois de a sessão morrer. A branch original é restaurada no `finally`.

## Sensibilidade verificada

Quatro reversões, todas reprovando:

- predicado de volta à identidade inteira → o caso `work-restamp` reprova com `TAKEOVER-IDENTITY-DIVERGENT`, que **é** o bloqueio permanente descrito no R3;
- filtro de volta para depois do contador → o sucessor volta a ser recusado em vez de ter o veredito rebaixado;
- guarda neutralizada → a seleção que não alcança nada volta a devolver sucesso, o buraco do R3-4;
- guarda alargada de volta → reprova pelo lado do no-op legítimo.

## Verificação

`python3 tests/run_validators.py` → **exit 0**: 30 validadores, **1489** testes, 0 falhas, 2 skips condicionados a macOS. A contagem subiu de 1488 com o caso `work-restamp`.

## Métricas

- Requisitos verificados: 12 FR + 6 SC aplicáveis
- Cláusulas constitucionais: 11 — sem violação; 6.0.3 sem publicar, sem novo bump
- Achados: missing 0 · partial 0 · contradicts 0 · unrequested 0

## Próxima ação

Seguir para `verify` e depois `review` R4.

---

# Rodada 9 — 2026-09-20, consumindo o review R4

**Entradas**: spec.md, plan.md, tasks.md (T001–T033), review.md (R4), constituição · **Desfecho**: `tasks_appended` (Phase 10, T034–T039)

## O padrão, nomeado

Quatro rodadas de review, quatro `REQUEST CHANGES`, e a mesma forma em todas: **a correção fecha o caso que examinou e abre o vizinho**. A raiz comum é que `gauntlet_context_takeover_command` e `gauntlet_cleanup_command` vêm sendo corrigidos isoladamente, sem tratar os irmãos que compartilham a mesma lógica — o predicado mudou na tomada e não nos dois comandos de continuidade; o filtro mudou no ramo de contexto e não no de atividade.

T035 existe justamente para quebrar esse ciclo: em vez de corrigir mais um ponto, alinha os irmãos.

| Achado | Gap Type | Severidade | Origem | Evidência | Tarefa |
|---|---|---|---|---|---|
| K1 | contradicts | **CRITICAL** | FR-010 | `grill_workspace.py:3903-3918` coleta o retido antes da discriminação por seletor, que só ocorre em `:3920`. O ramo por atividade sai rebaixado por recurso alheio, permanentemente | T034 |
| K2 | partial | **CRITICAL** | FR-011 | `TAKEOVER-IDENTITY-DIVERGENT` não aparece em teste algum; apagar o `raise` inteiro deixa a suíte em 37/37 | T036 |
| K3 | contradicts | HIGH | FR-001, FR-005 | A tomada ignora fase e branch; `prepare-switch` e `continuity-resume` comparam tudo e nunca recarimbam. A primeira virada de etapa recusa para sempre | T035 |
| K4 | partial | HIGH | FR-011 | O emissor paralelo do comando de checkpoint não é observado; regredindo só ele, os três validadores passam | T037 |
| K5 | partial | MEDIUM | FR-011 | O caso de recarimbo move a árvore fora do bloco protegido; falha entre checkout e escrita vaza branch para os casos seguintes | T038 |
| K6 | partial | MEDIUM | FR-010 | O código de recurso retido e o campo que o carrega não existem no protocolo. O leader recebe vocabulário sem regra e, como o protocolo manda não converter preservação em aprovação, a leitura padrão vira bloqueio — anulando o desenho não-bloqueante que a própria correção introduziu | T039 |

## Sobre K6, que quase não virou tarefa

A pergunta era se documentação de protocolo é lacuna de requisito ou débito. É lacuna. A correção de K1 desenha o campo para **relatar sem bloquear**, mas essa semântica só existe se quem consome souber lê-la. Sem o texto, a entrega publica um comportamento que o consumidor interpreta ao contrário do pretendido — o que é, na prática, o comportamento não entregue.

## Fora de escopo, por decisão registrada

**R4-4** (os cinco campos estruturais não distinguem worktree recriada no mesmo caminho) e **R4-5** (`project_id` vira com `git stash push -u`, porque a derivação usa `--all`, que inclui as referências de stash) são defeitos **pré-existentes** e de alcance maior que esta entrega. A spec não declara âncora de árvore nem derivação de identidade de projeto; corrigi-los aqui seria escopo novo entrando sem passar pela spec, e o segundo re-deriva identidade de campanha já selada.

Ficam registrados como trabalho próprio, a ser especificado. O detalhe de R4-5 merece registro à parte: **guardar a árvore suja antes de assumir a sessão é o gesto natural do fluxo de recuperação**, e é exatamente o que dispara o bloqueio — o defeito cai onde a tomada existe para curar.

## Os Minor

n1, n3, n4, n5, n6 e n7 seguem como débito, sem virar tarefa. n2 virou K6.

## Versão

6.0.3 sem publicar, `main` em 6.0.2. Sem novo bump.

## Métricas

- Requisitos verificados: 12 FR + 6 SC aplicáveis
- Cláusulas constitucionais: 11 — sem violação
- Achados: missing 0 · partial 4 · contradicts 2 · unrequested 0
- Severidade: CRITICAL 2 · HIGH 2 · MEDIUM 2

## Próxima ação

Seis tarefas em `## Phase 10: Convergence`. Executar `implement-parallel` e reconvergir.
