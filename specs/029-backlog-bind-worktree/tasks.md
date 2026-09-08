---

description: "Task list for 029 — backlog vinculado de qualquer worktree"
---

# Tasks: Backlog vinculado de qualquer worktree

**Input**: Design documents from `/specs/029-backlog-bind-worktree/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: obrigatórios (FR-011). O sintoma era invisível à suíte porque todo caso
de resolução usava `bound_path == str(self.root)`; sem os casos novos nada prova
a correção, e a CI não tem `backlogctl` real — o stub do seam mais um caso com
`git` real são a única prova possível.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos disjuntos, sem dependência pendente)
- **[Story]**: US1..US3 do `spec.md`
- Todo caminho é repo-relativo e explícito, porque o `partition` só fenceia o que
  a linha nomeia

## Path Conventions

Repositório existente, sem estrutura nova. Arquivos tocados (12): a ponte do
backlog, o validador do contrato do backlog, os oito pontos de versão, mais
`CLAUDE.md` e `CHANGELOG.md`.

**Fronteira conhecida do `partition`**: um token só é reconhecido como caminho
quando contém `/`. `CLAUDE.md`, `README.md` e `CHANGELOG.md` estão na raiz e são,
por construção, infenceáveis para um worker. Eles são trabalho do **leader**, e a
Phase 3 os declara como tal nomeando um caminho de evidência de coordenador.

---

## Phase 1: Fundação — a ponte resolve por conjunto de worktrees

**Purpose**: O helper de enumeração, a resolução por conjunto e o bind no alvo.
As três tarefas escrevem `backlog_bridge.py` e formam um grupo de conflito
único: são serializadas de propósito.

- [X] T001 Implementar `worktree_candidates(root: Path, tools) -> list[str]` em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`: `code, output = tools.run(["git", "worktree", "list", "--porcelain"], cwd=root)`; para cada linha com prefixo `worktree `, `os.path.realpath` do resto, na ordem do git, sem duplicatas; acrescentar `os.path.realpath(root)` ao fim se ausente; `code != 0` ou nenhuma linha → `[os.path.realpath(root)]`; nenhuma exceção por falha do git (FR-001, FR-002, FR-007, FR-010, Contract worktree-enumeration, Research R2, R6)
- [X] T002 Reescrever `resolve_backlog` em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py` para usar `candidates = worktree_candidates(root, tools)`, `target = candidates[0]`, `known = set(candidates)`: `bound` = backlogs cujo `os.path.realpath(bound_path)` ∈ `known` (ignorar `bound_path` vazio); mais de um `code` distinto em `bound` → `BacklogUnavailable(f"{target} matches more than one backlog: " + ", ".join(f"{b['code']} at {b['bound_path']}"))`; um `bound` → lógica atual de `requested` e payload `BOUND` com `bound_path` = o `bound_path` real do item; sem `bound` → `requested` declarado com `bound_path` fora de `known` recusa como hoje; `NEEDS-BIND` e `NEEDS-CREATE` usam `bound_path = target`, `unbound` casado por `Path(target).name` e `derive_identity(Path(target), taken)`; docstring atualizada com a regra do conjunto (FR-001, FR-003, FR-005, FR-006, FR-009, Contract backlog-resolution, Data model §Transições, Research R1, R3)
- [X] T003 Ajustar `ensure_bind` em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py` para chamar `["backlog", "bind", "--code", resolution["code"], "--path", resolution["bound_path"]]` em vez de `str(root)`, mantendo `create`, preview-first e a re-resolução final (FR-004, Contract backlog-resolution §Invariantes)

**Checkpoint**: `python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py preflight . --runtime claude`
nesta worktree reporta `backlog.backlog.status = BOUND`, `code = SGD`; `backlogctl backlog list` inalterado.

---

## Phase 2: Cobertura e distribuição

**Purpose**: Travar o comportamento por fixture e sincronizar a versão. T004..T007
escrevem o mesmo validador e serializam num grupo; os demais são disjuntos.

