---

description: "Task list for 031 — observar a instalação Codex do i-have-adhd"
---

# Tasks: Observar a instalação Codex do i-have-adhd

**Input**: Design documents from `/specs/031-codex-install-path/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: obrigatórios (FR-007). O teste atual do observer usa uma listagem Codex com `installPath`, que o Codex 0.154.0 não emite; sem a fixture real nada prova a correção.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos disjuntos, sem dependência pendente)
- **[Story]**: US1..US3 do `spec.md`
- Todo caminho é repo-relativo e explícito, porque o `partition` só fenceia o que a linha nomeia; nenhuma outra palavra das linhas de tarefa contém barra

## Path Conventions

Repositório existente, sem estrutura nova. Arquivos tocados (10): o observer, o validador de orquestração, uma fixture nova, os quatro manifests, o validador de distribuição e os dois headings sob `plugin/`; mais `README.md` e `CHANGELOG.md` na raiz.

**Fronteira conhecida do `partition`**: `README.md` e `CHANGELOG.md` estão na raiz e são infenceáveis para um worker. A Phase 3 os entrega ao **leader**, nomeando um caminho de evidência de coordenador.

---

## Phase 1: Observer e fixture real

**Purpose**: A correção do observer e a entrada real do Codex. Arquivos disjuntos.

- [X] T001 [P] [US1] Criar `tests/fixtures/orchestration/codex-plugin-list-0.154.0.json` com o objeto `{"installed": [<entrada>], "available": []}`, em que a entrada é, campo a campo, a entrada real de `i-have-adhd@i-have-adhd` capturada de `codex plugin list --json` do codex-cli 0.154.0 (pluginId, name, marketplaceName, version 0.3.0, installed true, enabled true, source git com url do repositório ayghri e ref main, marketplaceSource, installPolicy AVAILABLE, authPolicy ON_INSTALL), sem `installPath` e sem entradas de outros plugins (FR-007, Contract codex-plugin-list, Research R5)
- [X] T002 [P] [US1] Em `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, no ramo de `_orca_presentation_axes` que hoje só promove a instalação a partir de `installPath`: manter o comportamento atual quando `installPath` estiver presente (válido ou inválido, sem fallback — FR-004); quando ausente e o provider for codex, aceitar somente se `installed is True` e `marketplaceName`, `name` e `version` forem strings não vazias sem separador de diretório e diferentes de ponto e de dois pontos (FR-009), compor a raiz como home Codex (a mesma expressão de `CODEX_HOME` ou `.codex` sob o home já usada nas linhas 440 e 700 do mesmo arquivo) mais os segmentos plugins, cache, marketplaceName, name e version, e exigir que essa raiz seja diretório e que o SKILL.md da skill i-have-adhd sob ela seja arquivo regular; então preencher `installation` com status present, version, install_root e skill_ref no mesmo formato atual; qualquer falha mantém `installation` vazio; não conferir hash aqui, porque `approved_presentation_reference` já faz isso para os dois runtimes; atualizar o comentário que proíbe adivinhar caminho para nomear a exceção do ADR-0001 (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-009, Research R1–R4, Data model)

**Checkpoint**: `python3 tests/validate_agent_orchestration_contract.py` continua passando sem edição (Claude e listagem com `installPath` inalterados).

---

## Phase 2: Cobertura e distribuição

**Purpose**: Travar o comportamento pela fixture real e sincronizar a versão. T003 escreve o validador de orquestração sozinho; os demais são disjuntos.

- [X] T003 [US1] [US2] [US3] Em `tests/validate_agent_orchestration_contract.py`, acrescentar casos que carregam `tests/fixtures/orchestration/codex-plugin-list-0.154.0.json` e montam um home Codex temporário via `CODEX_HOME` com a cópia em plugins, cache, i-have-adhd, i-have-adhd, 0.3.0 contendo o SKILL.md da skill: listagem real + cópia presente → installation present com skill_ref dentro da raiz temporária (US1-S1) e resultado idêntico ao repetir (US1-S2); installed false → vazio (US2-S1); raiz ausente → vazio (US2-S2); SKILL.md com conteúdo divergente → a avaliação de apresentação devolve `STYLE-CONTENT-INCOMPATIBLE` (US2-S3); cada campo de identificação ausente, vazio, com separador ou igual a dois pontos → vazio (US2-S4, FR-009); `installPath` relativo numa entrada Codex → vazio, sem usar o caminho composto (FR-004); listagem Claude com `installPath` → resultado atual (US3); nenhum caso chama `codex`, `claude`, `node` ou rede (FR-005, FR-007, SC-001, SC-002, SC-003)
- [X] T004 [P] Atualizar a constante `VERSION` para `6.0.2` em `tests/validate_distribution.py` (FR-008)
- [X] T005 [P] Atualizar a versão para `6.0.2` nos quatro manifests: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json` e `.agents/plugins/marketplace.json` (FR-008)
- [X] T006 [P] Atualizar o heading para `# Grill with Docs v6.0.2` em `plugin/skills/grill-with-docs/SKILL.md` (FR-008)
- [X] T007 [P] Atualizar o heading para `# Protocolo de sessão v6.0.2` em `plugin/skills/grill-with-docs/references/session-protocol.md` (FR-008)

