# Contrato de linha de comando — `tests/check_version_bump.py`

## Invocação

```text
python3 tests/check_version_bump.py --base-ref REF [--head-ref REF] [--json]
```

- `--base-ref` obrigatório: referência da base de merge da pull request.
- `--head-ref` opcional, padrão `HEAD`.
- `--json` opcional: emite uma única linha JSON em stdout em vez de texto humano.

## Saída

Sempre uma decisão explícita. Em modo JSON, um único objeto:

```json
{"verdict":"FAIL","code":"MISSING-BUMP","base_version":"2.5.0","head_version":"2.5.0","message":"..."}
```

Em modo texto, uma mensagem que nomeia `base_version`, `head_version` e a exigência.

## Exit codes

| Código | Significado |
|---|---|
| `0` | `PASS` — sem mudança em `plugin/`, ou versão aumentou |
| `1` | `FAIL` — mudou `plugin/` sem bump, ou a versão regrediu |
| `2` | `FAIL` — versão ausente, malformada ou ilegível em qualquer um dos lados; também uso incorreto |

Não existe código de saída que signifique "não verificado". A ausência de informação suficiente é reprovação, não neutralidade.

## Contrato de biblioteca

O módulo expõe funções puras, sem git e sem I/O, para permitir teste direto:

- `parse_version(text) -> tuple[int,int,int]` — levanta `ValueError` em formato inválido
- `touches_plugin(paths) -> bool`
- `decide(paths, base_version, head_version) -> Verdict`

A camada que fala com `git` é fina e fica isolada dessas funções.
