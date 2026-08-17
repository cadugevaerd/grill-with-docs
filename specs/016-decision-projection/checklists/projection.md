# Projection Requirements Quality Checklist

**Purpose**: Validar a qualidade dos requisitos da FASE-002 antes de implementar
**Created**: 2026-08-17
**Feature**: [spec.md](../spec.md)

**Parâmetros**: profundidade padrão; audiência revisor de PR; foco em determinismo e no limite entre auditoria e verificação. Defaults aplicados sem pausa, por diretiva de sessão.

## Requirement Completeness

- [ ] CHK001 Está especificado o que acontece com campos da decisão que existem no item mas não são reconhecidos pelo auditor? [Gap]
- [x] CHK002 Existe requisito para o caso de o item carregar `status` que a ponte nunca emite, como `open` ou `merged`? [Coverage, data-model §Mapa inverso]
- [x] CHK003 Está especificado que a projeção deve ser legível pelos dois leitores do arquivo? [Gap] — resolvido: D2 elimina o segundo leitor
- [ ] CHK004 Há requisito sobre o que ocupa o lugar do título quando o item não tem um? [Gap, Spec §FR-001]
- [ ] CHK005 A obrigatoriedade de `owner`, `evidence-needed` e `next-action` para decisão aberta está declarada como requisito, ou só herdada do auditor? [Completeness, Spec §FR-001]

## Requirement Clarity

- [x] CHK006 "Marca que identifique a fatia de autoridade" é preciso o bastante para ser implementado sem escolher o algoritmo? [Clarity, Spec §FR-006] — sim: FR-007 declara a propriedade observável
- [ ] CHK007 "Critério estável do próprio conteúdo" em FR-004 permite mais de uma implementação com resultados diferentes? [Ambiguity, Spec §FR-004]
- [ ] CHK008 "Escrita atômica" está definida em termos observáveis, ou pressupõe mecanismo? [Clarity, Spec §FR-013]

## Requirement Consistency

- [x] CHK009 FR-008, que proíbe a auditoria de consultar a autoridade, é consistente com FR-009, que a manda reprovar registro sem marca? [Consistency] — sim: a marca é verificável offline
- [x] CHK010 FR-014, que torna edição manual não suportada, é consistente com o registro permanecer versionado e editável no git? [Consistency, Spec §FR-002 vs §FR-014]
- [ ] CHK011 O mapa inverso é consistente com o mapa direto da FASE-001, sem estado que traduza em mão única? [Consistency, data-model]

## Acceptance Criteria Quality

- [x] CHK012 SC-002 e SC-003 são objetivamente verificáveis? [Measurability] — sim, ambos nomeiam a perturbação a aplicar
- [ ] CHK013 SC-007 exige que interrupção não deixe estado inválido; existe forma declarada de provocar isso num teste? [Measurability, Spec §SC-007]
- [ ] CHK014 Todo requisito funcional tem critério de aceite correspondente? [Traceability]

## Scenario Coverage

- [ ] CHK015 Fluxo de exceção está coberto para autoridade indisponível nos dois comandos, geração e verificação? [Coverage]
- [x] CHK016 Existe requisito para registro gerado por versão anterior do gerador, com marca de formato diferente? [Gap, Recovery]
- [ ] CHK017 O caso de trabalho sem decisão alguma tem requisito explícito de arquivo válido e vazio? [Coverage, Spec §Edge Cases]

## Dependencies & Assumptions

- [x] CHK018 A dependência da FASE-001 está declarada? [Assumption] — sim, nas premissas
- [ ] CHK019 A premissa de que o auditor não muda de formato está registrada como risco? [Assumption, Gap]

## Notes

Três itens exigem decisão antes de implementar:

- **CHK002** é lacuna real. O mapa inverso cobre três estados; o item pode carregar `open` ou `merged` se alguém mexer à mão no backlog. Sem requisito, a tradução seria silenciosa ou explodiria.
- **CHK010** é tensão real, não contradição. O arquivo é versionado, logo editável; "não suportado" precisa significar "detectável", e isso deve estar escrito.
- **CHK016** aponta compatibilidade de formato da marca entre versões do gerador, que nada cobre hoje.

CHK003, CHK006, CHK009, CHK012 e CHK018 já passam. Os demais são de completude e seguem para `analyze`.

## Resolução aplicada

- **CHK002 resolvido**: FR-016 exige divergência nomeada para estado que a ponte nunca produz, em vez de tradução por aproximação.
- **CHK010 resolvido**: FR-017 define "não suportada" como detectável, não impedida, e SC-009 fixa a granularidade — um caractere.
- **CHK016 resolvido**: FR-018 exige que o registro declare a versão de formato.
