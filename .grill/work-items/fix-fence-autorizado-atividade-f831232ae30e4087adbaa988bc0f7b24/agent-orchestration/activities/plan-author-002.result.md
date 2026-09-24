# Relatório — plan-author-002 (AUTOR, rodada de correção do plano)

- payload lido por inteiro: sha256 `44e5983b996bcd9dc4bc2cfdada29af8a338a9711817414361d9973bdd56af57` (confere)
- input manifest `plan-author-002.input.json`: 30/30 sha256 conferidos, zero divergência
- HEAD `ad42a65` (código idêntico ao `39380f7`/`4cad807`: `git diff --stat 4cad807 HEAD` toca só `.grill/`; os cinco módulos e os dois validadores têm os mesmos sha256 do manifest). Toda citação file:line nova foi reconferida neste HEAD: `ws:4148-4156`, `4452`, `4453-4455`, `4474-4478`, `3952-3953`, `7081`, `7134`, `7214`, `1869-1881`, `6078-6080`; `T:2620-2637`.
- escrita só nos cinco arquivos do grant; nenhum commit; nada em `.grill/`
- nenhuma DQ-0001..DQ-0014 reaberta; decisão de saltos (CLOSED, salto derivado do estado) intacta
- `git diff --check` limpo; 5 arquivos, +40/−33

## sha256 finais

| Arquivo | sha256 |
|---|---|
| `specs/034-fence-autorizado-atividade/plan.md` | `91b26d7f18404846378d80c1764d633136f453e0bdf221eb596ebe359fba13cd` |
| `specs/034-fence-autorizado-atividade/research.md` | `64e79d8d23305b8d08df268e217e07a7c2646b795275f9613c00557bb5e750af` |
| `specs/034-fence-autorizado-atividade/data-model.md` | `cfa4c4e2c32822cb692478c63391996b35b0db72445e5367f32ab70eaa85ab2b` |
| `specs/034-fence-autorizado-atividade/quickstart.md` | `037cd5934467d8be29d0aaa21ef0bddeeb90247efddf389787c2d433b6f6fb7b` |
| `specs/034-fence-autorizado-atividade/contracts/activity-fence.md` | `f8aa5fcae474395094d567d7becf5725087418d9729ea29da6b51c8ee05ac3dd` |

## Findings → onde foram aplicados

### Finding 1 — replay e retomada exigem o mesmo solicitante
- `research.md` R2 passo 2: `_fence_recorded` recebe `args.session_ref`; `FENCE-REUSED` e retomada exigem `args.session_ref == operation["intended_after"]["requester"]["ref"]` (precedente `TAKEOVER-REUSED`, 4148-4156); solicitante divergente segue para o passo 3 e recusa `FENCE-ACTIVITY-STATE`. DQ-P3 do revisor registrada como resolvida pela opção A, sem decisão nova.
- `research.md` R11: caso p3b.
- `contracts/activity-fence.md` linha "Com `--apply`" (hash recalculado × hash da operação), linha "Ordem das checagens" e linha "Idempotência" (mesmo solicitante; outro `--session-ref` → `FENCE-ACTIVITY-STATE`).
- `data-model.md` "Transições": replay e retomada só com o mesmo solicitante; outro → `FENCE-ACTIVITY-STATE`.
- **Nota**: o revisor escreveu que a retomada com solicitante divergente cairia em `FENCE-INPUTS-STALE`. Pela ordem de R2 o par `(FAILED, CLOSE_PENDING)` não passa no passo 3, então a recusa é `FENCE-ACTIVITY-STATE` nos dois casos (replay e retomada). O payload pede "segue para as checagens normais", que é o que está escrito; o código resultante é derivação da ordem já aprovada, não decisão nova.

### Finding 2 — `--authorization` sem `required`
- `research.md` R1 (parser: `--session-ref` `required=True` como em 7134; `--authorization` sem `required`, default `None`; diferente do precedente `--attestation` em 7081) e R5 Rationale (flag omitida → `FENCE-AUTHORIZATION-INVALID` antes de `load_checkpoint_attestation`, FR-003 literal).
- `research.md` R11: n1 ganha "flag omitida".
- `contracts/activity-fence.md` linha "Autorização" (flag omitida → mesmo código único; por que não é `required`).
- `data-model.md` "Entradas do verbo", linha `authorization`.
- `quickstart.md` passo 1.

