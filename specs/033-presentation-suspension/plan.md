# Implementation Plan: Suspensão e reativação da apresentação local no core

**Branch**: `cadugevaerd/feat-new-subagents` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/033-presentation-suspension/spec.md`; work item `fix-presentation-suspension-d97e4c3d7b434c119477ec59d56ecbd5` (PLAN-CONTEXT, ADR-0001..0003, CONTEXT); laudo `.grill/triage-evidence/presentation-suspension-debug.md`; revisão independente R1 do plano (worker `ctx_b903b26f1523`), aplicada na r2 (§Revisão R1 aplicada); revisão independente R2 (worker `ctx_d966d5ec5594`), aplicada nesta r3 (§Revisão R2 aplicada)

## Summary

`project_leader_presentation` (`grill_core/agent_runtime.py:1107-1129`) é o único ponto que observa a sessão e projeta a apresentação local, e hoje chama `presentation_state` sem `suspension` nem `application`; a função pura já sabe representar `suspended_by_user` (`agent_runtime.py:275-287`) e os consumidores a jusante já aceitam essa projeção (`agent_orchestration.py:1108-1147`). A entrega acrescenta **um produtor**: uma função pura que percorre as mensagens normalizadas do transcript e devolve a última frase de controle (`stop adhd mode` / `start adhd mode`) dita em mensagem `role=user` com `id` string e um único bloco de texto. Suspensão vigente projeta `application=suspended_by_user`, `loading=stale`, `work_ready=true`, `use_ready=false`, sem `load_request` e sem chamar `_full_read`; reativação corta as leituras anteriores à frase, como a compactação já faz.

Com a projeção suspensa, `_session_readiness` (`grill_workspace.py:1646-1650`) já não recusa, porque `work_ready=true`. O gate de upgrade em `_gauntlet_authorized` só precisa **não recusar**: o bloco `grill_workspace.py:3468-3474`, que recusaria `STYLE-LOAD-UNCONFIRMED` por mudança de `config_fingerprint`/`gwd_skill_sha256` sem `use_ready`, é removido (ADR-0003, R7). Hoje ele é inalcançável (sem produtor, `work_ready ⇒ use_ready`); com o produtor, seria exatamente a recusa errada.

Contrato publicado passa a nomear fonte não-agente da sessão e `start adhd mode` em quatro lugares: `SKILL.md` §Bootstrap, `session-protocol.md`, `README.md` l.72 e `references/agent-orchestration.md` l.25 (FR-012). Testes offline: **todas** as mensagens injetadas nos cenários nascem de `_native_messages` sobre registros mínimos na forma capturada de sessões reais dos dois harness (FR-011, R10); o caso do gate já existe em `tests/validate_task_import_contract.py` e é invertido, como último bloco do `with` (C1; posição por I1 da R2). Bump patch nos nove pontos de versão no ship: os oito de versão mais a entrada em `CHANGELOG.md` (I2 da R2).

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão (`hashlib`, `json`)

**Primary Dependencies**: nenhuma nova; reaproveita `presentation_state`, `_native_messages`, `_full_read`, `leader_session_identity` e `_presentation_config_fingerprint` já existentes em `agent_runtime.py`

**Storage**: nenhum campo novo; a projeção suspensa entra no `presentation` do contexto de orquestração já persistido pelo Store (`.git/grill/orchestrator.json`) pelo refresh existente em `grill_workspace.py:3475-3482` (numeração de hoje; após remover o bloco morto, l.3468-3475)

**Testing**: `unittest` via `python3 tests/run_validators.py`; três validadores existentes tocados: `tests/validate_agent_orchestration_contract.py` (4 testes novos + helper `native`), `tests/validate_task_import_contract.py` (caso do gate invertido) e `tests/validate_distribution.py` (asserção `start adhd mode` por documento do FR-012, M2 da R2); fixture `tests/orchestration_fixture.py` sem alteração

**Target Platform**: Linux, macOS e Windows (matriz CI: 3 SOs × Python 3.10 e 3.13); nenhum teste toca rede, runtime real ou processo externo

**Project Type**: plugin CLI / biblioteca do core GWD

**Performance Goals**: uma varredura linear adicional sobre `transcript["messages"]` por observação, no mesmo transcript já lido para `_full_read`; nenhuma leitura extra do host

**Constraints**: fail-closed; a suspensão só nasce da observação da sessão (FR-006); códigos de recusa mantêm significado (FR-010); `presentation_state` continua pura e com a mesma assinatura; política `agent-orchestration.v1.json` intocada (R8, `policy_sha256`); menor diff (Ponytail/YAGNI)

**Scale/Scope**: 2 pontos de mudança no core (+25 linhas em `agent_runtime.py`, −7 linhas em `grill_workspace.py`), 4 documentos de contrato (1 parágrafo ou 1 frase cada), ~115 linhas de teste em dois validadores existentes mais 4 asserções em `validate_distribution.py`, 9 pontos de versão (8 de versão + `CHANGELOG.md`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constituição `2.1.0`, sha256 `54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569` (a mesma selada no work item). Onze cláusulas: dez princípios e Governance. Os status seguem o `CONSTITUTION-CHECK.md` do work item: as duas cláusulas de distribuição são NOT-APPLICABLE em trabalho plan-only, com a obrigação registrada para o ship.

| Cláusula | Pré-design | Pós-design | Evidência |
|---|---|---|---|
| Evidência antes de afirmação | PASS | PASS | laudo com reprodução offline (Exp A1/A2/A3/B); formas nativas capturadas de amostras locais Claude e Codex (research R10), revisadas de forma independente (R1) |
| Work item isolado e ownership | PASS | PASS | bundle próprio; este plano escreve só em `specs/033-presentation-suspension/` |
| Feature/fix plan-only | PASS | PASS | fix: código de produto e testes só em `implement-parallel`, por worker; plan termina em `PLAN_ONLY_STOP` |
| Sequência obrigatória do desenvolvimento | PASS | PASS | specify atestado (`c2dd807`); plan em andamento; checklist, tasks, analyze, partition a seguir |
| Verify/review antes de ship | PASS | PASS | etapas pending precedem ship; quickstart fixa os gates executáveis |
| Fail-closed sem waiver | PASS | PASS | suspensão só por mensagem `role=user` da própria sessão, com `id`; forma inválida da frase, fala do agente, resumo, sintética (Claude) e injeção com tag XML (Codex) não mudam nada; pré-requisitos seguem exigidos (C1 do laudo); `STYLE-SCOPE-CONFLICT` permanece; a limitação "primeira mensagem Codex" (R2) só deixa de reconhecer, nunca afrouxa |
| Rastreabilidade | PASS | PASS | FR-001..FR-013 → research R1..R14 → contratos → tarefas; ADR-0001..0003 citados por decisão; achados C1, I1–I3, M1–M5 da R1 mapeados em §Revisão R1 aplicada |
| Tier de modelo e esforço do worker Orca | PASS | PASS | autoria e revisão do plano em worker forte/alto; implementação delimitada em tier intermediário na partition; leitura/teste em tier econômico |
| Bump obrigatório do plugin | NOT-APPLICABLE | NOT-APPLICABLE | plan-only: nenhum byte de `plugin/**` alterado nesta etapa; obrigação registrada para o ship em R13 e no quickstart §5 (patch acima da publicada, 9 pontos incluindo `CHANGELOG.md`; `bump-gate.yml` reprova a PR sem bump) |
| Release obrigatória por versão | NOT-APPLICABLE | NOT-APPLICABLE | plan-only não publica versão, tag nem release; no ship, `publish.yml` cria tag e release ancoradas no push para `main` (R13) |
| Governance | PASS | PASS | Constituição lida somente leitura, hash coincide com `state.json`; nenhuma emenda, nenhum waiver |

Re-check pós-design: sem mudança. Nenhuma violação a justificar.

## Project Structure

### Documentation (this feature)

```text
specs/033-presentation-suspension/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── presentation-suspension.md      # frases de controle, projeção, registro, gate de upgrade, texto do contrato publicado
│   └── native-compaction-records.md    # forma capturada dos registros nativos (Claude e Codex) usada pelos testes
└── tasks.md                             # /speckit-tasks
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py      # _presentation_control (nova, ~15 l.) + project_leader_presentation (~10 l. alteradas)
plugin/skills/grill-with-docs/scripts/grill_workspace.py               # _gauntlet_authorized: bloco morto l.3468-3474 removido (−7)
plugin/skills/grill-with-docs/SKILL.md                                 # §Bootstrap l.32 (FR-012) + heading vX.Y.Z
plugin/skills/grill-with-docs/references/session-protocol.md           # §Apresentação local l.9 (FR-012) + heading vX.Y.Z
plugin/skills/grill-with-docs/references/agent-orchestration.md        # §Apresentação local GWD l.25 (FR-012)
README.md                                                              # l.72 (FR-012) + heading **vX.Y.Z
tests/validate_agent_orchestration_contract.py                         # helper native + 4 testes novos (~115 l.), ao lado de test_presentation_context
tests/validate_task_import_contract.py                                 # caso do gate invertido, último bloco do with em test_same_context_presentation_refresh_preserves_imported_history
plugin/.claude-plugin/plugin.json                                      # versão
plugin/.codex-plugin/plugin.json                                       # versão
.claude-plugin/marketplace.json                                        # versão
.agents/plugins/marketplace.json                                       # versão
tests/validate_distribution.py                                         # VERSION + assert "start adhd mode" por documento (FR-012)
CHANGELOG.md                                                           # heading ## X.Y.Z + entrada da 033 (nono ponto de versão)
```

**Structure Decision**: nenhum módulo, arquivo de produto ou fixture novo. O produtor entra ao lado de `_full_read`, no mesmo módulo que já normaliza o transcript, e é chamado de um único lugar. O helper que constrói mensagens nativas para os cenários (`native(runtime, records)`, ~15 linhas) entra como método da classe de teste do validador de orquestração, que já cobre `_full_read`, `_tool_results` e o adapter. O gate não ganha teste novo: o caso que já existe em `validate_task_import_contract.py` é invertido.

## Arquivos a tocar, estimativa e ordem

| # | Arquivo | Mudança | Linhas (est.) |
|---|---|---|---|
| 1 | `grill_core/agent_runtime.py` | `_presentation_control(messages)` pura, com guarda de `id` (R6); `project_leader_presentation` decide entre suspensa / reativada / fluxo atual | +25 |
| 2 | `grill_workspace.py` | remover o bloco morto l.3468-3474 (comentário de duas linhas, `if` e `raise STYLE-LOAD-UNCONFIRMED`) do gate de upgrade (R7) | −7 |
| 3 | `tests/validate_agent_orchestration_contract.py` | helper `native(runtime, records)`; `test_presentation_control_from_session_user_message`, `test_presentation_suspension_requires_prerequisites`, `test_native_compaction_records_become_compaction_blocks`, `test_presentation_upgrade_during_suspension_keeps_work_ready`; cada cenário roda nos dois runtimes | +115 |
| 4 | `tests/validate_task_import_contract.py` | inverter o caso l.179-185 de `test_same_context_presentation_refresh_preserves_imported_history` e movê-lo para depois da l.217, último bloco do `with`: readiness suspensa com configuração nova **entra** e é persistida (C1; posição e asserções em R7) | ±16 |
| 5 | `SKILL.md` §Bootstrap | parágrafo l.32 reescrito (contracts/presentation-suspension.md §Texto) | ±4 |
| 6 | `references/session-protocol.md` | parágrafo l.9 reescrito (idem) | ±4 |
| 7 | `README.md` | frase da l.72 reescrita (idem) + heading de versão | ±3 |
| 8 | `references/agent-orchestration.md` | frase da l.25 reescrita (idem) | ±2 |
| 9 | 9 pontos de versão | patch acima da versão publicada no ship (R13): os 8 de versão + `CHANGELOG.md` (heading `## X.Y.Z` e entrada da 033) | 9 + entrada |
| 10 | `tests/validate_distribution.py` | `assert "start adhd mode" in text` para `SKILL.md`, `session-protocol.md`, `README.md` e `agent-orchestration.md` (FR-012; R15, M2 da R2) | +4 |

Ordem para partition, três nós:

- **Nó gate** = 2 + 4. Sem dependência: o caso invertido mocka `_session_readiness` e não precisa do produtor. O caso entra depois da l.217 (`footprint() == stable`), porque a projeção suspensa persistida reescreve `orchestrator.json` e o journal, ambos no `footprint()` (R7).
- **Nó produtor** = 1 + 3. **Depende do nó gate**: `test_presentation_upgrade_during_suspension_keeps_work_ready` passa `checkpoint` (decorado com `_gauntlet_authorized`, `grill_workspace.py:6434`) com `config_fingerprint` mudado durante a suspensão, e só sai `exit 0` sem o bloco l.3468-3474.
- **Nó documentação/versão** = 5, 6, 7, 8, 9, 10. Sem dependência; os headings de 5, 6 e 7 são três dos pontos de versão, então os arquivos ficam no mesmo grant. O grant lista explicitamente `CHANGELOG.md` (I2 da R2: `validate_distribution.py:41-43` exige exatamente uma linha `## <VERSION>`, e sem grant o worker não pode escrevê-la) e `tests/validate_distribution.py` (`VERSION` + asserções do FR-012).

Nenhuma linha de tarefa pode conter token com `/` fora de caminho real (aprendizado da 028/029).

## Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Transporte Orca live (`contentComplete=true`) entrega mensagens já normalizadas pelo Orca; a marcação de mensagem sintética/meta nesse caminho não é verificável offline (laudo H3) | uma mensagem sintética cujo texto inteiro seja a frase suspenderia | regra de igualdade exata em bloco único; o fallback local (`_local_transcript` → `_native_messages`) está provado com formato real; risco residual documentado em research R14 |
| Codex: a primeira mensagem digitada da sessão chega como um `response_item` com dois blocos `input_text` (frase + `<environment_context>`), e a regra de bloco único não a reconhece (R2, R10) | `stop adhd mode` como primeira mensagem de uma sessão Codex não suspende; a frase precisa ser repetida numa mensagem posterior | conforme FR-001 (texto extra não conta); limitação declarada em R2/R14 e no contrato; caso negativo no teste com a forma capturada |
| Codex não marca mensagem sintética: injeções do harness (`<environment_context>`, `<codex_internal_context>`, `<hook_prompt>`) chegam como `role=user` e só não suspendem por desigualdade | US3.3 só é testável por marca no Claude (`isMeta`/`isSynthetic`); no Codex o equivalente é a injeção `role=user` com tag XML | igualdade exata; caso negativo Codex com a forma capturada; declarado em R3/R14 |
| Coordenador Orca pode suspender a apresentação de um worker (mensagem `user` do terminal despachado) | comportamento declarado, não defeito | ADR-0001; o texto do contrato (FR-012) passa a dizer isso |
| Editar `SKILL.md` muda `gwd_skill_sha256`: todo contexto ativo exige releitura após instalar a versão nova | igual a qualquer bump; contextos suspensos são exatamente os que esta entrega isenta | comportamento existente; nenhum código novo |
| Codex: ramo `event_msg.user_message` de `_native_messages` sem captura real (0 ocorrências em 591 rollouts da amostra) | ramo permanece sem teste com forma real | não tocar o ramo; testar `response_item` e `compacted`, que são as formas capturadas (R10) |
| Codex antigo pode espelhar a mesma mensagem em `event_msg` e `response_item` | dois registros `user` com a mesma frase; `source_ref` aponta ao último em ordem de arquivo | determinístico; a decisão não muda |
| Suspensão vale por sessão; `_presentation_control` percorre o transcript inteiro (não corta na compactação) | transcript longo: varredura O(n) já paga por `_full_read` | mesma lista, sem leitura adicional |

## Complexity Tracking

Sem violações.

## Revisão R1 aplicada

Revisão independente do plano `@6bfe9e3` (worker `ctx_b903b26f1523`, veredito REQUEST CHANGES). Cada achado → mudança nesta revisão:

| Achado | Mudança |
|---|---|
| **C1** — gate proposto quebrava `tests/validate_task_import_contract.py:179-185` sem o arquivo no grant | `validate_task_import_contract.py` entra no nó gate (§Arquivos, #4); o caso l.179-185 é invertido e movido para o fim do método, depois da l.217 (`self.assertEqual(self.footprint(), stable)`), como último bloco do `with`: readiness suspensa com `config_fingerprint` novo e registro completo → `wrapped(args) == ({'verdict': 'ENTERED'}, 0)`, `entered == [True, True, True]`, contexto persistido com `application=suspended_by_user` e o registro novo, `revision == prior.revision + 1` com `prior = store.read_snapshot(self.root)` lido imediatamente antes do caso (R7; posição e asserções corrigidas por I1 da R2). Nenhum teste novo para o gate |
| **I1** — condição de +1 linha deixava o `raise` morto; contrato atribuía `STYLE-LOAD-UNCONFIRMED` ao gate | decisão registrada em R7: **remover** o bloco `grill_workspace.py:3468-3474` (−7 linhas, comportamento observável idêntico). Atribuição corrigida no Summary, em R7, R11 e na tabela "Gate de upgrade" do contrato: quem recusa `STYLE-LOAD-UNCONFIRMED` é `_session_readiness` (`:1646-1650`, `work_ready=false`); o gate nunca vê esse caso |
| **I2** — forma real Codex: primeira mensagem divide o `response_item` com `<environment_context>`; sem marca de sintética no Codex | R2, R10 e `contracts/native-compaction-records.md` registram as duas formas Codex (um bloco; `plain + environment_context`) e a injeção `role=user` de bloco único com tag XML; limitação "primeira mensagem Codex" em R2, R14, §Riscos e no contrato; caso negativo com os dois blocos em `test_presentation_control_from_session_user_message`; US3.3 declarado como `isMeta`/`isSynthetic` no Claude e injeção `role=user` com tag XML no Codex (R3, quickstart) |
| **I3** — cenários injetavam mensagens normalizadas (forma derivada do código) | R10, data-model e o contrato fixam: **todas** as mensagens injetadas (frase, fala do agente, resumo `isCompactSummary`, `isMeta`/`isSynthetic`, `compact_boundary`, `compacted`, `response_item` Codex nas três formas) são produzidas por `_native_messages(raw, runtime, session_id)` sobre registros mínimos na forma do contrato, via helper `native(runtime, records)` (~15 l., sem arquivo novo), nos dois runtimes, e só então concatenadas ao transcript da fixture |
| **M1** — `message["id"]` sem guarda | `_presentation_control` só conta mensagem com `isinstance(message.get("id"), str) and message["id"]`, espelhando a guarda `isinstance(event_id, str)` de `_full_read` (`agent_runtime.py:1094`; `_tool_results` `:381` só testa truthiness, M3 da R2); registrado em R6, data-model e contrato |
| **M2** — `README.md:72` e `references/agent-orchestration.md:25` com semântica antiga | os dois entram no nó documentação (§Arquivos, #7 e #8) com texto de substituição em `contracts/presentation-suspension.md` §Texto |
| **M3** — política declara `suspend_command`; plano não dizia por que não a toca | R8 registra: `start adhd mode` fica literal no código como `stop` (`agent_runtime.py:275`); a chave é declarativa (nenhum leitor no código) e a política fica intocada porque `policy_sha256` (`grill_workspace.py:1710`) é comparado no gate (`STYLE-SCOPE-CONFLICT`) e toda edição derrubaria contextos abertos |
| **M4** — contrato afirmava enumerações fechadas (variantes, versões, papéis) | `native-compaction-records.md` e R10 marcam contagens como amostra, removem enumerações fechadas e afirmam só o que o normalizador lê (`type`/`subtype`/`sessionId` no Claude; `type`, `payload.id`, `payload.role`, `payload.content[].type/text` no Codex); confirmações do revisor registradas |
| **M5** — Constitution Check divergia do `CONSTITUTION-CHECK.md` do work item | Bump e Release marcadas NOT-APPLICABLE pré e pós-design, com a obrigação registrada para o ship (R13, quickstart §5) |

## Revisão R2 aplicada

Revisão independente do plano `@2f0101d` (worker `ctx_d966d5ec5594`, veredito REQUEST CHANGES; nenhum Critical). Cada achado → mudança nesta revisão:

| Achado | Mudança |
|---|---|
| **I1** — caso invertido do gate, prescrito entre o laço `files.items()` e `stable = self.footprint()`, reprovava adiante no próprio método (l.217, `footprint() == stable`); contrato dizia "fim do método" com `entered == [True, True]`, que também reprova | Posição única nos três lugares (R7, §Revisão R1 aplicada C1, contrato §Gate): **depois da l.217, último bloco do `with`**. Asserções: `wrapped(args) == ({'verdict': 'ENTERED'}, 0)`; `entered == [True, True, True]` (l.196 e l.212 já acrescentaram dois `True`); `revision == prior.revision + 1` com `prior = store.read_snapshot(self.root)` lido imediatamente antes do caso, não `after.revision`. Motivo em R7: a projeção suspensa persistida reescreve `orchestrator.json` e o journal, ambos no `footprint()`. §Arquivos #4 ±16 |
| **I2** — bump tem nove pontos: `validate_distribution.py:41-43` exige `## <VERSION>` em `CHANGELOG.md`, ausente do plano e do grant | `CHANGELOG.md` (heading `## X.Y.Z` + entrada da 033) é o nono ponto em R13, §Arquivos #9, quickstart §5 e no grant do nó de documentação. Summary, Technical Context e Constitution Check dizem "nove". Anotado em R13 e no quickstart §5 que o `CLAUDE.md` da raiz ainda diz "oito lugares" e fica fora desta partition |
| **M1** — caminho errado de `grill_status.py` em R9 | R9 cita `plugin/skills/grill-with-docs/scripts/grill_status.py:174-175` (fora de `grill_core/`) |
| **M2** — FR-012 sem verificação automatizada; FR-006/FR-010 sem teste próprio | R15 novo: `assert "start adhd mode" in text` por documento (`SKILL.md`, `session-protocol.md`, `README.md`, `agent-orchestration.md`) em `tests/validate_distribution.py`, já no nó de documentação (§Arquivos #10, +4; quickstart §2). FR-006 e FR-010 declarados propriedades de ausência cobertas pela suíte inteira (SC-004), sem teste próprio de propósito |
| **M3** — guarda de `id` atribuída a `_tool_results`, que só testa truthiness | R6, data-model e §Revisão R1 aplicada M1: a guarda `isinstance(..., str)` espelha `_full_read` (`agent_runtime.py:1094`); `_tool_results` `:381` citado só como truthiness |
| **M4** — "exatamente um bloco" sem guarda de tipo; `blocks: None` daria `TypeError` fora de `PresentationError`/`RuntimeError` | R2, data-model e contrato: `blocks` lista de exatamente um dict (`isinstance(blocks, list) and len(blocks) == 1 and isinstance(blocks[0], dict)`, como `_tool_results` `:375-377`) e `text` string; malformado é ignorado, nunca exceção |

Sem mudança de produto, de contrato de projeção ou de estrutura da partition: três nós, mesmas dependências.
