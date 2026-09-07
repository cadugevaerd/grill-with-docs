# Contract: entrada `harness-plugin` em `dependencies.json`

Schema do manifesto permanece `grill-dependencies/v1`.

```json
{
  "id": "ponytail",
  "kind": "harness-plugin",
  "required": true,
  "plugin": "ponytail",
  "marketplace": "ponytail",
  "marketplace_source": "DietrichGebert/ponytail",
  "min": "4.9.0",
  "owner": "plugin ponytail",
  "reason": "modo de trabalho oficial do projeto (lazy senior dev); hooks exigem node no PATH para ativacao automatica",
  "install_by_runtime": {
    "claude": [
      ["claude", "plugin", "marketplace", "add", "DietrichGebert/ponytail"],
      ["claude", "plugin", "install", "ponytail@ponytail"]
    ],
    "codex": [
      ["codex", "plugin", "marketplace", "add", "DietrichGebert/ponytail"],
      ["codex", "plugin", "add", "ponytail@ponytail"]
    ]
  }
}
```

## Regras

- `kind` obrigatório em `KINDS = {"runtime","binary","path","harness","specify-extension","harness-plugin"}`.
- `install_by_runtime`: opcional; dicionário com chaves em `("claude","codex")`; cada valor é lista de argv (lista não vazia de strings). Forma inválida → `ManifestError("invalid install command for <id>")`.
- `install` e `install_by_runtime` podem coexistir; para um runtime presente em `install_by_runtime`, ele prevalece.
- `plugin` e `marketplace` obrigatórios para `harness-plugin`; ausência → `ManifestError("invalid harness-plugin entry for <id>")`.
- Nenhum campo novo é exigido dos kinds existentes.
