# Data Model: Emissor da cadeia de atestação

**Fase 1** | **Data**: 2026-08-24

O modelo aqui é o da **cadeia** e o das tabelas que decidem quem pode cunhá-la.
Os quatro elos já têm forma definida em `attestation.py`; o que este documento
fixa é de onde cada campo vem na emissão, e o que a emissão recusa.

---

## Entidade: Classe de execução

Declarada por versão e por etapa, em `workflow_versions`.

| Campo | Valor |
|---|---|
| chave | `(versão, step_id)` |
| valor | `leader-allowed` \| `worker-required` |
| origem | Literal congelado, **nunca** derivado de `SEQUENCE_BY_VERSION` |

**Invariantes**:

- A tabela de cada versão cobre exatamente as etapas daquela versão — nem a
  mais, nem a menos.
- A única etapa `worker-required` de cada versão é exatamente
  `EXECUTOR_STEP_BY_VERSION[versão]`. Se as duas tabelas divergirem, a etapa que
  despacha workers deixaria de exigi-los, ou uma etapa que não despacha passaria
  a exigir.
- Etapa ausente ⇒ `EXECUTION_CLASS_UNDECLARED`. Versão ausente ⇒
  `EXECUTION_CLASS_VERSION_UNKNOWN`. Valor fora do conjunto ⇒
  `EXECUTION_CLASS_INVALID`.

**Estado**: entregue.

---

## Entidade: Executor

Quem conduziu a etapa. Determina a origem dos campos de despacho.

| Campo | Worker despachado | Leader |
|---|---|---|
| `worker_lease_id` | lease do worker, do store | lease próprio, do mesmo mecanismo |
| `worker_fencing_token` | fencing token do worker | fencing token próprio |
| `worktree_id` | worktree isolado do worker | worktree do coordenador |
| `wave_index` | índice da wave que o declarou (≥ 1) | `LEADER_WAVE_INDEX` = 0, com significado "fora de onda" |
| `run_id` | run que declarou a wave | run corrente do work item |

**Regra**: o executor `leader` só é admissível para etapa `leader-allowed`.
Tentar para `worker-required` ⇒ `WORKER_REQUIRED_STEP`.

**Estado**: a recusa está entregue; a montagem dos campos, não.

---

## Entidade: Cadeia

Os quatro elos mais o catálogo, na forma que `judge_checkpoint_attestation` exige.

| Elo | Origem na emissão | Estado |
|---|---|---|
| `resolution` | `step_skills.resolve_workflow_skill(step_id, runtime, registry_sha256)` — já produz `skill-resolution/v1` | consumir |
| `dispatch_intent` | montado: identidade do projeto e do work item, executor, digests JCS de correlação | **falta** |
| `invocation_started` / `invocation_terminal` | montados a partir do dispatch e do desfecho real | **falta** |
| `step_output` | montado, ancorado no digest do artefato | **falta** |
| `catalog` | o catálogo confiável que a resolução usou | consumir |

**Correlação**: `dispatch_key`, `skill_invocation_key`,
`skill_resolution_sha256`, `logical_plan_sha256`, `executable_plan_sha256` e
`content_sha256` são digests JCS calculados por `step_skills.sha256_jcs`, nunca
valores livres.

---

## Entidade: Âncora

O que o `step_output` sela sobre o artefato produzido.

| Campo | Regra |
|---|---|
| caminho | Relativo ao projeto, sem travessia, sem absoluto |
| leitura | Pela fronteira do chamador, sem seguir link simbólico |
| digest | `sha256:` + 64 hex sobre os bytes lidos |
| tamanho | Bytes lidos, para diagnóstico |

**Recusas**: `ARTEFACT_PATH_INVALID` (vazio ou não-texto),
`ARTEFACT_UNREADABLE` (ausente, ilegível, ou leitor devolvendo não-bytes).

**Invariante**: nunca há cadeia cunhada com digest vazio. A recusa precede a
emissão.

**Estado**: entregue.

---

## Entidade: Recusa de emissão

| Campo | Valor |
|---|---|
| tipo | `EmissionError`, subclasse de `AttestationError` |
| código | `EMISSION_REFUSED` |
| razão | `EXECUTION_CLASS_UNDECLARED` \| `EXECUTION_CLASS_VERSION_UNKNOWN` \| `EXECUTION_CLASS_INVALID` \| `WORKER_REQUIRED_STEP` \| `ARTEFACT_PATH_INVALID` \| `ARTEFACT_UNREADABLE` |
| detalhe | Os campos que nomeiam o caso: `step_id`, `workflow_version`, `path` |

**Por que código próprio**: não é `BLOCKED_CAPABILITY` — a capacidade pode estar
perfeitamente resolvível. Não é `UNATTESTED_STEP_OUTPUT` — nada foi atestado; o
que falhou foi cunhar.

**Por que subclasse**: quem já trata `AttestationError` continua falhando fechado
numa falha de emissão, em vez de deixá-la escapar como exceção não relacionada.

**Estado**: entregue.
