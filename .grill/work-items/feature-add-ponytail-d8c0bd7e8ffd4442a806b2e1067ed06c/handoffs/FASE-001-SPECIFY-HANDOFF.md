# FASE-001 — Ponytail na stack oficial: detecção, instalação delegada e documentação

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: ponytail, stack oficial, preflight, dono do artefato, registro de plugins do harness, kind de dependência, documentação do agente, decisão de confiança
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: BL-0001

## WHAT
- delivery-units: DU-001, DU-002
- development-type: platform-devops, documentation

**Resultado observável.** `preflight ROOT --runtime claude|codex` passa a listar a dependência `ponytail` (`kind: harness-plugin`, `required: true`) com `present`, `outdated` ou `missing`, versão resolvida e origem; ausente ou abaixo de `4.9.0`, o relatório nomeia a remediação exata do runtime ativo. Com `--allow-install`, a instalação é executada pela CLI do harness (`claude plugin marketplace add` + `claude plugin install`, ou `codex plugin marketplace add` + `codex plugin add`), nunca pelo core. `init` reporta o mesmo em `dependencies`. `GRILL_SKIP_DEPENDENCIES=1` e `--require-dependencies` tratam o ponytail como qualquer outra dependência declarada.

**Atores.** Quem conduz a sessão grill (Claude Code ou Codex), o humano que autoriza `--allow-install`, e a CI (matriz 3 SOs × Python, sem `claude`, `codex` ou rede).

**Cenários.**
1. Ponytail 4.9.0 instalado no runtime ativo → `present`, versão `4.9.0`, `source` aponta o registro/caché lido.
2. Ponytail ausente, sem `--allow-install` → `missing`, `remediation` com os dois comandos do runtime; `init` segue e lista em `missing_required`.
3. Ponytail ausente, `--allow-install` → os dois comandos são executados pelo dono, na ordem, e o relatório final reflete `present`.
4. Ponytail abaixo de `4.9.0` → `outdated`, remediação de reinstalar.
5. `--require-dependencies` com ponytail ausente → `MISSING-DEPENDENCY`.
6. `--runtime codex` com cache `~/.codex/plugins/cache/ponytail/ponytail/<versão>/` → `present`; sem cache → `missing`.
7. Toda a suíte roda sem `claude`/`codex` reais, com `Toolchain` fake e fixtures de registro/caché.

**Escopo deste repositório (dogfooding).** `CLAUDE.md` ganha seção que declara o ponytail na stack, o que o preflight verifica e como instalar; `AGENTS.md` nasce com o mesmo conteúdo essencial mais o texto de modo do ponytail para o Codex; `.claude/settings.json` versionado habilita `ponytail@ponytail`. `SKILL.md` e `README.md` do plugin mencionam a dependência nova.

**Critérios de aceite.**
- `python3 tests/run_validators.py` verde, incluindo casos novos para `harness-plugin` nos dois runtimes.
- Nenhum teste toca rede nem exige `claude`/`codex`.
- `dependencies.json` continua `grill-dependencies/v1` e os kinds antigos não mudam de comportamento.
- Bump SemVer minor aplicado nos oito pontos fixados por `validate_distribution.py`.

## WHY
O ponytail é o modo de trabalho adotado pelo projeto; hoje sua presença depende da máquina de quem conduz a sessão, invisível ao preflight e à documentação. Declará-lo na stack oficial torna a ausência detectável e a instalação reprodutível pelo mesmo contrato das demais dependências (ADR-0002, ADR-0003, ADR-0004), e documentá-lo aqui fecha o dogfooding sem criar política nova de escrita no consumidor (ADR-0001).
