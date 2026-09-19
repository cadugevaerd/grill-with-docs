# Research: Observar a instalação Codex do i-have-adhd

## R1 — Fonte do caminho da instalação no Codex

- **Decision**: compor `<home Codex>/plugins/cache/<marketplaceName>/<name>/<version>` a partir da entrada nativa (ADR-0001).
- **Rationale**: `codex plugin list --json` 0.154.0 não emite caminho, e `codex plugin` só oferece `add`, `list`, `marketplace` e `remove`. O mesmo layout já é consumido pelo preflight (`ensure_dependencies.py:278-288`).
- **Alternatives considered**: esperar `installPath` do Codex (sem prazo); ler o cache sem a listagem nativa (perde a prova de instalado/habilitado pelo harness).

## R2 — Onde conferir o conteúdo aprovado

- **Decision**: não conferir hash no observer; manter a verificação única em `approved_presentation_reference`, que já transforma conteúdo divergente em `STYLE-CONTENT-INCOMPATIBLE` (`agent_runtime.py:224-229`) e já é exigida por `prerequisites` (`compatible == "approved"`).
- **Rationale**: SSOT; o Claude já passa por esse ponto; duplicar a verificação criaria dois lugares para divergir.
- **Alternatives considered**: hash no observer, que duplicaria a regra e mudaria o código de recusa do caso 2.3.

## R3 — Resolução do home do Codex

- **Decision**: a mesma expressão já usada em `agent_runtime.py:440` e `:700` (`CODEX_HOME` ou `Path.home()/.codex`).
- **Rationale**: é a regra do próprio arquivo e equivale à do preflight (FR-003).
- **Alternatives considered**: importar `ensure_dependencies` no core, que criaria acoplamento de módulo sem ganho.

## R4 — Condições de aceite no observer

- **Decision**: exigir `installed is True`, `marketplaceName`, `name` e `version` como strings não vazias, segmentos sem separador de caminho nem `..`, diretório existente e `skills/i-have-adhd/SKILL.md` como arquivo regular. Falha em qualquer uma mantém `installation={}`.
- **Rationale**: os campos compõem um caminho; segmentos precisam ser seguros contra travessia. `installed=false` é declaração nativa de ausência.
- **Alternatives considered**: aceitar `installed` ausente, que é permissivo demais.

## R5 — Fixture

- **Decision**: gravar a entrada real de `i-have-adhd@i-have-adhd` da saída de `codex plugin list --json` 0.154.0 (captura sha256 `4bddc745…e721`), byte a byte no objeto da entrada, numa listagem `{"installed": [...], "available": []}`, sem entradas de outros plugins (que carregam caminhos locais da máquina).
- **Rationale**: memória `fixture-mais-limpa-que-a-realidade`; o teste atual usa listagem Codex com `installPath`, que o Codex não emite.
