# PLAN-CONTEXT

## FASE-001 — Modelo mais recente: Codex por família e especialista Claude em Opus
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
- Ponto único de resolução: `grill_core/tier_models.py` passa a resolver família→slug para Codex; `gauntlet_runs._resolve_worker_model`/`declare_worker` continuam sem `--model` e gravam o slug resolvido (ADR-0001, decisão de projeto `docs/adr/0013-worker-model-floor.md`). O mesmo resolvedor atende os papéis Codex de `agent_orchestration.py` (hoje literais nas linhas 51-52 e na policy).
- Fonte: `models_cache.json` sob `CODEX_HOME` ou `~/.codex` — reaproveitar a resolução de home Codex já usada por `ensure_dependencies.py`/`agent_runtime.py`; não criar segunda convenção. Critério: slugs com `visibility == "list"` cuja família casa, menor `priority` vence. Leitura por arquivo, stdlib, sem subprocesso, sem rede.
- Família por slug: definir no plan a regra de extração (sufixo após a última `-`) e rejeitar slugs que não casem; `gpt-reserve`, `codex-auto-review` (hidden) nunca entram.
- Frontier por família no asset; `FRONTIER-MODEL-FORBIDDEN` continua avaliado antes de worktree.
- Falha: `TIER-MODEL-UNRESOLVED` nomeado com runtime, tier/papel, família e caminho do catálogo; sem fallback.
- Policy/asset selados: `workflow-tier-models.json` está no `ESSENTIAL` v4 só pelo nome (conteúdo livre). `agent-orchestration.v1.json` é selado por `policy_sha256` em contextos existentes; o plan decide entre versão nova da policy ao lado da v1 ou reseal explícito, garantindo que contextos e work items já selados continuem verificáveis (seguir a regra do CLAUDE.md: versão nova é artefato novo, nunca edição da existente).
- Testes offline com seam injetável do caminho do catálogo; fixture derivada da saída real de `codex debug models` 0.155.1 (inclui `gpt-reserve` hidden e `gpt-5.5` com `upgrade`), não do código (memória `fixture-mais-limpa-que-a-realidade`). `tests/validate_tier_model_binding_contract.py` deixa de fixar `gpt-5.6-*` e passa a fixar famílias.
- Par de especialista Claude (ADR-0002): `roles.claude.author/reviewer` da policy e `SPECIALIST_PAIRS["claude"]` (`agent_orchestration.py:50-53`) passam a `("opus", "xhigh")`/`("opus", "high")`; tabela de `SKILL.md:41`, `session-protocol.md:67` e `README.md:59` deixam de citar `fable`; `tests/validate_agent_orchestration_contract.py:933` passa a fixar `opus`. Alias, nunca slug fixo.
- Gate de efetivo: `verify_specialist` exige `effective_model == resolved_model_id == par` e `agent_runtime.py:1236` só preenche `resolved_model_id` quando pedido == efetivo. O plan comprova o que o Orca reporta em `launch.effective` para o alias `opus` (alias ou `claude-opus-5-5`); se reportar slug, definir a regra de correspondência alias→linha sem aceitar outra linha, e gravar o slug resolvido de forma durável quando disponível (paralelo ao ADR-0001 decisão 3).
- Selo da policy: a troca de `roles.claude` entra na mesma decisão de versão nova da policy ou reseal já prevista acima para os papéis Codex; uma única mudança de policy cobre as duas.
- Pendência operacional (não é BL, decisão já tomada): até esta fase estar implementada, o gate exige `fable` e a decisão proíbe usá-lo, então nenhuma atividade autor/revisor roda no runtime Claude — inclusive as do ciclo desta própria feature (specify exige revisor; plan/tasks exigem autor e revisor). Condução do ciclo no runtime Codex (par `astra`) ou espera pela implementação é escolha do coordenador antes de `specify`. Nunca rodar atividade com `fable`.
- Distribuição: bump nos oito pontos de versão e release, conforme a Constituição.
- Riscos: formato do `models_cache.json` é contrato implícito do Codex; catálogo stale no disco resolve para o que estiver listado (o Codex atualiza o cache ao rodar).
