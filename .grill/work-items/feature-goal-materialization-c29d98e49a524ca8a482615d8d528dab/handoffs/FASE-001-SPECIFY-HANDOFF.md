# FASE-001 — Materialização e validação do goal.md

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: goal.md, materialização, marcador, tupla ESSENTIAL, SSOT de documento, no-clobber
- ADRs: ADR-0101, ADR-0102
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

Todo projeto que executa a criação de work item passa a ter, na raiz, o
documento de instruções que conduz o laço autônomo. Hoje esse documento existe
apenas como asset do plugin: quem consome o plugin não o recebe, e nada garante
que uma edição futura preserve o que ele precisa dizer.

A entrega tem três resultados observáveis:

1. **O documento chega ao consumidor.** A criação de work item fixa o documento
   na raiz do projeto, sem sobrescrever nada, e reporta o estado em que o
   encontrou — recém-criado, já presente e conforme, ou já presente e
   divergente. O hash do que foi fixado fica registrado no estado do work item,
   para que deriva posterior seja detectável.

2. **Arquivo humano na raiz é intocável.** Um documento preexistente com o mesmo
   nome que não corresponda ao contrato permanece byte a byte como está. Ele é
   reportado como divergente e a criação segue; nada é sobrescrito, renomeado ou
   copiado para backup. O relatório precisa distinguir esse caso do sucesso sem
   ambiguidade.

3. **O contrato fica travado por teste.** A suíte canônica passa a reprovar
   qualquer documento que perca uma das partes que o contrato exige. O conjunto
   dessas partes é declarado **uma única vez**, num lugar de onde todos os
   consumidores leem — o materializador, o validador e quem vier depois.
   Nenhum consumidor redeclara esse conjunto.

Critérios de aceite:

- Criação repetida é idempotente e reporta reuso, sem reescrever o arquivo.
- Documento divergente é preservado byte a byte e sinalizado.
- O hash registrado corresponde aos bytes efetivamente materializados.
- A suíte reprova a remoção de qualquer parte exigida pelo contrato.
- O teste roda sem rede e sem exigir ferramenta externa instalada.
- A versão publicada do plugin reflete a mudança em todos os pontos onde a
  distribuição a exige.

Escopo excluído: o texto normativo do documento, que já foi entregue pelo work
item anterior e não é reaberto aqui.

## WHY

Um documento que só existe no repositório de origem não automatiza projeto
nenhum. A fixação é o que faz o contrato chegar a quem consome, e o hash
registrado é o que permite detectar deriva depois.

A garantia de não sobrescrever existe porque a raiz de um projeto é território
do humano: um arquivo com esse nome pode ter sido escrito por alguém, para outra
finalidade. Destruí-lo com base numa colisão de nome trocaria uma conveniência
por trabalho alheio.

A declaração única do conjunto exigido não é preferência de estilo. Uma versão
recém-publicada deste mesmo plugin corrigiu um defeito cuja causa era
exatamente a duplicação de tabelas de versão: a interface declarava uma coisa
numa constante própria e usava outra algumas centenas de linhas abaixo, sem que
nada reprovasse a contradição, e o efeito só apareceu em campo, recusando todo
projeto na versão corrente. Repetir esse padrão aqui produziria o mesmo desfecho.

Restrição: a entrega altera o diretório publicado do plugin, o que exige
incremento de versão antes de qualquer merge ou push, sincronizado em todos os
pontos travados.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
