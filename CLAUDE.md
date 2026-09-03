# CLAUDE.md — grill-with-docs

Este repositório **é** o plugin `grill-with-docs` e também o consome (dogfooding). As duas coisas convivem na mesma árvore, então saber o que é fonte e o que é artefato de consumo evita confusão.

## Layout

- `plugin/` — fonte publicada do plugin: `SKILL.md`, `assets/`, `scripts/`, `references/` e os dois manifests (`.claude-plugin/`, `.codex-plugin/`).
- `tests/` — validadores canônicos. `tests/run_validators.py` faz glob de `validate_*.py`, então um arquivo novo entra na suíte sozinho.
- `tests/fixtures/` — repositórios sintéticos, incluindo `.specify/` próprios. Não confundir com o `.specify/` da raiz.
- `.specify/`, `.claude/` e `.agents/skills/` na raiz — stack Claude/Codex do Spec Kit deste repositório, versionada de propósito (ver abaixo).
- `WORKFLOW.md` na raiz — workflow project-wide gerenciado, marcador `grill-with-docs-workflow:v4`.

## Rodar os testes

```bash
python3 tests/run_validators.py
```

A suíte completa roda por `tests/run_validators.py`; conte os validadores pelo marcador `==>`, pois `validate_distribution.py` usa asserções diretas e não imprime `Ran N tests`. Nenhum teste pode tocar a rede nem exigir `specify`, `node` ou `backlogctl` reais — a matriz de CI (ubuntu/windows/macos, Python 3.10 e 3.13) não tem nenhum deles. Use os seams injetáveis: `Toolchain` em `ensure_dependencies.py` e o `resolve_cli` substituível em `backlog_bridge.py`.

## Restrições do core

- Somente biblioteca padrão, Python >=3.10. Sem dependência externa.
- O core **nunca baixa bytes**. Toda instalação é delegada a quem é dono do artefato (`uv`, `specify`, o instalador verificado do plugin `backlog`) e a verificação é por versão resolvida, nunca por hash de tarball.
- Hooks são read-only e não escrevem nem acessam a rede.
- Feature e fix são plan-only e terminam em `PLAN_ONLY_STOP`. Só hotfix tem trilha executável, via `HOTFIX-GO`.

## `ESSENTIAL` do WORKFLOW.md

Cada versão gerenciada tem a **própria** tupla `ESSENTIAL`, e elas nunca são derivadas umas das outras: `ensure_workflow.ESSENTIAL` (v2), `workflow_v3.ESSENTIAL` e `workflow_v4.ESSENTIAL`. Acrescentar uma substring à tupla de uma versão marca como `incompatible workflow` todo `WORKFLOW.md` daquela versão já materializado em projeto consumidor. Uma versão nova é sempre um marcador novo com tupla nova, ao lado das anteriores — nunca uma edição da tupla existente.

O mesmo vale para os assets: v3 e v4 têm registry, catálogo (com `catalog_id` próprio) e snapshot de confiança separados. Um documento v3 fixa o digest do registry v3 na própria prosa, então repontar aquele asset seria uma queda de frota, sem diff e sem caminho de migração.

A ordem canônica de cada versão vive em `grill_core/workflow_versions.py`, que é o SSOT tabular. As tabelas são literais congelados, nunca derivadas umas das outras: derivar `SEQUENCE_V4` de `SEQUENCE_V3` pelo mapa de renomeação faria um typo no mapa reescrever a ordem canônica em vez de reprovar um teste.

## `init` e dependências

`grill_workspace.py init` fixa o `WORKFLOW.md` antes de montar o bundle e reporta o estado das dependências externas em `dependencies`. O preflight é declarado em `plugin/skills/grill-with-docs/assets/dependencies.json`.

