# Quickstart: validar o backlog vinculado de qualquer worktree

## Pré-requisitos

- Python >= 3.10; `git` no PATH; sem rede; `backlogctl` real **não** é necessário para os testes.
- Repositório em `cadugevaerd/chore-fix-backlog`, que é uma worktree linkada de `~/Documentos/Projetos/grill-with-docs`.

## 1. Suíte de validação (CI)

```bash
python3 tests/run_validators.py
```

Esperado: exit 0; `tests/validate_backlog_contract.py` inclui os casos de `Resolution` por worktree, `BindLifecycle` com `--path` da controle e `RealWorktree` com `git worktree add`.

## 2. Prova manual do sintoma (esta worktree)

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py preflight . --runtime claude \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['backlog']['backlog'])"
```

Antes: `{'status': 'NEEDS-CREATE', 'code': 'CFB', ...}`. Depois: `{'status': 'BOUND', 'code': 'SGD', 'bound_path': '/home/.../Documentos/Projetos/grill-with-docs'}`.

## 3. Nenhum vínculo alterado

```bash
$BACKLOGCTL --json backlog list | python3 -c "import sys,json; [print(b['code'], b['bound_path']) for b in json.load(sys.stdin)['data']]"
```

A lista é idêntica antes e depois da mudança (SC-003).

## 4. Adoção deste work item (pós-ship)

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py backlog-adopt . \
  --work-id fix-backlog-bind-worktree-e7e330462d004d439ebb11ab6c6d95ea --apply
```

Esperado: `APPLIED`, `backlog_skipped` removido do `state.json`, sem merge prévio.

## 5. Distribuição

```bash
python3 tests/validate_distribution.py
```

Esperado: `5.4.1` nos oito pontos fixados.