**Checkpoint**: `python3 tests/validate_agent_orchestration_contract.py` e `python3 tests/validate_distribution.py` fecham em exit 0; o segundo ainda reprova em `README.md` até a Phase 3.

---

## Phase 3: Fechamento do leader

**Purpose**: Os arquivos da raiz que nenhum worker pode fencear e o registro da conferência. Tarefa de evidência de coordenador: `partition` a devolve em `deferred_to_leader`.

- [X] T008 Sincronizar o heading `**v6.0.2` em README.md, abrir a entrada `## 6.0.2` em CHANGELOG.md (fix: a observação da instalação Codex do i-have-adhd deixa de exigir `installPath`, que o codex-cli 0.154.0 não emite; o caminho é composto de campos da listagem nativa, restrito a nomes simples e confirmado em disco; conteúdo divergente segue recusado pela verificação comum), e registrar a conferência dos oito pontos de distribuição e o resultado de `python3 tests/run_validators.py` em `.grill/work-items/fix-codex-install-path-693af70e339f4e299fa51605d45bb1ff/AUDIT.md` (FR-008, SC-004, quickstart 2 e 3)

**Checkpoint**: os oito pontos concordam; `python3 tests/run_validators.py` fecha em exit 0; `git diff --check` limpo.

---

## Dependencies

```
Phase 1 (T001 ∥ T002)   barreira
        ↓
Phase 2 (T003 | T004 ∥ T005 ∥ T006 ∥ T007)   barreira
        ↓
Phase 3 (T008, leader)
```

- T003 depende de T001 (fixture) e de T002 (comportamento sob teste).
- T004–T007 não dependem de nada da Phase 1, mas ficam na Phase 2 para que a versão só mude junto com a cobertura.

## Parallel opportunities

- Phase 1: T001 e T002 em arquivos disjuntos.
- Phase 2: T004, T005, T006 e T007 em arquivos disjuntos, em paralelo com T003.

## Independent test criteria

- **US1**: listagem real sem `installPath` + cópia presente → `present` (T003).
- **US2**: cada variação de evidência incompleta → vazio; conteúdo divergente → `STYLE-CONTENT-INCOMPATIBLE` (T003).
- **US3**: casos Claude existentes inalterados e caso Claude com `installPath` (T003, checkpoint da Phase 1).

## Implementation strategy

MVP = Phase 1 + T003: o Codex passa a ser observado e o comportamento fica travado pela fixture real. A distribuição (T004–T008) acompanha na mesma entrega porque a Constituição exige bump para qualquer mudança em `plugin/`.

## Phase 4: Convergence

- [X] T009 CRITICAL Em `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, no ramo Codex sem `installPath` de `_orca_presentation_axes`: envolver a resolução do home Codex e as verificações de diretório e de arquivo num bloco try com except `(OSError, ValueError, RuntimeError)` que mantém `installation` vazio (o mesmo trio já tratado em `_runtime_config_axes`), e trocar o filtro de separadores por `PureWindowsPath(v).name == v`, mantendo a recusa explícita de vazio, ponto e dois pontos; e em `tests/validate_agent_orchestration_contract.py`, no método `test_codex_install_path_composed_from_cache_when_installpath_absent`, acrescentar: segmentos `D:` e `C:` em cada campo de identificação → vazio; `version` inteiro e `marketplaceName` nulo → vazio; `installPath` presente com valor nulo → vazio sem composição; `installed` ausente → vazio; `Path.home` levantando `RuntimeError` com `CODEX_HOME` ausente → vazio sem exceção per Constitution Fail-closed sem waiver, FR-002, FR-007, FR-009 (contradicts)
- [X] T010 Corrigir em CHANGELOG.md, na entrada `## 6.0.2`, a última frase para dizer que um teste novo usa a entrada real capturada do Codex 0.154.0 (o teste antigo com `installPath` continua), e registrar a rodada R1 do review e sua resolução em `.grill/work-items/fix-codex-install-path-693af70e339f4e299fa51605d45bb1ff/AUDIT.md` per FR-008 (partial)

## Phase 5: Convergence

- [ ] T011 Em `tests/validate_agent_orchestration_contract.py`, no caso do segmento literal `D:` dentro de `test_codex_install_path_composed_from_cache_when_installpath_absent`, semear o diretório de cache apenas quando o sistema aceita esse nome literal (`os.name != "nt"`), mantendo a asserção de recusa incondicional nos três campos de identificação, porque no Windows `D:` é âncora de drive e o caminho semeado escaparia do diretório temporário per FR-007, review R2 N1 (partial)
