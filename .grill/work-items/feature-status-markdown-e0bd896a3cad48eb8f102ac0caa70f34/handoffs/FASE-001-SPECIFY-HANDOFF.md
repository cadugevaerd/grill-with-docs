# FASE-001 — Status humano determinístico

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: status bruto, status humano, work item coerentemente fechado, pendência operacional, etapa GWD, all good, inicialização pendente, bump obrigatório
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: none

## WHAT
- delivery-units: DU-001, DU-002
- development-type: backend, qa

O comando de status passa a oferecer uma resposta humana única e previsível. Se não houver work item pendente nem etapa GWD pendente, a resposta é somente `all good`. Havendo pendência, a resposta é uma tabela Markdown com as colunas `Item`, `Status` e `Pendência`, uma linha por work item não fechado.

Critérios de aceitação:

1. A interface JSON existente continua sendo o formato padrão da CLI, preserva exit codes e mantém itens fechados visíveis para automações.
2. A skill usa a projeção Markdown canônica e reproduz sua saída sem resumir, traduzir ou reorganizar.
3. Um item só desaparece da tabela quando milestone, estado, fases, auditoria e onze etapas GWD estão coerentemente concluídos e não há finding nem blocker.
4. Um marcador terminal contraditório permanece visível como `blocked`, com as invariantes ausentes na coluna `Pendência`.
5. Pendências em andamento, bloqueadas ou ainda não iniciadas têm classificação e causa estáveis; múltiplos motivos são ordenados e unidos por `; `.
6. Nenhum work item produz uma linha de inicialização pendente, nunca `all good`; erros globais sem item produzem uma linha bloqueada de workspace.
7. Saídas repetidas sobre o mesmo estado são byte-idênticas, seguras para Markdown e comprovadamente read-only.
8. A alteração publica a versão `3.4.0` de forma consistente e com release correspondente à tag após merge.

Escopo excluído: converter o JSON padrão em Markdown; filtrar itens fechados do JSON; exigir reconciliação para fechamento; alterar `gauntlet-status`; mudar o resumo compacto injetado pelos hooks.

## WHY
Hoje o core já coleta um inventário JSON determinístico, mas a resposta humana é montada fora de um contrato único. Cada agente pode selecionar campos, ordem e linguagem diferentes, tornando invocações equivalentes visualmente incompatíveis. A solução precisa fixar a apresentação em código e preservar o JSON usado por testes e automações.

Ocultar um item apenas porque um marcador isolado diz `complete` criaria falso `all good`. O fechamento precisa ser uma conjunção das evidências já mantidas pelo GWD. Da mesma forma, um workspace nunca inicializado não é um workspace concluído: ausência de evidência vira pendência nomeada, coerente com o comportamento fail-closed do plugin.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
