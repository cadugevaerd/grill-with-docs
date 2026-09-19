# PLAN-CONTEXT

## FASE-001 — Observar a instalação Codex do i-have-adhd
- phase: FASE-001
- ADRs: ADR-0001
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
- Ponto único de mudança: o ramo de observação de instalação em `agent_runtime.py` (entorno de 490-516). Quando o provider for `codex` e a entrada nativa não tiver `installPath`, compor o caminho a partir de `marketplaceName`, `name` e `version` da própria entrada, sob o home do Codex, e aceitar somente com `installed=true`, diretório existente e `SKILL.md` com o hash aprovado da policy (ADR-0001).
- Reaproveitar a resolução do home/cache Codex que o preflight do Ponytail já usa; não criar segunda convenção.
- Stdlib apenas; sem subprocesso novo; o comando nativo exigido continua o mesmo (`codex plugin list --json`).
- Testes offline: listagem Codex real capturada (sem `installPath`) como fixture derivada da saída da ferramenta, não do código (memória `fixture-mais-limpa-que-a-realidade`); casos positivos e negativos: campo ausente, `installed=false`, diretório inexistente, hash divergente e Claude inalterado.
- Risco: layout do cache é contrato implícito do Codex; mudança futura degrada para `undetermined`, nunca para aceite falso.
