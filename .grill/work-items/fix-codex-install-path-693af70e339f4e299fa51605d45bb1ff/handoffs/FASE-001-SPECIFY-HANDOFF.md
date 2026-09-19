# FASE-001 — Observar a instalação Codex do i-have-adhd

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: observer de instalação, listagem nativa, layout do cache Codex
- ADRs: ADR-0001
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

**Resultado observável.** Numa sessão Codex, a entrada GWD (`$grill-with-docs iniciar|retomar`) deixa de ser recusada com `STYLE-DEPENDENCY-UNDETERMINED` quando a cópia aprovada do i-have-adhd está instalada e habilitada. A presença da instalação passa a ser reconhecida a partir da listagem nativa do Codex, e o fluxo segue para o bootstrap de leitura (`load_request`), como já acontece no Claude.

**Atores.** A sessão líder GWD no Codex, que executa a listagem nativa; a suíte de validadores, que passa a exercitar o formato real da listagem Codex.

**Cenários.**
1. Codex, plugin listado com `installed=true` e versão aprovada, cópia existente e com o hash aprovado → `installation=present`; a entrada chega ao `load_request`.
2. Codex, plugin listado com `installed=false` → a instalação continua não reconhecida; a entrada recusa.
3. Codex, cópia inexistente no local correspondente à entrada listada → continua não reconhecida; recusa.
4. Codex, cópia existente com conteúdo de hash diferente do aprovado → continua não reconhecida; recusa.
5. Codex, entrada listada sem algum dos campos que identificam a cópia → continua não reconhecida; recusa.
6. Claude, listagem com `installPath` → comportamento atual, sem nenhuma diferença.

**Escopo excluído.** Runtime Claude; mudar o comando nativo exigido; instalar, reparar ou mover a cópia; as demais lacunas registradas no T029 do work item de origem (assumir item de líder morto, preview do adopt diante do fence, troca antes do primeiro checkpoint, suspensão não registrada, campos do checkpoint de troca).

**Critérios de aceite.**
- Os seis cenários acima cobertos por validadores offline, usando como fixture a saída real do `codex plugin list --json` 0.154.0 (sem `installPath`), e não uma fixture derivada do código.
- `python3 tests/run_validators.py` em exit 0 e `git diff --check` limpo.
- Nenhum validador depende de `codex`, `claude`, `node` ou rede reais.
- Reexecução live do caso C1 do T029 numa sessão Codex supervisionada chega a `installation=present` e ao `load_request`. Essa reexecução é evidência do T029 no work item de origem, não aceite desta fase.

## WHY

**Valor.** Sem isso, nenhuma entrada GWD 6.0.0 funciona no Codex, e o aceite FR-024/SC-008 do work item `feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa` fica bloqueado na metade Codex da matriz (C1/C2).

**Evidência.** Triagem `tri-codex-install-path` (bugfix, high), com laudo `code-debug` de causa raiz comprovada em `.grill/triage-evidence/codex-install-path-debug.md`: a listagem nativa do Codex 0.154.0 não informa caminho, o Codex não tem outro comando que o exponha, e a instalação real existe íntegra.

**Restrições.** Continuar fail-closed: qualquer evidência incompleta ou divergente mantém a instalação não reconhecida. Somente biblioteca padrão; o core nunca baixa bytes; sem subprocesso novo. A candidata 6.0.0 ainda não foi publicada: se esta correção entrar antes do ship da 6.0.0, o bump da 6.0.0 a cobre; se entrar depois, o ciclo executor faz bump patch (6.0.1) e a release correspondente.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
