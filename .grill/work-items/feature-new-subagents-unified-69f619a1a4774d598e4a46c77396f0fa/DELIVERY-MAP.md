# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Plataforma de orquestração GWD
- module-kind: platform
- responsibility: Coordenar especialistas, continuidade, limpeza e escopo de escrita no workflow GWD.
- boundary: Plugin GWD, seus contratos de execução, skills e validação offline.
- depends-on: none

### DU-001 — Orquestração, continuidade e escopo dos agentes
- development-type: platform-devops
- phase: FASE-001
- scope-in: Oito requisitos de REQUEST.md e decisões R-0001 a R-0010, incluindo fluxo de design para consumidores frontend.
- scope-out: Site e Terraform do relato; construção de uma interface de produto nesta entrevista; transferência de workers ativos entre CLIs.
- depends-on: none
- acceptance: Oito critérios do handoff satisfeitos com evidência, respeitando preservação de trabalho, invocação canônica, governança e distribuição.
