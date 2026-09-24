VERDICT: CHANGES_REQUIRED

# Revisão independente — specify-reviewer-001 (etapa specify, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 `9ca9abc41ddd21ba647de9c3edc9f32a19f3ba9a15355daca4ce1967b6865c23` (confere)
- input manifest: 10/10 sha256 conferidos, zero divergência
- nada escrito no repositório; relatório só neste scratchpad
- convenção: `spec` = `specs/034-fence-autorizado-atividade/spec.md`; `chk` = `specs/034-fence-autorizado-atividade/checklists/requirements.md`; `H` = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24/handoffs/FASE-001-SPECIFY-HANDOFF.md`; `PC` = PLAN-CONTEXT.md (via `interview-author-001.result.md`)

## Resumo

A spec é fiel ao handoff em todos os pontos que o payload manda conferir: os quatro negativos de DQ-0006 (spec:55-58), o inconclusivo com a sessão do sucessor (spec:59), hash stale e replay (spec:73-74), aceite tardio (spec:41, spec:96), variante retida (spec:29-41), autoridade derivada do líder (spec:94), estado final não aceito (spec:96), attempt 2 como atividade nova (spec:25, spec:100), DQ-0012 fora (spec:128). Um único finding bloqueia: a spec acrescenta um cenário de "aplicação interrompida" que não existe no handoff e que fixa a mutação em dois passos, decisão que o PLAN-CONTEXT deixa explicitamente para o ciclo executor. Corrigido isso e três nits de vocabulário, a spec aprova.

## Findings

### F1 — BLOQUEANTE — "aplicação interrompida" amplia o handoff e fixa HOW (mutação em dois passos)

**Evidência.**
- spec:65 "Uma aplicação interrompida no meio é retomada pela mesma operação, sem duplicar efeito."
- spec:69 (Independent Test) "interromper a aplicação entre as duas mudanças e reaplicar."
- spec:75 (US4 AS3) "**Given** uma aplicação interrompida depois de encerrar a atividade e antes de fechar a sessão, **When** a mesma aplicação é repetida, **Then** ela conclui o que faltava, sem refazer o que já estava feito."
- spec:101 (FR-012) "Aplicação interrompida MUST ser retomável pela mesma operação."
- spec:121 (SC-004) "A retomada de aplicação interrompida conclui com exatamente um encerramento registrado."

**Por que bloqueia.**
1. Não está no handoff. H:31 cobre só "aplicação com hash divergente recusa; aplicação repetida com os mesmos inputs devolve reuso sem segundo efeito". Nenhum cenário, critério ou restrição de H:23-46 fala em interrupção ou retomada. É ampliação (critério 1 do payload).
2. É HOW. "depois de encerrar a atividade e antes de fechar a sessão" (spec:75) e "entre as duas mudanças" (spec:69) pressupõem que a aplicação grava a atividade e a sessão em dois passos separados com estado intermediário observável. Isso é a estrutura de dois `store.transact` do PC ("Mutação", salto 1 / salto 2; caso p5 dos testes), não uma propriedade do domínio.
3. Contradiz a liberdade que o plano reserva. O PC registra a alternativa F3 em um salto (`PRESERVED`), que "Elimina o salto 2, a janela de crash e o caso p5", e fecha com "Escolha do ciclo executor". Se a spec fixar o estado intermediário, a alternativa vira não conforme à spec — a spec decide o que a etapa plan tinha de decidir.
4. Testabilidade condicional: sob a alternativa em um salto, US4 AS3 não tem estado intermediário para montar, logo o cenário fica inexequível (chk:17 deixaria de ser verdadeiro).

**Correção sugerida (menor diff).** Remover a frase de spec:65, o trecho "interromper a aplicação entre as duas mudanças e reaplicar" de spec:69, o cenário spec:75 inteiro, a frase do meio de FR-012 (spec:101) e a segunda frase de SC-004 (spec:121). A propriedade WHAT que sobra — "repetir com os mesmos insumos devolve reuso sem segundo efeito" — já cobre a retentativa após falha, pois uma reaplicação após interrupção é uma repetição com os mesmos insumos.
Alternativa aceitável, se o líder quiser manter a robustez explícita sem HOW: uma frase única e agnóstica de estado em FR-012, do tipo "Uma aplicação que não concluiu, quando repetida com os mesmos insumos, MUST terminar com exatamente um encerramento registrado e o mesmo estado final de uma aplicação única", sem cenário de aceite que nomeie passos internos. Não exige DQ: não há decisão nova, só remoção do que o plano já reservou para si.

### F2 — menor — FR-015 nomeia identificador interno de código

**Evidência.** spec:104 "nem as tuplas `ESSENTIAL`". `ESSENTIAL` é o nome de constantes Python em `ensure_workflow`/`workflow_v3`/`workflow_v4` (CLAUDE.md). H:46 diz só "nada muda na Constituição, no WORKFLOW ou nos registries".
**Correção.** Trocar por "nem as regras de compatibilidade do WORKFLOW" ou apenas suprimir; o conteúdo já está coberto por "o WORKFLOW".

### F3 — menor — SC-005 nomeia a linguagem; handoff não

**Evidência.** spec:122 "nos três sistemas operacionais e nas duas versões de Python da matriz, sem rede". H:41 diz "verde nos três SOs, sem rede". chk:19 marca "technology-agnostic".
**Correção.** Alinhar ao handoff: "nos três sistemas operacionais da matriz de integração, sem rede". A matriz concreta é assunto de plan/DU-001.

### F4 — menor — SC-001 não é verificável dentro da FASE-001

**Evidência.** spec:118 mede o sucesso "nos dois casos reais (X7 e o `interview-author-001` do work item de origem)". O Store do X7 vive em outra máquina (DECISION-FRONTIER DQ-0001/DQ-0005 "EVIDENCE GAP"; PC "Riscos"), e o fence sobre `interview-author-001` de origem é a FASE-002, que a própria spec exclui em spec:128. Nenhum gate de verify/review desta fase consegue medir SC-001.
**Correção.** Reescrever como as duas formas verificáveis na suíte ("a forma órfã e a forma de sessão retida passam de tomada recusada a admitida depois de um único encerramento, sem edição manual do registro") e deixar os casos reais como motivação em US1/US2 "Why this priority" (spec:17, spec:33), onde já estão. Não amplia nem estreita: DU-001 já define aceite por forma.

### F5 — menor — edge case de concorrência introduz terceiro desfecho

**Evidência.** spec:82 "o outro recebe conflito ou reuso". O handoff só conhece dois desfechos para uma segunda aplicação: recusa por hash divergente e reuso (H:31).
**Correção.** "o outro recebe recusa ou reuso, nunca um segundo efeito". Mantém o edge case, sem vocabulário de mecanismo.

### F6 — menor — três itens do checklist só ficam verdadeiros após F1–F3

**Evidência.** chk:9 "No implementation details", chk:19 "technology-agnostic", chk:30 "No implementation details leak" estão `[x]`, mas spec:69/75 (dois passos), spec:104 (`ESSENTIAL`) e spec:122 (Python) os contradizem. Os demais itens do checklist conferem: chk:16 (nenhum marcador), chk:20-23 (cenários, edge cases, escopo em spec:128-130, assumptions), chk:27 (cada FR tem cenário ou SC correspondente), chk:34-35 (notas corretas: vocabulário do domínio e findings de HOW no plan, coerente com DQ-0011).
**Correção.** Nenhuma edição no checklist; ele passa a ser verdadeiro quando F1–F3 forem aplicados.

## Conferência de fidelidade (sem finding)

| Handoff | Spec |
|---|---|
| H:15 resultado, preview-first, hash | spec:15, spec:90 (FR-001) |
| H:18 líder sucessor, sessão própria provada | spec:31, spec:94 (FR-005), spec:59 |
| H:19 humano autorizador, recibo | spec:92 (FR-003), spec:110, spec:127 |
| H:20 variantes 1 e 2 | spec:15, spec:31, spec:95 (FR-006) |
| H:21 líder corrente exato quando vivo | spec:31, spec:39, spec:94 |
| H:24 cenário órfã | spec:23-25 |
| H:25 cenário retida, nunca aceito nem herdado, DQ-0008, DQ-0009 | spec:31, spec:39-41, spec:96 (FR-007) |
| H:26-29 quatro negativos DQ-0006 | spec:55-58 |
| H:30 inconclusivo, inclui sucessor | spec:59, spec:93 (FR-004) |
| H:31 hash stale / replay | spec:73-74, spec:101 (FR-012, frases 1 e 3) |
| H:32 aceite tardio | spec:41, spec:96, spec:120 (SC-003) |
| H:35 prévia não escreve; conteúdo do hash | spec:91 (FR-002), literal |
| H:36 estado bit a bit igual | spec:102 (FR-013), spec:119 (SC-002) |
| H:37 takeover sem alterar herança; prepare-switch | spec:98 (FR-009), spec:83-84 |
| H:38 sem aceite, aceite posterior recusado | spec:96 |
| H:39 rastreabilidade | spec:99 (FR-010), literal |
| H:40 attempt 2 nova, nada migra | spec:25, spec:100 (FR-011) |
| H:41 bump oito pontos; suíte verde | spec:103 (FR-014), spec:122 (ver F3) |
| H:46 restrições | spec:92-93, spec:96, spec:104 (ver F2) |
| DQ-0012 / FASE-002 fora | spec:128 |
| SGD-37/38/39, checkpoint automático fora | spec:129-130 |

Vocabulário aceito como observado do domínio, sem prescrever implementação: dispatch, liveness, hash, revogação de capability (spec:81, spec:126), recibo, verbo, tomada, troca de runtime, digests (H:39 usa "digests").

## DQs propostas

Nenhuma. O único ponto material (F1) não é decisão nova: é remoção de HOW que o PLAN-CONTEXT já reserva ao ciclo executor. Nenhuma DQ-0001..DQ-0012 foi reaberta, ampliada ou estreitada pela spec.
