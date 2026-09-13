# FASE-001 — Orquestração, continuidade e escopo dos agentes

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: Work item único, Limpeza, Retomada entre CLIs, Design frontend, Grant, Especialista, Estilo padrão
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005
- BLs: none

## WHAT

- delivery-units: DU-001
- development-type: platform-devops

Evoluir o grill-with-docs para atender aos oito requisitos abaixo em uma única entrega. Cada resultado é critério de aceite para o ciclo externo.

1. **Limpeza dos recursos dos agentes.** Limpar automaticamente sessões, worktrees e branches elegíveis ao fechar cada etapa ou wave e antes da troca de CLI. Encerrar sessões depois que o líder persistir resultado ou diagnóstico, incluindo especialistas somente leitura. Remover worktrees e branches somente com identidade comprovada, trabalho integrado, árvore limpa e nenhuma evidência exclusiva a preservar. Workers que falharam conservam trabalho e evidências pendentes. Recursos preservados aparecem no checkpoint com o motivo. A limpeza funciona após conclusão da run e entre waves elegíveis, sem contornar proteções contra perda.

2. **Orientação do chat principal.** Sempre sugerir Sol no Codex e Opus no Claude para a sessão principal que coordena o trabalho, inclusive ao iniciar e retomar. Essa recomendação é distinta da política dos especialistas e não implica trocar silenciosamente o modelo ativo.

3. **Continuidade entre CLIs.** Permitir continuar o mesmo trabalho, na mesma worktree, em outro CLI pelo último checkpoint persistido. Preservar resultados já aceitos e repetir somente o trecho interrompido, evitando execução concorrente e duplicação de efeitos. Não transferir workers ativos nem pressupor transferência da memória privada da sessão anterior. A troca exige checkpoint coerente e ausência de trabalho ativo concorrente.

4. **Design frontend antes das tarefas.** Para trabalho frontend, integrar Impeccable a uma subfase de plan que produza prévia visual revisável e obtenha aprovação antes de tasks. Brief textual isolado não satisfaz a prévia visual. Manter a sequência existente de onze macroetapas.

5. **Planejamento por especialistas.** Todo raciocínio sobre COMO, incluindo planejamento, tasks e design frontend, é realizado por especialistas topo de linha: gpt-6-astra no Codex e fable no Claude, com esforço xhigh. O líder invoca a skill canônica e conserva coordenação, registro dos resultados e atestação; não substitui o julgamento especializado.

6. **Revisão independente.** Toda revisão que exige julgamento — de requisitos, planos, tarefas, design, código ou segurança — usa especialista topo de linha com esforço high. Em atividades mistas, separar elaboração e revisão entre autor xhigh e revisor distinto high. A política abrange os pontos de revisão de todo o fluxo, não apenas review; validadores determinísticos continuam sendo verificações executáveis.

7. **Escopo de escrita inequívoco.** Cada tarefa declara explicitamente os arquivos que pode alterar. Essa lista é a única autoridade para o grant, incluindo arquivos novos e da raiz, como .gitignore e build-dist.sh, inclusive quando apresentados com ./. Referências na descrição, como ACTIVE/FREE, não concedem escrita. Declaração ausente ou inválida produz diagnóstico, sem inferir permissões da prosa. Tarefas antigas precisam de adaptação explícita ao novo contrato; DAGs já selados não são reescritos silenciosamente.

8. **Estilo de resposta obrigatório e funcional.** Integrar i-have-adhd (https://github.com/ayghri/i-have-adhd) à stack obrigatória em Codex e Claude Code, instalado e ativo por padrão, sem invocação manual a cada sessão. Exigir evidência distinta de instalação/versão, habilitação, carregamento automático e comportamento observado em sessão nova nos dois ambientes. Instalação sozinha, exit 0 de hook ou configuração declarada não comprovam funcionamento. Preservar configurações existentes e a política de implementação do Ponytail. O padrão vale no projeto/fluxo GWD e passa a ser aplicado pela skill GWD atualizada em ambos os CLIs. Sessões fora do GWD conservam seu padrão anterior.

Antes de despachar especialistas, verificar modelo e esforço efetivos. Ausência de capacidade ou divergência bloqueia com diagnóstico, sem substituição silenciosa. A confirmação do nome fable define a seleção, não comprova disponibilidade ou execução. Encerramentos de sessões também precisam de evidência do resultado; uma tentativa não pode ser apresentada como limpeza concluída.

Esta fase cobre plugin, core CLI, contratos, integração das skills, documentação e verificações correspondentes. Não inclui correções no site ou Terraform, transferência de workers ativos, nova macroetapa de design ou liberação indiscriminada de modelos frontier para workers de implementação. Aplicam-se os gates constitucionais de versão e publicação.

## WHY

As reproduções isoladas comprovaram dois defeitos do grill-with-docs: worktrees permanecem após convergência e a inferência de arquivos pela prosa produz grants incompletos ou espúrios. O usuário também relatou resíduos de branches e sessões; a operação atual de cleanup não os encerra. Corrigir esses caminhos evita resíduos e permissões que não correspondem ao trabalho declarado.

A continuidade por checkpoint permite trocar de CLI sem perder resultados aceitos. Especialistas com modelo e esforço explícitos tornam planejamento e revisão previsíveis; a prévia visual aprovada permite avaliar o resultado frontend antes de produzir suas tarefas.

A entrega preserva identidade, ownership, evidência e sequência canônica. Os registros fornecem rastreabilidade estrutural auditável; não constituem prova criptográfica de que um modelo ou uma skill executou o trabalho.

A ampliação de 2026-09-13 inclui estilo de resposta padrão com funcionamento verificável; instalação e configuração são condições distintas.

Este handoff prepara o ciclo externo e permanece sujeito a PLAN_ONLY_STOP. Não autoriza execução ou publicação nesta sessão.
