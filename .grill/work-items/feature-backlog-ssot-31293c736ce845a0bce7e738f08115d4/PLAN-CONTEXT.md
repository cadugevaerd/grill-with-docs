# PLAN-CONTEXT

## FASE-001 — Destravar a ponte com o backlog operacional
- phase: FASE-001
- ADRs: ADR-0003
- BLs: none
- delivery-units: DU-001
- development-type: backend

### HOW
Quatro defeitos independentes mantêm a ponte desligada, e três deles caem nesta fase.

O gate de integridade é o bloqueador raiz. `backlog_sync_command` chama `validate_bundle_integrity`, que compara os arquivos vivos contra `initial_artifacts` — os hashes dos templates gravados no `init`. Escrever uma decisão adiada é exatamente o que quebra esse pino, então o subcomando é insatisfazível por construção; `BUNDLE-INTEGRITY` foi reproduzido nos três work items existentes. A troca é por `validate_metadata`: validar adulteração do bloco imutável continua correto, validar hash de artefato que o contrato manda mudar não é. Sem isso nem a migração da FASE-004 consegue escrever.

O filtro `state != "open"` em `backlog_bridge.py:150` é o segundo. Combinado com `audit_decisions.py:615,623`, que reprovam decisão adiada em aberto, ele torna a janela de espelho idêntica à janela bloqueada: para fechar a milestone é preciso resolver tudo, e resolvido o espelho vira no-op permanente. O espelho passa a cobrir qualquer estado.

O mapa de estados segue ADR-0003 e a FSM medida: item nasce em `in_progress`, `resolved` transiciona para `done`, `superseded` para `cancelled`. `open` e `merged` não são usados. `open → done` é ilegal, então o mapa ingênuo do plano original não serve.

O armazenamento aceita duplicata sem erro — verificado, um `item add` repetido criou um segundo item. A deduplicação por `(work_id, BL-NNNN)` é responsabilidade inteira do gerador, lendo os marcadores `grill-work-id` e `grill-bl` da `description`. Esse é o único lugar disponível: o shape documentado de `item add` é `--code --title --description [--status] [--criticality] [--category] [--due-at]`, as flags são command-scoped, e não há campo estruturado de vínculo.

Restrição de ambiente: a matriz de CI não tem `backlogctl`, então todo teste entra pelo seam `resolve_cli`.

## FASE-002 — Projeção versionada e determinística
- phase: FASE-002
- ADRs: ADR-0001, ADR-0002
- BLs: none
- delivery-units: DU-002
- development-type: backend

### HOW
A autoridade de estado é o backlog operacional; a evidência no commit é a projeção versionada. `DECISION-BACKLOG.md` deixa de ser autoral e passa a ser gerado, com o gerador como único escritor.

Determinismo é requisito duro, não estético: a projeção é versionada e o `reconcile` exige que a segunda execução seja byte-idêntica. Ordenação canônica por identificador de decisão e formatação fixa.

O fingerprint da autoridade cobre apenas a fatia deste work item — identificadores, estados, criticality e hash de título dos itens vinculados. O campo `revision` que o `backlog list` devolve por backlog não serve: ele incrementa a cada mudança em qualquer item, inclusive de outros repositórios que compartilham a mesma base, o que produziria drift falso constante.

A auditoria não consulta a autoridade, por ADR-0002. Ela verifica coerência das referências entre ROADMAP, PLAN-CONTEXT e handoff, boa formação dos estados e presença do fingerprint. Frescor é gate de escrita mais um comando explícito de verificação, executado por quem tem o backlog disponível.

Recuperação: a projeção é derivada, então regenerar a partir da autoridade é o reparo natural. Uma falha entre criar o item e escrever a projeção deixa um item órfão que a geração seguinte incorpora. Não há transação entre SQLite e sistema de arquivos, e não se tentará simular uma.

## FASE-003 — Pré-requisito fail-closed
- phase: FASE-003
- ADRs: ADR-0001
- BLs: none
- delivery-units: DU-003
- development-type: platform-devops

### HOW
`backlogctl` passa de `required: false` para `required: true` em `assets/dependencies.json`. Hoje é a única dependência opcional das dez, e `ensure_dependencies.py:252` só conta as exigidas em `missing_required`, então `--require-dependencies` nunca bloqueava por falta de backlog.

O bind deixa de depender de `--allow-install`. O `init` recusa sem backlog resolvido e vinculado.

`--skip-backlog` sobrevive como única saída explícita. A cláusula constitucional proíbe waiver **implícito**, e uma flag nomeada e versionada não é implícita; há precedente em `GRILL_SKIP_DEPENDENCIES=1`, que nunca é reportado como `OK`. O uso fica carimbado no bundle, e um bundle carimbado não alcança GO sem antes vincular o backlog — sem o carimbo, um bundle criado com a saída ficaria indistinguível de um conforme e o gate mentiria sobre o próprio pré-requisito. Dois call sites em `tests/` dependem da flag, e removê-la quebraria também qualquer consumidor que rode `init` em CI.

