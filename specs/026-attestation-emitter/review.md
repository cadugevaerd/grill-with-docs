## Review Report

Verdict: REQUEST CHANGES
Source fingerprint: tree a6c7f79dc2b862b04d909fe79f57bb732553e1dfa4bffb29422c605ae9863547 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan e85a29cc44e7edce7be4b8c54c443bc09926e651d02078c019bafd1fb68de8b5

**Não casa com o fingerprint do Verify** (`tree b4d0abfed96c…`). A causa não é
mudança no que foi revisado, e está descrita em **Important #3** — é achado, não
apenas obstáculo. As três correções abaixo mudam a fonte de qualquer modo, então
converge/verify precisam rodar de novo depois delas.

Escopo revisado: `grill_core/attestation.py` (`mint_chain` com `supersedes_*`,
`supersede_step_execution`), `grill_workspace.py` (`attest --supersedes`,
`checkpoint --supersedes-attestation`, `verify_supersession`,
`mark_chain_stale`, gate `CHAIN-STALE`), os dois validadores, ADR-0205, bump.

### Test Quality

Boa. As três barreiras têm teste, o round-trip real `attest → checkpoint` roda
num projeto temporário de verdade (não em mock), e
`test_a_supersession_needs_the_bundle_this_item_actually_accepted` inclui a
asserção de que a fixture de fato difere — sem ela o teste passaria por acidente.
A consolidação da Phase 6 removeu a duplicação sem perder cobertura.

Uma lacuna: a cascata de `chain_stale` só é testada em unidade
(`StaleChainLedger`), nunca pelo CLI. Nenhum teste prova que superseder uma
etapa do meio marca as posteriores no `state.json` real. É observável — a
cascata deste work item exercitou o caminho oito vezes — mas não travado.

### Runtime Correctness

O núcleo está correto no que se propõe. `supersede_step_execution` valida os dois
receipts antes de comparar, então nenhum campo forjado sobrevive à comparação —
foi o que derrubou duas asserções ingênuas durante a implementação, e é o
comportamento certo.

A regra de mudança olhar o par (artefato, predecessor) está certa e é sutil: só o
artefato proibiria a re-atestação a jusante, que re-atesta com bytes idênticos.

Dois defeitos reais abaixo.

### Readability

Clara. As docstrings dizem por que, não o quê, e `require_emission_allowed`
explica o erro que corrigiu em vez de escondê-lo. `verify_supersession` tem dez
parâmetros — no limite, mas cada um é usado e nomeado.

### Architecture

Direção de dependência correta: `supersede_step_execution` é puro e não conhece
sequência nem estado; quem mantém o ledger é o CLI, que é quem sabe a ordem. A
docstring declara essa fronteira explicitamente em vez de deixá-la implícita.

Cunhar e aceitar continuam separados, e a supersessão respeita isso.

### Security

O ponto sensível é **Important #1**: a prova de que o bundle substituído é o
aceito não pina a identidade da execução.

### Performance

Sem preocupação. `_converged_waves_exist` percorre runs e waves a cada `attest` —
custo trivial. `verify_supersession` lê o bundle sucessor duas vezes (uma dentro
de `verify_checkpoint_attestation`, outra direto); é I/O de um arquivo pequeno,
mas é leitura duplicada sem motivo.

### Critical Issues

Nenhum.

### Important Issues

**#1 — A ligação com o bundle substituído não pina a identidade da execução**
`grill_workspace.py`, `verify_supersession`: a prova de que o bundle é "aquele
que o work item aceitou" compara `step_id`, `output_sha256` e
`skill_invocation_receipt_ref` contra o que o estado gravou. Nenhum dos três
depende de `step_execution_id`.

Verificado: dois `build_chain` para a mesma etapa e o mesmo artefato, diferindo
apenas em `wave_index`, produzem `output_sha256` e `receipt_ref` **idênticos** e
`step_execution_id` **diferentes** (`se-26c78b33317f…` vs `se-b0780e7224c8…`).
Um bundle assim passa na verificação.

Consequência: `superseded_outputs[step]` grava um `step_execution_id` que nunca
foi o receipt corrente, e o sucessor é ligado a essa execução fantasma. Não
derruba o gate — o sucessor ainda precisa julgar válido e ancorar no artefato —
mas corrompe exatamente a trilha de auditoria que a feature existe para tornar
confiável. FR-024 pede que o registro substituído seja "aquele que o item de
trabalho de fato aceitou"; a identidade da execução é parte disso.

*Correção*: gravar `development.attested_executions[step] = step_execution_id` na
aceitação e compará-lo em `verify_supersession`. Para itens cujo estado é
anterior ao campo, cair de volta no par atual — degradação declarada, e toda
aceitação nova passa a pinar.

**#2 — `phase-turn` não limpa `chain_stale`**
`grill_workspace.py`, `phase_turn_command`: a virada de fase reescreve `steps`,
`current_step` e `execution_branch`, e não toca em `chain_stale`. Uma fase virada
com o ledger não vazio carrega para a fase seguinte uma lista que nomeia etapas
de receipts que já não valem para ela, e `ship` da fase nova recusa com
`CHAIN-STALE` sobre pendência que não é dela. Como `phase-turn` é o caminho
normal entre fases deste repositório, é alcançável sem nada de anormal.

*Correção*: decidir e implementar o que a virada faz com o ledger — limpá-lo
junto com a matriz, ou recusar a virada enquanto não estiver vazio. A segunda é
mais severa e provavelmente mais correta: virar fase deixando cadeia
inverificável para trás é o que o ledger existe para impedir.

**#3 — `.grill/attestations/**` fora de `fingerprint_exclude`**
`.specify/extensions/verify-review-ship/verify-review-ship-config.yml:4-9`
exclui `state.json` e `ROUND-LOG.jsonl` do work item, e não os bundles de
atestação. Sob o protocolo grill, fechar uma etapa de gate escreve um bundle em
`.grill/attestations/`, que conta como fonte revisada — então **fechar `verify`
invalida o relatório do próprio `verify`**, e o mesmo aconteceria com `review`.
É um laço: rodar de novo produz um bundle novo e volta a invalidar.

Esta entrega torna o problema rotineiro (27 bundles no diff), então é achado
dela. O `state.json` já está excluído pelo mesmo raciocínio; o bundle ficou de
fora.

*Correção*: acrescentar `.grill/attestations/**` a `converge.fingerprint_exclude`.
Um receipt de gate é evidência **sobre** a revisão, não conteúdo revisado — a
mesma razão pela qual `verify.md` está excluído.

### Constitution References (only for discovered conflicts)

**Rastreabilidade** ("receipts e gates MUST ser rastreáveis ao work item e ao
commit"): Important #1 conflita — uma trilha que pode nomear uma execução que
nunca existiu não é rastreável no sentido que a cláusula exige.

### Final Recommendation

- REQUEST CHANGES: corrigir #1, #2 e #3, rodar `/speckit.converge`, depois
  verify e review de novo.
