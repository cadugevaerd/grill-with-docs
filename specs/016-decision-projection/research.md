# Research — FASE-002, projeção versionada e determinística

Nenhum marcador `NEEDS CLARIFICATION` sobreviveu à especificação. Este documento consolida o que foi medido e o que foi descoberto durante o planejamento.

## D1 — O formato de saída não é livre

**Decision**: a projeção reproduz exatamente o formato que `audit_decisions.py` já parseia.

**Rationale**: o auditor lê o mesmo arquivo e exige, por bloco, `state` em `{open, resolved, superseded}`, `phase` casando uma fase declarada no ROADMAP, e — quando `state` é `open` — os campos `owner`, `evidence-needed` e `next-action` preenchidos. Uma projeção que produzisse formato próprio quebraria o gate que ela alimenta.

Isso fecha o round-trip. A FASE-001 grava na descrição do item todos os campos da decisão **menos** `state`, que foi excluído de propósito por ser propriedade do item. Então a projeção recompõe o bloco a partir da descrição e obtém `state` invertendo o `status` do item.

**Alternatives considered**:
- Formato próprio mais rico, com o auditor adaptado: dobraria a superfície de mudança e colocaria o gate em risco por um ganho estético.

## D2 — Defeito descoberto: os dois parsers divergem

**Decision**: a ponte passa a usar `audit_decisions.split_blocks`, eliminando o segundo parser em vez de alinhá-lo.

**Rationale**: hoje existem duas leituras independentes do mesmo arquivo.

| Leitor | Padrão | Aceita |
|---|---|---|
| `audit_decisions.split_blocks` | `^##\s+(BL-\d{3,4})\b(.*?)` | 3 ou 4 dígitos, qualquer separador, título opcional |
| `backlog_bridge.BLOCK` | `^##\s+(BL-\d{4})\s+—\s+(.+?)\s*$` | só 4 dígitos, só travessão, título obrigatório |

Medido nos dois módulos carregados lado a lado:

| Cabeçalho | Auditor vê | Ponte vê |
|---|---|---|
| `## BL-0001 — Título` | sim | sim |
| `## BL-0001 - Título` (hífen ASCII) | sim | **não** |
| `## BL-001 — Título` | sim | **não** |
| `## BL-0001` | sim | **não** |
| `## BL-0001 – Título` (travessão curto) | sim | **não** |

Consequência viva, já na `main`: uma decisão escrita com hífen comum — o que qualquer teclado produz sem esforço — **bloqueia a fase pela auditoria e nunca é espelhada pela ponte**. É a mesma classe de divergência silenciosa que motivou o work item inteiro, sobrevivendo dentro dele. A revisão da FASE-001 não pegou porque toda fixture usava travessão.

Alinhar as duas expressões deixaria a duplicação viva e sujeita a divergir de novo. A ponte já carrega `audit_decisions` por `sibling()` para usar `fields()`, então reusar `split_blocks` custa pouco e mata a classe do defeito.

**Alternatives considered**:
- Copiar a expressão do auditor para a ponte: resolve hoje e recria o risco na próxima alteração de qualquer um dos lados.
- Normalizar o arquivo na escrita e manter a leitura estrita: não ajuda os arquivos autorais já existentes, que a FASE-004 vai migrar.

## D3 — A marca de origem não pode ser o contador do backlog

**Decision**: a marca cobre apenas a fatia deste work item — identificadores, estados e conteúdo dos itens vinculados — e é insensível a tudo mais.

**Rationale**: `backlog list` devolve um campo `revision` por backlog, que à primeira vista serviria de versão da autoridade. Não serve: ele avança a cada mudança em **qualquer** item daquele backlog. O `SGD` é compartilhado por este repositório e por qualquer outro que se vincule a ele, e hoje tem 15 itens dos quais a maioria não pertence a work item nenhum. Uma marca baseada nele acusaria divergência a cada mexida alheia, e o ruído treinaria o operador a ignorar o sinal.

**Alternatives considered**:
- `revision` do backlog: descartado acima.
- Carimbo de tempo da geração: quebra o determinismo exigido por FR-003, porque duas gerações idênticas produziriam arquivos diferentes.

## D4 — Determinismo é requisito duro

**Decision**: ordenação por identificador da decisão, formatação fixa, e nenhuma fonte de variação externa ao conteúdo.

**Rationale**: o `reconcile` exige que a segunda execução seja byte-idêntica, e a projeção é versionada. A ordem em que a autoridade devolve os itens não é contratual e pode mudar entre execuções; ordenar pelo identificador é estável e legível. Nada de carimbo de tempo, caminho absoluto ou ordem de dicionário na saída.

## D5 — Escrita atômica

**Decision**: staging mais rename, o mesmo padrão que a criação do bundle já usa.

**Rationale**: FR-013 exige que interrupção não deixe arquivo parcial. O repositório já resolveu esse problema uma vez, com escrita em staging e rename atômico, e a solução é portátil o bastante para a matriz. Reusar o padrão existente evita inventar um segundo mecanismo.

## D6 — Cobertura sem a autoridade real

**Decision**: os seams existentes, `StubToolchain` e a substituição de `resolve_cli`.

**Rationale**: mesma restrição da fase anterior, e ela é permanente. A auditoria offline, especificamente, precisa de teste que rode **sem** qualquer substituto configurado, porque o ponto é justamente que ela não chama nada.
