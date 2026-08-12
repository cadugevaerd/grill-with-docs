# Learnings — FASE-003

## O verde de um pipeline precisa afirmar algo sobre o mundo

O job de publicação terminava depois do `git push`, e isso parecia suficiente até alguém perguntar o que exatamente o zero do push prova. Prova que o remote respondeu. Não prova que o arquivo certo foi commitado, que o commit foi para o repositório certo, nem que a entrada carrega o pin desta release. Três formas de falhar em silêncio, todas com o job verde.

A regra generalizável: quando um passo escreve em um sistema externo, o critério de sucesso tem que ser uma leitura desse sistema, não o código de retorno da escrita. E a leitura precisa vir de uma conexão nova — reler o arquivo que o próprio passo editou atesta a memória do runner, não o destino.

## A releitura provou seu valor na primeira execução, sem precisar reprovar nada

A primeira publicação real rodou verde nos dois destinos, e a releitura confirmou `problems: []` a partir de clone novo. Isso parece anticlimático — o passo novo não pegou nada. Mas o valor dele não é achar defeito nesta execução: é que o verde desta execução agora significa "os destinos servem 2.5.0 pelo pin certo", verificado de fora, em vez de "dois `git push` retornaram zero". A diferença entre as duas afirmações é o que a fase inteira comprou.

A segunda execução fechou o outro lado: nada criado, nada empurrado, `VERIFIED` nos dois. Idempotência deixou de ser propriedade argumentada e virou observação.

## O bloqueio era real, e insistir nele foi correto

A fase ficou parada num ato humano: instalar a credencial. Publicar à mão daqui teria produzido o mesmo estado final nos marketplaces e destruído o objetivo — a automação seguiria sem nenhuma execução real, e o primeiro teste em condições reais aconteceria às cegas num merge futuro. Quando a autorização veio, o pipeline inteiro rodou de ponta a ponta e a fase fechou com evidência de produção, não com simulação. O custo de esperar foi tempo; o custo de contornar teria sido o próprio propósito da fase.

## A auditoria pegou o que eu deixei passar

Adicionei ADR-0007 ao ROADMAP e esqueci o handoff e o PLAN-CONTEXT. A auditoria reprovou com `ARTIFACT-INVALID` e nomeou as duas divergências. Um gate documental que roda de graça e aponta o arquivo exato vale mais do que a disciplina de lembrar — foi a segunda vez nesta milestone que uma verificação automática pegou uma inconsistência que a revisão humana tinha deixado passar.

## Premissa velha sobrevive a decisão nova, se ninguém for buscá-la

ADR-0006 trocou o espelho de conteúdo por referência `git-subdir` na FASE-002. Mesmo assim, o handoff e o PLAN-CONTEXT da FASE-003 continuaram pedindo "manifesto vendorizado" e "diretório de testes ausente da cópia publicada" — critérios de um modelo que já não existia. A decisão foi registrada; os documentos rio abaixo não foram varridos atrás dela.

Ao superseder um modelo, procurar os artefatos que dependiam dele é parte da decisão, não uma limpeza posterior. Aqui isso só apareceu porque a fase seria infechável contra o próprio critério de aceite.

## Um número errado num documento de governança custa confiança, não tempo

O ROADMAP dizia que o claude servia `2.4.0`; ele serve `2.4.1`. O impacto prático é nenhum — a reconciliação publica a versão corrente de qualquer jeito. O impacto real é que um leitor que confere esse número e vê outro passa a conferir todos os outros.

## Escopo por arquivo com dono único

FASE-002 perdeu tempo com dois agentes reescrevendo o mesmo publicador a partir de modelos arquiteturais diferentes. Aqui o trabalho foi sequencial e de dono único, e o paralelismo ficou onde ele realmente rende: um revisor adversarial independente, com escopo de leitura e mandato de procurar o falso verde.
