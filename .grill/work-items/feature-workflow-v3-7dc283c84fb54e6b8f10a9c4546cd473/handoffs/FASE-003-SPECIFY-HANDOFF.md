# FASE-003 — Work Item V3 e Project Store

- phase: FASE-003
- state: complete
- roadmap: ROADMAP.md#FASE-003
- context-refs: Work Item V3, Project Store
- ADRs: ADR-0003
- BLs: none

## WHAT
- delivery-units: DU-003
- development-type: platform-devops

Resultado observável: um operador pode evoluir um work item existente para V3 por preview e aprovação explícita, e worktrees vinculadas observam o mesmo estado íntegro sem perder atualizações concorrentes.

Critérios de aceite: preview não escreve; apply altera somente a identidade prevista; a identidade anterior é preservada; paths inseguros, dados adulterados, conflitos e escrita stale bloqueiam antes de efeito parcial; leitura não cria store; histórico adulterado, cortado ou reordenado é rejeitado.

## WHY
O ciclo V3 precisa distinguir trabalhos e tentativas sem depender do diretório em que o operador está. Uma fonte compartilhada e verificável permite auditoria e concorrência segura, onde cópias locais independentes ocultariam divergência.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.
