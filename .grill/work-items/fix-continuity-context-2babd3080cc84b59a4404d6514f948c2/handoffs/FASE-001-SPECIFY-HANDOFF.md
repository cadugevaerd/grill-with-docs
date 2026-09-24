# FASE-001 — Continuidade de contexto sem líder vivo

- phase: FASE-001
- state: complete
- roadmap: ROADMAP.md#FASE-001
- context-refs: contexto de orquestração, observação de líder, dispatch terminal, tomada de contexto, troca preparada, checkpoint de continuidade
- ADRs: ADR-0001, ADR-0002
- BLs: BL-0001

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

**Resultado observável.** Um work item cujo líder encerrou volta a ser trabalhável: uma sessão nova assume o contexto quando o encerramento do líder anterior está provado pelo host, e passa a conduzir o ciclo com a própria identidade. A troca ordenada entre sessões passa a ser possível desde o momento em que o work item é criado, sem depender de uma etapa já confirmada. Quem pede uma prévia de adoção recebe o mesmo veredito que o comando efetivo daria.

**Atores.** Quem conduz um ciclo e perde a sessão; quem passa o trabalho de um runtime a outro; quem audita o registro de contexto depois.

**Cenários.**
1. Líder anterior comprovadamente encerrado, sessão nova pede a tomada: a tomada é aceita, o contexto anterior fica encerrado, o novo assume com época seguinte, e estado, campanha, receipts e escopo continuam intactos.
2. Líder anterior ainda ativo: a tomada é recusada, com o mesmo rigor de hoje.
3. O host não responde, responde sem conclusão ou a resposta é ambígua: a tomada é recusada, por ausência de prova, e a recusa diz isso.
4. Work item recém-criado, sem nenhuma etapa confirmada: a troca ordenada pode ser preparada e a outra sessão retoma por ela.
5. Prévia de adoção diante de contexto de outra sessão: a prévia devolve a mesma recusa que o comando efetivo devolveria, sem escrever nada.
6. Retomada de um checkpoint criado antes desta entrega: continua funcionando, sem reescrita nem nova selagem.
7. Tomada pedida sobre um líder que nunca foi um trabalho observável pelo host: recusa nomeada, sem exceção aberta.

**Escopo excluído.** Comparar, na retomada, os digests do documento de workflow e da Constituição (BL-0001); observação de compactação e de suspensão de estilo, que pertence a outro work item; qualquer reescrita de checkpoint já selado.

**Critérios de aceite.**
- Os sete cenários cobertos por validação automatizada, sem depender de runtime real, rede ou processo externo.
- Registro de contexto mostra a sucessão: contexto anterior encerrado, contexto novo com época seguinte, e o motivo da tomada.
- Nenhum código de recusa existente muda de significado; a tomada tem código próprio quando recusada.
- Suíte completa do projeto em exit 0 e verificação de diff limpa.
- Reexecução do caso C2 da matriz T029: uma sessão nova retoma o work item criado por outra e chega ao trabalho. Essa evidência pertence ao work item de origem, não a esta fase.

## WHY

**Valor.** Hoje um work item fica preso para sempre se a sessão que o criou encerrar antes da primeira etapa confirmada. Foi o que aconteceu duas vezes em 2026-09-19 e é o que bloqueia a metade Codex da matriz de estilo.

**Evidência.** Triagem `tri-continuity-context` com laudo de causa raiz comprovada: a recusa persiste mesmo com o contexto e o líder anteriores encerrados, porque não existe transição de saída; e a prévia de adoção não executa a verificação que o comando efetivo executa.

**Restrições.** Fail-closed sem waiver: a autorização vem de prova do host, nunca do pedido; ausência de resposta não autoriza. Somente biblioteca padrão, sem processo novo e sem rede. Nenhum checkpoint selado é reescrito. A versão publicada corrente é 6.0.2; esta entrega exige bump patch para 6.0.3 nos oito pontos de versão e a release correspondente.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
