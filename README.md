# grill-with-docs

**v6.0.19 · MIT**

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

Inicie a skill GWD na própria sessão: `$grill-with-docs iniciar ROOT` ou `$grill-with-docs retomar ROOT` no Codex; `/grill-with-docs iniciar ROOT` ou `/grill-with-docs retomar ROOT` no Claude Code. `ROOT` é o Git root real; selecione o `work_id` quando houver mais de um. A sessão principal recebe recomendação Sol no Codex ou Opus no Claude, sem troca automática de modelo.

Pelo contrato, o entrypoint deve conduzir o bootstrap antes da primeira resposta de trabalho, obter observações da sessão e só continuar com `work_ready` validado; a limitação atual de init/adopt está descrita abaixo. Para inspecionar o estado sem iniciar trabalho:

```bash
CORE="$PLUGIN_ROOT/skills/grill-with-docs/scripts/grill_workspace.py"
python3 "$CORE" status "$PWD"
python3 "$CORE" status "$PWD" --format markdown
```

O formato padrão é JSON. O Markdown é a resposta humana canônica: `all good` quando não há pendências ou a tabela estável de work items pendentes, reproduzida integralmente.

`init` exige `--runtime claude|codex` e `--session-ref REF`; uma string inventada não comprova a sessão. Ele preserva o bootstrap de WORKFLOW/Constituição e o vínculo com backlog existente, reconhecido em todas as worktrees registradas. `--skip-backlog` mantém seu carimbo auditável. `--allow-install` autoriza somente a instalação delegada pelas superfícies proprietárias; o core nunca baixa bytes. As dependências anteriormente consultivas mantêm sua semântica e `--require-dependencies`; o requisito de apresentação abaixo é obrigatório no fluxo novo, mesmo sem essa flag. `GRILL_SKIP_DEPENDENCIES=1` não satisfaz esse requisito.

**Limitação atual:** na fonte `5bc9500e6fff10fce5353f758fdc334e490a3523`, `init` e `gauntlet-orchestration-adopt` podem criar contexto `ACTIVE` com uma string `session_ref`, sem observação de sessão correlacionada e sem `presentation`. O guard de autoridade compara contexto/época/estado e igualdade da string; sem apresentação, o guard retorna `{"legacy": true, "work_ready": true}`. Sucesso de init/adopt, contexto ACTIVE e esse fallback não provam a sessão nem a apresentação obrigatória. O bootstrap acima é obrigação normativa, ainda não garantida por esses handlers: manter trabalho dependente bloqueado até remediação delimitada do core e revalidação, pré-condições dos aceites funcionais posteriores.

Feature/fix terminam em `PLAN_ONLY_STOP`; a implementação pertence ao ciclo externo, com suas skills canônicas e gates. Hotfix conserva a trilha `HOTFIX-GO`, com reprodução, evidência, teste de correção, rollback e evidência constitucional.

## Oito requisitos do contrato 6.0.0

O suplemento `grill-agent-orchestration/v1` define as seguintes obrigações. Esta documentação descreve o contrato da candidata; presença de comandos ou checks offline não declara os caminhos live aprovados.

