# Data Model — FASE-002

Nenhum armazenamento próprio. Um artefato novo, derivado.

## Registro de decisões (projeção)

Arquivo `DECISION-BACKLOG.md` do work item. Versionado, gerado, read-only para humanos.

Formato por bloco, fixado por `audit_decisions.py` e não negociável:

```text
## BL-NNNN — <título>
- state: open | resolved | superseded
- phase: FASE-NNN
- owner: <texto>            (obrigatório quando state é open)
- evidence-needed: <texto>  (obrigatório quando state é open)
- next-action: <texto>      (obrigatório quando state é open)
- <demais campos preservados>
```

Cabeçalho e rodapé carregam a marca de origem e o aviso de que o arquivo é gerado.

## Mapa inverso de estados

A FASE-001 traduz decisão para item. Esta fase precisa do caminho de volta.

| Estado do item | Estado da decisão |
|---|---|
| `in_progress` | `open` |
| `done` | `resolved` |
| `cancelled` | `superseded` |

`open` e `merged` não são produzidos pela ponte, então encontrá-los é condição anômala e vira divergência nomeada, não tradução silenciosa.

## Marca de origem

Valor derivado exclusivamente da fatia deste work item: para cada decisão vinculada, seu identificador local, o estado do item e o conteúdo que entra no bloco. Ordenado antes de combinar, para não depender da ordem de resposta.

Não depende de: itens de outros work items, itens sem vínculo, contador de revisão do backlog, relógio, caminho absoluto.

## Divergência

Resultado da comparação entre registro e fatia de autoridade.

| Tipo | Significado |
|---|---|
| `MISSING-IN-PROJECTION` | a autoridade tem a decisão, o registro não |
| `MISSING-IN-AUTHORITY` | o registro tem a decisão, a autoridade não |
| `STATE-DIVERGED` | ambos têm, com estados diferentes |
| `CONTENT-DIVERGED` | ambos têm com o mesmo estado, mas o bloco difere |
| `MARK-ABSENT` | o registro não carrega marca de origem |
| `MARK-DIVERGED` | a marca gravada não corresponde à fatia atual |

Cada divergência nomeia a decisão envolvida. Nenhuma é reparada pela verificação; reparar é regenerar.
