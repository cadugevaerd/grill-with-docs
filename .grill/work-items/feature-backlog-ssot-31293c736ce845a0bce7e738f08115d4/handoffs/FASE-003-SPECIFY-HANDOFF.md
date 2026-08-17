# FASE-003 — Pré-requisito fail-closed

- phase: FASE-003
- state: planned
- roadmap: ROADMAP.md#FASE-003
- context-refs: Autoridade de estado, Backlog operacional
- ADRs: ADR-0001
- BLs: none

## WHY
O backlog operacional era pré-requisito pretendido deste repositório, mas nunca foi exigido: é a única dependência declarada como opcional entre as dez, e a contagem de faltantes só considera as exigidas. A consequência é que a opção de exigir dependências nunca bloqueou por falta de backlog, e a vinculação do repositório só acontecia sob uma autorização de instalação que raramente é passada. Um repositório consumidor novo, portanto, nunca ficava vinculado.

Sem vínculo, o espelho recusa de forma nomeada — e como nada o invocava, a recusa nunca aparecia. O pré-requisito existia no discurso e não no gate.

A cláusula constitucional proíbe waiver implícito. Uma saída nomeada, versionada e carimbada não é implícita, e há precedente no projeto para uma opção de desligamento que nunca é reportada como conforme. Sem o carimbo, porém, um work item criado pela saída ficaria indistinguível de um conforme, e o gate passaria a mentir sobre o próprio pré-requisito — por isso o registro é parte da decisão, não um detalhe. Remover a saída por completo quebraria dois pontos da verificação automatizada e todo consumidor que crie work item em ambiente sem o backlog.

## WHAT
- delivery-units: DU-003
- development-type: platform-devops

O backlog operacional vira exigência declarada, e a criação de um work item recusa sem ele.

Resultado observável: a dependência aparece como exigida no relatório; criar um work item sem backlog resolvido e vinculado recusa de forma nomeada; existe uma única saída explícita para ambientes sem backlog; e o uso dessa saída fica carimbado no work item, de modo que um work item criado assim não alcança aprovação sem antes vincular o backlog.

Atores: o operador em máquina comum, o operador em ambiente isolado sem rede, e a verificação automatizada que roda sem o backlog instalado.

Cenários que precisam passar:
- criação com backlog vinculado, que segue normalmente;
- criação sem backlog, que recusa;
- criação com a saída explícita, que prossegue e fica carimbada;
- work item carimbado tentando alcançar aprovação, que precisa ser barrado.

Escopo excluído: remover a saída explícita e alterar a matriz de verificação.

Critérios de aceite: recusa sem vínculo; saída explícita registrada e jamais reportada como conforme; work item carimbado não alcança aprovação.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