| Requisito | Comportamento e recusa |
|---|---|
| 1. Cleanup seguro | Fechamentos de etapa/wave e preparação de troca limpam recursos elegíveis, inclusive em runs COMPLETE. Persistir resultado/diagnóstico antes de fechar sessão, inclusive falha e read-only; confirmar cada recurso ou registrar preservação/UNKNOWN. |
| 2. Escrita explícita | `Files:` JSON é a única autoridade do grant, incluindo raiz, novos arquivos e `./`; a prosa não concede escrita. `Result:` de tarefa despachável consta em Files; sem sidecar implícito. Declaração inválida bloqueia sem grant parcial. |
| 3. Continuidade | Codex↔Claude na mesma worktree usa checkpoint coerente, quiescência observada e nova época via CAS. Preserva outputs/efeitos aceitos e repete somente tentativa não aceita; worker ativo ou efeito desconhecido bloqueia. |
| 4. Orientação do líder | Início e retomada recomendam Sol/Opus conforme runtime; `active_model_changed=false`. Recomendação não altera configuração nem a seleção obrigatória dos especialistas. |
| 5. Autoria técnica | Todo COMO, inclusive entrevista, plan, tasks e design, requer autor `gpt-6-astra/xhigh` no Codex ou `fable/xhigh` no Claude. Verificar identidade/modelo/esforço efetivos antes do payload; capacidade insuficiente bloqueia. |
| 6. Revisão independente | Todo julgamento de requisitos, plano, tasks, design, código ou segurança requer o mesmo modelo obrigatório do runtime com `high`, em sessão distinta de todos os autores dos bytes. Teste determinístico não substitui revisão. |
| 7. Prévia frontend | Design ocorre dentro de plan, com Impeccable observado, HTML autocontido, capturas PNG, manifest e revisão independente. Tasks exige aprovação humana do digest atual; alteração invalida aprovação. Sem frontend coerentemente classificado: `NOT_APPLICABLE`. |
| 8. Apresentação local | GWD carrega i-have-adhd por padrão em início/retomada nos dois CLIs, sem invocação manual, mantendo conteúdo completo, Ponytail e sessões externas. Instalação, habilitação, carga e comportamento são evidências distintas. |

As onze macroetapas permanecem `specify → plan → checklist → tasks → analyze → partition → implement-parallel → converge → verify → review → ship`. O líder invoca a skill canônica na sessão ativa, coordena e registra a evidência; especialistas não escrevem `.grill/` ou `.specify/reports/`, nem fecham macroetapas. Workers de implementação conservam o binding não-frontier por tier. Suplemento, template e apresentação são argumentos da mesma invocação, sem substituir skills ou pins v3/v4.

## Stack e alcance da apresentação

Ponytail >=4.9.0 mantém a política de implementação. `i-have-adhd@i-have-adhd` >=0.3.0 é obrigatório, instalado e habilitado no runtime efetivo; a policy aprova separadamente versão e hash dos bytes instalados. A versão inicialmente admitida é 0.3.0. Uma versão maior instalada não autoriza conteúdo ainda não revisado.

O bootstrap resolve a instalação selecionada pelo harness, confirma habilitação/confiança, lê integralmente o SKILL.md aprovado apontado por `presentation.load_request` e correlaciona o evento à sessão, geração, configuração e root. `STYLE-LOAD-UNCONFIRMED` com pedido de carga íntegro indica o próximo passo do bootstrap; depois da leitura observada, revalidar a entrada. Se o binário ou adapter não oferecer essa continuação, diagnosticar o impedimento e bloquear trabalho dependente; não fabricar loaded. `use_ready=true` permite aplicação ativa, mas não prova `functional_verified`.

Compactação ativa exige recarga corrente. `stop adhd mode` suspende somente a apresentação na mesma sessão/incarnation/escopo: revalidar fonte humana e pré-requisitos, permitir `work_ready=true` sem reinjeção, com `use_ready=false` e `functional_verified=false`. Nova sessão, inclusive especialista ou destino de retomada, inicia ativa com carga própria. Saída explícita do GWD produz `out_of_scope` e preserva o padrão externo. O limite de apresentação nunca omite requisitos, achados, arquivos, checks ou conteúdo solicitado; artefatos mantêm seus formatos integrais.

A GWD lê a referência; não auto-invoca a skill upstream nem executa seu hook. Não cria `.i-have-adhd-always`, instrução global ou override de diretório de configuração. Consumidores não recebem edição automática de AGENTS/CLAUDE; neste repositório há apenas a instrução local de bootstrap. Aprovação válida já concedida não é pedida novamente sem mudança real; disabled ou conflito novo requer diagnóstico específico e controle nativo autorizado, sem reinstalar para sobrepor a escolha.

## Verbos, migração e rollout

