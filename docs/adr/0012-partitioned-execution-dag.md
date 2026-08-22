# Partitioned Execution DAG

Supersede o ADR-0004 quanto ao produtor do Execution DAG. Sob o WORKFLOW v4 quem emite o DAG é a etapa `partition`, não `tasks`. A skill `tasks` permanece dona de `tasks.md`; `partition` lê esse arquivo já pronto e deriva o grafo.

A derivação MUST ser determinística e viver em código (`grill_core/partition.py`), nunca no prompt: a mesma `tasks.md` tem de produzir o mesmo `dag_content_sha256`, senão o hash pinado na run vira ruído. Dependências continuam não sendo inferidas de texto livre — as arestas vêm da ordem declarada dentro da fase, da ausência do marcador `[P]` e do compartilhamento de arquivo entre tarefas. Os nós são componentes conexos desse grafo, logo file-disjuntos e fechados sob dependência por construção; um componente nunca é fatiado para forçar uma contagem.

Três é teto, não promessa. Quando as dependências não permitem três grupos, `partition` emite menos nós e declara `PARTITION-DEGRADED` com a razão. Tarefa sem caminho de arquivo extraível bloqueia com `PARTITION-UNMAPPED-TASK` em vez de ser chutada para um bin.

Permanece do ADR-0004: o Gauntlet só despacha em paralelo nós sem dependências pendentes, e a automação cobre exclusivamente as onze macroetapas canônicas, que a configuração não reordena nem substitui.
