## Review Report

Verdict: APPROVE
Source fingerprint: tree 422766057daecf81feb2cd3a77fdbee1a2bc08d66dd9e3378617a8735367f33d / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan c84eb5f54d0f1e06985ecd030da53d0b60862cb2e4a4ba9e13fc9bb12b0a179f

### Limitação de independência

Sem revisor independente, como nas fases anteriores.

### Test Quality

Nove casos cobrindo detecção de modo, prévia sem mutação, semeadura de estado histórico, conversão para projeção marcada, contraparte já existente, bundle já projetado, estado inválido, bundle vazio e repositório sem vínculo.

O caso mais valioso é o do estado inválido, porque fixa a decisão de recusar o bundle inteiro. Sem ele, uma refatoração futura poderia "melhorar" o comportamento pulando a decisão problemática, que é exatamente o que não se quer.

Lacuna reconhecida: não há teste de interrupção no meio da migração. A convergência por reexecução é garantida pela deduplicação já coberta em outra classe, mas o caminho específico não é exercitado.

### Runtime Correctness

A semeadura usa `--status` no `add`, que é snapshot inicial e não transição — a mesma propriedade medida na FASE-001 e que permite um item nascer já encerrado. Sem ela, `open → done` seria ilegal e a migração precisaria de dois passos por decisão.

A regeneração da projeção acontece **depois** da criação das contrapartes, dentro do mesmo `--apply`. A ordem importa: projetar antes produziria um registro sem as decisões recém-criadas.

A recusa por bundle autoral em `backlog-project` fecha o buraco óbvio: sem ela, projetar um bundle autoral geraria um registro vazio, descartando em silêncio tudo que estava escrito à mão.

### Readability

`migrate` é linear e longa, mas cada bloco é uma decisão nomeada. Os comentários explicam as duas escolhas não óbvias — por que a recusa é do bundle inteiro e por que `--status` funciona.

`backlog_bridge.py` agora passa de 500 linhas e abriga ponte, projeção, verificação e migração. A observação da FASE-002 se confirmou: era o limite, e foi ultrapassado. Extrair projeção e migração para módulo próprio é dívida registrada, não bloqueio desta fase.

### Architecture

Reusar a ausência da marca como sinal de modo evitou um campo de estado novo e, com ele, um caminho de sincronização a mais que poderia divergir. É a mesma disciplina que eliminou o segundo parser na FASE-002.

### Security

A migração cria itens no backlog do operador, compartilhado entre repositórios. Mitigações: prévia por padrão, autorização explícita, escopo de um work item por execução, e deduplicação que impede reexecução de poluir.

### Performance

Uma listagem mais uma criação por decisão ausente. Irrelevante na escala real.

### Critical Issues

Nenhum.

### Important Issues

Nenhum. Uma dívida registrada: o tamanho de `backlog_bridge.py`.

### Constitution References

Nenhum conflito descoberto.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`

Ressalvas: sem revisor independente; SC-006 pendente do CI; migração dos bundles reais preparada e não aplicada, por exigir confirmação do operador.

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
