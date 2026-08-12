# Agent assignment — FASE-001

## Decisão de paralelismo

Sequencial, dono único. T-001 a T-004 são o mesmo arquivo e a mesma função; T-005 depende do contrato que T-004 fecha. Distribuir isso produziria escrita concorrente em `grill_workspace.py` sem ganho de tempo.

O paralelismo fica onde rende: um revisor adversarial independente na etapa `review`, com escopo de leitura. Na milestone anterior essa etapa encontrou quatro classes de corrupção silenciosa que a implementação e a auto-revisão tinham deixado passar.

## Escopos

| Dono | Tasks | Arquivos (escrita) |
|---|---|---|
| Sessão primária | T-001, T-002, T-003, T-004 | `plugin/skills/grill-with-docs/scripts/grill_workspace.py` |
| Sessão primária | T-005 | `tests/validate_workspace_contract.py` |
| Sessão primária | T-006 | os oito pontos de versão |
| `reviewer-004` (subagente) | review | nenhum — somente leitura |

Escrita fora do escopo declarado é proibida. Reatribuição é registrada aqui antes da próxima escrita.

## Mandato da revisão

O modo de falha que importa nesta fase é **guarda que deixou de rodar**. A extração do preâmbulo move lock, snapshot global e recusa de symlink para outro lugar; se alguma dessas guardas sair do caminho, nenhum teste existente necessariamente falha — o comportamento só diverge sob concorrência ou ataque.

O segundo é **mutação onde deveria haver recusa**: a virada escrevendo estado num caminho que deveria ter sido barrado.
