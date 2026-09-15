# PLAN-CONTEXT

## FASE-001 — Children Orca independentes de CLI
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006
- BLs: BL-0001
- delivery-units: DU-001
- development-type: platform-devops

### HOW
- **Base e dependência.** A base é `cadugevaerd/feat-new-subagents` @ `f7aa733` (candidata 6.0.0). O `specify` só abre depois do ship da 6.0.0, porque `depends-on-work` aponta para `feature-new-subagents-unified-69f619a1…`. O bundle foi criado pelo CLI pinado 5.4.1, então precisa de `gauntlet-orchestration-adopt` depois do ship.
- **Topologia (ADR-0001).** Sessão líder = coordenador: `run-create` e `worker-start` do próprio terminal, `check --wait --types worker_done,escalation,question`, validação do `worker_done` contra o Dispatch esperado e `worker-release` antes do ack. Cada Task spec segue o contrato Orca: Target, Change, Constraints, Ownership, Observable acceptance. Remover a exigência `orca:ctx-*` do líder em `agent_runtime.LeaderBoundary` e `grill_workspace._leader_boundary`; o observador passa a ser por child, via `worker-show --dispatch`.
- **Executável (ADR-0006).** Resolver uma vez, na ordem `ORCA_CLI_COMMAND` → `orca-dev` (com `ORCA_DEV_REPO_ROOT`) → `orca-ide` (Linux fora de terminal Orca) → `orca`. Nunca `orca` puro fora de terminal Orca, porque aciona o leitor de tela GNOME. Se o executável falhar, reportar o erro exato, sem trocar de executável.
- **Sem Orca (ADR-0002).** Checagem determinística: executável resolvido, `status --json` com `runtime.state=ready` e capability `orchestration.worker-launch-preferences.v1`. Qualquer falha gera recusa nomeada (sugestão: `ORCA-UNAVAILABLE`, `ORCA-CAPABILITY-MISSING`) antes do despacho. Remover o caminho degradado de `GOAL.template.md` §Delegação.
- **Binding (ADR-0003).** Fundir `workflow-tier-models.json` e `agent-orchestration.v1.json` roles num único asset por runtime × papel. Claude: autor `fable`/`xhigh`, revisor `fable`/`high`. Codex: autor `gpt-6-astra`/`xhigh`, revisor `gpt-6-astra`/`high`. Workers seguem não-frontier por tier. Revalidar se os IDs de worker herdados (`haiku/sonnet`, `gpt-5.6-luna/terra`) ainda existem antes de fixar. Sempre `--model`, `--effort` só quando suportado, nunca com `--terminal`; comparar `launch.requested` com `launch.effective` e bloquear na divergência. Lock-in: os hashes da policy 6.0.0 referenciam os assets fundidos.
- **Override de CLI (ADR-0004).** `--agent` = runtime do `init`. A outra coluna só com instrução humana explícita ou recusa observada (`worker-start` não-zero com `failedStage`, ou launch divergente), registrando `agent_override {from, to, reason, ref}`.
- **Placement (ADR-0005, BL-0001).** Worker: `gauntlet-worker-declare` continua criando `wt-run-*` e o grant, e o líder usa `worker-start --worktree path:<wt>`. Resolução de `path:` provada com `orca worktree show`; o lançamento real é aceite live. Autor/revisor: `--worktree current`. Não usar `new-child`/`new-top-level`. `converge`/`GRANT-SCOPE-VIOLATION` não mudam. Aposentar `plugin/agents/gauntlet-worker-medium.md` como mecanismo de despacho e reescrever `grill-implement-parallel/SKILL.md` §4.
- **Evidência (DQ-0008).** Por child, no receipt do líder: `run_id`, `task_id`, `dispatch_id`, `agent`, `launch.requested`, `launch.effective`, `worker_done` (message id e outcome), confirmação de `worker-release` e `agent_override` quando houver. Sem transcript. Auditoria offline e reproduzível. O worker continua proibido de escrever `.grill/` e `.specify/reports/`.
- **Dependência (ADR-0006).** Nova entrada `orca` em `assets/dependencies.json`, `required: true`, detecção por seam injetável (padrão `Toolchain`), sem subprocess real nos validadores. Bump 7.0.0 nos oito locais de `validate_distribution.py`.
- **Riscos.** (1) Limite de profundidade de aninhamento, se um child tentar iniciar outro child: especialistas e workers não criam children. (2) A CI não tem Orca: todos os testes precisam de stub. (3) Mudança de superfície do Orca entre versões: ler `orca skills get orchestration` na execução em vez de fixar flags na prosa além do mínimo contratual. (4) Hash de `agent-orchestration.md`/policy muda: recalcular referências.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
