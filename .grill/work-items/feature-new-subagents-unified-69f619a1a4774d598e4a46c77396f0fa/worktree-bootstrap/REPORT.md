# HOW operacional — contexto das worktrees históricas

Autor despachado: tarefa `task_5420e3c387cb`, dispatch `ctx_8d89266843c0`; perfil solicitado pelo coordenador Astra/xhigh. Esta análise não fornece observação independente do modelo efetivo. Revisão high distinta e aplicação pertencem ao líder.

**Resultado: a hipótese funciona para fornecer inputs e integrar duas fases com o core histórico 5.4.1, com precondições abaixo.** O menor procedimento é commit pelo líder dos artefatos existentes, `gauntlet-worker-declare` canônico na base original, fast-forward pelo líder ao commit integrado observado antes de qualquer payload e, depois, trabalho estritamente no grant. Não há verbo histórico específico para esse fast-forward: é operação Git local de preparação do líder entre declare e dispatch, não nova atestação nem alteração do schema. A prova não autoriza uso indiscriminado de merge-base como evidência de autoria. O fluxo permite prosseguir até converge, mas **não oferece replay de declare nem cleanup canônico após avanço de HEAD**; preservar worktrees é a saída histórica compatível, não resetar identidade para fazê-las parecer exatas.

## Escopo e prova executada

Nenhum arquivo do projeto, índice, branch, run, activation, pin, DAG, skill ou estado real foi editado. Não houve rede, instalação, baseline completo, macroetapa/atestação, worker/wave real nem subagente. Somente leitura e um repositório Git sintético temporário, removido ao concluir. Permanecem neste diretório temporário o script reproduzível, resultados e snapshots de leitura para a revisão.

Executado: `PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 /tmp/grill-how-H4WGPU/proof.py` — exit 0, 14 observações/asserts agrupadas em `proof-result.json`. Imports do bundle absoluto 5.4.1, com verificação de seus 58 hashes; funções reais `admit_or_reuse_run`, `declare_wave`, `declare_worker`, `record_progress`, `terminate_worker`, `converge_wave`, `cleanup_worker` e helpers Git/Store. A admissão da fixture é sintética; **não é prova de nova ativação da campanha real pela CLI**. Os helpers Bash são os bytes reais versionados. Toda chamada mutável recebeu apenas o Git temporário.

A prova mostrou:

1. `B → P` (commit do líder); worker 1 nasce em B, FF para P, diff próprio inicialmente vazio, implementa A + sidecar; terminate/converge aceitam e produzem E1 com merge `--no-ff`.
2. Worker 2 nasce novamente em B sem A; FF para E1 disponibiliza planejamento + A; implementa B + seu sidecar. Merge-base com executionHEAD é E1 e o diff próprio contém exatamente os dois arquivos concedidos. Converge chega a COMPLETE, mantendo a base B em toda admissão/evento Gauntlet.
3. Alteração própria de `.grill/context.md` posterior ao FF é `GRANT-SCOPE-VIOLATION` antes de qualquer merge. Entretanto alteração seguida de revert desaparece do **diff líquido** e seria aceita pelo core; o histórico por commit revela essa escrita. O revert ocorreu somente na fixture para provar essa limitação, não é remédio proposto.
4. Replay de declare após FF retorna `WORKSPACE-PRESERVED`, mantendo PREPARED. `merge --ff-only E` depois de trabalho próprio pode retornar sucesso como no-op com HEAD diferente de E; por isso exit 0 sozinho não prova bootstrap.
5. Commit comum e worktrees não mudam project_id derivado dos root commits. Cleanup preserva o worker avançado; depois de COMPLETE retorna `RUN-NOT-ELIGIBLE`. O helper histórico de limpeza ignora arquivos ignorados por Git.
6. Sem planejamento, o helper encontra a feature anterior; após FF encontra 030 e permanece limpo. Override divergente de `SPECIFY_FEATURE_DIRECTORY` escreve `feature.json`. `--paths-only` não escreve, mas aceita diretório inexistente e não valida plan/tasks.
7. Mudança rastreada pendente em `.specify/feature.json` no líder gera `EXECUTION-TREE-DIRTY`. Snapshots imediatamente antes/depois da prova conferiram igualdade de HEAD, refs, índice, worktrees, status e SHA-256 de todos os arquivos reais rastreados/não ignorados.

