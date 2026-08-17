# Contract — `backlog-sync`

Interface pública afetada por esta fase. Duas portas de entrada equivalentes: o subcomando do workspace e a ponte crua.

```text
grill_workspace.py backlog-sync ROOT --work-id ID [--apply]
backlog_bridge.py ROOT --work-item PATH --work-id ID [--apply] [--db PATH]
```

Saída: um objeto JSON por execução, em uma linha, chaves ordenadas.

## Pré-condições

| Condição | Antes | Depois desta fase |
|---|---|---|
| Bloco imutável íntegro | exigido | exigido, inalterado |
| Artefatos idênticos aos do `init` | **exigido** | **não exigido** |
| Repositório vinculado a um backlog | exigido | exigido, inalterado |

## Envelope de sucesso

```json
{
  "schema": "grill-backlog/v1",
  "db": "<caminho>",
  "backlog": {"status": "BOUND", "code": "SGD", "name": "...", "bound_path": "..."},
  "changed": false,
  "verdict": "PREVIEW",
  "items": [
    {"id": "BL-0001", "status": "PROPOSED", "state": "open", "target": "in_progress"}
  ]
}
```

`verdict` é `PREVIEW` quando nada mudou e `APPLIED` quando ao menos uma mutação ocorreu. `changed` acompanha. `db` está presente em **todo** envelope, inclusive nas recusas, para que a resposta sempre diga qual store foi alvo.

Cada entrada de `items` carrega `id`, `status` de desfecho, o `state` da decisão de origem e o `target` no backlog. Desfechos possíveis: `PROPOSED`, `APPLIED`, `REUSED`, `TRANSITIONED`, `TRANSITION-REFUSED`, `STATE-UNKNOWN`.

`TRANSITION-REFUSED` não é recusa da execução: o comando conclui, o item fica intocado e o operador decide. A ponte nunca emite `item reconcile-status` para contornar a FSM.

## Envelopes de recusa

| `code` | Quando | Exit |
|---|---|---|
| `BACKLOG-NOT-BOUND` | repositório sem backlog vinculado | 2 |
| `BACKLOG-UNAVAILABLE` | binário não resolvido, ou resposta fora do contrato | 2 |
| `IMMUTABLE-TAMPERED` | bloco imutável do work item adulterado | 2 |

`BUNDLE-INTEGRITY` deixa de ser alcançável por este comando. Continua válido nos comandos que legitimamente exigem bundle intocado.

Toda recusa de pré-condição — vínculo, identidade, disponibilidade — ocorre antes da primeira mutação, porque o conjunto completo de propostas é calculado antes de qualquer escrita. Uma interrupção no meio da aplicação não é compensada: não há transação entre chamadas sucessivas. A garantia oferecida é de convergência, não de atomicidade — a execução seguinte reconhece o que já existe, completa o que falta e não duplica.

## Contrato falado com o backlog operacional

Sempre `--json`, sempre com `--db`. Resposta aceita apenas com `result=ok` e `contract_version=2`. Acesso direto ao armazenamento é proibido.

Comandos emitidos por esta fase:

```text
backlog list
item list --code CODE
item add --code CODE --title TITLE --description TEXT --status STATE --criticality C --category general
item transition --id ID --status STATE
```

`item add --status` é snapshot inicial, não transição. `item transition` só é emitido para destinos legais na FSM.

## Idempotência

Duas execuções consecutivas com `--apply` sobre o mesmo work item, sem alteração no bundle, produzem o mesmo conjunto de itens. A segunda execução relata todas as decisões como `REUSED`, com `changed: false` e `verdict: PREVIEW`.
