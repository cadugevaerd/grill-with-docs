# Resultado do autor do plano — latest-models

**Resultado:** autoria técnica concluída; proposta pronta para revisão independente, sem declaração de aceite do macrostep.

- Atividade: `plan-author-latest-models`; contexto GWD: `ctx-3fec10eddb66b60e2ffa1290`, epoch 4.
- Task: `task_a3f8b1595998`; dispatch: `ctx_f5c360f6a064`.
- Work item: `feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec`, FASE-001, DU-001.
- Branch real: `cadugevaerd/fix-latest-models`; diretório lógico da feature: `specs/033-latest-models`.
- Relatório gerado em UTC: `2026-09-24T15:35:24.551667+00:00`.

## Entrega e escopo

Apliquei a skill local `.agents/skills/speckit-plan/SKILL.md`, com setup canônico, leitura da especificação, handoff, PLAN-CONTEXT, ADR-0001/0002, constituição e caminhos relevantes do código. O setup respeitou `.specify/feature.json`; nenhum override persistente foi criado. Os hooks opcionais de commit foram omitidos conforme a proibição explícita de commits. Não houve delegação adicional.

Foram produzidos os cinco artefatos autorizados abaixo, cobrindo pesquisa, interfaces, persistência, compatibilidade, testes e release. O corpo diferencia design proposto de comportamento implementado. Não foi produzido `tasks.md`, nem alterado produto, política, versão ou configuração do usuário.

| Artefato | SHA-256 |
|---|---|
| `specs/033-latest-models/plan.md` | `9c6d2893282010994e1c371ef61e7162fec217ad901f2d428528bea7b14c6810` |
| `specs/033-latest-models/research.md` | `e8f2610cd0d9c28829c94d9d0212ef08a35955bbfd6537a8f4218f011cf31f0b` |
| `specs/033-latest-models/data-model.md` | `12e14b7c9e9ede21bd63e17263dc72ce80960005e4e63e5005e02ab7a11c1817` |
| `specs/033-latest-models/quickstart.md` | `90adcb8f5a01df33d62b9596b13241d36dcf4b2236ee3ec627a02b95237de844` |
| `specs/033-latest-models/contracts/model-selection.md` | `e9f373cc5bcdc7d0cb4437333ffe691574bd6adfb5d3a378db7c8256949e7498` |

As alterações paralelas observadas em `.grill/` pertencem à coordenação e não foram editadas por este autor. Não houve escrita em `.specify/reports/`, commit, publicação, execução de agente real ou acesso à rede nesta autoria.

## Decisões centrais

1. **Seleção por família e prioridade local.** Um resolvedor compartilhado seleciona o único candidato `visibility=list` com menor prioridade numérica finita, preservando Luna/Terra/Sol e Astra conforme o papel. Não há ranking por geração, fallback, refresh, leitura de `config.toml` ou seguimento de `upgrade`. A fronteira de leitura reutiliza `_native_bytes`; catálogo inválido/ambíguo recusa antes dos efeitos com `TIER-MODEL-UNRESOLVED` e metadados preservados até a CLI.
2. **Persistência real dos workers.** O código atual retorna o modelo apenas em stdout; o plano prevê `model_binding` imutável no Store e cobre os três caminhos irmãos de `prepare_worker`. Runtime vem do registro de ativação validado, e não do objeto admission, que contém hashes. Retry da mesma tentativa usa a seleção salva; remediação resolve uma tentativa nova antes de orçamento, lease, estado ou worktree. Leitura/replay histórico aceita ausência do campo sem inventar evidência.
3. **Especialistas puros e evidência congelada.** A CLI resolve Astra antes de persistir a atividade e passa o par ao contrato puro. Todas as verificações posteriores usam o pedido salvo, inclusive requested/effective/resolved, esforço, identidade e fencing; não consultam o cache novamente. Claude solicita `opus` com xhigh/high, preservando igualdade exata do alias observado.
4. **Política versionada.** O asset v1 fica byte-idêntico; v2 atende novos itens e cada consumidor carrega a combinação allowlisted de referência/hash selada. Evidência histórica permanece verificável sem cache. No binário candidato, nova preparação de especialista sob v1 recusa `ORCHESTRATION-MIGRATION-REQUIRED`; não há migração/reseal em massa ou novo verbo. Campanhas históricas terminam no bundle fixado, sem iniciar atividades Claude fable, e novos itens adotam v2.
5. **Release e regressão existente.** Proposta SemVer `6.1.0`, reavaliada contra a base integrada antes de ship, com os oito pontos sincronizados e CHANGELOG cumulativo. A release inclui `f1475f4f9523fcd7063e32b547aa6fd8bc364528`, preservando sucessor sem campanha predecessora e recusa sem bridge quando o predecessor tinha campanha. Frontend `NOT_APPLICABLE` para platform-devops; bootstrap e revisão independente continuam obrigatórios.

