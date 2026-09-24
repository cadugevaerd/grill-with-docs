# Proposta de autoria — latest-models-codex

- Atividade: `interview-author-latest-models`.
- Destino: `feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec`, `FASE-001`.
- Origem: `tri-latest-models`, rota `feature`, severidade `medium`, sem impacto de produção registrado.
- Payload recebido: `input_sha256=6bbc87849eacc242b28e6fd272217cd8654ca53154cd3ba56feaeffd416b8097`.
- Limite: proposta documental, `PLAN_ONLY_STOP`; nenhum arquivo do repositório alterado, nenhum código ou teste do projeto executado.

As decisões abaixo já foram aceitas pelo humano no bundle fonte; esta proposta as transporta sem nova escolha. As evidências técnicas são as registradas em 2026-09-23, não uma verificação atual do catálogo, do código ou da disponibilidade dos modelos. Os hashes são os declarados no input recebido, sem nova aferição nesta atividade.

## Fontes lidas

Todos os caminhos abaixo são relativos à raiz do repositório.

- **S1:** `.grill/work-items/feature-latest-models-dbf134a84fc14114a438bddf1da709b6/docs/adr/ADR-0001.md` — resolução Codex por família e preservação do piso dos workers.
- **S2:** `.grill/work-items/feature-latest-models-dbf134a84fc14114a438bddf1da709b6/docs/adr/ADR-0002.md` — especialistas Claude via `opus`.
- **S3:** `.grill/work-items/feature-latest-models-dbf134a84fc14114a438bddf1da709b6/ROUND-LOG.jsonl` — autorização humana, rodadas `R-0001` a `R-0005`; SHA-256 declarado `62f411e8b9d538f5c4c2637355af0d880d829d691ff8ad3e9fed10d8793a6efc`.
- **S4:** `.grill/triage/tri-latest-models.json` — `triage_id=tri-latest-models`, `recorded_at_commit=d4bf60b09c376522904d0c19fd57e59a7df9ea61`.
- **S5:** `.grill/triage/latest-models-debug.md` — causa raiz e diagnóstico referenciado por S4; SHA-256 declarado `7ea74f2166f278fb9a3e531490d1981a4496898c96ac88b2913e280cfeea3ac8`.

Também foram lidos os artefatos existentes no novo work item. Ele registra base `1af890b0f31afe022ae9fe566c660b2d673f195a`, `audit_verdict=pending`, cláusulas constitucionais `PENDING` e conteúdo inicial ainda com placeholders. Seu `immutable.source=null` permanece intacto; a referência documental a `tri-latest-models` não autoriza reescrever metadados imutáveis.

## ADR-0001 — Resolver modelos Codex por família no catálogo local, fail-closed

- Destino proposto: `docs/adr/ADR-0001.md` do novo bundle.
- Decisão: aceita pelo humano em S3, `R-0001` a `R-0004`.
- Fase: `FASE-001`.
- Fontes: S1, S3, S4 e S5; triagem `tri-latest-models`.
- Relação: decisão transportada do bundle fonte; não substitui nem modifica seu ADR.

### Contexto

S5 registra que o binding Codex fixa `gpt-5.6-luna/terra/sol` e que a resolução devolve esses literais, sem consultar o catálogo. Sete workers reais usaram `gpt-5.6-terra`; no catálogo observado havia sucessores `gpt-6-luna/sol/astra`, mas não `gpt-6-terra`. Portanto, o defeito é o pin permanente de geração; usar `terra` da geração anterior continua correto enquanto ela for a opção preferida da própria família. S1 registra ainda que nomes curtos como `sol` não são aliases Codex comprovados: passam com fallback metadata e chegam literais à API.

### Decisão

1. O binding Codex declara famílias: `small=luna`, `medium=terra`, `large=sol`; a policy declara `astra` para autor e revisor Codex. Os esforços, papéis e independência do revisor permanecem como definidos na policy.
2. No despacho, resolver cada família para o slug **listado de menor `priority` daquela família** no `models_cache.json` sob o home do Codex. A resolução usa leitura local, sem subprocesso e sem rede; não escolhe o topo global nem deduz a geração mais nova pelo nome.
3. Persistir o slug resolvido no worker record e na observação do especialista, preservando a rastreabilidade do modelo efetivamente observado.
4. Catálogo ausente ou ilegível, formato incompatível, ou família sem slug listado: recusar com `TIER-MODEL-UNRESOLVED`, incluindo runtime, tier/papel, família e caminho do catálogo, **antes de qualquer worktree, lease ou payload**. Não usar fallback para slug antigo.
5. Manter `medium=terra`; a família acompanha automaticamente um sucessor quando ele for a opção de menor `priority` listada para `terra`. Não substituir por `luna` nem por uma lista de famílias.
6. Declarar o atributo `frontier` por família e preservar a aplicação do piso não-frontier dos workers sobre o slug resolvido. Atualização de geração não concede permissão adicional ao worker.
7. Preservar os tiers Claude `haiku/sonnet/opus` e as recomendações textuais do líder `Sol`/`Opus`; a única ampliação Claude é o par especialista tratado em ADR-0002.
8. Não modificar silenciosamente a policy v1 verificada por contextos com `policy_sha256` selado. O plan deve definir a compatibilidade por nova versão coexistente ou reseal explícito; nenhuma dessas alternativas foi escolhida pelo humano nas fontes.

