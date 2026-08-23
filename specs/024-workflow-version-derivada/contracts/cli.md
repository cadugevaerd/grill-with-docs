# Contrato de CLI

**Phase**: 1 | Superfície pública afetada: dois comandos de `grill_workspace.py`.

## `init` / `migrate` — criação de bundle

### Sucesso

Sem mudança de forma. O objeto `workflow` do resultado já carrega `path`, `sha256` e `status`; nenhum campo novo é acrescentado à saída.

Efeito observável: o `state.json` escrito passa a declarar a versão resolvida do documento nos dois campos, conforme o mapa de derivação em [data-model.md](../data-model.md).

### Recusa nova

```json
{
  "verdict": "BLOCKED",
  "code": "WORKFLOW-MARKER-UNRESOLVED",
  "workflow": {
    "path": "WORKFLOW.md",
    "markers_found": 0,
    "accepted": ["v2", "v3", "v4"]
  }
}
```

| Campo | Conteúdo |
|---|---|
| `code` | `WORKFLOW-MARKER-UNRESOLVED`, cunhado em `SCREAMING_SNAKE` e traduzido para KEBAB na fronteira, como os demais |
| `markers_found` | quantidade de declarações encontradas: `0`, ou `>= 2` |
| `accepted` | as versões aceitas, para a mensagem dizer o que fazer |

Exit code: `2` (`BLOCKED`), consistente com as demais recusas de uso.

**Garantia**: a recusa ocorre antes de qualquer escrita. Nenhum diretório de work item, staging ou arquivo existe depois dela.

**Caso não reconhecido**: uma declaração única cujo valor não está em `ACCEPTED_WORKFLOW_MARKERS` recusa pelo mesmo código, com `markers_found: 1`. É declaração única mas não é aceita, e o campo `accepted` é o que diz por quê.

## `audit` — asserção de estado

### Antes

```
findings: ["state: workflow version divergence"]   # sempre que version != "v2"
```

### Depois

```
findings: ["state: workflow version divergence"]   # somente se version ∉ ACCEPTED_WORKFLOW_MARKERS
```

A string do finding **não muda**: ela já descreve corretamente a condição, e mudá-la quebraria consumidores que casam pelo texto sem ganho algum.

Casos que passam a aprovar: `v3` e `v4`. Casos que continuam aprovando: `v2` — é o que preserva a frota. Casos que continuam reprovando: `null`, valor fora do conjunto, campo ausente, `workflow` não-objeto.

## Superfície interna consumida

| Símbolo | Módulo | Papel |
|---|---|---|
| `sole_managed_version(text)` | `ensure_workflow.py` | detector estrito, novo |
| `managed_version(text)` | `ensure_workflow.py` | inalterado, 7 chamadores |
| `ACCEPTED_WORKFLOW_MARKERS` | `audit_decisions.py:70` | conjunto aceito, já existente |
| `SEQUENCE_BY_VERSION` | `grill_workspace.py:2162` | domínio de `development.workflow_version` |
