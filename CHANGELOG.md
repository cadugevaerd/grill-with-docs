# Changelog

## 2.9.0

Destrava a ponte com o backlog operacional. Desde a 2.5.0 a integração existia e não funcionava: dos 8 `BL-NNNN` registrados em 4 work items deste repositório, apenas 1 chegou ao backlog. Três defeitos independentes, todos reproduzidos antes da correção.

- `backlog-sync` deixa de recusar work item cujos artefatos foram escritos depois do `init`. O comando validava o bundle contra `initial_artifacts`, o retrato dos templates no instante da criação, de modo que registrar uma decisão adiada — o único motivo para rodá-lo — invalidava a própria pré-condição. Passa a validar a identidade imutável, que é a garantia que de fato importa. `BUNDLE-INTEGRITY` continua ativo nos três comandos que legitimamente exigem bundle intocado.
- O espelho passa a cobrir decisões em **qualquer** estado. O filtro anterior só considerava `open`, enquanto o auditor reprova fase com decisão aberta; as duas regras somadas faziam a janela de espelho coincidir com a janela bloqueada, e um marco fechado não tinha mais nada a espelhar.
- Mapa de estados derivado da FSM real do `backlogctl`, medida nos 25 pares: o item nasce em `in_progress`, `resolved` vira `done` e `superseded` vira `cancelled`. `open → done` é ilegal, o que invalida o mapa direto. Nenhum estado fictício é gravado. Consequência visível: decisão adiada em aberto aparece como `in_progress`, não `open`.
- Deduplicação por `(work_id, BL-NNNN)`, porque o armazenamento aceita duplicata sem erro. Reexecutar deixou de poder poluir o backlog.
- Reconciliação de estado com desfecho explícito por decisão: `PROPOSED`, `APPLIED`, `REUSED`, `TRANSITIONED` e `TRANSITION-REFUSED`. O último cobre estado desejado inalcançável a partir do atual — a ponte relata e não toca o item, nunca recorrendo a `item reconcile-status`, que o contrato do backlog proíbe como transição comum.
- Toda recusa de pré-condição ocorre antes da primeira mutação. Não há transação entre chamadas sucessivas: a garantia oferecida é de convergência, não de atomicidade, e está declarada no contrato.
- 26 testes novos em `tests/validate_backlog_contract.py`, todos pelo seam `resolve_cli`, sem exigir `backlogctl` real.

## 2.5.0

- `init` passa a fixar o `WORKFLOW.md` project-wide antes de montar o bundle. Antes o encadeamento era manual e um `WORKFLOW.md` ausente virava `sha256: null` no `WORK-ITEM.json`; agora ausência materializa o template e conteúdo incompatível bloqueia com `WORKFLOW-UNAVAILABLE`.
- Preflight de dependências declarado em `assets/dependencies.json` e executado por `scripts/ensure_dependencies.py`: Python, `git`, Spec Kit (CLI, scaffold e as extensões `git`, `agent-assign`, `bugfix`, `verify-review-ship`) e `backlogctl`. O core nunca baixa bytes — cada instalação é delegada a quem é dono do artefato e verificada por versão.
- `init` reporta as dependências sem bloquear. `--allow-install` autoriza a instalação delegada, `--require-dependencies` torna o gate fail-closed e `--skip-backlog` desliga a integração. `GRILL_SKIP_DEPENDENCIES=1` desliga a detecção em ambiente air-gapped e nunca conta como `OK`.
- Novos subcomandos `preflight` e `backlog-sync`.
- As extensões community do Spec Kit passam a ser instaladas a partir de um catálogo declarado confiável em `.specify/extension-catalogs.yml`, em vez de responder automaticamente ao aviso interativo de fonte não confiável do `--from <archive-url>`.
- Integração com o plugin `backlog` via `scripts/backlog_bridge.py`: bind do repositório ao backlog correspondente e espelho dos BL abertos como itens. Preview-first — nada muta sem `--apply`/`--allow-install`, que é a confirmação explícita exigida pelo contrato do backlog. Só fala `backlogctl --json`, nunca SQLite.

## 2.4.1

- Extração do plugin para um repositório público autocontido, sem mudança funcional.
- Catálogos e manifests públicos alinhados à versão 2.4.1.