- [X] T004 [P] [US1] Estender `StubToolchain.run` em `tests/validate_backlog_contract.py` para casar `tuple(argv[1:])` quando `argv[0] == "git"` (chave `("worktree", "list", "--porcelain")`), mantendo `argv[2:]` para o backlogctl e a resposta padrão `0, envelope([])`; acrescentar helper de módulo `porcelain(*paths) -> str` que monta `worktree <p>\nHEAD 0000000\nbranch refs/heads/x\n\n` por caminho; acrescentar em `Resolution` os casos: `bound_path` = controle e `root` = linkada → `BOUND` com `code` do vínculo; `bound_path` = linkada e `root` = controle → `BOUND` com `bound_path` igual à linkada (sem re-apontar); casos existentes continuam passando sem edição (FR-001, FR-002, FR-005, SC-001, US1-S1, US1-S3, Research R5, CHK008, CHK011)
- [X] T005 [P] [US2] Acrescentar em `tests/validate_backlog_contract.py`: em `Resolution`, `NEEDS-CREATE` a partir da linkada com `name` e `code` derivados de `Path(controle).name` e `bound_path` = controle; backlog `unbound` com o nome da controle → `NEEDS-BIND` com `bound_path` = controle; `requested` já vinculado fora do conjunto → `BacklogUnavailable`; em `BindLifecycle`, `ensure_bind(linkada, apply=True)` com `git` stubado emite `["backlog", "bind", "--code", ..., "--path", controle]` (FR-003, FR-004, SC-002, US2-S1..S4, Contract backlog-resolution, CHK010, CHK014)
- [X] T006 [P] [US3] Acrescentar em `tests/validate_backlog_contract.py`, em `Resolution`: dois backlogs de códigos distintos vinculados a controle e linkada → `BacklogUnavailable` cuja mensagem contém os dois códigos, e `tools.mutations()` vazio; `git` respondendo `code=1` → comportamento atual (`bound_path == str(root)` casa; outro caminho não casa); porcelain com caminho duplicado e com grafia não normalizada (`/a/./b`) → um só candidato após `realpath` (FR-006, FR-007, FR-002, US3-S1, US3-S2, Edge Cases, Contract worktree-enumeration §Garantias, CHK003, CHK004, CHK029)
- [X] T007 [P] [US1] Acrescentar classe `RealWorktree(unittest.TestCase)` em `tests/validate_backlog_contract.py`: em `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)`, `git init -q`, `git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init`, `git worktree add -q` do subdiretório `linked` do temporário com `-b linked`; toolchain híbrido que responde `backlog list` pelo stub (um item com `bound_path` = `os.path.realpath` do subdiretório `repo`) e delega `argv[0] == "git"` a `subprocess.run` real com `cwd`; `resolve_backlog` sobre o caminho da linkada → `BOUND`; `skipTest` se `git` ausente em `shutil.which` (FR-011, SC-004, ADR-0002, Research R4, CHK007)
- [X] T008 [P] Atualizar a constante `VERSION` para `5.4.1` em `tests/validate_distribution.py` (FR-012, SC-005)
- [X] T009 [P] Atualizar a versão para `5.4.1` nos quatro manifests: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json` e `.agents/plugins/marketplace.json` (FR-012)
- [X] T010 [P] Atualizar o heading para `# Grill with Docs v5.4.1` e acrescentar, no parágrafo de `backlog_bridge.py ROOT --code CODE` da seção "Dependências e backlog" de `plugin/skills/grill-with-docs/SKILL.md`, uma frase: o vínculo é reconhecido de qualquer worktree registrada do repositório, e um vínculo novo grava o caminho da worktree de controle (FR-008, FR-012, Research R1)
- [X] T011 [P] Atualizar o heading para `# Protocolo de sessão v5.4.1` em `plugin/skills/grill-with-docs/references/session-protocol.md` (FR-012)

