# Learnings — FASE-003

## Onde a configuração mora decide o que ela pode fazer

O gate estava correto e era inútil como gate: dentro do `ci.yml`, herdava um filtro de caminhos que existia por outro motivo — a matriz é cara. Duas exigências legítimas, uma restrição do serviço, e o resultado era um check que não podia ser exigido.

A correção não foi lógica, foi de arranjo: mudar o job de arquivo. Vale lembrar quando uma regra parece impossível de aplicar — às vezes o obstáculo é onde ela está declarada, não o que ela diz.

## A alternativa óbvia era a errada, e estava escrita no próprio backlog

O SGD-7 sugeria um job-shim que reportasse sucesso quando o gate fosse pulado. Resolve o sintoma e reintroduz falso verde: aprovado passa a ser indistinguível de não-executado.

Aceitar a sugestão registrada teria sido o caminho de menor atrito. O que a barrou foi a memória de uma fase anterior desta mesma milestone, que gastou um ciclo inteiro eliminando essa exata confusão na publicação. Decisões antigas só protegem se forem lembradas na hora certa — por isso ADR-0003 registra a recusa, e um teste impede que ela volte por descuido.

## Migração silenciosa pede teste de fiação

Mover um job de um workflow para outro não quebra nada visivelmente se o destino estiver errado: o repositório simplesmente fica sem gate, e ninguém descobre até integrar algo que deveria ter sido barrado.

Os testes desta fase não verificam "o arquivo existe". Verificam as quatro propriedades que fazem o gate funcionar, cada uma correspondendo a um jeito distinto de a migração falhar em silêncio. Para mudança de infraestrutura, o teste útil é o que descreve a propriedade, não o artefato.

## O código pode ficar pronto e o requisito continuar descumprido

FR-007 diz que a reprovação deve bloquear. Depois desta fase o gate reporta sempre — e ainda não bloqueia nada, porque exigir o check é configuração do serviço.

Registrei em `CLAUDE.md` em vez de deixar no backlog externo, porque é lá que alguém vai procurar quando mexer nos workflows. Um pendente que só existe num sistema que ninguém abre é um pendente perdido.
