# FASE-001 — Fence autorizado de atividade órfã

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: atividade órfã, sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, attempt 2, resultado não aceito
- ADRs: ADR-0001
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

### Resultado
Um operador com autorização humana exata consegue encerrar, sem aceitar, uma atividade de especialista órfã ou de sessão retida, de modo que o work item volte a admitir takeover e o contexto sucessor reexecute o autor como attempt 2. A rota é preview-first: a prévia mostra exatamente o que será encerrado e um hash; só a aplicação com esse hash muda o estado.

### Atores
- **Líder sucessor**: sessão nova que precisa assumir o work item e é recusada por trabalho ativo de uma atividade sem dono. Quando o líder anterior está terminal, é o sucessor quem pede o fence, e a própria sessão dele é observada e provada antes de qualquer efeito (DQ-0008).
- **Humano autorizador**: quem decide descartar o trabalho da atividade e assina a autorização exata para este work item, este contexto e esta atividade (no adendo DQ-0007 a decisão chegou como mensagem do coordenador; é esse tipo de recibo que a autorização referencia).
- **Especialista órfão**: sessão de autor cujo dispatch já terminou; ou não gravou resultado (variante 1), ou gravou mas sua sessão ficou retida pelo Orca e nunca poderá provar fechamento (variante 2).
- **Líder corrente**: líder vivo que pede o fence de uma atividade própria de sessão retida; enquanto o líder está vivo, somente o líder corrente exato pode pedir (DQ-0008).

### Cenários
1. **Órfã (caso X7)**: atividade `DISPATCHED`, especialista terminado, líder liberado. Prévia lista a atividade, os dois dispatches e seus veredictos terminais, e o hash. Aplicação com o hash e a autorização exata: atividade termina não aceita, recurso de sessão é fechado com recibo, takeover passa a ser admitido, sucessor prepara attempt 2 como atividade nova.
2. **Sessão retida (caso `interview-author-001` do work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d)**: atividade com resultado gravado, sessão retida pelo Orca, dispatch terminado. Mesma rota; o resultado gravado permanece registrado, mas nunca é aceito nem herdado. Pedido pelo líder corrente exato quando o líder está vivo, ou por sucessor com prova terminal do líder (DQ-0008); a atividade chega a estado terminal não aceito (DQ-0009).
3. **Negativo — sem autorização**: prévia e aplicação recusam com o mesmo código; nada muda no estado.
4. **Negativo — autorização de outro contexto, atividade ou run**: recusa idêntica ao caso 3; nada muda.
5. **Negativo — líder vivo que não é o chamador**: o dispatch do líder da atividade ainda está ativo e o solicitante não é esse líder corrente exato; recusa própria; nada muda (DQ-0008).
6. **Negativo — especialista vivo**: o dispatch do especialista ainda está ativo; recusa própria; nada muda.
7. **Negativo — evidência inconclusiva**: observação ausente, ilegível, não correlacionada ou liveness sem veredicto terminal; recusa de prova não comprovada; nada muda. Inclui o sucessor cuja própria sessão não conclui a observação de prontidão.
8. **Hash stale / replay**: aplicação com hash divergente recusa; aplicação repetida com os mesmos inputs devolve reuso sem segundo efeito.
9. **Aceite tardio**: qualquer tentativa de aceitar a atividade encerrada é recusada.

### Critérios de aceite
- Prévia nunca escreve; o hash da prévia cobre atividade, contexto, solicitante, veredictos e referências das duas observações e a autorização.
- Os quatro negativos de DQ-0006 e o inconclusivo deixam o estado bit a bit igual.
- Após o fence no cenário 1, o takeover é admitido sem alterar a regra de herança de workers; após o fence no cenário 2, a atividade deixa de contar como ativa para takeover e prepare-switch.
- A atividade encerrada não possui aceite, e aceite posterior é recusado.
- A operação de fence fica rastreável ao work item, ao contexto, à atividade, ao solicitante, aos digests observados e à autorização verbatim.
- Attempt 2 nasce como atividade nova no contexto sucessor; nada do resultado encerrado migra.
- Versão do plugin incrementada nos oito pontos de distribuição; suíte de validadores do repositório verde nos três SOs, sem rede.

## WHY
- **Valor**: o X7 está preso: instalar 6.0.30 não destrava (DQ-0005), porque nenhum verbo alcança uma atividade `DISPATCHED` sem líder; a única saída seria editar o Store à mão, o que a Constituição trata como contorno. O work item de origem desta decisão, fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d, caiu no mesmo defeito: com o terminal do líder desconectado, o sucessor é recusado por `TAKEOVER-WORK-ACTIVE` por causa de `interview-author-001`, e o ciclo executor não pode começar lá. Este work item é a menor rota legítima para os dois casos.
- **Evidência**: leituras literais do Store do X7 pelo coordenador (DQ-0001, DQ-0005); estado vivo de `interview-author-001` observado no work item de origem (dispatch `completed`, capability revogada, terminal retido, liveness `unverifiable`, atividade `RESULT_RECORDED`, recurso `CLOSE_PENDING`), que reproduz a variante 2 no próprio repositório e bloqueou o takeover daquele work item; decisões humanas DQ-0002 (escopo A), DQ-0006 (opção A), DQ-0007 (adendo), DQ-0008 (autoridade), DQ-0009 (aresta), DQ-0010 (attempt 2) e DQ-0011 (findings da revisão), migradas sem reabertura.
- **Restrições**: autorização humana é obrigatória e exata (nunca genérica, nunca por flag); prova terminal vem do ambiente, nunca da alegação do chamador; silêncio e expiry não provam; o resultado da atividade encerrada nunca é aceito nem herdado; nada muda na Constituição, no WORKFLOW ou nos registries; fix é plan-only e termina em `PLAN_ONLY_STOP`.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
