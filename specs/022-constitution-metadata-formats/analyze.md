# Analyze: consistência entre spec, plan e tasks

## Cobertura dos requisitos

| FR | Onde é implementado | Onde é testado |
|---|---|---|
| FR-001 três formas | `constitution_metadata`, `footer_fields` | `test_managed_grill_template_audits_clean`, `test_spec_kit_constitution_audits_clean`, `test_legacy_top_level_fields_audit_clean`, `test_footer_pairs_are_split_on_the_pipe` |
| FR-002 governança por heading | `section_body` | `test_governance_accepts_a_portuguese_heading`, `test_governance_body_stops_at_the_next_heading`, `test_governance_heading_without_prose_is_empty` |
| FR-003 comentários HTML | `HTML_COMMENT` em `constitution_metadata` | `test_commented_example_footer_supplies_no_values` |
| FR-004 precedência | `setdefault` sobre chave vazia | `test_declared_fields_win_over_the_footer` |
| FR-005 bold obrigatório | `FOOTER_LINE` | `test_unbolded_prose_is_not_read_as_a_footer` |
| FR-006 fail-closed | bloco `:276-288` inalterado | `test_constitution_without_metadata_still_fails_closed`, `test_footer_version_must_be_semver`, `test_footer_ratified_must_be_iso` |
| FR-007 regex intocados | — | verificado no diff |
| FR-008 nenhuma constituição reescrita | — | verificado no diff |

Nenhum FR sem teste. Nenhum teste sem FR.

## Divergências encontradas

Nenhuma entre spec, plan e tasks. A única correção de rumo durante a execução foi de formato do
laudo (seção `## Status`), registrada em `tasks.md`.

## Riscos de ambiguidade

- **Chaves do rodapé em português**: um projeto que escrevesse `**Versão**:` não seria reconhecido.
  Documentado como premissa no spec — o template oficial gera as chaves em inglês mesmo em
  constituição escrita em português, e é o formato que o relato apresenta. Não há caso real conhecido
  em contrário; ampliar sem evidência seria adivinhação.
- **Heading de governança em nível H1**: não reconhecido, por simetria com `constitution_clauses`,
  que também só considera H2/H3.

## Consistência com o núcleo

`triage` continua consultiva nesta versão: o registro em `.grill/triage/` documenta a rota, mas
`init` e `hotfix` não a exigem. Este ciclo não altera esse estado.
