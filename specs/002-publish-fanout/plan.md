# Implementation Plan: Publicação fan-out nos marketplaces

**Branch**: `002-publish-fanout` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

## Summary

Publicar é criar a tag `vX.Y.Z` no repositório canônico e apontar a entrada de cada marketplace para ela. Um publicador stdlib recebe um clone do marketplace e reescreve apenas `version`, `source.ref` e `source.sha` da entrada, criando-a quando ausente e preservando todo o resto. Um workflow cria a tag e chama o publicador uma vez por marketplace, em jobs independentes.

Nenhum conteúdo é copiado para os agregadores: o `source` é do tipo `git-subdir`, apontando para `plugin/` no canônico, fixado por tag e SHA.

## Technical Context

**Language/Version**: Python 3.10+, stdlib apenas

**Primary Dependencies**: `git` para clone/commit/push, já exigido pelo repositório

**Storage**: N/A

**Testing**: `unittest`, coletado por `tests/run_validators.py`; git real em diretório temporário, como já faz `validate_bump_gate_contract.py`

**Target Platform**: GitHub Actions, ubuntu

**Project Type**: ferramenta de CI, fora do bundle distribuído

**Constraints**: sem rede nos testes; a decisão de o que publicar precisa ser testável sem credencial e sem os repositórios reais

## Constitution Check

Constituição `789b55f4`, 8 cláusulas.

| Cláusula | Avaliação |
|---|---|
| Evidência antes de afirmação | PASS — o schema de cada marketplace foi lido dos repositórios reais, não presumido. |
| Work item isolado e ownership | PASS — artefatos no work item; código em branch dedicada. |
| Feature/fix plan-only | PASS — restringe a sessão grill, encerrada; este é o ciclo externo. |
| Sequência obrigatória | PARCIAL — os 11 passos são percorridos, mas a matriz de checkpoint do grill está esgotada pela FASE-001 e recusa novas transições. Defeito registrado como `SGD-6`; a sequência é seguida e evidenciada em `specs/002-publish-fanout/`. |
| Verify/review antes de ship | PASS. |
| Fail-closed sem waiver | PASS — destino indeterminado, schema desconhecido ou índice ilegível reprovam; FR-009. |
| Rastreabilidade | PASS — spec, plano e tarefas citam FASE-002 e os ADRs. |
| Governance | PASS — Constituição lida, não alterada. |

O `PARCIAL` é registrado, não dispensado: nenhum ADR concede waiver, e o defeito está aberto no backlog externo.

## Project Structure

```text
specs/002-publish-fanout/
├── plan.md, spec.md, research.md, data-model.md, quickstart.md
├── contracts/cli.md
└── checklists/

tests/
├── publish_to_marketplace.py               # NOVO — reescreve a entrada de índice; fora do glob validate_*
└── validate_publish_contract.py            # NOVO — testes, entram na suíte pelo glob

.github/workflows/
└── publish.yml                             # NOVO — um job por marketplace
```

**Structure Decision**: mesma fronteira da FASE-001. O publicador fica em `tests/`, fora de `plugin/`, com nome fora do glob `validate_*.py` porque precisa de um clone de destino que a matriz de validadores não tem. A lógica de decisão é pura e testável sem rede.

O publicador **não clona nem empurra**. Recebe um checkout pronto e deixa o índice reescrito. Clonar, criar tag e empurrar é do workflow, que é quem tem credencial — isso mantém a ferramenta inteiramente testável offline.

## Camadas

1. **Pura**: dado o índice de um marketplace e a release a publicar, decidir a entrada resultante e se houve mudança.
2. **Sistema de arquivos**: reescrever o índice preservando formatação.
3. **Git**: tag no canônico, commit e push no agregador. Só esta camada precisa de credencial, e ela vive no workflow, não no publicador.

Os testes exercitam 1 e 2 exaustivamente, sem rede e sem credencial.

## Alvos declarados

Tabela fixa no código, não descoberta em runtime, atendendo SC-005 e FR-009:

| id | repositório | índice | entrada quando ausente |
|---|---|---|---|
| `claude` | `cadugevaerd/claude-skills` | `.claude-plugin/marketplace.json` | já existe, em `git-subdir` |
| `codex` | `cadugevaerd/codex-skills` | `.agents/plugins/marketplace.json` | criar, com `policy` e `category` do manifesto Codex canônico |

Os dois usam `source` do tipo `git-subdir` com `{url, path, ref, sha}`. Suporte no Codex confirmado pelas variantes declaradas no binário `codex-cli` 0.139.0.
