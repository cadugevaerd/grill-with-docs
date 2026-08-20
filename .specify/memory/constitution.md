<!-- grill-with-docs-constitution:v1 -->
<!--
Sync Impact Report
Version change: 1.1.0 -> 1.2.0 (MINOR: nova cláusula normativa)
Modified principles: nenhuma renomeada ou redefinida
Added sections: "Release obrigatória por versão"
Removed sections: nenhuma
Rationale: a disciplina de publicação estava pela metade. "Bump obrigatório do plugin"
  já exigia incremento de versão e tag imutável, mas nada exigia a release
  correspondente. O resultado observável: só existe a release v2.4.1 (2026-08-10),
  enquanto as tags seguiram até v3.3.2 -- o pipeline cria a tag e para aí.
Deferred: automatizar a criação da release em .github/workflows/publish.yml é
  implementação e sai por /speckit-specify, não por esta emenda.
Follow-up: work items existentes selam o hash da versão anterior e passam a acusar
  CONSTITUTION-STALE; re-selagem é ato deliberado por work item.
-->
# Grill Constitution

- version: 1.2.0
- ratified: 2026-08-11
- last-amended: 2026-08-20
- governance: Grill lifecycle governance; changes require review, evidence, and work-item traceability.

## Core Principles

### Evidência antes de afirmação
Toda afirmação verificável MUST ser acompanhada de evidência legível e rastreável.

### Work item isolado e ownership
Cada feature, fix ou hotfix MUST possuir work item isolado, identidade imutável e ownership explícito.

### Feature/fix plan-only
Feature e fix terminam em PLAN_ONLY_STOP; nenhum plano autoriza alteração ou publicação.

### Sequência obrigatória do desenvolvimento
O desenvolvimento MUST seguir, sem saltos: specify, plan, checklist, tasks, analyze, agent-assign, agent-execute, converge, verify, review, ship.

### Verify/review antes de ship
Ship somente pode iniciar após verify e review completos, com evidências.

### Fail-closed sem waiver
Ambiguidade, corrupção, ausência de evidência ou violação MUST bloquear; não existe waiver implícito.

### Rastreabilidade
Decisões, mudanças, fases, módulos, DUs, receipts e gates MUST ser rastreáveis ao work item e ao commit.

### Bump obrigatório do plugin
Toda alteração em `plugin/**` MUST incrementar a versão SemVer antes de merge ou push. A versão MUST permanecer idêntica nos manifests, marketplaces, documentação de distribuição e validador; o gate de bump MUST executar tanto na PR quanto antes da tag de publicação. Nunca reutilize uma tag publicada nem edite um marketplace para contornar um bump ausente.

### Release obrigatória por versão
Toda versão publicada MUST ter release correspondente no repositório canônico, ancorada exatamente no mesmo commit da tag imutável daquela versão. A release MUST ser criada pelo pipeline no merge para `main`, no mesmo fluxo que cria a tag: tag sem release é publicação incompleta. Criar release à mão para cobrir uma publicação que o pipeline não fez MUST ser tratado como contorno, não como conformidade. A cláusula vale das versões novas em diante; releases ausentes de versões anteriores a esta emenda são dívida declarada e rastreável, nunca waiver.

## Governance

Esta Constituição é autoridade normativa do projeto. Alterações exigem versão SemVer, data ISO, evidência, revisão e registro no work item. Hooks são somente leitura. A Constituição preexistente humana ou gerenciada é preservada byte a byte e continua autoridade.
