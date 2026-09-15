# FASE-001 — Children Orca independentes de CLI

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: sessão líder, coordenador, child, Run, Dispatch, especialista, worker, caminho degradado, candidata 6.0.0
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006
- BLs: BL-0001

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

**Resultado.** Em qualquer etapa com especialista (autor ou revisor) ou worker, o agente que conduz o GWD sabe exatamente como iniciar cada um como child Orca e faz isso da mesma forma no Claude Code e no Codex.

**Atores.** Humano; sessão líder (coordenador); children especialistas; children workers; Orca.

**Cenários.**
1. Com Orca pronto e líder no Claude Code, cada autor, revisor e worker é iniciado como child, e cada child fica identificável por Run, Task e Dispatch.
2. O mesmo cenário com líder no Codex produz a mesma sequência observável, mudando só o agente e o par modelo/esforço da coluna do runtime.
3. Com o Orca ausente ou sem runtime pronto, o preflight/init reporta a falta, e a etapa com child recusa com código nomeado antes de iniciar qualquer child.
4. Se o lançamento na CLI padrão falhar com recusa observada, ou se o humano pedir explicitamente, o child pode usar a outra CLI, e a troca fica registrada com motivo. Troca sem uma dessas causas é recusada.
5. Se o modelo ou esforço efetivo do child divergir do pedido, o despacho é bloqueado.
6. Um worker roda dentro do worktree isolado do seu nó, e o escopo de arquivos continua sendo verificado na convergência.
7. A auditoria de uma etapa concluída mostra, para cada child, identificação, agente, pedido e efetivo de lançamento, desfecho, liberação e eventual troca de CLI, sem depender de acesso ao Orca.

**Escopo.** Incluído: os sete cenários acima, a declaração do Orca como pré-requisito obrigatório e a nova versão MAJOR. Excluído: mudanças no Orca, conteúdo de conversa dos children, emenda da Constituição, alteração do workflow e dos registries.

**Critérios de aceite.**
- Nenhuma instrução do GWD manda iniciar especialista ou worker por mecanismo de subagente fora do Orca.
- Os cenários 1 e 2 são demonstrados ao vivo nos dois runtimes.
- Os cenários 3, 4 e 5 terminam em recusas nomeadas, cobertas por testes sem rede e sem Orca real.
- A versão publicada é 7.0.0, consistente nos locais travados pela distribuição.

## WHY

**Valor.** Hoje o agente não sabe como invocar children: o GWD fala em "subagente" nativo, que só existe no Claude Code, e o Orca aparece apenas como caminho opcional. Resultado: comportamento diferente por CLI, independência do revisor dependente do runtime e tier de modelo que não se consegue provar.

**Evidência.** O `init` da candidata 6.0.0 recusou com `LEADER-ADAPTER-UNSUPPORTED` nesta sessão, porque exige que o próprio líder seja um Dispatch, o inverso do modelo coordenador do guia Orca 1.4.200. A skill de implement-parallel despacha subagente nativo com `model: sonnet`.

**Restrições.** Constituição read-only, incluindo a cláusula de tier do worker Orca; fail-closed sem waiver; testes sem rede, sem `orca` real e na matriz ubuntu/windows/macos; depende do ship da candidata 6.0.0.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
