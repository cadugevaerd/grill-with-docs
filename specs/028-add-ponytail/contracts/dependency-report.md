# Contract: relatório do preflight para `harness-plugin`

Saída de `ensure_dependencies.py ROOT --runtime claude|codex [--allow-install]` e do campo `dependencies` de `grill_workspace.py init|preflight`. Schema `grill-dependencies/v1`, inalterado.

## Item de relatório

```json
{"id": "ponytail", "kind": "harness-plugin", "required": true,
 "status": "present", "version": "4.9.0",
 "source": "/home/u/.claude/plugins/installed_plugins.json"}
```

| Cenário | `status` | `version` | `source` | `reason` | `remediation` |
|---|---|---|---|---|---|
| instalado ≥ min (Claude) | `present` | do registro | `.../installed_plugins.json` | — | — |
| instalado ≥ min (Codex) | `present` | do `plugin.json` da maior versão | `.../<versão>/.codex-plugin/plugin.json` | — | — |
| instalado < min | `outdated` | encontrada | caminho lido | `versao <v> abaixo do minimo 4.9.0` | comandos do runtime |
| registro/diretório ausente ou chave ausente | `missing` | `null` | `null` | `reason` da entrada | comandos do runtime |
| registro ilegível / forma inesperada | `undetermined` | `null` | `null` | `registro de plugins ilegivel: <path>` | — |

`remediation` (string): `claude plugin marketplace add DietrichGebert/ponytail && claude plugin install ponytail@ponytail` no runtime `claude`; `codex plugin marketplace add DietrichGebert/ponytail && codex plugin add ponytail@ponytail` no runtime `codex`.

## Efeitos no payload

- `missing_required` inclui `"ponytail"` quando `status != present` (inclusive `undetermined`, como hoje para as demais).
- `verdict`: `MISSING-DEPENDENCY` quando `missing_required` não vazio; `SKIPPED` sob `GRILL_SKIP_DEPENDENCIES=1`.
- Com `--allow-install`, `installed[]` recebe `{"id":"ponytail","status":"INSTALLED|FAILED","commands":[{"argv":[...],"returncode":N,"output":"..."}]}`; `undetermined` nunca entra em `installed`.

## Garantias

- `detect()` não executa processo para este kind.
- Nenhum item de outro kind muda de forma ou valor.
