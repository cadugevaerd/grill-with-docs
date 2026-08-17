## Review Report

Verdict: APPROVE
Source fingerprint: tree b6869e1acbeb24efeb1da207034fd30eeebefdeb3a36696ebb1e5542e1df372b / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan f974821ff7029fc9c7234fcc457c106f5032f23cbb12bf2950752fb99df14d2d

### Limitação de independência

A mesma da FASE-001, e ela persiste: não houve revisor independente. Esta revisão é do próprio autor da mudança. Registrado, não dissimulado.

### Test Quality

54 para 82 testes no validador da ponte; suíte de 972 para 1000. Verde com e sem `backlogctl`.

Dois testes valem mais que os outros porque provam comportamento contra a realidade e não contra a intenção. `ParserAgreement` compara os dois leitores nas cinco variantes de cabeçalho e teria reprovado o código anterior em quatro delas. `test_a_failed_write_leaves_the_previous_record_intact` injeta falha no meio da escrita e exige que o registro anterior sobreviva — atomicidade provada, não afirmada.

Ponto fraco reconhecido: `audit_findings` reconstrói a condição do gate em vez de invocar o auditor inteiro, porque alcançar aquele ponto pelo caminho completo exige um bundle válido inteiro. O teste prova a regra, não a fiação. A fiação é coberta indiretamente pelos nove testes de `validate_contract.py` que reprovaram quando a condição estava errada.

### Runtime Correctness

Um defeito de ordenação encontrado e corrigido durante a execução: exigir a marca de origem sem condição reprovou nove testes, porque todo bundle existente é não-marcado e a migração só chega na FASE-004. Não era bug de implementação, era sequência errada no próprio ROADMAP. A exigência passou a ser condicional a `decision_backlog_mode: projected`, declarado ao aplicar a projeção. Efeito colateral bom: o gate liga sozinho conforme cada bundle migra, o que dispensa a FASE-004 de ligá-lo separadamente.

Determinismo: ordenação por identificador, sem relógio, sem caminho absoluto, sem ordem de dicionário na saída. Verificado por teste que embaralha a resposta da autoridade e exige o mesmo arquivo.

Marca de origem: cobre a fatia do work item e ignora `item_status` no cálculo, para não duplicar o que o estado já expressa. Teste prova que decisão de outro work item não a move.

Escrita atômica: staging mais `replace`, o mesmo padrão da criação do bundle. `Path.replace` é atômico no mesmo sistema de arquivos nos três sistemas da matriz, e o staging fica ao lado do alvo, então não cruza sistema de arquivos.

### Readability

`render_projection`, `authority_mark` e `compare_projection` são funções pequenas com responsabilidade única. Os comentários explicam as decisões não óbvias — por que `revision` não serve de marca, por que a exigência é condicional, por que `state` vem do status.

`backlog_bridge.py` passou de 226 para cerca de 390 linhas e hoje abriga ponte, projeção e verificação. Ainda coeso, porque os três compartilham o vocabulário de estados, mas é o limite. Se a FASE-004 acrescentar migração ao mesmo arquivo, extrair a projeção para módulo próprio deixa de ser opcional. Registrado como observação, não como bloqueio.

### Architecture

A eliminação do segundo parser é a melhoria estrutural da fase: a divergência entre leitores deixou de ser um bug corrigido e passou a ser um estado irrepresentável, porque só existe um leitor.

Direção de dependência preservada: a ponte fala apenas o contrato público; o auditor não ganhou dependência externa alguma e continua offline, que era a exigência de ADR-0002.

### Security

Nenhum segredo no diff. O registro gerado não interpola conteúdo em shell; nada é executado a partir dele. A marca é SHA-256 sobre JSON canônico, usada para detecção de divergência e não como controle de acesso — não há afirmação de segurança embutida nela.

Risco residual: o conteúdo da descrição do item entra no registro versionado. Quem escreve uma decisão controla o que vai para o arquivo. É o mesmo nível de confiança de qualquer artefato do work item, e não muda com esta fase.

### Performance

Irrelevante na escala real. Uma listagem por execução, mais renderização linear no número de decisões.

### Critical Issues

Nenhum.

### Important Issues

Nenhum remanescente.

### Constitution References

- **Fail-closed sem waiver** — a exigência condicional poderia parecer afrouxamento. Não é: sem condição, o gate reprovaria trabalho legítimo que não tem caminho de migração, o que é falha por construção e não rigor. A condição é explícita, gravada no bundle e verificável.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`

Ressalvas: independência do revisor não obtida; SC-008 pendente da matriz de CI.

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
