# FASE-001 — Suspensão e reativação da apresentação local no core

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: apresentação local, suspensão, reativação, fonte não-agente da sessão, bloco de compactação
- ADRs: ADR-0001, ADR-0002, ADR-0003
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

**Resultado observável.** Quem conduz um fluxo GWD pode dizer `stop adhd mode` e continuar trabalhando sem a apresentação, inclusive depois de compactar o contexto e de atualizar o plugin, e pode dizer `start adhd mode` para voltar ao padrão, com nova leitura. O estado exposto pelo preflight e pelos verbos do fluxo passa a refletir essas escolhas.

**Atores.** Quem conduz a sessão GWD; o coordenador Orca que fala com um worker; quem audita o estado de apresentação.

**Cenários.**
1. Sessão ativa, usuário diz `stop adhd mode`: apresentação suspensa, trabalho liberado, sem pedido de recarga.
2. Suspensa e compactada na mesma sessão: continua suspensa, trabalho liberado, sem recarga.
3. Suspensa, usuário diz `start adhd mode`: volta ao padrão ativo e exige nova leitura integral antes do uso.
4. A frase aparece só em fala do agente ou em resumo de compactação: nada muda.
5. Suspensa e o plugin ou a configuração da sessão mudam: continua suspensa e trabalhando; a leitura da versão nova acontece na reativação.
6. Ativa e compactada, sem suspensão: exige nova leitura, como hoje.
7. Nova sessão, runtime ou incarnation: começa ativa, sem herdar suspensão.

**Escopo excluído.** Conformidade das respostas do modelo (achado F1); reexecução da matriz T029, que pertence ao work item de origem.

**Critérios de aceite.**
- Os sete cenários cobertos por validação automatizada, sem runtime real, rede ou processo externo, com eventos no formato real do harness.
- O registro de suspensão identifica a mensagem de origem.
- Nenhum código de recusa existente muda de significado.
- Suíte completa do projeto em exit 0 e diff limpo.

## WHY

**Valor.** Hoje `stop adhd mode` não tem efeito no core: depois de compactar, o fluxo pede a recarga que a própria suspensão proíbe, e quem cumpre o contrato é a sessão, por conta própria. É pré-requisito da feature `new-subagents-unified` (achado F2 do T029).

**Evidência.** Triagem `tri-presentation-suspension` com laudo de causa raiz comprovada: a projeção de apresentação nunca produz suspensão; a tradução do marcador de compactação já existe e só falta teste.

**Restrições.** Fail-closed sem waiver: autorrelato do agente nunca suspende nem reativa. Somente biblioteca padrão, sem processo novo e sem rede. A versão publicada corrente é 6.0.28; a entrega exige bump patch acima da versão publicada no momento do ship, nos oito pontos de versão, e a release correspondente.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
