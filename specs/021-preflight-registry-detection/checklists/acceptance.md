# Acceptance Checklist: Detecção de extensão pelo registro

**Created**: 2026-08-20 · **Feature**: [spec.md](../spec.md) · **Plan**: [plan.md](../plan.md)

Cada item é verificável por teste automatizado, salvo os marcados **(manual)**. Nenhum item pode ser satisfeito por inspeção de código apenas.

## A. Fonte de verdade (FR-001, FR-002)

- [ ] A1 — A detecção não invoca `specify` nem cria processo filho. Verificável por `Toolchain` instrumentado que falha o teste se `run` for chamado no caminho de extensão.
- [ ] A2 — Registro com `git` na chave e a palavra `git` ausente de qualquer outro lugar: `git` é `present`.
- [ ] A3 — Registro **sem** a chave `bugfix`, porém com a string `bugfix` em campo de texto de outra extensão: `bugfix` **não** é `present`. Regressão direta do falso positivo original.
- [ ] A4 — Nenhum resíduo de escape ANSI pode satisfazer a verificação: chave `[2mgit[0m` no registro **não** faz `ext:git` presente.

## B. Estado por extensão (FR-003, FR-004, FR-009)

- [ ] B1 — Slug presente e `enabled: true` → `present`, com `version` do registro e `source` apontando o caminho do registro.
- [ ] B2 — Slug presente e `enabled: false` → `missing`, `reason` declara desabilitada, remediação contém `extension enable` e **não** contém `extension add`.
- [ ] B3 — Slug ausente do mapa → `missing`, `reason` declara ausência, remediação contém `extension add`.
- [ ] B4 — Slug presente, `enabled: true`, sem campo `version` → `present` mesmo assim; versão nula não invalida presença.

## C. Registro não legível (FR-005, FR-006, FR-007, FR-008)

- [ ] C1 — Registro ausente → todos os `ext:*` em `undetermined`.
- [ ] C2 — Registro com JSON inválido → desfecho byte-a-byte idêntico ao de C1 nos itens de extensão.
- [ ] C3 — Registro com `schema_version: "2.0"` → desfecho idêntico a C1 nos itens de extensão.
- [ ] C4 — Em C1/C2/C3, nenhum item de extensão traz chave `remediation`.
- [ ] C5 — Em C1/C2/C3, nenhum item de extensão tem status `missing`.
- [ ] C6 — Em C1/C2/C3, `spec-kit-extension-registry` aparece uma única vez em `missing_required`, e traz `remediation` própria.
- [ ] C7 — Em C1/C2/C3, `verdict` é `MISSING-DEPENDENCY` — `undetermined` bloqueia.
- [ ] C8 — `--allow-install` sobre registro ilegível **não** executa nenhum comando de instalação de extensão.

## D. Ambiente íntegro (FR-008, SC-001)

- [ ] D1 — Registro com as quatro extensões exigidas, todas habilitadas → `verdict: OK` e `missing_required` vazio.
- [ ] D2 — **(manual)** No repositório real, `preflight .` retorna `verdict: OK` e exit 0. Este é o cenário que originou SGD-16 e o único que prova a correção fim a fim.

## E. Contrato e regressão (FR-010, FR-011, SC-005, SC-006)

- [ ] E1 — `SCHEMA` permanece `grill-dependencies/v1`.
- [ ] E2 — Nenhum teste novo toca a rede, cria processo filho ou exige `specify`/`node`/`backlogctl` reais.
- [ ] E3 — Validadores que enumeram status exaustivamente aceitam `undetermined`.
- [ ] E4 — Suíte completa verde: contagem >= baseline 1066 e exit 0.
- [ ] E5 — Versão 3.3.1 idêntica nos oito pontos fixados por `tests/validate_distribution.py`.
- [ ] E6 — `CHANGELOG.md` tem entrada `## 3.3.1` descrevendo as duas classes de falha, não apenas o ANSI.

## F. Higiene do diff

- [ ] F1 — `installed_extensions` na forma antiga (`re.findall` sobre saída de CLI) não existe mais no módulo. Removida, não mantida em paralelo.
- [ ] F2 — Nenhuma captura de `except Exception` introduzida; exceções nomeadas.
- [ ] F3 — Nenhum arquivo fora do escopo declarado no ROADMAP da FASE-001 é tocado.

## Notes

A3 e A4 são os itens que impedem a correção de ser cosmética. Um patch que só remove ANSI passa em A2, B1-B4 e D1, e **reprova** em A3 — que é metade do defeito original e a parte que o relato inicial não mencionava.

C2 e C3 existem porque "as três formas convergem" é afirmação verificável, e convergência é exatamente o tipo de coisa que se presume e não se confere.

D2 é manual por necessidade: a suíte roda com fixtures, e o ambiente real com as quatro extensões instaladas é o que o CI não tem. Sem ele, a correção estaria provada contra fixtures e não contra o mundo que a reprovou.
