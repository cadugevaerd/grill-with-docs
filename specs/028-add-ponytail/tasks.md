---

description: "Task list for 028 — ponytail na stack oficial"
---

# Tasks: Ponytail na stack oficial

**Input**: Design documents from `/specs/028-add-ponytail/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: obrigatórios. SC-001, SC-003 e SC-004 só são verificáveis por teste, e a
CI não tem `claude`, `codex` nem rede — as fixtures são a única prova possível.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos disjuntos, sem dependência pendente)
- **[Story]**: US1..US3 do `spec.md`
- Todo caminho é repo-relativo e explícito, porque o `partition` só fenceia o que
  a linha nomeia

## Path Conventions

Repositório existente, sem estrutura nova. Arquivos tocados (13): o detector e o
manifesto do plugin, o validador de dependências, os oito pontos de versão, mais
`CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` e `CHANGELOG.md`.

**Fronteira conhecida do `partition`**: um token só é reconhecido como caminho
quando contém `/`. `CLAUDE.md`, `AGENTS.md`, `README.md` e `CHANGELOG.md` estão na
raiz e são, por construção, infenceáveis para um worker. Eles são trabalho do
**leader**, e a Phase 3 os declara como tal nomeando um caminho de evidência de
coordenador — não é contorno, é a única atribuição honesta que a ferramenta
permite.

---

## Phase 1: Fundação — manifesto e detector

**Purpose**: O kind novo, a entrada nova e a leitura por runtime. As quatro
tarefas tocam `ensure_dependencies.py` ou `dependencies.json`; T002..T004
escrevem o mesmo arquivo e formam um grupo de conflito único: são serializadas
de propósito.

- [ ] T001 [P] Acrescentar a entrada `ponytail` (`kind: harness-plugin`, `required: true`, `plugin`, `marketplace`, `marketplace_source`, `min: 4.9.0`, `owner`, `reason`, `install_by_runtime` com as duas sequências) em `plugin/skills/grill-with-docs/assets/dependencies.json`, exatamente como em `specs/028-add-ponytail/contracts/dependency-manifest-entry.md`, sem tocar as entradas existentes (FR-001, FR-004, Contract manifest-entry)
- [ ] T002 [P] Acrescentar `"harness-plugin"` a `KINDS` e estender `load_manifest` em `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py` para validar `install_by_runtime` (chaves ⊆ `RUNTIMES`, valores lista de argv de strings; erro `invalid install command for <id>`) e exigir `plugin` e `marketplace` em entradas `harness-plugin` (erro `invalid harness-plugin entry for <id>`) (Contract manifest-entry, Data model §Dependência declarada)
- [ ] T003 Implementar `declared_install(entry, runtime)` em `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py` — devolve `install_by_runtime[runtime]` quando existe, senão `install` — e usá-lo em `remediation()` e em `install()` no lugar de `entry.get("install")`, preservando o tratamento de `enable` das extensões (FR-004, FR-005, FR-006, Research R4)
- [ ] T004 Implementar `plugin_registry_state(entry, tools, runtime)` e o ramo `harness-plugin` de `detect()` em `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py`: raiz por `CLAUDE_CONFIG_DIR` ou `CODEX_HOME` com fallback ao subdiretório `.claude` ou `.codex` do `HOME` via `tools.environ`; Claude lê o arquivo `installed_plugins.json` do diretório `plugins`, chave `plugins["<plugin>@<marketplace>"][0].version`; Codex escolhe a maior versão entre os subdiretórios do cache de plugins (`<marketplace>`, `<plugin>`, `<versão>`) que contêm `.codex-plugin` com `plugin.json`; arquivo ou chave ausente → `missing`, ilegível → `undetermined` com `reason` `registro de plugins ilegivel: <path>`, `meets(min)` decide `present` ou `outdated` com `reason` `versao <v> abaixo do minimo <min>`; `source` = caminho lido; nenhuma chamada a `tools.run` (FR-002, FR-003, Research R1, R2, R5, Contract dependency-report)

**Checkpoint**: `python3 plugin/skills/grill-with-docs/scripts/ensure_dependencies.py . --runtime claude`
lista `ponytail` como `present` `4.9.0` nesta máquina; nenhum outro item muda.

---

## Phase 2: Cobertura e distribuição

**Purpose**: Travar o comportamento por fixture e sincronizar a versão. Grupos de
conflito disjuntos — o `partition` empacota em bins paralelos.

- [ ] T005 [P] [US1] Acrescentar em `tests/validate_dependencies_contract.py` os casos de detecção `harness-plugin` para `--runtime claude` com `StubToolchain(environ={"HOME": <tmp>})` e fixture `installed_plugins.json`: present (4.9.0), outdated (4.8.0, `reason` nomeia o mínimo), missing (arquivo ausente e chave ausente, `remediation` = os dois comandos do Claude unidos por ` && `), undetermined (JSON inválido, sem `remediation`), e a asserção de que `tools.calls` fica vazio durante `detect` (FR-002, FR-003, FR-004, SC-001, Contract dependency-report, CHK001, CHK010, CHK026)
- [ ] T006 [P] [US1] Acrescentar em `tests/validate_dependencies_contract.py` os casos de detecção para `--runtime codex` com fixture de cache do Codex (diretórios `ponytail`, `ponytail`, `<versão>`, `.codex-plugin`, arquivo `plugin.json`): present, maior versão vence entre `4.8.0` e `4.9.0`, `version` do JSON prevalece sobre o nome do diretório, missing (diretório ausente, `remediation` = os dois comandos do Codex), undetermined (`plugin.json` ilegível), e `CODEX_HOME` ou `CLAUDE_CONFIG_DIR` relocando a raiz (FR-002, FR-003, SC-001, Research R2, CHK002, CHK009)
- [ ] T007 [P] [US2] Acrescentar em `tests/validate_dependencies_contract.py` os casos de instalação delegada: com `allow_install=True` e ponytail ausente, `tools.calls` contém exatamente as duas sequências do runtime ativo na ordem, para `claude` e para `codex`; sem `allow_install` nenhuma chamada; falha no primeiro comando interrompe com `FAILED` e o relatório final continua `missing`; `undetermined` nunca entra em `installed` (FR-005, FR-006, SC-002, Contract dependency-report §Efeitos, CHK022, CHK023)
- [ ] T008 [P] [US1] Acrescentar em `tests/validate_dependencies_contract.py` os casos de invariância e manifesto: relatório dos kinds existentes byte-idêntico antes e depois da entrada nova (comparação com a entrada `ponytail` removida do manifesto em memória); `load_manifest` aceita a entrada bundled e recusa `install_by_runtime` com chave fora de `RUNTIMES`, com argv não-lista e `harness-plugin` sem `plugin` ou sem `marketplace`; `preflight` com `--require-dependencies` e ponytail ausente devolve `MISSING-DEPENDENCY`; `GRILL_SKIP_DEPENDENCIES=1` devolve `SKIPPED` (FR-007, FR-008, FR-009, FR-010, SC-004, Contract manifest-entry, CHK004, CHK007, CHK018)
- [ ] T009 [P] Atualizar a constante `VERSION` para `5.4.0` em `tests/validate_distribution.py` (FR-015, SC-003)
- [ ] T010 [P] Atualizar a versão para `5.4.0` nos quatro manifests: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json` e `.agents/plugins/marketplace.json` (FR-015)
- [ ] T011 [P] Atualizar o heading para `# Grill with Docs v5.4.0` e acrescentar, na seção "Dependências e backlog" de `plugin/skills/grill-with-docs/SKILL.md`, um parágrafo que declara o ponytail (`harness-plugin`, mínimo 4.9.0, detecção por registro em disco do runtime ativo, instalação pela CLI do harness sob `--allow-install`) e o limite de que no Codex "instalado" não prova "habilitado" (FR-014, FR-015, Research R8)
- [ ] T012 [P] Atualizar o heading para `# Protocolo de sessão v5.4.0` em `plugin/skills/grill-with-docs/references/session-protocol.md` e acrescentar ao checklist de preflight uma linha que cita o ponytail entre as dependências lidas do campo `dependencies` (FR-014, FR-015)
- [ ] T013 [P] [US3] Criar `.claude/settings.json` com `{"enabledPlugins": {"ponytail@ponytail": true}}` (FR-013, ADR-0001 emenda)

