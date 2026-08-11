# FASE-001 — Gate de bump no CI

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: Repositório canônico, Manifesto do plugin, Publicação
- ADRs: ADR-0002
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

Resultado observável: uma pull request que altere o conteúdo do plugin sem subir a versão declarada é reprovada pelo CI, com mensagem que diz qual versão está declarada e que ela precisa aumentar. Uma pull request que não toque o conteúdo do plugin passa sem exigir bump. Uma pull request que toque o conteúdo e suba a versão passa.

Atores: quem abre pull request no repositório canônico, e o CI que decide.

Cenários que o gate precisa distinguir:
- mudança apenas em testes ou documentação fora do plugin, sem bump — aprovada;
- mudança no conteúdo do plugin sem bump — reprovada;
- mudança no conteúdo do plugin com bump — aprovada;
- mudança no conteúdo do plugin com a versão reduzida — reprovada.

Escopo: apenas a verificação. Nada nesta fase escreve fora do repositório canônico.

Critérios de aceite: os quatro cenários acima verificáveis; a mensagem de falha nomeia a versão declarada e a exigência; o gate não duplica as checagens de coerência de versão que os validadores já fazem.

## WHY
A versão precisa identificar o conteúdo. O cache do cliente é indexado por versão — há seis diretórios de versão lado a lado no cache local — então conteúdo diferente sob a mesma versão simplesmente não alcança quem já tem aquela versão instalada.

O histórico mostra que a disciplina não se sustenta sem gate: dos quatro merges na main em 2026-08-11, apenas um subiu a versão, e um dos outros acrescentou uma flag nova visível ao usuário sob a versão já existente.

Esta fase vem primeiro porque a publicação automática sem o gate transformaria cada merge sem bump em uma republicação silenciosa da mesma versão com bytes diferentes.

Restrição: o gate depende do merge base para comparar versões, o que existe em pull request e não em push direto na main.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
