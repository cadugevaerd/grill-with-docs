# Plan: Gate de bump bloqueante

**Spec**: `spec.md` · **ADR**: ADR-0003

## Decisões de desenho

1. **Workflow próprio, sem `paths:`.** É a única forma de o gate escapar do filtro, porque o filtro é do workflow. O `ci.yml` mantém o dele e continua dono da matriz.
2. **Nada de shim.** Um job que reporta sucesso quando o real foi pulado torna aprovado indistinguível de não-executado — a mesma classe de falso verde que a milestone anterior gastou uma fase eliminando na publicação.
3. **Os dois cuidados viajam junto.** `fetch-depth: 0`, porque o clone raso não contém a merge base; e a base vinda de `github.event.pull_request.base.sha`, porque no evento de proposta o checkout é um merge commit efêmero. Perder qualquer um dos dois quebra o gate de formas silenciosas.
4. **O ato humano fica declarado no artefato, não implícito.** Registrar a verificação como obrigatória é configuração do serviço; o código pode ficar pronto e o requisito seguir descumprido.

## Camadas

| Camada | Onde | Novo |
|---|---|---|
| Gate | `.github/workflows/bump-gate.yml` | sim |
| Matriz | `.github/workflows/ci.yml` | job removido |
| Contrato | `tests/validate_bump_gate_contract.py` | estendido |

## Gates

- Suíte verde; baseline 309.
- Não toca `plugin/`: nenhum bump, nenhuma publicação no merge. É a fase que prova o caso negativo.
- A prova de que o gate passa a reportar onde antes calava é observável na própria proposta desta fase, que muda só workflows e testes.

## Riscos

- **Remover o job do `ci.yml` e não recriá-lo corretamente** deixaria o repositório sem gate nenhum, silenciosamente. Mitigado por o contrato executável verificar a existência e a forma dos dois workflows.
- **A guarda de deduplicação do `ci.yml`** foi escrita quando o gate morava lá. Ela é `pull_request` OR `!merge de PR`; o gate novo roda só em `pull_request`, então não é afetado — mas o teste precisa fixar isso.