## Observação real e fontes

Campanha `run-b12537dfc4dca1621cc1f08d`, base `6ad0dc2807c74fe37af52207700620dd02e8cbd0`; execution branch vinculada `cadugevaerd/feat-new-subagents`. Run ADMITTED, zero workers; só o placeholder `wave-0001/DECLARED/pending-declaration`, nenhuma wave efetiva. O pin de conteúdo do DAG ainda **não existe na run**: será estabelecido pelo primeiro declare de wave canônico. Isso não autoriza editar o DAG nem gravar o pin manualmente; o digest já validado é o esperado.

`gauntlet_runs.py` do bundle 5.4.1:

- 1020–1095: identidade derivada de common Git dir, path/branch/base exatos; EXACT exige HEAD igual à base.
- 1158–1173 e 1294–1398: admissão live compara quatro digests; eventos e workspace usam admissão original; `worktree add` ancora nela; replay PREPARED revalida igualdade exata.
- 1430–1517: declarar pelo DAG; modelo derivado; wave ativa e dependências terminais.
- 1621–1752: progress e terminate não revalidam equality de HEAD/base nem o diff/clean; sucesso terminal isolado não prova integração.
- 1941–1998: cleanup exige flags e Git EXACT; não é elegível depois de COMPLETE por `_run_for_worker`.
- 2023–2031: nome real é **`_branch_changed_paths`**, não `_worker_changed_paths`; calcula `merge-base HEAD branch` e diff líquido até branch.
- 2184–2332: converge compara digests, ancora eventos na admissão gravada, confere execution branch/clean/DAG pin, diff próprio versus grant e então merge serial.
- `store.py:504`: project_id pelos root commits de `rev-list --max-parents=0 --all`; `:816` exige workspace.base_commit igual ao da admissão.
- `grill_workspace.py:2614–2700`: cada operação pela CLI refaz prova live da ativação; `:2843–2875` gera brief; `:2973–3000` lê binding de execution branch do WI do ROOT fornecido.

`common.sh:58–70,163–227` resolve ROOT/feature e persiste override; `check-prerequisites.sh:81–140` opta por `--no-persist` só no paths-only. `speckit-implement` exige prerequisites normais, leituras de plan/tasks/contratos/constituição; seus passos genéricos de ignore files e marcar tasks não ampliam o grant do brief. A skill histórica `grill-implement-parallel` restringe sidecar, veda tasks.md/checkpoint, verifica checklists/hooks e exige declare canônico. Hooks before/after implement locais são opcionais; checklist observado 43/43 conforme registro do líder.

## Protocolo para o líder aplicar após revisão

### 1. Preparar um commit de contexto sem alterar bytes de identidade

Revalidar o bundle histórico de `cycle-toolchain-5.4.1.json`, os digests em `observations.json`, ausência de workers/waves efetivos e o binding Git. Usar Git sem locks opcionais nas leituras. ROOT é sempre a worktree de execução real para **operações de campanha**; os arquivos herdados no worker não são a fonte de estado live do coordenador.

```bash
set -euo pipefail
ROOT=/home/carlosaraujo/orca/workspaces/grill-with-docs/feat-new-subagents
WI=feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa
RUN=run-b12537dfc4dca1621cc1f08d
BASE=6ad0dc2807c74fe37af52207700620dd02e8cbd0
DAG=specs/030-agent-orchestration/execution-dag.json
HIST=/home/carlosaraujo/.codex/plugins/cache/grill-with-docs/grill-with-docs/5.4.1
CLI="$HIST/skills/grill-with-docs/scripts/grill_workspace.py"
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0

test "$(git -C "$ROOT" branch --show-current)" = cadugevaerd/feat-new-subagents
test "$(git -C "$ROOT" rev-parse HEAD)" = "$BASE"
git -C "$ROOT" diff --cached --exit-code
```

