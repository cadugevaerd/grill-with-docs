# PLAN-CONTEXT

## FASE-001 — Ativação explícita e contrato de configuração
- phase: FASE-001
- ADRs: ADR-0001, ADR-0004, ADR-0007
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
O comando de Gauntlet será opt-in: inicialização valida Workflow V3, a identidade do catálogo e o adapter Claude Code antes de criar a configuração do projeto; execução não cria nem infere essa configuração. Work items V2 continuam no fluxo manual, e runtimes sem todos os entrypoints canônicos comprovados, como Codex e Hermes no catálogo atual, bloqueiam com diagnóstico em vez de receber fallback.

A configuração declara o limite de cinco workers, o limite de stall de quinze minutos e o mapeamento do Model Tier abstrato para o adapter. A política fixa pequeno para checklist e atualização Markdown, médio para tasks, agent-execute, converge e verify, e grande para specify, plan, analyze, agent-assign, review e ship. Ela permite apenas promoção registrada antes do dispatch.

## FASE-002 — Estado durável, evidência e isolamento
- phase: FASE-002
- ADRs: ADR-0003, ADR-0005, ADR-0006, ADR-0010
- BLs: none
- delivery-units: DU-002
- development-type: platform-devops

### HOW
O Project Store atual já fornece CAS, lock global, snapshots e journal encadeado em `events.jsonl`; a feature estende a representação validada de cada work item e usa o journal existente para eventos de run, sem criar banco, arquivo de estado concorrente ou autoridade externa. Cada transição relevante precisa vincular run, wave, worker, lease, input, saída e receipt ao mesmo work item e à mesma revisão-base.

O coordenador é a única Evidence Boundary: workers não recebem acesso ao Store, às leases nem aos receipts. Cada nó recebe um worktree e branch filhos, originados do commit-base declarado, e só comandos e capacidades aprovados. Worktrees limpos e convergidos podem ser removidos; qualquer falha, conflito ou bloqueio preserva os artefatos até limpeza explícita e validada.

## FASE-003 — Scheduler Claude e waves do DAG
- phase: FASE-003
- ADRs: ADR-0001, ADR-0004, ADR-0005, ADR-0007, ADR-0012, ADR-0013, ADR-0014, ADR-0015, ADR-0016, ADR-0017, ADR-0018, ADR-0019
- BLs: BL-0001, BL-0002, BL-0003
- delivery-units: DU-003
- development-type: platform-devops

### HOW
A Canonical Skill `tasks` produz um Execution DAG versionado com nós, dependências, escopo, artefatos esperados e tier mínimo — a FASE-003 não escreve um gerador de DAG separado; ela despacha a própria macroetapa `tasks` a um subagente líder e consome o DAG que essa macroetapa produz como saída (ADR-0014). Antes de qualquer despacho de `agent-execute`, o DAG é validado e qualquer nó cujo `files` bata com uma de duas regras de path é rejeitado fail-closed junto com o resto do DAG, sem novo campo de schema (ADR-0018): (i) um segmento `.specify/reports/` em qualquer profundidade (evidência de verify/review/ship); (ii) um segmento `.grill` em qualquer profundidade — a árvore de controle inteira do grill, não uma lista fechada de basenames (uma lista de três nomes deixava `state.json` de fora, onde vive a própria cadeia de atestação; achado da rodada 8) (`tasks.md` da FASE-002 já produziu um nó assim, T019/T020 de 012 batendo (i) e T019 de 011 batendo (ii); a suposição de que todo nó pertence a `agent-execute` não pode ficar implícita). O scheduler só coloca em wave nós `parallel:true` sem dependências pendentes; cada uma das onze macroetapas V3 recebe seu próprio subagente líder, despachado em sequência fixa e nunca em paralelo com outra macroetapa — sem exceção: `agent-execute` também tem um líder próprio, que por sua vez roda o laço de wave internamente (despacha os workers do DAG, observa progresso, remedia stall/retry) antes de submeter seu próprio checkpoint pela mesma cadeia de atestação das outras dez, porque o formato de atestação existente modela uma invocação por bundle e não teria como representar N workers agregados (ADR-0016). Uma macroetapa cujo checkpoint grava `blocked` (em vez de `complete`) trava a run ali — `current_step` só avança além de um passo `complete`, nunca de um `blocked` — e nenhuma macroetapa seguinte é despachada até resolução manual.