**Checkpoint**: `python3 tests/validate_dependencies_contract.py` e
`python3 tests/validate_distribution.py` fecham em exit 0 — o segundo ainda
reprova em `README.md` até a Phase 3.

---

## Phase 3: Fechamento do leader

**Purpose**: Os arquivos da raiz que nenhum worker pode fencear, e o registro da
conferência. Tarefa de evidência de coordenador — `partition` a devolve em
`deferred_to_leader` e nenhum worker a executa.

- [ ] T014 [US3] Acrescentar a seção `## Ponytail na stack` em CLAUDE.md (o que é, o que o preflight verifica — instalado e ≥ 4.9.0, não "habilitado" —, comandos por harness, hooks exigem `node`), criar AGENTS.md com a mesma seção mais o texto de modo do ponytail (fonte `AGENTS.md` do plugin 4.9.0, MIT), sincronizar o heading `**v5.4.0` e uma frase sobre o ponytail em README.md, abrir a entrada `## 5.4.0` em CHANGELOG.md, e registrar a conferência dos oito pontos de distribuição em `.grill/work-items/feature-add-ponytail-494ea379ecc84a38b029d55ec39ffe8f/AUDIT.md` (FR-011, FR-012, FR-014, FR-015, SC-005, Research R7, R9)

**Checkpoint**: os oito pontos concordam; `python3 tests/run_validators.py`
fecha em exit 0; `grep -n "Ponytail na stack" CLAUDE.md AGENTS.md` acha os dois.

