# FASE-001 — Atestação ancorada na versão declarada

- phase: FASE-001
- state: blocked
- roadmap: ROADMAP.md#FASE-001
- context-refs: versão declarada, versão ativa, registry ancorado, resolução de skill, código de contrato, escopo declarado, reivindicação histórica, conflito de escopo
- ADRs: ADR-0001, ADR-0002
- BLs: BL-0001

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

Cada checkpoint deve ser julgado pelo registry correspondente à versão que o próprio work item declara. Isso vale simultaneamente para itens v3 e v4 no mesmo runtime e não admite fallback silencioso para a versão ativa.

Atores: operador que avança um checkpoint; work item que declara sua versão; consumidor que precisa distinguir bloqueio previsto de defeito inesperado.

Cenários:

1. Um item v3 apresenta atestação de `agent-assign` ou `agent-execute`. O gate usa o registry v3, reconhece o passo e avalia a cadeia completa.
2. Um item v4 apresenta atestação de etapa v4. O gate usa o registry v4 e mantém o comportamento vigente.
3. Um chamador tenta julgar atestação sem declarar versão. A operação recusa na fronteira; a versão ativa não é inferida.
4. A versão declarada resolve uma skill como indisponível para o runtime. O operador recebe `UNATTESTED-STEP-OUTPUT` e a razão específica, nunca `UNEXPECTED-FAILURE`.
5. Uma resolução carrega digest de registry diferente do registry da versão declarada. A atestação é recusada como divergente.

Critérios de aceitação:

- Itens v3 e v4 são julgados contra seus respectivos registries no mesmo processo.
- As três entradas públicas exigem versão declarada keyword-only e sem default.
- O checkpoint usa o valor do estado do work item, sem ler versão do receipt como autoridade.
- Skill não resolvida preserva código e razão previstos pelo contrato.
- Regressões de campanha, predecessor, contexto e integridade continuam verdes.
- O plugin recebe bump patch sincronizado e a distribuição valida em exit 0.
- BL-0001/SGD-24 é resolvido antes de a fase sair de `blocked`.

## WHY

O defeito permaneceu oculto enquanto todos os bundles eram carimbados como v4. A correção da derivação no work item dependente torna o caminho v3 real e revela que a atestação ainda escolhe o registry ativo. Com isso, etapas legítimas de v3 aparecem como inexistentes; a exceção prevista ainda escapa ao catch-all e vira `UNEXPECTED-FAILURE`.

Evidência: a cadeia termina em carregamento sem versão, embora o loader aceite seleção explícita; o checkpoint já possui `development.workflow_version`, mas não o propaga; a fronteira do CLI não captura a exceção de resolução. A Constituição exige versão resolvida a partir do artefato e tratamento fail-closed.

Restrição: o escopo real sobrepõe um recibo histórico concluído. O conflito é defeito separado do reconciliador, registrado em BL-0001/SGD-24. A fase não pode receber GO enquanto esse bloqueio persistir, e o escopo não pode ser omitido para contorná-lo.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
