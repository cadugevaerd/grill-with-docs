# Relatório de debug

## Status

Causa raiz comprovada.

## Sintoma reproduzido

`audit` devolve `NO-GO` / `ARTIFACT-INVALID` com quatro achados sobre a constituição em qualquer
projeto cuja `.specify/memory/constitution.md` siga o template oficial do Spec Kit:

```
- constitution: governance vazio
- constitution: last-amended ISO inválido
- constitution: ratified ISO inválido
- constitution: version SemVer inválida
```

Reproduzido nesta árvore copiando `tests/fixtures/go-project` (que audita `GO`) e trocando apenas a
constituição por uma no formato oficial. O projeto original continua `GO`; o mesmo projeto com a
constituição do Spec Kit passa a `NO-GO` com exatamente esses quatro achados.

Relatado primeiro por uma sessão consumidora rodando o plugin 3.3.0; o bloco de código é
byte-idêntico em 3.3.1, então o defeito sobrevive à atualização.

## Evidências

- `plugin/skills/grill-with-docs/scripts/audit_decisions.py:278` (antes do fix):
  `values = {**fields(text), **top_fields(text)}`.
- `FIELD` (`:21`) casa `- chave: valor`; `TOP_FIELD` (`:22`) casa `chave: valor` no início da linha.
- Rodapé real, idêntico ao template upstream `.specify/templates/constitution-template.md:49`:
  `**Version**: 1.2.0 | **Ratified**: 2026-07-30 | **Last Amended**: 2026-08-11`.
- `audit_decisions.py:758`: qualquer item em `findings` produz `NO-GO` / `ARTIFACT-INVALID`.
- `grill_workspace.py:392-408` (`ensure_managed_constitution`) devolve `(False, hash)` para uma
  constituição preexistente — preservação byte a byte, sem reescrita.
- `grill_workspace.py:501` (`validate_constitution_text`) só reprova placeholder ou conteúdo vazio;
  `:511` (`constitution_clauses`) só exige headings H2/H3. Uma constituição do Spec Kit passa nos dois.

## Causa raiz

O leitor de metadados da constituição conhece uma única forma de campo (`chave: valor`, com ou sem
bullet) e é aplicado a um arquivo que o próprio ecossistema Spec Kit produz em outra forma. Três
incompatibilidades simultâneas:

1. as chaves vêm em `**bold**` — `**Version**` não é `version`;
2. os três pares ficam na mesma linha, separados por `|`, e os regex são ancorados a linha inteira;
3. `governance` é procurado como campo, mas no arquivo real é heading `## Governance` seguido de
   prosa — não existe, em nenhum idioma, uma linha `governance: algo`.

O defeito é do parser, não do conteúdo: o arquivo do consumidor está conforme o template oficial, e
a skill trata a constituição como read-only depois do `init`. Reescrever o arquivo para agradar o
parser inverteria a hierarquia — a fonte de verdade se adaptando ao bug.

## Cadeia causal

`init` preserva a constituição preexistente byte a byte (`ensure_managed_constitution`) → o arquivo
preservado está no formato do Spec Kit → `audit` lê seus metadados com `fields`/`top_fields`, que
não casam com o rodapé bold nem com o heading de governance → `values` fica sem `version`,
`ratified`, `last-amended` e `governance` → quatro `findings` → `audit_decisions.py:758` converte
qualquer finding em `NO-GO` / `ARTIFACT-INVALID` → o veredito falso encobre o bloqueio real do
projeto.

## Arquivos envolvidos

- `plugin/skills/grill-with-docs/scripts/audit_decisions.py` — `:21-22` (regex), `:276-288` (bloco
  de validação), `:758` (conversão em veredito).
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py` — `:392-408`, `:501`, `:511`.
- `.specify/templates/constitution-template.md:49` — o rodapé oficial.
- `plugin/skills/grill-with-docs/assets/GRILL-CONSTITUTION.template.md:4-7` — a forma gerenciada.
- `tests/validate_contract.py:67-69`, `tests/fixtures/{go,blocked}-project/` — as fixtures.

## Por que 1088 testes não pegaram

Coexistem três formas de constituição e nenhum teste exercitava a forma real:

| Forma | Onde vive | Regex que casa | Testada via audit |
|---|---|---|---|
| bullet `- version: 1.1.0` | asset gerenciado, constituição viva do repo | `FIELD` | não |
| top-level `version: 1.0.0` | todas as fixtures de teste | `TOP_FIELD` | sim |
| rodapé `**Version**: …` | template oficial do Spec Kit | nenhum | não |

Toda fixture foi escrita a partir do parser, não da saída real da ferramenta — o mesmo padrão que
produziu o defeito de ANSI no preflight (`specs/021-preflight-registry-detection/`). A forma que o
próprio plugin escreve nunca passava pelo `audit` em teste.

## Não faz parte deste defeito

A pendência de produto da sessão consumidora (FASE-001 travada pela resposta negativa do RDO Web ao
contrato v0.1.0, já registrada em `state.json`). Corrigir o parser não a resolve; apenas para de
gritar um falso positivo por cima do bloqueio verdadeiro.
