# Data Model: Ponytail na stack oficial

## Entidades

### Dependência declarada (`dependencies.json` → entrada)

| Campo | Tipo | Regra |
|---|---|---|
| `id` | string única | `"ponytail"` |
| `kind` | enum | `"harness-plugin"` (novo em `KINDS`) |
| `required` | bool | `true` |
| `plugin` | string | `"ponytail"` — nome do plugin no marketplace |
| `marketplace` | string | `"ponytail"` — nome local do marketplace (chave `<plugin>@<marketplace>`) |
| `marketplace_source` | string | `"DietrichGebert/ponytail"` — fonte registrada pelo `marketplace add` |
| `min` | string SemVer | `"4.9.0"` |
| `owner` | string | `"plugin ponytail"` |
| `reason` | string | motivo humano |
| `install_by_runtime` | `{runtime: [[argv...], ...]}` | chaves ⊆ `RUNTIMES`; cada argv lista não vazia de strings |

Validação em `load_manifest`: `kind ∈ KINDS`; `install` (se houver) lista de argv; `install_by_runtime` (se houver) dicionário cujas chaves ∈ `RUNTIMES` e valores lista de argv.

### Registro de plugins do harness (leitura)

| Harness | Caminho | Forma | Versão |
|---|---|---|---|
| Claude Code | `<CLAUDE_CONFIG_DIR|~/.claude>/plugins/installed_plugins.json` | `{"plugins": {"<plugin>@<marketplace>": [{"version": "...", "installPath": "...", "scope": "..."}]}}` | `plugins[key][0].version` |
| Codex | `<CODEX_HOME|~/.codex>/plugins/cache/<marketplace>/<plugin>/<versão>/.codex-plugin/plugin.json` | `{"name": "...", "version": "..."}` | maior `<versão>` por `parse_version`; `version` do JSON, fallback nome do diretório |

### Relatório por dependência (`detect()` → item)

| Campo | Valor para `harness-plugin` |
|---|---|
| `id`, `kind`, `required` | copiados da entrada |
| `status` | `present` \| `outdated` \| `missing` \| `undetermined` |
| `version` | string ou `null` |
| `source` | caminho lido (arquivo Claude ou `plugin.json` Codex) ou `null` |
| `reason` | quando não `present`: motivo observado (`registro de plugins ilegivel: <path>` para `undetermined`; `reason` da entrada para `missing`; `versao <v> abaixo do minimo <min>` para `outdated`) |
| `remediation` | quando não `present` e não `undetermined`: comandos do runtime ativo unidos por ` && ` |

### Resultado de instalação (`install()` → item)

Inalterado: `{"id", "status": INSTALLED|FAILED|BLOCKED|SKIPPED, "commands": [{"argv", "returncode", "output"}]}`. Para `harness-plugin`, `commands` vem de `install_by_runtime[runtime]`.

## Transições de estado

```text
[registro ausente | chave ausente] ──► missing ──(--allow-install, sucesso)──► present
[registro ilegível]                 ──► undetermined (nunca instala, nunca "present")
[versão < min]                      ──► outdated ──(--allow-install, sucesso)──► present
[GRILL_SKIP_DEPENDENCIES=1]         ──► SKIPPED (relatório vazio; nunca OK)
```

## Invariantes

- Nenhum kind existente muda de relatório (comparação antes/depois idêntica — SC-004).
- `harness-plugin` nunca chama `tools.run` em `detect()`; só `install()` executa, e só sob `--allow-install`.
- `undetermined` nunca entra em `pending` de `install()` (regra já existente).
