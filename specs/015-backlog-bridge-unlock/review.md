## Review Report

Verdict: APPROVE
Source fingerprint: tree 7044396efb54fae2818353cffc74a50048d03d7760dd40f6141f1ede12801005 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan ac49cbc2c8496efb1077406d34bb3fae1f195f05f27c0d28360967c402f16c68
                    (matches Converge e Verify; computado por `.specify/extensions/verify-review-ship/scripts/source-fingerprint.sh`)

### Limitação de independência

Um revisor independente foi despachado no início desta revisão e **não retornou** dentro da sessão. Duas mensagens pedindo resultado parcial ficaram sem resposta. Portanto esta revisão apoia-se na passagem adversarial conduzida pelo próprio autor da mudança, o que é uma independência mais fraca do que o gate pretende. Fica registrado como ressalva, não dissimulado.

A passagem encontrou quatro defeitos reais, todos corrigidos antes deste veredito. Isso é evidência de que a passagem não foi complacente, mas não substitui um segundo par de olhos.

### Test Quality

Cobertura saiu de 22 para 54 testes no validador da ponte; a suíte completa saiu de 940 para 972. A razão entre teste e produção é 348 linhas contra 144.

O ponto mais forte: a suíte foi executada **com e sem** `backlogctl` presente, e passa idêntica nos dois casos. Isso não era verdade no meio da revisão, e foi o primeiro defeito encontrado.

Testes que passavam pelo motivo errado foram eliminados. `test_the_artifact_gate_still_guards_commands_that_need_it` começou como asserção fim-a-fim sobre `audit`, que alcançava `CHECK-NOT-APPROVED` e depois `ARTIFACT-INVALID` antes do gate pretendido — passaria sem provar nada sobre a integridade. Foi trocado por exercício direto do gate mais uma asserção estrutural de que ele continua ligado nos três comandos que o exigem.

### Runtime Correctness

Quatro defeitos encontrados e corrigidos:

1. **`backlog_bridge.py:295` e `grill_workspace.py:1156`** — o envelope `BACKLOG-UNAVAILABLE` não trazia `db`. Em qualquer máquina sem `backlogctl`, isto é, a matriz de CI inteira, `test_the_subcommand_accepts_an_alternate_store` falharia. Era a mesma dependência de ambiente que T027 existia para eliminar, reintroduzida pela própria correção. Corrigido com `store_path`, resolvido antes de qualquer coisa poder falhar, e presente em todo envelope.
2. **`backlog_bridge.py:226`** — `STATE_TARGET.get(state, DEFAULT)` coagia estado não reconhecido para `open`. Cenário: `- state: resolvd` cria item `in_progress`, relatando como em curso uma decisão já resolvida. A ponte pode rodar sobre bundle que a auditoria não vetou, então não pode presumir vocabulário válido. Agora recusa com `STATE-UNKNOWN`, sem mutar, nomeando o valor ofensor.
3. **`backlog_bridge.py:204`** — `describe()` copiava `state` para a descrição do item. A transição posterior move o `status` e nunca reescreve o texto, então a descrição passava a afirmar `open` num item já `done`. O artefato que serve de evidência do vínculo mentia sobre o próprio estado. `state` saiu da descrição; o `status` do item é a autoridade, por ADR-0001.
4. **`backlog_bridge.py:258`** — exceção no meio do laço de aplicação escapava, e o operador recebia recusa nua embora itens anteriores já tivessem sido criados. Mesma classe do SGD-14. Agora a falha para a escrita e viaja com o relato: `FAILED` na que quebrou, `SKIPPED` nas não tentadas, `changed` dizendo se algo foi escrito.

Transições: a tabela foi medida empiricamente nos 25 pares, não inferida. `open → done` ilegal é o fato que sustenta o desenho. O caminho `TRANSITION-REFUSED` foi observado em dado real do repositório antes de virar teste: `SGD-3` está `open` enquanto `BL-0001` está `resolved`.

Ordem de operações: o conjunto de propostas é calculado antes da primeira mutação, então recusa de vínculo, de identidade ou de disponibilidade ocorre com o backlog intacto.

### Readability

Comentários explicam o **porquê** nos pontos não óbvios — por que o item nasce `in_progress`, por que `state` não entra na descrição, por que estado desconhecido recusa. Nenhum comentário narra o que o código já diz.

`sync_items` cresceu e hoje concentra resolução, indexação, classificação e aplicação. Ainda é linear e legível, mas é o candidato natural a extração se a FASE-002 acrescentar mais um eixo. Não é achado bloqueante.

### Architecture

A direção de dependência está correta: a ponte fala apenas `backlogctl --json`, nunca o armazenamento. `store_path`, `index_existing` e as duas tabelas de estado são unidades pequenas e testáveis. Nada em `grill_workspace.py` além do repasse de `--db` e da troca de um gate.

A troca de `validate_bundle_integrity` por `validate_metadata` **não** enfraquece garantia real: a propriedade tamper-evident vive em `immutable_sha256`, que continua verificada. O que caiu foi a exigência de que artefatos mutáveis permanecessem idênticos aos templates — exigência que era insatisfazível por construção neste comando. Um teste impede que o gate seja removido dos outros três chamadores.

### Security

Nenhum segredo no diff; varredura por padrões de token, chave privada e atribuição de senha não retornou nada. Nenhum `.env`, `.pem`, `.key`.

Superfície de processo inalterada: `shell=False` preservado. Nenhuma entrada de usuário chega a shell. O parsing dos marcadores usa `re.findall` sobre texto controlado e aplica `.strip()`, o que também neutraliza `\r` de arquivos CRLF.

Risco residual aceito e registrado: os marcadores vivem em texto livre da descrição, então um operador que edite a descrição à mão pode quebrar o vínculo. A spec declara esse caso nos Edge Cases. Não há campo estruturado disponível em `item add`, o que torna a alternativa indisponível, não preterida.

### Performance

Não aplicável em escala relevante. O número de decisões por work item é da ordem de unidades e o custo é dominado por chamadas de processo externo. `index_existing` é uma passagem linear sobre os itens do backlog; `sync_items` faz uma chamada de listagem mais uma por mutação, que é o mínimo para o contrato.

### Critical Issues

Nenhum remanescente.

### Important Issues

Nenhum remanescente. Os quatro listados em Runtime Correctness foram corrigidos e cobertos por regressão dentro desta revisão.

Item deferido, fora do escopo desta fase e já rastreado: `SGD-14` descreve o mesmo padrão de falha em `finally` no `checkpoint` e no `phase-turn` do workspace. Esta fase corrigiu a instância na ponte; as outras duas permanecem abertas no backlog operacional.

### Constitution References (only for discovered conflicts)

- **Evidência antes de afirmação** — citada por dois achados. O defeito 3 fazia um artefato de evidência afirmar um estado falso; o defeito 4 fazia uma recusa afirmar que nada acontecera quando havia acontecido. Ambos corrigidos.
- **Fail-closed sem waiver** — citada pelo defeito 2, que era fail-open silencioso sobre vocabulário desconhecido. Corrigido.

Nenhuma auditoria cláusula a cláusula foi repetida aqui; as três referências saem de achados técnicos concretos.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`

Ressalvas que acompanham a aprovação, ambas não bloqueantes e ambas declaradas:

1. A independência do revisor não foi obtida. Se houver apetite, vale um segundo par de olhos antes do merge.
2. SC-005 exige os três sistemas operacionais e só a matriz de CI verifica; permanece não verificado até a branch ser empurrada.
