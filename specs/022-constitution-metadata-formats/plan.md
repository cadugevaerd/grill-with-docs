# Implementation Plan: Metadados da constituição em suas três formas reais

**Spec**: `specs/022-constitution-metadata-formats/spec.md`
**Triagem**: `tri-9981372e1dbc4d7ebfcf532f09d9573a` — rota `bugfix`, severidade `high`, causa raiz comprovada.

## Abordagem escolhida

Um leitor único, `constitution_metadata(text)`, dentro do próprio `audit_decisions.py`, que devolve o
dicionário de metadados já normalizado. O bloco de validação (`:276-288`) passa a consumir esse
leitor e nada mais muda no fluxo do `audit`.

### Alternativas descartadas

- **Mover para `grill_core/`**: `audit_decisions.py` é script standalone carregado por
  `backlog_bridge.py:184` via `sibling()`. Introduzir dependência de pacote quebraria esse caminho
  por um ganho de organização que não existe — o parser de artefatos já mora aqui e é SSOT.
- **Estender `FIELD`/`TOP_FIELD`**: blast radius em cinco outros artefatos (ROADMAP FASE,
  DECISION-BACKLOG BL, handoffs, PLAN-CONTEXT, DECISION-FRONTIER) mais descrições de work item.
  Um regex mais permissivo ali produziria campos fantasma em documentos que hoje parseiam certo.
- **Gatear por marcador**: pular as checagens quando `<!-- grill-with-docs-constitution:v1 -->`
  estiver ausente. Resolveria o falso positivo abrindo um falso negativo — constituição sem metadado
  auditável passaria calada, contra a cláusula "Fail-closed sem waiver".
- **Normalizar a constituição do consumidor**: inverteria a hierarquia. O arquivo está conforme o
  template oficial e é read-only depois do `init`.

## Desenho

```
HTML_COMMENT  (?s)<!--.*?-->
HEADING       (?m)^(#{2,3})\s+(.+?)\s*$
FOOTER_LINE   (?m)^.*\*\*\s*(?:Version|Ratified|Last\s+Amended)\s*\*\*\s*:.*$
FOOTER_PAIR   \*\*\s*([^*|:]+?)\s*\*\*\s*:\s*([^|]*)
GOVERNANCE_NAMES = {"governance", "governança", "governanca"}

footer_fields(text)          -> dict   # pares do rodapé, quebrados no `|`
section_body(text, names)    -> str    # corpo do H2/H3 de governança, sem a linha do rodapé
constitution_metadata(text)  -> dict   # o leitor único
```

`constitution_metadata`:

1. descarta comentários HTML — só para extração. A varredura de placeholders (`:280`) continua sobre
   o texto cru, sem mudança de comportamento;
2. `{**fields(t), **top_fields(t)}` — precedência atual preservada;
3. o rodapé preenche **somente chave ausente ou vazia** (FR-004);
4. governança cai para `section_body` quando o campo não existe (FR-002).

O bloco `:276-288` troca uma linha (`values = constitution_metadata(text)`); as strings dos findings
ficam idênticas (FR-006).

## Cobertura

`tests/validate_constitution_metadata.py`, novo, entra sozinho na suíte pelo glob de
`run_validators.py`. Fixtures derivadas dos artefatos shipados, nunca do parser:

- forma bullet gerada em tempo de teste a partir de `assets/GRILL-CONSTITUTION.template.md`, com a
  mesma substituição que `grill_workspace.py:397` faz — assim não há como divergir do que o `init`
  escreve;
- forma Spec Kit vendorizada em `tests/fixtures/constitutions/spec-kit-filled.md`, gerada do template
  upstream com os placeholders preenchidos e **os comentários preservados**, inclusive o rodapé de
  exemplo comentado.

Vendorizar em vez de ler `.specify/templates/` em tempo de teste isola a suíte do churn de refresh do
catálogo, mantendo a fidelidade ao formato real.

Pelo menos um caso de cada forma roda o CLI de verdade por subprocess, não só a função pura — a
lição do defeito anterior (`specs/021-preflight-registry-detection/`) foi exatamente essa.

## Restrições respeitadas

- Somente biblioteca padrão, Python >= 3.10.
- Sem rede; sem `specify`, `node` ou `backlogctl` reais.
- `audit` permanece read-only.
- `FIELD` e `TOP_FIELD` intocados.

## Bump

`plugin/**` mudou → 3.3.1 → 3.3.2 nos oito lugares travados por `tests/validate_distribution.py`.
