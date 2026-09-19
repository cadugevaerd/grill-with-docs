# Pedido e escopo único

Owner: Carlos Araújo. Sessão condutora: Claude Code (Opus). Branch: cadugevaerd/feat-new-subagents.
Origem: T029 do work item `feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa`, caso C1 (2026-09-19). Triagem: tri-codex-install-path (bugfix, high, `triage_sha256` e5136f39…e291; laudo `.grill/triage-evidence/codex-install-path-debug.md`).

## Requisito solicitado

Corrigir a observação da instalação do `i-have-adhd` no runtime Codex para que a entrada GWD 6.0.0 (`$grill-with-docs iniciar|retomar`) consiga chegar a `installation=present` a partir de evidência nativa. Hoje a entrada falha fechada com `STYLE-DEPENDENCY-UNDETERMINED`.

## Evidência observada

- `codex plugin list --json` (codex-cli 0.154.0) lista `i-have-adhd@i-have-adhd` com `version=0.3.0`, `installed=true` e `enabled=true`, mas **sem** `installPath`. A entrada traz só `source={"source":"git","url":"https://github.com/ayghri/i-have-adhd.git","ref":"main"}` e `marketplaceSource`.
- O observer em `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py:511-514` só promove `installation` a `present` com `installPath` absoluto e `version`; sem esse campo, fica `undetermined`. O comentário do código proíbe escolher versão de cache ou adivinhar caminho ausente da saída nativa.
- A cópia instalada existe em `~/.codex/plugins/cache/i-have-adhd/i-have-adhd/0.3.0/skills/i-have-adhd/SKILL.md`, com SHA-256 `3170b16a…27e9` igual ao aprovado.
- Dispatch `ctx_dc4fd5fc4d91`, rollout Codex `01a0baa3-7e61-7142-b940-d467bc08d1d9`. Registro completo em `STYLE-LIVE-VALIDATION.md` do work item de origem (commit `3d177d9`).

## Restrições conhecidas

- Não relaxar o fail-closed: não se pode inferir caminho nem versão que a evidência nativa não sustente.
- Sem dependência externa; stdlib apenas. O core nunca baixa bytes.
- Claude não pode regredir: o formato `installPath` do `claude plugin list --json` continua valendo.
- A correção precisa de teste offline pelo seam injetável, sem `codex` real no CI.

## Fora do escopo

As outras lacunas registradas no T029 ficam para work items próprios: assumir work item de líder morto, preview do adopt que não detecta o fence, troca de sessão antes do primeiro checkpoint, suspensão (`stop adhd mode`) não registrada pelo core e os campos do checkpoint de troca.
