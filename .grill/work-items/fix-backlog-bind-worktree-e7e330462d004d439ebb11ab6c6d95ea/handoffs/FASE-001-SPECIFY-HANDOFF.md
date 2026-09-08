# FASE-001 — Resolver o backlog vinculado de qualquer worktree do repositório

- phase: FASE-001
- state: complete
- roadmap: ROADMAP.md#FASE-001
- context-refs: worktree de controle, worktree linkada, caminho vinculado, conjunto de candidatos, resolução do backlog, seam de toolchain, carimbo de escape
- ADRs: ADR-0001, ADR-0002
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

**Resultado observável.** `preflight`, `init` e os verbos `backlog-*` executados numa
worktree linkada de um repositório já vinculado encontram o backlog como `BOUND`, com o
mesmo código que a worktree de controle encontra. `--skip-backlog` deixa de ser necessário
para trabalhar em worktree.

**Atores.** Quem abre uma worktree para um work item e roda a CLI do grill nela; a suíte de
validadores, que passa a exercer a resolução a partir de uma worktree linkada.

**Cenários.**
1. Backlog vinculado à worktree de controle, comando rodando numa linkada → `BOUND`.
2. Backlog vinculado a uma worktree linkada, comando rodando na de controle ou noutra
   linkada → `BOUND`, sem re-apontar o vínculo.
3. Repositório sem backlog, comando rodando numa linkada → `NEEDS-CREATE` com nome e
   código derivados da worktree de controle; `bind` aplicado grava o caminho da de controle.
4. Dois backlogs de códigos distintos vinculados a worktrees do mesmo repositório → recusa
   explícita nomeando ambos; nada muda.
5. Enumeração de worktrees indisponível → comportamento atual (comparação com o próprio
   caminho), sem exceção não tratada.
6. Caminho vinculado aponta a worktree já removida → continua `NEEDS-CREATE`, como hoje;
   fora do escopo (DQ-0005).

**Escopo excluído.** Re-apontar vínculo obsoleto (DQ-0005, condição pré-existente); mudar a chave do vínculo no
backlogctl; migrar ou re-vincular backlogs existentes; qualquer mudança fora da ponte e
do seu contrato de teste.

**Critérios de aceite.**
- `preflight` nesta worktree devolve `backlog.status = BOUND` e `code = SGD`.
- Existe caso de teste em que a raiz é uma worktree linkada e o caminho vinculado é a de
  controle, com verdict `BOUND`; existe um caso com `git worktree add` real.
- `python3 tests/run_validators.py` em exit 0.
- Nenhum código de erro público muda de string; nenhum vínculo existente é alterado.
- Versão do plugin incrementada nos oito lugares que o validador de distribuição fixa,
  antes de merge.

## WHY

**Valor.** O fluxo oficial deste projeto é um work item por worktree, e o backlog é
pré-requisito de `init` desde a 3.0.0. Com o bug, os dois requisitos se contradizem: todo
`init` em worktree precisa contornar o backlog, todo bundle nasce carimbado e a adoção só
fecha depois do merge. O fix devolve a coerência entre os dois contratos.

**Evidência.** Reproduzido nesta sessão: `preflight` nesta worktree propõe criar `CFB`
enquanto `SGD` já existe vinculado à worktree de controle. A ponte compara caminho por
igualdade de string; o core, no mesmo pacote, já deriva identidade de repositório de forma
independente de worktree. A suíte não pegou porque todos os casos de resolução usam o
mesmo caminho dos dois lados da comparação.

**Restrições.** O backlogctl é de outro repositório e não muda aqui; o vínculo continua
sendo um caminho por código. A ponte nunca re-vincula em silêncio, então binds já feitos a
worktrees linkadas têm de continuar válidos como estão. A entrega altera `plugin/**`, o que
obriga bump antes do merge; a leitura proposta é patch e fica como assunção a confirmar.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
