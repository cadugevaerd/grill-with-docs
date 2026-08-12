# Checklist de aceite — FASE-003

- [ ] CHK-001 — Existe workflow próprio do gate, sem filtro de caminhos.
- [ ] CHK-002 — O gate roda em `pull_request`.
- [ ] CHK-003 — `fetch-depth: 0` preservado.
- [ ] CHK-004 — A base vem do payload do evento, não de nome de ramo.
- [ ] CHK-005 — O job do gate não existe mais no workflow da matriz.
- [ ] CHK-006 — O workflow da matriz mantém o filtro de caminhos.
- [ ] CHK-007 — A guarda de deduplicação da matriz continua intacta.
- [ ] CHK-008 — Nenhum job reporta sucesso sem executar o gate.
- [ ] CHK-009 — O YAML dos dois workflows parseia e o shell passa em `bash -n`.
- [ ] CHK-010 — Suíte verde, contagem ≥ 309.
- [ ] CHK-011 — Nada em `plugin/` mudou; nenhuma versão subiu.
- [ ] CHK-012 — O ato humano de exigir o check está declarado por escrito.