Commite somente a lista de artefatos **existentes e revisados**, depois de registrar SHA-256 por arquivo e conferir o staged diff. O mínimo para conteúdo e prerequisites é `specs/030-agent-orchestration/**` e o `feature.json` já apontando para 030; a `.grill/gauntlet.yaml` rastreada também precisa ser commitada nos mesmos bytes para não bloquear converge. O WI existente pode acompanhar como contexto de leitura e para preservar os artefatos atuais, conforme hipótese aprovada. Não incluir `.git/grill`, outputs técnicos ainda inexistentes nem qualquer arquivo criado por worker. Não usar `git add -A`.

```bash
git -C "$ROOT" add -- specs/030-agent-orchestration .specify/feature.json .grill/gauntlet.yaml \
  ".grill/work-items/$WI"
git -C "$ROOT" diff --cached --name-status
git -C "$ROOT" diff --cached --check
# Após comparar staged blobs à lista/hashes aprovados, efetuar o commit do líder:
git -C "$ROOT" commit -m "docs: record approved orchestration planning context"
PLAN_HEAD=$(git -C "$ROOT" rev-parse HEAD)
test "$(git -C "$ROOT" rev-parse HEAD^)" = "$BASE"
git -C "$ROOT" diff --exit-code
git -C "$ROOT" diff --cached --exit-code
```

Este relatório não executou esses comandos mutáveis. Novos registros do líder adicionados antes da aplicação exigem reobservação da lista do WI; commits não alteram os bytes/hash de activation, WORK-ITEM ou workflow. Se hooks Git mudarem bytes ou acrescentarem arquivos, parar e revisar. Tracked dirt em registros do líder deve estar commitada antes de converge; durante cada payload, manter executionHEAD fixo para impedir ingresso lateral de efeitos do worker. Sem stash, reset de execution branch, commit órfão ou reativação/re-admissão: `gauntlet-run` depois de avançar HEAD pode criar outra run, pois a chave de admissão inclui base_commit.

### 2. Declarar a wave e o worker; só depois avançar o contexto

Primeira fase usa `NODE=p01-a`; seguintes usam nó exato e `depends_on` do DAG. Exigir não só dependências TERMINAL, mas todas já `workspace.converged=true` e seus commits contidos em executionHEAD. O DAG real tem largura 1 e cadeia de 11 nós: não despachar fase seguinte antes de converge da anterior. Não chamar implementação por código candidato; continuar controlando a campanha pela CLI absoluta histórica.

```bash
NODE=p01-a
E=$(git -C "$ROOT" rev-parse HEAD)
git -C "$ROOT" merge-base --is-ancestor "$BASE" "$E"
python3 "$CLI" gauntlet-wave-declare "$ROOT" --work-id "$WI" --run-id "$RUN" \
  --dag "$DAG" --node-id "$NODE"
# Guardar o wave_id efetivamente devolvido; primeira wave deve ser wave-0001.
WAVE=wave-0001
```

Abaixo o argv do declare é derivado do DAG para não converter vários arquivos em uma string com vírgulas nem inventar grants/tier. O líder deve guardar stdout e conferir `WORKER-PREPARED`, worker_id/node_id, base, modelo e a leitura live do registro PREPARED antes de prosseguir.

```bash
python3 - "$ROOT" "$CLI" "$WI" "$RUN" "$WAVE" "$DAG" "$NODE" <<'PY'
import json, subprocess, sys
root, cli, wi, run, wave, dag, node_id = sys.argv[1:]
doc = json.load(open(root + '/' + dag))
node = next(n for n in doc['nodes'] if n['id'] == node_id)
argv = [sys.executable, cli, 'gauntlet-worker-declare', root,
        '--work-id', wi, '--run-id', run, '--wave-id', wave,
        '--dag', dag, '--node-id', node_id, '--tier', node['tier']]
for path in node['files']:
    argv += ['--files', path]
subprocess.run(argv, check=True)
PY
```

Derivar path do common Git dir e confrontar com registro canônico, sem renomear/mover/recriar a worktree:

