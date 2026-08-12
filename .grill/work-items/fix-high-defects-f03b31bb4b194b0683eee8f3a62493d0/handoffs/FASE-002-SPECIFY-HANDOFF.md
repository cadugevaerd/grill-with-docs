# FASE-002 — Deriva viva precisa

- phase: FASE-002
- state: complete
- roadmap: ROADMAP.md#FASE-002
- context-refs: Pino de identidade, Deriva viva, Work item terminal
- ADRs: ADR-0002
- BLs: none

## WHAT
- delivery-units: DU-002
- development-type: platform-devops

Resultado observável: a consulta de situação volta a distinguir bloqueio real de diferença esperada, em vez de reprovar todo work item que tenha mais de um commit.

Atores: quem consulta a situação durante o trabalho e precisa saber se há algo travado; quem consulta depois do encerramento e não deveria ver alarme.

Cenários:
- work item em andamento, lido do seu próprio ramo — nenhum alarme, mesmo com muitos commits desde a criação;
- work item em andamento, lido de outro ramo — alarme, porque ler o registro de um lugar que não é o dele é o risco que se quer detectar;
- work item já encerrado, lido da linha principal — nenhum alarme, porque o ramo de trabalho já não existe e a diferença é esperada;
- work item com bloqueio real — o bloqueio aparece, em vez de ficar escondido atrás do alarme permanente.

Escopo: a condição que hoje compara o registro de identidade com o estado vivo, e o recorte da janela em que essa comparação pode significar algo.

Fora de escopo: alterar o que foi registrado na criação, ou o mecanismo que protege esse registro contra adulteração.

Critérios de aceite: nenhum alarme para work item multi-commit no próprio ramo; alarme preservado para leitura a partir de outro ramo durante o trabalho; nenhum alarme para work item encerrado; e um bloqueio real continua visível e continua reprovando.

## WHY
Metade da comparação nunca pode ser verdadeira: o valor registrado é anterior ao próprio registro existir, então nenhum commit que contenha o trabalho consegue igualá-lo. A outra metade deixa de poder ser verdadeira assim que o trabalho termina e o ramo é apagado.

O resultado é um alarme que soa sempre. Um alarme que soa sempre não avisa nada — ele esconde. Durante toda a milestone anterior a consulta de situação respondeu bloqueado, e essa resposta não carregou informação nenhuma; qualquer bloqueio verdadeiro teria passado despercebido no meio do ruído.

Corrigir não é afrouxar a verificação. É devolver à verificação a capacidade de dizer algo, restringindo-a à janela em que ela pode ser verdadeira.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