- **backlogctl é exigido desde a 3.0.0**: `init` recusa com `BACKLOG-REQUIRED` sem backlog vinculado;
- `--runtime claude|codex` é obrigatório e seleciona o harness da sessão sem consultar o default salvo em `.specify/integration.json`;
- demais dependências: só detecta e reporta, nunca bloqueia;
- `--allow-install`: autoriza a instalação delegada e a criação/bind do backlog. Essa flag é a confirmação explícita que o contrato do backlog exige;
- `--require-dependencies`: torna a falta um `MISSING-DEPENDENCY` fail-closed;
- `--skip-backlog`: única saída para criar sem backlog. Fica carimbada em `state.json` e aparece em toda auditoria como `backlog_skipped`. `backlog-adopt ROOT --work-id ID --apply` limpa o carimbo depois do vínculo;
- `GRILL_SKIP_DEPENDENCIES=1`: desliga a detecção em ambiente air-gapped e **nunca** é reportado como `OK`.

Subcomandos auxiliares: `preflight ROOT --runtime claude|codex [--allow-install] [--skip-backlog]` e `backlog-sync ROOT --work-id ID [--apply] [--db PATH]`.

## Triagem e rotas

`triage ROOT --report LAUDO.md --route bugfix|hotfix|feature|module --severity ... [--apply]` é pré-ciclo como o `preflight` e sela a decisão de rota em `.grill/triage/<id>.json`. O core **não classifica linguagem natural** — quem interpreta o problema é a skill `code-debug`, que emite o laudo; o core verifica que o laudo declara `causa raiz comprovada` e que a evidência exigida pela rota está presente. Sem isso, `ROOT-CAUSE-UNPROVEN` e nenhuma rota abre.

A lógica pura mora em `plugin/skills/grill-with-docs/scripts/grill_core/triage.py`, que **não importa `grill_workspace`** e não toca disco: recebe texto já lido pela fronteira `safe_read_regular_fd` do CLI. Códigos são cunhados em `SCREAMING_SNAKE` e traduzidos para KEBAB por `translate_v3_code`. Contrato travado em `tests/validate_triage_contract.py`.

Desde a 3.3.0 a triagem é **consultiva**: `init` e `hotfix` ainda não a exigem. Torná-la obrigatória (`TRIAGE-REQUIRED`, `ROUTE-MISMATCH`) é a fase seguinte, e é o que faz `feature` e `fix` deixarem de ser o mesmo bundle com rótulo diferente.

## Extensões do Spec Kit

`git`, `bugfix` e `verify-review-ship` são exigidas pelo `WORKFLOW.md`. As duas últimas vivem no catálogo `community`, que é discovery-only: instalar por `--from <archive-url>` dispara um aviso interativo de fonte não confiável e aborta em modo não-interativo. Um instalador automatizado não deve responder esse aviso no lugar do humano, então `--allow-install` registra o catálogo como confiável em `.specify/extension-catalogs.yml` (`install_allowed: true`) e instala pelo nome. É uma decisão de confiança explícita e revisável no diff.

## Por que `.specify/`, `.claude/` e `.agents/skills/` são versionados

A stack do Spec Kit deste repositório está no controle de versão de propósito, para que a configuração seja reproduzível e revisável. Consequências a conhecer:

- `.specify/extensions/` carrega código de terceiros vendorizado (`bugfix` de Quratulain-bilal; `agent-assign` de xymelon permanece na árvore como histórico, já não exigido desde a 4.0.0). Atualizações de extensão aparecem como diff.
- `.specify/extensions/.cache/` é cache do catálogo e gera churn a cada refresh.
- `.agents/skills/speckit-*` materializa a integração Codex; `.claude/skills/speckit-*` mantém a integração Claude secundária.
- `.claude/settings.local.json` é override por máquina; mudanças locais de configuração viram diff.
- `.specify/memory/constitution.md` na raiz é a **Constituição gerenciada do grill**, gerada de `assets/GRILL-CONSTITUTION.template.md` e não o placeholder do spec-kit. São 9 cláusulas normativas e ela é read-only depois do bootstrap: nenhum ADR ou decisão local funciona como waiver. Duas dessas cláusulas — `Bump obrigatório do plugin` e `Release obrigatória por versão` — existem **só aqui**, não no asset: governam a distribuição deste plugin e não teriam sentido na constituição de um projeto consumidor. Emendar a Constituição é ato deliberado e caro: o hash muda e todo work item que selou o hash anterior passa a acusar `CONSTITUTION-STALE` até ser re-selado.

