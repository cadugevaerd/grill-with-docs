## Review Report

Verdict: APPROVE
Source fingerprint: tree 2e9de55eb4bfb23d3e6aaed57b799ef222d5f6a49c7129ff7bcaa5c9c62bd152 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan a25ae1d5c7f5ac13aa567321acb26c067bd5a534553884523cff7d504d7c2ea6

### Limitação de independência

A mesma das duas fases anteriores: sem revisor independente. Registrado.

### Test Quality

1000 para 1007 testes. O número esconde o trabalho real: 34 pontos de criação em 14 validadores precisaram declarar `--skip-backlog`. Esse diff **é** a prova de que o pré-requisito passou a valer — antes, nenhum deles precisava dizer nada.

Dois testes existentes fizeram trabalho de revisor melhor que qualquer teste novo:

- `test_migration_only_touches_the_metadata_document` pegou o carimbo escrito fora de `initial_artifacts`. Sem ele, todo bundle criado pela saída reprovaria o próprio gate de integridade, e nada nos testes novos olhava para isso.
- Os 52 fixtures que quebraram foram o que revelou que FR-007 era forte demais.

A cobertura nova tem sete casos e cobre recusa, saída, carimbo dentro do pino, visibilidade na auditoria e recusa da adoção sem vínculo.

Lacuna reconhecida: não há teste do caminho feliz da adoção — vincular, adotar, carimbo sumir — porque montá-lo exige um backlog real. É a mesma restrição que rege toda a fase, e SC-005 fica verificado apenas pela metade que não precisa do binário.

### Runtime Correctness

Duas correções de desenho, ambas descobertas pela execução e não por inspeção.

A primeira é sobre ordem: o carimbo era gravado depois de o bundle ser publicado, logo fora do conjunto de hashes que define a integridade. A correção move a gravação para antes da fixação do pino, o que também é conceitualmente mais correto — o carimbo descreve como o bundle nasceu, então pertence ao seu estado inicial.

A segunda é sobre força: exigir que o carimbo bloqueasse aprovação tornaria inauditável todo bundle criado em ambiente sem backlog, incluindo a matriz inteira de CI. Trocar bloqueio por relato preserva o que a cláusula constitucional realmente exige — ausência de waiver **implícito** — sem criar uma falha maior.

`backlog-adopt` fecha o buraco que a saída abriria. Sem ele, um work item criado sem backlog nunca mais alcançaria o estado limpo, mesmo depois de vinculado. Ele exige vínculo presente, então não é um apagador silencioso.

### Readability

`initial_files` ganhou um parâmetro nomeado com valor padrão, o que mantém todos os chamadores existentes intactos. O comentário explica por que a gravação precisa acontecer ali e não depois — a informação que economiza a próxima pessoa de repetir o defeito.

`grill_workspace.py` continua grande. Não piorou de forma relevante nesta fase, mas segue como o arquivo mais pesado do plugin.

### Architecture

A mudança é pequena em código e grande em contrato. A parte arquitetural que vale registrar é a escolha de não criar mecanismo novo: o carimbo mora ao lado de `decision_backlog_mode` no `state.json`, e ambos respondem à mesma pergunta — como este bundle foi produzido.

### Security

Nenhum segredo. A superfície de processo não mudou. O carimbo é um booleano em arquivo já versionado, sem conteúdo sensível.

Observação: a saída é uma flag de linha de comando, portanto trivialmente acionável por quem já executa o plugin. Ela não é um controle de segurança e não é apresentada como tal — é um registro de proveniência.

### Performance

Sem impacto.

### Critical Issues

Nenhum.

### Important Issues

Nenhum remanescente.

### Constitution References

- **Fail-closed sem waiver** — é o tema da fase e foi o que forçou a reformulação de FR-007. A leitura aplicada: a cláusula proíbe waiver implícito, e uma saída nomeada, versionada e sempre reportada não é implícita. Bloquear seria mais rígido e produziria uma falha maior.
- **Evidência antes de afirmação** — o carimbo existe para que um bundle não afirme conformidade com um pré-requisito que contornou.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`

Ressalvas: sem revisor independente; SC-006 pendente da matriz de CI; caminho feliz da adoção sem cobertura automatizada, por depender de backlog real.

---

## Correção posterior — a independência existiu

Este relatório afirmou que o revisor independente não retornou. **Isso ficou falso.** Ele retornou depois, com três rodadas de revisão, e a afirmação de ausência de independência estava errada em todos os relatórios desta milestone.

O que ele encontrou, e que a revisão do autor não tinha encontrado:

- **Duas classes `DeferredParsing` com o mesmo nome** em `tests/validate_backlog_contract.py`. A segunda sobrescrevia a primeira no namespace do módulo, deixando dois testes mortos. Um deles, `test_only_open_blocks_are_mirrored`, afirmava o filtro `state: open` que a FASE-001 removeu de propósito — provado por execução direta: o teste esperava `['BL-0001']` e o código atual devolve `['BL-0001', 'BL-0002']`. Ele **reprovaria** se rodasse. A suíte reportava verde escondendo 2 de 101 métodos.
- **`StubToolchain.mutations()` não contava `item transition`**, então um `assertEqual(mutations(), [])` diria "nada mutou" com uma transição real emitida. Nenhum teste passava pelo motivo errado hoje, mas o helper é reaproveitável e a armadilha era real.
- **Docstring de `backlog_sync_command`** ainda dizia "the open BLs", contradizendo a mudança central da fase.
- **Visibilidade de `STATE-UNKNOWN`**: uma decisão pulada por estado inválido saía com `verdict: PREVIEW` e exit 0. Quem lê só o código de saída não veria a omissão.

Os quatro foram corrigidos. Os demais achados dele — divergência entre os dois parsers, relato de falha parcial, coerção de estado desconhecido — já tinham sido corrigidos em fases posteriores ao commit que ele revisou.

Vale registrar o que isso mostra: a revisão do autor encontrou 16 defeitos e ainda assim deixou passar um teste morto que contradizia a própria correção que a fase entregou. A independência não era formalidade.
