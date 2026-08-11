# Tasks: Gate de bump de versão

**Feature**: `001-bump-gate` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Ordem topológica. `[P]` marca tarefas paralelizáveis por não compartilharem arquivo.

## T-001 — Lógica pura de decisão
- **files**: `tests/check_version_bump.py`
- **depends-on**: none
- **entrega**: `parse_version`, `touches_plugin` e `decide` conforme `contracts/cli.md`, sem git e sem I/O
- **aceite**: `decide` cobre os cinco códigos de `data-model.md#Verdict`; `parse_version` levanta `ValueError` em entrada inválida
- **satisfaz**: FR-001, FR-002, FR-003, FR-005

## T-002 — Camada de git e CLI
- **files**: `tests/check_version_bump.py`
- **depends-on**: T-001
- **entrega**: leitura da versão em duas revisões via `git show`, diff de nomes com três pontos, parsing de argumentos, saída texto e JSON, exit codes
- **aceite**: exit `0`/`1`/`2` conforme o contrato; `--json` emite exatamente uma linha; a mensagem de texto nomeia as duas versões e a exigência
- **satisfaz**: FR-001, FR-002, FR-004, FR-005

## T-003 — Testes da lógica pura
- **files**: `tests/validate_bump_gate_contract.py`
- **depends-on**: T-001
- **entrega**: casos para os quatro cenários do handoff, mais versão ausente, malformada, remoção de arquivo em `plugin/`, mudança só em `tests/**` e o caso em que a única mudança em `plugin/` é a própria versão
- **aceite**: roda sem git e sem contexto de pull request; entra na suíte pelo glob `validate_*.py`
- **satisfaz**: SC-001, e a verificação executada dos itens de `checklists/acceptance.md`

## T-004 — [P] Job de CI
- **files**: `.github/workflows/ci.yml`
- **depends-on**: T-002
- **entrega**: job `bump-gate` disparado apenas em `pull_request`, com `fetch-depth: 0`, executando o verificador contra a base da pull request
- **aceite**: a matriz de portabilidade existente permanece byte a byte inalterada; o job novo não roda em `push`
- **satisfaz**: FR-007

## T-005 — Verificação de ponta a ponta
- **files**: nenhum; execução
- **depends-on**: T-002, T-003, T-004
- **entrega**: os quatro cenários exercitados contra o repositório real conforme `quickstart.md`, e a suíte completa verde
- **aceite**: `tests/run_validators.py` sai com `0`; cada cenário produz o código e o exit esperados; `tests/check_version_bump.py` confirmadamente ausente da coleta de validadores
- **satisfaz**: SC-001, SC-002, SC-004
