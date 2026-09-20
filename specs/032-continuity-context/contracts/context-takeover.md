# Contrato: tomada de contexto

```text
gauntlet-context-takeover ROOT --work-id ID --session-ref orca:ctx_<novo> [--expected-sha256 SHA] [--apply]
```

- Sem `--apply`: prévia. Executa todas as verificações, inclusive a observação do dispatch anterior, e devolve `TAKEOVER-PREVIEW` com `expected_sha256`, ou a recusa que o apply devolveria. Não escreve.
- Com `--apply` e `--expected-sha256`: efetiva. Hash divergente devolve `TAKEOVER-INPUTS-STALE`.
- Recusas: `TAKEOVER-LEADER-ACTIVE`, `TAKEOVER-EVIDENCE-UNPROVEN`, `TAKEOVER-NOT-OBSERVABLE`, `TAKEOVER-INPUTS-STALE`, além das recusas de identidade e estado já existentes.
- Sucesso: `TAKEOVER-APPLIED`, com `context_id` novo, `epoch`, `from_context_id` e o bloco `succession`.
- Idempotência: repetir com a mesma entrada, já aplicada, devolve `TAKEOVER-REUSED`.
- Invariantes: não altera `development`, campanha, `attested_outputs`, `attested_executions` nem `scope_files`; não reescreve checkpoint; não cria work item.
