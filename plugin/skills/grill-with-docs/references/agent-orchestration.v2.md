# Suplemento de orquestração v2

Aplica-se somente ao workflow v5. A policy v1 e os contratos históricos não mudam.
O líder invoca as onze skills canônicas na própria sessão, com o contexto devolvido por
`gauntlet-step-enter`; entrega de contexto não atesta invocação.

## Classificação e revisão

Antes de cada etapa, o líder prepara `.grill/work-items/<id>/step-inputs/<step>.json`:
`schema: grill-step-assessment/v1`, `step`, `new_how` booleano, `risks` (array),
`justification` não vazia e `files` (array de objetos `path`, `sha256`, cobrindo as fontes
usadas para classificar a etapa). O core verifica os bytes dessas fontes, não interpreta
linguagem natural. Use os nomes de risco da policy; `risks: []` exige justificativa.
Falta, fonte stale ou classificação divergente bloqueiam. Atualize a classificação ao
mudar o escopo; nunca use lista vazia para omitir risco conhecido.

Revisão independente obrigatória em `plan` e `review`. As demais etapas são executadas
pelo líder, sem especialista obrigatório para cumprir a matriz. Novas decisões de COMO
exigem autor especializado. Mudança material após planejamento aprovado em segurança,
autorização, dados sensíveis, migração, compatibilidade pública, arquitetura ou frontend
exige revisão extra na etapa afetada. Revisão visual e aprovação humana da prévia continuam
obrigatórias. `ship` continua exigindo autorização humana.

Cada atividade de ciclo inclui `assessment_sha256` no input manifest, igual ao hash
canônico da classificação corrente devolvido na entrada. Uma classificação alterada não
herda aprovação anterior. Revisor permanece independente de todos os autores relevantes;
checks determinísticos não são revisão. Identidade, modelo/esforço efetivos e fechamento
confirmado continuam obrigatórios antes dos aceites.

## Tarefas e recuperação

Use `task-files/v1`: grants explícitos, Result individual e barreiras de fase.
No v5, pule o passo migrate-v4 da skill histórica de partition: o workflow já está
materializado e nunca deve ser rebaixado. Preserve os demais passos e os paths
revisionados que partition-emit devolver; não fixe execution-dag.json.
No implement-parallel, o Result declarado por tarefa substitui o sidecar histórico por nó.
O padrão é dois grupos; `partition-emit --groups N` permite teto explícito.
Um worker executa o nó inteiro, sem abrir uma sessão por tarefa. Nunca agrupe entre fases.
Antes de despachar, consulte aceites: importe nós completos via `gauntlet-tasks-import`
ou use `gauntlet-tasks-rebase` para tarefas inalteradas em DAG sucessor. Ambos exigem
preview e apply com hash; resultados desconhecidos exigem reconciliação da mesma operação.
Preserve identidade, grants, sidecars commitados e provas de cleanup.

## Bootstrap e evidência

O bootstrap de apresentação permanece obrigatório e local ao GWD. Siga a seção
“Apresentação local obrigatória” do protocolo de sessão; não duplique nem resuma a
referência upstream. Nova sessão e compactação exigem carga atual, salvo suspensão
humana comprovada na mesma sessão. Não crie cache persistente de autoridade.
`CHAIN-STALE` exige cadeia sucessora mesmo com artefatos idênticos. Reaproveite os
artefatos válidos, nunca invente execução ou aceite. Durante implementação, checks
focados; início e verificação final executam a suíte completa. Gates que exigem nova
execução continuam obrigatórios. Não há cache persistente de testes.
