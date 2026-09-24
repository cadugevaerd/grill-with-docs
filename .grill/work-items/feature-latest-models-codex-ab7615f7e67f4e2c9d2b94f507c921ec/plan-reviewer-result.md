# Revisão independente do plano — latest-models

**Veredito: CHANGES_REQUIRED**

Revisão de `specs/033-latest-models/plan.md` e quatro artefatos de suporte, sob `.agents/skills/speckit-plan/SKILL.md`, Constituição 2.1.0, spec, handoff, PLAN-CONTEXT, ADR-0001/0002 e contrato GWD. O bloqueador é a continuidade operacional do próprio ciclo após a candidata, não a regra de seleção de modelos.

## Finding obrigatório

### P1 — Definir um bundle de continuidade que contenha f1475f4 antes de bloquear novas atividades v1

**Local:** `specs/033-latest-models/plan.md:117` e `:119`. A mesma premissa aparece em `research.md:96`, `data-model.md:84`, `contracts/model-selection.md:121` e `quickstart.md:9`.

O plano determina que o binário candidato recuse toda nova preparação de especialista em v1 com `ORCHESTRATION-MIGRATION-REQUIRED`, mantenha v1 nos contextos sucessores e não forneça migração. Como saída, afirma que esta campanha termina no bundle já fixado. Essa saída não está concretizada e o bundle instalado 6.0.30 inspecionado não consegue sequer validar o estado atual: falta-lhe a correção f1475f4, que existe apenas no checkout entre as duas cópias comparadas.

**Evidência reproduzida nesta revisão, sem mutação:** importei separadamente os contratos do checkout e do cache instalado, li o bloco `agent_orchestration` do Store atual e chamei `validate_block` em cada módulo. O checkout retornou PASS; o cache retornou `OrchestrationError: successor context has no campaign bridge`.

- Checkout: `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, SHA-256 `aad0a06e5d8d51c6f75e1126a09410e6fc67b65f72f48083e8731e6eeaca9b1b`.
- Cache comparado: `/home/carlosaraujo/.codex/plugins/cache/grill-with-docs/grill-with-docs/6.0.30/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, SHA-256 `753b7be85d0b039e5e304dc941a321ffa7e253982adbb9ba7ae26ef59766b914`.
- Contexto corrente `ctx-3fec10eddb66b60e2ffa1290`: campanha presente; predecessor `ctx-abe82e929ba403bc2dc10449`: campanha ausente; `campaign_bridge` ausente. É exatamente o caso corrigido por f1475f4.
- Snapshot observado em `/home/carlosaraujo/Documentos/Projetos/grill-with-docs/.git/grill/orchestrator.json`: revisão 3282, SHA-256 de bytes `0d635d373b9377c7e4e5d8b536ab038568d79d834fb4730f70e4ebfee99149e4`.
- A exceção correta está em `agent_orchestration.py:1393`; o teste positivo e o negativo estão em `tests/validate_agent_orchestration_contract.py:2049`. O commit `f1475f4f9523fcd7063e32b547aa6fd8bc364528` modifica precisamente esse contrato e esse teste, com bump diferido para esta feature.

**Consequência:** continuar pelo checkout resolve o defeito atual, mas, quando ele passar a ser o candidato previsto, novas revisões obrigatórias em `converge` e `review` ficarão bloqueadas pela policy v1. Voltar ao cache 6.0.30 reintroduz o erro estrutural acima. Aceitar atividades já registradas não supre especialistas futuros sobre bytes ainda não produzidos; criar outro work item v2 tampouco conclui a campanha original. Portanto, não é suficiente deixar a escolha de CLI para tasks ou para a fase executável.

**Correção concreta requerida no plano e no quickstart:** definir, antes de qualquer integração da candidata, um bundle preservado fora dos caches upstream, derivado de uma revisão identificada que já contenha f1475f4 e ainda mantenha a preparação v1 necessária ao ciclo. Registrar seu caminho absoluto de CLI, revisão e manifest de hashes; separar expressamente esse CLI de coordenação do checkout candidato usado pelos validadores. Exigir prova read-only de que esse bundle valida o Store atual, preserva os pins históricos e admite os especialistas Codex necessários às etapas restantes, com bootstrap e fechamento normais; manter proibido qualquer novo especialista fable. Descrever quando e por quem esse bundle é fixado e revalidado até ship, sem editar caches, seals, receipts ou bridges históricos. Acrescentar um cenário de continuidade que combine o predecessor sem campanha, a futura recusa v1 na candidata e a continuação pelo bundle preservado. Se a política vigente não admitir essa preservação, resolver explicitamente a alternativa autorizada antes de aprovar o plano.

Esta revisão não criou esse bundle nem alterou o fluxo; a decisão pertence à revisão do design. A afirmação `no design question remains open` em `plan.md:150` deve ser retirada ou sustentada por essa correção.

## Demais verificações críticas

