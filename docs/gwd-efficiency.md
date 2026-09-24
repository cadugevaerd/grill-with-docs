# GWD 7.0.0 — eficiência do workflow v5

## Identidade e autorização

- Trabalho: `gwd-efficiency-v5`; branch `codex/gwd-efficiency-v5`.
- Origem: `af0d435`; implementação pelo assistente a pedido do usuário.
- Autorização: implementação direta do plano aprovado, sem percorrer o ciclo GWD desta entrega.
- Não foram criados receipts ou checkpoints simulando etapas. Constituição e WORKFLOW.md deste repositório permanecem preservados. Publicação manual da versão 7.0.0 foi autorizada posteriormente, sem GitHub Actions. Não há migração automática de trabalhos ativos.

## Decisões e comportamento

O workflow v5 conserva as onze etapas e seleciona a policy v2. Plan e review exigem revisão independente; risco material exige revisão extra. Novas decisões de COMO continuam exigindo autoria especializada. A revisão final deve incluir todos os autores especializados aceitos no item, e permanece independente deles.

A classificação de cada etapa é um arquivo em `.grill/work-items/<id>/step-inputs/<step>.json`. Declara schema `grill-step-assessment/v1`, step, new_how booleano, risks, justification e files com path/sha256 das fontes. O core verifica formato, fontes e correspondência com a atividade; não interpreta linguagem natural nem comprova por si que o operador declarou todos os riscos. Cada input manifest de atividade carrega assessment_sha256 canônico. No v5, o input_fingerprint do receipt também inclui esse digest; o checkpoint o compara com a classificação corrente, mesmo quando não há atividade especializada obrigatória. Fontes alteradas ou classificação divergente exigem revalidação, inclusive no caminho direto de checkpoint/attest.

Dois grupos são o padrão v5; `--groups` explícito prevalece. O algoritmo existente continua determinístico, mantém conflitos de arquivos no mesmo nó e fases como barreiras. O worker executa o nó inteiro com resultados individuais por tarefa. Import/rebase existentes recuperam resultados aceitos; a mudança inclui orientação explícita de recuperação antes do despacho, sem novo scheduler.

A entrevista v5 admite três perguntas independentes por lote. Cada DQ respondida gera uma linha com round_id próprio, question_id, transition, batch, question_run e batch_questions. Resposta parcial não inventa decisões. O auditor verifica lotes coerentes e o limite de 25 perguntas apresentadas por sessão; dependência semântica entre perguntas continua sendo julgamento do autor.

A resolução em lote valida os bytes do registry uma vez por chamada. O default de confiança segue a versão do registry fornecido. Receipts históricos sem registry explícito só podem selecionar um dos assets distribuídos pelo digest exato. Nenhum cache persiste entre chamadas. A leitura da apresentação resolve os executáveis uma vez por passagem; preserva observações inicial/final, validação da referência e compactação.

Skill e protocolo de entrada foram reduzidos. Os manuais completos ficam em referências carregadas antes da operação correspondente. CHAIN-STALE continua exigindo cadeia sucessora; não há invalidação semântica geral nem cache persistente de testes.

## Compatibilidade

Assets, tabelas e policies v3/v4 permanecem preservados; o leitor reconhece v5 adicionalmente. Documentos v4 humanos sem marcador continuam vinculados ao registry v4. Novos projetos inicializam v5; projetos existentes conservam seu documento. Não há migrate-v5 nem migração automática. A Constituição gerenciada não muda, pois a sequência de onze etapas permanece.

Na invocação v5, o suplemento instrui partition a não executar migrate-v4 e a consumir os paths revisionados emitidos pelo core. As instruções históricas continuam disponíveis para as versões originais.

## Evidência de desempenho

Comando reproduzível: `python3 tests/benchmark_efficiency.py`. Cinco repetições, baseline `af0d435`, dados sintéticos, stdlib e nenhuma sessão real de modelo.

| Cenário | Antes | Depois |
|---|---:|---:|
| Resolver as onze skills, mediana | 9,744 ms | 5,905 ms |
| Validações do registry por resolução em lote | 11 | 1 |
| Passagem de apresentação com 500 resultados, mediana | 7,462 ms | 3,251 ms |
| Resoluções de executável nessa passagem | 500 | 1 |
| Seis tarefas independentes: nós de worker | 3 | 2 |
| Retomada com duas tarefas aceitas: tarefas repetidas | 0 | 0 |
| Contexto inicial: skill + protocolo + suplemento | 76.510 bytes | 16.596 bytes |

Os manuais sob demanda, a policy JSON e a referência upstream não estão incluídos na contagem de contexto. Os tempos não medem abertura de modelos, espera humana, persistência do workflow completo ou transporte nativo. O número de etapas com revisão fixa cai de sete para duas por contrato; o ganho total em minutos exige observação live. Menos workers reduz coordenação, mas pode aumentar o tempo de implementação de tarefas demoradas; o teto explícito permite ajustar isso.

## Validação

A suíte inicial do código original encontrou duas falhas preexistentes em validate_partition_contract.py: o corpus passou a conter DAG v2, mas o teste exigia parallel no relatório e não contabilizava tarefas read-only. O teste agora lê parallel no DAG e contabiliza todas as categorias, sem filtrar o corpus ou alterar grants.

Os testes v5 cobrem bootstrap, catálogos dos dois runtimes, preservação de v4 sem marcador, duas revisões fixas, exceções, hashes de classificação, fontes stale, omissão de autores, respostas parciais, limites por sessão e agrupamento com Result individual. Há um cenário público de init → step-enter → checkpoint com recusa após mudança de risco, além de um round-trip de receipt que rejeita classificação alterada sem introduzir risco novo. As fixtures Gauntlet materializam o documento v5 na preparação; não pressupõem um comando migrate-v5.

Revisão independente: GO após correções de seleção de versão sem marcador, omissão de autores na revisão final e vínculo do receipt à classificação. Testes de eficiência: 10/10. Validação interrompida a pedido do usuário antes do término do último validador; não há resultado verde da suíte completa. Os contratos de eficiência (10/10), registry (111/111 após o ajuste de higiene), ativação (45/45), convergência (53/53), runs (23/23), scheduler (53/53), particionamento (48/48) e versões passaram. `git diff --check` passou. O benchmark offline foi executado em cinco repetições.
