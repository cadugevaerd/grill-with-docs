# FASE-001 — Versão de workflow derivada do documento

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: marcador de workflow, campo derivado, campo constante, detector estrito, par writer/reader, versão ativa do plugin
- ADRs: ADR-0001, ADR-0002
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

Ao criar um work item, o registro de estado passa a dizer qual versão de workflow o repositório efetivamente declara, em vez de repetir um valor fixo. A auditoria passa a aceitar qualquer versão gerenciada legítima nesse registro, em vez de exigir uma específica.

Atores: quem cria um work item (`init`) e quem audita um work item existente (`audit`).

Cenários:

1. Repositório cuja declaração de workflow é v4 — hoje a maioria. O work item nasce registrando v4 e audita sem intervenção. Hoje ele nasce registrando v2; corrigido para v4 à mão, recebe `state: workflow version divergence` e NO-GO.
2. Repositório que preserva uma declaração v3 sob plugin v4. O work item nasce registrando v3, e o restante do sistema passa a julgá-lo pela sequência v3 que ele declara — inclusive a projeção de status, que já lê esse registro. Hoje ele nasce afirmando v4 e é julgado pela sequência errada.
3. Repositório cujo documento de workflow não declara exatamente uma versão gerenciada — nenhuma, ou duas. A criação é recusada, nomeando o que foi encontrado e o que era esperado, e nenhum work item é criado. Hoje ele nasceria e só seria reprovado na auditoria, tarde e longe da causa.
4. Os work items já existentes deste repositório, todos registrando v2 sobre documento v4. O veredito de cada um permanece exatamente o que era. Nenhuma migração, nenhuma reescrita, nenhuma queda de frota.

Escopo: o carimbo feito na criação, a resolução da versão declarada e a asserção correspondente da auditoria.

Fora de escopo: detectar que um registro ficou obsoleto porque o documento migrou depois da criação. Essa verificação mais forte foi avaliada e recusada, porque derrubaria de uma vez todos os work items já publicados, sem prévia e sem caminho de migração. Também fora: reescrever work items já publicados e alterar as ordens canônicas de qualquer versão de workflow.

Critérios de aceitação:

- Um work item criado sobre declaração v4 registra v4 e audita GO sem edição manual do registro.
- Um work item criado sobre declaração v3 registra v3.
- Criação sobre documento sem declaração única é recusada, sem deixar work item parcial, com mensagem que nomeia o encontrado e o esperado.
- Os work items existentes que registram v2 mantêm o veredito atual.
- A suíte de validadores fecha em exit 0, com a matriz de casos coberta a partir do documento real materializado, não de texto derivado do próprio detector.

## WHY

O registro de versão nunca foi verificado. Quem escreve e quem confere compartilham o mesmo valor fixo, então concordam sempre — e um par que só concorda consigo mesmo não é verificação, é decoração. A consequência apareceu quando o valor verdadeiro foi registrado: o único caminho para GO era declarar uma versão falsa. Evidência: `state: workflow version divergence` em NO-GO sobre um documento comprovadamente v4, em 3.4.0, 4.0.0 e 4.0.1.

O mesmo defeito tem uma segunda cópia com consequência maior. A projeção de status foi corrigida em `a188157` justamente para julgar cada work item pela sequência que ele declara, em vez de projetar a sequência mais recente sobre todos. Essa correção depende de o registro dizer a verdade. Com o registro congelado, ela volta a errar pela outra ponta em qualquer repositório que preserve uma declaração anterior — o bug reaparece com sinal trocado, não some.

A verdade já está disponível: a auditoria lê o marcador real do documento e aceita v2, v3 e v4 desde a introdução das versões gerenciadas. Faltava o carimbo transportá-la.

Restrições: nenhum work item já publicado pode mudar de veredito por causa desta mudança — é o que separa esta correção de uma queda de frota, e é a mesma razão pela qual os assets de v3 nunca foram repontados. A mudança toca o plugin publicado, então exige bump de versão nos oito lugares travados pelo validador de distribuição.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
