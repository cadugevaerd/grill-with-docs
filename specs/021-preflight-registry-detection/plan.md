# Implementation Plan: Detecção de extensão pelo registro

**Branch**: `worktree-fix-preflight-ansi` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-preflight-registry-detection/spec.md`

## Summary

`installed_extensions` (`plugin/skills/grill-with-docs/scripts/ensure_dependencies.py:154-160`) tokeniza a saída crua de `specify extension list` com `re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", output)`. Duas falhas independentes saem daí: o escape ANSI da linha do slug (`\x1b[2mgit\x1b[0m`) produz o token `2mgit`, e o `findall` sobre a saída inteira casa palavras de linhas de descrição — `bugfix` é dado como presente pela frase `Structured bugfix workflow`.

A abordagem é trocar a fonte, não consertar o regex: ler `.specify/extensions/.registry`, JSON com `schema_version`, e o slug como **chave** de mapa. Chave exata elimina as duas classes de uma vez, dá `enabled` e `version`, e remove o subprocess do caminho de detecção — o que torna o teste um fixture em vez de mock de processo filho.

Duas consequências entram no escopo: registro não legível vira dependência declarada própria com status `undetermined` nos `ext:*` (nunca `missing`), e a remediação passa a seguir o motivo observado (`enable` para desabilitada, `add` para ausente).

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão

**Primary Dependencies**: nenhuma. O core não tem dependência externa e não baixa bytes.

**Storage**: arquivos no repositório — `.specify/extensions/.registry` (leitura), `plugin/skills/grill-with-docs/assets/dependencies.json` (manifest)

**Testing**: `unittest` via `tests/run_validators.py` (glob de `validate_*.py`). Baseline 1066 testes, 21 validadores, exit 0, 1 skip dependente de ambiente.

**Target Platform**: ubuntu/windows/macos × Python 3.10 e 3.13 (matriz de `ci.yml`)

**Project Type**: CLI/biblioteca — plugin distribuído

**Performance Goals**: N/A. A troca **remove** um subprocess por execução de preflight.

**Constraints**: nenhum teste pode tocar a rede nem exigir `specify`, `node` ou `backlogctl` reais. Detecção é read-only.

**Scale/Scope**: um módulo (`ensure_dependencies.py`), um manifest, um validador novo, mais o contrato de distribuição.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Gate | Situação |
|---|---|---|
| Evidência antes de afirmação | O relatório não pode afirmar situação não observada | **PASS por construção** — é o objeto da mudança: `undetermined` existe exatamente para não afirmar ausência não observada |
| Work item isolado e ownership | Trabalho sob `work_id` próprio, branch dedicada | **PASS** — `fix-preflight-ansi-09d77024258a45ecbe612a8d22ffea95`, branch `worktree-fix-preflight-ansi` |
| Feature/fix plan-only | O ciclo de 11 etapas é do executor posterior, não da sessão de planejamento | **PASS** — o bundle parou em `PLAN_ONLY_STOP`; este plano pertence ao ciclo externo |
| Sequência obrigatória | Sem saltos entre as 11 etapas | **PASS** — `specify` concluído, `plan` corrente, demais pendentes |
| Verify/review antes de ship | Ship só após verify e review com evidência | **Gate ativo** — reavaliado na etapa `ship` |
| Fail-closed sem waiver | Ambiguidade e ausência de evidência bloqueiam | **PASS** — `undetermined` entra em `missing_required` e bloqueia; as três formas de ilegibilidade convergem |
| Rastreabilidade | Decisão → fase → commit | **PASS** — FR-001..011 ↔ ADR-0001..0004 ↔ SGD-16 |
| Bump obrigatório do plugin | Alteração em `plugin/**` exige bump replicado | **Gate ativo** — 3.3.0 → 3.3.1 em oito lugares, verificado por `tests/validate_distribution.py` |

Nenhuma violação. A tabela de Complexity Tracking fica vazia por isso.

## Project Structure

### Documentation (this feature)

```text
specs/021-preflight-registry-detection/
├── plan.md              # This file
├── spec.md              # /speckit-specify output
├── tasks.md             # /speckit-tasks output
├── verify.md            # /speckit-verify-review-ship-verify output
├── review.md            # /speckit-verify-review-ship-review output
└── checklists/
    └── requirements.md
```

Sem `research.md`: a investigação foi feita na entrevista do work item e está em ADR-0001..0004, com as medições reproduzíveis. Sem `data-model.md` nem `contracts/`: a única estrutura de dados é o registro do spec-kit, descrito abaixo, e o contrato de saída é o `grill-dependencies/v1` já existente.

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/
├── assets/
│   └── dependencies.json          # + entrada spec-kit-extension-registry; + campo enable nos ext:*
└── scripts/
    └── ensure_dependencies.py     # troca da fonte, status undetermined, remediação por motivo

