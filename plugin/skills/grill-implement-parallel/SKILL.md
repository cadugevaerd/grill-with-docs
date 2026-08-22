---
name: grill-implement-parallel
description: Orquestra os workers não-frontier da etapa implement-parallel sobre o Execution DAG, com worktree isolado por worker e receipt submetido apenas pelo leader.
argument-hint: "<git-root> --work-id <id> --run-id <run> --dag <path>"
---
# Grill Implement Parallel v4.0.0

Canonical Skill da etapa **`implement-parallel`** do WORKFLOW v4. Você é o **leader**: orquestra, não implementa. Os workers implementam, cada um no próprio worktree, cada um com escopo fechado, nenhum com modelo de fronteira.

## Regras invioláveis

1. **O receipt da etapa é seu.** Nenhum worker faz checkpoint da etapa (spec 013 US1, ADR-0010).
2. **Você não escolhe modelo.** `gauntlet-worker-declare` resolve o modelo a partir do tier do nó. Não passe `--model`.
3. **Nenhum worker toca `tasks.md`.** Cada um grava só o próprio sidecar.
4. **Tarefas em `deferred_to_leader` são suas.** Elas escrevem evidência de coordenador e worker nenhum pode executá-las.

## Passos

### 1. Preflight — antes de qualquer worker existir

- **Checklists.** Rode o mesmo scan que `speckit-implement` faz. Se houver item aberto, **pare aqui** com `CHECKLIST-INCOMPLETE` e peça a decisão ao humano **uma vez**, no chat principal. Três workers parando para perguntar é deadlock de três vias com o `stall_minutes` correndo.
- **Hooks.** Leia `.specify/extensions.yml`. Qualquer entrada em `hooks.before_implement`/`hooks.after_implement` com `optional: false` ⇒ bloqueie com `HOOK-FANOUT-UNSAFE`. Um hook obrigatório que muta estado compartilhado dispararia uma vez por worker.

### 2. Declarar a wave

```bash
python3 <plugin>/scripts/grill_workspace.py gauntlet-wave-declare ROOT \
    --work-id ID --run-id RUN --dag specs/NNN/execution-dag.json \
    --node-id p01-a --node-id p01-b --node-id p01-c
```

Só nós prontos (dependências terminais) entram. Um nó `parallel:false` despacha **sozinho** na própria wave.

### 3. Declarar cada worker

```bash
python3 <plugin>/scripts/grill_workspace.py gauntlet-worker-declare ROOT \
    --work-id ID --run-id RUN --wave-id wave-0001 --node-id p01-a \
    --tier medium --dag specs/NNN/execution-dag.json \
    --files <cada file do nó>
```

Use `gauntlet-worker-declare`, nunca `gauntlet-prepare-worker`: a superfície legada aceita `--scope` sem DAG e pula seis verificações (sufixo reservado, piso de tier, escopo de evidência, pertencimento à wave, wave ativa, dependência terminal).

### 4. Despachar os subagentes

Um subagente por worker, no worktree do worker, com o **modelo que o declare devolveu** — nunca um escolhido por você. Cada subagente:

1. invoca `speckit-implement` com o brief como `$ARGUMENTS`;
2. chama `gauntlet-progress-record` a cada tarefa concluída (renova o lease, evita `stall` aos 15 min);
3. grava `specs/NNN/implement/<node-id>.tasks.json`;
4. commita na própria branch;
5. chama `gauntlet-worker-terminal --outcome completed`.

O brief vem de comando, não de prosa sua:

```bash
python3 <plugin>/scripts/grill_workspace.py gauntlet-partition-brief ROOT \
    --dag specs/NNN/execution-dag.json --node-id p01-a \
    --report specs/NNN/partition-report.json
```

O brief é **dica**. A garantia é o grant do worktree mais a verificação de diff em `gauntlet-converge` (`GRANT-SCOPE-VIOLATION`).

### 5. Convergir

```bash
python3 <plugin>/scripts/grill_workspace.py gauntlet-converge ROOT \
    --work-id ID --run-id RUN --wave-id wave-0001
```

Merge `--no-ff` serial, em ordem de `node_id`. Conflito de conteúdo **não** é resolvido automaticamente (ADR-0009): `INTEGRATION_CONFLICT` nomeia os nós e o humano resolve. `gauntlet-remediate` só aceita `stall` e `transient-failure`.

Repita 2–5 enquanto houver nó não terminal.

### 6. Reconciliar e fechar

```bash
python3 <plugin>/scripts/grill_workspace.py gauntlet-tasks-reconcile ROOT \
    --work-id ID --run-id RUN --dag specs/NNN/execution-dag.json
```

Lê os sidecars já mergeados e marca `[X]` em `tasks.md`, uma vez, na branch do coordenador. Determinístico, sem modelo no loop.

Depois execute você mesmo as tarefas de `deferred_to_leader`, e só então faça o checkpoint da etapa.

## Worker que falha

`gauntlet-converge` integra apenas lineage-head em estado terminal. Um worker `FAILED` é ignorado no merge e a wave fecha sem ele; a etapa `converge` seguinte apanha o resto como tarefa nova — é literalmente para isso que ela existe.
