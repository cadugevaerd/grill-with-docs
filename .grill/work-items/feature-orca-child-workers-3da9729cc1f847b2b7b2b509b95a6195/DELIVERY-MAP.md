# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Invocação de children Orca pelo GWD
- module-kind: platform
- responsibility: Contrato único para a sessão líder coordenar especialistas e workers como children Orca, igual em Claude Code e Codex
- boundary: Skills, references, assets de policy/binding/dependências e o adapter de líder/child do core GWD
- depends-on: none

### DU-001 — Contrato de children Orca independente de CLI
- development-type: platform-devops
- phase: FASE-001
- scope-in: Topologia coordenador/child, bloqueio sem Orca, binding único de modelo/esforço, override de CLI, placement em worktree do gauntlet, evidência por child, Orca como dependência obrigatória e bump MAJOR
- scope-out: Mudança no Orca, criação de worktree pelo Orca, cópia de transcript, emenda da Constituição, alteração de WORKFLOW/ESSENTIAL/registries v3/v4
- depends-on: none
- acceptance: Na mesma entrada GWD, Claude Code e Codex iniciam cada especialista e worker como child Orca verificável por Dispatch, recusam de forma nomeada sem Orca pronto e registram evidência estrutural auditável offline

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