```bash
COMMON=$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir)
W="$COMMON/grill/wt-$RUN-$NODE"
WB="grill/$WI/$RUN/$NODE"
test ! -L "$W"
test "$(git -C "$W" rev-parse --show-toplevel)" = "$W"
test "$(git -C "$W" branch --show-current)" = "$WB"
test "$(git -C "$W" rev-parse HEAD)" = "$BASE"
test "$(git -C "$ROOT" rev-parse HEAD)" = "$E"
test -z "$(git -C "$W" status --porcelain=v1 --untracked-files=all)"
test -z "$(git -C "$W" ls-files --others --ignored --exclude-standard)"
git -C "$ROOT" worktree list --porcelain
# Conferir uma única inscrição para W/WB; PREPARED e lease/fence do worker intactos.
git -C "$W" merge --ff-only "$E"
test "$(git -C "$W" rev-parse HEAD)" = "$E"
test "$(git -C "$ROOT" rev-parse HEAD)" = "$E"
test -z "$(git -C "$W" status --porcelain=v1 --untracked-files=all)"
test -z "$(git -C "$W" ls-files --others --ignored --exclude-standard)"
git -C "$W" diff --exit-code "$E" HEAD
```

**Antes de payload**, guardar uma observação externa aos grants: UTC, run/work_id/wave/node, Task/Dispatch Orca, path/branch/common-dir, base B, E/árvore de E, HEAD/árvore do worker, grants/tier/modelo devolvidos, lease/fence, digests de DAG/brief/planejamento e dependências convergidas. Registrar o sucesso de PREPARED antes do FF e o resultado completo do FF. A observação do bootstrap pertence ao líder; não inventa campo/receipt dentro da run. Igualdade HEAD=E prova que não existe commit próprio anterior ocultado como contexto. Esses dados podem ficar no artefato de coordenação externo já usado pelo líder; se gravados em arquivo rastreado do ROOT, sua sujeira deve ser tratada sem modificar E durante o payload.

### 3. Resolver os prerequisites da worktree certa sem escrita

Executar a partir de W; o estado herdado `feature.json` já deve conter `specs/030-agent-orchestration`. Sanitizar overrides da sessão. **Não** usar `SPECIFY_INIT_DIR="$ROOT"` nos comandos técnicos: isso redireciona operações de Spec Kit à worktree do líder. `SPECIFY_FEATURE` muda apenas o identificador exibido, não resolve feature_dir.

```bash
(
  cd "$W"
  env -u SPECIFY_FEATURE_DIRECTORY -u SPECIFY_FEATURE \
    SPECIFY_INIT_DIR="$W" \
    bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
)
```

Exigir `FEATURE_DIR` exatamente `W/specs/030-agent-orchestration`, tasks em AVAILABLE_DOCS, presença de spec/plan/tasks/checklists/contratos esperados e igualdade de seus hashes com E. Antes/depois, `feature.json` e status do worker devem ser idênticos/limpos. `--paths-only` isolado não é gate de prerequisites. Não rodar setup-plan/setup-tasks, copiar templates, rebindar, alterar `feature.json`, instalar skills nem refazer fases completas. Helpers e templates existentes são inputs herdados. A chamada real de speckit-implement também deve receber esse cwd/ambiente, além do brief canônico abaixo.

```bash
python3 "$CLI" gauntlet-partition-brief "$ROOT" --dag "$DAG" --node-id "$NODE" \
  --report specs/030-agent-orchestration/partition-report.json
```

Passar o brief como `$ARGUMENTS`, preservando tasks atribuídas, paths e sidecar. O escopo explícito proíbe edição de ignore files fora do grant, tasks.md, `.grill/`, `.specify/reports/` e qualquer artefato de coordenação; ausência de prerequisite necessário fora do grant é diagnóstico para o líder, nunca correção silenciosa. Hooks opcionais não são autorização de auto-commit global. Processo técnico não escreve no ROOT do coordenador. Progress/terminal da campanha precisam resolver o ROOT canônico do líder e sua CLI histórica; delegar sua emissão ao líder a partir de progresso observado mantém a fronteira de coordenação e evita confiar no `state.json` herdado e possivelmente obsoleto no worker.

### 4. Antes de terminal/converge: cercar todo efeito próprio