### Consequências e alternativas rejeitadas

O formato do catálogo local torna-se dependência declarada; incompatibilidade provoca recusa nomeada. Os testes futuros precisam de seam injetável e execução offline. Foram rejeitados: topo global do catálogo, alias de API `gpt-6`, atualização manual de pins, fallback last-known e troca da família `terra` do tier `medium` (S1/S3).

## ADR-0002 — Especialistas Claude usam o alias `opus`

- Destino proposto: `docs/adr/ADR-0002.md` do novo bundle.
- Decisão: aceita pelo humano em S3, `R-0005`.
- Fase: `FASE-001`.
- Fontes: S2 e S3; relação com ADR-0001 e `tri-latest-models`.

### Contexto e decisão

O humano escolheu Opus 5.5 para autoria e revisão de julgamento, declarado pelo alias `opus` para acompanhar a linha, sem fixar `claude-opus-5-5`. O par fica **autor `opus/xhigh`; revisor `opus/high`**, preservando estrutura da policy, matriz de atividades, papéis e independência do revisor.

O alcance futuro compreende `roles.claude`, `SPECIALIST_PAIRS["claude"]`, as tabelas de papéis em `SKILL.md` e `references/session-protocol.md`, o texto correspondente no README e o validador do par. Os tiers Claude, a recomendação textual do líder e o piso não-frontier dos workers permanecem intactos.

Nenhuma atividade de especialista Claude pode usar `fable` a partir dessa decisão. Enquanto o gate exigir `fable`, as atividades autor/revisor Claude ficam impedidas; o ciclo pode ser conduzido no runtime Codex com o par `astra`. Isso é pendência operacional, não waiver nem permissão para contornar o gate.

### Consequências

O plan deve comprovar se o Orca observa `opus` como alias ou slug resolvido e preservar o slug duravelmente quando disponível; pedir um alias, isoladamente, não comprova o efetivo. A mudança da policy deve respeitar os contextos selados conforme ADR-0001. Foram rejeitados manter `fable`, usá-lo temporariamente durante a entrevista, fixar o slug e reescrever silenciosamente a policy v1 (S2/S3).

## DECISION-FRONTIER — DQ-0001 a DQ-0005 resolvidas

Todas pertencem à `FASE-001`, com `state: resolved`. As citações reproduzem os registros humanos de S3; as perguntas abaixo apenas organizam as decisões já tomadas.

| DQ | Pergunta canônica / fingerprint proposto | Decisão humana preservada | Evidência | final-ref |
|---|---|---|---|---|
| DQ-0001 | Como atualizar modelos Codex sem pin de geração? / `codex-familia-catalogo-local` | “Humano via coordenador Orca: A (família via catálogo local, menor priority, gravado no worker record)” | S3 `R-0001`; S1 | `docs/adr/ADR-0001.md` |
| DQ-0002 | Qual família mantém o tier medium Codex? / `codex-medium-familia-terra` | “Humano via coordenador Orca: A (manter família terra no medium)” | S3 `R-0002`; S1 | `docs/adr/ADR-0001.md` |
| DQ-0003 | O que acontece quando o catálogo não permite resolver a família? / `codex-resolucao-fail-closed` | “Humano via coordenador Orca: A (recusa fail-closed TIER-MODEL-UNRESOLVED, seam injetável nos testes)” | S3 `R-0003`; S1 | `docs/adr/ADR-0001.md` |
| DQ-0004 | Como autor e revisor Codex acompanham a família? / `codex-especialistas-familia-astra` | “Humano via coordenador Orca: A (autor/revisor Codex via família astra; hash da policy com cuidado)” | S3 `R-0004`; S1 | `docs/adr/ADR-0001.md` |
| DQ-0005 | Qual modelo e esforço usar no par especialista Claude? / `claude-especialistas-alias-opus` | “Humano via coordenador Orca, 2026-09-23: par autor/revisor Claude = Opus 5.5 pelo alias opus (autor xhigh, revisor high), não mais fable; estrutura da policy mantida” | S3 `R-0005`; S2 | `docs/adr/ADR-0002.md` |

