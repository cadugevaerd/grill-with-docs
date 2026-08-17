# Implementation Plan: Projeção versionada e determinística das decisões

**Branch**: `feat/backlog-ssot` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-decision-projection/spec.md`

## Summary

FASE-002 inverte a autoria de `DECISION-BACKLOG.md`: o arquivo deixa de ser escrito à mão e passa a ser gerado a partir dos itens do backlog operacional vinculados ao work item, permanecendo versionado como evidência no commit.

O ponto que decide a viabilidade: o formato de saída **não é livre**. `audit_decisions.py` já parseia esse arquivo e exige `## BL-NNNN — título` com `- state:` em `{open, resolved, superseded}`, `- phase:` casando uma fase do ROADMAP, e, quando `state: open`, os campos `owner`, `evidence-needed` e `next-action` preenchidos. A projeção precisa reproduzir exatamente isso, senão quebra o gate que ela deveria alimentar.

Isso fecha o desenho do round-trip. A FASE-001 já grava todos os campos da decisão na descrição do item **exceto** `state`, que foi deliberadamente excluído por ser propriedade do item. Então a projeção recompõe cada bloco a partir da descrição, e obtém `state` invertendo o `status` do item.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão.

**Primary Dependencies**: nenhuma em runtime. O `backlogctl` continua sendo processo externo alcançado só por `Toolchain.run`, pelo contrato `--json` já estabelecido.

**Storage**: o arquivo gerado é o único artefato novo persistido, dentro do bundle do work item. Nenhum estado próprio.

**Testing**: `unittest` da stdlib. Alvo principal `tests/validate_backlog_contract.py`, que já tem `StubToolchain` e a substituição de `MODULE.resolve_cli`. A cobertura da auditoria offline entra em `tests/validate_contract.py` ou no validador de workspace, conforme onde o gate for exercitado.

**Target Platform**: matriz com ubuntu, windows e macos, em Python 3.10 e 3.13, sem `backlogctl` instalado.

**Project Type**: plugin de CLI consumido pelo próprio repositório.

**Performance Goals**: não aplicável; unidades de decisão por work item.

**Constraints**: geração byte-idêntica em reexecução, porque o `reconcile` exige no-op; escrita atômica; auditoria sem processo externo; nenhum teste exige binário real.

**Scale/Scope**: um gerador, um verificador, um mapa inverso de estados e uma validação nova no auditor. Nenhum arquivo novo de produção previsto além de possível extensão do módulo da ponte.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Status | Evidência / justificativa |
|---|---|---|
| Evidência antes de afirmação | PASS | A marca de origem é o que permite afirmar que o arquivo é derivado; sem ela o auditor reprova, em vez de presumir. |
| Work item isolado e ownership | PASS | Tudo escrito sob o bundle do work item corrente, na branch fixada no bloco imutável. |
| Feature/fix plan-only | PASS | Implementação corre no ciclo externo do Spec Kit, que é onde é autorizada. |
| Sequência obrigatória do desenvolvimento | PASS | `phase-turn` resetou a matriz ao fechar a FASE-001; `specify` concluído, `plan` em curso. |
| Verify/review antes de ship | PASS | Planejado na mesma ordem da fase anterior. |
| Fail-closed sem waiver | PASS | Três recusas nomeadas novas: registro sem marca de origem reprova a auditoria; verificação sem autoridade recusa em vez de afirmar frescor; divergência é relatada, nunca reparada em silêncio. |
| Rastreabilidade | PASS | ADR-0001 e ADR-0002 governam esta fase e estão citados no ROADMAP, no PLAN-CONTEXT e no handoff do work item. |
| Bump obrigatório do plugin | PASS | Toca `plugin/**`, então exige bump. Alvo: **2.9.0 → 2.10.0**, incremento menor, porque acrescenta comportamento sem quebrar contrato publicado. A inversão só vira incompatível quando o `init` passar a recusar, na FASE-003. |

Nenhuma violação. Complexity Tracking omitido.

**Recheck pós-design (Fase 1)**: o design não introduziu violação, e a Fase 0 descobriu um defeito que amplia o escopo de forma justificada. Os dois leitores do registro divergem — o auditor aceita hífen ASCII, três dígitos e título ausente; a ponte exige travessão, quatro dígitos e título. Uma decisão escrita com hífen comum bloqueia a fase pela auditoria e nunca é espelhada, o que é a mesma divergência silenciosa que o work item existe para eliminar, sobrevivendo dentro dele. A correção é eliminar o segundo parser, não alinhá-lo, e entra nesta fase porque o round-trip da projeção exige que os dois lados concordem.

## Project Structure

### Documentation (this feature)

```text
specs/016-decision-projection/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── projection-cli.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/
├── scripts/
│   ├── backlog_bridge.py       # mapa inverso, geração canônica, marca de origem, verificação
│   ├── grill_workspace.py      # subcomandos novos e escrita atômica
│   └── audit_decisions.py      # exigir a marca de origem, offline
└── SKILL.md

tests/
├── validate_backlog_contract.py   # geração, determinismo, marca, verificação
└── validate_contract.py           # auditoria offline sobre projeção
```

**Structure Decision**: repositório existente. O gerador e o verificador ficam no módulo da ponte, junto do mapa de estados que já vive lá, porque compartilham o vocabulário. A exigência da marca entra no auditor, que é quem já lê o arquivo. `grill_workspace.py` ganha apenas o wiring dos subcomandos e a escrita atômica, seguindo o padrão de staging e rename já usado na criação do bundle.