tests/
├── validate_extension_detection.py  # NOVO — contrato da detecção (entra na suíte por glob)
└── validate_distribution.py         # constante VERSION -> 3.3.1
```

**Structure Decision**: layout existente, sem diretório novo. O validador novo entra na suíte sozinho pelo glob de `validate_*.py` em `tests/run_validators.py`.

## Phase 0 — Fonte de verdade

Formato observado de `.specify/extensions/.registry` (JSON, `schema_version: "1.0"`):

```json
{
  "schema_version": "1.0",
  "extensions": {
    "git": { "version": "1.0.0", "enabled": true, "priority": 10, ... }
  }
}
```

O slug é chave. `enabled` é booleano. `version` é string.

Medições que sustentam a escolha (ADR-0001):

- `specify extension list` não tem modo machine-readable — só `--available` e `--all`.
- `NO_COLOR=1` **não** limpa os escapes; sobra `\x1b[1m`/`\x1b[2m`. `TERM=dumb` limpa, mas amarra a correção a comportamento de env de uma versão do Rich/Typer.
- Sob o parser atual: `git`, `agent-assign` e `verify-review-ship` ausentes do set; `bugfix` presente por texto de descrição; os quatro tokens `2m<slug>` presentes.

## Phase 1 — Design

### 1. Leitura do registro

`extension_registry(root: Path) -> dict[str, dict] | None`

Retorna o mapa de extensões, ou `None` quando o registro **não é legível**. `None` é o único canal de indeterminação, e cobre os três casos com o mesmo desfecho:

- arquivo ausente (`OSError`);
- JSON inválido (`json.JSONDecodeError`);
- `schema_version` que não começa com `1.` (versão de contrato não reconhecida).

`schema_version` é verificado **antes** de qualquer acesso ao conteúdo. Nada de `except Exception`: as exceções capturadas são nomeadas, coerente com o resto do módulo.

### 2. Avaliação por extensão

| Observação | status | reason | remediação |
|---|---|---|---|
| slug no mapa e `enabled: true` | `present` | — | — |
| slug no mapa e `enabled: false` | `missing` | registrada porém desabilitada | `specify extension enable <slug>` |
| slug fora do mapa | `missing` | ausente do registro | `specify extension add <slug>` |
| registro `None` | `undetermined` | registro ilegível (causa nomeada) | **nenhuma** |

`version` é preenchida a partir do registro quando `present`. `source` passa a ser o caminho do registro, não `"specify extension list"`.

### 3. Remediação por motivo observado

`remediation()` hoje só renderiza o campo `install` do manifest (linhas 143-151). Ganha dois caminhos, ambos **declarados no manifest** — a invariante "só comandos declarados no manifest" não é rompida:

- entradas `specify-extension` ganham o campo `enable`: `["specify", "extension", "enable", "<slug>"]`;
- entradas quaisquer podem trazer `remediation` como string literal, usada quando não há comando executável a propor.

`install()` passa a pular itens `undetermined` — não há o que instalar quando a presença não foi observada — e, para extensão desabilitada, executa o comando `enable` e não o `add`. Emitir `add` para algo já instalado é a mesma família de erro que originou este trabalho.

### 4. Registro como dependência declarada

Entrada nova no manifest, `kind: path`, na posição imediatamente anterior aos `ext:*`, para que a causa raiz apareça antes das consequências no relatório ordenado:

```json
{
  "id": "spec-kit-extension-registry",
  "kind": "path",
  "required": true,
  "path": ".specify/extensions/.registry",
  "reason": "registro do Spec Kit e a fonte de verdade das extensoes instaladas",
  "remediation": "instale ao menos uma extensao com `specify extension add <slug>`, ou alinhe a versao do Spec Kit se o schema do registro nao for reconhecido"
}
```

Sem `install`: o grill não cria o registro do spec-kit. A remediação é textual porque as duas causas (ausência e schema não reconhecido) não têm um comando único que sirva às duas.

O ramo `kind: path` de `detect()` compara existência e `contains`. Ele não valida `schema_version`, então schema não reconhecido deixaria a entrada `present` enquanto os `ext:*` ficam `undetermined` — incoerente. O ramo `path` ganha uma verificação declarada por `schema_check`, aplicada somente a esta entrada.

### 5. `missing_required` e verdict

`missing_required` já é `report["required"] and report["status"] != "present"` (linha 329), então `undetermined` bloqueia sem mudança. É o comportamento desejado e está coberto por teste explícito, para não depender de acidente.

### 6. Contrato e testes

`SCHEMA` permanece `grill-dependencies/v1` (ADR-0004). Os validadores que enumeram status exaustivamente são atualizados na mesma fase — é o que impede a adição de passar silenciosa.

`tests/validate_extension_detection.py` cobre os cenários da spec com fixture JSON em diretório temporário, sem `specify`, sem subprocess e sem rede.

## Complexity Tracking

> Constitution Check sem violações. Nada a justificar.
