# Contrato: tupla `ESSENTIAL` do `goal.md`

**Fase 1** | **Task**: T003 (ADR-0003)

Esta tupla é o portão de compatibilidade do `goal.md`, no mesmo desenho de
`workflow_v3.ESSENTIAL` / `workflow_v4.ESSENTIAL`: um `all(item in text for
item in ESSENTIAL)`, checagem de presença de substring, sem ordem nem posição.
Ela **não** substitui validação estrutural (contagem de seções, uma única
ocorrência de H1, ordem das trilhas) — essa é entrega da FASE-003 (ADR-0008).
Aqui só se fixa: o texto está presente ou não.

## Marcador

```text
<!-- grill-with-docs-goal:v1 -->
```

Independente da versão SemVer do plugin (ADR-0003). Nunca reescrito ao lado de
`ensure_workflow.MARKER`, `workflow_v3.MARKER` ou `workflow_v4.MARKER` — é
identidade própria do `goal.md`, versionada `v1` por conta própria.

## Origem das entradas

Nenhuma entrada abaixo deriva, copia ou transforma qualquer item de
`workflow_v3.ESSENTIAL`, `workflow_v4.ESSENTIAL` ou `ensure_workflow.ESSENTIAL`.
Onde o texto literal já existe em outro contrato desta fase (`stop-signal.md`,
`goal-objective-templates.md`) ou em `data-model.md`, a entrada **reaproveita**
esse texto como âncora — porque ele já é normativo ali, não porque foi copiado
de um workflow. Onde nenhum documento anterior fixa texto (título, cabeçalhos
de trilha, delegação, orientação), a entrada é **cunhada aqui pela primeira
vez**: este arquivo é quem fixa esse literal, e `GOAL.template.md` (T002/T028)
precisa conter exatamente esse texto.

## Tupla (literal congelado, ordem de leitura = ordem de `data-model.md` §Documento)

```python
ESSENTIAL = (
    "<!-- grill-with-docs-goal:v1 -->",
    "Loop de objetivo — grill-with-docs",
    "## Contrato de parada",
    "GOAL-HOLD:",
    "ou quando a resposta contiver a linha GOAL-HOLD:",
    "## Templates de objetivo",
    "Template A",
    "Template B",
    "## Trilha pré-ciclo",
    "## Trilha ciclo v4",
    "## Cláusula residual",
    "## Delegação",
    "## Orientação",
    "HOLD-PRE-01",
    "SAFETY_STOP",
    "BLOCKED-CONSTITUTION",
    "ROOT-CAUSE-UNPROVEN",
    "PLAN_ONLY_STOP",
    "HOLD-V4-01",
    "BLOCKED_CAPABILITY",
    "GRANT-SCOPE-VIOLATION",
    "INTEGRATION-CONFLICT",
    "HOLD-V4-02",
)
```

## Justificativa por entrada

