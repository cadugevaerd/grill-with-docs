## Review Report

Verdict: APPROVE
Source fingerprint: tree ccc4c9746a6088650aaaa7744e8611b5afa804e358e4cd11eeead25883222c11 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 7a9332aeedf9791bcdbcc4d25fa47f3f13b218274ae0d6145f86a4e777c9ccca
                    (idêntico ao de Converge/Verify; `source-fingerprint.sh specs/028-add-ponytail` em HEAD `6f02757`, revalidado após o commit de learnings; diff adicional = 3 linhas de prosa em CLAUDE.md, sem código)

Escopo revisado: `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py` (+104/−5), `assets/dependencies.json` (+21), `tests/validate_dependencies_contract.py` (+311, 25 testes novos + 1 reescrito), `tests/validate_attestation_emitter_contract.py` (T015), 4 manifests, `SKILL.md`, `session-protocol.md`, `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json`, `tests/validate_distribution.py`. Revisor único em fallback sequencial (leader, read-only); Orca disponível mas o diff é pequeno e sem paralelismo útil.

### Test Quality
- 4 classes novas cobrem as quatro saídas por runtime, relocação por `CLAUDE_CONFIG_DIR`/`CODEX_HOME`, ausência de subprocesso em `detect()`, sequência de instalação exata por runtime, falha no primeiro comando, exclusão de `undetermined` da instalação, invariância byte-idêntica dos kinds antigos, recusas de `load_manifest`, `MISSING-DEPENDENCY` e `SKIPPED`. Fixtures em `HOME` temporário via `StubToolchain(environ=...)`, sem rede nem binários reais.
- `test_install_runs_only_manifest_commands_and_expands_the_placeholder` (tests/validate_dependencies_contract.py:567-590) foi reescrito preservando a intenção original — nenhuma invocação de `claude`/`codex` como agente — e tornando-a precisa: todo argv com `argv[0] ∈ {claude, codex}` deve ser um instalador declarado em `declared_install(entry, "claude")`; `["codex","exec",...]` e formas `-p`/`--print`/bare continuam recusadas.
- Minor: US3 (docs/settings) só tem verificação por `grep`/`json.load` no quickstart; `validate_distribution` cobre os headings. Aceitável para conteúdo documental.

### Runtime Correctness
- `plugin_registry_state` (ensure_dependencies.py:247-306): `missing` × `undetermined` distintos e conservadores — chave presente com lista vazia ou registro sem `version` string → `undetermined` (não instala por cima); arquivo ausente/chave ausente → `missing`. Codex: maior versão por `parse_version`, `version` do JSON prevalece; `plugin.json` ilegível só vira `undetermined` se nenhuma versão legível existir. `HOME="~"` expandido como em `resolve_binary`.
- `detect()` nunca chama `tools.run` neste kind (provado por teste); a instalação passa por `install()` já existente, com `INSTALL_TIMEOUT` e `FAILED` no primeiro erro.
- `load_manifest` valida `install_by_runtime` (chaves ⊆ `RUNTIMES`, argv lista de strings) e exige `plugin`/`marketplace` no kind novo; kinds antigos não ganham exigência nova.
- Minor (ensure_dependencies.py:274): o ramo `else` de `plugin_registry_state` trata qualquer runtime ≠ `claude` como Codex; inalcançável pela CLI porque `detect()` já recusa runtime fora de `RUNTIMES`, mas um `elif runtime == "codex"` + erro explícito tornaria a função defensiva por si. Não bloqueia.
- Minor: diretório de versão sem nome parseável e sem `version` no JSON é ignorado (vira `missing` se for o único). O cache real do Codex usa `<versão>/`; contrato documenta o fallback. Não bloqueia.

### Readability
- Docstrings explicam o porquê (R1, R5) no estilo do arquivo; `declared_install` nomeia a diferença de verbo entre harnesses. Comentário no pós-processamento de `undetermined` explica por que a razão específica sobrevive ao texto genérico.
- T015 (`_activated_work_id`): descoberta determinística (`sorted`) com fallback literal documentado; `.grill/gauntlet.yaml` e `.grill/work-items/` são versionados, então um clone limpo resolve um bundle ativado. Minor: se um dia nenhum bundle ativado existir na árvore, os dois casos `CliRefusesBeforeReading` reprovam com `WORK-ITEM-MISSING` — o docstring já nomeia esse limite.

### Architecture
- Sem módulo novo; kind adicionado no mesmo detector e no mesmo laço de instalação, reutilizando `Toolchain`, `meets`, `parse_version`, `_read_json`. Dependência de direção preservada: manifesto → detector → CLI; `grill_workspace.py` intocado.
- `install_by_runtime` coexiste com `install` sem migrar entradas antigas (invariância provada).

### Security
- Nenhum download pelo core; instalação só sob `--allow-install`, por argv fixo do manifesto, `shell=False` (herdado de `Toolchain.run`). Confiança no marketplace `DietrichGebert/ponytail` declarada no manifesto e visível no diff (mesmo modelo do catálogo community). Detecção lê arquivos do próprio usuário; nenhum caminho vem de entrada externa. Sem segredos no diff.

### Performance
- Claude: 1 leitura de JSON. Codex: 1 `iterdir` + 1 JSON por versão em cache (tipicamente 1–2). Sem subprocesso. Suíte completa 8m19s local (inalterado na ordem de grandeza; `validate_dependencies_contract.py` 63 testes em <0,2s).

### Critical Issues
- Nenhum.

### Important Issues
- Nenhum.

### Constitution References (only for discovered conflicts)
- Nenhum conflito descoberto.

### Final Recommendation
- APPROVE: run `/speckit.verify-review-ship.ship`
