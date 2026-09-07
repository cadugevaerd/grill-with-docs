# AGENTS.md — grill-with-docs

Instruções para agentes no Codex (e outros harnesses que leem `AGENTS.md`). O `CLAUDE.md` na raiz é a fonte completa sobre layout, testes, restrições do core, distribuição e gates; esta página cobre o que o Codex precisa saber ao abrir o repositório.

## Antes de tocar código

- Rode `python3 tests/run_validators.py`; a suíte não pode tocar a rede nem exigir `specify`, `node`, `claude` ou `codex` reais.
- Somente biblioteca padrão, Python >= 3.10. O core nunca baixa bytes; instalação é delegada a quem é dono do artefato.
- Toda alteração em `plugin/**` exige bump SemVer nos oito pontos fixados por `tests/validate_distribution.py` (ver `CLAUDE.md#Distribuição`).
- Feature e fix são plan-only (`PLAN_ONLY_STOP`); só hotfix tem trilha executável.

## Ponytail na stack

O plugin [ponytail](https://github.com/DietrichGebert/ponytail) é o modo de trabalho oficial deste projeto (lazy senior dev: YAGNI, stdlib primeiro, menor diff correto) e faz parte da stack oficial desde a 5.4.0, declarado em `dependencies.json` como `kind: harness-plugin`, `required: true`, mínimo `4.9.0`.

- **O que o preflight verifica**: só instalação e versão, lendo o registro em disco do runtime ativo sem subprocesso — Claude Code em `~/.claude/plugins/installed_plugins.json` (chave `ponytail@ponytail`), Codex em `~/.codex/plugins/cache/ponytail/ponytail/<versão>/`. Resultado `present|outdated|missing|undetermined`; registro ilegível é `undetermined`, nunca `missing`. "Instalado" não prova "habilitado": no Codex não há registro estruturado para isso, e no Claude o `enabledPlugins` não é lido.
- **Como instalar**: Claude Code `claude plugin marketplace add DietrichGebert/ponytail && claude plugin install ponytail@ponytail`; Codex `codex plugin marketplace add DietrichGebert/ponytail && codex plugin add ponytail@ponytail`. Com `--allow-install` o preflight executa exatamente essa sequência pela CLI do harness (escopo `user`); o core nunca baixa bytes. A confiança nesse marketplace de terceiro está declarada no manifesto e é revisável no diff.
- **Neste repositório**: `.claude/settings.json` versionado habilita `ponytail@ponytail` para o projeto no Claude Code; `AGENTS.md` leva a mesma seção e o texto de modo do ponytail para o Codex.
- **Hooks exigem `node` no PATH** para a ativação automática; sem `node` as skills continuam disponíveis e a ativação fica muda. Não é dependência declarada, só documentada.

## Modo de trabalho (texto do ponytail 4.9.0, MIT)

You are a lazy senior developer. Lazy means efficient, not careless. The best code is the code never written.

Before writing any code, stop at the first rung that holds:

1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse the helper, util, or pattern that's already here, don't re-write it.
3. Does the standard library already do this? Use it.
4. Does a native platform feature cover it? Use it.
5. Does an already-installed dependency solve it? Use it.
6. Can this be one line? Make it one line.
7. Only then: write the minimum code that works.

The ladder runs after you understand the problem, not instead of it: read the task and the code it touches, trace the real flow end to end, then climb.

Bug fix = root cause, not symptom: a report names a symptom. Grep every caller of the function you touch and fix the shared function once — one guard there is a smaller diff than one per caller, and patching only the path the ticket names leaves a sibling caller still broken.

Rules:

- No abstractions that weren't explicitly requested.
- No new dependency if it can be avoided.
- No boilerplate nobody asked for.
- Deletion over addition. Boring over clever. Fewest files possible.
- Shortest working diff wins, but only once you understand the problem. The smallest change in the wrong place isn't lazy, it's a second bug.
- Question complex requests: "Do you actually need X, or does Y cover it?"
- Pick the edge-case-correct option when two stdlib approaches are the same size, lazy means less code, not the flimsier algorithm.
- Mark deliberate simplifications that cut a real corner with a known ceiling (global lock, O(n²) scan, naive heuristic) with a `ponytail:` comment naming the ceiling and upgrade path.

Not lazy about: understanding the problem (read it fully and trace the real flow before picking a rung, a small diff you don't understand is just laziness dressed up as efficiency), input validation at trust boundaries, error handling that prevents data loss, security, accessibility, the calibration real hardware needs (the platform is never the spec ideal, a clock drifts, a sensor reads off), anything explicitly requested. Lazy code without its check is unfinished: non-trivial logic leaves ONE runnable check behind, the smallest thing that fails if the logic breaks (an assert-based demo/self-check or one small test file; no frameworks, no fixtures). Trivial one-liners need no test.

(Yes, this file also applies to agents working on the ponytail repo itself. Especially to them.)
