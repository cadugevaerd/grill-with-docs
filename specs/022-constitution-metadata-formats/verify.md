# Verify: metadados da constituição em suas três formas reais

## Gates executáveis

| Gate | Comando | Resultado |
|---|---|---|
| Suíte completa | `python3 tests/run_validators.py` | 1102 testes, 23 validadores, exit 0, 1 skip de ambiente em `validate_workspace_contract.py` |
| Validador novo | `python3 tests/validate_constitution_metadata.py` | 14 testes, OK |
| Regressão do auditor | `python3 tests/validate_contract.py` | OK, dentro da suíte |
| Distribuição | `python3 tests/validate_distribution.py` | `distribution: OK` em 3.3.2 |

Baseline anterior: 1088 testes em 22 validadores. Delta de +14 corresponde exatamente ao validador
novo; nenhum validador anterior mudou de contagem.

## Prova de que o teste testa o defeito

Com a correção revertida (`git stash push` só de `audit_decisions.py`), o validador novo quebra:

```
Ran 14 tests in 0.490s
FAILED (failures=5, errors=6)
```

Onze dos catorze casos dependem do fix. Restaurada a correção, 14/14 OK. Os três que passam nas duas
versões são os de fail-closed e o da forma top-level — exatamente os que **não** podem mudar de
comportamento.

## D2 — o cenário que originou o relato

Projeto derivado de `tests/fixtures/go-project` com a constituição trocada pela forma oficial do
Spec Kit (rodapé bold + `## Governance` com prosa):

**Antes**

```
NO-GO
- constitution: governance vazio
- constitution: last-amended ISO inválido
- constitution: ratified ISO inválido
- constitution: version SemVer inválida
```

**Depois**

```
GO
selected-phase: FASE-001
selected-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
```

O projeto de controle `tests/fixtures/go-project`, intocado, continua `GO` nas duas versões.

## Checklist de aceitação

- [x] SC-001 — quatro findings antes, nenhum depois, medido no CLI real.
- [x] SC-002 — 1088 → 1102 testes, exit 0, sem regressão.
- [x] SC-003 — bullet shipado e rodapé Spec Kit exercitados por subprocess, não só pela função pura.
- [x] SC-004 — `audit` deste repo segue íntegro; nenhuma constituição foi tocada.

## Higiene de diff

```
 .agents/plugins/marketplace.json                   |  2 +-
 .claude-plugin/marketplace.json                    |  2 +-
 CLAUDE.md                                          |  2 +-
 README.md                                          |  2 +-
 plugin/.claude-plugin/plugin.json                  |  2 +-
 plugin/.codex-plugin/plugin.json                   |  2 +-
 plugin/skills/grill-with-docs/SKILL.md             |  2 +-
 .../grill-with-docs/references/session-protocol.md |  2 +-
 .../grill-with-docs/scripts/audit_decisions.py     | 53 +++++++++++++++++++++-
 tests/validate_distribution.py                     |  2 +-
```

Mais os arquivos novos: `tests/validate_constitution_metadata.py`,
`tests/fixtures/constitutions/spec-kit-filled.md`, `specs/022-constitution-metadata-formats/`,
`.grill/triage/` e o work item.

Sete das dez modificações são o bump de uma linha. A mudança de comportamento inteira cabe em
53 linhas de um arquivo.

- `FIELD` e `TOP_FIELD`: nenhuma linha de diff (FR-007).
- `.specify/memory/constitution.md`: ausente do diff (FR-008).

## Restrições do core preservadas

- Somente biblioteca padrão; nenhuma dependência nova.
- Nenhum byte baixado; nenhum teste toca rede, `specify`, `node` ou `backlogctl`.
- `audit` continua read-only — a prova é o próprio `test_..._audits_clean`, que roda o CLI sobre uma
  cópia temporária.

## Ressalva declarada

O rodapé é reconhecido pelas chaves em inglês (`Version`, `Ratified`, `Last Amended`), que é o que o
template oficial gera mesmo em constituição escrita em português. Uma constituição que traduzisse as
chaves do rodapé não seria reconhecida. Documentado como premissa no spec; não há caso real conhecido
e ampliar sem evidência seria adivinhação.

## Veredito

PASS.
