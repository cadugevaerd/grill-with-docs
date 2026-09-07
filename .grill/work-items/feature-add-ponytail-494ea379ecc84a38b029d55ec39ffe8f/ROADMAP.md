# ROADMAP

- execution-order: FASE-001

## FASE-001 — Ponytail na stack oficial: detecção, instalação delegada e documentação
- state: ready-for-specify
- objetivo: `preflight`/`init` detectam o plugin ponytail no runtime ativo (Claude Code ou Codex), nomeiam a remediação quando ausente ou desatualizado, instalam pela CLI do harness sob `--allow-install`; e este repositório documenta o ponytail como parte da stack em `CLAUDE.md` e num `AGENTS.md` novo, com ativação versionada em `.claude/settings.json`.
- scope-in: kind `harness-plugin` em `dependencies.json`/`ensure_dependencies.py`; entrada `ponytail` (`required: true`, `min: 4.9.0`, `install` por runtime, marketplace `DietrichGebert/ponytail`); testes por runtime em `tests/validate_dependencies_contract.py`; menção em `SKILL.md` e `README.md`; `CLAUDE.md`, `AGENTS.md` e `.claude/settings.json` deste repositório; bump SemVer minor com os oito pontos de versão.
- scope-out: escrita em `CLAUDE.md`/`AGENTS.md`/`.claude/settings.json` de projeto consumidor; verificação de plugin habilitado; gate incondicional; detecção via CLI do harness; suporte a outros harnesses do ponytail (Copilot, Cursor etc.).
- context-refs: ponytail, stack oficial, preflight, dono do artefato, registro de plugins do harness, kind de dependência, documentação do agente, decisão de confiança
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: BL-0001
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001, DU-002

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.
