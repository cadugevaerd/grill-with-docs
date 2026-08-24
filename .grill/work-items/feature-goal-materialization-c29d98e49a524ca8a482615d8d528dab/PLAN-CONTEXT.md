# PLAN-CONTEXT

## FASE-001 — Materialização e validação do goal.md
- phase: FASE-001
- ADRs: ADR-0101, ADR-0102
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
- `grill_core/goal_document.py` é o SSOT: declara `VERSION`, `MARKER`
  (`grill-with-docs-goal:v1`) e a tupla `ESSENTIAL` como literal congelado,
  transcrita de `specs/024-goal-md-contract/contracts/essential-substrings.md`.
  A tupla **nunca** é derivada de nenhuma tupla de `WORKFLOW.md` nem de outra
  versão: derivá-la faria um typo reescrever o contrato em vez de reprovar um
  teste (ADR-0101).
- `ensure_goal.py` é fino e espelha a fronteira de I/O de `ensure_workflow.py`:
  `atomic_create` no-clobber, leitura por descritor sem seguir symlink, e um
  `emit` que reporta `CREATED | REUSED | PRESERVED` (ADR-0102).
- `init` fixa o documento antes de montar o bundle, como já faz com o workflow,
  e registra `path` e `sha256` no `state.json` do work item.
- Documento existente que não case a tupla permanece byte a byte e é reportado
  como `PRESERVED`; nada é sobrescrito, renomeado ou copiado para backup.
- Validador novo em `tests/`, nomeado `validate_*.py` para entrar na suíte pelo
  glob de `tests/run_validators.py`. Ele lê a tupla **do módulo SSOT**, nunca de
  uma cópia — é isso que torna a tupla efetivamente congelada.
- Somente biblioteca padrão, Python >=3.10, sem rede e sem exigir `specify`,
  `node` ou `backlogctl` reais: a matriz de CI não tem nenhum deles.
- A entrega altera `plugin/**`, logo exige bump SemVer sobre a 5.0.0 publicada,
  sincronizado nos oito lugares travados por `tests/validate_distribution.py`.
  Feature nova sem quebra de contrato é MINOR: 5.1.0.
- `ensure_workflow.py` não é convergido para a forma nova. A assimetria é
  deliberada e está declarada em ADR-0101.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
