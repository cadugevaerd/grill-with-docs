# Pedido e escopo único

Owner: Carlos Araújo. Sessão condutora: Codex. Branch: cadugevaerd/feat-new-subagents.
Triagem: tri-ff9665c9fc13427e927e665e5b09f600. Tipo: feature com correções associadas; nenhum item separado.

## Requisitos solicitados
1. Corrigir gauntlet-cleanup: usuário confirmou resíduos de worktrees, branches e sessões de subagentes. Abranger os três recursos, preservando trabalho não integrado.
2. Sempre sugerir Sol para Codex e Opus para Claude no chat principal.
3. Permitir continuar a mesma worktree em outro CLI do ponto onde parou.
4. Fluxo específico de frontend com design para visualizar antes de desenvolver, integrando a skill Impeccable ao workflow.
5. Planejamento, tasks e todo raciocínio sobre COMO devem usar subagentes topo de linha: Astra no Codex e Fable no Claude, effort xhigh.
6. Todas as revisões devem usar subagentes topo de linha, effort high.
7. Corrigir o particionador GWD: incluir arquivos de raiz como .gitignore e build-dist.sh, inclusive escritos com ./, e não confundir expressões como ACTIVE/FREE com arquivos. O defeito pertence ao GWD, não ao site nem ao Terraform. O relato informa que o despacho foi interrompido antes de conceder escopo incorreto.

8. Adicionar i-have-adhd (https://github.com/ayghri/i-have-adhd) como componente obrigatório da stack, instalado em Codex e Claude Code, ativo por padrão e com funcionamento comprovado em ambos; instalação sozinha não satisfaz o aceite.

## Evidências e limites
- Relatório: ../../triage/new-subagents-debug.md; triagem selada em ../../triage/tri-ff9665c9fc13427e927e665e5b09f600.json.
- Análise arquitetural somente leitura delegada ao subagente mapear_decisoes com gpt-6-astra/xhigh.
- O identificador Claude `fable` foi confirmado pelo usuário em R-0005. Disponibilidade e suporte efetivo a high/xhigh permanecem EVIDENCE GAP até verificação no harness; confirmação do nome não é prova de execução.
- Pré-flight: backlog SGD BOUND, dependências presentes; nenhum skip ou instalação.
- Esta sessão apenas prepara decisões. Não implementa produto, não executa specify/plan, não faz commit/merge.

## Decisões da entrevista
- R-0001: limpeza abrange worktrees, branches e sessões.
- R-0002: frontend terá subfase de plan com prévia visual e aprovação antes de tasks; nenhuma macroetapa nova.
- R-0003: usuário confirmou retomada entre CLIs pelo último checkpoint persistido, repetindo somente o trecho interrompido; transferência de workers ativos não integra esta decisão.
- R-0004: especialistas realizam todo o raciocínio de planejamento e revisão dentro da skill canônica invocada pelo líder; líder mantém coordenação, registro das evidências e atestação.
- R-0005: modelo dos especialistas Claude identificado pelo usuário como `fable`; Codex usa `gpt-6-astra`. Planejamento xhigh e revisões high conforme pedido original; modelo e esforço efetivos devem ser verificados, sem substituição silenciosa.
- R-0006: em etapas mistas, separar elaboração e revisão: autor xhigh e revisor distinto high, ambos especialistas topo de linha. A regra de revisão se aplica a todos os pontos de julgamento, não apenas à etapa final review.
- R-0007: adotar lista explícita de arquivos por tarefa no tasks.md, incluindo arquivos novos e da raiz, como autoridade do grant; referências na prosa não concedem escrita. Tarefas antigas precisam de adaptação ao novo contrato.
- R-0008: limpeza automática ao concluir etapa/wave e antes da troca de CLI; encerrar sessões após persistir resultados e remover worktrees/branches apenas com identidade comprovada, árvore limpa, trabalho integrado e evidência preservada. Recursos pendentes permanecem visíveis e preservados.

## Ampliação de escopo — 2026-09-13

- Pedido literal: "obrigatorio: instalar em ambos o ambiente e tornar o default a biblioteca - https://github.com/ayghri/i-have-adhd precisa garantir que está funcionando."
- O componente é um plugin/skill de estilo de resposta, não dependência Python do core. Ambientes interpretados a partir deste work item: Codex e Claude Code.
- Instalação 0.3.0 realizada pelas CLIs dos dois harnesses; ambos listam instalado e habilitado. A ativação automática e a prova comportamental ainda não foram concluídas.
- R-0010 / DQ-0009 resolvida: usuário confirmou "no projeto GWD e após atualizar a skill GWD esse padrão será usado pelos CLIs em questão." Default restrito ao projeto/fluxo GWD, aplicado pela skill GWD atualizada em Codex e Claude Code; nenhuma alteração do padrão global das sessões fora do GWD.
- A spec já atestada cobre os sete requisitos originais. A ampliação exige invocação de specify com cadeia sucessora antes de fechar plan; o receipt anterior será preservado.
