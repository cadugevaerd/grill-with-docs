# Relatório de debug

## Status
- causa raiz comprovada

## Sintoma reproduzido
- Comando/cenário: `python3 plugin/skills/grill-with-docs/scripts/grill_status.py /home/carlosaraujo/Documentos/Projetos/grill-with-docs --format markdown`, combinado com o limite histórico de `timeout=5` do wrapper público.
- Resultado observado: a projeção real terminou em 10,56 s; uma subprocess equivalente com limite de 5 s gerou `TimeoutExpired`, enquanto o limite de 30 s terminou normalmente em 9,03 s.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| O commit `070bb29d15ea25207d46266405aaa40534a45d91` contém `timeout=5` nas linhas históricas 3769 e 3790 | `git show HEAD:plugin/skills/grill-with-docs/scripts/grill_workspace.py` | O wrapper público encerrava a projeção após cinco segundos nos formatos JSON e Markdown. |
| A projeção real terminou em 10,56 s e exit 2 com tabela válida | `/usr/bin/time ... grill_status.py ... --format markdown` | O cálculo é finito, mas excede o limite histórico de cinco segundos neste repositório. |
| `timeout=5` gerou `TimeoutExpired` após 5,00 s; `timeout=30` concluiu após 9,03 s | experimento isolado com `subprocess.run` | O limite, e não um travamento permanente, determina o falso `STATUS-TIMEOUT`. |
| O worktree já continha mudanças em `grill_status.py`, `grill_workspace.py` e `validate_status_contract.py` | `git status --short` antes da investigação | As correções observadas são preexistentes e não foram produzidas pela etapa diagnóstica. |

## Caminho de investigação/Hipóteses eliminadas
1. Inspeção do commit atual → confirmou `timeout=5` nos dois entry points públicos.
2. Execução direta da projeção → produziu saída válida em 10,56 s, eliminando falha funcional ou travamento permanente como explicação do sintoma.
3. Contrafactual isolado com a mesma duração → cinco segundos falharam e trinta segundos concluíram, confirmando causalidade do limite.

## Causa raiz
O wrapper público em `grill_workspace.py` impõe cinco segundos a uma projeção que, no workspace real com vários work items e worktrees, exige aproximadamente dez segundos. `subprocess.TimeoutExpired` é convertido diretamente em `STATUS-TIMEOUT`, produzindo um bloqueio falso apesar de `grill_status.py` conseguir concluir e gerar uma tabela válida.

## Cadeia causal
Workspace com múltiplos work items/worktrees → projeção executa probes Git e leva mais de cinco segundos → `subprocess.run(..., timeout=5)` interrompe o processo → o wrapper converte a exceção em `STATUS-TIMEOUT`.

## Arquivos envolvidos
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py`: define o timeout do entry point público e converte `TimeoutExpired` em `STATUS-TIMEOUT`.
- `plugin/skills/grill-with-docs/scripts/grill_status.py`: calcula a projeção e concentra o custo dos probes Git.
- `tests/validate_status_contract.py`: contrato de regressão para o escopo dos probes por worktree.

## Limitações/incertezas
- nenhuma para o sintoma reproduzido

Diagnóstico encerrado. Nenhuma correção foi executada.
