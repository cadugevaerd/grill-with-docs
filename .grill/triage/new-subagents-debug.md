# Relatório de debug

## Status
- causa raiz comprovada

## Sintoma reproduzido
- Baseline: branch cadugevaerd/feat-new-subagents, commit 6ad0dc2; árvore inicialmente limpa; Python 3.12.3.
- Cenário cleanup: fixture temporária de tests/validate_gauntlet_converge_contract.py, GauntletConvergeContractHarness, bind_execution_branch, converged_wave_fixture, converge e gauntlet-cleanup para T1.
- Resultado: WAVE-CONVERGED, run COMPLETE; cleanup exit 2 RUN-NOT-ELIGIBLE.
- Cenário duas waves: two_wave_fixture, converge wave-0001; run ADMITTED; cleanup exit 2 PRESERVED.
- Cenário partition: extract_files aplicado a .gitignore, build-dist.sh, ./.gitignore, ./build-dist.sh e ACTIVE/FREE.
- Resultado: quatro tuplas vazias; ACTIVE/FREE retorna ('ACTIVE/FREE',).

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| COMPLETE recusado em cleanup | grill_core/gauntlet_runs.py:1158-1173,1946 | cleanup reutiliza admissão de preparação que proíbe run concluída |
| clean=true, converged=true, cleanup_eligible=false após convergir | reprodução com duas waves e gauntlet_runs.py:1035,1962,2115 | elegibilidade nunca é habilitada pelo fluxo observado |
| cleanup chama git worktree remove, sem remoção de branch ou sessão | gauntlet_runs.py:1941-1996 | esses recursos não fazem parte da operação implementada |
| extract_files exige barra; validador rejeita prefixo ponto | grill_core/partition.py:98-128 | arquivos na raiz não geram grants, inclusive com ./ |
| ACTIVE/FREE aceito | chamada direta extract_files; partition.py:98-128 | token de prosa sintaticamente seguro é tratado como arquivo |

## Caminho de investigação/Hipóteses eliminadas
1. Reproduções isoladas usam helpers existentes, Git temporário e nenhuma rede; não removeram recursos reais.
2. Worktree suja não explica PRESERVED: clean=true após terminal e convergência bem-sucedida.
3. Falta de convergência não explica: WAVE-CONVERGED e converged=true registrados.
4. Acrescentar ./ não resolve arquivo de raiz: reprodução direta retorna vazio.
5. Defeito do partition reproduzido sem site ou Terraform.

## Causa raiz
A limpeza aplica a mesma admissão de preparação, que recusa COMPLETE; antes de COMPLETE também exige cleanup_eligible=true, mas a convergência não promove essa flag. A operação implementada só remove a worktree, não a branch nem a sessão do harness. O partition infere arquivos de tokens com barra, sem distinguir prosa de declaração de escopo, enquanto exclui nomes de raiz e rejeita ./ pela validação de caminho.

## Cadeia causal
Worker termina e converge → run COMPLETE ou elegibilidade falsa → cleanup bloqueia/preserva → worktree permanece. Branches e sessões não possuem remoção nessa operação. Tarefa contém arquivo de raiz e expressão com barra → heurística descarta o primeiro e aceita a segunda → grant incompleto e espúrio.

## Arquivos envolvidos
- plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py: admissão, convergência e limpeza.
- plugin/skills/grill-with-docs/scripts/grill_workspace.py:2723-2745: comando cleanup.
- plugin/skills/grill-with-docs/scripts/grill_core/partition.py:98-128: extração.
- tests/validate_gauntlet_converge_contract.py: fixtures reutilizadas.

## Limitações/incertezas
- Usuário confirmou resíduos de worktrees, branches e sessões. Não houve inspeção ou encerramento de sessões reais; ausência de integração no cleanup é fato local, o mecanismo de encerramento por harness permanece decisão aberta.
- Reproduções comprovam os caminhos acima; não afirmam causa única de todo resíduo histórico.
- Os demais cinco pontos são requisitos de evolução, não bugs diagnosticados.

Diagnóstico encerrado. Nenhuma correção foi executada.