Não há nova decisão humana pendente neste recorte. Não criar BL fictício; a compatibilidade da policy e a comprovação da observação do alias pertencem ao plan. Na integração, o coordenador deve registrar a proveniência das cinco resoluções em `ROUND-LOG.jsonl`; a linha inicial com `source-or-adr` não comprova autorização humana.

## Handoff proposto — FASE-001: Atualização de modelos por família e alias

- phase: FASE-001
- roadmap: ROADMAP.md#FASE-001
- context-refs: família de modelo; catálogo local; prioridade do catálogo; slug resolvido; tier; especialista; alias; policy selada
- ADRs: docs/adr/ADR-0001.md; docs/adr/ADR-0002.md
- BLs: none

### WHAT

- delivery-units: DU-001
- development-type: documentation

Produzir a especificação e o plano verificável para que despachos Codex de workers e especialistas acompanhem a opção preferida da família aprovada e para que especialistas Claude usem `opus`, preservando tiers, esforços, independência de revisão e restrições de elegibilidade. Esta entrega encerra em `PLAN_ONLY_STOP`.

O contrato de aceitação do comportamento a planejar deve demonstrar:

1. A presença de um novo modelo preferido na mesma família muda a seleção Codex sem edição manual de um pin de geração; a seleção nunca troca de família para buscar uma geração numericamente maior.
2. O tier `medium` continua em `terra`, inclusive quando outras famílias têm geração posterior; autor e revisor Codex continuam na família `astra`.
3. Uma resolução impossível produz `TIER-MODEL-UNRESOLVED`, identifica o contexto necessário ao diagnóstico e impede o despacho antes da criação de recursos e entrega de conteúdo de trabalho.
4. Cada despacho mantém evidência durável do modelo resolvido e do efetivo observado; modelo solicitado não é tratado como prova isolada do efetivo.
5. Autor e revisor Claude usam `opus/xhigh` e `opus/high`, respectivamente, sem atividade de especialista em `fable`; indisponibilidade de um caminho admissível mantém o bloqueio.
6. Os tiers Claude, recomendações do líder, piso não-frontier dos workers e integridade dos contextos selados permanecem preservados. A validação futura funciona offline, sem depender de executáveis reais dos harnesses.

Ficam fora desta entrega: implementação do produto, despacho para implementar a feature, alteração de configuração global do líder, mudança arbitrária de famílias, concessão de elegibilidade frontier, download de catálogo/modelos e reescrita silenciosa de contextos selados.

### WHY

`tri-latest-models` (S4/S5) registra que o modelo solicitado aos workers nasce de um binding literal e não acompanha o catálogo local. A resolução por família remove a manutenção por geração sem confundir atualização com mudança de tier; `medium=terra` preserva a escolha humana quando não existe sucessor na geração observada. O alias `opus` aplica a escolha humana ao par Claude e evita reproduzir um pin de geração. Recusa explícita, evidência durável e preservação da policy selada mantêm a decisão verificável e impedem substituições silenciosas.

## Notas técnicas para PLAN-CONTEXT e integração

- Manter `FASE-001`, `DU-001`, `development-type: documentation`, ambos os ADRs e `BLs: none` coerentes em ROADMAP, DELIVERY-MAP, PLAN-CONTEXT e handoff. O comportamento de produto acima é alvo do plano, não evidência de implementação concluída.
- Concentrar a futura resolução no caminho compartilhado do binding e cobrir seus consumidores de workers e especialistas, conforme o fluxo documentado em S5; não adicionar guardas independentes por caller. Usar somente stdlib/Python >= 3.10 e leitura local, conforme as restrições fornecidas do repositório.
- Detalhar no plan a identificação inequívoca das famílias em slugs, a validação do formato/prioridade, o tratamento de empates, a localização do home Codex e a classificação frontier por família. As fontes não estabelecem esses detalhes; não apresentá-los como decisões humanas já tomadas nem inventar modelos.
- Comprovar compatibilidade do `policy_sha256` e observação do alias Claude antes de liberar os caminhos afetados. Não escolher silenciosamente entre nova versão coexistente e reseal explícito.
- Prever verificações offline para seleção dentro da família, permanência de `terra`, falha antes de efeitos, rastreabilidade e preservação do piso. Uma futura alteração em `plugin/**` exige bump SemVer nos oito pontos do contrato de distribuição; este relatório não altera o plugin.
- O coordenador ainda deve incorporar a proposta, completar a evidência constitucional, submeter à revisão independente e auditar o bundle. Não declarar `GO`, `ready-for-specify` ou conclusão do work item a partir deste relatório; o estado observado permanece `pending`/`in-progress`.

**Entrega desta atividade:** proposta documental completa, com cinco decisões humanas preservadas e origem `tri-latest-models` rastreada. Nenhum gate, catálogo atual, bootstrap de estilo ou teste foi certificado por esta leitura restrita.
