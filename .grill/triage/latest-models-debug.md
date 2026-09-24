# Relatório de debug

## Status
- causa raiz comprovada

## Sintoma reproduzido
- Comando/cenário: `cd plugin/skills/grill-with-docs/scripts && python3 -c "from grill_core import tier_models as t; print([t.resolve_model('codex', x, actor_class='worker')['model'] for x in ('small','medium')])"` na worktree `fix-latest-models` (HEAD `d4bf60b`, branch `cadugevaerd/fix-latest-models`), plugin fonte 6.0.24.
- Resultado observado: `['gpt-5.6-luna', 'gpt-5.6-terra']`, enquanto o catálogo local do Codex (`~/.codex/models_cache.json`, `fetched_at 2026-09-23T20:48:13Z`, codex-cli 0.155.1) lista `gpt-6-astra` (prio 1), `gpt-6-sol` (prio 2), `gpt-6-luna` (prio 3) acima de `gpt-5.6-sol` (4), `gpt-5.6-terra` (7) e `gpt-5.6-luna` (8). O worker Codex é despachado com a geração anterior.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| Tiers Codex literais `gpt-5.6-luna/terra/sol`; Claude aliases `haiku/sonnet/opus` | `plugin/skills/grill-with-docs/assets/workflow-tier-models.json` | o binding tier→modelo é um id literal por geração, sem resolução contra catálogo |
| `resolve_model` devolve `resolved["model"]` do asset sem consultar runtime/catálogo | `plugin/skills/grill-with-docs/scripts/grill_core/tier_models.py:127-167` | não existe caminho de código que descubra modelo mais recente |
| `declare_worker` deriva o modelo só do tier (`_resolve_worker_model`) e grava no worker record; chamador não passa `--model` | `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py:2076-2173`, `plugin/skills/grill-implement-parallel/SKILL.md:13` | o id literal do asset é o que efetivamente chega ao launch do worker, sem override possível |
| 7 registros reais `"model": "gpt-5.6-terra"` em `implementation/*/launch-verified.json` | `.grill/work-items/feature-new-subagents-unified-*/implementation/` | o sintoma ocorreu em despacho real, não só em teste |
| Catálogo Codex: gpt-6-astra/sol/luna listados; não existe `gpt-6-terra` | `~/.codex/models_cache.json` (leitura) | a geração nova existe localmente; o nome do tier médio não tem sucessor 1:1 |
| Teste fixa os ids: `EXPECTED_MODELS["codex"] = gpt-5.6-*` ("Pinned on purpose") | `tests/validate_tier_model_binding_contract.py:34-38` | o pin é contrato deliberado; atualizar exige editar asset + teste a cada geração |
| ADR-0013 define o binding como asset versionado com derivação por tier | `docs/adr/0013-worker-model-floor.md` | nenhuma spec exige "modelo mais recente automático"; é capacidade ausente, não desvio de spec |
| Policy de especialistas fixa `gpt-6-astra` (Codex) e `fable` (Claude) literais | `plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json:13-19`, `grill_core/agent_orchestration.py:51-52` | mesma classe de pin literal no autor/revisor (hoje coincide com o topo do catálogo, mas envelhece igual) |
| `workflow_v4.ESSENTIAL` contém só o nome `workflow-tier-models.json`, não o conteúdo | `grill_core/workflow_v4.py:134` | alterar o conteúdo do asset não marca WORKFLOW.md v4 como incompatível |

## Caminho de investigação/Hipóteses eliminadas
1. H1: o runtime Codex ignora `--model` e cai no default do config → refutada para o worker: o próprio `launch-verified.json` registra `gpt-5.6-terra` como modelo requisitado pelo core; o valor antigo nasce no asset, não no harness.
2. H2: o GWD consulta o catálogo mas o cache está stale → refutada: `tier_models.py` não lê `models_cache.json` nem chama CLI; o cache local já contém gpt-6-*.
3. H3: o lado Claude sofre o mesmo defeito → limitada: tiers Claude usam aliases (`haiku/sonnet/opus`) resolvidos pelo harness ao mais recente; o sintoma reproduzido é específico do Codex, cujos ids são literais por geração.
4. Reprodução direta de `resolve_model` para codex small/medium → `gpt-5.6-luna`/`gpt-5.6-terra` (large bloqueia `FRONTIER-MODEL-FORBIDDEN` por design).

## Causa raiz
O binding tier→modelo do runtime Codex em `assets/workflow-tier-models.json` é um id de modelo literal de uma geração específica (`gpt-5.6-*`), e `tier_models.resolve_model` o devolve verbatim sem qualquer resolução contra o catálogo de modelos do runtime. Como `declare_worker` só aceita o modelo derivado desse asset, todo worker Codex é lançado com a geração pinada até alguém editar manualmente asset e teste; a publicação da geração `gpt-6-*` não tem caminho para chegar ao despacho.

## Cadeia causal
Geração nova `gpt-6-*` publicada no catálogo Codex → `workflow-tier-models.json` continua com `gpt-5.6-luna/terra/sol` literais (pin reforçado por `EXPECTED_MODELS` no validador) → `tier_models.resolve_model('codex', tier, actor_class='worker')` devolve o literal → `gauntlet_runs.declare_worker` grava e o launch usa `gpt-5.6-*` → worker executa na versão antiga.

## Arquivos envolvidos
- `plugin/skills/grill-with-docs/assets/workflow-tier-models.json`: fonte dos ids literais Codex por tier.
- `plugin/skills/grill-with-docs/scripts/grill_core/tier_models.py`: resolve tier→modelo sem consultar catálogo.
- `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`: `declare_worker`/`_resolve_worker_model` consomem o binding e gravam o modelo do worker.
- `tests/validate_tier_model_binding_contract.py`: trava os ids literais `gpt-5.6-*`.
- `plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json` e `grill_core/agent_orchestration.py`: mesmo padrão de pin literal para autor/revisor.

## Limitações/incertezas
- O catálogo Codex da geração 6 não tem `terra`; o mapeamento do tier `medium` para a geração nova não é derivável só por nome.
- A classificação `frontier` de `gpt-6-sol`/`gpt-6-luna` não está declarada em fonte local; o catálogo não expõe esse atributo.
- O modelo da sessão líder Codex vem de `~/.codex/config.toml` (`model = "gpt-5.6-sol"`), configuração global do usuário fora do GWD; o GWD só recomenda "Sol" e não troca modelo.

Diagnóstico encerrado. Nenhuma correção foi executada.
