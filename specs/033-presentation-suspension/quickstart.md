# Quickstart: validar a suspensão e a reativação

Tudo offline: nenhum comando abaixo toca rede, runtime real ou processo externo.

1. Baseline antes de tocar código (deve passar; o defeito não é coberto):

   ```bash
   python3 tests/validate_agent_orchestration_contract.py
   python3 tests/validate_task_import_contract.py
   ```

2. Focado, depois da implementação — os quatro testes novos no validador de orquestração e o caso invertido do gate no validador de importação:

   ```bash
   python3 tests/validate_agent_orchestration_contract.py -k presentation_control -k suspension -k native_compaction -k upgrade_during_suspension
   python3 tests/validate_task_import_contract.py -k same_context_presentation_refresh
   ```

   Cada cenário roda nos dois runtimes (`subTest(runtime=...)`) com mensagens produzidas por `_native_messages` sobre a forma capturada (research R10). Cenários cobertos (mapa SC-001): 1→US1.1 stop suspende sem recarga; 2→US1.2 stop + compactação segue suspensa; 3→US2.1 start reativa e exige leitura posterior; 4→US3.1-3 frase em `assistant`, em resumo de compactação e em mensagem sintética não muda nada (sintética = `isMeta`/`isSynthetic` no Claude; injeção `role=user` com tag XML no Codex); 5→US4.1 upgrade durante a suspensão libera e grava o registro novo; 6→US5.1 compactação sem suspensão continua exigindo leitura; 7→US2.3 boundary nova começa ativa. Mais: US1.3 (`suspension.source_ref` termina no id da mensagem), US1.4 (pré-requisito ausente → `work_ready=false` e diagnóstico nomeado), US2.2 (alternância, vale a última), US4.2 (`STYLE-SCOPE-CONFLICT` permanece), US5.2 (`compact_boundary` e `compacted` no formato real), edge cases (espaços nas pontas; texto extra; `start` sem `stop`; mensagem `user` sem `id`; forma Codex de dois blocos `(plain, <environment_context>)` não conta).

   FR-012 (M2 da R2): `python3 tests/validate_distribution.py` assere `start adhd mode` em cada um dos quatro documentos. Fica verde só com o bump completo dos nove pontos (§5), então roda no fim do nó de documentação, não antes.

3. Exposição (FR-013) e SC-003 — dentro de `test_presentation_upgrade_during_suspension_keeps_work_ready`:

   ```bash
   python3 tests/validate_agent_orchestration_contract.py -k upgrade_during_suspension
   ```

   `preflight … --session-ref` com a frase no transcript devolve exit 0, `verdict=OK`, `presentation.application=suspended_by_user`, `use_ready=false`, `work_ready=true`, `suspension` presente, `load_request` ausente; `checkpoint` com `config_fingerprint` mudado devolve exit 0 e o contexto gravado traz o registro com a configuração nova. Esse `checkpoint` passa por `_gauntlet_authorized`, então este teste só fica verde depois do nó do gate (remoção do bloco `grill_workspace.py:3468-3474`); o nó do produtor depende dele na partition.

4. Suíte completa e higiene do diff (SC-004):

   ```bash
   python3 tests/run_validators.py
   git diff --check
   ```

   Conte os validadores pelo marcador `==>` (31 hoje); `validate_distribution.py` usa asserções diretas e não imprime `Ran N tests`.

5. Distribuição, no ship, depois do bump nos nove pontos (R13: os oito de versão mais a linha `## X.Y.Z` e a entrada da 033 em `CHANGELOG.md`, que `validate_distribution.py:41-43` exige; obrigação constitucional registrada como NOT-APPLICABLE no plan-only):

   ```bash
   python3 tests/validate_distribution.py
   git show origin/main:plugin/.claude-plugin/plugin.json | grep '"version"'
   ```

   O segundo comando dá a versão publicada; o alvo é o patch seguinte (hoje 6.0.30 → 6.0.31). O `README.md` entra no mesmo nó de documentação pelo heading e pela frase da l.72 (FR-012); `CHANGELOG.md` entra pelo heading `## 6.0.31` e pela entrada da 033 (I2 da R2). O `CLAUDE.md` da raiz ainda diz "oito lugares" e não é corrigido nesta entrega.

6. Fora do aceite desta entrega (assunções da spec): reexecutar A1/A2 da matriz T029 com a versão instalada e registrar no work item de origem; conformidade das respostas do modelo (F1) segue fora.
