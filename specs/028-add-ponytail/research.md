# Research: Ponytail na stack oficial

Nenhum `NEEDS CLARIFICATION` na spec; as decisões abaixo consolidam o que a entrevista do work item selou e o que foi verificado em sessão (2026-09-07).

## R1 — Fonte de verdade da instalação por harness

- **Decision**: ler arquivos em disco. Claude: `installed_plugins.json` (chave `ponytail@ponytail`, lista com `version`, `installPath`, `scope`). Codex: cache `plugins/cache/ponytail/ponytail/<versão>/.codex-plugin/plugin.json`.
- **Rationale**: offline, determinístico, testável por fixture, sem timeout nem parse de texto. Mesmo layout de cache nos dois harnesses (`<marketplace>/<plugin>/<versão>/`).
- **Alternatives considered**: `claude plugin list --json` (existe, mas subprocesso e exige CLI no PATH); `codex plugin list` (só texto, sem `--json`); híbrido arquivo+CLI (dois caminhos de teste). Fonte: ADR-0003; `claude plugin list --help`; `codex plugin list --help`.

## R2 — Raiz de configuração de cada harness

- **Decision**: `CLAUDE_CONFIG_DIR` (fallback `$HOME/.claude`) e `CODEX_HOME` (fallback `$HOME/.codex`), lidos de `tools.environ`.
- **Rationale**: são as variáveis que os próprios harnesses honram para relocar o diretório de configuração; `tools.environ` já é a seam usada por `resolve_binary` para `${HOME}`.
- **Alternatives considered**: só `$HOME` (quebra em instalações relocadas); caminho fixo no manifesto (não testável sem tocar o home real).

## R3 — Instalação delegada e confiança no marketplace

- **Decision**: sob `--allow-install`, `marketplace add DietrichGebert/ponytail` seguido de `install`/`add ponytail@ponytail`, pela CLI do runtime ativo, escopo `user`.
- **Rationale**: o dono do artefato é a CLI do harness; o precedente do catálogo community do Spec Kit registra a confiança no manifesto, revisável no diff. Fonte: ADR-0004; `claude plugin install --help` (`--scope` default `user`); `codex plugin add --help`.
- **Alternatives considered**: `--scope project` no Claude (sem equivalente no Codex; escreve no consumidor); só remediação (trata o ponytail pior que o Spec Kit).

## R4 — Forma do campo de instalação por runtime

- **Decision**: campo novo `install_by_runtime: {"claude": [argv...], "codex": [argv...]}`; `install` (lista única) permanece para os kinds existentes.
- **Rationale**: as sequências diferem no verbo (`install` vs `add`), então um placeholder `${GRILL_RUNTIME}` não basta; um dicionário por runtime é legível e `load_manifest` valida a forma sem ambiguidade.
- **Alternatives considered**: placeholder de verbo (`${GRILL_PLUGIN_INSTALL_VERB}`) — opaco; duas entradas de dependência (uma por runtime) — a mesma dependência apareceria duas vezes no relatório.

## R5 — Semântica de `undetermined`

- **Decision**: registro ilegível ou de forma inesperada → `undetermined`; arquivo/diretório ausente ou chave ausente → `missing`.
- **Rationale**: é a semântica já usada por `extension_registry`/`extension_state` ("não observado" nunca vira "ausente"); `install()` já exclui `undetermined` de instalação automática.
- **Alternatives considered**: tratar ilegível como `missing` (instalaria por cima do que pode existir).

## R6 — Versão mínima

- **Decision**: `min: 4.9.0`.
- **Rationale**: única versão verificada nos dois harnesses; suporte a Codex documentado no README dessa versão. Fonte: DQ-0006.
- **Alternatives considered**: sem `min` (sem garantia de suporte Codex).

## R7 — Escopo documental

- **Decision**: `CLAUDE.md`, `AGENTS.md` e `.claude/settings.json` deste repositório; nada no consumidor. Fonte: ADR-0001, DQ-0005.
- **Alternatives considered**: materialização no consumidor via `init` (política nova de escrita fora de `.grill/`).

## R8 — Estado "habilitado"

- **Decision**: fora de escopo; documentar que no Codex "instalado" não prova "habilitado" (BL-0001 resolvido como limite aceito).
- **Rationale**: Codex não tem `enable/disable` nem registro estruturado; no Claude, `enabledPlugins` é configuração de projeto, não instalação.

## R9 — Dependência de `node`

- **Decision**: não declarar `node` como dependência; documentar. Fonte: README do ponytail, linha 117 — sem `node` as skills funcionam e a ativação automática fica muda.
