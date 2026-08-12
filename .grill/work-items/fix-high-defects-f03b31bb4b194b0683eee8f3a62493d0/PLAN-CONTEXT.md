# PLAN-CONTEXT

## FASE-001 — Virada de fase auditada
- phase: FASE-001
- ADRs: ADR-0001
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
O escritor de estado é o subcomando `checkpoint` em `grill_workspace.py`. A regra que bloqueia está em `:1810`: `in-progress` exige `current in {pending, blocked}` e todos os passos anteriores `complete`. Depois de um ciclo, `specify` está `complete` e a condição é insatisfazível.

`development.audit` é `setdefault("audit", [])` com append por transição (`:1803`). Já contém 22 entradas no work item anterior, cobrindo os 11 passos de uma fase. Isso é o que permite resetar `steps` sem perder histórico — e é a razão de ADR-0001 não mexer no schema.

Restrição dura: nenhum bundle existente pode precisar de migração. O work item `feature-release-repo-sync` está terminal e reconciliado, com recibo em `.grill/global/receipts/`; qualquer mudança que o invalide quebra a projeção global.

A mensagem de `INVALID-TRANSITION` precisa nomear o comando de virada. Sem isso, o operador que esquecer o passo reencontra exatamente o sintoma de hoje e não tem como saber que existe saída — o defeito volta disfarçado de erro legítimo.

Testes vivem em `tests/validate_workspace_contract.py`, coletado por glob em `tests/run_validators.py`. A matriz de CI não tem `specify`, `node` nem `backlogctl`, então nada pode depender deles.

## FASE-002 — Deriva viva precisa
- phase: FASE-002
- ADRs: ADR-0002
- BLs: none
- delivery-units: DU-002
- development-type: platform-devops

### HOW
O ponto único é `grill_status.py:87`, hoje um `or` que une duas comparações de naturezas diferentes. A de head é insatisfazível por construção; a de branch é satisfazível durante o trabalho e insatisfazível depois do ship, quando o branch é apagado.

O conceito de "terminal" já existe no auditor, que exige `state.status=complete`, `milestone_status=completed`, `active_phase=null` e todas as fases terminais para emitir `MILESTONE-COMPLETE`. `status` precisa da mesma noção, e as duas leituras têm de concordar — se divergirem, o finding aparece ou some na hora errada. A fonte é `state.json`, já lida por ambos.

`immutable_sha256` e `CONSTITUTION-HASH-MISMATCH` continuam intocados; são eles que seguram a tamper-evidence depois de removida a metade de head.

Contrato de status a preservar: saída JSON de linha única, byte-idêntica entre execuções, e leitura read-only. `tests/validate_status_contract.py` trava os três, incluindo o snapshot que hoje exclui `.git/`.

## FASE-003 — Gate de bump bloqueante
- phase: FASE-003
- ADRs: ADR-0003
- BLs: none
- delivery-units: DU-003
- development-type: platform-devops

### HOW
`on.pull_request.paths` é declarado no nível do workflow. Não existe filtro por job, então o gate só escapa do filtro da matriz saindo do `ci.yml` para um arquivo próprio sem `paths:`.

`tests/check_version_bump.py` já devolve `NO-PLUGIN-CHANGE` quando `plugin/` não muda, e o job custou 8s no run 31622181169. Rodar sempre é barato e o veredito é real — não é shim.

O `ci.yml` conserva o filtro e a guarda de deduplicação adicionada em `e107b19`, que pula a matriz em merge de PR. A guarda é `pull_request` OR `!startsWith(head_commit.message, 'Merge pull request ')`; ela não alcança o gate, que roda só em `pull_request`.

Dois cuidados no corte: `fetch-depth: 0` é obrigatório, porque o clone raso não contém a merge base; e a base vem de `github.event.pull_request.base.sha`, nunca de nome de branch, porque no evento `pull_request` o checkout é um merge commit efêmero. Os dois já estão comentados no `ci.yml` atual e precisam viajar junto.

Fora do alcance de commit: registrar o check no branch protection. É ato humano no GitHub e precisa aparecer como tal no fechamento da fase, senão o código fica pronto e FR-007 continua descumprido.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
