<!-- grill-task-files:v1 -->

# Tasks: Suspensão e reativação da apresentação local no core

**Input**: Design documents de `specs/033-presentation-suspension/` (spec.md, plan.md r3, research.md R1..R15, data-model.md, quickstart.md, contracts de suspensão e de registros nativos, checklists)

**Prerequisites**: plan.md atestado (`203d85a`), checklist atestado (`10ab88b`); work item `fix-presentation-suspension-d97e4c3d7b434c119477ec59d56ecbd5`, ADR-0001..0003

**Tests**: obrigatórios (FR-011, SC-001..SC-004). Hoje o defeito não é coberto: nenhum produtor de suspensão existe e a tradução dos registros nativos de compactação não tem teste. Toda mensagem injetada nos cenários nasce de `_native_messages` sobre registros mínimos na forma capturada de sessões reais de Claude Code e Codex, nunca de literal normalizado (Research R10, I3 da R1). Nenhum teste toca rede, runtime real ou processo externo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos disjuntos, sem dependência pendente). Nesta entrega nenhuma fase tem duas tarefas: cada fase é um nó, e a paralelização é entre workers de nós distintos, não dentro da fase.
- **[Story]**: US1..US5 do `spec.md`.
- Contrato `task-files/v1`: o grant de cada tarefa é exatamente a lista `Files:` da linha seguinte; a prosa da descrição não concede nada. Mesmo assim, nenhuma palavra das linhas de tarefa contém barra fora de caminho real (aprendizado da 028 e da 029).
- Toda tarefa despachável declara `Result:` em `specs/033-presentation-suspension/implement/<TID>.tasks.json`, também presente em `Files:`.
- Nenhuma tarefa escreve na reserva de evidência do líder. Os checkpoints de fase abaixo são prosa executada pelo líder ou pelo worker antes do resultado, não tarefas read-only, para não abrir pendência de aceite fora do scheduler.

## Path Conventions

Repositório existente, nenhum módulo, arquivo de produto ou fixture novo (plan.md §Structure Decision). Arquivos tocados (14): dois pontos do core (`grill_core/agent_runtime.py` e `grill_workspace.py`), dois validadores existentes, quatro documentos de contrato publicado, quatro manifests, o validador de distribuição e `CHANGELOG.md`. Os três nós seguem plan.md §Ordem para partition: gate, produtor (depende do gate) e documentação com versão (sem dependência, mas última por ser a tarefa de bump).

**Versão**: patch acima da versão publicada no momento do ship, nos nove pontos (Research R13, I2 da R2). Hoje a `main` remota publica 6.0.30, logo o alvo provisório é 6.0.31; o número é confirmado no ship com `git show` do manifesto Claude na `main` remota, e se a `main` avançar antes disso o alvo passa a ser a publicada mais um. O `CLAUDE.md` da raiz ainda diz "oito lugares" e não é corrigido nesta entrega.

---

## Phase 1: Gate de upgrade sob suspensão

**Purpose**: Deixar o gate de `_gauntlet_authorized` sem a recusa que, com o produtor, seria exatamente a errada (ADR-0003, Research R7). Sem dependência: o caso invertido mocka `_session_readiness` e não precisa do produtor. O nó produtor da Phase 2 depende deste nó, porque `test_presentation_upgrade_during_suspension_keeps_work_ready` passa `checkpoint` pelo gate com `config_fingerprint` mudado e só sai exit 0 sem o bloco removido aqui.

- [ ] T001 [US4] Em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, no decorador `_gauntlet_authorized`, remover o bloco morto das linhas 3468-3474 (as duas linhas de comentário, o `if` que compara `config_fingerprint` e `gwd_skill_sha256` sem `use_ready`, e o `raise` de `STYLE-LOAD-UNCONFIRMED`), mantendo intactos `require_presentation_work_ready`, a comparação de `session_identity`, `runtime`, `scope` e `policy_sha256` que recusa `STYLE-SCOPE-CONFLICT` e o refresh que grava `readiness["presentation"]` no contexto quando ela muda; nenhum código de recusa muda de significado, porque quem emite `STYLE-LOAD-UNCONFIRMED` para apresentação ativa e não lida continua sendo a projeção lida por `_session_readiness`. E em `tests/validate_task_import_contract.py`, método `test_same_context_presentation_refresh_preserves_imported_history`, inverter o caso das linhas 179-185 (que hoje assere `STYLE-LOAD-UNCONFIRMED` para uma readiness mockada suspensa) e movê-lo para depois da linha 217 (`self.assertEqual(self.footprint(), stable)`), como último bloco do `with`, porque a projeção suspensa persistida reescreve o documento do Store e o journal, ambos no `footprint()`: `suspended = copy.deepcopy(fresh)` com `use_ready=False`, `application='suspended_by_user'`, `loading='stale'`, `config_fingerprint` com valor novo e `suspension` completa (`command` igual a `stop adhd mode`, `source_ref`, `source_sha256` hexadecimal de 64 caracteres, `session_identity` e `scope` copiados de `fresh`, o mesmo `config_fingerprint` novo); `prior = store.read_snapshot(self.root)` lido imediatamente antes do caso; com `_session_readiness` mockado para `suspended`, asserir `wrapped(args) == ({'verdict': 'ENTERED'}, 0)`, `entered == [True, True, True]`, o contexto `ctx-epoch16` do snapshot novo com `presentation == suspended['presentation']` e `revision == prior.revision + 1`; nenhum teste novo para o gate e nenhum caso existente afrouxado (FR-007, FR-010, US4.1, US4.2, ADR-0003, Research R7, R11, Contract §Gate de upgrade, C1 e I1 da R1, I1 da R2)
  Files: ["plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_task_import_contract.py", "specs/033-presentation-suspension/implement/T001.tasks.json"]
  Result: "specs/033-presentation-suspension/implement/T001.tasks.json"

