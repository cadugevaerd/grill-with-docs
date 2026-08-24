# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| cadeia de atestação | A sequência `skill-resolution → dispatch-intent → skill-invocation → step-output` que o núcleo exige para aceitar a conclusão de uma etapa. | "receipt" sozinho, "log" | `attestation.judge_checkpoint_attestation` |
| emissor | Quem monta a cadeia a partir do que já é conhecido e a entrega ao checkpoint. Hoje não existe. | "gerador", "assinador" | BL-0101 do work item `feature-goal-materialization` |
| leader | A sessão condutora do ciclo, que resolve a skill, invoca, monta o receipt e faz o checkpoint. É a única Evidence Boundary. | "orquestrador" sozinho | `WORKFLOW.md` §Execução paralela |
| executor da etapa | Quem efetivamente conduziu a etapa: um worker despachado ou o próprio leader. | "agente" | ADR-0201 |
| evidência estrutural | Correlação verificável entre documentos e digests, sem proveniência criptográfica nem defesa contra executor malicioso. | "prova", "assinatura" | `specs/010-execution-attestation/spec.md` §Out |
| artefato da etapa | O arquivo que a etapa produziu, cujo digest é selado no `step-output`. | "output" sozinho | ADR-0202 |
| lease | Concessão temporária de execução, com identificador e fencing token, que o núcleo já registra por worker. | "lock" | `grill_core/store.py` — `worker lease` |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.
