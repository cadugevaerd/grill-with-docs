# PLAN-CONTEXT

## FASE-001 — Resolver o backlog vinculado de qualquer worktree do repositório
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW

**Causa raiz.** `resolve_backlog` (`backlog_bridge.py:114-142`) compara `bound_path` com
`str(root)` por igualdade de string. `root` vem de `project_root` (`grill_workspace.py:257-264`),
que devolve o toplevel da worktree em que o comando roda; numa worktree linkada esse toplevel
não é o caminho vinculado. `derive_identity` (`98-110`) agrava: deriva nome e código de
`root.name`, o nome da branch/worktree, e por isso a proposta de criação sai como `CFB`.
Os seis callers (`156,169,237,473,523,573`) passam pela mesma função: um ponto de correção.

**Superfície de mudança, em ordem de dependência.**

1. `backlog_bridge.py` — helper `worktree_candidates(root, tools) -> list[str]`: executa
   `tools.run(["git", "worktree", "list", "--porcelain"], cwd=root)`, lê as linhas com
   prefixo `worktree `, aplica `os.path.realpath` a cada uma e devolve na ordem do git
   (primeira = worktree de controle). Código de saída ≠ 0 ou nenhuma linha → `[realpath(root)]`.
   Sem `subprocess` direto: o seam de toolchain continua sendo o único ponto de side effect
   da ponte. (ADR-0001, DQ-0002/R-0002)
2. `resolve_backlog` — `candidates = worktree_candidates(...)`, `target = candidates[0]`;
   `bound` passa a ser a lista dos backlogs cujo `realpath(bound_path)` está em
   `set(candidates)`. Mais de um código distinto → `BacklogUnavailable` nomeando os códigos
   e caminhos. Todo `bound_path` de payload `NEEDS-*` e o `root.name` de `derive_identity`
   e do casamento `unbound` usam `target`, não `root`. A verificação de `requested` já
   vinculado noutro lugar passa a testar `declared.bound_path ∉ candidates`. (ADR-0001)
3. `ensure_bind` — `backlog bind --path` recebe `resolution["bound_path"]` (o alvo), não
   `str(root)`. (ADR-0001)
4. `tests/validate_backlog_contract.py` — `StubToolchain.run` casa `argv[1:]` quando
   `argv[0] == "git"`; casos novos de `Resolution` e `BindLifecycle` do ADR-0002; um caso
   com `git init` + `git worktree add` em diretório temporário. (ADR-0002)

**Restrições que o plano não pode violar.**

- Somente stdlib; nenhum acesso direto ao SQLite; o backlogctl continua a única
  autoridade de mutação e toda mutação segue preview-first.
- Um subprocesso `git` por resolução, nunca por item: `sync_items` e `project` resolvem
  uma vez e iteram itens com o código já resolvido.
- Nenhum bind existente muda: `DTA`, `EEA`, `FLM` permanecem `BOUND` ao caminho atual.
  A ponte não re-vincula em silêncio, hoje e depois.
- Nenhum código público novo nem string alterada: ambiguidade sai como
  `BACKLOG-UNAVAILABLE` com `detail`; `BACKLOG-NOT-BOUND`, `BACKLOG-REQUIRED` e
  `NEEDS-CREATE|NEEDS-BIND|BOUND` mantêm forma.
- `project_root` continua exigindo o toplevel; o fallback `{root}` nunca substitui essa
  recusa.

**Cobertura exigida.** Ver ADR-0002. Critério mínimo: um caso em que `root` é uma worktree
linkada e `bound_path` é a de controle, com verdict `BOUND` — o caso que hoje não existe.

### Obrigações carregadas ao ciclo executor

- **Bump obrigatório**: o plano altera `plugin/**`; subir a versão nos oito lugares que
  `tests/validate_distribution.py` fixa antes do merge. Leitura SemVer: **patch**,
  5.4.0 → 5.4.1 — corrige comportamento sem mudar contrato público (DQ-0006/R-0006).
  Assunção a confirmar no ciclo executor.
- **Suíte verde**: `python3 tests/run_validators.py` em exit 0; hoje 28 validadores
  (contar pelo marcador `==>`). Rodar uma vez antes de tocar código para fixar a baseline.
- **Carimbo de escape deste bundle**: nasceu com `backlog_skipped` porque o bug que corrige
  é o que impediu o bind. Depois do ship, rodar
  `backlog-adopt ROOT --work-id fix-backlog-bind-worktree-e7e330462d004d439ebb11ab6c6d95ea --apply` a partir desta mesma worktree —
  o próprio fix torna isso possível sem merge prévio.
- **Prova de aceite manual**: `preflight . --runtime claude` nesta worktree devolve
  `backlog.status = BOUND`, `code = SGD`.
- **Memória do projeto**: a nota `backlog-bind-nao-segue-worktree` descreve o contorno
  (`--skip-backlog` + adopt pós-merge) e deve ser marcada como resolvida após o ship.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
