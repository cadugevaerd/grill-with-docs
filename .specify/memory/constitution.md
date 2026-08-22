<!-- grill-with-docs-constitution:v1 -->
<!--
Sync Impact Report
Version change: 2.0.0 -> 2.1.0 (MINOR: nova cláusula normativa)
Modified principles: nenhuma. Nenhuma cláusula existente foi renomeada,
  redefinida ou removida.
Added sections: "Tier de modelo e esforço do worker Orca", sob Core Principles.
Removed sections: nenhuma
Rationale: os workers despachados via Orca Orchestration vinham sem par
  modelo/esforço declarado, então o runtime escolhia por default. Trabalho de
  leitura consumia tier forte e migração de esquema podia cair em tier
  econômico, sem nada no retorno que denunciasse a divergência. A cláusula
  fixa a correspondência entre natureza do trabalho e tier, exige a declaração
  explícita no worker-start e exige a conferência de launch.effective, que é o
  único ponto onde o efetivo aparece. É acréscimo, não redefinição, logo MINOR.
Deferred: nenhum. A cláusula é governança operacional e não depende de código
  novo neste repositório. Orca é ferramenta de orquestração local do operador,
  não faz parte do bundle publicado, logo a cláusula vive apenas na Constituição
  viva e NÃO entra em assets/GRILL-CONSTITUTION.template.md.
Follow-up: work items existentes selam o hash 2.0.0 e passam a acusar
  CONSTITUTION-STALE; os oito work items vivos neste repositório estão com os
  onze passos complete, logo nenhum executa outro checkpoint e a re-selagem é
  no-op observável.
-->
# Grill Constitution

- version: 2.1.0
- ratified: 2026-08-11
- last-amended: 2026-08-22
- governance: Grill lifecycle governance; changes require review, evidence, and work-item traceability.

## Core Principles

### Evidência antes de afirmação
Toda afirmação verificável MUST ser acompanhada de evidência legível e rastreável.

### Work item isolado e ownership
Cada feature, fix ou hotfix MUST possuir work item isolado, identidade imutável e ownership explícito.

### Feature/fix plan-only
Feature e fix terminam em PLAN_ONLY_STOP; nenhum plano autoriza alteração ou publicação.

### Sequência obrigatória do desenvolvimento
O desenvolvimento MUST seguir, sem saltos: specify, plan, checklist, tasks, analyze, partition, implement-parallel, converge, verify, review, ship.

### Verify/review antes de ship
Ship somente pode iniciar após verify e review completos, com evidências.

### Fail-closed sem waiver
Ambiguidade, corrupção, ausência de evidência ou violação MUST bloquear; não existe waiver implícito.

### Rastreabilidade
Decisões, mudanças, fases, módulos, DUs, receipts e gates MUST ser rastreáveis ao work item e ao commit.

### Tier de modelo e esforço do worker Orca
Todo worker criado via Orca Orchestration MUST declarar `--model` no `worker-start` e, quando o runtime suportar, também `--effort`. O tier MUST corresponder à natureza do trabalho: pesquisa, triagem, leitura de código e testes usam modelo econômico com esforço baixo; implementação delimitada usa modelo intermediário; arquitetura, segurança, migração, resposta a incidente e revisão final usam modelo forte com esforço alto. O retorno JSON do `worker-start` MUST ser conferido: `launch.effective` MUST corresponder ao par modelo/esforço solicitado, e divergência MUST bloquear o despacho em vez de prosseguir sob o efetivo. Reutilizar um `--terminal` existente MUST NOT ocorrer quando modelo ou esforço precisam ser definidos, porque essas preferências só se aplicam a terminais novos.

### Bump obrigatório do plugin
Toda alteração em `plugin/**` MUST incrementar a versão SemVer antes de merge ou push. A versão MUST permanecer idêntica nos manifests, marketplaces, documentação de distribuição e validador; o gate de bump MUST executar tanto na PR quanto antes da tag de publicação. Nunca reutilize uma tag publicada nem edite um marketplace para contornar um bump ausente.

### Release obrigatória por versão
Toda versão publicada MUST ter release correspondente no repositório canônico, ancorada exatamente no mesmo commit da tag imutável daquela versão. A release MUST ser criada pelo pipeline no merge para `main`, no mesmo fluxo que cria a tag: tag sem release é publicação incompleta. Criar release à mão para cobrir uma publicação que o pipeline não fez MUST ser tratado como contorno, não como conformidade. A cláusula vale das versões novas em diante; releases ausentes de versões anteriores a esta emenda são dívida declarada e rastreável, nunca waiver.

## Governance

Esta Constituição é autoridade normativa do projeto. Alterações exigem versão SemVer, data ISO, evidência, revisão e registro no work item. Hooks são somente leitura. A Constituição preexistente humana ou gerenciada é preservada byte a byte e continua autoridade.