| # | Substring | Bloco de §Documento que fixa | Por que este comprimento exato |
|---|---|---|---|
| 1 | `<!-- grill-with-docs-goal:v1 -->` | marcador | É o valor inteiro do campo `marcador` na tabela de `data-model.md` (linha 18). Mais curto perderia o número de versão do marcador (`v1`), que é o que distingue este documento de uma v2 futura; mais longo (ex.: incluir a quebra de linha) tornaria a checagem frágil a como o editor grava EOL. |
| 2 | `Loop de objetivo — grill-with-docs` | título | Nenhum documento anterior fixa o texto do H1. Cunhado aqui: é o texto que `GOAL.template.md` deve conter na primeira linha de título. Sem o `#` de Markdown porque a checagem é de substring de conteúdo, não de sintaxe — exigir o `#` quebraria se o nível do cabeçalho mudasse por reformatação sem mudar o sentido. |
| 3 | `## Trilha pré-ciclo` | trilhas (id `pre-ciclo`) | Cunhado aqui, no vocabulário que `data-model.md` já usa para nomear a entidade (`id: pre-ciclo`). Com `##` porque distingue o título da seção do id solto `pre-ciclo`, que também aparece em prosa corrida e não seria uma âncora estrutural confiável sozinho. |
| 4 | `## Templates de objetivo` | trilhas (id `ciclo-v4`) | Mesmo raciocínio da entrada 3, para a segunda trilha. `ciclo v4` (com espaço) em vez do id `ciclo-v4` (com hífen) porque é assim que o título em prosa se lê; o id com hífen já não seria um cabeçalho legível. |
| 5 | `Template A` | templates de objetivo, trilha pré-ciclo | Já é o rótulo literal usado em `goal-objective-templates.md` (`## Template A — trilha pré-ciclo`) e em `tasks.md` T006. Sem o sufixo `— trilha pré-ciclo` porque esse sufixo é prosa explicativa, não o rótulo — poderia ser reescrito sem quebrar o contrato; `Template A` sozinho é o identificador estável. |
| 6 | `Template B` | templates de objetivo, trilha ciclo v4 | Mesmo raciocínio da entrada 5, espelhando `goal-objective-templates.md` e T007. |
| 7 | `ou quando a resposta contiver a linha GOAL-HOLD:` | contrato de parada (alternativa de parada dentro dos templates) | Frase literal e obrigatória em **ambos** os templates, fixada em `goal-objective-templates.md` §Invariantes e em `data-model.md` linha 60. Citada aqui por inteiro — nem truncada, nem parafraseada — porque `data-model.md` já afirma que reescrevê-la como instrução separada devolve o modo de falha que ela existe para derrotar; uma âncora mais curta (ex.: só `GOAL-HOLD:`, já coberta pela entrada 8) não provaria que a frase de alternativa continua colada à formulação julgada. |
| 8 | `GOAL-HOLD:` | contrato de parada (forma do sinal) | Forma fixada em `stop-signal.md` (`GOAL-HOLD: <motivo>`). Só o prefixo com dois-pontos, sem `<motivo>`, porque o motivo é variável por natureza — exigir texto de motivo fixo tornaria a checagem inútil para qualquer resposta real do laço. |
| 9 | `PLAN_ONLY_STOP` | pontos de interação, trilha pré-ciclo (ponto obrigatório) | Id do único ponto marcado `obrigatório: true` na trilha pré-ciclo (`data-model.md` linha 94, tabela pré-ciclo). É também o nome da cláusula constitucional citada em `CLAUDE.md`. Token exato porque é o que o núcleo emite; qualquer variação de maiúsculas/hífen deixaria de casar com a saída real. |
| 10 | `HOLD-V4-01` | pontos de interação, trilha ciclo v4 (ponto obrigatório) | Id do ponto marcado `obrigatório: true` na trilha ciclo-v4 (`data-model.md` linha 100, condição "autorização de `ship`"). Ancorar no id `HOLD-V4-01`, e não na palavra solta `ship`, evita falso positivo: `ship` aparece como substring dentro de palavras comuns (`leadership`, `relationship`) e não prova que a tabela de pontos de interação está presente — o id não. |
| 11 | `cláusula residual` | pontos de interação (cláusula residual) | Termo já canônico e repetido sem variação em `data-model.md` (`## Entidade: Cláusula residual`), `spec.md` e `tasks.md` (T018/T019). Reaproveitado como está, em minúsculas, porque é assim que aparece em prosa corrida nesses documentos — exigir maiúscula inicial quebraria sempre que a frase não abrir período. |
| 12 | `## Delegação` | delegação | Cunhado aqui; nomeia a seção com a mesma palavra que `data-model.md` usa para a entidade (`Entidade: Worker delegado`) e que `ADR-0006` usa para a prática. Forma de cabeçalho (`##`) para distinguir de menções soltas à palavra "delegação" em prosa. |
| 13 | `## Orientação` | orientação | Cunhado aqui; único bloco de §Documento sem nenhum termo literal fixado em outro contrato desta fase (a lista de verbos em si não é normativa — FR-016 só exige que existam). A âncora fixa que a seção existe, não seu conteúdo verbal, que pode legitimamente mudar conforme os verbos do core mudam. |

## O que esta tupla **não** garante

- Que as duas tabelas de pontos de interação estejam completas linha a linha —
  isso é o levantamento de T001/`interaction-points.md` e a conferência de
  T025.
- Que a ordem das seções siga `data-model.md` §Documento — ordem é checagem
  estrutural, fora do que `all(item in text for item in ESSENTIAL)` mede.
- Que não haja duas linhas `GOAL-HOLD:` na mesma resposta emitida pelo laço —
  isso é comportamento de runtime, não do documento estático.

## Verificação cruzada (T028)

A Fase 7 confere que todo item desta tupla aparece, byte a byte, em
`plugin/skills/grill-with-docs/assets/GOAL.template.md`. Divergência ali é
sinal de que este arquivo ou o template mudou sem o outro — a tupla é a fonte
da verdade para o que o template **precisa** conter, não o inverso.


## Nota de alinhamento (leader, wave-0001)

A tupla foi escrita em paralelo ao esqueleto e usava três âncoras que o
documento não tem: `Loop de objetivo — grill-with-docs` (o título real é
`Loop de objetivo — grill-with-docs`), `## Trilha pré-ciclo` e
`## Trilha ciclo v4` (o `data-model.md` §Documento define **uma** seção
`## Trilha pré-ciclo`, com as duas trilhas dentro dela).

Os dois workers da wave não podiam ver o trabalho um do outro — arquivos
disjuntos, nenhum conflito de merge —, então a divergência só apareceu na
verificação. O `data-model.md` §Documento é o SSOT do desenho e as âncoras foram
alinhadas a ele, não o contrário.


## Revisão de convergência (T032–T035)

A avaliação de `converge` encontrou quatro lacunas de âncora. Nenhuma era
conteúdo ausente no documento; todas eram seções e identificadores reais que a
tupla deixava de fixar, e portanto que um documento mutilado poderia perder sem
reprovar o validador da FASE-003.

| Acrescentado | Por quê |
|---|---|
| `## Contrato de parada` | A seção que define a parada é o núcleo do documento e não tinha âncora estrutural. |
| `## Trilha ciclo v4` | A âncora existia na primeira redação da tupla e se perdeu numa tentativa de alinhamento ao esqueleto. A segunda trilha ficava desprotegida. |
| `## Cláusula residual` | Substitui a forma minúscula `cláusula residual`, que casava em prosa corrente e não garantia que a seção existisse. |
| Nove identificadores de ponto | Das dezoito linhas das duas tabelas, apenas `PLAN_ONLY_STOP` e `HOLD-V4-01` estavam fixados. Os acrescentados cobrem as duas paradas obrigatórias e ao menos um representante de cada uma das cinco classes de fonte de FR-006. |

A ordem da tupla passa a seguir a ordem das seções no documento, o que torna uma
inversão de seções visível na leitura do próprio contrato.
