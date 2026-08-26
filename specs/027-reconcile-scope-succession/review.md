## Review Report

Verdict: APPROVE
Source fingerprint: tree 75cb65c3be238787ec0b0c1319e9e9f267feb2e09e0f485b5962bdc0a7cc5cbc / work 0b6b719245b665d0cb15d2467058358eb1b83cc02ef2e4be48ef924b30f75183 / plan fb440b73d3784db6877322bfd708dbaeaa2943c9d45fd4cf8f9018b224e9f261

### Nota sobre a correspondência de fingerprint

O `verify.md` registrou `tree 90a82a5f… / work af0fa3d1…`; a medição atual dá
`tree 75cb65c3… / work 0b6b7192…`. **O componente `plan` é idêntico** nas duas.

A divergência **não** é mudança no que foi revisado. Entre as duas medições
houve exatamente um commit, de 9 arquivos: 6 bundles de atestação, `state.json`
e os 2 relatórios de gate. Os relatórios já são excluídos pela config; os
recibos e o `state.json` não são — e como `tree` é `git ls-files -s`, commitar
arquivo antes não-rastreado move o hash de `work` para `tree` mesmo sem um byte
de conteúdo revisado mudar.

Provado mecanicamente, não afirmado:

```
git diff --name-only 7cb6529 HEAD -- <os 11 caminhos do WORK-ITEM.json>   -> vazio
git status --porcelain -- <os 11 caminhos do WORK-ITEM.json>              -> vazio
```

Nenhum arquivo do escopo revisado mudou entre a medição do `verify` e esta.
A evidência do `verify` é fresca; o proxy é que tem um ponto cego.

**Achado sobre a ferramenta, não sobre o código**: `converge.fingerprint_exclude`
deveria cobrir `.grill/**`. Recibos de etapa são registro dos próprios gates —
exatamente a classe de artefato que a exclusão existe para neutralizar, pela
mesma razão que já exclui `verify.md`. Sem isso, qualquer ciclo que comite
receipts entre dois gates produz mismatch permanente. Fora do escopo deste work
item; registrado para quem mantém a extensão.

### Test Quality

Nove casos de sucessão, todos verdes, cobrindo os dois caminhos e as duas
direções de declaração. A cobertura negativa é o ponto forte: ausência, terceiro
e transitividade têm caso dedicado, que é o que FR-012 exige para que uma
simplificação futura reprove em vez de passar.

Dois destaques de qualidade real:

- `test_reconcile_succession_preserves_targeted_path_refusals` cria um ADR real
  para popular `qualified_ids` e então afirma **literalmente**
  `ADR-CONFLICT:consumer->owner/ADR-0001` **junto com** a ausência de
  `SCOPE-OVERLAP`. É mais estrito que o teste pré-existente
  `test_targeted_reconcile_rejects_scope_and_adr_against_receipt`, cuja asserção
  é um `or` frouxo que passaria com qualquer um dos dois. Esse par é a prova de
  que a autorização não vazou para o conflito de decisão.
- `test_reconcile_succession_multi_id_dependency_authorizes_only_the_declared_prior`
  distingue "declara o prior" de "declara qualquer coisa" — com lista de um id só
  os dois são indistinguíveis.

Observação menor, não bloqueante: vários casos agrupam sub-cenários com
`shutil.rmtree(self.root / ".grill")` entre eles. Uma falha no terceiro
sub-cenário não diz que os dois primeiros passaram, e o nome do teste não
localiza. O padrão já é o da casa (`test_reconcile_detects_missing_dependency_and_cycle`
faz igual), então é consistência, não desleixo.

### Runtime Correctness

Fronteiras verificadas uma a uma:

| Entrada | Comportamento | Correto |
|---|---|---|
| `depends-on-work` ausente | `.get(left, [])` → `[]` → False | sim |
| Lista vazia | False | sim |
| Malformada (não-lista, ou lista com não-string) | mapa vazio no targeted, `[]` no completo; `DEPENDENCY-SCHEMA` ainda emitido | sim, fail-closed |
| Ids duplicados | `sorted(set(...))` nos dois caminhos | sim |
| Autorreferência | laço pula `prior_id == args.work_id` antes da consulta | sim |
| Par mutuamente declarado | escopo autorizado, `DEPENDENCY-CYCLE` ainda emitido no caminho completo | sim, agregado continua fail-closed |
| Cadeia transitiva | pertinência direta apenas; nenhum fechamento calculado | sim |

