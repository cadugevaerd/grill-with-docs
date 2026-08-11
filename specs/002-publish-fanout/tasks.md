# Tasks: Publicação fan-out

**Feature**: `002-publish-fanout` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## T-001 — Alvos declarados e camada pura da entrada
- **files**: `tests/publish_to_marketplace.py`
- **depends-on**: none
- **entrega**: tabela `TARGETS`; `parse_release()`; `plan_entry()` puro cobrindo criação, atualização e `UNCHANGED`
- **aceite**: `source` sai como `git-subdir` com `{url, path, ref, sha}` nos dois alvos; campos curados preservados; entrada já correta devolve `UNCHANGED`
- **satisfaz**: FR-002, FR-003, FR-004, FR-005

## T-002 — Reescrita do índice e CLI
- **files**: `tests/publish_to_marketplace.py`
- **depends-on**: T-001
- **entrega**: `apply_entry()` preservando indentação, ordem de chaves e newline final; CLI com preview padrão, saída texto e JSON, exit codes do contrato
- **aceite**: sem `--apply` nada é escrito; entradas vizinhas ficam byte-idênticas; índice ilegível sai `1`; alvo desconhecido sai `2`
- **satisfaz**: FR-003, FR-005, FR-009

## T-003 — Testes
- **files**: `tests/validate_publish_contract.py`
- **depends-on**: T-002
- **entrega**: camada pura exaustiva; aplicação em diretório temporário; fixtures com os dois índices reais
- **aceite**: roda sem rede e sem credencial, nos três sistemas e nas duas versões de Python; entra na suíte pelo glob
- **satisfaz**: SC-001..SC-005

## T-004 — Workflow de publicação
- **files**: `.github/workflows/publish.yml`
- **depends-on**: T-002
- **entrega**: disparo em push na main filtrado por `plugin/**` e `workflow_dispatch`; job que cria a tag no canônico; um job por marketplace, independentes, que clonam, rodam o publicador e empurram só quando houve mudança
- **aceite**: tag imutável — recriar apontando para outro commit reprova; sem `|| true`; segredo referenciado, nunca ecoado
- **satisfaz**: FR-001, FR-006, FR-007, FR-008

## T-005 — Verificação local contra clones reais
- **files**: nenhum; execução
- **depends-on**: T-003, T-004
- **entrega**: publicador rodado contra clones dos dois marketplaces; preview e apply; segunda execução no-op
- **aceite**: entrada criada no Codex, atualizada no Claude de `v2.4.1` para a release corrente, vizinhas intactas, segunda execução sem mudança
- **satisfaz**: SC-001, SC-002, SC-004
