# Agent assignment — FASE-003

## Decisão de paralelismo

Sequencial, um único executor. T-001 → T-002 → T-003 são o mesmo arquivo e a mesma função; T-004 depende do formato de saída que T-002 define. Distribuir isso entre agentes criaria escritas concorrentes no mesmo arquivo em troca de nenhum ganho de tempo real.

Em FASE-002 o oposto foi tentado e produziu uma colisão: dois agentes reescreveram o mesmo publicador a partir de modelos arquiteturais diferentes, e um deles seguiu trabalhando sobre um escopo que já tinha mudado de dono sem reatribuição registrada. A lição aplicada aqui é escopo por arquivo com dono único e explícito.

## Escopos

| Dono | Tasks | Arquivos (escrita) | Escrita fora do escopo |
|---|---|---|---|
| Sessão primária | T-001, T-002, T-003, T-005 | `tests/publish_to_marketplace.py`, `tests/validate_publish_contract.py` | proibida |
| Sessão primária | T-004 | `.github/workflows/publish.yml` | proibida |
| Sessão primária | T-006 | ROADMAP, handoff, `docs/adr/`, DECISION-BACKLOG do work item | proibida |
| `reviewer-003` (subagente) | review | nenhum — somente leitura | proibida |

## Revisão independente

Um subagente adversarial roda na etapa `review`, com escopo de leitura e mandato de refutar. Em FASE-002 essa etapa encontrou quatro classes de corrupção silenciosa que a implementação e a auto-revisão tinham deixado passar, uma delas capaz de escrever no objeto errado sem erro. O mandato é o mesmo: procurar o caso em que a verificação **aprova** algo que não deveria.

## Regra de handoff

Se um escopo mudar de dono no meio da execução, a reatribuição é registrada aqui antes da próxima escrita. Assumir silenciosamente o arquivo de outro agente deixa o escopo órfão para todos os demais.
