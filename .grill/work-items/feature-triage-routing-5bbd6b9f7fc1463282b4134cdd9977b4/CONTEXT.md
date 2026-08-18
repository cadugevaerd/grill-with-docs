# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| Laudo de Causa Raiz | O documento que uma skill de diagnóstico emite ao fim de uma investigação, declarando explicitamente se a causa foi comprovada, não comprovada ou bloqueada por ambiente. | relato de bug, descrição do problema, hipótese | ADR-0001 |
| Rota | O tipo de trilha que um trabalho seguirá: `hotfix`, `bugfix`, `feature` ou `module`. É escolhida por quem investiga e verificada pelo core. | tipo, categoria, label | ADR-0003 |
| Matriz de Evidência | A tabela normativa que declara, por rota, qual evidência é exigida e qual é proibida. É o único critério de roteamento que o core pode aplicar sem interpretar. | heurística, classificador, inferência | ADR-0003 |
| Registro de Triagem | O documento selado que fixa laudo, rota e evidência de uma decisão de roteamento, gravado em `.grill/triage/<id>.json`. | anotação, rascunho de triagem, metadata mutável | ADR-0002 |
| Selo de Triagem | O `triage_sha256` calculado sobre o Registro de Triagem inteiro menos ele próprio, tornando a edição posterior detectável. | checksum informativo, hash de conveniência | ADR-0002 |
| Trilha | A sequência de etapas que uma Rota percorre. `feature` percorre as onze etapas; `bugfix` percorrerá oito; `hotfix` não percorre nenhuma e entrega `HOTFIX-GO`. | fluxo, pipeline, caminho feliz | ADR-0004 |
| Triagem Consultiva | O estado da 3.3.0, em que o Registro de Triagem existe e é verificável mas nenhum comando o exige ainda. | triagem opcional, triagem desligada | ADR-0004 |

## Relationships

- Um **Laudo de Causa Raiz** habilita zero ou uma **Rota**; enquanto não declarar causa comprovada, habilita nenhuma.
- Uma **Rota** é admitida somente quando a **Matriz de Evidência** daquela rota está satisfeita.
- Um **Registro de Triagem** fixa exatamente um **Laudo de Causa Raiz** e exatamente uma **Rota**, e é protegido por um **Selo de Triagem**.
- Cada **Rota** determina uma **Trilha**, e trilhas diferentes percorrem números diferentes de etapas.
- **Triagem Consultiva** é a fase em que o Registro de Triagem existe sem ser pré-requisito de nenhum comando.

## Example dialogue

> **Dev:** "O `init` consegue ler o meu relato e decidir sozinho se isso é bug ou feature?"
> **Domain expert:** "Não. O core é determinístico e não interpreta texto. Quem decide é quem investiga, e o que o core faz é recusar a **Rota** cuja **Matriz de Evidência** não estiver satisfeita — e recusar qualquer rota enquanto o **Laudo de Causa Raiz** não declarar causa comprovada."

## Flagged ambiguities

- "triagem" em uso corrente pode significar priorizar um backlog; aqui significa exclusivamente decidir a **Rota** de um trabalho a partir de um **Laudo de Causa Raiz**.
- "severidade" é entrada declarada pelo operador, não medição: ela participa da **Matriz de Evidência** de `hotfix` e não é inferida de nada.

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.
