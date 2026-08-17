# FASE-005 — Verificação e publicação 3.0.0

- phase: FASE-005
- state: complete
- roadmap: ROADMAP.md#FASE-005
- context-refs: Projeção, Backlog operacional
- ADRs: none
- BLs: none

## WHY
Os quatro defeitos que desligaram a integração passaram despercebidos porque nenhum deles tinha cobertura. Um deles em particular — a recusa por o work item ter artefatos escritos — é insatisfazível por construção e mesmo assim nunca reprovou nada, porque nada exercitava o caminho. Corrigir sem cobrir devolve o mesmo risco.

A verificação automatizada roda em três sistemas operacionais e duas versões de linguagem, sem o backlog operacional instalado. Isso não é acidente e não vai mudar: toda cobertura precisa entrar por ponto de injeção, nunca exigindo o binário real.

Inverter a autoridade e tornar a criação recusante são mudanças incompatíveis com todo work item e todo consumidor existentes. Isso é bump maior, não menor.

Há um limite conhecido: registrar um gate como verificação obrigatória na proteção da branch é configuração de serviço e nenhum commit consegue fazê-lo. Fica declarado como ato humano, não como entrega desta fase.

## WHAT
- delivery-units: DU-005
- development-type: qa

Os defeitos ganham regressão e a versão incompatível é publicada de forma consistente.

Resultado observável: cada um dos quatro defeitos tem teste que reprova o comportamento antigo; determinismo, mapeamento de estados, idempotência da migração e recusa do work item não migrado estão cobertos; a suíte fecha verde na matriz sem o backlog real; e a versão é idêntica nos oito lugares que o contrato de distribuição fixa.

Atores: a verificação automatizada da matriz e o operador que publica.

Cenários que precisam passar:
- suíte completa em ambiente sem o backlog operacional;
- cada defeito exercitado no sentido que reprova antes da correção;
- divergência de versão entre quaisquer dos oito lugares, que precisa reprovar.

Escopo excluído: registrar a verificação obrigatória na proteção da branch, que é ato humano.

Critérios de aceite: suíte verde na matriz sem o binário real; regressão presente para os quatro defeitos; versão consistente nos oito lugares.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
