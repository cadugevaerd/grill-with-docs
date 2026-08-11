# Ship fase A — aprendizados aprovados

## Estado local não é estado publicado

O erro mais caro da fase: li `~/.claude/plugins/marketplaces/claude-skills`, um checkout que o próprio agente mantém, e tratei como o repositório publicado. Estava 70 commits à frente do `origin` e nunca empurrado. Toda a fase, e três ADRs da entrevista anterior, foram desenhados sobre isso.

A verificação que teria evitado: um `git status -sb` no checkout, ou clonar do remoto antes de afirmar qualquer coisa sobre o que está publicado. Custo de não fazer: uma entrevista inteira decidida sobre premissa falsa, incluindo uma opção correta descartada por eu tê-la marcado como `EVIDENCE GAP`.

## Editar JSON de terceiros é edição de texto, não de estrutura

Reserializar um documento que outra pessoa mantém normaliza a formatação dela e afoga a mudança real. Nas três tentativas, cada abordagem estrutural produziu um defeito: reserialização total reformatou vizinhas; âncora no último `}` caiu dentro de um objeto aninhado; regex sem profundidade patcheou a chave errada. O que funcionou foi tratar o arquivo como texto e localizar spans com consciência de string e de profundidade.

## Testes de camada pura não pegam defeito de fronteira

Os três defeitos viviam entre a estrutura parseada e o texto do arquivo. Todos os testes da camada pura passavam com eles presentes. O que os revelou foi executar contra os arquivos reais dos dois marketplaces.

## Recusar-se a sobrescrever em silêncio é o comportamento certo

Um executor percebeu que a nova implementação contradizia um ADR com status `accepted`, preservou a versão alheia, restaurou a sua e pediu um ADR novo antes de aceitar a virada. Estava certo: a virada era deliberada, mas eu não havia registrado a supersessão. `ADR-0006` existe por causa disso.
