# FASE-002 — Migração explícita para Workflow V3

- phase: FASE-002
- state: complete
- roadmap: ROADMAP.md#FASE-002
- context-refs: Managed Workflow, Workflow V2, Workflow V3, Skill Resolution
- ADRs: ADR-0001
- BLs: none

## WHAT
- delivery-units: DU-002
- development-type: platform-devops

Resultado observável: um operador de projeto com Workflow V2 consegue inspecionar uma proposta V3, aprová-la pela identidade que inspecionou e continuar usando o projeto após a adoção. Projeto V2 válido continua reconhecido e não é alterado por inspeção ou por tentativa não autorizada.

Critérios de aceite: preview não muda o projeto; apply exige a identidade prévia; repetição idêntica não cria mudança; documento humano equivalente não é sobrescrito; documento V3 com referência ausente, incompleta ou divergente é bloqueado; a projeção de status continua somente leitura.

## WHY
V3 adiciona governança de capacidade, mas a adoção não pode transformar uma verificação em alteração implícita de projetos existentes. A compatibilidade V2 reduz risco operacional durante a transição e conserva um caminho de recuperação legível.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.
