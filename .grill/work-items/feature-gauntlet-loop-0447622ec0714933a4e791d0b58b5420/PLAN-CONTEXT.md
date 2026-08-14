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
- ADRs: ADR-0001, ADR-0004, ADR-0005, ADR-0007
- BLs: none
- delivery-units: DU-003
- development-type: platform-devops

### HOW
A Canonical Skill `tasks` produz um Execution DAG versionado com nós, dependências, escopo, artefatos esperados e tier mínimo. O scheduler valida essa estrutura e somente coloca em wave nós sem dependências pendentes; cada macroetapa recebe seu subagente líder e `agent-execute` pode ocupar até cinco Worker Worktrees simultâneos. As onze macroetapas V3 permanecem ordenadas e não são extensíveis nesta primeira versão.

O adapter Claude usa a interface nativa não interativa com modelo selecionável e saída estruturada em stream, iniciado no worktree do worker e sem shell implícito. O watchdog trata ausência de progresso por quinze minutos: substitui uma vez o worker ou relança uma vez o Loop no mesmo run; recorrência bloqueia com diagnóstico. Somente timeout ou limite temporário classificado recebe retry automático; retomada fora desse caso exige validação explícita do estado persistido.

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
