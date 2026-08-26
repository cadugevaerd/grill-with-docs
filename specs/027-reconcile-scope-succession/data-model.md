# Phase 1 — Data model

Nenhuma entidade nova é persistida e nenhum schema muda. O que segue descreve as
estruturas já existentes e, para cada uma, o que esta mudança passa a ler.

## Entidades persistidas (formato inalterado)

### Work item bundle — `.grill/work-items/<work_id>/WORK-ITEM.json`

| Campo | Tipo | Papel nesta mudança |
|---|---|---|
| `immutable.work_id` | string | Identidade do trabalho. Chave dos dois lados da relação. |
| `scope.paths` | lista de strings | Caminhos declarados. Normalizados por `normalized_scope`: relativos, sem `..`, sem barra final, ordenados e deduplicados. |
| `depends-on-work` | lista de strings | **Passa a ser lido também na decisão de escopo.** Já era lido para `DEPENDENCY-*`. |
| `conflicts-with-adrs` | lista de strings | Inalterado. Não interage com a autorização. |

Regras de validação (inalteradas): `scope.paths` que não seja lista de strings →
`SCOPE-SCHEMA`; caminho absoluto, com `..` ou vazio → `SCOPE-PATH`;
`depends-on-work` que não seja lista de strings → `DEPENDENCY-SCHEMA`.

### Recibo de reconciliação — `.grill/global/receipts/<work_id>.json`

| Campo | Tipo | Papel nesta mudança |
|---|---|---|
| `work_id` | string | Identifica o trabalho anterior. É o `prior_id` testado contra as dependências declaradas pelo alvo. |
| `scope` | lista de strings | Escopo preservado do trabalho concluído. Lado direito da comparação de sobreposição. |
| `qualified_ids` | lista de strings | Inalterado. Usado só por `ADR-CONFLICT`. |
| `identity` | objeto | Inalterado. |

**Nenhum campo é acrescentado, removido ou reinterpretado.** Um recibo gravado
antes desta mudança tem exatamente os dados de que a autorização precisa, porque
quem declara a relação é sempre o sucessor, nunca o recibo.

## Estruturas em memória

### `dependencies: dict[str, set[str]]`

Mapa `work_id → conjunto de dependências diretas declaradas`.

- **Caminho full**: já construído em `validate_reconciliation` a partir de todos
  os bundles avaliados (hoje como `dict[str, list[str]]`).
- **Caminho targeted**: passa a ser construído antes do laço de sobreposição, a
  partir do único bundle-alvo. Hoje é lido depois do laço — mover essa leitura é
  a mudança de ordem que a correção exige.

Invariante: um `work_id` cuja declaração é malformada mapeia para conjunto
**vazio**. Declaração inválida nunca autoriza.

Invariante: o mapa contém **apenas arestas diretas**. Nenhum fechamento
transitivo é calculado, em nenhum dos dois caminhos.

## Relação: autorização de sucessão

Relação binária sobre pares de trabalhos, derivada — não persistida.

```
authorized(a, b)  ⇔  b ∈ dependencies[a]  ∨  a ∈ dependencies[b]
```

| Propriedade | Valor | Consequência |
|---|---|---|
| Simétrica | sim | No caminho full a ordem do par não importa; a direção da declaração é que identifica o sucessor. |
| Transitiva | **não** | `authorized(A,B) ∧ authorized(B,C)` não implica `authorized(A,C)`. É o que FR-003 exige. |
| Reflexiva | irrelevante | O par `(x, x)` nunca é avaliado: o targeted pula `prior_id == work_id` e o full só forma pares distintos. |

No caminho targeted o alvo é sempre o sucessor candidato, então a forma usada é a
metade direcional: `authorized(target, prior) ⇔ prior ∈ dependencies[target]`.

## Efeito sobre as anotações de conflito

| Anotação | Efeito da autorização |
|---|---|
| `SCOPE-OVERLAP:<a>:<pa><-><b>:<pb>` | **Suprimida** quando `authorized(a, b)`. Único efeito da mudança. |
| `DEPENDENCY-SCHEMA:<id>` | Inalterada. Além disso, força `dependencies[id] = ∅`. |
| `DEPENDENCY-MISSING:<a>-><b>` | Inalterada. |
| `DEPENDENCY-NOT-RECONCILED:<a>-><b>` | Inalterada. |
| `DEPENDENCY-SELF:<id>` | Inalterada. |
| `DEPENDENCY-CYCLE:<id>` | Inalterada. Um par mutuamente declarado tem escopo autorizado e continua reprovado pelo ciclo. |
| `ADR-CONFLICT:<a>-><ref>` | Inalterada, e nunca dispensada por dependência. |
| `ADR-CONFLICT-SCHEMA:<id>` | Inalterada. |
| `CONSTITUTION-STALE`, `CONSTITUTION-CHECK`, `STATE-NOT-RECONCILABLE`, `ROADMAP-NOT-TERMINAL`, `DUPLICATE-WORK-ID` | Inalteradas. Avaliadas antes e independentemente. |

## Transições de estado

Nenhuma. A autorização é uma decisão de classificação, sem estado próprio, sem
persistência e sem ordem de aplicação. Preview e apply avaliam a mesma função
sobre os mesmos dados e portanto chegam ao mesmo conjunto de conflitos.
