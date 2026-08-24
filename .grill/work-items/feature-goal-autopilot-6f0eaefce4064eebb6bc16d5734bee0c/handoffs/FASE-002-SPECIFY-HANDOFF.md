# FASE-002 — Materialização pelo init

- phase: FASE-002
- state: planned
- roadmap: ROADMAP.md#FASE-002
- context-refs: goal.md, GWD
- ADRs: ADR-0003
- BLs: none

## WHAT
- delivery-units: DU-002
- development-type: documentation

Todo projeto que executa a criação de work item passa a ter o documento fixado
na raiz, sem sobrescrever nada, com identidade versionada própria e hash
registrado no estado do bundle. O retorno da criação passa a reportar o estado
desse documento no mesmo formato em que já reporta o contrato de workflow.

Documento humano preexistente que não case o contrato permanece intacto byte a
byte e é reportado como incompatível, nunca substituído.

Critérios de aceite: criação repetida é idempotente e reporta reuso; documento
divergente é preservado e sinalizado; o hash registrado corresponde aos bytes
materializados.

Escopo excluído: o texto normativo do documento e a validação automatizada.

## WHY

Um documento que só existe no repositório de origem não automatiza projeto
nenhum. A fixação é o que faz o contrato chegar a quem consome, e o hash
registrado é o que permite detectar deriva depois. A garantia de não
sobrescrever existe porque o documento na raiz de um projeto pode ter sido
escrito por uma pessoa.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
