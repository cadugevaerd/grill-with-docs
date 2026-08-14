# FASE-001 — Catálogo de skills canônicas

- phase: FASE-001
- state: complete
- roadmap: ROADMAP.md#FASE-001
- context-refs: Managed Workflow, Canonical Skill, Skill Resolution
- ADRs: ADR-0001, ADR-0002
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

Resultado observável: cada etapa obrigatória do ciclo de desenvolvimento aponta para uma única skill canônica no runtime suportado. A resolução informa a identidade da capacidade ou bloqueia antes de executar quando a capacidade não está comprovada, é ambígua, está desatualizada ou não é confiável.

Critérios de aceite: as onze etapas permanecem obrigatórias e ordenadas; cada uma tem identidade exclusiva; somente ship requer autorização humana adicional; o catálogo confiável identifica a capacidade por conteúdo e versão; runtime sem entrypoint comprovado não recebe substituto; não existe modo direto, emulado ou best-effort para cumprir uma etapa exigida.

## WHY
Um agente que aproxima a intenção de uma etapa não produz evidência de que o processo combinado foi seguido. A identidade canônica permite que operadores e auditores distingam uma execução autorizada de uma substituição silenciosa, mesmo que ambas gerem texto semelhante.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.
