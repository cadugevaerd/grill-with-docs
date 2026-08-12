# Analysis — FASE-001

## Cobertura dos requisitos

| FR | Onde | Task |
|---|---|---|
| FR-001 operação explícita de virada | `phase_turn_command` | T-002 |
| FR-002 razão obrigatória, registrada | `REASON-REQUIRED` + entrada na trilha | T-002 |
| FR-003 recusa com fase incompleta, sem mutação | `PHASE-INCOMPLETE` antes de qualquer escrita | T-002 |
| FR-004 idempotência | registro todo `pending` devolve `REUSED` | T-002 |
| FR-005 recusa nomeia a virada | `PHASE-TURN-REQUIRED` | T-003 |
| FR-006 sem mudança de forma | nenhuma chave nova em `development` | T-002, T-005 |
| FR-007 trilha reconstrói a fase encerrada | append-only preservado | T-005 |

## Riscos

**R-1 — A extração do preâmbulo toca o caminho mais testado do core.**
`checkpoint_command` carrega lock, guarda de mutação global, recusa de symlink e escrita atômica. Um erro na extração não aparece como falha óbvia: aparece como guarda que deixou de rodar. Mitigação: a extração não altera ordem nem condições, e a suíte cobre concorrência, lock órfão e recibo inválido. Se algum desses testes ficar verde por não exercitar mais o caminho, o defeito passa — por isso T-005 inclui a guarda global e o lock explicitamente, em vez de confiar na cobertura herdada.

**R-2 — Idempotência e recusa se contradizem se implementadas na ordem errada.**
"Recusar quando nem tudo está `complete`" e "não fazer nada quando tudo está `pending`" descrevem o mesmo estado de entrada por caminhos opostos. Checar idempotência antes da recusa é obrigatório; inverter torna FR-004 inalcançável.

**R-3 — `step` fora de `SEQUENCE` na trilha.**
Hoje nenhum leitor itera a trilha: o único acesso é o append. Um leitor futuro que assuma `SEQUENCE` quebra em silêncio. Aceito, com o shape fixado por teste para que a suposição falhe alto.

**R-4 — A virada esquecida devolve o operador ao sintoma de hoje.**
Mitigado por FR-005, mas não eliminado: quem não ler o código de erro continua perdido. É o limite do que dá para consertar sem tornar a virada automática, opção descartada em ADR-0001 por ser mudança de estado implícita.

**R-5 — Distinguir fases pela razão é convenção, não estrutura.**
A trilha não terá campo de fase, então separar as fases depende de quem escreveu a razão ter sido claro. É consequência aceita de FR-006; a alternativa era mudar o schema e migrar bundles.

**R-6 — Bump de versão publica.**
`plugin/` muda, então o merge dispara publicação automática e cria a tag `v2.5.2` no canônico. É comportamento desejado e já provado, mas significa que esta fase produz release pública — não é mudança interna.

## Dependências

- Interna: T-001 → T-002 → T-004 → T-005 → T-006. T-003 é independente e pode entrar em qualquer ponto antes de T-005.
- Externa: nenhuma. Tudo é stdlib, sem rede.
- A projeção global existente não pode ser invalidada; `reconcile` é reexecutado na verificação.

## Fora de escopo

- Campo de fase no estado, e a migração que ele exigiria.
- Virada automática ao marcar a fase `complete` no ROADMAP.
- Re-pino de identidade, que é FASE-002.
- Exposição da trilha na projeção de `status`.
