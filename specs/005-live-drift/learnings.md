# Learnings — FASE-002

## A spec estava certa e insuficiente, e só o uso mostrou

O recorte "não alarmar em work item terminal" era correto. Aplicado, silenciou o work item concluído — e deixou o em andamento alarmando, porque o ramo da criação tinha morrido no ship anterior.

O raciocínio que produziu a spec era bom e parou cedo. O que o completou foi rodar a mudança e olhar a saída real, com dois work items em estados diferentes. Nenhuma releitura da spec teria produzido isso.

## Uma condição insatisfazível costuma ter irmãs

O defeito original era um operando que nunca podia ser falso. Ao corrigi-lo, a primeira versão criou outro: comparar contra um ramo que o próprio protocolo apaga. Mesma forma, um nível acima.

Vale como heurística: ao remover uma comparação insatisfazível, perguntar de cada operando restante em que condições ele deixa de poder ser verdadeiro. Aqui a resposta estava no próprio protocolo — uma fase por ramo, ramo apagado no ship.

## Silêncio bom e silêncio ruim se parecem

Depois da mudança, `status` devolveu `OK` pela primeira vez na milestone. Isso é indistinguível, à primeira vista, de ter quebrado a detecção. O que separa os dois é o quadrante que continua alarmando: ramo registrado vivo, work item em andamento, leitura de outro lugar.

Por isso o teste que mais importa nesta fase não é o que prova o silêncio — é o que prova que o alarme sobreviveu.

## Duas implementações da mesma noção

"Terminal" agora é decidido em dois lugares, sobre os mesmos dois campos, por códigos diferentes. Ficou registrado como risco aceito, não resolvido. É o tipo de duplicação que não dói hoje e cobra juros na primeira mudança de regra.
