---
name: grill-partition
description: Particiona tasks.md em subfases file-disjuntas e emite o Execution DAG versionado da etapa partition, de forma determinística e sem julgamento de modelo.
argument-hint: "<git-root> --work-id <id> --feature <NNN-slug>"
---
# Grill Partition v4.0.0

Canonical Skill da etapa **`partition`** do WORKFLOW v4. Lê o `tasks.md` que a etapa `tasks` produziu e emite o Execution DAG que a etapa `implement-parallel` vai despachar.

## Regra inviolável

O agrupamento **não é decisão sua**. Ele vive em `grill_core/partition.py` e é determinístico: a mesma `tasks.md` produz o mesmo `dag_content_sha256`. Você invoca o comando, lê o veredito e reporta. Reagrupar "porque faria melhor" quebra o pin da run e é `POLICY_VIOLATION/DIRECT_STEP_EXECUTION`.

## Passos

1. **Prerequisites**

   ```bash
   .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
   ```

2. **Emitir o DAG**

   ```bash
   python3 <plugin>/scripts/grill_workspace.py partition-emit ROOT \
       --work-id ID --feature NNN-slug [--groups 3] [--apply]
   ```

   Sem `--apply` é preview: imprime o DAG e o relatório sem escrever. Com `--apply` grava `specs/NNN-slug/execution-dag.json` e `specs/NNN-slug/partition-report.json`.

3. **Validar pelo validador oficial** — último ato, sempre:

   ```bash
   python3 <plugin>/scripts/grill_workspace.py gauntlet-dag-validate ROOT \
       --work-id ID --run-id RUN --dag specs/NNN-slug/execution-dag.json
   ```

   Veredito diferente de `DAG-VALID` ⇒ reporte `blocked` e **não** faça checkpoint.

4. **Checkpoint** só depois de `DAG-VALID`.

## Como ler o relatório

| Campo | Significado |
|---|---|
| `verdict` | `PARTITION-COMPLETE` quando toda fase alcançou a largura pedida e nada sobrou; `PARTITION-DEGRADED` caso contrário |
| `max_workers` | Largura real da wave mais larga, limitada pela largura pedida |
| `phases[].achieved_groups` | Bins paralelos daquela fase. **3 é teto, não promessa** |
| `phases[].reasons` | `CONFLICT_GROUPS_BELOW_LIMIT` (a fase não tinha 3 grupos de arquivo disjuntos), `UNMAPPED_TASKS`, `EVIDENCE_BOUNDARY_TASKS` |
| `unmapped_task_ids` | Tarefas sem caminho extraível. Vão para um nó `parallel:false` que roda sozinho |
| `deferred_to_leader` | Tarefas que escrevem evidência de coordenador (`.grill/`, `.specify/reports/`). **Nenhum worker pode executá-las** — são do leader (ADR-0010) |

`PARTITION-DEGRADED` não é falha. É o relatório dizendo a verdade sobre um `tasks.md` cujas dependências ou cuja falta de paths não permitem a largura pedida.

## Recusas

| Código | Quando |
|---|---|
| `PARTITION-NO-TASKS` | `tasks.md` não declara tarefa alguma |
| `PARTITION-UNSCOPED-FEATURE` | Nenhuma tarefa despachável nomeia um caminho: não há o que cercar |
| `PARTITION-COORDINATOR-ONLY` | Toda tarefa escreve evidência de coordenador |
| `PARTITION-INVALID-WIDTH` | `--groups` menor que 1 |

Nenhuma delas se resolve editando o DAG à mão. Todas se resolvem no `tasks.md`.

## O que esta skill nunca faz

- Não edita `tasks.md`.
- Não escolhe agente, modelo ou tier — o tier vem do `TIER_POLICY` da ativação.
- Não despacha worker: isso é `implement-parallel`.
- Não fatia um grupo de conflito para forçar 3 bins.