O líder exige processo parado, HEAD do worker observado e execução ainda em E; **não atualizar E após ver output**. Worker commita só o grant; nenhuma entrada lateral em execution branch antes da conferência/converge. Não aceitar cherry-pick/merge prévio de output do worker no líder como “herança”.

```bash
WH=$(git -C "$W" rev-parse HEAD)
test "$(git -C "$ROOT" rev-parse HEAD)" = "$E"
test "$(git -C "$W" branch --show-current)" = "$WB"
git -C "$W" merge-base --is-ancestor "$E" "$WH"
test "$(git -C "$ROOT" merge-base HEAD "$WB")" = "$E"
test -z "$(git -C "$W" status --porcelain=v1 --untracked-files=all)"
test -z "$(git -C "$W" ls-files --others --ignored --exclude-standard)"
git -C "$W" diff --check "$E" "$WH"
```

Comparar com o grant exatamente derivado de node.files, tanto o diff líquido quanto **cada commit** próprio; o teste abaixo também recusa commits de merge próprios, pois não são necessários ao procedimento serial e podem obscurecer autoria:

```bash
python3 - "$ROOT" "$W" "$DAG" "$NODE" "$E" "$WH" <<'PY'
import json, subprocess, sys
root, worker, dag, node_id, inherited, head = sys.argv[1:]
node = next(n for n in json.load(open(root + '/' + dag))['nodes'] if n['id'] == node_id)
grant = set(node['files'])
def git(*args):
    return subprocess.check_output(['git', '-C', worker, *args])
def changed(*args):
    return {p.decode() for p in git(*args).split(b'\0') if p}
assert not git('rev-list','--min-parents=2', inherited+'..'+head).strip(), 'own merge commit'
own = changed('diff','--no-renames','--name-only','-z',inherited,head)
assert own <= grant, ('net diff outside grant', sorted(own-grant))
for commit in git('rev-list', inherited+'..'+head).decode().split():
    paths = changed('diff-tree','--no-commit-id','--no-renames','--name-only','-r','-z',commit+'^',commit)
    assert paths <= grant, ('commit outside grant', commit, sorted(paths-grant))
print(json.dumps({'node_id':node_id,'input_head':inherited,'output_head':head,'own_paths':sorted(own)}))
PY
```

Guardar resultado, commits/árvores/diffs, sidecar e checks técnicos reais. A inspeção de commits detecta efeito protegido revertido depois; hashes dos inputs herdados devem continuar iguais onde não há grant. Limite explícito: Git/digests não provam ausência de escrita transitória não commitada contra um executor malicioso, nem isolam o common Git dir por ACL. O contrato histórico é estrutural/cooperativo. Não alegar sandbox de segurança ou rastreamento de syscall que não existem; qualquer escrita fora do grant observada invalida o worker mesmo que revertida.

Só após esses controles, o líder emite terminal com a observação de sucesso e faz converge canônico **na mesma executionHEAD E**, usando o DAG explícito (o exemplo abreviado da skill omite `--dag`, mas a CLI o exige):

```bash
python3 "$CLI" gauntlet-worker-terminal "$ROOT" --work-id "$WI" --run-id "$RUN" \
  --worker-id "$NODE" --outcome completed
python3 "$CLI" gauntlet-converge "$ROOT" --work-id "$WI" --run-id "$RUN" \
  --wave-id "$WAVE" --dag "$DAG"
```

Conferir `workspace.converged=true`, wave convergida e novo executionHEAD contendo WH; esse commit passa a ser o input E da fase seguinte. Preservar histórico original: todos os merges da campanha seguem o core 5.4.1. Nenhuma macroetapa/reconciliação de tasks é concedida ao worker por este HOW.

## Replay, interrupção e reversibilidade

