# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": ["ROUND-LOG.jsonl R-0001..R-0009", "docs/adr/ADR-0001.md..ADR-0006.md seções Contexto com fontes e estado de evidência"],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Cada decisão cita arquivo:linha, saída de comando ou guia Orca versionado. O gap de placement ficou declarado em ADR-0005 e BL-0001, sem ser apresentado como fato.",
      "status": "PASS"
    },
    {
      "evidence": ["WORK-ITEM.json immutable_sha256 ba17ab51...", "branch cadugevaerd/lookdown", "depends-on-work feature-new-subagents-unified-69f619a1..."],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "O bundle é próprio e tem identidade imutável. Só este diretório foi escrito, e a dependência de outro work item está declarada, sem escrita nele.",
      "status": "PASS"
    },
    {
      "evidence": ["handoffs/FASE-001-SPECIFY-HANDOFF.md", "nenhum arquivo fora de .grill/work-items/feature-orca-child-workers-* alterado"],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "A entrevista produz apenas decisões e o handoff, e termina em PLAN_ONLY_STOP sem código nem publicação.",
      "status": "PASS"
    },
    {
      "evidence": ["state.json development.current_step=specify, todas as etapas pending"],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "O work item começa em specify, sem saltos. As onze etapas ficam para o ciclo seguinte.",
      "status": "PASS"
    },
    {
      "evidence": ["state.json steps verify/review/ship pending"],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Nenhum ship é iniciado nesta sessão. A ordem verify, review e ship permanece exigida pelo WORKFLOW v4.",
      "status": "PASS"
    },
    {
      "evidence": ["docs/adr/ADR-0002.md", "docs/adr/ADR-0004.md exception", "BL-0001"],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Orca indisponível, launch divergente e troca de CLI sem causa observada bloqueiam. O gap de placement bloqueia tasks de despacho até ser resolvido.",
      "status": "PASS"
    },
    {
      "evidence": ["DECISION-FRONTIER.md final-ref por DQ", "ROUND-LOG.jsonl", "DELIVERY-MAP.md MOD-001/DU-001"],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Toda DQ aponta ADR ou rodada, e todo ADR aponta fonte. A DU liga fase, módulo e aceite.",
      "status": "PASS"
    },
    {
      "evidence": ["docs/adr/ADR-0003.md", "orca orchestration worker-start --help", "orca status --json orchestration.worker-launch-preferences.v1"],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "O plano exige --model sempre, --effort pela tabela única e conferência de launch.effective com bloqueio na divergência, sem reuso de --terminal. Isso reforça a cláusula e não a enfraquece.",
      "status": "PASS"
    },
    {
      "evidence": ["docs/adr/ADR-0006.md: versão 7.0.0 e oito locais de validate_distribution.py"],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "A mudança em plugin/** já nasce com bump MAJOR declarado para o ciclo de implementação.",
      "status": "PASS"
    },
    {
      "evidence": ["CLAUDE.md §Gates de integração publish.yml", "docs/adr/ADR-0006.md"],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "A 7.0.0 será publicada pelo pipeline publish.yml com tag e release ancoradas no mesmo commit. Nada é publicado nesta sessão plan-only.",
      "status": "PASS"
    },
    {
      "evidence": ["constitution.md sha256 54d5522b...", "nenhuma emenda proposta (DU-001 scope-out)"],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição é lida e preservada byte a byte, e nenhum ADR a dispensa ou emenda.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
