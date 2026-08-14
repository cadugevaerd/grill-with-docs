# Grill with Docs

Linguagem compartilhada para o protocolo de planejamento e execução cooperativa de mudanças.

## Language

**Gauntlet Loop**:
O ciclo que orquestra etapas prontas do workflow por meio de agentes cooperativos.
_Avoid_: gauntled, loop manual, executor externo

**Canonical Skill**:
A skill registrada e autorizada para executar uma etapa específica do workflow.
_Avoid_: substituto direto, emulação semântica, tarefa equivalente

**Model Tier**:
A classe de capacidade atribuída a uma execução de Canonical Skill.
_Avoid_: nome comercial de modelo, modelo implícito, downgrade silencioso

**Autonomous Run**:
Um Gauntlet Run que avança pelas etapas permitidas sem confirmação humana intermediária.
_Avoid_: ship autônomo, execução sem limites, aprovação implícita

**Worker Worktree**:
O worktree Git isolado atribuído exclusivamente a um worker para executar um nó independente.
_Avoid_: escrita concorrente no worktree do coordenador, branch compartilhada entre workers

**Execution DAG**:
O grafo versionado que declara o trabalho executável e suas dependências.
_Avoid_: dependência inferida pelo modelo, paralelismo implícito, ordem textual ambígua

**Resumable Run**:
Um Gauntlet Run cujo progresso e evidências persistem para recuperação validada.
_Avoid_: retomada cega, estado apenas em memória

**Stall Recovery**:
A recuperação limitada de uma run que deixa de demonstrar progresso.
_Avoid_: timeout silencioso, tentativas ilimitadas, descarte do diagnóstico

**Capability Grant**:
A permissão mínima declarada que um nó do Execution DAG concede ao seu worker.
_Avoid_: capacidade implícita, acesso de orquestrador pelo worker, rede liberada por padrão

**Evidence Boundary**:
A fronteira local em que o coordenador valida o resultado observado e registra a evidência de uma Canonical Skill.
_Avoid_: receipt autoafirmado pelo worker, autoridade externa, evidência sem observação

**Gauntlet Configuration**:
A configuração versionada que governa a execução de um Gauntlet-Enabled Work Item.
_Avoid_: configuração global oculta, ativação implícita, redução do mínimo obrigatório

**Gauntlet-Enabled Work Item**:
Um work item V3 configurado e autorizado a iniciar um Gauntlet Run.
_Avoid_: work item V2 ativado, adapter não verificado, migração silenciosa

**Independent Review**:
A revisão somente leitura feita por um subagente que não planejou nem executou a mudança avaliada.
_Avoid_: autoaprovação, reviewer com escrita, review pelo executor

**Integration Conflict**:
O bloqueio nomeado quando mudanças de workers não convergem sem conflito ou sobrepõem escopos declarados.
_Avoid_: resolução automática de conflito, merge silencioso, reescrita implícita do DAG

**Review Block**:
O bloqueio nomeado emitido quando uma Independent Review não aprova a mudança.
_Avoid_: reparo automático fora do workflow, reprovação ignorada, ship sem review aprovado

## Relationships

- Um **Gauntlet Loop** invoca uma **Canonical Skill** para cada etapa pronta.
- Um **Execution DAG** determina quais workers podem executar em paralelo.
- Cada worker opera em um **Worker Worktree** e recebe somente o **Capability Grant** do nó.
- A **Evidence Boundary** do coordenador registra a evidência observada; workers não a emitem.
- Um **Autonomous Run** preserva o gate humano antes de `ship`.
- Um **Resumable Run** usa **Stall Recovery** para recuperar ausência de progresso e preserva bloqueios rastreáveis.
- Uma **Independent Review** é necessária antes da autorização humana de `ship`.
- Uma reprovação de **Independent Review** produz um **Review Block**.
- Somente um **Gauntlet-Enabled Work Item** inicia um **Gauntlet Run**.

## Example dialogue

> **Dev:** "Os dois nós podem executar juntos?"
> **Domain expert:** "Sim, se o **Execution DAG** não declara dependência entre eles; cada worker usa seu próprio **Worker Worktree**."

## Flagged ambiguities

- "gauntled" foi normalizado para **Gauntlet Loop**.
