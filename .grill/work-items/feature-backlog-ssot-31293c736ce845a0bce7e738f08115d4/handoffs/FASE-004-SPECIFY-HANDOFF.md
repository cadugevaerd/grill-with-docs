# FASE-004 — Migração de bundles legados

- phase: FASE-004
- state: complete
- roadmap: ROADMAP.md#FASE-004
- context-refs: Projeção, Item de backlog, Evidência no commit
- ADRs: ADR-0003
- BLs: none

## WHY
Os work items já existentes têm o registro de decisões adiadas escrito à mão. Quando o modelo novo entrar, esses registros ficam órfãos: referenciados nos artefatos de plano, mas sem contraparte na autoridade. Sem caminho de migração, conviveriam dois formatos para sempre.

Migração automática e silenciosa está fora de questão. Migrar cria itens no backlog do operador, e o contrato do plugin que o governa exige confirmação explícita para qualquer mutação. Há precedente no próprio projeto: um estado global legado bloqueia em vez de migrar sozinho, porque não existe migração implícita.

O bloqueio precisa ser fail-closed sem cegar o diagnóstico. Se todo comando recusar, o operador perde justamente a ferramenta que diria o que precisa ser migrado.

Os registros históricos são quase todos terminais. Criar item para eles gera ruído no backlog operacional, mas preserva sem exceção a invariante de que toda referência aponta para um item — e é essa ausência de exceção que mantém o gate simples, em vez de exigir uma regra permanente para históricos.

## WHAT
- delivery-units: DU-004
- development-type: backend

Um work item no formato antigo migra uma única vez para o modelo derivado, sob confirmação explícita.

Resultado observável: o formato do work item é detectável; a migração mostra prévia e só altera algo sob confirmação; reexecutar não duplica nem altera nada; registros históricos preservam o estado que tinham; comandos de leitura continuam funcionando e apontam a pendência como impedimento; comandos que alteram recusam enquanto a migração não ocorrer.

Atores: o operador que atualiza um repositório existente, e o operador de um repositório novo, que nunca deve ver esse caminho.

Cenários que precisam passar:
- work item no formato antigo, migrado com confirmação;
- mesmo work item migrado de novo, sem efeito;
- work item já no formato novo, intocado;
- registro histórico encerrado, que precisa chegar encerrado;
- registro que já tem contraparte, que não pode ganhar uma segunda;
- comando de leitura sobre work item não migrado, que precisa concluir e reportar;
- comando que altera sobre work item não migrado, que precisa recusar.

Escopo excluído: preenchimento manual e alteração de itens preexistentes na autoridade.

Critérios de aceite: migração idempotente sob confirmação; estados históricos preservados; leitura reporta e alteração recusa.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
