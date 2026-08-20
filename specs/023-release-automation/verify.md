# Verify: release automática por versão publicada

## Gates executáveis

| Gate | Comando | Resultado |
|---|---|---|
| Contrato de workflow | `python3 tests/validate_bump_gate_contract.py` | 50 testes, OK (45 antes) |
| Suíte completa | `python3 tests/run_validators.py` | exit 0, 1 skip de ambiente |
| Bump | `python3 tests/check_version_bump.py --base origin/main` | `PASS NO-PLUGIN-CHANGE` |

## Prova de que o teste testa a mudança

Com `publish.yml` revertido (`git stash push` só desse arquivo):

```
Ran 50 tests in 0.268s
FAILED (errors=4)
```

Quatro dos cinco testes novos dependem do passo. O quinto,
`test_the_publish_workflow_has_valid_shell`, passa nos dois lados de propósito: é guarda permanente
contra shell quebrado no `publish.yml`, não detector desta mudança. Restaurado o passo, 50/50 OK.

## Cobertura por requisito

| FR | Teste |
|---|---|
| FR-001, FR-002, FR-008 | `test_publish_creates_the_release_after_the_tag_that_anchors_it` |
| FR-003, FR-005, FR-006 | `test_an_existing_release_is_success_not_conflict` |
| FR-004 | `test_a_release_anchored_elsewhere_fails_the_publication` |
| FR-007 | `test_the_release_step_takes_no_new_secret_and_no_event_payload` |

## Higiene de diff

Um passo em `publish.yml`, cinco testes, os documentos de `specs/023-release-automation/`. Nenhum
arquivo de `plugin/**` tocado — daí o `NO-PLUGIN-CHANGE`. Nenhuma dependência nova, nenhum segredo
novo, nenhuma action de terceiro adicionada.

## Ressalva declarada

O comportamento real do passo só é observável na primeira publicação depois do merge: o contrato
verifica a estrutura e o shell do workflow, não executa a API do GitHub. É a mesma fronteira dos
gates que já existiam para tag e marketplace — o repositório não simula o GitHub em teste. A primeira
versão publicada depois deste merge é a verificação de campo.

## Veredito

PASS.
