# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Publicação do plugin nos marketplaces
- module-kind: platform
- responsibility: Manter a versão e o conteúdo servidos pelos marketplaces iguais aos do repositório canônico
- boundary: Pipeline do repositório canônico e as cópias vendorizadas em claude-skills e codex-skills
- depends-on: none

### DU-001 — Gate de bump
- development-type: platform-devops
- phase: FASE-001
- scope-in: Reprovar pull request que altere o conteúdo do plugin sem subir a versão
- scope-out: Qualquer escrita fora do repositório canônico
- depends-on: none
- acceptance: Os quatro cenários de bump distinguidos pelo CI, com mensagem de falha que nomeia a versão declarada

### DU-002 — Publicação fan-out
- development-type: platform-devops
- phase: FASE-002
- scope-in: Espelhar plugin/ e README para os dois marketplaces e sincronizar a versão na entrada de cada um
- scope-out: Reconciliação do atraso já existente e mudanças no formato de marketplace
- depends-on: DU-001
- acceptance: Após merge que toque plugin/, os dois destinos declaram a versão do canônico e não contêm testes

### DU-003 — Reconciliação do atraso
- development-type: platform-devops
- phase: FASE-003
- scope-in: Gatilho manual e execução única que leva a versão corrente aos dois marketplaces
- scope-out: Republicação de versões históricas
- depends-on: DU-002
- acceptance: Os dois destinos servindo a versão corrente e o gatilho manual permanecendo disponível

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