O cap de 1 a 5 workers fixado na ativação é concorrente, não cumulativo: um worker terminal libera seu slot e um worker de substituição por stall ou um retry de falha transitória contam contra esse mesmo cap (ADR-0012), o que exige estender a contagem do Store para ignorar workers terminais. O Store também ganha um ciclo de vida real de wave — estados além do `DECLARED` congelado e a regra de que só a wave superada é imutável, nunca o mapa inteiro (ADR-0013) — para que uma run com mais de cinco nós independentes avance por waves sucessivas.

A invocação real de qualquer subagente é sempre ação de quem detém a autoridade de despacho corrente, nunca do core determinístico (stdlib-only, não invoca subprocesso nem subagente; só grava lease/grant/checkpoint) — para dez macroetapas essa autoridade é a sessão orquestradora externa; para `agent-execute`, é o próprio líder despachado daquela macroetapa, durante sua janela ativa (ADR-0017). Essa delegação é normativa e escopada (ADR-0019): o líder herda exatamente a autoridade coordinator-only de mintar lease/grant, gravar progresso e gravar remediação pros workers que ele próprio despacha; ele nunca vira um worker, nunca conta contra o cap concorrente do run, nunca detém grant escopado a `files` de outro nó, e sua autoridade termina no instante em que seu próprio checkpoint é aceito — não sobrevive além disso, e não amplia em nada o que ADR-0006/ADR-0010 já negam a um worker comum. Essa mesma autoridade corrente grava, via uma primitiva coordinator-only nova do core, cada transição de progresso periódica correlacionada à lease do worker enquanto ele roda — nunca o próprio worker se autorreportando — e cada gravação de progresso renova o TTL da lease pela mesma duração fixa da concessão original, então um worker `large`-tier genuinamente produtivo além de uma hora não perde a lease por decurso de tempo. Cada nó do DAG tem exatamente um orçamento de remediação automática pra sua vida inteira na run, compartilhado entre stall (User Story 3) e retry transiente (User Story 4) — não um orçamento por mecanismo, senão um nó poderia alternar entre os dois indefinidamente. O watchdog trata ausência de progresso por quinze minutos substituindo o worker exatamente uma vez, gastando esse orçamento único do nó — nunca o orçamento de resume manual em nível de run já existente na FASE-002 (ADR-0015); "relançar o Loop" nunca é uma ação automática desta fase, permanece exclusivo do resume manual da FASE-002. Toda lease de worker de remediação (substituição por stall ou retry transiente) já nasce com o orçamento gasto, então qualquer falha seguinte no mesmo nó — de qualquer um dos dois mecanismos — bloqueia com diagnóstico em vez de remediar de novo.

## FASE-004 — Convergência, revisão e entrega verificável
- phase: FASE-004
- ADRs: ADR-0002, ADR-0008, ADR-0009, ADR-0011
- BLs: none
- delivery-units: DU-004
- development-type: platform-devops

### HOW
`converge` integra em série apenas alterações limpas e validadas. Sobreposição de escopo ou conflito Git produz `INTEGRATION_CONFLICT`, identifica os nós envolvidos e não recebe auto-merge nem reescrita do DAG. Status compactos de macroetapa, wave, bloqueio e recovery são entregues ao chat principal; logs contínuos e raciocínio de workers não são expostos.

`review` roda em subagente grande, novo e somente leitura, distinto de quem planejou ou executou, e confronta especificação, plano, DAG, diffs e receipts. Reprovação produz `REVIEW_BLOCKED`; não há ciclo automático de reparo nesta versão. Depois de review aprovado, ship aguarda autorização humana explícita para despachar a Canonical Skill, nunca para executar push ou release diretamente. Os contratos novos devem incluir regressões de isolamento, DAG, lease, stall, receipt, convergência, compatibilidade V2 e adapter não comprovado; a distribuição sobe para 2.6.0 conforme a regra constitucional.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
