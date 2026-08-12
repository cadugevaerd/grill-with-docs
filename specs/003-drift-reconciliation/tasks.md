# Tasks — FASE-003

Ordem é dependência real, não preferência.

## T-001 — `verify_release` no publicador
**Arquivo**: `tests/publish_to_marketplace.py`
**Depende de**: nada

Função pura sobre índice carregado e `Release`. Retorna veredito e lista de divergências nomeadas. Reprova: entrada ausente, entrada duplicada, `version` divergente, `source` não-objeto, qualquer um dos cinco campos do pin divergente. Não compara campos curados.

**Pronto quando**: a função existe, é importável pela suíte e não faz I/O.

## T-002 — `--verify` na CLI
**Arquivo**: `tests/publish_to_marketplace.py`
**Depende de**: T-001

Nova flag, recusada junto com `--apply`. Payload com `verdict` `VERIFIED`/`MISMATCH` e as divergências. Código de saída `3` na divergência, distinto de `1` e `2`.

**Pronto quando**: as três saídas são distinguíveis por código.

## T-003 — Testes de contrato
**Arquivo**: `tests/validate_publish_contract.py`
**Depende de**: T-002

Cobre CHK-001 a CHK-010, incluindo o ciclo aplicar-depois-verificar sobre o mesmo checkout.

**Pronto quando**: a suíte inteira passa e a contagem sobe em relação às 270 atuais.

## T-004 — Passo de releitura no workflow
**Arquivo**: `.github/workflows/publish.yml`
**Depende de**: T-002

Depois do push: clone raso novo do destino, `--verify` contra ele, e assert de que a tag resolve no canônico para o commit publicado. Reusa o cabeçalho mascarado; não introduz segredo novo.

**Pronto quando**: o YAML parseia, o shell tem sintaxe válida e a ordem dos passos é push → releitura.

## T-005 — Prova local contra clones reais
**Depende de**: T-003, T-004

Clonar os dois destinos, rodar o ciclo completo `--apply` → `--verify` em cada um, e confirmar: claude atualiza, codex cria, releitura aprova, segunda passada não muda nada. Nada é empurrado.

**Pronto quando**: os dois destinos aprovam localmente e o diff é do tamanho esperado.

## T-006 — Reconciliação documental
**Arquivos**: ROADMAP, handoff, ADR, DECISION-BACKLOG
**Depende de**: T-005

Corrigir `2.4.0` → `2.4.1` no ROADMAP; registrar que os critérios de aceite do handoff vinham do modelo espelhado e o que os substitui; ADR da releitura obrigatória.

## T-007 — Execução real
**Depende de**: segredo instalado (**ato humano**)

Disparo manual, leitura do resultado nos dois destinos, segundo disparo para provar idempotência.
