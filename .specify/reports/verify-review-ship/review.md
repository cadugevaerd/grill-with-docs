## Review Report

Verdict: APPROVE
Source fingerprint: tree 0127089e64cdb59ced08016a8464adc504ea2fc012e498b40a703d678e741089 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 6829dc3378c82021c96bb05a0702e41a6686a247a788c6f8495e4b3a3828edb2

Casa exatamente com Converge (décima passada, `converged`) e Verify (`PASS`,
terceira rodada). A primeira rodada de review devolveu `REQUEST CHANGES` com
três achados Important, e os três estão corrigidos e travados por teste.

Esta é a segunda rodada, reemitida: durante ela corrigi um comentário enganoso
em `verify_supersession`, o que moveu a fonte e obrigou converge e verify a
rodarem de novo antes de o veredito valer. O achado está registrado abaixo, em
Readability.

### Test Quality

Cobertura sólida e adversarial onde importa. Cada barreira nova tem um teste que
prova a barreira **e** um que prova que ela destrava na própria condição —
`test_a_phase_turns_once_the_stale_chain_is_cleared` e
`test_ship_is_not_blocked_once_the_stale_ledger_is_empty` existem porque um gate
que não destrava é tão defeituoso quanto um que não trava.

`test_a_supersession_needs_the_execution_that_was_accepted` assere primeiro que
a fixture de fato difere só na execução. Sem isso passaria por acidente, que é o
modo silencioso de um teste de segurança falhar.

O round-trip `attest → checkpoint` roda num projeto temporário real, não em
mock, e verifica o histórico gravado — âncora, execução, razão e a execução que
substituiu.

### Runtime Correctness

As três correções fazem o que dizem, verificado no estado deste work item: nove
etapas aceitas, nove execuções pinadas, nenhuma no caminho de fallback.

A degradação para receipts anteriores ao campo é explícita e limitada — cai no
par, e toda aceitação nova pina. Não é buraco deixado aberto, é migração sem
migração de dados.

O gate `CHAIN-STALE` na virada de fase está no lugar certo do fluxo: depois da
idempotência e de `PHASE-INCOMPLETE`, antes de qualquer escrita, e o teste
confirma que a recusa não reinicia a matriz.

### Readability

Boa. Um defeito encontrado e corrigido nesta revisão: o comentário acima da
verificação do par ainda dizia que ele "é a única coisa aqui que quem chama não
consegue restatar" — falso depois da correção, e falso justamente sobre a
propriedade de segurança da função, seis linhas acima do código que prova o
contrário. Reescrito para dizer que nenhuma das duas metades basta sozinha e
por quê.

### Architecture

Fronteira preservada: `supersede_step_execution` continua puro e sem conhecer
sequência nem estado; quem mantém o ledger é o CLI, que é quem sabe a ordem. A
correção #1 respeitou isso — o pino da execução é estado, e ficou no CLI.

`verify_checkpoint_attestation` passou a devolver `step_execution_id` junto do
veredito em vez de o chamador reabrir o bundle. É a informação viajando pelo
caminho por onde a decisão já viajava.

### Security

O ponto que motivou a rodada está fechado. A prova de que o bundle substituído é
o aceito passou a cobrir a identidade da execução, e o teste demonstra o ataque
concreto que antes passava: duas cadeias da mesma etapa e do mesmo artefato,
diferindo só no índice de onda, com digest e receipt ref idênticos.

Continua valendo — e está declarado em SKILL.md e no contrato — que a cadeia
prova correlação estrutural, não que a skill registrada rodou. Proveniência
criptográfica segue fora de escopo por decisão, não por omissão.

### Performance

Sem preocupação. Nada no caminho quente; as leituras são de arquivos pequenos.

### Critical Issues

Nenhum.

### Important Issues

Nenhum pendente. Os três da rodada anterior estão corrigidos:

1. A ligação com o bundle substituído pina a execução (`attested_executions`).
2. A virada de fase recusa com `CHAIN-STALE`.
3. `.grill/attestations/**` saiu do fingerprint — verificável nesta rodada, em
   que escrever o relatório e fechar a etapa deixaram `tree` e `work` imóveis.

### Nits (não bloqueiam)

- Este relatório teve de ser reemitido porque o conserto do comentário mudou a
  fonte no meio da revisão. Um review que corrige o que encontra deixa de ser
  read-only, e a consequência é um ciclo inteiro de gates. Vale como aviso de
  processo: achado de leitura devia sair como achado, e a correção entrar na
  rodada seguinte.

- `attestation.supersede_step_execution({}, prior, successor)` passa um store
  descartável: a imutabilidade que `record_step_execution` garante vale só
  dentro daquela chamada. Na prática o guarda durável é o trio verificado e o
  histórico append-only, e a função está sendo usada como validador. Funciona,
  mas o parâmetro sugere uma persistência que ali não existe.
- `phase_turn_command` checa idempotência (matriz inteira em `pending`) antes do
  gate de `chain_stale`. Um item que tenha virado a fase **antes** de o gate
  existir, com o ledger sujo, ainda devolveria `REUSED` em silêncio. Borda
  legada; não alcançável por fluxo normal daqui em diante.
- `payload["chain_stale"]` é atribuído depois de `audit.append(payload)`, então
  o registro de auditoria recebe o campo por referência. É o que se quer — a
  trilha grava a cascata —, mas depende de aliasing em vez de dizê-lo.

### Constitution References (only for discovered conflicts)

Nenhum conflito. O de **Rastreabilidade** citado na rodada anterior está
resolvido: a trilha não pode mais nomear uma execução que nunca existiu.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`

`ship` continua sendo parada obrigatória com autorização humana explícita: ele
faz merge, push direto para `main` e dispara a publicação nos marketplaces.
