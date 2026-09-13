# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "REQUEST.md",
        "../../triage/new-subagents-debug.md",
        "STACK-I-HAVE-ADHD.md"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Defeitos delimitados por reproduções isoladas e locais de código; disponibilidade Fable explicitamente não comprovada. Instalação e teste isolado do hook separados de ativação padrão e prova em sessão nova.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "REQUEST.md"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Namespace único criado por init na branch dedicada; owner Carlos Araújo; nenhum bundle irmão alterado.",
      "status": "PASS"
    },
    {
      "evidence": [
        "REQUEST.md",
        "state.json"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Pré-ciclo original encerrou em PLAN_ONLY_STOP; ciclo externo foi autorizado pelo usuário e specify concluída. A ampliação atual altera a entrevista e instala a dependência explicitamente solicitada; não implementa código ou pula a sequência.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json",
        "PLAN-CONTEXT.md",
        "DECISION-FRONTIER.md"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "R-0002 e ADR-0002 mantêm design dentro de plan; sequência de onze macroetapas preservada.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json",
        "CYCLE-EXECUTION.md",
        "SPECIFY-EXECUTION.md"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhum ship realizado; verify e review continuam pré-requisitos da entrega, e plan está bloqueada para incorporar a ampliação de escopo.",
      "status": "PASS"
    },
    {
      "evidence": [
        "DECISION-FRONTIER.md",
        "AUDIT.md",
        "REVIEW-I-HAVE-ADHD.md"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Nove decisões resolvidas; revisão independente da ampliação GO DOCUMENTAL, sem findings bloqueantes. Instalação e testes isolados continuam distintos do default e comportamento em sessão nova, exigidos para aceite da entrega.",
      "status": "PASS"
    },
    {
      "evidence": [
        "REQUEST.md",
        "ROUND-LOG.jsonl",
        "WORK-ITEM.json"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Pedido, confirmação do usuário, diagnóstico e triagem estão ligados ao work item e ao commit baseline.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json",
        "CYCLE-EXECUTION.md",
        "SPECIFY-EXECUTION.md"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Especialistas Orca posteriores registram requested/effective coincidentes em SPECIFY-EXECUTION.md e CYCLE-EXECUTION.md; a ampliação preserva os limites e grants.",
      "status": "PASS"
    },
    {
      "evidence": [
        "REQUEST.md",
        "PLAN-CONTEXT.md"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhuma alteração em plugin nesta sessão; obrigação para implementação futura registrada.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "REQUEST.md",
        "PLAN-CONTEXT.md"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Nenhuma versão publicada; obrigação futura de release pelo pipeline preservada.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "REQUEST.md"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "Constituição preservada com hash registrado; nenhuma emenda ou waiver foi aplicado.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
