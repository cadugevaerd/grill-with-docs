# FASE-001 — Destravar a ponte com o backlog operacional

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: Backlog de decisão, Backlog operacional, Item de backlog, Referência de decisão
- ADRs: ADR-0003
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: backend

A ponte entre o work item e o backlog operacional passa a funcionar sobre um bundle real, com decisões já escritas.

Resultado observável: para um work item com decisões adiadas registradas, o espelho reporta e aplica sem recusar o bundle por ter artefatos escritos; decisões em qualquer estado são espelhadas, não apenas as abertas; e reexecutar o espelho não cria item repetido.

Atores: o operador que conduz a sessão de decisão e o backlog operacional vinculado ao repositório.

Cenários que precisam passar:
- work item com decisão adiada em aberto, espelhada pela primeira vez;
- work item cujas decisões já foram todas encerradas, hoje invisível para o espelho;
- segunda execução sobre o mesmo work item, que não pode produzir item novo;
- ausência do backlog vinculado, que continua recusando de forma nomeada.

Escopo excluído: geração da projeção versionada, mudança do pré-requisito e migração de bundles antigos.

Critérios de aceite: espelho opera sobre bundle com artefatos escritos; nenhuma duplicata em reexecução; estados refletidos conforme ADR-0003.

## WHY
Dos oito registros de decisão adiada existentes em quatro work items, apenas um chegou ao backlog operacional; os outros quatorze itens do backlog foram criados à mão. A integração existe e está desligada.

Três causas independentes se somam aqui. O gate de integridade compara os arquivos vivos contra o estado de criação do bundle, então escrever uma decisão é exatamente o que o invalida — a recusa foi reproduzida nos três work items existentes. O filtro que só espelha decisões abertas se combina com o gate que reprova decisões abertas, de modo que a única janela em que o espelho tem trabalho é a janela em que o trabalho está bloqueado. E o armazenamento aceita duplicata sem erro, verificado em banco descartável, o que torna a deduplicação responsabilidade de quem escreve.

Esta fase é pré-requisito das demais: sem destravar a escrita, nem a migração planejada consegue produzir seus artefatos.

Restrição: a matriz de verificação não dispõe do backlog operacional real, então toda cobertura precisa entrar por ponto de injeção já existente.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