### Finding 3 + DQ-0014 (opção A) — cleanup não reconhece o fence
- `research.md` R8: parágrafo novo com `closed = state in {CLOSED, REMOVED} and bool(result_acceptance_ref)` (4452), `SESSION-CLOSE-UNPROVEN` (4453-4455), veredicto `UNKNOWN` exit 2 (4474-4478), por que não bloqueia (7214; 1869-1881; quiescência lê estado), SGD-41 como endurecimento.
- `research.md` R11 p2: asserção do `gauntlet-cleanup --context-id` do contexto vivo.
- `contracts/activity-fence.md` linha "Depois do fence".
- `data-model.md` linha `result_acceptance_ref` e "Transições" (último item).
- `quickstart.md` passo 1.
- `plan.md` Constitution Check, linha "Rastreabilidade" (DQ-0001..DQ-0014; SGD-40, SGD-41).

### Finding 4 — payload do `FENCE-CAS-CONFLICT` pós-salto 1
- `research.md` R7 salto 2: única recusa com estado alterado (exceção a FR-013); payload com `activity_state`, `resource_state`, `operation_id`; saída = retomada de R2 sobre `(FAILED, CLOSE_PENDING)`.
- `research.md` R2 passo 2: `FENCE-CAS-CONFLICT` de `_fence_recorded` carrega os três campos.
- `research.md` R11 p5: variante pós-salto 1 (recurso movido para `PRESERVED` → `FENCE-CAS-CONFLICT` com o payload).
- `contracts/activity-fence.md` linha "Recusas" (exceção ao "bit a bit igual").
- `data-model.md` "Transições", item "Qualquer recusa".

### Finding 5 — lacunas de teste
- `research.md` R11: n2d (`work_id` divergente), n8b (`(RESULT_RECORDED, REGISTERED)`, `(DISPATCHED, CLOSE_PENDING)`, `(RESULT_RECORDED, CLOSED)`), n9 (`transact` interposto entre prévia e apply → `FENCE-CAS-CONFLICT`, Store igual ao estado interposto; seam de 2620-2637), p3b; Rationale cita os Findings.
- `plan.md` Source Code: `test_activity_fence (n1..n9, p1..p5)`.
- `quickstart.md` passo 1.

### Finding 6 — prosa
- `research.md` R9: "`gauntlet-prepare-switch` escreve `FAILED` só a partir de `DISPATCHED` (3952-3953); nenhum outro caminho percorre `RESULT_RECORDED → FAILED`".
- `research.md` R10 (título e decisão: attempt 2 no contexto novo na forma órfã, no mesmo contexto com líder vivo) e `data-model.md` `intended_after`: `successor: "attempt-2-as-new-activity"`; `contracts/activity-fence.md` linha "Depois do fence" idem.
- HEAD citado: `plan.md` Constitution Check (`ad42a65`, com `4cad807` do revisor) e `research.md` linha 3.
- `plan.md` Summary: reexecução do autor pelo sucessor (órfã) ou pelo líder vivo (retida).

### Nits
- "DQ-P1" → "DQ-0013 (opção A; SGD-40)" em `research.md` R5 e seção "DQs propostas" (heading e linha "Selada"), e em `data-model.md` linha `content_sha256`. Menções históricas a `9dd8df6` e ao nome "DQ-P1" ficaram só como rastro ("proposta aqui como DQ-P1"; "plan-author-001 conferiu em 9dd8df6").

## DQs propostas novas

Nenhuma. A seção "DQs propostas" de `research.md` agora registra: DQ-P1 → DQ-0013 (A; SGD-40); DQ-P2 do revisor → DQ-0014 (A; SGD-41); DQ-P3 do revisor → resolvida pelo Finding 1 (A), sem DQ.

## Fora do grant (não tocado)
- Nada. Sem mudanças em `.grill/`, `DELIVERY-MAP.md`, `PLAN-CONTEXT.md` ou código.
