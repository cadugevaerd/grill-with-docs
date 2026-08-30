# Protocolo de sessão v5.3.2

Frases com **deve**, **nunca** e **somente** são normativas. A inicialização cria o workflow/Constituição quando ausentes; depois do init, os artefatos são read-only.

## Fluxo e checkpoints

`grill_workspace.py init` cria a Constituição gerenciada somente quando ausente, sem clobber, com fsync/readback; arquivo existente preserva bytes. Ausência não é `not-present`: é bootstrap pendente e deve ser resolvida no init. Symlink, ancestor symlink, UTF-8 inválido ou corrida insegura falham fechado.

Após init, avance somente pela matriz persistente de 11 passos: `specify → plan → checklist → tasks → analyze → partition → implement-parallel → converge → verify → review → ship`. Use `grill_workspace.py checkpoint ROOT --work-id ID --step STEP --state in-progress|complete|blocked [--evidence PATH] [--reason TEXT]`. Não há saltos; `complete` exige evidência regular segura com SHA-256, `blocked` exige razão, retry parte de blocked e `ship` exige verify+review completos. Eventos idênticos retornam `REUSED`; divergência retorna `STATE-DIVERGENCE`. Legado retorna `LEGACY-UNTRACKED` e só pode ser inicializado explicitamente com `--initialize-legacy --from-step STEP`, decisão e evidência.

`grill_workspace.py status ROOT` é a única interface pública de status; hooks apenas projetam resumo humano e não escrevem/rede.


## Fluxo

```text
worktree/branch dedicada
        │
        ▼
grill_workspace init ──> .grill/work-items/<work-id>/
        │
        ▼
entrevista → audit → PLAN_ONLY_STOP
        │
        ▼
ship externo → state complete/GO → reconcile preview → apply na integração
```

## Preflight `iniciar|retomar`

- [ ] Resolver e fixar o Git root real.
- [ ] Confirmar branch/worktree dedicada para a feature, fix ou hotfix.
- [ ] Se o trabalho nasce de um problema relatado, invocar `code-debug` **antes** de escolher o tipo; sem laudo de causa raiz não há como distinguir incidente de defeito nem defeito de funcionalidade faltante.
- [ ] Executar `grill_workspace.py triage ROOT --report LAUDO.md --route ...` em preview, conferir a rota e só então repetir com `--apply`; fixar o `triage_id` retornado.
- [ ] Aceitar `TRIAGE-RECORDED|TRIAGE-PREVIEW|REUSED`. `ROOT-CAUSE-UNPROVEN` significa investigação incompleta, não documento malformado: volte ao `code-debug`, não edite o laudo.
- [ ] Executar `grill_workspace.py init ROOT --type ... --slug ...`; ele fixa o `WORKFLOW.md` project-wide e aceita somente `CREATED|REUSED` no campo `workflow`.
- [ ] Ler o campo `dependencies` do retorno; usar `--allow-install` para instalação delegada e `--require-dependencies` quando o gate precisar ser fail-closed.
- [ ] Fixar o `work_id` retornado e usar somente `.grill/work-items/<work-id>/`.
- [ ] Confirmar `WORK-ITEM.json`, metadata imutável e hash canônico.
- [ ] Reler `WORKFLOW.md` project-wide e seu hash.
- [ ] Se a Constituição estiver ausente, executar init explícito; após init, somente leitura.
- [ ] Se presente, validar UTF-8, placeholders, hash e cobertura exata em `CONSTITUTION-CHECK.md`.
- [ ] Nunca emendar, dispensar ou enfraquecer a Constituição após init.
- [ ] Validar paths sem traversal/symlink e preservar conteúdo humano.
- [ ] Confirmar que `.grill/global/` não foi alterado pelo init.

Falha de identidade, integridade, path, lock ou materialização é `BLOCKED`. Falha constitucional é `BLOCKED-CONSTITUTION`. Antes de `init`, a ausência indica bootstrap pendente; após `init`, ausência, check `PENDING`, hash divergente ou conteúdo inválido bloqueiam o gate constitucional até correção explícita.

## Entradas e controle

Project-wide:

- `.specify/memory/constitution.md` — criada pelo init quando ausente; depois, read-only;
- `WORKFLOW.md`.

Work-item local:

- `CONTEXT.md`, `docs/adr/`, `ROADMAP.md`, `DECISION-BACKLOG.md`, `PLAN-CONTEXT.md` e handoff selecionado;
- controles: `WORK-ITEM.json`, `CONSTITUTION-CHECK.md`, `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl`, `state.json`, `AUDIT.md`.

Nunca resolva um path local contra o Git root; resolva contra o diretório do work item.

## Gate constitucional

Para cada heading normativo H2/H3, `CONSTITUTION-CHECK.md` deve conter exatamente uma entrada com:

- `id` e `heading` correspondentes;
- `status`: somente `PASS|NOT-APPLICABLE` libera;
- `evidence` não vazia;
- `justification` não vazia;
- `constitution_sha256` atual.

`PENDING|UNMAPPED|BLOCKED|VIOLATION`, cobertura ausente/duplicada, hash stale, status desconhecido ou ambiguidade retornam exit `3`. Nenhum ADR funciona como waiver.

## Loop de entrevista

1. Classificar cenário e evidências.
2. Carregar a fronteira completa.
3. Fazer uma pergunta atômica.
4. Registrar transição e impact scan.
5. Atualizar somente o work item atual.
6. Acrescentar uma linha ao log append-only.
7. Recalcular a fronteira antes da próxima pergunta.