## FASE-004 — Migração de bundles legados
- phase: FASE-004
- ADRs: ADR-0003
- BLs: none
- delivery-units: DU-004
- development-type: backend

### HOW
O bundle ganha marcador de modo para a migração ser detectável e acontecer uma única vez.

Migração automática silenciosa está fora: o contrato do plugin `backlog` exige confirmação explícita para qualquer mutação, e migrar cria itens no backlog do operador. Vale o precedente de `GLOBAL-BASELINE-UNVERIFIED`, que bloqueia global legado sem migração implícita. O comando é preview-first e exige `--apply`.

Alcance do bloqueio: comandos read-only continuam rodando e emitem a pendência como finding bloqueante, então o veredito é NO-GO mas o operador enxerga o que precisa migrar; comandos que mutam recusam de saída. Bloquear tudo tiraria a ferramenta de diagnóstico justo quando ela é necessária.

Toda decisão adiada histórica vira item, inclusive as já encerradas, usando `item add --status`, que é snapshot inicial e não transição — verificado. Isso preserva sem exceção a invariante de que toda referência aponta para um item, o que mantém o gate simples; o custo aceito é ruído de itens encerrados no backlog operacional. No estado atual seriam sete itens novos, todos terminais, já que a oitava decisão adiada já tem item.

Idempotência é por construção própria, pelos mesmos marcadores da FASE-001, porque o armazenamento não recusa duplicata.

## FASE-006 — Detecção de skill sombreada no preflight
- phase: FASE-006
- ADRs: none
- BLs: none
- delivery-units: DU-006
- development-type: platform-devops

### HOW
Defeito observado nesta própria sessão: uma skill pessoal chamada `grill-with-docs`, instalada como symlink em `~/.claude/skills/` apontando para `~/.agents/skills/`, sombreou a skill homônima do plugin. O comando de sessão resolveu para a pessoal, que não tem os subcomandos do protocolo, e o operador só descobriu porque o argumento não fez sentido. Silencioso e reproduzível em qualquer ambiente novo.

O preflight já é o lugar onde o ambiente é inspecionado e reportado, então a detecção entra ali e aparece também no init, junto com o relato de dependências.

Alcance fechado nos nomes que o próprio plugin publica. O grill tem autoridade legítima sobre os próprios nomes e nenhuma sobre nomes de terceiros; varrer todo o ambiente atrás de duplicata qualquer produziria falso positivo e obrigaria a mapear o layout de skill de cada agente hospedeiro.

Ordem de precedência a considerar na detecção: skill de projeto, skill pessoal e skill de plugin podem coexistir sob o mesmo nome, e a sombra é o caso em que a de projeto ou a pessoal vence a do plugin. Symlink conta como presença, e foi exatamente a forma que causou o defeito — resolver o alvo importa para o relato, mas a presença do link já basta para sombrear.

Por padrão detecta e reporta, sem bloquear, seguindo o comportamento atual do preflight para dependências. Remoção exige flag explícita, pelo mesmo motivo de `--allow-install`: apagar arquivo fora do repositório é mutação no ambiente do operador e não pode acontecer por efeito colateral de um comando de diagnóstico. Remoção automática está descartada porque destruiria uma skill pessoal que o operador talvez quisesse manter, bastando renomear.

Restrição de teste: a matriz roda em três sistemas, incluindo Windows, então a detecção precisa lidar com layout de caminho e com symlink de forma portátil, e os testes precisam montar diretórios de skill sintéticos em vez de tocar o ambiente real.

## FASE-005 — Verificação e publicação 3.0.0
- phase: FASE-005
- ADRs: none
- BLs: none
- delivery-units: DU-005
- development-type: qa

### HOW
Regressão para os quatro defeitos, mais determinismo da projeção, round-trip dos estados, idempotência da migração e recusa do bundle não migrado. Todo teste injeta um `backlogctl` falso pelo seam `resolve_cli`; a matriz roda em três sistemas e duas versões de Python sem o binário real.

Inverter a autoridade e tornar o `init` fail-closed são incompatíveis com todo bundle e consumidor existentes, então a versão é 3.0.0. O bump vale nos oito lugares travados por `tests/validate_distribution.py`.

A tupla `ESSENTIAL` de `ensure_workflow.py` não é tocada: marcador novo invalidaria todo `WORKFLOW.md` v2 já materializado em consumidores, exigindo v3 e migração própria. O gate equivalente vive no auditor.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
