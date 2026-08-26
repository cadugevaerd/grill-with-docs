# FASE-001 — Emissor da cadeia de atestação

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: cadeia de atestação, emissor, leader, executor da etapa, evidência estrutural, artefato da etapa, lease
- ADRs: ADR-0201, ADR-0202, ADR-0203, ADR-0204, ADR-0205
- BLs: BL-0201, BL-0202

## WHAT
- delivery-units: DU-001, DU-002
- development-type: platform-devops

Concluir uma etapa do ciclo passa a ser possível sem inventar nada. Hoje o núcleo
exige, para aceitar a conclusão, uma cadeia de quatro documentos correlacionados;
ele sabe validar essa cadeia e não sabe produzi-la, e nenhuma outra parte do
sistema a produz. O resultado é que o ciclo inteiro ficou inalcançável.

A entrega tem três resultados observáveis:

1. **Cada etapa declara quem pode conduzi-la.** Existe uma tabela, ao lado da
   ordem canônica das etapas e congelada como ela, dizendo quais etapas exigem um
   executor isolado e despachado, e quais admitem que a própria sessão condutora
   as execute. A etapa de execução paralela exige executor despachado, porque ali
   o isolamento e o escopo fechado de arquivos são o mecanismo de segurança, não
   conveniência. Etapa sem entrada na tabela falha fechado, nomeando o que falta
   decidir.

2. **A sessão condutora consegue atestar o que ela mesma faz.** Ela obtém
   concessão de execução pelo mesmo mecanismo que o sistema já usa para conceder
   a executores despachados, e a cadeia é montada a partir do que já é conhecido:
   identidade do projeto, identidade e revisão do item de trabalho, referência do
   registro de capacidades, ponto do histórico em que a árvore está. Nenhum campo
   é preenchido com valor de conveniência; o índice de onda recebe o valor que
   significa "fora de onda", e isso é declarado.

3. **O que a cadeia afirma é ancorado em algo observável.** Quem conduz a etapa
   informa o caminho do artefato que ela produziu; a emissão lê esse arquivo e
   sela seu resumo criptográfico. Arquivo ausente, ilegível ou fora do projeto é
   recusa nomeada, nunca emissão com resumo vazio.

Critérios de aceite:

- Uma etapa conduzida pela sessão condutora conclui pelo mecanismo normal de
  checkpoint, sem que nenhum campo seja inventado.
- A etapa de execução paralela continua exigindo executor despachado, e tentar
  atestá-la como conduzida pela sessão falha nomeando a exigência.
- Etapa ausente da tabela de classes falha fechado.
- Alterar o artefato depois da emissão quebra a correlação, de forma detectável.
- Artefato ausente, ilegível ou fora do projeto produz recusa nomeada.
- A suíte do projeto trava essas garantias e roda sem rede e sem ferramenta
  externa instalada.

Escopo excluído, e declarado como tal desde o desenho original desta máquina:
proveniência criptográfica, defesa contra executor malicioso, e qualquer
acoplamento ao formato de rastro de um runtime de agente específico.

## WHY

O ciclo de trabalho deste projeto tem onze etapas e nenhuma delas pode ser
concluída hoje em um projeto na versão corrente. A exigência da cadeia foi
ativada corretamente — antes ela era ignorada em silêncio para documentos da
versão corrente, o que é pior — e a correção revelou que a outra metade do
mecanismo nunca foi construída.

A alternativa a construir essa metade é montar os documentos à mão, afirmando
concessões de execução e identificadores que não existiram. Isso é precisamente
o que a governança do projeto proíbe: evidência antes de afirmação, e nenhuma
saída semanticamente equivalente no lugar da invocação real. Um sistema que
obriga seus operadores a fabricar evidência para avançar ensina exatamente o
hábito que ele existe para impedir.

A delimitação por tabela existe porque a permissão de a sessão condutora
executar é, sem fronteira declarada, uma rota de escape: qualquer etapa poderia
se declarar assim para não passar pelo despacho isolado. Declarar a fronteira
numa tabela congelada torna qualquer deslocamento dela uma decisão visível em
diff, e não um efeito colateral.

A âncora no artefato é deliberadamente modesta. Ela não prova que a capacidade
registrada foi invocada; prova que existe um artefato e que ele não mudou depois.
Prometer mais do que isso seria inventar uma garantia que o desenho declara fora
de escopo — e uma garantia falsa é pior que uma garantia modesta bem descrita.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
