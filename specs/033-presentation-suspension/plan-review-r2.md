# Revisão independente R2 — plano 033 (specs/033-presentation-suspension @ 2f0101d)

Revisor: worker `ctx_d966d5ec5594` (distinto dos autores `ctx_a7fda0d81b4e`, `ctx_341f83b17df8` e do revisor R1 `ctx_b903b26f1523`). Read-only: nenhum arquivo do repositório, `.grill/` ou `.specify/` tocado; nenhum commit.

Alvo: `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/presentation-suspension.md`, `contracts/native-compaction-records.md`, conferidos contra `spec.md` (FR-001..013), a revisão R1 (`plan033-review.md`), ADR-0003 do work item e o código em HEAD `2f0101d`: `grill_workspace.py` (`_session_readiness` :1631-1653, `_gauntlet_authorized` :3445-3490, `preflight` :1303-1310, `checkpoint_command` :6434), `agent_runtime.py` (`presentation_state` :180-314, `_tool_results` :371-402, `_native_messages` :620-712, `_full_read` :1071-1104, `project_leader_presentation` :1107-1129), `agent_orchestration.py` (`_presentation` :1108-1149, `require_presentation_work_ready` :1151-1161), `store.py:294`, `tests/validate_task_import_contract.py` :97-217, `tests/validate_agent_orchestration_contract.py` (:188-208, :762-820, :983-987), `tests/orchestration_fixture.py` (:48-88), `tests/validate_distribution.py` :28-44, os quatro documentos do FR-012 e os manifests.

## Findings

### Critical

Nenhum.

### Important

**I1 — O caso invertido do gate, como prescrito em R7, reprova mais adiante no próprio método (`stable`), e plano e contrato divergem sobre onde inseri-lo.**

Evidência:

- `research.md` R7 e `plan.md` §Revisão R1 aplicada mandam mover o caso para **depois** do laço `files.items()` (l.195-208) e asserem `entered == [True, True]` e `revision == after.revision + 1`. Esses dois valores só batem se o caso entra **entre a l.208 e a l.209** (`entered` é `[True]` após a l.197; a l.210 acrescenta o segundo `True`).
- `contracts/presentation-suspension.md` §Gate diz "movido para o **fim do método**". No fim do método `entered` já é `[True, True]` antes do caso, então a asserção prescrita (`[True, True]` depois dele) reprova; seria `[True, True, True]`.
- Inserido entre l.208 e l.209, o caso persiste no contexto a projeção suspensa com `config_fingerprint=<valor novo>`. A l.209 captura `stable = self.footprint()` **com** esse estado; `footprint()` (`validate_task_import_contract.py:97-99`) inclui `.git/grill/`. A l.210 chama `wrapped(args)` sem mock: `_session_readiness` real devolve `fresh` (ativa, fingerprint derivado de `'d'*64`), que difere da suspensa persistida em `config_fingerprint` → bloco removido → `context["presentation"] != readiness["presentation"]` → `store.transact(refresh)` reescreve `orchestrator.json` e o journal. A l.217 `self.assertEqual(self.footprint(), stable)` reprova.

Correção (menor diff): inserir o caso **depois da l.217**, como último bloco do `with`, e prescrever: `entered == [True, True, True]`; `revision` comparado a um snapshot lido imediatamente antes do caso (`store.read_snapshot(self.root).revision + 1`), não a `after.revision`; contrato, R7 e §Revisão R1 aplicada com o mesmo texto ("fim do método, depois de `footprint() == stable`"). Alternativa: manter entre l.208-209 e, ao final do caso, restaurar o contexto (`wrapped(args)` sem mock, reprojeta `fresh`) **antes** da l.209 — mais linhas, sem ganho.

**I2 — O bump tem nove pontos, não oito: `CHANGELOG.md` é fixado pelo validador e não está em nenhum grant.**

