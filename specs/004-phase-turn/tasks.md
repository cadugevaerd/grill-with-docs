# Tasks — FASE-001

## T-001 — Extrair o preâmbulo compartilhado
**Arquivo**: `plugin/skills/grill-with-docs/scripts/grill_workspace.py`
**Depende de**: nada

Resolução do item, recusa de symlink, snapshot global e lock saem de dentro de `checkpoint_command` para um helper reutilizável. Comportamento idêntico; nenhum código de erro muda.

**Pronto quando**: a suíte de workspace passa sem alteração nos testes existentes.

## T-002 — `phase_turn_command`
**Arquivo**: `plugin/skills/grill-with-docs/scripts/grill_workspace.py`
**Depende de**: T-001

Implementa o contrato da tabela de `plan.md`: `TURNED`, `REUSED`, `PHASE-INCOMPLETE`, `REASON-REQUIRED`, `LEGACY-UNTRACKED`. Grava a entrada na trilha com `step: "phase-turn"` e `state: "turned"`.

**Pronto quando**: os cinco resultados são distinguíveis e só o primeiro escreve.

## T-003 — Recusa nomeada
**Arquivo**: `plugin/skills/grill-with-docs/scripts/grill_workspace.py`
**Depende de**: nada

No ramo `in-progress`, quando **todos** os passos estão `complete`, o código passa a ser `PHASE-TURN-REQUIRED`. Transição inválida por outro motivo continua `INVALID-TRANSITION`.

**Pronto quando**: os dois códigos são distinguíveis por teste.

## T-004 — Subparser
**Arquivo**: `plugin/skills/grill-with-docs/scripts/grill_workspace.py`
**Depende de**: T-002

`phase-turn ROOT --work-id ID --reason RAZÃO`, com `--reason` exigido pela lógica e não pelo parser, para que a recusa seja um código nomeado e não um erro de uso.

**Pronto quando**: o subcomando aparece no `--help` e devolve JSON de linha única.

## T-005 — Contrato executável
**Arquivo**: `tests/validate_workspace_contract.py`
**Depende de**: T-004

Cobre CHK-001 a CHK-016, incluindo o ciclo duplo com virada no meio e a leitura do work item já reconciliado.

**Pronto quando**: a suíte inteira passa e a contagem sobe.

## T-006 — Bump de versão
**Arquivos**: os oito de `CLAUDE.md`
**Depende de**: T-005

2.5.1 → 2.5.2 nos quatro manifests, na constante do validador e nos três headings de documentação.

**Pronto quando**: `validate_distribution.py` aprova e o gate de bump responde `BUMPED`.
