# FASE-002 — Publicação fan-out nos dois marketplaces

- phase: FASE-002
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-002
- context-refs: Marketplace, Cópia vendorizada, Entrada de marketplace, Publicação
- ADRs: ADR-0001, ADR-0003, ADR-0004, ADR-0005
- BLs: BL-0001

## WHAT
- delivery-units: DU-002
- development-type: platform-devops

Resultado observável: depois de um merge na main que altere o conteúdo do plugin, os dois marketplaces passam a servir a mesma versão e o mesmo conteúdo do repositório canônico, sem qualquer intervenção manual.

Atores: quem faz merge na main; os dois marketplaces como destino; o consumidor que instala o plugin a partir deles.

Cenários:
- merge que altera o conteúdo do plugin — os dois marketplaces são atualizados;
- merge que não altera o conteúdo do plugin — nada é publicado;
- um marketplace indisponível e o outro saudável — o saudável é atualizado, o indisponível é reportado como falha e pode ser reexecutado sozinho;
- reexecução após sucesso — o resultado é o mesmo, sem efeito acumulado;
- arquivo removido do plugin no canônico — desaparece também do destino.

Escopo: a publicação em si e a atualização da versão declarada na entrada de cada marketplace. O texto descritivo curado de cada entrada permanece intocado.

Fora de escopo: zerar o atraso já existente, que pertence à fase seguinte.

Critérios de aceite: os cinco cenários verificáveis; a versão declarada nos dois destinos igual à do canônico; nenhum arquivo de teste presente na cópia publicada.

## WHY
O plugin é desenvolvido em um repositório e consumido a partir de outros dois, que hoje carregam uma cópia manual. Sem automação essa cópia envelhece: o canônico está duas versões à frente do que os usuários instalam.

A publicação parte do canônico porque é lá que a mudança nasce e é lá que existe um único gatilho; a alternativa espalharia a mesma lógica por dois agregadores que juntos hospedam dezesseis plugins.

Restrição aceita e registrada: a credencial usada concede mais poder do que a tarefa exige. BL-0001 acompanha a migração para escopo mínimo, com gatilho definido, e não bloqueia esta fase.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
