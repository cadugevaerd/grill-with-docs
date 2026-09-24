# Revisão independente de Specify — latest-models, r3

**Veredito: APPROVED**

- Activity: `specify-reviewer-r3-latest-models`.
- Context: `ctx-abe82e929ba403bc2dc10449`; fence: `3`.
- Task: `task_b2b4fada11fd`; dispatch: `ctx_35c502a0d652`.
- Input manifest SHA-256 declarado no payload: `391a20ce72774409a61adf465794b58bc4e84c42e914bc023649d3aed5174272`.
- Escopo: os seis arquivos do manifest, lidos integralmente; SHA-256 e tamanho conferidos na leitura e imediatamente antes deste relatório. Os enunciados originais de R1–R3 foram fornecidos pelo coordenador via resposta Orca ao pedido de esclarecimento.

`HANDOFF`, `ADR-0001` e `ADR-0002` abaixo são os arquivos em `handoffs/FASE-001-SPECIFY-HANDOFF.md`, `docs/adr/ADR-0001.md` e `docs/adr/ADR-0002.md`, respectivamente, sob `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/`.

## Reavaliação de R1–R3

### R1 — Resolvido: orientação pública do par Claude

`specs/033-latest-models/spec.md:83` acrescenta FR-011: orientação pública deve apresentar autor `opus`/`xhigh` e revisor `opus`/`high`, sem exigir `fable`. SC-006, em `spec.md:103`, torna esse resultado verificável. Isso cobre HANDOFF:33 e ADR-0002:21, além do par em execução já coberto por FR-007 e pelos cenários em `spec.md:57-58`.

As marcações de cobertura em `specs/033-latest-models/checklists/requirements.md:20` e `:27` agora têm suporte explícito para o resultado público que faltava.

### R2 — Resolvido: incremento de versão e release

FR-012, em `specs/033-latest-models/spec.md:84`, exige incremento SemVer nos oito pontos, CHANGELOG correspondente e, para uma versão publicada, tag imutável e release pelo pipeline no mesmo commit. SC-007, em `spec.md:104`, exige versão superior e reafirma esses resultados; já não basta conservar a versão anterior consistente.

Isso cobre HANDOFF:43 e os gates de `.specify/memory/constitution.md:58-62`. A cláusula constitucional continua determinando o momento do bump, antes de merge ou push. A condição de publicação não exige publicar nesta etapa e não dispensa verify/review, sequência canônica ou autorização de ship. A marcação de completude em `checklists/requirements.md:29` é compatível com esses critérios documentais; não representa execução dos gates.

### R3 — Resolvido: evidência offline e higiene do diff

FR-013, em `specs/033-latest-models/spec.md:85`, exige fixture derivada do catálogo Codex 0.155.1, independência dos executáveis reais `codex`, `claude`, `node` e da rede, e expectativas de despacho determinadas pela prioridade fornecida, sem fixar uma geração. SC-008, em `spec.md:105`, cobre os oito cenários e a geração nova listada mas não preferida. SC-009, em `spec.md:106`, exige `git diff --check` sem erros; SC-005, em `spec.md:102`, mantém o sucesso da suíte completa.

Isso cobre HANDOFF:31-35. Os slugs concretos dos exemplos em `spec.md:23-26` são dados de cenário, coerentes com o próprio handoff; não anulam a exigência de variar a escolha conforme o catálogo. As marcações de cobertura e dependências em `checklists/requirements.md:20` e `:23` agora têm suporte.

## Cobertura do escopo aprovado

| Cenário do handoff | Evidência na spec |
| --- | --- |
| 1. Luna escolhida por prioridade, inclusive prioridades invertidas | `spec.md:23-24`, FR-001 em `:73` |
| 2. Terra preservada; nova geração só vence por prioridade | `spec.md:25-26`, FR-002 em `:74` |
| 3. Autor/revisor Codex usa Astra preferida, compara efetivo e registra slug | `spec.md:56`, FR-003/FR-004 em `:75-76` |
| 4. Catálogo ausente/ilegível recusa antes de efeitos | `spec.md:40`, FR-005 em `:77`, SC-003 em `:100` |
| 5. Família sem modelo listado recusa; oculto não qualifica | `spec.md:41`, edge case em `:63`, FR-005 em `:77` |
| 6. Família frontier continua proibida para worker | `spec.md:42`, FR-002 em `:74`, FR-006 em `:78` |
| 7. Especialistas Claude usam opus e esforços prescritos; fable diverge | `spec.md:57-58`, FR-007 em `:79` |
| 8. Tiers Claude e recomendação do líder preservados | `spec.md:67`, FR-008 em `:80`, premissa em `:112` |

FR-009 e o cenário em `spec.md:59,81` preservam a verificabilidade histórica sem reescrever policy ou receipts, conforme ADR-0001:39 e ADR-0002:30,35. As famílias, a prioridade em vez de geração e a recusa sem fallback estão alinhadas com ADR-0001:19-24,36-38. Os requisitos não autorizam exceção ao piso dos workers, dispensa de evidência ou alteração da Constituição.

O checklist contém as seções de qualidade, completude e prontidão; sua nota em `checklists/requirements.md:34` vincula os critérios novos às lacunas anteriores e mantém publicação condicionada à etapa canônica. Nomes de runtime, pares, recusas e restrições de validação são parte do contrato observável aprovado, sem impor uma implementação nova.

## Achados materiais e limites

**Nenhum novo achado material. R1, R2 e R3 encerrados nesta revisão documental.**

A comprovação de como Orca observa o alias `opus` e do registro do slug Claude quando disponível permanece responsabilidade do plan, conforme ADR-0002:34. Este parecer não comprova implementação, comportamento live, execução dos validadores ou gates de distribuição. Não executei código do projeto nem validadores para esta revisão de documentos; nenhum arquivo do repositório foi alterado.

O bootstrap desta sessão confirmou `presentation.work_ready=true`, `loading=loaded`, `enablement=enabled` e `trust=ready`; `behavior=not_tested` e `functional_verified=false` não foram convertidos em alegação funcional. O coordenador deve persistir e aceitar o resultado pelos gates canônicos, sem que este relatório ateste ou feche a macroetapa. A especificação aprovada não autoriza implementação, merge ou publicação; permanece o limite `PLAN_ONLY_STOP`.
