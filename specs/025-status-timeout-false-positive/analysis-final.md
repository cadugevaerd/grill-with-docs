# Análise final — false positive de STATUS-TIMEOUT

**HEAD analisado**: `a61ac8d` (pós-revisão autorizada de T005/T006)
**Veredito**: `READY-FOR-PARTITION`

## Revisão T005/T006 (achado de implementação)

`EXIT_BLOCKED=2` passa a ser aceito em T005/T006 **somente** quando acompanhado de payload
JSON (T005) ou tabela Markdown (T006) válidos refletindo estado real de work items bloqueados
— distinto de erro de uso do `argparse` (positional `root` ausente), que sai 2 **sem** payload
e continua sendo achado. Confirmado no código real: `EXIT_BLOCKED = 2`
(`grill_workspace.py:30`); `status_command`/`status_markdown_command` propagam
`process.returncode` do subprocesso `grill_status.py` (sempre com payload/tabela), enquanto o
argparse do `grill_workspace.py` falha **antes** de invocar `status_command`, sem payload
algum. FR-001/SC-001 exigem só ausência de `STATUS-TIMEOUT` dentro do timeout público — não
exigem exit 0 estrito — logo a mudança não afrouxa nenhum requisito. Sem conflito em
`contracts/grill-status-v1.md`, `quickstart.md` ou `checklists/`. Fail-closed preservado:
achado continua obrigatório para exit-2-sem-payload.

## Evidência executada

- Suíte completa após integrar `main`: exit 0; 1307 testes em 27 validadores; 1 skip.
- Particionador real, `groups=3`: `PARTITION-DEGRADED`, `max_workers=3`, 22 tarefas, 20 dispatchable, 9 nós.
- `unmapped_task_ids`: vazio.
- `deferred_to_leader`: exatamente T017 e T018, pelo Evidence Boundary declarado em `.specify/reports/status-timeout-bump-leader.md`.
- Phase 6: `p06-a`, `p06-b` e `p06-c`, file-disjuntos, cobrindo T010–T016.
- Phase 7: um único `p07-a`, contendo T019 → T020 → T021 → T022 e dependendo dos três nós da Phase 6.
- Razões esperadas: `EVIDENCE_BOUNDARY_TASKS` na Phase 6; `CONFLICT_GROUPS_BELOW_LIMIT` nas fases 1–5 e 7.

## Achados

- CRITICAL: 0.
- HIGH: 0.
- MEDIUM: 1 (herdado, não relacionado à revisão T005/T006). Dois trechos residuais atribuem o defer de T017–T018 aos arquivos raiz; tecnicamente, o defer é provocado pelo path Evidence Boundary. Não bloqueia: o relatório real confirma o defer e o DAG correto.

## Rastreabilidade

FR-001–FR-008 e SC-001–SC-006 possuem cobertura completa em T001–T022, inclusive após a revisão
de T005/T006 (a distinção EXIT_BLOCKED=2-com-payload × argparse-exit-2-sem-payload não altera
mapeamento de nenhum FR/SC). Os gates de distribuição permanecem fail-closed e executam sobre um
único SHA tracked-clean.

**READY-FOR-PARTITION**
