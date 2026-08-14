# Independent read-only review

A etapa `review` usa um subagente novo, de Model Tier grande e sem acesso de escrita, que não planejou nem executou a mudança avaliada. Ele confronta especificação, plano, Execution DAG, diffs e receipts; apenas uma revisão aprovada permite chegar ao gate humano de `ship`.
