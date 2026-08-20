# Review: Detecção de extensão pelo registro

**Date**: 2026-08-20 · **Branch**: `worktree-fix-preflight-ansi` · **Base**: `69ace7de` (v3.3.0)

Revisão técnica pós-`converge`/`verify`. Diff completo lido linha a linha, não apenas os gates.

## Achado 1 — corrigido nesta revisão

`extension_state` usava `if not record.get("enabled")`. Um registro cujo campo `enabled` esteja **ausente** cai nesse ramo e era reportado como "registrada porém desabilitada".

Isso é uma afirmação não observada — precisamente a classe de erro que esta correção existe para eliminar. O registro malformado e o registro desabilitado bloqueiam igual, mas apenas um dos dois foi observado, e apagar a diferença por conveniência contradiz a decisão que sustenta o trabalho inteiro (ADR-0002, cláusula **Evidência antes de afirmação**).

Severidade: baixa em probabilidade — o spec-kit sempre grava `enabled` —, alta em coerência. Um módulo que prega a distinção e não a pratica no próprio código perde a autoridade do argumento.

**Correção aplicada**: `enabled is not True` bloqueia; a razão distingue `enabled is False` ("desabilitada") de campo ausente ("sem estado de habilitacao reconhecivel"). Teste B5 acrescentado. Suíte: 1088 testes, exit 0.

## Achado 2 — aceito, não corrigido

`extension_registry()` é lida duas vezes por execução de `detect()`: uma na entrada `spec-kit-extension-registry` (via `schema_check`) e outra na primeira entrada `specify-extension`. O sentinela `_UNREAD` só memoiza dentro do laço de extensões.

Custo real: uma leitura extra de um arquivo de ~2 KB, contra o subprocess que a mudança **removeu**. O saldo de I/O é fortemente positivo. Memoizar entre os dois ramos exigiria carregar estado através de tipos de dependência diferentes, acoplando o ramo `path` ao ramo `specify-extension` para economizar um `read_text`.

Não vale o acoplamento. Registrado para não ser redescoberto como novidade.

## Achado 3 — observação, sem ação

`remediation()` aceita tanto lista de listas (`install`) quanto lista plana (`enable`) via `isinstance(commands[0], list)`. Funciona e está coberto, mas é polimorfismo de forma dentro do manifest.

A alternativa — exigir `[["specify","extension","enable","git"]]` — seria mais uniforme e mais ruidosa no JSON. Fica como está, com a heurística explícita numa linha só. Se um terceiro formato aparecer, normalizar na leitura do manifest será a saída correta.

## Verificações de risco

| Risco do `analyze` | Situação final |
|---|---|
| Correção cosmética passar como completa | **Fechado** — `test_slug_inside_a_description_is_not_a_match` e `test_ansi_wrapped_key_is_not_a_match` reprovam patch que só remova ANSI |
| `--allow-install` instalar sobre indeterminação | **Fechado** — `undetermined` fora de `pending`, com teste C8 |
| `kind: path` dar `present` com schema não reconhecido | **Fechado** — `schema_check`, com teste C3 |
| Contrato interno do spec-kit mudar | **Mitigado** — vira `undetermined`, nunca falso negativo |
| `undetermined` em schema `v1` sem bump do identificador | **Aceito e nomeado** (ADR-0004); validadores atualizados |

## Conformidade constitucional

| Cláusula | Situação |
|---|---|
| Evidência antes de afirmação | PASS — reforçada pelo Achado 1 |
| Work item isolado e ownership | PASS — bundle intocado, hash auditado preservado |
| Feature/fix plan-only | PASS — o plano parou em `PLAN_ONLY_STOP`; esta é a execução externa prevista |
| Sequência obrigatória | PASS — 11 etapas sem salto, `ship` a seguir |
| Verify/review antes de ship | PASS — `verify.md` e este documento precedem o ship |
| Fail-closed sem waiver | PASS — `undetermined` bloqueia; nenhum waiver usado |
| Rastreabilidade | PASS — FR ↔ ADR ↔ task ↔ commit ↔ SGD-16 |
| Bump obrigatório do plugin | PASS — 3.3.1 nos oito pontos, `validate_distribution.py: OK` |

## Qualidade do diff

211 inserções / 58 remoções em 13 arquivos, mais 1 novo. Nenhum arquivo fora do escopo de `assign.md`. `dependencies.json` com 33 inserções e zero remoções — sem reformatação mascarando mudança.

O parser antigo foi **removido**, não mantido em paralelo (F1, com teste). Nenhum `except Exception` (F2, com teste). Nenhum import novo; core segue stdlib-only.

## Veredito

**APROVADO** para `ship`.

Um achado corrigido durante a revisão, dois registrados sem ação com justificativa. A suíte fechou em 1088 testes e exit 0 depois da correção, não antes — a revisão alterou o código e foi revalidada.
