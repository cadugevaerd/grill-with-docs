<!-- grill-with-docs-constitution:v1 -->
<!--
Sync Impact Report
Version change: 2.1.0 -> 2.2.0 (MINOR: nova cláusula normativa)
Modified principles: nenhuma. Nenhuma cláusula existente foi renomeada,
  redefinida ou removida.
Added sections: "Versão resolvida, nunca embutida", sob Core Principles.
Removed sections: nenhuma
Rationale: a introdução da versão v4 do workflow gerenciado deixou para trás
  três pontos que continuaram decidindo pela versão anterior, e nenhum deles
  falhou de forma visível. O carimbo de versão no registro de estado e a
  asserção correspondente da auditoria compartilhavam o mesmo literal "v2",
  então concordavam sempre e só reprovavam quem registrasse o valor verdadeiro.
  O asset de estado congelava a versão ativa, fazendo todo bundle declarar v4
  mesmo sobre documento v3. E o gate de elegibilidade da camada executável
  chamava a implementação v3 sobre documento v4, tornando essa camada
  inalcançável para qualquer consumidor já migrado, enquanto a implementação v4
  correta existia e nunca era chamada. Os três são a mesma falha: decisão por
  versão resolvida contra literal em vez de contra a declaração do artefato. A
  cláusula fixa a regra que teria reprovado os três na introdução da versão, e
  exige que a introdução de uma versão nova enumere e prove cada ponto de
  despacho. É acréscimo, não redefinição, logo MINOR.
Deferred: propagar a cláusula para assets/GRILL-CONSTITUTION.template.md NÃO
  foi feito aqui. A regra é genérica e serviria a qualquer projeto consumidor
  com contrato versionado, mas propagá-la altera o bundle publicado, exige bump
  do plugin e muda o hash da Constituição de toda a frota consumidora, com o
  CONSTITUTION-STALE correspondente em cada repositório. É decisão própria, com
  work item próprio, e não efeito colateral desta emenda.
Follow-up: work items existentes selam o hash 2.1.0 e passam a acusar
  CONSTITUTION-STALE. Diferente da emenda anterior, esta ocorre com um work item
  no meio do ciclo — fix-audit-workflow-version-5ff06e6e523c485dbfdcd28d0f5b0538,
  com implement-parallel pendente — logo a re-selagem dele é ato observável e
  necessário, não no-op.
-->
# Grill Constitution

- version: 2.2.0
- ratified: 2026-08-11
- last-amended: 2026-08-23
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

### Versão resolvida, nunca embutida
Toda decisão que dependa da versão de um contrato gerenciado — sequência de etapas, gate de elegibilidade, registro de estado, asset versionado — MUST resolver a versão a partir da declaração do próprio artefato, ou de tabela versionada indexada por versão. Comparar contra literal de versão embutido no código MUST ser tratado como defeito, nunca como validação.

Todo campo que descreve um artefato versionado MUST ser derivado desse artefato no momento da escrita. Literal congelado em código ou em asset MUST NOT servir como valor final de tal campo. Um par writer/reader que compartilha o mesmo literal concorda consigo mesmo em todo caminho default e portanto não verifica nada: reprova apenas quem registra o valor verdadeiro, que é o inverso do que um gate existe para fazer.

Introduzir uma versão gerenciada nova MUST enumerar, no work item que a introduz, todos os pontos do código que despacham por versão, e cada ponto MUST provar que resolve a versão em vez de assumi-la. Ponto de despacho não enumerado MUST bloquear a introdução da versão. Manter o caminho da versão anterior como default silencioso MUST NOT ocorrer: a versão anterior continua atendida por entrada própria na tabela versionada, nunca por fallback.

### Bump obrigatório do plugin
Toda alteração em `plugin/**` MUST incrementar a versão SemVer antes de merge ou push. A versão MUST permanecer idêntica nos manifests, marketplaces, documentação de distribuição e validador; o gate de bump MUST executar tanto na PR quanto antes da tag de publicação. Nunca reutilize uma tag publicada nem edite um marketplace para contornar um bump ausente.

### Release obrigatória por versão
Toda versão publicada MUST ter release correspondente no repositório canônico, ancorada exatamente no mesmo commit da tag imutável daquela versão. A release MUST ser criada pelo pipeline no merge para `main`, no mesmo fluxo que cria a tag: tag sem release é publicação incompleta. Criar release à mão para cobrir uma publicação que o pipeline não fez MUST ser tratado como contorno, não como conformidade. A cláusula vale das versões novas em diante; releases ausentes de versões anteriores a esta emenda são dívida declarada e rastreável, nunca waiver.

## Governance

Esta Constituição é autoridade normativa do projeto. Alterações exigem versão SemVer, data ISO, evidência, revisão e registro no work item. Hooks são somente leitura. A Constituição preexistente humana ou gerenciada é preservada byte a byte e continua autoridade.
