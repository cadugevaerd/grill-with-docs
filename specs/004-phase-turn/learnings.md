# Learnings — FASE-001

## Copiar um padrão é herdar seus defeitos

`phase_turn_command` nasceu com `development.setdefault("audit", []).append(...)`, copiado do `checkpoint`. O padrão parecia seguro porque estava lá havia muito tempo e nunca tinha falhado. Falhava: trilha presente e de outro tipo derruba com `AttributeError`, sem código nomeado.

O defeito só apareceu porque a sondagem adversarial atacou o código novo — e, ao atacá-lo, expôs o antigo. Vale como método: quando um trecho novo copia um trecho velho, testar o novo é testar os dois, e o velho é o que ninguém está olhando.

## Comparação estática não prova extração

Extrair guardas para funções compartilhadas move os códigos de erro para outro lugar no arquivo. Qualquer diff ou varredura de ordem acusa divergência, mesmo quando o comportamento é idêntico — e a inversa também vale: pode não acusar nada e a guarda ter saído do caminho.

O que provou foi rodar as duas versões, a de `HEAD~1` e a atual, contra os mesmos cinco casos e comparar os códigos de saída. Cinco guardas, cinco iguais. Para refatoração de código de segurança, a prova é executar as duas versões lado a lado, não ler o diff.

## Idempotência e recusa podem descrever o mesmo estado

"Recusar quando nem tudo está `complete`" e "não fazer nada quando tudo está `pending`" parecem regras independentes, mas o segundo estado é um caso particular do primeiro. Implementadas na ordem errada, a idempotência vira inalcançável — e o sintoma seria uma reexecução legítima recusada como "fase incompleta", que é confuso justamente por soar plausível.

Regra que fica: quando duas condições podem casar a mesma entrada, a ordem entre elas é decisão de desenho e merece teste, não comentário.

## O código de erro é a documentação que o operador lê

`INVALID-TRANSITION` estava correto e era inútil: descrevia o sintoma. Duas fases inteiras da milestone anterior ficaram sem trilha porque quem esbarrou nele concluiu que não havia saída — e não havia mesmo, mas a mensagem também não dizia isso.

`PHASE-TURN-REQUIRED` custa a mesma linha e transporta o remédio. Num CLI, o código de erro é lido muito mais vezes do que qualquer README.

## Dogfooding encontra o que o teste não encontra

Esta fase foi conduzida com o próprio `checkpoint`, passo a passo. Foi assim que ficou concreto o que o SGD-6 custava: não é um travamento abstrato, é a diferença entre uma trilha com 11 passos registrados e nenhuma trilha. Ler o defeito no backlog não produz a mesma convicção que esbarrar nele enquanto se trabalha.
