# Review — FASE-003

**Veredito: APPROVE.**

## Risco declarado, e como foi coberto

O modo de falha era ficar sem gate sem perceber: remover o job de um arquivo e errar o outro não produz sintoma até alguém integrar conteúdo distribuído sem bump — e aí é tarde.

A cobertura não é "o arquivo existe". `WorkflowWiring` fixa as quatro propriedades que fazem o gate funcionar, cada uma correspondendo a um jeito diferente de a migração falhar em silêncio:

- sem `paths:` — se herdasse filtro, ficaria mudo onde importa;
- `fetch-depth: 0` — sem ele, o clone raso não tem a merge base e o gate falha ruidosamente;
- base do payload, com recusa explícita de `github.base_ref` — comparar contra nome de ramo falha em silêncio, que é pior;
- ausência de `exit 0` em qualquer passo dos dois workflows — nenhum shim aprovando por não ter rodado.

## Decisão que sobreviveu à revisão

A alternativa do job-shim, sugerida no próprio SGD-7, foi recusada e a recusa está registrada em ADR-0003. Ela tornaria aprovado indistinguível de não-executado — a mesma classe de falso verde que a milestone anterior gastou uma fase inteira eliminando na publicação. O teste `test_no_job_reports_success_without_running_the_gate` impede que a alternativa volte por descuido.

## O que a fase não resolve

O ato humano. É a única coisa entre este código e FR-007 ser gate de verdade, e nenhum commit o alcança. Está em `CLAUDE.md` e em SGD-4/SGD-7.

## Revisão independente

Não houve subagente nesta fase. O registrado é a passada da sessão primária — declarado como tal.