Evidência: `tests/validate_distribution.py:41-43` lê `CHANGELOG.md` e exige exatamente uma linha `## {VERSION}` (pin desde `b3ed20e`, 5.2.1). `CHANGELOG.md:3` é `## 6.0.28` hoje. O plano (§Technical Context, §Arquivos #9, R13, quickstart §5, Constitution Check) e o `CLAUDE.md` do repositório dizem "oito pontos"; o nó documentação/versão da partition lista SKILL.md, session-protocol.md, README.md, agent-orchestration.md, os quatro manifests e `validate_distribution.py`, sem `CHANGELOG.md`. Quem fizer o bump (nó de documentação ou etapa ship) roda `python3 tests/validate_distribution.py` e reprova em `("CHANGELOG.md", "6.0.31", [])` até acrescentar a entrada — e, se for o worker do nó, sem grant sobre o arquivo.

Correção: registrar `CHANGELOG.md` (heading `## X.Y.Z` + entrada da 033) como nono ponto em R13, §Arquivos #9, quickstart §5 e no grant do nó de documentação. O `CLAUDE.md` da raiz também está desatualizado ("oito lugares"), mas corrigi-lo é fora do escopo desta partition; vale anotar em R13.

### Minor

**M1 — Caminho errado em R9.** `grill_status.py` vive em `plugin/skills/grill-with-docs/scripts/grill_status.py` (l.174-175 confere: copia `context["presentation"]` inteira), não em `grill_core/`. Só afeta rastreabilidade.

**M2 — FR-012 sem verificação automatizada; custo de três linhas no arquivo já em grant.** Nenhum validador lê o texto dos quatro documentos (`grep adhd tests/*.py` só acha o nome do plugin `i-have-adhd`). `validate_distribution.py` já abre `SKILL.md`, `session-protocol.md` e `README.md` (l.31-33) e está no nó de documentação: um `assert "start adhd mode" in text` por documento (mais `agent-orchestration.md`) fixa o FR-012 e evita que um bump futuro apague a frase sem reprovar. FR-006 e FR-010 também não têm teste próprio; são propriedades de ausência (nenhuma flag; nenhum código novo) e a suíte inteira as cobre — aceitável, mas dizer isso no plano.

**M3 — R6/data-model atribuem a guarda de `id` a `_tool_results`, que só testa truthiness.** `_tool_results` (`agent_runtime.py:381`) usa `message.get("id")`; quem exige `isinstance(event_id, str)` é `_full_read` (`:1094`). A guarda prescrita (`isinstance(...str) and message["id"]`) é a certa; só a citação está deslocada.

**M4 — A regra "exatamente um bloco" precisa da guarda de tipo explícita.** No transporte Orca live (`contentComplete=true`) as mensagens já vêm normalizadas pelo Orca; `_tool_results` (`:375-377`) checa `isinstance(blocks, list)` e `isinstance(blocks[0], dict)` antes de `len`. R2 e o data-model descrevem só a cardinalidade; um `blocks: None` daria `TypeError` fora de `PresentationError`/`RuntimeError`, mesma classe de vazamento que M1 da R1 fechou para `id`. Uma frase em R2 ("blocks lista de um dict") basta para o worker.

## Verificação dos achados R1

| R1 | Fechado? | Evidência no código / nos artefatos |
|---|---|---|
| **C1** grant + teste do gate | Sim, com ressalva I1 | `validate_task_import_contract.py` entrou no nó gate (§Arquivos #4). Confirmado que, sem o bloco, o caso l.179-185 atual reprovaria: `_presentation` (`agent_orchestration.py:1140-1143`) aceita `work_ready ∧ suspended_by_user ∧ suspension≠None`, nada mais recusa, o handler roda e `entered == []` (l.195) falha. A inversão prescrita tem o defeito de posição descrito em I1 |
| **I1** bloco morto / atribuição | Sim | Decisão de remoção em R7; `:3468-3474` são exatamente 7 linhas (2 comentário, 3 `if`, 2 `raise`). Atribuição corrigida no Summary, R7, R11 e tabela do contrato |
| **I2** formas Codex | Sim | R2, R10, R14, §Riscos e `native-compaction-records.md` registram bloco único e `(plain, <environment_context>)`, a forma de três blocos, injeção `role=user` com tag XML e a limitação "primeira mensagem Codex"; caso negativo previsto no teste; US3.3 diferenciado por runtime |
| **I3** mensagens nativas em todos os cenários | Sim | R10, data-model e os dois contratos fixam `native(runtime, records)` → `_native_messages` para todas as mensagens injetadas; só o `tool_pair` da fixture (preflight+cat) fica literal, como a R1 aceitou |
| **M1** guarda de `id` | Sim (ver M3 aqui) | R6, data-model e contrato |
| **M2** README/agent-orchestration | Sim | #7 e #8 no nó documentação; âncoras verbatim conferidas: `README.md:72`, `agent-orchestration.md:25`, `session-protocol.md:9`, `SKILL.md:32` (trecho de "documentado na mesma…" até "exigem nova leitura." existe, uma ocorrência) |
| **M3** política | Sim | R8; `agent-orchestration.v1.json:67` tem `suspend_command`; `policy_sha256` em `:1710` e comparado em `:3465-3467` |
| **M4** enumerações | Sim | contrato e R10 marcam amostra e limitam ao que o normalizador lê |
| **M5** Constitution Check | Sim | NOT-APPLICABLE pré/pós, coincide com `CONSTITUTION-CHECK.md` l.97-106 do work item |

## Remoção do bloco `:3468-3474` (FR-010)

- **Inalcançável hoje**: `presentation_state` calcula `use_ready = prerequisites ∧ loaded ∧ active` e `work_ready = prerequisites ∧ (use_ready ∨ (suspended_by_user ∧ valid_suspension))` (`:286-287`); `project_leader_presentation` nunca passa `application`/`suspension` (`:1118-1126`), logo `work_ready ⇒ use_ready` e `_session_readiness` já recusou `work_ready=false` em `:1649`. A condição `¬use_ready` no gate nunca é verdadeira em produção.
- **Único teste que o alcança**: `validate_task_import_contract.py:179-185`, via mock — o caso que o plano inverte. `grep "upgrade requires a fresh full read" tests/` → 0. Os casos do laço l.154-160 (`use_ready=False`, `loading='stale'` etc.) já reprovam no validador `_presentation` chamado em `:3462` ("invalid presentation work_ready/use_ready"), não no bloco.
- **Códigos**: `STYLE-LOAD-UNCONFIRMED` continua emitido por `presentation_state` (`:273`) e propagado por `_session_readiness` (`:1649`, com `extra.presentation`) e por `require_presentation_work_ready` (`:1160`); `STYLE-SCOPE-CONFLICT` em `:3465-3467` e `:1648` intacto. Nenhum verbo além do bloco lê `use_ready` (`grep use_ready grill_workspace.py store.py agent_orchestration.py`): `init`, `adopt`, `step-enter` (`:5597`), `store.py:294` e `agent_orchestration.py:510` só exigem `work_ready`, então a sessão suspensa entra em todos.
- Conclusão: remover não muda comportamento observável nem significado de código. FR-010 atendido.

## Regressões novas

Nenhuma no produto. As duas encontradas são do plano (I1: teste prescrito reprova; I2: bump incompleto) e estão acima. Conferido ainda:

- `_presentation` aceita `loading == "stale"` e `suspension` dict JSON (`:1130-1143`); checkpoint v2 carrega `context.presentation` inteiro (`:1958`, `:3806`), então `suspension` aninhado entra no `checkpoint_sha256` sem schema novo.
- `preflight` (`:1303-1310`) anexa a projeção de `_session_readiness`; com `work_ready=true` o verdict segue o de dependências — a asserção `verdict=OK` do teste (R9) está certa.
- `run_cli` do validador é in-process (`:983-987`), então `mock.patch.object(_leader_boundary…)` alcança o `checkpoint` — o desenho de `test_presentation_upgrade_during_suspension_keeps_work_ready` é viável.
- Fixture `boundary` (`orchestration_fixture.py:55-88`) expõe `transcript["result"]["transcript"]["messages"]` como lista mutável em transporte `contentComplete=true`, sem alteração necessária.
- `_native_messages` confere linha a linha com a tabela de asserções do contrato: `compacted` → `system/compaction` com `native:<n>` (`:637-638`, id em `:627`); `response_item.message` → `payload.role`/`content` (`:640-644`), `payload.id` ausente → `native:<n>`; `input_text`/`output_text` → `text` (`:696-699`); Claude `isMeta/isSynthetic/isCompactSummary` → `system` (`:680-681`); `compact_boundary` → `compaction` (`:682-683`); `content` string → um bloco (`:678-679`); `user` só com `tool-result` → `tool` (`:709-710`). Ramo `event_msg.user_message` (`:661-664`) existe e fica sem teste, como declarado.
- R5: `_full_read` recalcula o corte de compactação sobre a lista que recebe (`:1075-1079`), então passar `messages[start+1:]` compõe com o corte sem código extra.
- Versão: 6.0.28 nos oito pontos; `origin/main` publica 6.0.30 e não é ancestral de HEAD; alvo 6.0.31 correto (mais o CHANGELOG, I2).

## FR-001..013 — caminho e teste

| FR | Onde | Teste |
|---|---|---|
| 001 | R2; `_presentation_control` em `agent_runtime.py` | `test_presentation_control_from_session_user_message` (2 runtimes; espaços, texto extra, caixa, dois blocos Codex) |
| 002 | R4, R12; `project_leader_presentation` suspensa sem `_full_read` | cenários 1-2 (US1.1/1.2); `test_presentation_suspension_requires_prerequisites` (US1.4) |
| 003 | R5; fatiamento `messages[start+1:]` | cenário 3 (US2.1); US2.2; edge `start` sem `stop` |
| 004 | R3; `_native_messages` já rebaixa/descarta | cenário 4 (US3.1-3), por runtime |
| 005 | R6; registro | US1.3 (`source_ref` termina no id) |
| 006 | R8; nenhuma flag | sem teste próprio (propriedade de ausência; ver M2) |
| 007 | R7; remoção `:3468-3474` | `validate_task_import_contract.py` caso invertido (I1) + `test_presentation_upgrade_during_suspension_keeps_work_ready` (US4.1); US4.2 `STYLE-SCOPE-CONFLICT` |
| 008 | R4, R10 | cenário 6 (US5.1); `test_native_compaction_records_become_compaction_blocks` (US5.2) |
| 009 | R1/R14; transcript novo | cenário 7 (US2.3) |
| 010 | R11; nenhum código novo | suíte completa (SC-004); sem teste próprio |
| 011 | R10; helper `native` | todos os cenários, 2 runtimes |
| 012 | contrato §Texto; 4 documentos | nenhum (M2) |
| 013 | R9; dict inteiro repassado | asserção `preflight` em `test_presentation_upgrade_during_suspension_keeps_work_ready` |

## Grants por nó

| Nó | Arquivos no grant | Cobre tudo? |
|---|---|---|
| gate | `grill_workspace.py`, `tests/validate_task_import_contract.py` | Sim |
| produtor (depende do gate) | `grill_core/agent_runtime.py`, `tests/validate_agent_orchestration_contract.py` | Sim; fixture não muda; dependência do gate correta (o `checkpoint` do teste passa por `_gauntlet_authorized`, `:6434`) |
| documentação/versão | `SKILL.md`, `session-protocol.md`, `agent-orchestration.md`, `README.md`, 4 manifests, `tests/validate_distribution.py` | **Não**: falta `CHANGELOG.md` (I2). Com M2, `validate_distribution.py` já está no grant |

Nenhum token com `/` fora de caminho real nas linhas de tarefa previstas — a regra está no plano; conferir no `partition-emit` em preview, como o CLAUDE.md pede.

## Verdict

**REQUEST CHANGES** — pequenas e localizadas. I1 corrige a posição e as asserções do caso invertido (R7, §Revisão R1 aplicada, contrato §Gate) para que o teste prescrito passe; I2 acrescenta `CHANGELOG.md` como nono ponto de versão e ao grant do nó de documentação. Sem esses dois, o worker do nó gate ou o ship reprova a suíte seguindo o plano ao pé da letra. M1-M4 podem ir no mesmo passe. Produto, contratos, FR-010 e a estrutura da partition estão corretos; com I1 e I2 aplicados, aprovado para `checklist`/`tasks`.
