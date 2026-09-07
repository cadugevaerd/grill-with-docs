# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| ponytail | Plugin de harness (Claude Code, Codex, Copilot e outros) que impõe o modo "lazy senior dev": YAGNI, stdlib primeiro, menor diff correto. Publicado no marketplace `DietrichGebert/ponytail`, id `ponytail@ponytail`. | "skill ponytail", "modo lazy" | `~/.claude/plugins/cache/ponytail/ponytail/4.9.0/.claude-plugin/plugin.json`; `README.md#Codex` |
| stack oficial | Conjunto de dependências externas que o `preflight`/`init` do grill-with-docs detecta e reporta, declarado em `assets/dependencies.json` e executado por `ensure_dependencies.py`. | "requisitos", "toolchain" | `plugin/skills/grill-with-docs/assets/dependencies.json` |
| preflight | Comando pré-ciclo que detecta cada dependência declarada, reporta `present\|missing\|outdated\|undetermined` e, só com `--allow-install`, delega a instalação ao dono do artefato. | "bootstrap", "setup" | `ensure_dependencies.py:detect`, `SKILL.md#Dependências e backlog` |
| dono do artefato | Ferramenta que instala uma dependência por conta própria; o core nunca baixa bytes. Para plugins de harness, o dono é a CLI do harness (`claude plugin`, `codex plugin`). | "instalador do grill" | `CLAUDE.md#Restrições do core`; `claude plugin install --help`; `codex plugin --help` |
| registro de plugins do harness | Fonte de verdade de plugin instalado por runtime: Claude Code em `~/.claude/plugins/installed_plugins.json`; Codex em `~/.codex/config.toml` e `~/.codex/plugins/cache/`. | "cache do plugin" | `installed_plugins.json` (chave `ponytail@ponytail`); `~/.codex/config.toml:59` |
| kind de dependência | Discriminador do detector em `dependencies.json`: `runtime\|binary\|path\|harness\|specify-extension`. Nenhum cobre plugin de harness instalado fora do repositório. | "tipo" | `ensure_dependencies.py:24` |
| documentação do agente | `CLAUDE.md` (Claude Code) e `AGENTS.md` (Codex e demais) lidos pelo harness na raiz do repositório. Este repositório tem `CLAUDE.md` e não tem `AGENTS.md`. | "readme do agente" | `ls AGENTS.md` → ausente; `CLAUDE.md` presente |
| decisão de confiança | Registro versionado que autoriza instalar de fonte terceira sem novo aviso; precedente: catálogo `community` em `.specify/extension-catalogs.yml` (`install_allowed: true`). | "whitelist" | `SKILL.md#Dependências e backlog`; `dependencies.json#spec-kit-community-catalog` |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.