## Backlog

Este repositório está vinculado ao backlog `SGD` (`spec-kit-grill-with-docs`), herdado do caminho anterior do projeto. O código não coincide com o nome do diretório, então o vínculo foi feito com `backlog_bridge.py . --code SGD --apply`. Toda mutação no backlog é preview-first e exige `--apply`.

## Gates de integração

São dois workflows, e a separação é deliberada:

- `.github/workflows/ci.yml` — matriz de portabilidade (3 SOs × Python), com `paths:` restrito ao que ela cobre. Tem guarda que pula a matriz em merge de PR, porque o evento `pull_request` já testou a mesma árvore.
- `.github/workflows/bump-gate.yml` — o gate de versão, **sem** `paths:`. Ele roda em toda PR e sempre reporta.
- `.github/workflows/publish.yml` — publica no push para `main` que toca `plugin/**`. O job `release` exige o bump, cria a tag anotada imutável e, desde a cláusula `Release obrigatória por versão`, cria também a GitHub Release ancorada nessa tag. Release preexistente é sucesso; tag ausente ou ancoragem divergente reprovam. Só depois o job `publish` aponta os marketplaces.
  O job resolve um `anchor` — o commit em que a versão está publicada — e **tudo a jusante ancora nele, nunca em `github.sha`**. No push os dois coincidem. Fora do push (`workflow_dispatch`) a execução é *reconciliação*: se a tag daquela versão já existe em commit anterior, o job não remarca e também não morre — segue e garante release e marketplaces ancorados na tag. É o que permite reparar uma release perdida sem criar release à mão, que a cláusula trata como contorno. A imutabilidade segue intacta: remarcação só é tentada quando a tag não existe, e um push divergente continua reprovando.

O gate mora sozinho porque `paths:` é declarado no nível do workflow, não do job: enquanto vivia no `ci.yml`, herdava o filtro da matriz e ficava mudo nas PRs que não o casavam. Um required check mudo prende a PR para sempre.

**Registrado** (2026-08-30, SGD-4 e SGD-7): `Version bump gate` é *required status check* na branch protection de `main` em `cadugevaerd/grill-with-docs`, com `strict: true` — a PR também precisa estar atualizada em relação à base, o que fecha a ressalva da guarda de deduplicação do `ci.yml`, onde uma PR desatualizada poderia depositar árvore diferente da testada. O check está amarrado ao app do GitHub Actions (`app_id: 15368`), então um status de terceiro com o mesmo nome não o satisfaz. Ligar a proteção também passou a recusar force-push e deleção da `main`, que antes eram livres.

Nenhum commit consegue mexer nisso; é configuração do serviço, e o estado real vive só na API:

```bash
gh api repos/cadugevaerd/grill-with-docs/branches/main/protection
```

**`enforce_admins` está `false`, de propósito.** O gate bloqueia o merge de qualquer PR, inclusive as do dono, mas push direto para `main` continua permitido para quem é admin — é como o ship deste repo opera hoje. A consequência é que FR-007 vincula o caminho de PR, não o de push: quem tem admin ainda contorna. Tornar a cláusula constitucional realmente vinculante é `enforce_admins: true`, um `PATCH` de uma linha, ao custo de todo ship passar a exigir PR.

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

## Project Learnings

- **`EXIT_BLOCKED=2` com payload ≠ exit 2 puro do argparse**: argparse usa exit code 2 para os próprios erros de parsing. Um contrato de CLI que espera `EXIT_BLOCKED=2` precisa checar o payload, não só o código de saída — senão confunde bloqueio legítimo com erro de parsing (`specs/025-status-timeout-false-positive/tasks.md`, T005/T006).
- **Estado Git live resolve uma vez por worktree, não uma vez por work item**: comandos que iteram work items e precisam de estado Git (branches, status) devem resolver esse estado uma vez por worktree e passá-lo por parâmetro, não reconsultar por item — custo O(items) de subprocessos Git é o bug a evitar (`plugin/skills/grill-with-docs/scripts/grill_core/grill_status.py`).
