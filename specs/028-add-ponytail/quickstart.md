# Quickstart: validar o ponytail na stack oficial

## Pré-requisitos

- Python >= 3.10; sem rede; `claude`/`codex` **não** são necessários para os testes.
- Repositório em `cadugevaerd/chore-add-ponytail`.

## 1. Suíte de validação (CI)

```bash
python3 tests/run_validators.py
```

Esperado: todos os validadores passam; `validate_dependencies_contract.py` inclui casos `harness-plugin` para `claude` e `codex` (present/outdated/missing/undetermined) e a sequência de instalação por runtime; `validate_distribution.py` fixa `5.4.0`.

## 2. Detecção real nesta máquina

```bash
python3 plugin/skills/grill-with-docs/scripts/ensure_dependencies.py . --runtime claude | python3 -c "import json,sys; print([d for d in json.load(sys.stdin)['dependencies'] if d['id']=='ponytail'])"
python3 plugin/skills/grill-with-docs/scripts/ensure_dependencies.py . --runtime codex  | python3 -c "import json,sys; print([d for d in json.load(sys.stdin)['dependencies'] if d['id']=='ponytail'])"
```

Esperado (máquina de referência): `status: present`, `version: 4.9.0`, `source` apontando `installed_plugins.json` (claude) ou `.../4.9.0/.codex-plugin/plugin.json` (codex).

## 3. Ausência simulada, sem instalar

```bash
HOME=$(mktemp -d) python3 plugin/skills/grill-with-docs/scripts/ensure_dependencies.py . --runtime claude | python3 -c "import json,sys; d=json.load(sys.stdin); p=[x for x in d['dependencies'] if x['id']=='ponytail'][0]; print(p['status'], p['remediation']); print(d['missing_required'])"
```

Esperado: `missing claude plugin marketplace add DietrichGebert/ponytail && claude plugin install ponytail@ponytail` e `ponytail` em `missing_required`. Nenhum processo executado.

## 4. Instalação delegada (opcional, toca o ambiente do usuário)

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py preflight . --runtime claude --allow-install
```

Esperado: `installed[]` com a sequência de dois comandos, depois `ponytail` `present`. Só executar com autorização humana (HOLD-PRE-03).

## 5. Documentação e ativação deste repositório

```bash
grep -n "Ponytail na stack" CLAUDE.md AGENTS.md
python3 -c "import json; print(json.load(open('.claude/settings.json'))['enabledPlugins']['ponytail@ponytail'])"
grep -n "ponytail" plugin/skills/grill-with-docs/SKILL.md README.md | head
```

Esperado: seção presente nos dois arquivos; `True`; menção em SKILL.md e README.md.

## 6. Bump

```bash
grep -rn "5.4.0" plugin/.claude-plugin/plugin.json plugin/.codex-plugin/plugin.json .claude-plugin/marketplace.json .agents/plugins/marketplace.json tests/validate_distribution.py plugin/skills/grill-with-docs/SKILL.md plugin/skills/grill-with-docs/references/session-protocol.md README.md | wc -l
```

Esperado: 8 (um por ponto de versão). Ver [contracts/](contracts/) e [data-model.md](data-model.md) para as formas exatas.
