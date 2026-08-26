# Contrato: o documento `goal.md`

**Fase 1** | **Data**: 2026-08-26 | **SSOT**: `plugin/skills/grill-with-docs/scripts/grill_core/goal_document.py`

Este contrato define o que faz de um arquivo na raiz um `goal.md` **conforme**.
Ele é declarado num único lugar do repositório e lido — nunca copiado — pelo
materializador, pelo validador e por qualquer consumidor futuro (FR-009, FR-010,
SC-006).

## Marcador de versão

```text
grill-with-docs-goal:v1
```

Aparece na **primeira linha** do documento, como comentário HTML:

```markdown
<!-- grill-with-docs-goal:v1 -->
```

O marcador é do **contrato do documento**, não da versão publicada do plugin
(FR-011). O plugin pode ir a 6.x sem que `v1` mude; o `v1` muda quando as partes
exigidas mudarem, e aí `v2` nasce **ao lado** de `v1`, com tupla própria.

Reconhecimento: expressão regular `grill-with-docs-goal:(v\d+)` casada **apenas
contra a primeira linha** do texto. Um marcador solto no meio do documento não o
identifica como gerenciado — do contrário, um arquivo humano que citasse o
marcador em prosa passaria a ser julgado pelo contrato, e um documento
gerenciado com a primeira linha removida continuaria sendo aceito.

Ausência de marcador não é erro do documento — é um documento humano, e o
tratamento está no contrato de materialização.

## Tupla `ESSENTIAL`

Conjunto congelado de substrings cuja presença define conformidade:

> **Este bloco é citação, não declaração.** A tupla viva está em
> `grill_core/goal_document.py`, e é de lá que materializador e validador leem.
> Um documento de especificação não é importado em tempo de execução; SC-006
> mede a árvore de fontes, não a de specs.

```python
ESSENTIAL = (
    "## Contrato de parada",
    "GOAL-HOLD:",
    "## Templates de objetivo",
    "### Template A — trilha pré-ciclo",
    "### Template B — trilha ciclo v4",
    "## Trilha pré-ciclo",
    "## Trilha ciclo v4",
    "PLAN_ONLY_STOP",
    "## Cláusula residual",
    "## Delegação",
    "## Orientação",
)
```

**Por que estes onze e não outros.** Cada item é uma peça sem a qual o laço
autônomo não consegue decidir quando parar:

| Item | O que se perde sem ele |
|---|---|
| `## Contrato de parada` | A forma da sinalização deixa de ser declarada. |
| `GOAL-HOLD:` | O token literal que o juiz do laço pesa. Sem ele o documento descreve uma parada que ninguém emite. |
| `## Templates de objetivo` | A seção normativa que carrega a alternativa de parada para dentro da formulação julgada. |
| `### Template A — trilha pré-ciclo` | A formulação da primeira trilha. |
| `### Template B — trilha ciclo v4` | A formulação da segunda trilha. |
| `## Trilha pré-ciclo` | Os pontos de parada enumerados antes da fronteira. |
| `## Trilha ciclo v4` | Os pontos de parada enumerados depois dela. |
| `PLAN_ONLY_STOP` | O nome da fronteira entre as duas trilhas — a única parada constitucionalmente obrigatória. |
| `## Cláusula residual` | O critério que cobre o que as tabelas não enumeram. Sem ele o laço atravessa o não enumerado. |
| `## Delegação` | O contrato de worker, Evidence Boundary e tier. |
| `## Orientação` | Os verbos que o laço consulta para saber onde está. |

## Regra de conformidade

```text
compatible(text) := text.strip() != "" and all(item in text for item in ESSENTIAL)
```

**Presença, e só presença.** A regra:

- **não** impõe ordem entre os itens — um documento reordenado continua conforme
  (FR-014, Edge Case "partes exigidas mas em ordem diferente");
- **não** proíbe conteúdo adicional — um documento com seções extras, ou com
  texto após a última seção exigida, continua conforme (Edge Case "conteúdo
  adicional depois");
- **reprova** documento vazio ou só com espaço em branco (Edge Case "arquivo
  vazio").

## Congelamento

A tupla é um **literal congelado**. Três proibições explícitas:

1. **Nunca derivada do template.** Computar `ESSENTIAL` a partir dos headings de
   `GOAL.template.md` faria um template mutilado validar-se a si mesmo — o
   validador passaria a confirmar que o template é igual a ele mesmo, que é
   sempre verdade.
2. **Nunca derivada da tupla de outra versão.** `v2`, quando existir, declara a
   sua própria por extenso. Derivá-la de `v1` por um mapa de renomeação faria um
   typo no mapa reescrever o contrato em vez de reprovar um teste — é a mesma
   lição que `grill_core/workflow_versions.py` já registra para `SEQUENCE_V3` e
   `SEQUENCE_V4`.
3. **Nunca redeclarada por consumidor.** Validador, materializador e `init` leem
   deste módulo. Uma segunda cópia é a falha que a 5.0.0 teve de desfazer na CLI.

**Consequência declarada de acrescentar um item**: todo `goal.md` já
materializado em projeto consumidor passa a divergir de uma vez, sem diff e sem
caminho de migração. Por isso uma mudança de contrato é marcador novo com tupla
nova, ao lado da anterior — nunca uma edição da tupla existente.

## Verificação

`tests/validate_goal_document_contract.py` trava:

- que `assets/GOAL.template.md` carrega o marcador na primeira linha;
- que o template é `compatible()` — a tupla e o template concordam;
- que remover **cada** item da tupla, um de cada vez, reprova, e que a saída
  **nomeia o item ausente** (FR-012, SC-005);
- que ordem trocada continua aprovando e conteúdo extra continua aprovando
  (FR-014);
- que documento vazio reprova;
- que `ESSENTIAL` aparece declarada em exatamente um arquivo do repositório
  (SC-006), por busca textual sobre a árvore de fontes;
- tudo sem rede e sem ferramenta externa (FR-013).