## Evidências consultadas

- Cache Codex local observado: client `0.155.1`, fetched_at `2026-09-24T15:19:31.255515319Z`, nove entradas, SHA-256 `fb54aa00ed0854df9429c86cae7b0e21a51bf500d8e8e226490163a0f582da4f`. A pesquisa registra a projeção necessária; não foi copiado o cache do usuário para o repositório.
- Evidência nativa de Opus recebida da coordenação em `opus-alias-launch-evidence.json`, SHA-256 `657e761d31b2be862cc6a2fd445fa52b7419e67c7d2aebf3e5f6d01f263fe343`, dispatches `ctx_ffb2d08c15de` e `ctx_a96d57fcf5e9`: requested/effective `claude`/`opus`/`high`. O arquivo e sua correlação foram inspecionados; este autor não lançou esses agentes.
- Política v1 preservada: SHA-256 `c30b3cecf9c5cc4949c8c3d14eca050608d773f4ffa690fc2c9e72e7a95a3553`, reconferido após a autoria.
- Constituição 2.1.0: SHA-256 `54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569`; verificação de desenho antes/depois documentada no plano, sem exceção proposta.

## Verificação executada

| Verificação | Resultado |
|---|---|
| `python3 tests/run_validators.py` | Iniciada antes da autoria, concluída uma única vez com exit 0; todos os processos do runner passaram. O último validator executou 78 testes em 395.109 s, `OK (skipped=1)`; skip esperado do alias macOS `/var -> /private/var` ausente no host Linux. |
| `git diff --check` | Exit 0. |
| Check Python dos cinco documentos, inclusive untracked | UTF-8, newline final, ausência de whitespace terminal/placeholders e existência de todos os links Markdown locais: aprovado. |
| Integridade da política histórica v1 | Hash original preservado. |
| Frontend | `NOT_APPLICABLE`; não requer preview ou PNG. |

A suíte é evidência do baseline atual, não validação de uma implementação futura do plano. Os cenários novos e os efeitos negativos esperados estão especificados no contrato e no quickstart para a etapa executável posterior.

## Bootstrap da sessão

A instalação, habilitação e confiança de `i-have-adhd@i-have-adhd` foram confirmadas nesta dispatch; a leitura integral da referência aprovada foi correlacionada pelo preflight. Após compactação, a primeira revalidação retornou `STYLE-LOAD-UNCONFIRMED` porque o resultado do preflight saiu fracionado entre exec e polling. O diagnóstico foi enviado por `orca orchestration ask`; conforme orientação da coordenação, repeti preflight e leitura integral com resposta completa em cada chamada.

O preflight final retornou exit 0, `presentation.work_ready=true`, `use_ready=true`, `loading=loaded`, `enablement=enabled`, `trust=ready`, `diagnostics=[]`. Evento atual: `orca:ctx_f5c360f6a064:ctco_01a0d40c-9fd2-7552-816d-fd192c5efe90`; skill SHA-256 `3170b16ace00aecb0dd7feb54c0b5aa642e7502acda06ecd24fd89a11c7127e9`; config fingerprint `5d2973ec9bd87d025fe8662dc85afc5bf0df6c749de2c69b99ff900a6c2ebff3`. `functional_verified=false` e `behavior=not_tested`: não se declara verificação comportamental.

## Limites e próximo responsável

O cache local prova a forma e a preferência observadas, não disponibilidade remota. A evidência real Claude prova o alias `opus` com esforço high, não um slug completo do provedor nem um lançamento xhigh; o plano exige teste determinístico das duas funções e mantém o contrato de observação exato. A recusa de nova preparação v1 é uma fronteira explícita de rollout para julgamento do revisor, sem bloqueador de autoria em aberto.

A coordenação deve encaminhar os cinco artefatos à revisão independente e decidir o aceite do macrostep no fluxo canônico. Este autor não atestou nem encerrou o macrostep, não implementou a feature e não autorizou ship. O `worker_done` subsequente encerra apenas esta sessão especialista; nenhum trabalho adicional será iniciado sob esta dispatch.
