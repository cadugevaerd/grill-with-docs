# Contract — geração e verificação da projeção

Dois subcomandos novos. Ambos falam apenas o contrato público do backlog e nunca leem o armazenamento.

```text
grill_workspace.py backlog-project ROOT --work-id ID [--apply] [--db PATH]
grill_workspace.py backlog-verify  ROOT --work-id ID [--db PATH]
```

## `backlog-project`

Gera o registro a partir da fatia de autoridade. Preview é o padrão; `--apply` escreve.

```json
{
  "schema": "grill-projection/v1",
  "db": "<caminho>",
  "work_id": "<id>",
  "mark": "<marca de origem>",
  "entries": 4,
  "changed": false,
  "verdict": "PREVIEW"
}
```

`verdict` é `PREVIEW` quando nada foi escrito, `APPLIED` quando o arquivo mudou, e `REUSED` quando `--apply` foi pedido e o conteúdo gerado já era idêntico ao existente — o caso que prova o determinismo.

Escrita é atômica: staging mais rename. Interrupção não deixa arquivo parcial.

## `backlog-verify`

Compara registro e autoridade. Nunca escreve.

```json
{
  "schema": "grill-projection/v1",
  "db": "<caminho>",
  "work_id": "<id>",
  "verdict": "FRESH",
  "divergences": []
}
```

`verdict` é `FRESH` sem divergência e `DIVERGED` com. Cada entrada de `divergences` traz `id`, `type` e o detalhe. Sem a autoridade disponível, recusa com `BACKLOG-UNAVAILABLE` — nunca afirma frescor que não pode comprovar.

## Envelopes de recusa

| `code` | Quando | Exit |
|---|---|---|
| `BACKLOG-NOT-BOUND` | repositório sem backlog vinculado | 2 |
| `BACKLOG-UNAVAILABLE` | binário não resolvido, ou resposta fora do contrato | 2 |
| `IMMUTABLE-TAMPERED` | bloco imutável do work item adulterado | 2 |

`db` está presente em todo envelope, inclusive nas recusas, pela mesma razão da fase anterior: o resultado precisa ser idêntico com e sem o binário instalado.

## Efeito no gate de auditoria

A auditoria passa a exigir a marca de origem no registro e reprova com `PROJECTION-UNMARKED` quando ela falta. Ela **não** consulta a autoridade, por ADR-0002, e continua sem executar processo externo. Frescor não é responsabilidade dela.
