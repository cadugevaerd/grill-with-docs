# Revisão independente de Specify — latest-models

**Veredito: CHANGES_REQUIRED**

- Activity: `specify-reviewer-latest-models`
- Context: `ctx-e7a6afd156d2dd3e657106db`
- Payload fence: `2`
- Escopo: os seis arquivos do `input_manifest`; todos os SHA-256 conferem com o payload.
- Revisão documental: nenhum código de projeto ou validador executado; nenhum arquivo do repositório alterado.

Neste relatório, `HANDOFF`, `ADR-0001` e `ADR-0002` referem-se, respectivamente, a `handoffs/FASE-001-SPECIFY-HANDOFF.md`, `docs/adr/ADR-0001.md` e `docs/adr/ADR-0002.md` sob `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/`.

## Achados que exigem ajuste

### R1 — P2: falta o resultado público da substituição de Fable

**Local:** `specs/033-latest-models/spec.md:79` e `:95-99`; checklist `specs/033-latest-models/checklists/requirements.md:20` e `:27`.

FR-007 cobre o par aceito em execução, mas não existe requisito ou critério de sucesso para retirar `fable` como par exigido da documentação pública. É possível satisfazer todos os FRs e SCs mantendo a tabela de papéis e o texto de autoria técnica instruindo o usuário a pedir um modelo que o gate recusa.

**Autoridade:** HANDOFF:33 exige esse resultado explicitamente; ADR-0002:21 inclui tabela de papéis e textos públicos no alcance da decisão.

**Correção mínima:** acrescentar um critério verificável de que a documentação pública apresenta autor `opus`/`xhigh` e revisor `opus`/`high`, sem exigir `fable`. Não é necessário prescrever como editar os documentos.

### R2 — P2: consistência de versão não cobre bump e release obrigatórios

**Local:** `specs/033-latest-models/spec.md:99`; checklist `specs/033-latest-models/checklists/requirements.md:29`.

SC-005 aceita metadados consistentes mesmo se todos conservarem a versão antiga; também não exige a release correspondente. Portanto, o critério declarado permite uma entrega que não cumpre os gates de distribuição aprovados.

**Autoridade:** HANDOFF:43 exige bump nos oito pontos e release correspondente; `.specify/memory/constitution.md:58-62` exige incremento SemVer antes de merge/push e release pelo pipeline no mesmo commit da tag imutável.

**Correção mínima:** explicitar esses gates como condições da futura entrega, mantendo o fluxo atual plan-only. Isso não autoriza implementação, merge ou publicação nesta fase (`constitution.md:40-41`).

### R3 — P2: os critérios de validação perderam restrições explícitas do handoff

**Local:** `specs/033-latest-models/spec.md:82` e `:95-99`; checklist `specs/033-latest-models/checklists/requirements.md:20` e `:23`.

FR-010 exige funcionamento offline sem instalar runtime, mas ainda permite depender de executáveis reais já instalados. SC-001 cobre os oito cenários, porém não preserva a origem exigida para a fixture nem o critério contra expectativas de despacho fixadas por geração; SC-005 também omite o gate `git diff --check`. Assim, uma suíte offline com executáveis reais e expectativas estáticas poderia atender ao texto atual sem atender ao aceite aprovado.

**Autoridade:** HANDOFF:31 exige fixture derivada do catálogo Codex 0.155.1 e independência de `codex`, `claude`, `node` e rede reais; HANDOFF:32 proíbe slugs de geração fixados como expectativa de despacho; HANDOFF:35 exige a suíte em exit 0 e diff limpo.

**Correção mínima:** preservar esses critérios de evidência na especificação. Distinguir os slugs concretos usados como dados dos cenários/fixtures — permitidos e já presentes no handoff — de expectativas de despacho que fixem a geração independentemente do catálogo fornecido.

## Checklist e limites da revisão

Após os ajustes, reavaliar as marcações de completude citadas, atualmente assinaladas apesar dessas lacunas. Não há necessidade de implementar a feature para corrigir os três achados.

O comportamento central está alinhado: menor prioridade dentro da família, Terra preservada, recusa antes de efeitos, piso frontier, registro Codex, par Claude e verificabilidade histórica. ADR-0002:34 reserva ao plan a comprovação de como Orca observa `opus` e o registro do slug Claude quando disponível; essa investigação não é exigida como implementação nesta revisão.

A revisão não comprova execução, integração com Orca ou validação da futura implementação. O próximo passo é ajustar spec/checklist e submetê-los novamente à revisão, preservando `PLAN_ONLY_STOP`.