`ADR-CONFLICT` está **fora** do bloco autorizado no caminho targeted
(`grill_workspace.py:2025-2027`), então dependência direta nunca o dispensa.
Este era o vetor de vazamento mais provável e está fechado.

Sem mudança de estado persistido, sem migração, sem novo I/O, sem alteração no
lock de `reconcile --apply`. Concorrência inalterada.

### Readability

`overlap_authorized` (`grill_workspace.py:1634-1637`) é uma linha de retorno com
comentário de porquê, no idioma do arquivo.

**Um ponto que merece registro, abaixo de Important**: no caminho targeted
(`:2020`) a regra direcional que a ADR-0001 exige — "o alvo precisa declarar o
prior" — é obtida passando um mapa de **uma chave só** para um predicado
**simétrico**. Funciona, e funciona hoje por construção: o recibo não guarda
`depends-on-work`, então a chave do prior nunca existe. Mas a direcionalidade
está garantida por ausência de dado, não pela chamada. Se um dia o recibo
passar a preservar dependências e alguém popular esse mapa, a semântica vira
silenciosamente "qualquer um dos dois declara" — permitindo que o antecessor
autorize um sucessor que nunca o declarou. Sem teste falhando.

Correção concreta sugerida, barata: um comentário de uma linha no call site
dizendo que o mapa é deliberadamente de chave única e por quê. Não bloqueia o
ship; a alternativa mais forte seria um segundo helper direcional, o que
duplicaria a regra que FR-008 quer única.

### Architecture

O predicado vive ao lado de `scopes_overlap`, não em `grill_core/`. A decisão
está justificada em `research.md §R-005` e `plan.md §Structure Decision`: os
dados de que ele depende só existem nas duas funções chamadoras, e nenhum
arquivo de `grill_core/` está no escopo declarado. Uma regra, dois call sites,
nenhum módulo novo, nenhum import novo. Direção de dependência inalterada.

### Security

Nenhuma superfície nova: o predicado é puro, não faz I/O, não parseia entrada
externa. `depends-on-work` já era lido antes desta mudança — o que mudou foi
**quando**, não **se**. Nenhum segredo, credencial ou arquivo de ambiente no
diff.

Vale nomear o que a mudança faz em termos de segurança, porque é uma
flexibilização de controle: ela **remove uma recusa**. O risco não é injeção, é
autorização ampla demais. A mitigação é a estreiteza da regra (dependência
direta declarada, nunca inferida) e a cerca de testes negativos que FR-012
tornou obrigatória. Ausência, terceiro e transitividade continuam bloqueando, e
cada um tem teste dedicado.

### Performance

`right in dependencies.get(left, [])` é varredura linear em lista, avaliada
O(w²) vezes no caminho completo. Para dezenas de work items é irrelevante, e a
guarda entra **antes** do laço aninhado de caminhos, então em pares autorizados
ela economiza O(p²) comparações em vez de custar.

Discrepância menor entre documento e código: `data-model.md` descreve o mapa
como `dict[str, set[str]]` com pertinência O(1); o código usa `list[str]`. Sem
efeito prático nesta escala, mas o documento promete uma estrutura que o código
não usa.

### Critical Issues

Nenhum.

### Important Issues

Nenhum.

### Constitution References (only for discovered conflicts)

Nenhum conflito descoberto.

Duas cláusulas foram tocadas por achados técnicos e **passam**, citadas apenas
por isso: *Fail-closed sem waiver* — a flexibilização é a mais estreita possível
e cada caminho de escape tem teste negativo; *Bump obrigatório do plugin* —
`plugin/**` mudou e o gate reporta `BUMPED` de 5.2.0 para 5.2.1.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`

Dois itens levados adiante como registro, nenhum bloqueante:

1. Comentário de uma linha no call site targeted sobre o mapa de chave única.
2. `converge.fingerprint_exclude` deveria cobrir `.grill/**` — defeito da
   extensão, não deste work item.
