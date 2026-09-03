# grill-with-docs

**v5.3.4 · MIT**

Plugin de planejamento arquitetural e entrega **Delivery First**: entrevista decisões, mantém work items isolados, valida a Constituição e produz evidência auditável. O plugin é plan-only para feature/fix (`PLAN_ONLY_STOP`); hotfix/incident segue uma faixa rápida, explícita e fail-closed (`HOTFIX-GO`). Auditoria e reconciliação não substituem o ship externo.

Compatível com Codex e Claude Code. Repositório público canônico: [cadugevaerd/grill-with-docs](https://github.com/cadugevaerd/grill-with-docs).

## Instalação no Codex

```bash
git clone https://github.com/cadugevaerd/grill-with-docs.git
cd grill-with-docs
codex plugin marketplace add .
codex plugin add grill-with-docs@grill-with-docs
```

## Instalação no Claude Code

```bash
claude plugin marketplace add cadugevaerd/grill-with-docs
claude plugin install grill-with-docs@grill-with-docs
```

## Uso

O bundle instalado contém a skill `grill-with-docs`, hooks de inicialização e scripts Python somente com biblioteca padrão. O fluxo básico é iniciar um work item e depois retomar, auditar ou conciliar conforme o protocolo:

```bash
CORE="$PLUGIN_ROOT/skills/grill-with-docs/scripts/grill_workspace.py"
python3 "$CORE" preflight "$PWD" --runtime codex
python3 "$CORE" init "$PWD" --runtime codex --type feature --slug minha-feature
python3 "$CORE" status "$PWD"
python3 "$CORE" status "$PWD" --format markdown
```

O formato padrão é JSON para automações. `--format markdown` produz a resposta humana canônica: `all good` quando não há pendências ou uma tabela estável de work items pendentes.

O `init` fixa o `WORKFLOW.md` project-wide e reporta o estado das dependências externas (Spec Kit e extensões, `backlogctl`). `--runtime claude|codex` é obrigatório e seleciona o harness da sessão, independentemente do default salvo pelo Spec Kit. Por padrão ele apenas relata; `--allow-install` autoriza a materialização da integração e extensões nesse harness sem remover o outro, e `--require-dependencies` torna o gate fail-closed. O plugin nunca baixa binários por conta própria.

Feature/fix terminam em `PLAN_ONLY_STOP`; a implementação deve ocorrer fora do plugin. Para incidentes, use os comandos de hotfix documentados em `skills/grill-with-docs/SKILL.md`, sempre com reprodução, evidência, teste de correção, rollback e evidência constitucional.

## Limites e compatibilidade

- A Constituição existente é preservada e tratada como read-only.
- Hooks apontam somente para o diretório instalado via `PLUGIN_ROOT`/`CLAUDE_PLUGIN_ROOT`.
- Python 3.10+ e biblioteca padrão; os testes do repositório rodam com Python 3.13.
- O plugin não publica código, não executa o fluxo normal de implementação e não faz ship externo automaticamente.

## Desenvolvimento local

Os validadores canônicos ficam em `tests/` e podem ser executados diretamente:

```bash
python3 tests/validate_contract.py
python3 tests/validate_checkpoint_contract.py
python3 tests/validate_workspace_contract.py
python3 tests/validate_workflow_contract.py
python3 tests/validate_status_contract.py
python3 tests/validate_distribution.py
```

Consulte `CHANGELOG.md` para o histórico da extração pública.
