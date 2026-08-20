# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| registro de extensões | `.specify/extensions/.registry` — JSON do spec-kit com `schema_version` e, por slug, `version`, `enabled` e `registered_commands`. Fonte de verdade da detecção. | "lista de extensões", "output do specify", "catálogo" | ADR-0001 |
| catálogo de extensões | `.specify/extension-catalogs.yml` — de **onde** extensões podem ser instaladas e se a fonte é confiável (`install_allowed`). Não diz o que está instalado. | "registro", "lista" | ADR-0001 |
| slug da extensão | Identificador exato da extensão (`git`, `agent-assign`, `bugfix`, `verify-review-ship`). É chave no registro, nunca substring de texto livre. | "nome da extensão", "título" | ADR-0001 |
| detecção de extensão | Responder se uma extensão exigida pelo `WORKFLOW.md` está utilizável. Utilizável = registrada **e** `enabled`. | "checar instalação" | ADR-0001, ADR-0003 |
| falso negativo | Extensão utilizável reportada como ausente. É o defeito de origem: `git`, `agent-assign` e `verify-review-ship`. | "erro do preflight" | SGD-16 |
| falso positivo | Extensão reportada como presente por casamento acidental em texto livre, não pelo slug. Observado em `bugfix`. | "detectou certo" | SGD-16 |
| present | Slug existe no registro e `enabled: true`. | "instalada" | ADR-0003 |
| missing | Não utilizável: ausente do registro, **ou** registrada com `enabled: false`. O `reason` distingue os dois. | "não instalada" | ADR-0003 |
| undetermined | O registro não pôde ser lido — ausente ou `schema_version` desconhecido — então a presença não foi observada. Não é afirmação de ausência. | "missing", "erro" | ADR-0002 |
| remediação | Comando que resolve o item **pelo motivo observado**: `add` para ausente, `enable` para desabilitada. Deixa de ser fixa por dependência. | "install", "comando do manifest" | ADR-0003 |
| bump obrigatório | Incremento SemVer exigido por qualquer alteração em `plugin/**`, replicado nos oito lugares que `tests/validate_distribution.py` fixa. | "versionar", "release" | ADR-0004 |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.