---

## Dependencies

```
Phase 1 (T001 ∥ T002 → T003 → T004)   barreira
        ↓
Phase 2 (T005..T013, paralelas)       barreira
        ↓
Phase 3 (T014, leader)
```

- T003 e T004 dependem de T002 (KINDS e validação do manifesto).
- T004 depende de T001 só em runtime (a entrada precisa existir para o
  checkpoint da fase); os dois arquivos são disjuntos.
- T005..T008 dependem da Phase 1: exercitam o comportamento novo.
- T009..T013 não dependem da correção, mas ficam na Phase 2 para que o gate de
  bump e a suíte fechem no mesmo checkpoint.
- T014 depende de T009..T012: a conferência só faz sentido com os outros sete
  pontos já no valor novo.

## Parallel opportunities

Phase 1: dois grupos — `dependencies.json` (T001) e `ensure_dependencies.py`
(T002 → T003 → T004, serial por arquivo).

Phase 2: seis grupos de conflito disjuntos:

| Grupo | Arquivo(s) | Tarefas |
|---|---|---|
| A | `tests/validate_dependencies_contract.py` | T005, T006, T007, T008 |
| B | `tests/validate_distribution.py` | T009 |
| C | os quatro manifests JSON | T010 |
| D | `plugin/skills/grill-with-docs/SKILL.md` | T011 |
| E | `plugin/skills/grill-with-docs/references/session-protocol.md` | T012 |
| F | `.claude/settings.json` | T013 |

Phase 3 é serial e do leader.

## Independent test criteria

| Story | Critério independente |
|---|---|
| US1 | Fixtures por runtime produzem present/outdated/missing/undetermined corretos e `detect` não executa processo (T005, T006, T008) |
| US2 | Com autorização, a sequência do runtime ativo é executada na ordem e só ela; sem autorização, nada roda; falha é nomeada (T007) |
| US3 | `CLAUDE.md` e `AGENTS.md` têm a seção `Ponytail na stack`; `.claude/settings.json` habilita o plugin (T013, T014) |

## Implementation strategy

MVP = Phase 1 + T005 + T006 + T008. Isso entrega a detecção nos dois harnesses
**e** a prova de que nada existente mudou — as duas metades que a cláusula
*Fail-closed sem waiver* exige juntas.

T007 fecha a instalação delegada. T009..T014 são a obrigação de distribuição da
cláusula *Bump obrigatório do plugin* e a documentação; não podem faltar no
merge.
