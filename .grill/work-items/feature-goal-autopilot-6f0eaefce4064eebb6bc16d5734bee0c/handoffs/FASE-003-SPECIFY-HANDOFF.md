# FASE-003 — Validador e distribuição

- phase: FASE-003
- state: superseded
- roadmap: ROADMAP.md#FASE-003
- context-refs: goal.md
- ADRs: ADR-0003, ADR-0008
- BLs: none

## WHAT
- delivery-units: DU-003
- development-type: documentation

O contrato do documento passa a ser travado por teste na suíte canônica do
repositório, e a versão publicada do plugin reflete a mudança em todos os
lugares em que a distribuição a exige.

Critérios de aceite: a suíte reprova qualquer quebra do contrato do documento;
o teste roda sem rede e sem exigir ferramenta externa instalada; a versão fica
idêntica em todos os pontos travados; o gate de versão aprova.

Escopo excluído: o texto normativo e a materialização.

## WHY

Um contrato sem teste é convenção. A suíte é o que impede que uma edição
posterior remova silenciosamente uma garantia que consumidores já dependem, e o
gate de versão é o que impede que a mudança chegue ao público sem identidade
nova. Ambas as exigências são normativas no projeto, não preferência.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
