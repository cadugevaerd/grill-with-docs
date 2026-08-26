## Review Report

Verdict: APPROVE
Source fingerprint: tree 1c39f65b4dad64d77d7c38612d30ba7333e051a6cceb840c1cbb93363659ebf9 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan fb440b73d3784db6877322bfd708dbaeaa2943c9d45fd4cf8f9018b224e9f261

Casa exatamente com o registrado no `verify.md` desta rodada, nos três
componentes. `work` é o sha do vazio: nada pendente no escopo medido.

Segunda execução deste gate. A primeira, e o `verify` que a precedeu, mediram
sob uma regra de exclusão defeituosa; o diagnóstico está em `verify.md §Reexecução`.

### Test Quality

Nove casos de sucessão, todos verdes, cobrindo os dois caminhos e as duas
direções de declaração. A cobertura negativa é o ponto forte — ausência,
terceiro e transitividade têm caso dedicado, que é o que FR-012 exige para que
uma simplificação futura reprove em vez de passar silenciosamente.

Dois pares que carregam o peso da correção:

- `test_reconcile_succession_preserves_targeted_path_refusals` cria um ADR real
  para popular `qualified_ids` e afirma **literalmente**
  `ADR-CONFLICT:consumer->owner/ADR-0001` **junto com** a ausência de
  `SCOPE-OVERLAP`. É mais estrito que o pré-existente
  `test_targeted_reconcile_rejects_scope_and_adr_against_receipt`, cuja asserção
  é um `or` frouxo que passaria com qualquer um dos dois. Esse par é a prova de
  que a autorização não vazou para o conflito de decisão.
- `test_reconcile_succession_multi_id_dependency_authorizes_only_the_declared_prior`
  distingue "declara o prior" de "declara qualquer coisa" — com lista de um id
  só, os dois são indistinguíveis.

Menor, não bloqueante: vários casos agrupam sub-cenários com
`shutil.rmtree(self.root / ".grill")` entre eles, então uma falha no terceiro
sub-cenário não diz que os dois primeiros passaram e o nome do teste não
localiza. É o padrão da casa (`test_reconcile_detects_missing_dependency_and_cycle`
faz igual), logo consistência, não desleixo.

### Runtime Correctness

| Entrada | Comportamento | Correto |
|---|---|---|
| `depends-on-work` ausente | `.get(left, [])` → `[]` → False | sim |
| Lista vazia | False | sim |
| Malformada | mapa vazio no targeted, `[]` no completo; `DEPENDENCY-SCHEMA` ainda emitido | sim, fail-closed |
| Ids duplicados | `sorted(set(...))` nos dois caminhos | sim |
| Autorreferência | laço pula `prior_id == args.work_id` antes da consulta | sim |
| Par mutuamente declarado | escopo autorizado, `DEPENDENCY-CYCLE` ainda emitido no caminho completo | sim, agregado fail-closed |
| Cadeia transitiva | pertinência direta apenas; nenhum fechamento calculado | sim |

`ADR-CONFLICT` está fora do bloco autorizado no caminho targeted
(`grill_workspace.py:2025-2027`): dependência direta nunca o dispensa. Era o
vetor de vazamento mais provável e está fechado.

Sem mudança de estado persistido, sem migração, sem I/O novo, sem alteração no
lock de `reconcile --apply`.

### Readability

`overlap_authorized` (`grill_workspace.py:1634-1637`) é um retorno de uma linha
com comentário de porquê, no idioma do arquivo.

Registrado abaixo de Important: no caminho targeted (`:2020`) a regra direcional
que a ADR-0001 exige — "o alvo precisa declarar o prior" — é obtida passando um
mapa de **uma chave só** para um predicado **simétrico**. Funciona hoje por
construção: o recibo não guarda `depends-on-work`, então a chave do prior nunca
existe. Mas a direcionalidade está garantida por ausência de dado, não pela
chamada. Se o recibo passar a preservar dependências e alguém popular esse mapa,
a semântica vira em silêncio "qualquer um dos dois declara", permitindo que o
antecessor autorize um sucessor que nunca o declarou — sem teste falhando.
Correção sugerida: um comentário de uma linha no call site. Não bloqueia.

