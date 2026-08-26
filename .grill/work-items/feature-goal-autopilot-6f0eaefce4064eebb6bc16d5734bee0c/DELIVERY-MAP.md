# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Contrato documental do goal loop
- module-kind: cross-cutting
- responsibility: Definir o texto normativo que um goal loop segue para conduzir o protocolo e parar nos pontos de interação
- boundary: Documento `goal.md` e seus templates de objetivo
- depends-on: none

### DU-001 — Texto normativo do goal.md
- development-type: documentation
- phase: FASE-001
- scope-in: Trilhas, templates de objetivo, pontos de interação, cláusula residual, delegação Orca
- scope-out: Materialização, validação, versionamento
- depends-on: none
- acceptance: O documento cobre as duas trilhas, enumera os pontos de interação por trilha, fecha com a cláusula residual e não depende de recurso exclusivo de nenhum runtime de goal

## MOD-002 — Fixação project-wide
- module-kind: platform
- responsibility: Materializar o documento no projeto consumidor com identidade versionada e hash auditável
- boundary: Assets do plugin e caminho de fixação do `init`
- depends-on: MOD-001

### DU-002 — Materialização no-clobber pelo init
- development-type: documentation
- phase: FASE-002
- scope-in: Template em assets, fixação pelo `init`, marcador e tupla `ESSENTIAL` próprios, hash em `state.json`, reporte no retorno
- scope-out: Texto normativo, validador
- depends-on: DU-001
- acceptance: `init` fixa o documento na raiz sem clobber, reporta estado e hash, e preserva byte a byte documento humano incompatível

## MOD-003 — Contrato público e distribuição
- module-kind: platform
- responsibility: Travar o contrato por teste e manter a versão publicada coerente
- boundary: Suíte de validadores e manifests de distribuição
- depends-on: MOD-002

### DU-003 — Validador e bump
- development-type: documentation
- phase: FASE-003
- scope-in: Validador novo em `tests/`, bump SemVer nos oito lugares, release ancorada pelo pipeline
- scope-out: Texto normativo, materialização
- depends-on: DU-002
- acceptance: Suíte canônica reprova qualquer quebra do contrato do documento e o gate de bump aprova a versão nova

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
