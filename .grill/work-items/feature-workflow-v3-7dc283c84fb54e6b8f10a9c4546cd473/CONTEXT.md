# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| Managed Workflow | O contrato project-wide que define a sequência de desenvolvimento exigida. | process notes, optional playbook | ADR-0001 |
| Workflow V2 | O Managed Workflow estabelecido que permanece suportado até migração explícita. | legacy workflow, obsolete workflow | ADR-0001 |
| Workflow V3 | O Managed Workflow opt-in que vincula cada etapa exigida a uma Canonical Skill. | automatic upgrade, replacement workflow | ADR-0001 |
| Canonical Skill | A única capacidade registrada autorizada a realizar uma etapa exigida em um runtime. | fallback, agent approximation, direct execution | ADR-0002 |
| Skill Resolution | A identidade pinada de uma Canonical Skill para uma etapa e runtime. | suggestion, discovered skill | ADR-0002 |
| Execution Attestation | Evidência estrutural cooperativa que correlaciona uma Canonical Skill ao output no contexto atual; não é prova criptográfica. | green result, artifact proof, hostile-agent defense | ADR-0004 |
| Work Item V3 | O registro isolado de trabalho cuja identidade, linhagem e ciclo são verificados. | task folder, mutable job | ADR-0003 |
| Project Store | O registro compartilhado e íntegro que coordena Work Items entre worktrees vinculadas. | local cache, per-worktree source of truth | ADR-0003 |

## Relationships

- A **Managed Workflow** contém exatamente onze etapas exigidas.
- Um **Workflow V3** vincula cada etapa exigida a uma **Canonical Skill** por uma **Skill Resolution**.
- Uma **Execution Attestation** prova um resultado de **Canonical Skill** para um **Work Item V3**.
- Um **Project Store** coordena um ou mais **Work Item V3** entre worktrees vinculadas.

## Example dialogue

> **Dev:** "Can I run review directly if I have the report?"
> **Domain expert:** "No. In **Workflow V3**, review is accepted only with an **Execution Attestation** for its **Canonical Skill**."

## Flagged ambiguities

- "checkpoint" registra progresso; não prova que uma etapa foi executada pela **Canonical Skill**.
