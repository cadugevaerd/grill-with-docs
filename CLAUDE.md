# CLAUDE.md — grill-with-docs

Este repositório **é** o plugin `grill-with-docs` e também o consome (dogfooding). As duas coisas convivem na mesma árvore, então saber o que é fonte e o que é artefato de consumo evita confusão.

## Layout

- `plugin/` — fonte publicada do plugin: `SKILL.md`, `assets/`, `scripts/`, `references/` e os dois manifests (`.claude-plugin/`, `.codex-plugin/`).
- `tests/` — validadores canônicos. `tests/run_validators.py` faz glob de `validate_*.py`, então um arquivo novo entra na suíte sozinho.
- `tests/fixtures/` — repositórios sintéticos, incluindo `.specify/` próprios. Não confundir com o `.specify/` da raiz.
- `.specify/` e `.claude/` na raiz — stack do Spec Kit deste repositório, versionada de propósito (ver abaixo).
- `WORKFLOW.md` na raiz — workflow project-wide gerenciado, marcador `grill-with-docs-workflow:v2`.

## Rodar os testes

```bash
python3 tests/run_validators.py
```

Baseline atual: 877 testes, exit 0, com 1 skip dependente de ambiente em `validate_workspace_contract.py`. Nenhum teste pode tocar a rede nem exigir `specify`, `node` ou `backlogctl` reais — a matriz de CI (ubuntu/windows/macos, Python 3.10 e 3.13) não tem nenhum deles. Use os seams injetáveis: `Toolchain` em `ensure_dependencies.py` e o `resolve_cli` substituível em `backlog_bridge.py`.

## Restrições do core

- Somente biblioteca padrão, Python >=3.10. Sem dependência externa.
- O core **nunca baixa bytes**. Toda instalação é delegada a quem é dono do artefato (`uv`, `specify`, o instalador verificado do plugin `backlog`) e a verificação é por versão resolvida, nunca por hash de tarball.
- Hooks são read-only e não escrevem nem acessam a rede.
- Feature e fix são plan-only e terminam em `PLAN_ONLY_STOP`. Só hotfix tem trilha executável, via `HOTFIX-GO`.

## `ESSENTIAL` do WORKFLOW.md

`ensure_workflow.py` valida `WORKFLOW.md` exigindo **todas** as substrings da tupla `ESSENTIAL`. Acrescentar um marcador novo marca como `incompatible workflow` todo `WORKFLOW.md` v2 já materializado em projetos consumidores. Não mexa nessa tupla sem bump de `VERSION` para `v3` e um caminho de migração.

## `init` e dependências

`grill_workspace.py init` fixa o `WORKFLOW.md` antes de montar o bundle e reporta o estado das dependências externas em `dependencies`. O preflight é declarado em `plugin/skills/grill-with-docs/assets/dependencies.json`.

- padrão: só detecta e reporta, nunca bloqueia;
- `--allow-install`: autoriza a instalação delegada e a criação/bind do backlog. Essa flag é a confirmação explícita que o contrato do backlog exige;
- `--require-dependencies`: torna a falta um `MISSING-DEPENDENCY` fail-closed;
- `--skip-backlog`: desliga a integração com o backlog;
- `GRILL_SKIP_DEPENDENCIES=1`: desliga a detecção em ambiente air-gapped e **nunca** é reportado como `OK`.

Subcomandos auxiliares: `preflight ROOT [--allow-install] [--skip-backlog]` e `backlog-sync ROOT --work-id ID [--apply] [--db PATH]`.

## Extensões do Spec Kit

`git`, `agent-assign`, `bugfix` e `verify-review-ship` são exigidas pelo `WORKFLOW.md`. As três últimas vivem no catálogo `community`, que é discovery-only: instalar por `--from <archive-url>` dispara um aviso interativo de fonte não confiável e aborta em modo não-interativo. Um instalador automatizado não deve responder esse aviso no lugar do humano, então `--allow-install` registra o catálogo como confiável em `.specify/extension-catalogs.yml` (`install_allowed: true`) e instala pelo nome. É uma decisão de confiança explícita e revisável no diff.

## Por que `.specify/` e `.claude/` são versionados

A stack do Spec Kit deste repositório está no controle de versão de propósito, para que a configuração seja reproduzível e revisável. Consequências a conhecer:

- `.specify/extensions/` carrega código de terceiros vendorizado (`agent-assign` de xymelon, `bugfix` de Quratulain-bilal). Atualizações de extensão aparecem como diff.
- `.specify/extensions/.cache/` é cache do catálogo e gera churn a cada refresh.
- `.claude/settings.local.json` é override por máquina; mudanças locais de configuração viram diff.
- `.specify/memory/constitution.md` na raiz é a **Constituição gerenciada do grill**, gerada de `assets/GRILL-CONSTITUTION.template.md` e não o placeholder do spec-kit. São 8 cláusulas normativas e ela é read-only depois do bootstrap: nenhum ADR ou decisão local funciona como waiver.

## Backlog

Este repositório está vinculado ao backlog `SGD` (`spec-kit-grill-with-docs`), herdado do caminho anterior do projeto. O código não coincide com o nome do diretório, então o vínculo foi feito com `backlog_bridge.py . --code SGD --apply`. Toda mutação no backlog é preview-first e exige `--apply`.

## Gates de integração

São dois workflows, e a separação é deliberada:

- `.github/workflows/ci.yml` — matriz de portabilidade (3 SOs × Python), com `paths:` restrito ao que ela cobre. Tem guarda que pula a matriz em merge de PR, porque o evento `pull_request` já testou a mesma árvore.
- `.github/workflows/bump-gate.yml` — o gate de versão, **sem** `paths:`. Ele roda em toda PR e sempre reporta.

O gate mora sozinho porque `paths:` é declarado no nível do workflow, não do job: enquanto vivia no `ci.yml`, herdava o filtro da matriz e ficava mudo nas PRs que não o casavam. Um required check mudo prende a PR para sempre.

**Ato humano pendente:** registrar `Version bump gate` como *required status check* na branch protection de `main`, em `cadugevaerd/grill-with-docs`. Sem isso, FR-007 é convenção e não gate — a reprovação aparece em vermelho e nada impede o merge. Nenhum commit consegue fazer isso; é configuração do serviço. Rastreado em SGD-4 e SGD-7.

Ao marcar, vale exigir junto **branch atualizada em relação à base**: isso fecha a ressalva da guarda de deduplicação do `ci.yml`, onde uma PR desatualizada poderia depositar árvore diferente da testada.

## Distribuição

`tests/validate_distribution.py` trava o contrato público. Ao mudar a versão, atualize em **oito** lugares — os quatro manifests, a constante `VERSION` do próprio validador e três headings de documentação que o validador também fixa:

- `plugin/.claude-plugin/plugin.json`
- `plugin/.codex-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.agents/plugins/marketplace.json`
- constante `VERSION` em `tests/validate_distribution.py`
- `plugin/skills/grill-with-docs/SKILL.md` — heading `# Grill with Docs vX.Y.Z`
- `plugin/skills/grill-with-docs/references/session-protocol.md` — heading `# Protocolo de sessão vX.Y.Z`
- `README.md` — heading `**vX.Y.Z`

Os três headings existem porque derivavam silenciosamente dos manifests; o validador exige exatamente uma ocorrência de cada prefixo, casando a versão.
