# SGD-24 — Reutilização legítima de escopo reconciliado

O reconciliador deve distinguir sobreposição concorrente de reutilização sequencial explicitamente declarada. Um work item não pode ser impedido de declarar seu escopo real apenas porque um trabalho já concluído e reconciliado tocou o mesmo caminho.

O comportamento fail-closed permanece obrigatório: sobreposição sem relação de sucessão comprovável continua `SCOPE-OVERLAP`; dependência ausente, não reconciliada, autocíclica ou cíclica continua bloqueada; conflitos ADR continuam independentes. O plano deve decidir e testar se somente dependência direta ou também dependência transitiva constitui sucessão autorizada.
