# PLAN-CONTEXT

## FASE-001 — Sucessão explícita de escopo reconciliado
- phase: FASE-001
- ADRs: ADR-0001
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW

**Uma regra, dois caminhos.** Extrair uma função pura no próprio
`grill_workspace.py` que receba os IDs dos dois trabalhos e o mapa de
dependências já normalizado. Ela autoriza a sobreposição somente quando um ID
aparece diretamente em `depends-on-work` do outro. Não calcular fechamento
transitivo e não consultar ordem lexical, timestamps ou ancestry Git.

**Reconcile completo.** `validate_reconciliation` já materializa
`dependencies[work_id]` e valida schema, ausência e ciclos. A comparação
pairwise de `scopes` deve chamar a regra direcional antes de emitir
`SCOPE-OVERLAP`. Schema inválido mantém lista vazia, portanto não concede
autorização; dependência ausente ou ciclo continua produzindo seu conflito
próprio mesmo que outro par seja válido.

**Reconcile targeted.** Ler e validar `target.metadata["depends-on-work"]`
antes do laço sobre receipts. Um `prior_id` só é dispensado da comparação de
escopo quando está no conjunto direto do target. Dependência de terceiro não
autoriza; `ADR-CONFLICT` continua sendo calculado sem qualquer dispensa. O
receipt não muda de schema: ele já preserva `depends_on_work` e sua própria
existência prova que o trabalho anterior chegou ao estado reconciliável.

**Matriz de prova.** Em `tests/validate_workspace_contract.py`, cobrir os dois
caminhos (full e targeted) com: dependência direta + overlap aceita; overlap sem
dependência recusado; dependência de terceiro recusada; cadeia A→B→C sem A→C
recusada para overlap A/C; dependência direta sem overlap continua aceita;
ciclo, ausência, self e conflito ADR preservados. O cenário targeted deve
aplicar primeiro o receipt de `owner` e provar que o preview do sucessor é
read-only.

**Autorização bootstrap.** Este work item declara dependência direta de
`feature-workflow-v3-7dc283c84fb54e6b8f10a9c4546cd473`, dono do receipt que
reivindica `grill_workspace.py` e `validate_workspace_contract.py`. Depois da
entrega, o SGD-19 deve declarar a mesma dependência antes de reconciliar.

**Distribuição.** A mudança em `plugin/**` exige bump patch `5.0.0 → 5.0.1`
sincronizado nos manifests, marketplaces, headings, README e
`tests/validate_distribution.py`, além da entrada no CHANGELOG. Verificação:
validador de workspace isolado, validador de distribuição isolado e suíte
completa; merge em main deve produzir tag e release no mesmo commit pelo
pipeline.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
