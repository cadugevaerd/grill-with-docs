# Converge — FASE-003

Executor único, sem colisão de escopo. Tudo abaixo é evidência coletada em 2026-08-12, com `HEAD` em `5591b1b6883e5ceba88fcbc0d112eddee3ebff36`.

## Estado inicial, medido pelo próprio verificador

Antes de qualquer escrita, `--verify` contra clones frescos dos dois destinos:

```
claude  MISMATCH exit=3
  version='2.4.1', esperado '2.5.0'
  source.ref='v2.4.1', esperado 'v2.5.0'
  source.sha='c6a9b070…', esperado '5591b1b6…'
codex   MISMATCH exit=3
  entrada 'grill-with-docs' ausente do índice
```

O drift que a fase existe para eliminar está aí, medido pela ferramenta que vai atestar o fim dele. O ROADMAP registrava `2.4.0`; o observado é `2.4.1`, corrigido em T-006.

## Ciclo completo contra os clones reais

| Destino | `--apply` | Diff | `--verify` depois | Segunda aplicação |
|---|---|---|---|---|
| claude | `UPDATED` | 3 inserções, 3 remoções, um arquivo | `VERIFIED` exit 0 | `UNCHANGED` |
| codex | `CREATED` | 17 inserções, zero remoções | `VERIFIED` exit 0 | `UNCHANGED` |

Nada foi empurrado. As três linhas do claude são exatamente `version`, `source.ref` e `source.sha`; as 17 do codex são a entrada nova inteira, inserida depois do último vizinho.

## Resolução da tag

A lógica do passo de releitura, exercitada contra o canônico real:

```
v2.4.1 -> c6a9b0708f737dd9f13a3ca98c3b5fa2a00c4cbf
v9.9.9 -> nada
```

`v2.4.1` é tag anotada: o objeto de tag é `880827b1…` e o commit é `c6a9b070…`. A resolução entrega o **commit**, não o objeto de tag — comparar contra o objeto de tag reprovaria toda publicação anotada. Tag ausente entrega vazio, o que derruba o passo com erro nomeado.

## Workflow

Passos do job `publish`, na ordem: `Checkout do canônico` → `Set up Python` → `Clonar o marketplace` → `Apontar a entrada para a release` → `Commitar e empurrar somente se mudou` → `Verificar o estado publicado`. Gatilhos: `push` e `workflow_dispatch`. YAML parseia; todo bloco `run` dos dois jobs passa em `bash -n`.

A releitura não herda `working-directory: marketplace` do passo anterior, então roda a partir da raiz do canônico, onde o publicador vive. Clona em `marketplace-verify`, diretório distinto do clone de trabalho.

## Suíte

`tests/validate_publish_contract.py`: 33 → 49 testes, todos verdes. Suíte canônica completa registrada em `verify.md`.

## O que não foi integrado

A execução real. Ela depende do segredo de publicação, que não está instalado no repositório canônico e cuja instalação é ato humano — o workflow tem zero execuções até aqui. Tudo que não depende disso está entregue.
