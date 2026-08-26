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

**Regra**: o receipt da etapa é sempre do leader — nenhum worker faz checkpoint
de etapa. Para etapa `worker-required`, o leader só emite contra prova de que
workers despachados fizeram o trabalho: waves convergidas na run, lidas do
estado durável. Sem essa prova ⇒ `WORKER_EXECUTION_UNPROVEN`. A prova nunca é
declarada por quem pede a emissão, porque isso seria a autocertificação que a
classe existe para impedir (ADR-0203).

**Estado**: entregue.

---

## Entidade: Cadeia

Os quatro elos mais o catálogo, na forma que `judge_checkpoint_attestation` exige.

| Elo | Origem na emissão | Estado |
|---|---|---|
| `resolution` | `step_skills.resolve_shipped_workflow_skills`, que carrega os assets de confiança da versão e já produz `skill-resolution/v1` | consumir |
| `dispatch_intent` | montado: identidade do projeto e do work item, executor, digests JCS de correlação | entregue |
| `invocation_started` / `invocation_terminal` | montados a partir do dispatch e do desfecho real | entregue |
| `step_output` | montado, ancorado no digest do artefato | entregue |
| `catalog` | o catálogo confiável que a resolução usou | consumir |
| `human_authorization` | **carregado** de um `human-authorization/v1`; presente só quando a resolução da etapa o exige | consumir |

**Correlação**: `dispatch_key`, `skill_invocation_key`,
`skill_resolution_sha256`, `logical_plan_sha256`, `executable_plan_sha256` e
`content_sha256` são digests JCS calculados por `step_skills.sha256_jcs`, nunca
valores livres.

**Autorização humana**: `ship` é a única etapa cuja resolução declara
`human_authorization_required`. O documento é **carregado**, nunca produzido
pela emissão: ele existe antes da cadeia, e cunhá-lo tornaria "um humano
aprovou" indistinguível de "quem queria a aprovação disse que sim". É validado
na entrada — escopo igual à etapa, decisão `APPROVED` —, então autorização
malformada é recusada na emissão em vez de sobreviver num bundle que só o juiz
rejeita depois. Etapa que a exige e não a apresenta é
`HUMAN_AUTHORIZATION_REQUIRED`, antes de qualquer escrita.

A autorização permite **invocar** a skill registrada; nunca a substitui nem
autoriza side effect direto. `judge_step_output` a aceita e não a inspeciona,
justamente porque uma autorização válida não muda se a cadeia está atestada.

**Estado**: entregue, em `mint_chain`.

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
| razão | `EXECUTION_CLASS_UNDECLARED` \| `EXECUTION_CLASS_VERSION_UNKNOWN` \| `EXECUTION_CLASS_INVALID` \| `WORKER_EXECUTION_UNPROVEN` \| `ARTEFACT_PATH_INVALID` \| `ARTEFACT_UNREADABLE` \| `SUPERSEDE_LINK_INCOMPLETE` \| `SUPERSEDE_ROUND_NOT_ADVANCED` |
| detalhe | Os campos que nomeiam o caso: `step_id`, `workflow_version`, `path` |

**Por que código próprio**: não é `BLOCKED_CAPABILITY` — a capacidade pode estar
perfeitamente resolvível. Não é `UNATTESTED_STEP_OUTPUT` — nada foi atestado; o
que falhou foi cunhar.

**Por que subclasse**: quem já trata `AttestationError` continua falhando fechado
numa falha de emissão, em vez de deixá-la escapar como exceção não relacionada.

**Estado**: entregue.

---

## Entidade: Cadeia sucessora

| Campo | Valor |
|---|---|
| `supersedes_step_execution_id` | A execução que este registro substitui; `null` num primeiro registro |
| `supersedes_attempt_id` | A tentativa correspondente; viaja junto com o campo acima, nunca sozinha |
| `execution_round` | Estritamente maior que a da execução substituída; `1` num primeiro registro |
| histórico | `development.superseded_outputs[step]`, com âncora, execução, tentativa, ronda, caminho do bundle, razão declarada e a execução que passou a substituí-lo |

**Por que sucessora e não reescrita**: o registro anterior nunca é apagado nem
alterado. A auditoria lê um histórico em vez de uma contradição — cada registro
continua ancorado nos bytes que de fato viu. Reescrever destruiria a distinção
entre correção honesta e adulteração, que é a razão de a cadeia existir.

**Por que os dois campos viajam juntos**: um sem o outro nomeia metade do que
substitui, o que é pior que não nomear nada — a referência fica irresolúvel.

**Por que exigir mudança**: o par (artefato, predecessor). Um sucessor que não
move nenhum dos dois é no-op fantasiado de correção. Olhar só o artefato
proibiria a re-atestação de uma etapa a jusante, que re-atesta com o artefato
byte-idêntico porque não refez trabalho algum.

**Por que o bundle substituído tem de ser o aceito**: provado contra os três
valores que o estado gravou na aceitação — `output_sha256`, `receipt_ref` e o
`step_execution_id` em `development.attested_executions[step]`. Sem nada disso
bastaria cunhar um bundle novo e apresentá-lo como o original, e toda a cadeia
sucessora seria forjável.

**Por que o par não bastava**: nem `output_sha256` nem `receipt_ref` dependem da
execução. Duas cadeias da mesma etapa e do mesmo artefato, diferindo só no índice
de onda, carregam os dois valores idênticos sob `step_execution_id` diferentes.
Aceitar uma delas gravaria no histórico uma execução que nunca foi o receipt
corrente, com o sucessor ligado a ela. Para receipts aceitos antes de o campo
existir, a verificação cai no par — degradação declarada, e toda aceitação nova
pina a execução.

**Estado**: entregue.

---

## Entidade: Pendência de nova emissão

| Campo | Valor |
|---|---|
| lista | `development.chain_stale`, em ordem de sequência |
| entra | Toda etapa posterior à substituída que já tinha registro atestado |
| sai | Ao ser atestada de novo, contra o predecessor que agora vale |
| efeito | `ship` e a virada de fase recusam com `CHAIN-STALE` enquanto a lista não estiver vazia |

**O que a pendência afirma**: não que as etapas seguintes estejam erradas — que
estão **inverificáveis**. Cada uma selou o registro do predecessor, e esse
registro deixou de ser o corrente; nada na cadeia sabe dizer se o trabalho
posterior ainda vale sob o artefato corrigido.

**Por que existe**: sem nomeá-las, uma substituição apenas realocaria a
divergência uma etapa adiante, em vez de resolvê-la.

**Por que a virada de fase também recusa**: encerrar a fase não resolve a
pendência, sobrevive a ela. O registro de etapas reinicia e a lista não, então a
fase seguinte seria recusada na publicação por pendência que não é dela — e
deixar cadeia inverificável para trás é o que a lista existe para impedir.

**Estado**: entregue.
