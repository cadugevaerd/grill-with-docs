# FASE-001 — Triagem selada

- phase: FASE-001
- state: complete
- roadmap: ROADMAP.md#FASE-001
- context-refs: Laudo de Causa Raiz, Rota, Matriz de Evidência, Registro de Triagem, Selo de Triagem
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

Um operador que investigou um problema e comprovou a causa raiz consegue registrar, de forma verificável e reexecutável, qual rota aquele trabalho deve seguir.

Atores: o operador que conduz a sessão, e a skill de diagnóstico que produz o laudo.

Cenários:
- Laudo comprova a causa e a evidência da rota está completa: a decisão é registrada e fica selada.
- Laudo comprova a causa mas falta evidência que a rota exige, ou sobra evidência que ela proíbe: a decisão é recusada nomeando os campos exatos.
- Laudo não comprova a causa, ou está bloqueado por ambiente: nenhuma rota abre.
- Laudo não é um relatório de diagnóstico, ou tem seção obrigatória vazia: a recusa nomeia a seção faltante.
- A mesma decisão é registrada de novo: é reconhecida como a mesma, sem duplicar.
- O registro é editado depois: a adulteração é detectada.

Escopo: quatro rotas — incidente, defeito contra spec existente, funcionalidade nova e módulo novo. Fora de escopo: exigir a triagem em qualquer comando existente, e a sequência de etapas de cada rota.

Critérios de aceite: uma rota só abre a partir de laudo que comprova a causa raiz com a evidência que aquela rota exige; a decisão registrada é resistente a adulteração; nenhuma execução recusada escreve byte algum.

## WHY
O tipo de trabalho hoje é declarado por quem digita o comando e nada o verifica: `feature` e `fix` produzem bundles idênticos byte a byte, e a única diferença de comportamento por tipo em todo o produto é a obrigatoriedade de um artefato na auditoria. Não existe etapa onde investigar: o ciclo começa pedindo o quê e o porquê, o que pressupõe a causa conhecida sem nunca verificar que seja.

A evidência de que o problema é real está no próprio repositório: a extensão de bugfix é exigida fail-closed, instalada em toda máquina, e nunca invocada por lugar nenhum — uma trilha de correção declarada e inexistente.

Restrições: o core é determinístico e não interpreta linguagem natural, e três contratos existentes já impõem isso; nenhuma etapa pode tocar a rede ou depender de ferramenta externa real; a superfície pública de comandos existentes não pode mudar nesta fase.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