**Checkpoint**: `python3 tests/validate_backlog_contract.py` e
`python3 tests/validate_distribution.py` fecham em exit 0 — o segundo ainda
reprova em `README.md` até a Phase 3.

---

## Phase 3: Fechamento do leader

**Purpose**: Os arquivos da raiz que nenhum worker pode fencear, e o registro da
conferência. Tarefa de evidência de coordenador — `partition` a devolve em
`deferred_to_leader` e nenhum worker a executa.

- [X] T012 Sincronizar o heading `**v5.4.1` em README.md, abrir a entrada `## 5.4.1` em CHANGELOG.md (fix: bind do backlog reconhecido de qualquer worktree registrada; bind novo grava a worktree de controle; ambiguidade recusa; nenhum vínculo existente alterado), acrescentar em CLAUDE.md, na seção "`init` e dependências", uma frase de que o bind é resolvido pelo conjunto de worktrees do repositório e que `--skip-backlog` deixou de ser necessário em worktree, e registrar a conferência dos oito pontos de distribuição e a prova manual do quickstart §2 em `.grill/work-items/fix-backlog-bind-worktree-e7e330462d004d439ebb11ab6c6d95ea/AUDIT.md` (FR-012, SC-003, SC-005, Research R7, quickstart §2, §3, §5)

**Checkpoint**: os oito pontos concordam; `python3 tests/run_validators.py`
fecha em exit 0; `preflight .` nesta worktree devolve `BOUND SGD`.

---

## Dependencies

```
Phase 1 (T001 → T002 → T003, serial por arquivo)   barreira
        ↓
Phase 2 (T004..T007 serial | T008 ∥ T009 ∥ T010 ∥ T011)   barreira
        ↓
Phase 3 (T012, leader)
```

- T002 depende de T001 (usa o helper); T003 depende de T002 (usa `bound_path` do payload).
- T004..T007 dependem da Phase 1: exercitam o comportamento novo. T005..T007 dependem de T004 (stub e helper `porcelain`).
- T008..T011 não dependem da correção, mas ficam na Phase 2 para que o gate de bump e a suíte fechem no mesmo checkpoint.
- T012 depende de T008..T011: a conferência só faz sentido com os outros sete pontos já no valor novo.

## Parallel opportunities

Phase 1: um grupo — `plugin/skills/grill-with-docs/scripts/backlog_bridge.py` (T001 → T002 → T003).

Phase 2: cinco grupos de conflito disjuntos:

| Grupo | Arquivo(s) | Tarefas |
|---|---|---|
| A | `tests/validate_backlog_contract.py` | T004, T005, T006, T007 |
| B | `tests/validate_distribution.py` | T008 |
| C | os quatro manifests JSON | T009 |
| D | `plugin/skills/grill-with-docs/SKILL.md` | T010 |
| E | `plugin/skills/grill-with-docs/references/session-protocol.md` | T011 |

Phase 3 é serial e do leader.

## Independent test criteria

| Story | Critério independente |
|---|---|
| US1 | Resolução a partir de worktree linkada devolve `BOUND` com o código do vínculo, por stub e por git real; vínculo em linkada não é re-apontado (T004, T007) |
| US2 | `NEEDS-CREATE`/`NEEDS-BIND` derivam nome, código e caminho da worktree de controle; `bind --path` grava a controle (T005) |
| US3 | Ambiguidade recusa nomeando os dois códigos sem mutar; git indisponível mantém o comportamento atual; caminhos normalizados (T006) |

## Implementation strategy

MVP = Phase 1 + T004 + T007. Isso entrega a resolução por worktree **e** a prova
contra saída real do git — o caso que a suíte nunca teve.

T005 e T006 fecham alvo de bind e fail-closed. T008..T012 são a obrigação de
distribuição da cláusula *Bump obrigatório do plugin* e a documentação; não
podem faltar no merge.