Entradas de decisão novas usam `question_id` e `transition`. Eventos de lifecycle usam `record_type: lifecycle` e um `event` permitido, sem transição de decisão. Logs legados permanecem imutáveis: o auditor os lê no schema histórico e nunca exige reescrita retroativa.

Duas rodadas sem progresso, terceira repetição, terceira expansão consecutiva ou 25 perguntas materiais: checkpoint + `SAFETY_STOP`. `stop|pausar` grava `PAUSED_USER`.

## Triagem

`triage` sela a rota antes de existir work item. Ele não classifica o problema — quem classifica é `code-debug`, e o core apenas verifica. Recuse-se a contornar: editar o laudo para que ele passe é fabricar a prova que o gate existe para exigir.

Enquanto o laudo não declarar `causa raiz comprovada`, o comando devolve `ROOT-CAUSE-UNPROVEN` (NO-GO) e nenhuma rota abre. `hotfix` exige severidade crítica, impacto declarado, escopo fechado e rollback; `bugfix` exige uma spec existente para receber o patch; `feature` e `module` proíbem as duas coisas. Evidência faltante é `ROUTE-EVIDENCE-MISSING`, evidência contraditória é `ROUTE-EVIDENCE-CONFLICT`, e ambas listam exatamente quais campos.

Preview é o padrão. O registro selado em `.grill/triage/<triage-id>.json` é imutável e deve ser commitado junto com o trabalho que ele originou.

## Hotfix-fast / incident

`hotfix` é a trilha executável de incidente. Ela cria um bundle autocontido com `HOTFIX.md`, `state.json` e `WORK-ITEM.json` marcado `closed=true`, e retorna `HOTFIX-GO` apenas quando todos os campos obrigatórios estão presentes. Escopo com traversal/quebra de linha, ausência de evidência ou divergência de identidade falha fechado. Não consultar ROADMAP, BL, DQ, workflow global ou reconciliação para decidir segurança do hotfix; a Constituição continua obrigatória quando presente. O bundle deve registrar `hotfix.closed=true`; `HOTFIX-GO` revalida integridade, identidade, escopo e teste. Ship é externo. Reconciliação e auditoria documental completa são ações pós-ship.

Feature/fix continuam em `PLAN_ONLY_STOP` e não ganham atalho de implementação.

## Auditoria

- [ ] Executar `grill_workspace.py audit ROOT --work-id ID`.
- [ ] Não chamar bootstrap nem escrever arquivos.
- [ ] Validar Constituição antes do auditor decisório.
- [ ] Confirmar fingerprints idênticos antes/depois.
- [ ] Validar ordem explícita, fase única pronta, dependências, BLs e handoff WHAT/WHY.
- [ ] Se todas as fases estiverem `complete|superseded`, exigir zero BL/DQ material aberto, `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; emitir `MILESTONE-COMPLETE` sem exigir nova fase ready.

Roots separados são permitidos com `--artifact-root PATH --project-root ROOT`.

Exit codes do core: `0` sucesso/GO/MILESTONE-COMPLETE/PREVIEW/APPLIED/CREATED/REUSED; `1` NO-GO; `2` BLOCKED/uso; `3` BLOCKED-CONSTITUTION.

## Reconciliação

Preview:

- [ ] Ler root atual, `--source-root` e `--source-ref` sem checkout.
- [ ] Não criar `.grill`, lock ou arquivo global.
- [ ] Exigir `milestone_status=completed`, `state.status=complete`, `active_phase=null`, `audit_verdict=GO` e todas as fases do `execution-order` em `complete|superseded`.
- [ ] Detectar IDs divergentes, escopo sobreposto, dependências ausentes/cíclicas, ADRs conflitantes e Constituição stale.
- [ ] Em modo incremental, usar `--work-id ID`; validar somente o alvo contra receipts anteriores e rejeitar baseline global legado sem `receipts/` com `GLOBAL-BASELINE-UNVERIFIED`.
- [ ] Qualificar IDs como `<work-id>/<ID>`.

Apply:

- [ ] Exigir `--integration-branch` igual à branch atual.
- [ ] Exigir árvore limpa e zero conflitos.
- [ ] Serializar por lock global.
- [ ] Gravar somente `.grill/global/ROADMAP.md` e `AUDIT.md`.
- [ ] Segunda execução deve ser no-op byte-idêntico.
- [ ] Nunca reescrever work items.
- [ ] Persistir `.grill/global/receipts/<work-id>.json`; a aplicação incremental preserva recibos anteriores e retorna `REUSED` sem churn quando inalterada.

## Migração

- [ ] Para `WORKFLOW.md` v2/v3, executar `migrate-v4 ROOT` em preview e aplicar somente com `--expected-sha256`; usar `--allow-local-edits` apenas após revisar o diff.
- [ ] Preview primeiro e sem escrita.
- [ ] Mapear arquivos planos, `docs/adr`, `adrs` e `handoffs`.
- [ ] Validar tudo antes do staging.
- [ ] Rejeitar symlink inclusive quebrado e UTF-8 inválido.
- [ ] Aplicar por rename atômico; manter origem intacta.
- [ ] Target idêntico é `REUSED`; divergente é `BLOCKED`.

## `PLAN_ONLY_STOP`

Após pacote válido, auditoria `GO` e handoff entregue:

1. emitir `PLAN_ONLY_STOP`;
2. parar imediatamente;
3. não executar `specify|plan`;
4. não implementar código nem criar commit/merge;
5. deixar ship e reconciliação para ciclos externos.

Hooks `SessionStart|SubagentStart` são somente contexto read-only e nunca inicializam work items.
