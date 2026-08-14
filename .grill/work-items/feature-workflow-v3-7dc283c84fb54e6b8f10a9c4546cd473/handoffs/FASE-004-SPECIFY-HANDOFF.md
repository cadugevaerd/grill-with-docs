# FASE-004 — Atestação cooperativa e wiring V3

- phase: FASE-004
- state: blocked
- roadmap: ROADMAP.md#FASE-004
- context-refs: Execution Attestation, Canonical Skill, Skill Resolution, Work Item V3
- ADRs: ADR-0002, ADR-0003, ADR-0004
- BLs: BL-0001, BL-0002

## WHAT
- delivery-units: DU-004
- development-type: platform-devops

Resultado observável: um output de etapa só é aceito quando uma cadeia cooperativa correlaciona a skill canônica ao work item, run, geração e plano atuais. O coordenador pode delegar a composição e revisão do receipt a subagente. Um output direto, incompleto, repetido, divergente ou terminado com falha não avança o fluxo.

Critérios de aceite: a cadeia de resolução, despacho, início, término e output é correlacionada antes da transição; retries preservam terminais anteriores e ganham identidade nova; verify, review e ship diretos são recusados; interfaces públicas preservam diagnósticos estáveis em V2 e V3; falhas internas ainda geram uma resposta estruturada. O receipt é evidência estrutural, não prova criptográfica contra executor malicioso.

## WHY
Um relatório, diff ou teste verde isolado não prova que a etapa obrigatória foi executada pelo processo autorizado. A atestação transforma a regra de "usar a skill" em evidência verificável, inclusive sob replay e adulteração.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.
