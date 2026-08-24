# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Classe de execução por etapa
- module-kind: platform
- responsibility: Declarar, de forma congelada e revisável, qual etapa admite executor-leader e qual exige worker despachado
- boundary: Tabela ao lado das sequências canônicas
- depends-on: none

### DU-001 — Tabela de classe e sua recusa
- development-type: platform-devops
- phase: FASE-001
- scope-in: Tabela literal congelada; recusa nomeada para etapa sem entrada
- scope-out: Alteração da ordem canônica das etapas
- depends-on: none
- acceptance: Toda etapa da sequência tem classe declarada; etapa sem entrada falha fechado nomeando a classe ausente

## MOD-002 — Emissão da cadeia
- module-kind: platform
- responsibility: Montar os quatro elos a partir do estado conhecido e selar o digest do artefato
- boundary: Emissor e sua fronteira de leitura
- depends-on: MOD-001

### DU-002 — Emissor e âncora no artefato
- development-type: platform-devops
- phase: FASE-001
- scope-in: Concessão de lease ao leader; montagem dos quatro elos; leitura segura do artefato e selagem do digest; recusa nomeada para artefato ausente, ilegível ou fora do projeto
- scope-out: Proveniência criptográfica e rastro de runtime
- depends-on: DU-001
- acceptance: Uma etapa conduzida pelo leader conclui por checkpoint sem que nenhum campo seja inventado; artefato alterado após a emissão quebra a correlação

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
