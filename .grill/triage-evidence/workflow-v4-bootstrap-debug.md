# Relatório de debug

## Status
- causa raiz comprovada

## Sintoma reproduzido
- Comando/cenário: em um repositório Git temporário vazio, executar `python3 plugin/skills/grill-with-docs/scripts/ensure_workflow.py --ensure <root>`; depois invocar `python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py migrate-v4 <root> --work-id x`.
- Resultado observado: o bootstrap retorna `status: CREATED`, `version: v2`, e cria `<!-- grill-with-docs-workflow:v2 -->`; a CLI retorna `INVALID-ARGUMENTS`, pois `migrate-v4` não é um subcomando aceito.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| `TEMPLATE = HERE.parents[1] / "assets/WORKFLOW.template.md"` com `VERSION = "v2"` | `plugin/skills/grill-with-docs/scripts/ensure_workflow.py:20-23` | O único materializador do bootstrap novo escreve o template v2. |
| `EXECUTABLE_MARKER_VERSIONS = (V3_MARKER_VERSION, V4_MARKER_VERSION)` | `plugin/skills/grill-with-docs/scripts/ensure_workflow.py:38` | O runtime reconhece v4; o problema não é a capacidade de execução do gate. |
| `migrate_command(... to_version: VERSION ...)` | `plugin/skills/grill-with-docs/scripts/grill_core/workflow_v4.py:304-343` | Já há migração v2/v3 para v4, com preview e CAS. |
| Apenas `migrate` e `migrate-v3` são registrados e despachados | `plugin/skills/grill-with-docs/scripts/grill_workspace.py:3969-3981,4124-4130` | A migração v4 não possui entrada pela CLI pública. |
| `migrate-v3 --rebind-workflow` exige `execution_gate(...).status == "OK"` | `plugin/skills/grill-with-docs/scripts/grill_workspace.py:2355-2376` | Rebind não pode romper o ciclo para um documento v2. |

## Caminho de investigação/Hipóteses eliminadas
1. O gate v4 estar sem wiring foi eliminado: `ensure_workflow.py` declara v4 em `EXECUTABLE_MARKER_VERSIONS`.
2. A migração v4 estar ausente foi eliminada: `workflow_v4.migrate_command` entrega preview, CAS, proteção de edições locais e `REUSED`.
3. `migrate-v3 --rebind-workflow` ser rota alternativa foi eliminada: ele exige que o workflow já passe no gate v4.

## Causa raiz
O bootstrap ainda materializa apenas o template v2 e a migração v4 existente não é exposta por `grill_workspace.py`. Portanto, projetos novos nascem inelegíveis para o Gauntlet e projetos existentes não dispõem de comando público para migrar o documento antes do rebind.

## Cadeia causal
Projeto sem `WORKFLOW.md` → `ensure_workflow --ensure` materializa v2 → `gauntlet-init` exige workflow elegível v4 → ativação bloqueada → `migrate-v3 --rebind-workflow` também exige v4 → não há rota CLI para `workflow_v4.migrate_command` → projeto não alcança `gauntlet-init`/`--run-id`.

## Arquivos envolvidos
- `plugin/skills/grill-with-docs/scripts/ensure_workflow.py`: seleciona o template de bootstrap.
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py`: publica subcomandos e implementa o rebind que pressupõe elegibilidade.
- `plugin/skills/grill-with-docs/scripts/grill_core/workflow_v4.py`: contém a migração pronta, porém inacessível pela CLI principal.
- `plugin/skills/grill-with-docs/assets/WORKFLOW.v4.template.md`: template já disponível para a migration/bootstrap v4.

## Limitações/incertezas
- Nenhuma para o sintoma reproduzido.

Diagnóstico encerrado. Nenhuma correção foi executada.