| Verbo | Responsabilidade |
|---|---|
| `preflight`, `init`, `gauntlet-orchestration-adopt` | Pré-requisitos, contexto novo ou adoção explícita com escopo exato; adoção usa preview e apply com hash esperado. |
| `gauntlet-step-enter`, `gauntlet-activity` | Admitir entrada canônica; preparar, liberar payload e aceitar atividade correlacionada com autor/revisor ou check determinístico. |
| `gauntlet-cleanup`, `gauntlet-prepare-switch`, `gauntlet-resume` | Reconciliar recursos, cercar despachos e preparar/retomar checkpoint sem concorrência nem repetição de efeito aceito. |
| `gauntlet-preview`, `gauntlet-preview-decide` | Registrar prévia revisável e decisão humana observada vinculada ao digest apresentado. |
| `task-files-migrate`, `partition-emit`, `gauntlet-partition-brief`, `gauntlet-tasks-reconcile` | Aplicar proposta de tasks revisada, gerar grants exatos e reconciliar apenas resultados atribuídos e aceitos. |

O [protocolo de sessão](plugin/skills/grill-with-docs/references/session-protocol.md) detalha ordem, recusas e recuperação; os contratos completos ficam em [spec 030](specs/030-agent-orchestration/contracts/cli.md). Conferir `--help` do binário efetivamente selecionado; forma ausente ou divergente é lacuna a resolver antes do rollout, nunca licença para pular o guard.

6.0.0 é mudança major: trabalho legado continua legível/auditável, mas execução no binário novo exige adoção explícita. Migrar tasks exige proposta completa de autor xhigh revisada por high, preview e hashes correntes; não inferir Files do texto antigo. DAG selado, inclusive de run COMPLETE, conserva bytes e receipts. Continuação usa revisão/run sucessora explícita, importando aceites verificados e nodes somente para trabalho restante.

Em cada fase, convergir workers e aceitar read-only/deferred na ordem declarada antes de avançar; fases sem workers também formam barreiras. `TASK-PHASE-PENDING` impede fases posteriores e a última fase pendente impede conclusão. `Files: []` não cria worker/grant; tarefa com evidência reservada é inteira deferred ao líder. Sem nenhuma tarefa despachável, `PARTITION-NO-WORKERS` interrompe antes de admissão/DAG-VALID/checkpoint; não fabricar worker para satisfazer a classe `worker-required`.

Cleanup exige identidade comprovada; worktree/branch só saem com trabalho integrado, árvore limpa e nenhuma evidência exclusiva. Persistir intenção, executar pela superfície proprietária e confirmar por read-back; não usar force/clean/reset nem presumir close por silêncio. Recursos preservados têm motivo por recurso. `STEP-ACCEPTED-CLEANUP-PENDING` mantém a etapa aceita: retry drena cleanup, sem repetir a etapa. `UNKNOWN` de sessão impede afirmar quiescência.

O ciclo que constrói 6.0.0 termina com seu bundle histórico preservado, CLI absoluto e hashes/pins revalidados; a candidata é ensaiada em projeto e sessões isolados. Não atualizar/adotar a campanha histórica no meio do ciclo. Depois de ship encerrado, adoção explícita de work item COMPLETE importa referências e inventário sem reabrir etapas ou reatestar o passado. Bump consistente, verify, revisão independente e autorização humana de ship continuam obrigatórios; o pipeline cria tag imutável e GitHub Release no mesmo anchor antes de atualizar marketplaces.

## Limites e compatibilidade

- A Constituição existente é preservada e tratada como read-only.
- Hooks apontam somente para o diretório instalado via `PLUGIN_ROOT`/`CLAUDE_PLUGIN_ROOT`.
- Python 3.10+ e biblioteca padrão; os testes do repositório rodam com Python 3.13.
- O plugin não publica código, não executa o fluxo normal de implementação e não faz ship externo automaticamente.

## Desenvolvimento local

Os validadores canônicos ficam em `tests/`. A suíte usa fixtures/seams offline, sem rede nem CLIs reais dos harnesses; execute:

```bash
python3 tests/run_validators.py
python3 tests/validate_distribution.py
git diff --check
```

Conte validadores pelo marcador `==>` e registre failures/skips reais. Distribuição verifica os oito pontos 6.0.0 e um único heading de CHANGELOG. O [quickstart](specs/030-agent-orchestration/quickstart.md) exige também orquestração live e estilo C1/C2/A1/A2, compactação, suspensão e controles externos nos dois CLIs, com revisão high independente; teste offline, instalação ou recusa correta não substituem esse aceite. Registros são evidência estrutural auditável, sem prova criptográfica de execução de modelo ou skill.

Consulte `CHANGELOG.md` para o histórico cumulativo.