**Checkpoint** (quickstart 1 e 2): antes de tocar código, `python3 tests/validate_agent_orchestration_contract.py` e `python3 tests/validate_task_import_contract.py` passam (baseline). Depois: `python3 tests/validate_task_import_contract.py -k same_context_presentation_refresh` fecha em exit 0 com o caso invertido; `python3 tests/validate_agent_orchestration_contract.py` continua verde sem edição de teste; `python3 tests/run_validators.py` fecha em exit 0.

---

## Phase 2: Produtor da suspensão e cobertura com forma nativa

**Purpose**: O único produtor de suspensão do core, no único ponto que observa a sessão, e os quatro testes que provam os sete cenários do handoff nos dois runtimes. Depende da Phase 1 (barreira): o teste de upgrade durante a suspensão atravessa o gate.

- [ ] T002 [US1] [US2] [US3] [US4] [US5] Em `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, ao lado de `_full_read`, acrescentar a função pura `_presentation_control(messages) -> tuple[int, int, dict | None]`, que percorre a lista normalizada inteira sem cortar na compactação e devolve o índice da última `stop adhd mode`, o índice da última `start adhd mode` e a mensagem da última frase (`-1, -1, None` na ausência); só conta mensagem com `role == "user"`, `id` string não vazio (`isinstance(message.get("id"), str) and message["id"]`, espelhando a guarda de `_full_read`), `blocks` lista de exatamente um dict (`isinstance(blocks, list) and len(blocks) == 1 and isinstance(blocks[0], dict)`), bloco de `type` igual a `text`, `text` string e `text.strip()` igual à frase, sensível a caixa; `id` ausente, `blocks` malformado, texto extra, bloco extra ou caixa diferente são ignorados, nunca exceção. Em `project_leader_presentation`, decidir após montar `kwargs`: `stop > start` projeta `presentation_state(**kwargs, application="suspended_by_user", loading={"stale": True}, suspension=registro)` sem chamar `_full_read`, com registro `command` igual a `stop adhd mode`, `source_ref` igual a `observed["source_ref"] + ":" + message["id"]`, `source_sha256` igual ao sha256 do texto do bloco antes do `strip()`, `session_identity` igual a `leader_session_identity(observed)`, `config_fingerprint` corrente e `scope` da observação, reconstruído a cada observação para que um upgrade aponte a configuração nova; `start > stop >= 0` segue o fluxo atual com `_full_read` sobre `messages[start + 1:]`; `stop == -1` segue o fluxo atual inalterado (inclui `start` sem `stop` anterior); `presentation_state` mantém assinatura e pureza, nenhum verbo ganha flag ou campo de suspensão e a política `agent-orchestration.v1.json` não é tocada. E em `tests/validate_agent_orchestration_contract.py`, ao lado de `test_presentation_context`: helper `native(runtime, records, session_id)` como método da classe (cerca de 15 linhas), que serializa uma linha JSON por registro mínimo na forma capturada do contrato de registros nativos (no Codex, `session_meta` com `payload.id == session_id` prefixado) e devolve `_native_messages(raw, runtime, session_id)`; e quatro testes, cada cenário em `subTest(runtime=...)` para Claude e Codex, com toda mensagem injetada nascendo do helper e concatenada às `messages` de `orchestration_fixture.boundary`: `test_presentation_control_from_session_user_message` (stop suspende sem recarga: `application=suspended_by_user`, `loading=stale`, `work_ready=true`, `use_ready=false`, `load_request` ausente e `suspension.source_ref` terminando no id da mensagem; stop seguido de compactação segue suspensa; start reativa, exige leitura integral posterior à frase e leitura anterior não conta; alternância entre as frases vale a última; frase só em `assistant`, só em resumo `isCompactSummary`, só em `isMeta` ou `isSynthetic` no Claude e só em injeção `role=user` iniciada por tag XML no Codex não muda nada; espaços nas pontas contam; texto extra, caixa diferente, mensagem `user` sem `id`, `blocks` malformado e a forma Codex de dois blocos `input_text` não contam; start sem stop não fatia; boundary nova começa ativa), `test_presentation_suspension_requires_prerequisites` (frase presente e adapter com `enablement.state` igual a `disabled`, depois `installation.status` igual a `missing` e `trust.state` igual a `pending`: `application=suspended_by_user`, `work_ready=false` e o primeiro diagnóstico nomeia o pré-requisito), `test_native_compaction_records_become_compaction_blocks` (tradução isolada conforme a tabela de asserções do contrato de registros nativos: `compact_boundary` e `compacted` nas duas variantes de chaves viram `role` igual a `system` com um único bloco `compaction` e nenhum texto de `replacement_history` ou `retained_context` na lista; `isCompactSummary`, `isMeta` e `isSynthetic` viram `system`; mensagem digitada vira `user` com um bloco `text`; `response_item` sem `payload.id` recebe id `native:<n>`; dois `input_text` viram dois blocos; `developer` e `assistant` preservam o papel) e `test_presentation_upgrade_during_suspension_keeps_work_ready` (`preflight` com `--session-ref` e a frase no transcript devolve exit 0, `verdict=OK`, `application=suspended_by_user`, `use_ready=false`, `work_ready=true`, `suspension` presente e `load_request` ausente; `checkpoint` com `config_fingerprint` mudado devolve exit 0 e o contexto gravado traz o registro com a configuração nova; mudança de sessão, runtime, escopo ou política continua `STYLE-SCOPE-CONFLICT`); a fixture `orchestration_fixture` não muda, o ramo `event_msg` de `user_message` fica intocado por não ter captura real, e nenhum caso existente é afrouxado (FR-001..FR-009, FR-011, FR-013, SC-001..SC-003, ADR-0001, ADR-0002, Research R1..R6, R9, R10, R12, R14, Contract §Frases de controle, §Projeção, §Registro de suspensão, Data model, quickstart 2 e 3)
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py", "tests/validate_agent_orchestration_contract.py", "specs/033-presentation-suspension/implement/T002.tasks.json"]
  Result: "specs/033-presentation-suspension/implement/T002.tasks.json"

**Checkpoint** (quickstart 2, 3 e 4): `python3 tests/validate_agent_orchestration_contract.py -k presentation_control -k suspension -k native_compaction -k upgrade_during_suspension` fecha em exit 0 nos dois runtimes; `python3 tests/validate_agent_orchestration_contract.py -k upgrade_during_suspension` prova FR-013 e SC-003; `python3 tests/run_validators.py` fecha em exit 0 (31 validadores pelo marcador `==>`); `git diff --check` limpo.

---

## Phase 3: Contrato publicado e versão

**Purpose**: Os quatro documentos do FR-012, o bump patch nos nove pontos e a asserção que trava a frase de reativação na distribuição. Última fase por ser a tarefa de versão: o número é confirmado no ship. Os headings de `SKILL.md`, `session-protocol.md` e `README.md` são três dos pontos de versão, então os documentos e o bump ficam no mesmo grant.

- [ ] T003 [US1] [US2] Substituir, pelo texto fixado no contrato de suspensão desta spec (`presentation-suspension`, §Texto do contrato publicado), os quatro trechos que ainda descrevem a semântica antiga: em `plugin/skills/grill-with-docs/SKILL.md` §Bootstrap de apresentação obrigatório (linha 32, do trecho que começa em `stop adhd mode` documentado até o final em exigem nova leitura), em `plugin/skills/grill-with-docs/references/session-protocol.md` §Apresentação local obrigatória (linha 9, da frase que começa em `stop adhd mode` é a única suspensão local até a sessão nova não herda essa suspensão), em `README.md` (linha 72, a frase que começa em `stop adhd mode` suspende somente a apresentação) e em `plugin/skills/grill-with-docs/references/agent-orchestration.md` §Apresentação local GWD (linha 25, a frase que começa em `stop adhd mode` suspende somente a apresentação); os quatro passam a declarar fonte não-agente da própria sessão como conteúdo único de mensagem de usuário, o coordenador Orca como fonte possível num despacho, a sobrevivência da suspensão a compactação, upgrade e mudança de configuração, e `start adhd mode` como reativação explícita que exige leitura integral posterior à frase. Fazer o bump patch acima da versão publicada (alvo provisório 6.0.31 sobre a 6.0.30 publicada hoje; número confirmado no ship com `git show` do manifesto Claude na `main` remota) nos nove pontos: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, constante `VERSION` em `tests/validate_distribution.py`, heading `# Grill with Docs vX.Y.Z` em `plugin/skills/grill-with-docs/SKILL.md`, heading `# Protocolo de sessão vX.Y.Z` em `plugin/skills/grill-with-docs/references/session-protocol.md`, heading `**vX.Y.Z` em `README.md` e, em `CHANGELOG.md`, exatamente uma linha `## X.Y.Z` acima da entrada mais recente, seguida da entrada da 033 (produtor de suspensão e reativação a partir de mensagem de usuário da própria sessão, com `start adhd mode` e sobrevivência a compactação e upgrade; gate de upgrade liberado sob suspensão válida; contrato publicado com fonte não-agente; testes com a forma nativa capturada de Claude Code e Codex); e em `tests/validate_distribution.py` acrescentar, para cada um dos quatro documentos acima, `assert "start adhd mode" in text, path`, ao lado da verificação de headings; a política `agent-orchestration.v1.json` e o `CLAUDE.md` da raiz não mudam (FR-012, SC-004, Research R8, R13, R15, Contract §Texto do contrato publicado, M2 e M3 da R1, I2 e M2 da R2, quickstart 5)
  Files: ["plugin/skills/grill-with-docs/SKILL.md", "plugin/skills/grill-with-docs/references/session-protocol.md", "plugin/skills/grill-with-docs/references/agent-orchestration.md", "README.md", "CHANGELOG.md", "plugin/.claude-plugin/plugin.json", "plugin/.codex-plugin/plugin.json", ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json", "tests/validate_distribution.py", "specs/033-presentation-suspension/implement/T003.tasks.json"]
  Result: "specs/033-presentation-suspension/implement/T003.tasks.json"

**Checkpoint** (quickstart 2, 4 e 5): `python3 tests/validate_distribution.py` imprime `distribution: OK` só depois dos nove pontos e das quatro asserções, por isso roda no fim deste nó e não antes; os nove pontos concordam entre si; `python3 tests/run_validators.py` fecha em exit 0 (31 validadores); `git diff --check` limpo. No ship, o número final é reconfirmado contra a `main` remota e `bump-gate.yml` reprova a PR sem bump.

---

## Dependencies

```
Phase 1 (T001, nó gate)                       barreira
        ↓
Phase 2 (T002, nó produtor; depende do gate)  barreira
        ↓
Phase 3 (T003, nó documentação e versão)
```

- T002 depende de T001: `test_presentation_upgrade_during_suspension_keeps_work_ready` passa `checkpoint` pelo decorador `_gauntlet_authorized` com `config_fingerprint` mudado durante a suspensão e só sai exit 0 sem o bloco que T001 remove.
- T003 não depende de T001 nem de T002 pelo código, mas é a tarefa de versão e por isso fecha a sequência; a asserção de `start adhd mode` em `tests/validate_distribution.py` só fica verde com os quatro documentos e o bump completos no mesmo nó.
- Nenhuma tarefa é deferida ao líder e nenhuma é read-only.

## Parallel opportunities

- Nenhuma dentro de fase: cada fase tem um único nó com arquivos que se exigem mutuamente (o caso invertido não passa sem a remoção do bloco; os testes do produtor não passam sem o produtor; a asserção de distribuição não passa sem documentos e bump). Dividir qualquer nó em dois workers daria a um deles uma suíte que não fecha no próprio worktree.
- O paralelismo desta entrega é a independência do nó de documentação, que o `partition` pode escalonar assim que a barreira da Phase 2 fechar, sem esperar revisão de código.

## Independent test criteria

- **US1**: stop suspende sem recarga, antes e depois de compactação; `suspension.source_ref` identifica a mensagem; pré-requisito ausente derruba `work_ready` com diagnóstico nomeado (T002).
- **US2**: start reativa e exige leitura posterior; alternância vale a última; boundary nova começa ativa (T002).
- **US3**: frase em fala do agente, em resumo de compactação e em mensagem sintética ou injeção do harness não muda nada, nos dois runtimes (T002).
- **US4**: upgrade durante a suspensão libera e grava o registro novo (T001 pelo gate, T002 pelo CLI); mudança de sessão, runtime, escopo ou política continua `STYLE-SCOPE-CONFLICT` (T001, T002).
- **US5**: compactação sem suspensão continua exigindo leitura; `compact_boundary` e `compacted` no formato real viram bloco de compactação (T002).
- **FR-012**: os quatro documentos nomeiam `start adhd mode` e a fonte não-agente, travados por asserção na distribuição (T003).

## Implementation strategy

MVP = Phase 1 mais Phase 2: a suspensão passa a existir no core, atravessa compactação e upgrade, e os sete cenários do handoff passam nos dois runtimes (SC-001). A Phase 3 cumpre FR-012 e a obrigação constitucional de bump e release, com o número resolvido no ship.