- **Antes de PREPARED confirmado:** o FF é proibido. Resposta perdida de declare exige read-back; não avançar um PREPARING. Um FF nesse intervalo causa ORPHANED no reconcile. Não forjar flags/base nem recriar recursos para limpar o erro.
- **Depois de PREPARED, antes do FF:** replay idêntico de declare funciona se a worktree continua exatamente em B; ainda assim observar estado antes de repetir qualquer chamada.
- **Depois do FF, antes do payload:** não redeclarar; verificar a observação externa pré-payload, path/branch/base gravados, run PREPARED, worker HEAD=E e ausência de dirt. O FF pode ser constatado por HEAD/árvore e registro Git mesmo se stdout se perdeu. Ausência de prova de que o payload não começou impede classificá-lo como contexto limpo.
- **Depois do payload:** nunca executar segundo bootstrap, reset/rebase, trocar base gravada, ajustar pins/grants, ou elevar E ao HEAD do worker para fazê-lo desaparecer do diff. Preservar e reportar divergências; o grant não cresce.
- **Cleanup:** o worker com commits próprios já falharia EXACT mesmo sem FF; não é incompatibilidade nova específica da hipótese. O default `cleanup_eligible=false` também impede remoção. Não existe caminho demonstrado de cleanup automático para estes HEADs avançados na 5.4.1, e COMPLETE bloqueia a entrada. Retenção é resultado previsto; se remoção canônica for requisito do aceite deste HOW, o veredito passa a **NO-GO nesse requisito**, não um reset a B.
- **Reversibilidade:** nenhum ref é forçado e nenhum commit original é removido pelo procedimento. O commit de planejamento pode ser revertido por ato Git futuro do dono quando não houver execução ativa; isso reintroduziria os bloqueios de prerequisites/clean e não é rollback da run. O FF não cria commit adicional e o ponto B permanece acessível; não se propõe desfazê-lo movendo branch de worker, pois isso violaria replay/identidade e esconderia efeitos. Em interrupção, preservar é a recuperação compatível demonstrada.

## Digests para revisão

Todos os digests abaixo são SHA-256 dos bytes, sem prefixo. `observations.json` contém hashes adicionais, admissão completa, estado observado e distinção entre pin ausente e DAG validado.

- CLI histórica: `f71350d84b0ac517f462d6829cdd818425b5248e3675a746cce9c52e42523d2f`.
- gauntlet_runs histórico: `2e2b6c9c58338a356204b26e021888468ae5e6b4274fca9151b181b01ddf6f2c`.
- store histórico: `84e8cd535abdd5beef658f11a01d0c4731031682492d5f9c90e595b86a3a1c45`.
- WORKFLOW: `d2c4ea0806ea5e8235678582154aedaeb0ba686641bd836934bffe133db60ab5`.
- WORK-ITEM: `837e7410c5040bf24b1da838bb22d8c2cd3234027267b1ff0fffdf999f29ea3b`.
- .grill/gauntlet.yaml: `0893ae9f2c0191d2f4388154f6e7fbbb3c781fc1d0c61993485c73875072aa04`.
- Spec: `54d217cfb218cecc3990b9dbe29fffb9277177fe92aea447f0743955fdca44a7`.
- Plan: `78fe45fc8af6feeee8d46f897b6a70365cb3cae81fe4ae25613adf1bd369f66a`.
- Tasks: `946a43207a2e9e5768371dc7ab43e51e7e6427de8c375d96b5091bc50183dc3d`.
- DAG bytes/atestação: `748abdc506985b6d2979ff85bba66eed72c001bb2d56d7763097cdf5e1b14c6e`.
- DAG conteúdo canônico validado: `24ceaed2ee0b846ebfb96fd8a032955dd1ea649cb00fd4cb59e841189f9cea7c` (não intercambiável com digest dos bytes; ainda não gravado como pin da run sem wave real).
- proof.py: `6c20b29b9de22d01c102ed96ceb3f048d8f506a1540e4ffba3e470b562e69a78`.
- proof-result.json: `a1167dd823f50b01e8e6ec595df151c539b330cf9e57be7cd58ebc2f7d11936a`.

Os blocos Bash pressupõem a mesma sessão exclusiva com `set -euo pipefail`; toda assertion/recusa interrompe a sequência. Os inventários de ignored são estritos: usar `PYTHONDONTWRITEBYTECODE=1` e directs de testes descartáveis evita resíduos; se houver, preservar/diagnosticar, sem `clean -fdx`.

Fica para a revisão high distinta decidir o aceite operacional destas precondições e da retenção; o líder aplica e registra as observações reais antes do primeiro payload. Não há conclusão sobre implementação do produto 6.0.0.
