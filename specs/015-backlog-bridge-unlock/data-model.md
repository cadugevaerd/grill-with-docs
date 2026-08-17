# Data Model — FASE-001

Nenhum armazenamento próprio é introduzido. As entidades abaixo existem em memória durante uma execução do espelho, ou pertencem a sistemas já existentes.

## Decisão adiada (lida do bundle)

Origem: blocos `## BL-NNNN — <título>` em `DECISION-BACKLOG.md` do work item, parseados por `parse_deferred`.

| Campo | Origem | Regra |
|---|---|---|
| `id` | cabeçalho do bloco | casa `BL-\d{4}`; local ao work item |
| `title` | cabeçalho do bloco | texto após o travessão |
| `state` | campo `state` do bloco | um de `open`, `resolved`, `superseded` |
| `criticality` | campo do bloco, quando presente | um de `critical`, `high`, `medium`, `low`; ausente vira `medium` |
| demais campos | campos livres do bloco | copiados para a descrição do item |

Mudança nesta fase: a entrada deixa de ser descartada quando `state != "open"`. O estado passa a ser dado de saída, não critério de filtro.

## Item de backlog

Pertence ao backlog operacional. A ponte nunca o cria diretamente no armazenamento; só através da interface pública.

| Campo | Uso pela ponte |
|---|---|
| `id` | atribuído pelo backlog, necessário para transicionar |
| `status` | comparado com o estado desejado para decidir se há transição |
| `description` | carrega os marcadores de vínculo |
| `criticality`, `category` | preenchidos na criação |

## Vínculo

Chave: `(work_id, BL-NNNN)`.

Materializado como duas linhas no fim da `description` do item:

```text
grill-work-id: <work_id>
grill-bl: BL-NNNN
```

Recuperado por varredura das descrições dos itens do backlog. Não há campo estruturado disponível na criação, conforme D4 do research.

Mudança nesta fase: o índice deixa de ser um conjunto de chaves e passa a mapear a chave para a identidade e o estado atual do item, para permitir reconciliação.

## Mapa de estados

Tabela única, consultada nas duas direções, derivada da FSM medida em D3.

| Estado da decisão | Estado do item | Momento |
|---|---|---|
| `open` | `in_progress` | criação, via snapshot inicial |
| `resolved` | `done` | transição a partir de `in_progress` |
| `superseded` | `cancelled` | transição a partir de `in_progress` |

Item criado já em estado terminal usa snapshot inicial na criação, o que é legal e dispensa transição.

Transições que a ponte nunca emite: qualquer destino `open` ou `merged`.

## Desfecho por decisão

Valor de relato, um por decisão processada.

| Desfecho | Significado |
|---|---|
| `PROPOSED` | prévia; item seria criado |
| `APPLIED` | item criado nesta execução |
| `REUSED` | vínculo já existia e o estado já estava correto |
| `TRANSITIONED` | vínculo já existia e o estado do item foi corrigido |
| `TRANSITION-REFUSED` | vínculo já existia e o estado desejado é inalcançável a partir do atual; nada foi tocado |
| `STATE-UNKNOWN` | o estado declarado na decisão não pertence ao vocabulário conhecido; nada foi criado nem transicionado |
| `FAILED` | a mutação desta decisão foi tentada e o backlog recusou |
| `SKIPPED` | não foi tentada porque uma mutação anterior já havia falhado |

`TRANSITIONED` é novo nesta fase e é o que permite ao operador distinguir "nada a fazer" de "estado reconciliado". `TRANSITION-REFUSED` cobre o caso em que a FSM não admite o caminho, por exemplo item já em `done` cuja decisão voltou a `open`; a ponte não força, não usa o reparo administrativo e não silencia.
