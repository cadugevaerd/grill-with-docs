# PLAN-CONTEXT

## FASE-001 — Contrato do goal.md
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002, ADR-0004, ADR-0005, ADR-0006, ADR-0007
- BLs: BL-0001
- delivery-units: DU-001
- development-type: documentation

### HOW
- O documento é neutro em relação ao runtime de goal loop: nenhuma instrução
  pode assumir `token_budget`, transição de status ou tabela SQLite (ADR-0001).
- Estrutura em duas trilhas, separadas por `PLAN_ONLY_STOP` nomeado (ADR-0002).
- Dois **templates de objetivo** normativos, um por trilha, cada um embutindo a
  condição de parada na formulação julgada: "…até `<conclusão>` **ou** até que a
  resposta contenha a linha `GOAL-HOLD:`" (ADR-0004).
- `GOAL-HOLD: <motivo>` é emitido como última linha da resposta, motivo em uma
  frase.
- Lista fechada de pontos de interação, por trilha, mais cláusula residual
  fail-closed (ADR-0005).
- Seção de delegação Orca: sessão principal é leader e única Evidence Boundary;
  workers Orca paralelizam por subdomínio dentro da etapa e nunca produzem
  `step-output` nem escrevem em `.grill/` ou `.specify/reports/` (ADR-0006,
  ADR-0007).
- Todo `worker-start` declara `--model` e, quando suportado, `--effort`, e
  confere `launch.effective` contra `launch.requested`; divergência bloqueia.
  Exceção: em `implement-parallel` o modelo é derivado de
  `assets/workflow-tier-models.json`, não escolhido.
- Detecção do Orca, determinística: binário `orca` resolvível **e** `orca
  status` reportando runtime pronto. Falha em qualquer das duas cai no caminho
  degradado — execução sequencial pelo mecanismo nativo do runtime, sem perda
  de conformidade e sem bloqueio.
- O documento cita nominalmente os verbos de orientação existentes: `status
  --format markdown`, `gauntlet-status --work-id`, `checkpoint`, `phase-turn`
  (ADR-0008).
- Backstop instruído (BL-0001): o documento manda o operador declarar
  orçamento de turnos curto na trilha de entrevista, em vez de herdar o default
  do runtime, e exige a linha `GOAL-HOLD:` isolada como última linha da
  resposta.

## FASE-002 — Materialização pelo init
- phase: FASE-002
- ADRs: ADR-0003
- BLs: none
- delivery-units: DU-002
- development-type: documentation

### HOW
- Template em `plugin/skills/grill-with-docs/assets/`, materializado como
  `goal.md` na raiz do projeto consumidor, **no-clobber**, pela mesma máquina
  que fixa o `WORKFLOW.md`.
- Marcador de versão próprio, no formato `<!-- grill-with-docs-goal:v1 -->`,
  **independente** da versão SemVer do plugin — atrelá-lo ao SemVer geraria
  incompatibilidade declarada a cada bump, sem mudança de contrato.
- Tupla `ESSENTIAL` própria e congelada, literal, **nunca** derivada da tupla
  de nenhuma versão de `WORKFLOW.md`: derivá-la faria um typo reescrever o
  contrato em vez de reprovar um teste.
- `init` fixa o `goal.md` antes de montar o bundle, como já faz com o
  workflow, e reporta o estado no mesmo formato (`status`: `CREATED` |
  `REUSED` | `PRESERVED`), com `sha256` fixado em `state.json`.
- Documento humano preexistente que não case o contrato permanece byte-intacto
  e é reportado como incompatível, nunca sobrescrito.

## FASE-003 — Validador e distribuição
- phase: FASE-003
- ADRs: ADR-0003, ADR-0008
- BLs: none
- delivery-units: DU-003
- development-type: documentation

### HOW
- Validador novo em `tests/`, nomeado `validate_*.py` para entrar na suíte pelo
  glob de `tests/run_validators.py`.
- Somente biblioteca padrão, Python >=3.10, sem rede e sem exigir `specify`,
  `node` ou `backlogctl` reais — a matriz de CI não tem nenhum deles.
- O validador trava: presença do marcador, a tupla `ESSENTIAL` inteira, a
  existência dos dois templates de objetivo, a lista fechada de pontos de
  interação e a cláusula residual.
- Alterar `plugin/**` dispara **Bump obrigatório do plugin**: SemVer
  sincronizado nos oito lugares travados por `tests/validate_distribution.py`,
  incluindo a constante `VERSION` do próprio validador e os três headings de
  documentação.
- Dispara também **Release obrigatória por versão**: tag anotada imutável e
  GitHub Release ancorada no mesmo commit, criadas pelo pipeline no merge para
  `main`, nunca à mão.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
