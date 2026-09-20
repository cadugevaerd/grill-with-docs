# DECISION-BACKLOG

## BL-0001 — Comparar na retomada os digests reais de WORKFLOW.md e da Constituição
- phase: FASE-001
- state: resolved
- owner: Carlos Araújo
- resolution: adiado por decisão explícita em R-0002. Esta fase só renomeia os campos do checkpoint para o que eles carregam (ADR-0002), sem mudar comportamento. Passar a comparar os digests reais acrescenta recusa nova na retomada e é mudança de contrato: exige ciclo próprio.
- evidence: checkpoint `cp-switch-b9ab5c9b4e73616f5adb2737` do T029, com `workflow_sha256 = e0a30cb8…` (inputs do contexto) e `constitution_sha256 = 4786e719…` (metadata de origem), contra `d2c4ea08…` do WORKFLOW e `54d5522b…` da Constituição
- trigger: primeira retomada em que a autoridade normativa (WORKFLOW ou Constituição) mudou entre a troca e a retomada

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
