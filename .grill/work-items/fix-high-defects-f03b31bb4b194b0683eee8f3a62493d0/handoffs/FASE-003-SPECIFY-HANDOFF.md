# FASE-003 — Gate de bump bloqueante

- phase: FASE-003
- state: complete
- roadmap: ROADMAP.md#FASE-003
- context-refs: Gate de bump, Required status check, Filtro de paths
- ADRs: ADR-0003
- BLs: none

## WHAT
- delivery-units: DU-003
- development-type: platform-devops

Resultado observável: a verificação de versão passa a se pronunciar sobre toda proposta de mudança, de modo que possa ser exigida como condição de integração sem prender propostas que ela não avalia.

Atores: quem propõe mudança, de conteúdo distribuído ou não; quem administra a proteção da linha principal.

Cenários:
- proposta que altera o conteúdo distribuído sem subir a versão — reprovada;
- proposta que altera o conteúdo distribuído com a versão subida — aprovada;
- proposta que não toca o conteúdo distribuído — aprovada por não haver o que exigir, e não por ter sido pulada;
- proposta que hoje não aciona verificação alguma, como a que muda só documentação — passa a receber veredito.

Escopo: fazer a verificação se pronunciar em toda proposta, e comprovar que o veredito vem de execução real nos casos que hoje são pulados.

Fora de escopo: mudar o alcance da bateria de portabilidade; e o ato de exigir a verificação na proteção da linha principal, que é humano e externo.

Critérios de aceite: veredito presente em toda proposta, incluindo as que hoje não acionam verificação; aprovação distinguível de ausência de execução; a bateria de portabilidade continua restrita ao que importa; e fica declarado, para quem administra o repositório, qual verificação precisa ser exigida.

## WHY
A regra diz que reprovar deve impedir a integração. Hoje reprovar apenas mostra vermelho: nada bloqueia. Transformar isso em bloqueio exige exigir a verificação na proteção da linha principal.

Só que exigir uma verificação que às vezes não se pronuncia prende para sempre as propostas em que ela cala — e ela cala justamente nas que não tocam o conteúdo distribuído, que são a maioria das propostas de documentação. Os dois problemas são o mesmo problema visto de dois lados, e resolver um sem o outro troca uma regra frouxa por uma trava.

A saída precisa preservar uma distinção que já custou caro noutro lugar deste projeto: aprovado por ter sido verificado não pode virar indistinguível de aprovado por não ter sido olhado.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
