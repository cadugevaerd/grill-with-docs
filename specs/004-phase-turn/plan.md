# Plan: Virada de fase auditada

**Spec**: `spec.md` · **Branch**: `fix/high-defects` · **ADR**: ADR-0001

## Onde o defeito mora

`checkpoint_command` (`grill_workspace.py:1738`) mantém `development.steps` com os 11 passos por work item. A transição para `in-progress` exige `current in {pending, blocked}` (`:1810`). Depois de um ciclo, todos os passos estão `complete`, então a condição é insatisfazível e a recusa sai como `INVALID-TRANSITION` — um código que descreve o sintoma e esconde a causa.

`development.audit` recebe append por transição (`:1803`) e não é lido por ninguém: `grill_status.py` projeta `steps`, `current_step`, `completed` e `blocked`, nunca `audit`. Isso é o que autoriza reiniciar `steps` sem perder histórico, e é a base de ADR-0001.

## Decisões de desenho

1. **Subcomando próprio, não flag no `checkpoint`.** `--step` e `--state` são `required=True` no parser do checkpoint (`:1912-1913`). Tornar os dois opcionais para acomodar uma virada transformaria um parser estrito num parser condicional, e o custo cairia sobre o caminho quente. A virada é uma operação distinta e ganha subcomando distinto.
2. **A virada reusa o preâmbulo por extração, não por cópia.** Resolução do item, recusa de symlink, guarda de mutação global e lock são idênticos aos do checkpoint. Duplicar 25 linhas de guarda é como as guardas divergem com o tempo; a extração é verificada pelos testes que já cobrem o checkpoint.
3. **Idempotência antes da recusa.** Um registro inteiro em `pending` é o estado que a virada produz. Aplicada de novo, ela devolve `REUSED` sem escrever, em vez de reprovar por "fase incompleta" — senão FR-003 e FR-004 se contradizem.
4. **A recusa por fase encerrada ganha código próprio.** `PHASE-TURN-REQUIRED` em vez de `INVALID-TRANSITION` quando **todos** os passos estão `complete`. O código é a mensagem: o operador lê o remédio, não o sintoma. `INVALID-TRANSITION` continua valendo para transição realmente inválida, como pular um passo.
5. **A trilha distingue fases pela razão, não por campo novo.** Acrescentar um campo de fase às entradas seria mudança de forma, excluída por FR-006. A entrada da virada usa o mesmo shape das demais, com `step` fora de `SEQUENCE`.

## Camadas

| Camada | Onde | Novo |
|---|---|---|
| Preâmbulo compartilhado | `grill_workspace.py`, helper extraído | sim, por extração |
| Decisão da virada | `grill_workspace.py`, `phase_turn_command` | sim |
| Código de recusa nomeada | `grill_workspace.py`, ramo `in-progress` | alterado |
| CLI | `grill_workspace.py`, subparser `phase-turn` | sim |
| Contrato | `tests/validate_workspace_contract.py` | sim |

## Contrato do subcomando

`phase-turn ROOT --work-id ID --reason RAZÃO`

| Estado do registro | Resultado |
|---|---|
| todos `complete` | reinicia, grava na trilha, `verdict: TURNED` |
| todos `pending` | nada muda, `verdict: REUSED` |
| qualquer outro | `PHASE-INCOMPLETE`, nada muda |
| razão vazia | `REASON-REQUIRED`, nada muda |
| `development` ausente ou de outro schema | `LEGACY-UNTRACKED` |

A entrada gravada na trilha tem o shape das demais — `step`, `state`, `evidence`, `reason` — com `step: "phase-turn"` e `state: "turned"`. Nenhum leitor atual itera a trilha esperando membros de `SEQUENCE`; o único acesso é o append em `:1803`.

## Gates

- `python3 tests/run_validators.py` verde. Baseline: 291 testes, exit 0.
- Muda `plugin/`, então o gate de bump exige subir a versão: 2.5.1 → 2.5.2, em oito lugares.
- Nenhum bundle existente pode precisar de migração. O work item já reconciliado tem recibo determinístico; o teste tem de provar que ele continua legível.

## Riscos

- **Extrair o preâmbulo toca o caminho quente do checkpoint.** Mitigado por a suíte já cobrir checkpoint em profundidade, incluindo concorrência e recuperação de lock órfão.
- **A virada esquecida reproduz o sintoma.** Mitigado por FR-005: a recusa nomeia a virada. É a diferença entre travar e travar dizendo o que fazer.
- **`step` fora de `SEQUENCE` na trilha.** Um leitor futuro que assuma `SEQUENCE` quebra. O teste fixa o shape para que a suposição apareça como falha, não como corrupção.
