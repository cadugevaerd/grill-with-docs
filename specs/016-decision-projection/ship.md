## Ship Report

Status: MERGED
Source fingerprint: tree b6869e1acbeb24efeb1da207034fd30eeebefdeb3a36696ebb1e5542e1df372b / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan f974821ff7029fc9c7234fcc457c106f5032f23cbb12bf2950752fb99df14d2d

### Phase A — Evidence

Converge `CONVERGED` na segunda passagem, Verify `PASS`, Review `APPROVE`, fingerprints casando. Nenhum achado Critical ou Important aberto.

Rollback: reverter o commit de merge `63350eb`. Nada publicado, então não há tag nem entrada de marketplace a retirar.

### Phase B — Learning Gate

Um candidato novo, com evidência concreta.

| ID | Aprendizado | Evidência | Rota | Decisão |
|---|---|---|---|---|
| LRN-005 | Dois leitores do mesmo artefato divergem em silêncio; a correção é eliminar um, não alinhá-los | quatro de cinco variantes de cabeçalho divergiam | agent-context | **DEFERRED** |
| LRN-006 | Gate novo que exige marca em artefato existente precisa de condição, senão reprova todo trabalho anterior à migração | nove testes reprovados | agent-context | **DEFERRED** |

Ambos são decisão de política do operador e ficam deferidos, como LRN-003 da fase anterior. Nada aplicado, nenhuma revalidação disparada.

### Phase C/D — Integração

Pre-flight limpo. Merge `no-ff` produziu `63350eb`, com dois pais. Gates reexecutados antes do merge: 1000 testes exit 0, `distribution: OK` em 2.10.0.

**Push não executado**, mantendo a decisão do operador tomada na FASE-001: `publish.yml` dispara em `push` para `main` filtrando `paths: plugin/**`, e a publicação está concentrada na FASE-005.

### Phase E/F — Pendências

`memory.mode` é `propose-only` e depende de verificação de ref remoto, que não ocorreu. Permanece pendente.

SC-008 segue não verificado: exige os três sistemas operacionais e só a matriz de CI verifica.
