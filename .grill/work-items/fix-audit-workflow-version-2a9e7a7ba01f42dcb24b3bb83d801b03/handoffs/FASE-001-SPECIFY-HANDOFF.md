# FASE-001 — Versão de workflow derivada do documento

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: marcador de workflow, campo derivado, campo constante, detector estrito, par writer/reader, versão ativa do plugin
- ADRs: ADR-0001, ADR-0002, ADR-0003
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

Ao criar um work item, o registro de estado passa a dizer qual sequência de etapas o repositório efetivamente declara, em vez de repetir um valor fixo. Quando o documento de workflow não declara exatamente uma versão gerenciada, a criação é recusada em vez de produzir um registro condenado.

Atores: quem cria um work item, e quem classifica um work item existente pela sequência que ele declara.

Cenários:

1. Repositório que preserva uma declaração de workflow anterior sob a versão corrente do plugin. O work item nasce registrando a sequência anterior, e o restante do sistema passa a julgá-lo por ela — inclusive a projeção de status, que já lê esse registro. Hoje ele nasce afirmando a sequência corrente e é julgado pela errada, com etapas que o documento dele não contém.
2. Repositório cuja declaração é a corrente — hoje a maioria. O registro continua correto, agora por derivação em vez de coincidência.
3. Repositório cujo documento de workflow não declara exatamente uma versão gerenciada — nenhuma, ou duas. A criação é recusada, nomeando o que foi encontrado e o que era esperado, e nenhum work item é criado. Hoje ele nasceria e só seria reprovado depois, longe da causa.
4. Os work items já existentes. Cada um continua sendo classificado pelo que ele próprio declara, e o veredito de todos permanece exatamente o que era. Nenhuma migração, nenhuma reescrita.

Escopo: o carimbo do campo que declara a sequência, feito na criação, e a resolução da declaração do documento.

Fora de escopo: o campo que descreve a forma do bloco de workflow no registro de estado. Ele foi renomeado e redefinido fora deste trabalho, e sob a definição nova não descreve artefato externo algum. Também fora: detectar que um registro ficou obsoleto porque o documento migrou depois da criação — verificação mais forte, avaliada e recusada porque derrubaria de uma vez todos os work items já publicados, sem prévia e sem caminho de migração. E fora: reescrever work items já publicados, e alterar as ordens canônicas de qualquer versão de workflow.

Critérios de aceitação:

- Um work item criado sobre declaração anterior registra essa sequência, e a projeção o classifica por ela.
- Um work item criado sobre a declaração corrente registra a sequência corrente.
- Criação sobre documento sem declaração única é recusada, sem deixar work item parcial, com mensagem que nomeia o encontrado e o esperado.
- Os work items existentes mantêm o veredito atual.
- A suíte de validadores fecha em exit 0, com a matriz de casos coberta a partir do documento real materializado, não de texto derivado do próprio detector.

## WHY

A projeção de status foi corrigida para julgar cada work item pela sequência que ele declara, em vez de projetar a sequência mais recente sobre todos. Essa correção depende de o registro dizer a verdade — e o registro é um literal congelado no asset, idêntico em todo bundle criado. Num repositório que preserva uma declaração anterior, a correção erra pela outra ponta: o bundle afirma a sequência corrente, e é julgado por etapas que o documento dele não contém. O defeito não some, troca de sinal.

Evidência: o campo permanece congelado no asset da versão corrente do plugin, e a função que o lê devolve esse literal para qualquer repositório, independentemente do que o documento declare.

O caso irmão desse defeito — um par de escrita e verificação sobre o mesmo literal, que concordava sempre e só reprovava quem registrasse o valor verdadeiro — foi encerrado fora deste trabalho por uma redefinição: o campo em questão passou a declarar a forma do próprio bloco, e não a versão do documento. Sob essa definição o literal é legítimo, e este trabalho não o toca. O que restou é o campo que continua descrevendo um artefato externo sem ser lido dele.

Restrições: nenhum work item já publicado pode mudar de veredito por causa desta mudança — é o que separa esta correção de uma queda de frota. A mudança toca o plugin publicado, então exige bump de versão nos pontos travados pelo validador de distribuição.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
