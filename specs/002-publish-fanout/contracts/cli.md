# Contrato de linha de comando — `tests/publish_to_marketplace.py`

## Invocação

```text
python3 tests/publish_to_marketplace.py --target claude|codex --checkout DIR \
    --version X.Y.Z --ref vX.Y.Z --sha <sha40> [--apply] [--json]
```

- `--target` obrigatório: um dos alvos declarados. Desconhecido é erro de uso.
- `--checkout` obrigatório: clone do marketplace, contendo o índice esperado.
- `--version`, `--ref`, `--sha` obrigatórios: a release a publicar.
- `--apply` ausente: preview, nada é escrito.
- `--json`: uma única linha JSON.

O publicador **não** clona, não cria tag e não empurra. Recebe um checkout pronto e reescreve o índice. Isso o mantém testável sem rede e sem credencial.

## Saída

```json
{"target":"codex","verdict":"APPLIED","changed":true,"entry":"CREATED",
 "version":"2.5.0","ref":"v2.5.0","sha":"45f6b98…","index":".agents/plugins/marketplace.json"}
```

`entry` é `CREATED`, `UPDATED` ou `UNCHANGED`. `verdict` é `PREVIEW` ou `APPLIED`.

## Exit codes

| Código | Significado |
|---|---|
| `0` | `PREVIEW` ou `APPLIED`, com ou sem mudança |
| `1` | destino inconsistente: índice ausente, JSON inválido, `plugins` não é lista, ou entrada existente com `source` de tipo inesperado |
| `2` | uso incorreto: alvo desconhecido, checkout inexistente, versão/ref/sha malformados |

Não existe saída que signifique "não publicado por falta de informação". Informação insuficiente é reprovação.

## Contrato de biblioteca

- `parse_release(version, ref, sha) -> Release` — valida formato; `ValueError` em entrada inválida
- `plan_entry(index, target, release, meta) -> EntryPlan` — puro; entrada resultante e status
- `apply_entry(checkout, target, plan) -> None` — reescreve o índice preservando formatação e ordem
