# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| contexto de orquestração | Registro por work item que amarra líder observado, época, atividades e checkpoints no store `.git/grill/orchestrator.json` | sessão, vínculo | grill_workspace.py:1624-1645 |
| observação de líder | Conjunto `session_ref`, `incarnation`, `observation_ref` e `observation_sha256` produzido pelo adapter a partir do dispatch vivo | identidade da sessão | agent_runtime.py:755-790 |
| dispatch terminal | Dispatch cujo host prova encerramento: status fora de `dispatched|running`, capacidade revogada, ou liveness `exited` | worker morto, sessão fechada | ADR-0001 |
| tomada de contexto | Ato explícito em que uma sessão nova assume um work item cujo líder está terminal, com preview, hash e registro de sucessão | adoção, rebind | ADR-0001 |
| troca preparada | Caminho ordenado `gauntlet-prepare-switch` seguido de `gauntlet-resume`, iniciado pela própria sessão de origem | handoff | WORKFLOW/protocolo |
| checkpoint de continuidade | Documento imutável que carrega o estado para outra sessão retomar | snapshot | agent_orchestration.py:671-680 |
