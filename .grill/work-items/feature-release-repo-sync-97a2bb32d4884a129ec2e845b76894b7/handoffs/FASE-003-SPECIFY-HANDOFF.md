# FASE-003 — Reconciliação do drift existente

- phase: FASE-003
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-003
- context-refs: Drift de publicação, Publicação
- ADRs: ADR-0007
- BLs: none

## WHAT
- delivery-units: DU-003
- development-type: platform-devops

Resultado observável: os dois marketplaces deixam de servir a versão antiga e passam a servir a versão corrente do canônico, sem esperar pela próxima mudança de conteúdo do plugin.

Atores: quem opera a publicação manualmente uma única vez; os dois marketplaces como destino.

Cenários:
- disparo manual com os dois marketplaces atrasados — ambos passam a servir a versão corrente;
- disparo manual quando já estão em dia — nada muda e a execução termina limpa;
- disparo manual com um destino indisponível — o outro é atualizado e a falha é reportada.

Escopo: o gatilho manual e uma execução única de reconciliação, mais a verificação do estado final nos dois destinos.

Fora de escopo: republicar versões históricas que nunca chegaram aos marketplaces.

Critérios de aceite: os dois destinos declarando a versão corrente do canônico, tanto no manifesto vendorizado quanto na entrada de marketplace; o diretório de testes ausente da cópia publicada; o gatilho manual permanecendo disponível depois da reconciliação.

> Nota de reconciliação, 2026-08-12: os dois primeiros critérios acima pressupõem o espelho de conteúdo abandonado em ADR-0006 — não existe cópia publicada, logo não há manifesto vendorizado nem diretório de testes a remover. ADR-0007 registra o que os substitui: cada destino é relido de um clone novo e precisa declarar a versão corrente e os cinco campos do pin `git-subdir`, com a referência resolvendo no canônico para o commit publicado. O terceiro critério permanece como está. O texto original fica preservado por rastreabilidade.

## WHY
A publicação automática só reage a mudanças no conteúdo do plugin, e o próprio trabalho que a introduz não é uma dessas mudanças. Sem um disparo manual, o atraso atual sobreviveria por tempo indeterminado e a automação ficaria sem nenhuma execução real — o primeiro teste em condições reais aconteceria às cegas, em um merge futuro qualquer.

O gatilho manual permanece depois como saída de emergência: permite republicar sem precisar inventar um commit quando uma execução falha e a reexecução automática já não está disponível.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
