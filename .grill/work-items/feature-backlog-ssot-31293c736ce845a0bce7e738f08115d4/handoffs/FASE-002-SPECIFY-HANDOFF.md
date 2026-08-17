# FASE-002 — Projeção versionada e determinística

- phase: FASE-002
- state: complete
- roadmap: ROADMAP.md#FASE-002
- context-refs: Projeção, Evidência no commit, Autoridade de estado
- ADRs: ADR-0001, ADR-0002
- BLs: none

## WHY
A autoridade sobre o ciclo de vida das decisões passa para o backlog operacional, que vive fora do controle de versão e é global por máquina. A cláusula constitucional de rastreabilidade exige que decisões sejam rastreáveis ao work item e ao commit, e um registro que só existe em banco local não é rastreável a commit nenhum.

Um clone do repositório em máquina nova não carrega esse banco. Sem artefato versionado, o repositório traria o código e teria perdido suas decisões adiadas.

O caso decisivo é a revisão: quem clona a branch não tem os itens deste work item na própria máquina, e pode ter um backlog homônimo com conteúdo diferente. Por isso a verificação de frescor não pode ser pré-condição do gate — ela travaria ou acusaria divergência falsa na máquina do revisor.

## WHAT
- delivery-units: DU-002
- development-type: backend

O registro versionado de decisões adiadas deixa de ser escrito à mão e passa a ser derivado da autoridade.

Resultado observável: gerar duas vezes seguidas produz bytes idênticos; o artefato carrega o identificador da fatia de autoridade que o originou; a auditoria valida o artefato sem consultar processo externo; e existe um comando explícito que compara artefato e autoridade, para quem tem o backlog disponível.

Atores: o operador que conduz a sessão, o revisor que só tem o repositório, e a verificação automatizada que roda sem o backlog instalado.

Cenários que precisam passar:
- geração repetida sem mudança, que precisa ser no-op byte a byte;
- auditoria em máquina sem o backlog operacional, que precisa concluir;
- artefato editado à mão, que precisa ser detectado;
- falha depois de registrar a decisão na autoridade e antes de escrever o artefato, cuja geração seguinte precisa incorporar o registro órfão.

Escopo excluído: consultar a autoridade dentro do gate de auditoria.

Critérios de aceite: reexecução byte-idêntica; auditoria conclui sem processo externo; divergência entre artefato e autoridade é detectável pelo comando de verificação.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
