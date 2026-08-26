# Contract — autorização de sucessão de escopo em `reconcile`

Interface pública afetada: o subcomando `grill_workspace.py reconcile`, nas duas
formas. Este documento fixa o comportamento observável; a implementação é livre
desde que o satisfaça.

## Superfície

```
grill_workspace.py reconcile ROOT [--work-id ID] [--apply]
                             [--integration-branch BRANCH]
                             [--source-root PATH ...] [--source-ref REF ...]
```

- Sem `--work-id`: reconciliação **completa**, sobre todos os bundles avaliados.
- Com `--work-id`: reconciliação **targeted**, do alvo contra os recibos já
  gravados.

Saída: um objeto JSON com `verdict`, `code`, `work_ids`, `qualified_ids`,
`conflicts` e `count`. Códigos de saída inalterados: `0` sem conflito, `1`
`NO-GO`, `2` `BLOCKED`.

## C-001 — Autorização por dependência direta (targeted)

**Dado** um recibo gravado de `prior` cujo `scope` contém `P`
**e** um alvo `succ` cujo `scope.paths` contém `Q`, com `P` e `Q` sobrepostos
**e** `succ["depends-on-work"]` contendo `prior`
**quando** `reconcile ROOT --work-id succ` é executado
**então** `conflicts` não contém nenhuma entrada
`SCOPE-OVERLAP:succ:*<->prior:*`.

## C-002 — Autorização por dependência direta (full)

**Dado** dois bundles `a` e `b` avaliados na mesma execução, com escopos
sobrepostos
**e** `b ∈ a["depends-on-work"]` **ou** `a ∈ b["depends-on-work"]`
**quando** `reconcile ROOT` é executado
**então** `conflicts` não contém entrada `SCOPE-OVERLAP` para o par `(a, b)`.

## C-003 — Ausência de dependência continua bloqueando

**Dado** escopos sobrepostos entre `a` e `b`
**e** nenhum dos dois declarando o outro
**quando** qualquer uma das duas formas é executada
**então** a entrada `SCOPE-OVERLAP` correspondente está em `conflicts`
**e** o código de saída é `1`.

## C-004 — Dependência de terceiro não autoriza

**Dado** escopos sobrepostos entre `a` e `b`
**e** `a["depends-on-work"] == ["c"]`, com `c` distinto de `b`
**quando** qualquer uma das duas formas é executada
**então** a entrada `SCOPE-OVERLAP` para o par `(a, b)` está em `conflicts`.

## C-005 — Transitividade não autoriza

**Dado** `a["depends-on-work"] == ["b"]` e `b["depends-on-work"] == ["c"]`
**e** os escopos de `a` e `c` sobrepostos, com `c ∉ a["depends-on-work"]`
**quando** qualquer uma das duas formas é executada
**então** a entrada `SCOPE-OVERLAP` para o par `(a, c)` está em `conflicts`.

## C-006 — Declaração malformada não autoriza

**Dado** `a["depends-on-work"]` que não é uma lista de strings
**e** escopo de `a` sobreposto ao de `b`
**quando** qualquer uma das duas formas é executada
**então** `DEPENDENCY-SCHEMA:a` está em `conflicts`
**e** a entrada `SCOPE-OVERLAP` para o par `(a, b)` também está.

## C-007 — Recusas independentes preservadas

Para cada situação abaixo, a anotação indicada permanece em `conflicts`
exatamente com o formato atual, **mesmo quando** há dependência direta declarada
entre os trabalhos envolvidos:

| Situação | Anotação preservada |
|---|---|
| Dependência para trabalho ausente do conjunto avaliado (full) | `DEPENDENCY-MISSING:<a>-><b>` |
| Dependência para trabalho ainda não reconciliado (targeted) | `DEPENDENCY-NOT-RECONCILED:<a>-><b>` |
| Trabalho que declara a si mesmo (targeted) | `DEPENDENCY-SELF:<a>` |
| Ciclo de dependências | `DEPENDENCY-CYCLE:<id>` |
| Conflito com decisão registrada em recibo | `ADR-CONFLICT:<a>-><ref>` |
| Referência de decisão malformada | `ADR-CONFLICT-SCHEMA:<a>` |

## C-008 — Preview read-only

**Dado** qualquer entrada, autorizada ou não
**quando** `reconcile` é executado sem `--apply`
**então** nenhum byte sob `ROOT` muda.

## C-009 — Apply atômico e idempotente

**Dado** um par autorizado sem nenhum outro conflito
**quando** `reconcile ... --apply --integration-branch <branch>` é executado duas
vezes
**então** a primeira execução devolve `verdict: "APPLIED"`, a segunda devolve
`verdict: "REUSED"`, e o conteúdo de `.grill/global/` é idêntico byte a byte
entre as duas — inclusive `mtime`.

## C-010 — Recibos legados sem migração

**Dado** recibos gravados antes desta mudança
**quando** `reconcile` os lê
**então** são aceitos sem conversão, e os recibos gravados depois têm exatamente
os mesmos campos.

## C-011 — Versão sincronizada

**Dado** a árvore após esta mudança
**quando** `tests/validate_distribution.py` é executado
**então** a versão `5.2.1` aparece exatamente uma vez em cada um dos oito pontos
fixados, sem divergência.
