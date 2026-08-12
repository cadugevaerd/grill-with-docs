# Verify — FASE-003

**Veredito: PASS**, com um item que depende de ato humano e fica declarado.

## Checklist

| Item | Estado | Evidência |
|---|---|---|
| CHK-001 workflow próprio | ✅ | `test_the_gate_lives_in_its_own_workflow` |
| CHK-002 roda em `pull_request` | ✅ | `test_the_gate_has_no_path_filter` |
| CHK-003 `fetch-depth: 0` | ✅ | `test_the_gate_keeps_full_history_and_the_payload_base` |
| CHK-004 base do payload | ✅ | idem, e recusa explícita de `github.base_ref` |
| CHK-005 job removido do `ci.yml` | ✅ | `test_the_matrix_workflow_no_longer_owns_the_gate` |
| CHK-006 filtro da matriz preservado | ✅ | `test_the_matrix_keeps_its_path_filter_and_its_dedup_guard` |
| CHK-007 guarda de deduplicação intacta | ✅ | idem |
| CHK-008 sem aprovação simulada | ✅ | `test_no_job_reports_success_without_running_the_gate` |
| CHK-009 YAML e shell válidos | ✅ | `test_both_workflows_have_valid_shell` |
| CHK-010 suíte ≥ 309 | ✅ | 316 |
| CHK-011 `plugin/` intocado | ✅ | diff sem entradas em `plugin/` |
| CHK-012 ato humano declarado | ✅ | `CLAUDE.md`, seção "Gates de integração" |

## O que continua não cumprido

FR-006 exige que o ato humano esteja declarado, e está. Mas o requisito de origem — reprovação bloquear a integração — só passa a valer quando alguém marcar `Version bump gate` como required na proteção de `main`. O código está pronto; a regra segue sendo convenção até lá. Rastreado em SGD-4 e SGD-7, e escrito em `CLAUDE.md` para não depender da memória desta sessão.