### Architecture

Predicado ao lado de `scopes_overlap`, não em `grill_core/`. Justificado em
`research.md §R-005` e `plan.md §Structure Decision`: os dados de que ele
depende só existem nos dois chamadores, e nenhum arquivo de `grill_core/` está
no escopo declarado. Uma regra, dois call sites, nenhum módulo novo, nenhum
import novo.

### Security

Nenhuma superfície nova: o predicado é puro, sem I/O, sem parse de entrada
externa. `depends-on-work` já era lido — mudou **quando**, não **se**. Nenhum
segredo ou arquivo de ambiente no diff.

Vale nomear o que a mudança faz em termos de segurança, porque é flexibilização
de controle: ela **remove uma recusa**. O risco não é injeção, é autorização
ampla demais. A mitigação é a estreiteza da regra — dependência direta
declarada, nunca inferida — e a cerca de testes negativos que FR-012 tornou
obrigatória.

### Performance

`right in dependencies.get(left, [])` é varredura linear em lista, avaliada
O(w²) vezes no caminho completo. Para dezenas de work items é irrelevante, e a
guarda entra **antes** do laço aninhado de caminhos: em pares autorizados
economiza O(p²) comparações em vez de custar.

Discrepância menor entre documento e código: `data-model.md` descreve o mapa
como conjunto com pertinência O(1); o código usa lista. Sem efeito prático nesta
escala, mas o documento promete estrutura que o código não usa.

### Escopo adicional revisado: correção do gate

`.specify/extensions/verify-review-ship/verify-review-ship-config.yml`, +13
linhas, autorizada explicitamente pelo humano após `ship` reportar `BLOCKED`.

O que faz: acrescenta `.grill/work-items/**/attestations/**` e
`.grill/work-items/**/SHIP-AUTHORIZATION.json` a `fingerprint_exclude`.

Correto e mínimo, por três razões:

1. **Corrige um padrão morto, não afrouxa a regra.** A config já declarava
   `.grill/attestations/**` com essa intenção — o comentário dela diz que bundle
   de atestação é evidência sobre a revisão e que contá-lo é "laço, não
   detecção". O caminho é que estava errado.
2. **Não usa a exclusão cega que foi autorizada.** `.grill/**` teria removido da
   detecção `WORK-ITEM.json`, evidência de triagem e `gauntlet.yaml`, que são
   conteúdo real. O padrão adotado é o mais estreito que resolve.
3. **O efeito foi comprovado, não assumido.** Cunhar um bundle no diretório de
   atestações e medir de novo devolve `tree` e `work` idênticos.

Risco residual: `SHIP-AUTHORIZATION.json` sai da detecção do fingerprint. É
aceitável porque o documento não é conteúdo revisado e porque o gate de `ship`
o valida por conta própria — `schema`, `scope`, `decision`, `authorized_by`,
`receipt_ref` e `content_sha256`, com o hash conferido contra o corpo. Excluí-lo
do fingerprint não o tira de nenhuma verificação.

O segundo defeito descoberto ao aplicar a correção — comentário entre itens da
lista descarta em silêncio o restante, porque o leitor para na primeira linha
não-item — está documentado na própria config. Vale mais que a correção: é uma
armadilha que faria a próxima pessoa acreditar ter excluído algo que não
excluiu. Corrigir o leitor é da extensão, não deste work item.

### Critical Issues

Nenhum.

### Important Issues

Nenhum.

### Constitution References (only for discovered conflicts)

Nenhum conflito descoberto.

Duas cláusulas tocadas por achados técnicos, ambas passando, citadas só por
isso: *Fail-closed sem waiver* — a flexibilização é a mais estreita possível e
cada caminho de escape tem teste negativo; *Bump obrigatório do plugin* —
`plugin/**` mudou e o gate reporta `BUMPED` de 5.2.0 para 5.2.1.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`

Três itens de registro, nenhum bloqueante:

1. Comentário de uma linha no call site targeted sobre o mapa de chave única.
2. `data-model.md` promete conjunto; o código usa lista.
3. O leitor de `fingerprint_exclude` descarta em silêncio itens após um
   comentário interleaved — defeito da extensão.
