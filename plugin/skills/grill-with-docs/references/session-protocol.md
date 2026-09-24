# Protocolo de sessão v7.1.0

Frases com **deve**, **nunca** e **somente** são normativas. A inicialização cria o workflow/Constituição quando ausentes; depois do init, os artefatos são read-only.

## Apresentação local obrigatória

Antes de qualquer resposta de trabalho em um fluxo GWD, inclusive início, retomada, compactação reentrada e especialista, execute o bootstrap local de `i-have-adhd@i-have-adhd`. O bootstrap resolve a instalação **selecionada pelo runtime**, exige observações correlacionadas e distintas de habilitação e confiança, e lê o arquivo regular aprovado por inteiro com o `load_request`; registra sessão, geração/configuração, escopo GWD e hashes do arquivo/corpo. Nunca trate cache, enumeração, caminho impresso, exit 0 ou autorrelato como leitura/obediência; não execute hook upstream, não auto-invoque a skill e não altere configurações, caches ou flags globais.

Enquanto a aplicação estiver ativa, cada nova sessão/incarnation, runtime ou reentrada após compactação exige leitura atual antes de uso. `stop adhd mode` é a única suspensão local: requer fonte humana da mesma sessão/incarnation/escopo, deixa `work_ready=true` somente após revalidar instalação, compatibilidade, enablement e trust, mantém `loading=stale` e não recarrega/aplica o corpo. A sessão nova não herda essa suspensão. `normal mode` só respeita pedido explícito e nunca é emitido pelo loader. Preservar Ponytail, conteúdo solicitado e as regras/exceções completas da referência; fora do GWD, `application=out_of_scope` e não há alteração de configuração externa.

**Limitação atual do bootstrap:** na fonte `5bc9500e6fff10fce5353f758fdc334e490a3523`, init/adopt podem criar contexto `ACTIVE` sem observação correlacionada nem `presentation`. A igualdade da string `session_ref` no guard de autoridade e o fallback `{"legacy": true, "work_ready": true}` do guard de apresentação ausente não provam sessão nem apresentação obrigatória, mesmo com sucesso do CLI. Os requisitos acima são normativos, ainda não garantidos por esses caminhos; remediação delimitada do core e revalidação continuam pré-condições dos aceites funcionais posteriores. Não liberar trabalho dependente por esse fallback.

## Eficiência no workflow v5

A policy é selecionada pelo work item: v3/v4 continuam com v1; v5 usa v2 e
`agent-orchestration.v2.md`. As regras abaixo sobre especialização mecânica e revisão
obrigatória em todas as etapas descrevem v1; no v5, a matriz e classificação v2 governam
os papéis. Identidade, independência, apresentação, grants, cleanup e gates de ship valem
para ambos. Não há migração automática de itens ou projetos existentes.

Antes de cada etapa v5, preparar `step-inputs/<step>.json` dentro do work item, conforme
o suplemento v2. O core revalida essa classificação em entrada, atividades, checkpoint
e attest. O input manifest de cada atividade carrega `assessment_sha256`; mudar a
classificação ou suas fontes invalida seu reaproveitamento. Frontend continua exigindo
prévia e aprovação humana, inclusive quando o trabalho não exige outra revisão intermediária.

A entrevista v5 admite até três perguntas independentes por lote. Cada DQ respondida
gera uma linha com round_id próprio, `question_id`, `transition`, `batch`, `question_run`
e `batch_questions` (lista completa e idêntica em todas as respostas do lote).
`question_run` identifica a sessão de entrevista; retomada da mesma sessão conserva o ID.
Resposta parcial mantém as demais DQs pendentes. Perguntas dependentes são feitas
separadamente. Impact scan e persistência ocorrem após as respostas; limites contam
perguntas materiais apresentadas, incluindo as ainda sem resposta, nunca número de lotes.
Escolhas reversíveis de implementação ficam com o autor e são documentadas; escopo,
comportamento público e risco material permanecem decisões humanas.

No v5, dois grupos são o padrão de partition; `--groups N` define teto explícito.
Cada worker executa todas as tarefas de seu nó, mantendo Result individual. Não abrir
sessões por tarefa nem agrupar entre fases. Antes do despacho, ler aceites e seguir a
recuperação abaixo. Durante implementação, usar checks focados; início e verify final
executam a suíte completa. Evidência válida pode ser citada, mas não dispensa nova
execução quando exigida pelo gate. Não há cache persistente de autoridade ou testes.

### Recuperação antes de despacho

No mesmo DAG, reúna todos os nós completos para uma única importação no successor:

```text
python3 .../grill_workspace.py gauntlet-tasks-import ROOT --work-id ID --run-id SUCCESSOR --dag DAG --source-task T001=SOURCE --session-ref SESSION
```

Após inspecionar o preview, repetir com `--apply --expected-sha256 HASH`. Em DAG novo,
use `gauntlet-tasks-rebase` conforme a seção de continuidade; transporte somente tarefas
com fingerprint inalterado. Nunca copie aceites manualmente. Resultado desconhecido
exige reconciliação da operação original. Cleanup pendente drena a mesma obrigação.
`CHAIN-STALE` continua exigindo cadeia sucessora; artefato byte-idêntico pode ser
reaproveitado durante a revalidação, sem inventar execução de skill ou nova revisão.

## Admissão e encerramento

Resolver Git root e worktree dedicada. Apresentar recomendação Sol no Codex ou Opus no
Claude sem trocar modelo. Confirmar bootstrap e autoridade observados antes de init/retomada.
A Constituição é no-clobber no init e read-only depois; evidência ausente ou stale bloqueia.
O líder invoca cada canonical skill na sessão ativa: não usar subprocessos de agentes
para executar macroetapas. Antes da invocação, `gauntlet-step-enter` admite o contexto.
Especialistas não escrevem `.grill/` ou `.specify/reports/` nem fecham macroetapas.

Para os verbos, argumentos, recusas e recovery completos, leia antes da operação a seção
correspondente de [operações de sessão](session-operations.md):

- Fluxo e checkpoints: `--session-ref` e `--operation-id` estável; retry reutiliza ambos e os inputs.
- Admissão, atividades e arquivos explícitos: prepare → dispatch → accept; payload somente após
  bootstrap neutro e observação de identidade/modelo/esforço/close. Files/Result são grants fechados.
- Cleanup e continuidade: persistir resultado antes de fechar; confirmação por read-back,
  nunca timeout, silêncio ou lease. Preservar recursos com trabalho/evidência exclusiva.
- Migração e import/rebase: preview/apply com hashes, sem reescrever história nem fabricar workers.
- Gate constitucional, triagem, hotfix, auditoria e reconciliação: aplicar cada pré-condição publicada.

Mudança de CLI exige quiescência comprovada e contexto sucessor. Retomada lê aceites e
checkpoint antes de despachar. `STEP-ACCEPTED-CLEANUP-PENDING` já aceitou a etapa:
drenar cleanup sem repetir o trabalho. `PARTITION-NO-WORKERS` não autoriza worker fictício.
`PLAN_ONLY_STOP` encerra feature/fix; hotfix tem trilha própria, com HOTFIX-GO e ship externo.
