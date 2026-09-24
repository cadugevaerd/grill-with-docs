VERDICT: APPROVED

# Revisão independente — specify-reviewer-002 (etapa specify, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 `f915bde71d4ccf224b58f923efd32d269496e608fc7bbffedf398621ecd1c0db` (confere)
- input manifest: 11/11 sha256 conferidos, zero divergência
- cópias embutidas em `interview-author-001.result.md` (CONTEXT, ADR-0001, ROADMAP, handoff FASE-001) idênticas aos arquivos em disco; DECISION-FRONTIER em disco tem a DQ-0012 a mais, adicionada depois pelo líder (esperado)
- nada escrito no repositório; relatório só neste scratchpad
- convenção: `spec` = `specs/034-fence-autorizado-atividade/spec.md`; `chk` = `specs/034-fence-autorizado-atividade/checklists/requirements.md`; `H` = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24/handoffs/FASE-001-SPECIFY-HANDOFF.md`; `DF` = `DECISION-FRONTIER.md` do work item; `R1` = `specify-reviewer-001.result.md`

## Resumo

Nenhum finding bloqueante. As cinco correções pedidas por `specify-reviewer-001` estão aplicadas, nenhuma abriu lacuna em relação ao handoff, e a spec continua fiel a todos os pontos que o payload manda conferir. Três findings menores sobrevivem à revisão completa (não só do delta): uma imprecisão de metadado na linha `Input` (DQ-0012 não é migrada), uma ambiguidade de vocabulário no cenário negativo inconclusivo (`sem veredicto terminal` inclui literalmente o veredicto `ativo`) e um nome de entidade que contradiz a própria definição (`Observação terminal` com veredicto `ativo`/`indeterminado`). Nenhum exige DQ; são edições de uma frase cada e podem entrar no plan ou numa revisão editorial da spec sem reabrir a etapa.

## Conferência das correções de R1

| R1 | Correção pedida | Estado na spec | Evidência |
|---|---|---|---|
| F1 (bloqueante) | remover "aplicação interrompida" (frase de US4, Independent Test, AS3, meio de FR-012, 2ª frase de SC-004) | **aplicada** | spec:65 só reuso + hash stale; spec:69 "aplicar duas vezes com os mesmos insumos; aplicar com hash desatualizado"; US4 tem 2 cenários (spec:73-74); FR-012 spec:100 só reuso + hash divergente; SC-004 spec:120 uma frase. `grep -i 'interromp\|retom'` → zero hits |
| F2 | tirar `ESSENTIAL` de FR-015 | **aplicada** | spec:103 "a Constituição, o WORKFLOW nem os registries e catálogos"; `grep ESSENTIAL` → zero |
| F3 | tirar Python de SC-005 | **aplicada** | spec:121 "nos três sistemas operacionais da matriz de integração, sem rede"; `grep -i python` → zero |
| F4 | SC-001 por forma, não por caso real | **aplicada** | spec:117 "Na forma órfã e na forma de sessão retida, a tomada do work item passa de recusada a admitida depois de um único encerramento autorizado, sem edição manual do registro"; casos reais ficaram só em "Why this priority" (spec:17, spec:33) |
| F5 | "conflito" → "recusa" | **aplicada** | spec:81 "o outro recebe recusa ou reuso, nunca um segundo efeito"; `grep conflito` → zero |
| F6 | checklist passa a ser verdadeiro após F1–F3 | **verdadeiro agora** | chk:9, chk:19, chk:30 conferem (ver seção Checklist) |

**"Nada mais mudou".** A spec anterior não está em disco (arquivo untracked, sem histórico git, sem cópia em outra worktree), então a conferência é por reconstrução: R1 citava 130 linhas (spec:128-130 para escopo); a atual tem 129. A única remoção de linha inteira pedida foi o AS3 de US4 (antigo spec:75), e todas as citações de R1 posteriores a essa linha aparecem deslocadas exatamente −1 na spec atual (spec:82→81 concorrência, 94→93 FR-005, 96→95 FR-007, 101→100 FR-012, 104→103 FR-015, 118→117 SC-001, 121→120 SC-004, 122→121 SC-005, 128→127 FASE-002). As citações de R1 anteriores a 75 (spec:15, 17, 23-25, 29-41, 55-59, 65, 69, 73-74) casam sem deslocamento. Consistente com edição restrita aos cinco pontos.

**Lacunas abertas pelas correções.** Nenhuma em relação ao handoff. A remoção de F1 deixa a spec silenciosa sobre aplicação parcialmente concluída; H:31 também é silencioso (só hash stale e replay), e a robustez de retomada é HOW que o PLAN-CONTEXT reserva ao ciclo executor (alternativa `PRESERVED` em um salto). FR-012 + US4 AS1 cobrem a retentativa após timeout como "repetição com os mesmos insumos". Não é finding.

## Findings

### F1 — menor — linha `Input` declara DQ-0012 como migrada; ela é nativa deste work item

**Evidência.** spec:9 "decisões DQ-0001..DQ-0012, migradas de `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` sem reabertura". DF:12, 25, 37, 50, 63, 76, 89, 102, 115, 128, 141 trazem `migrated-from` para DQ-0001..DQ-0011; o bloco DQ-0012 (DF:145-155) não tem `migrated-from` e a resolution diz "decisão do coordenador sob o goal" (DF:154), com evidência na DQ proposta A do autor deste work item (DF:155). ADR-0001:33 também lista só "DQ-0006..DQ-0011 migradas".
**Por que importa.** É rastreabilidade (Constituição, "Rastreabilidade"): a spec afirma uma origem que a fronteira não sustenta. Não altera nenhum cenário nem requisito.
**Correção sugerida.** spec:9: "decisões DQ-0001..DQ-0011, migradas de `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` sem reabertura, e DQ-0012 decidida neste work item".

### F2 — menor — US3 AS5 usa "sem veredicto terminal", que inclui literalmente o veredicto `ativo`

**Evidência.** spec:59 "**Given** uma observação ausente, ilegível, não correlacionada ou sem veredicto terminal, inclusive a da própria sessão do sucessor, **When** o encerramento é pedido, **Then** a recusa é por prova não comprovada e nada muda." A própria spec define três veredictos — "terminal, ativo ou indeterminado" (spec:110) — e trata `ativo` com desfechos próprios: especialista ativo → recusa própria (spec:58, FR-004); líder ativo → admitido se o solicitante é o líder corrente (spec:39, FR-005) ou recusa própria se não é (spec:57). Lido ao pé da letra, spec:59 manda recusar "por prova não comprovada" também nesses casos, contradizendo spec:39/57/58. O edge case spec:80 usa o termo certo ("veredicto indeterminado (sem status terminal, sem revogação e sem liveness conclusiva)"), mas só para o especialista; o líder indeterminado não aparece em lugar nenhum além da leitura genérica de spec:59.
**Origem.** Herdado de H:30 ("liveness sem veredicto terminal"), onde "liveness sem veredicto" significa liveness inconclusiva; a spec perdeu "liveness" e o sentido ficou mais largo. Já estava na versão revisada por R1 (citada como conforme em R1:71); é finding de revisão completa, não do delta.
**Por que é menor e não bloqueante.** FR-004 ("observação inconclusiva MUST NOT contar como prova") e FR-013 estão corretos e precisos; a leitura pretendida é recuperável pela taxonomia de spec:110 e pela regra "caso específico antes do genérico" (AS3/AS4 antes de AS5). Afeta só a redação de um cenário; um autor de testes atento não erra, um apressado pode.
**Correção sugerida.** spec:59: "ou com veredicto indeterminado (do especialista, do líder ou da própria sessão do sucessor)". Opcional: spec:80 "Especialista **ou líder** com veredicto indeterminado (...)".

### F3 — menor — entidade "Observação terminal" admite veredictos não terminais

**Evidência.** spec:110 "**Observação terminal**: leitura do ambiente sobre o dispatch do especialista ou do líder, com veredicto terminal, ativo ou indeterminado." O nome fixa "terminal"; a definição admite `ativo` e `indeterminado`. spec:23 usa "as duas observações terminais" no sentido de veredicto (ambos terminais no caso órfão), o que mostra que "observação terminal" na spec já significa "observação **com veredicto** terminal", e a entidade genérica não pode ter o mesmo nome.
**Correção sugerida.** Renomear a entidade para "Observação de dispatch" (ou "Observação do ambiente"), mantendo a definição. Zero impacto em FR/SC.

## Fidelidade ao handoff (sem finding)

| Handoff | Spec |
|---|---|
| H:15 resultado, preview-first, hash | spec:15, FR-001 spec:89 |
| H:18 líder sucessor, própria sessão observada e provada (DQ-0008) | spec:31, spec:40, FR-005 spec:93, spec:59 |
| H:19 humano autorizador, recibo referenciado | FR-003 spec:91, spec:109, spec:126 |
| H:20 variantes 1 e 2 | spec:15, spec:31, FR-006 spec:94 |
| H:21 líder corrente exato quando vivo | spec:31, spec:39, FR-005 |
| H:24 cenário órfã: prévia lista atividade, dois veredictos, hash; aplicação → não aceita, sessão fechada com recibo, takeover admitido, attempt 2 | spec:23-25, FR-007, FR-008 spec:96, FR-011 spec:99 |
| H:25 cenário retida: resultado registrado, nunca aceito nem herdado; DQ-0008; DQ-0009 estado terminal não aceito | spec:31, spec:39-41, FR-007 spec:95 ("estado final não aceito, com motivo registrado") |
| H:26 sem autorização, mesmo código, nada muda | spec:55, FR-003 |
| H:27 autorização de outro contexto/atividade/run, recusa idêntica | spec:56, FR-003 "Ausência e alvo divergente MUST recusar com o mesmo código" |
| H:28 líder vivo que não é o chamador, recusa própria | spec:57, FR-005 "código próprio" |
| H:29 especialista vivo, recusa própria | spec:58 |
| H:30 inconclusivo, inclui sucessor | spec:59 (ver F2), FR-004 spec:92, spec:80 |
| H:31 hash stale / replay | spec:73-74, FR-012 spec:100 |
| H:32 aceite tardio | spec:41, FR-007, SC-003 spec:119 |
| H:35 prévia não escreve; conteúdo do hash | FR-002 spec:90, literal |
| H:36 quatro negativos + inconclusivo, estado bit a bit igual | FR-013 spec:101, SC-002 spec:118 (acrescenta hash stale, coerente com FR-012) |
| H:37 takeover sem alterar herança; deixa de contar para takeover e prepare-switch | FR-009 spec:97, spec:35, spec:82-83 |
| H:38 sem aceite, aceite posterior recusado | FR-007 |
| H:39 rastreabilidade | FR-010 spec:98, literal |
| H:40 attempt 2 nova, nada migra (DQ-0010) | spec:25, FR-011 |
| H:41 bump oito pontos; suíte verde três SOs sem rede | FR-014 spec:102, SC-005 spec:121 |
| H:46 restrições (autorização exata, prova do ambiente, silêncio/expiry não provam, nunca aceito/herdado, nada em Constituição/WORKFLOW/registries) | FR-003, FR-004, FR-007, FR-015 spec:103 |
| DQ-0012 / FASE-002 fora | spec:127 |
| SGD-37/38/39, checkpoint automático fora (DQ-0002) | spec:128-129 |

Acréscimos da spec sem par literal no handoff, todos deriváveis e aceitos: spec:23 lista "o solicitante" na prévia (o hash o cobre por H:35, logo a prévia precisa exibi-lo); spec:78 estado fora das duas formas recusa (complemento de FR-006); spec:79 decisão diferente de aprovação = ausência (definição de "autorização humana exata" no CONTEXT.md); spec:81 concorrência (já aceito em R1 com F5). Nada foi estreitado nem contradito.

## WHAT/WHY × HOW (sem finding)

`grep -Ei 'python|ESSENTIAL|transact|store\b|FAILED|CLOSED|CLOSE_PENDING|DISPATCHED|RESULT_RECORDED|\.py|classe|API|função'` → zero hits. Backticks só em spec:3 (branch), spec:9 (ids de handoff e work item) e spec:127 (`superseded`, estado de fase do ROADMAP). Vocabulário observado do domínio, sem prescrever implementação: dispatch, liveness, hash, revogação de capability (spec:125, mesmo julgamento de R1:85), recibo, verbo (FR-001; H:44 e DQ-0008 usam "verbo"), tomada, troca de runtime, digests (H:39). "Oito pontos de distribuição" (FR-014) é literal de H:41. A frase "nunca por flag" de H:46 não entrou na spec, e está certo: é HOW.

## Testabilidade (sem finding além de F2)

FR-001..FR-015 são todas verificáveis por inspeção de registro, diff ou suíte; nenhuma traz `[NEEDS CLARIFICATION]` (grep zero). SC-001..SC-005 são mensuráveis por forma, contagem ou CI. Cenários de aceite montam o próprio Given; US1 AS2 e US2 AS2 referenciam o Given do cenário anterior, o que é encadeamento de estado, não dependência de execução. US2 AS1 (líder vivo) não conflita com US1 AS1 ("duas observações terminais"): US1 é a forma órfã, onde os dois são terminais por definição.

## Escopo (sem finding)

spec:127 FASE-002 fora; spec:128 SGD-37/38/39 fora; spec:129 checkpoint automático fora. Nenhuma frase da spec toca herança de workers (FR-009 a declara inalterada), Constituição, WORKFLOW ou registries (FR-015).

## Checklist (sem finding)

Todos os `[x]` são verdadeiros na spec atual: chk:9/19/30 (sem implementação, tecnologia-agnóstico) passam após F1–F3 de R1; chk:12 (User Scenarios, Requirements, Success Criteria presentes); chk:16 (zero marcadores); chk:17-18 (FR/SC testáveis e mensuráveis); chk:20-23 (cenários, edge cases spec:76-83, escopo spec:127-129, assumptions spec:123-129); chk:27 (FR-014 e FR-015 são auto-verificáveis por validador/diff; os demais têm AS ou SC); chk:34-35 (notas corretas: `platform-devops` = H:12; DQ-0001..DQ-0012 todas `resolved`/`out-of-scope` no DF; findings de HOW da revisão de origem vão ao plan, coerente com DQ-0011). F2 deste laudo não invalida chk:17: os FR estão sem ambiguidade; a ambiguidade está num cenário de aceite.

## DQs propostas

Nenhuma. F1–F3 são edições editoriais de uma frase cada, sem decisão material nova; nenhuma DQ-0001..DQ-0012 foi reaberta, ampliada ou estreitada pela spec.