| Área | Julgamento e evidência |
|---|---|
| Seleção Codex | Adequada como design: família por full-match, apenas `visibility=list`, menor prioridade numérica finita, bool excluído, empate mínimo e duplicação relevante recusados; geração, ordem e `upgrade` não decidem. A família Terra permanece medium. Contrato §§1–2 e research R1–R3. |
| Três produtores de worker | Cobertura explícita de `declare_worker`, `gauntlet-prepare-worker` e `_mint_remediation_worker`, confirmados no código. Persistência de `model_binding` na primeira declaração, antes dos efeitos, reutilização da tentativa e nova resolução para remediação estão descritas. O runtime da preparação passiva vem do registro de activation validado, não de admission nem de um default. `plan.md:99`–`:103`; código em `gauntlet_runs.py:1914`, `:2113`, `:2439` e `grill_workspace.py:4482`. |
| Store e histórico | Campo historicamente opcional e imutável, sem backfill; replay/cleanup não leem o cache. Preparação histórica sem prova recusa nominalmente. A implementação ainda precisará provar essas invariantes, sobretudo a leitura antes dos efeitos de recovery e os dois caminhos de remediação. Data model §3 e quickstart §2 cobrem isso como obrigação futura, sem alegar implementação. |
| Policy v1/v2 | Nova policy em arquivo próprio e loader allowlisted por ref/hash/schema; v1, suplemento e template permanecem byte-idênticos. Plano enumera init/adopt, preflight, bind, atividades, cobertura, step-enter, checkpoint/attest e continuidade. Isso resolve a compatibilidade de leitura no design; não resolve o finding de continuidade de execução. V1 reconferida com SHA-256 `c30b3cecf9c5cc4949c8c3d14eca050608d773f4ffa690fc2c9e72e7a95a3553`. |
| Falhas sem efeitos | Catálogo ausente, inválido, ambíguo ou sem família recusa antes de worker/lease/worktree/bootstrap/payload; frontier recusa antes de ler catálogo. O plano identifica corretamente a perda atual de `TierModelError.extra` em `_resolve_worker_model` e exige propagação pela CLI. Quickstart exige código JSON, exit e comparação de Store/journal/receipts/leases/worktrees, não apenas mocks. |
| Especialistas | Resolução na fronteira CLI e persistência no pedido; verificação posterior contra o par salvo, sem reconsultar catálogo. Estão incluídos os consumidores diretos e transitivos, requested/effective/resolved, provider, esforço, independência, identidade e fechamento. |
| Opus | Conferidos os dois envelopes nativos de `opus-alias-launch-evidence.json`: IDs de dispatch/worker correlacionados, requested/effective `claude`/`opus`/`high`. `agent_runtime.py:1236` registra o alias como resolved ID quando pedido e efetivo coincidem. Igualdade exata é sustentada; não há prova de slug completo nem de lançamento author xhigh nesses envelopes, limitação que research R6 declara corretamente. |
| Distribuição | `plan.md:127`–`:135` enumera os oito pontos corretos, conferidos em `CLAUDE.md:113` e `tests/validate_distribution.py`. CHANGELOG cumulativo inclui expressamente f1475f4; 6.1.0 é proposta a revalidar contra a base integrada. Tag imutável e Release no mesmo anchor permanecem gates posteriores. |
| Skill, Constituição e escopo | Cinco artefatos presentes e sem placeholders de design; hooks de commit before/after plan são opcionais em `.specify/extensions.yml` e a proibição de commits foi respeitada. Frontend NOT_APPLICABLE é coerente. Nenhuma implementação, atestação, publicação ou macroetapa posterior foi executada por este revisor. |

## Cobertura e integridade dos inputs

Todos os 34 arquivos de `plan-reviewer-input.json` foram inspecionados integralmente ou nos trechos relevantes às afirmações, e seus SHA-256 foram recalculados: **34 correspondências, zero divergências**. O relatório do autor e suas observações foram usados como contexto; o finding acima veio de leitura e reprodução independentes.

- Governança: goal, CLAUDE, Constituição, extensions, skill speckit-plan, suplemento, policy v1 e template Files.
- Produto e testes: binding asset, tier_models, agent_orchestration, agent_runtime, gauntlet_runs, ensure_dependencies, ADR worker-floor, validadores tier-model/orchestration/distribution e CHANGELOG.
- Requisitos: spec, handoff FASE-001, PLAN-CONTEXT e ADR-0001/0002.
- Entrega e proveniência: cinco artefatos do plano, attestation specify, resultado do autor, observações aberta/fechada do autor e evidência Opus.

A attestation specify registra `COMPLETED` na invocação terminal e no resultado. Autor observado: dispatch `ctx_f5c360f6a064`, `gpt-6-astra`/`xhigh`, encerrado; este revisor é outra sessão, dispatch `ctx_99ef435ded2b`, task `task_f65207996c94`. Não foi reutilizada a sessão autora.

## Verificação executada e limites

- Bootstrap desta sessão: `presentation.work_ready=true`, `loading=loaded`, `trust=ready`, `enablement=enabled`, leitura integral correlacionada. `behavior=not_tested` e `functional_verified=false`; não há alegação comportamental.
- `git diff --check`: exit 0.
- Reprodução read-only dos dois contratos contra o mesmo bloco do Store: checkout PASS; cache 6.0.30 recusa nominal descrita no finding.
- Suíte baseline: `python3 tests/run_validators.py` foi iniciada e interrompida deliberadamente por este revisor após concluir a análise documental e a reprodução direta, durante `validate_gauntlet_activation_contract.py`; exit 130 por SIGINT. Os validadores anteriores concluíram sem falha reportada, inclusive `distribution: OK`, mas a suíte completa NÃO foi validada nesta sessão. Não há claim de PASS geral, nem substituição por relato do autor; a execução integral continua obrigatória na futura entrega executável.

Não houve edição de arquivo no repositório, commit, lançamento de worker ou execução de macroetapa posterior. O único artefato escrito por este revisor é este relatório externo, para cópia literal pela coordenação.

Riscos residuais: o cache Codex é contrato local implícito e não prova disponibilidade remota; Opus xhigh continua exigindo observação real em cada admissão futura; seletores, persistência, recusas e compatibility loader ainda são design e precisam da validação executável prevista. Nenhum desses limites elimina o finding P1. O plano precisa da correção de continuidade e de nova revisão antes do aceite do macrostep.
