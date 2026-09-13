# Stack obrigatória — i-have-adhd

Data: 2026-09-13. Requisito 8 de REQUEST.md; work item e FASE-001 existentes, sem criação de item separado.

## Pedido e aceite

O usuário exige instalar https://github.com/ayghri/i-have-adhd nos dois ambientes deste trabalho (Codex e Claude Code), tornar padrão e garantir funcionamento. O componente é plugin/skill de apresentação, não biblioteca Python adicionada ao core.

O aceite exige evidências separadas de instalação/versão, habilitação, carregamento automático no alcance escolhido e comportamento observado em sessão nova de cada harness. Não basta listar arquivos nem executar um hook isoladamente. Configuração existente deve ser preservada; a política de implementação do Ponytail permanece distinta da apresentação.

DQ-0009 resolvida em R-0010. Resposta literal: "no projeto GWD e após atualizar a skill GWD esse padrão será usado pelos CLIs em questão." O default vale no projeto/fluxo GWD, aplicado pela skill GWD atualizada em Codex e Claude Code, sem invocação manual do i-have-adhd e sem mudar sessões externas ao GWD. A integração e a prova de sessões novas pertencem à entrega deste work item; não estão concluídas nesta entrevista.

## Fontes oficiais inspecionadas

- [README](https://github.com/ayghri/i-have-adhd/blob/main/README.md): objetivo e comportamento.
- [Guia de agentes](https://github.com/ayghri/i-have-adhd/blob/main/AGENTS.md): mapa de entradas e verificações.
- [Instalação](https://github.com/ayghri/i-have-adhd/blob/main/INSTALL.md): CLIs dos harnesses e mecanismos de default.
- [Skill canônica](https://github.com/ayghri/i-have-adhd/blob/main/skills/i-have-adhd/SKILL.md): persistência e dez regras; disable-model-invocation true.
- [Manifest Claude](https://github.com/ayghri/i-have-adhd/blob/main/.claude-plugin/plugin.json) e [manifest Codex](https://github.com/ayghri/i-have-adhd/blob/main/.codex-plugin/plugin.json): versão 0.3.0, licença MIT.
- [Hooks](https://github.com/ayghri/i-have-adhd/blob/main/hooks/hooks.json) e [always-on](https://github.com/ayghri/i-have-adhd/blob/main/hooks/always-on.mjs): SessionStart, matcher startup/resume/clear/compact, uso de node e flag no diretório de configuração Claude. Falha silenciosa: exit 0 sem saída não prova ativação.

A documentação Claude descreve flag .i-have-adhd-always no diretório de configuração; Codex descreve instruções persistentes via AGENTS.md. Mecanismos não são intercambiáveis por suposição. A presença do hook na cópia Codex não prova que o harness o disparou.

## Instalação executada e observada

```text
codex plugin marketplace add ayghri/i-have-adhd --ref main --json
codex plugin add i-have-adhd@i-have-adhd --json
claude plugin marketplace add ayghri/i-have-adhd
claude plugin install i-have-adhd@i-have-adhd --scope user --json
```

Todos concluíram com exit 0. Codex reportou versão 0.3.0 e installPath no cache do plugin; Claude reportou outcome ok. As listagens posteriores confirmaram instalado/habilitado nos dois ambientes.

- Codex: `/home/carlosaraujo/.codex/plugins/cache/i-have-adhd/i-have-adhd/0.3.0`.
- Claude: `/home/carlosaraujo/.claude/plugins/cache/i-have-adhd/i-have-adhd/0.3.0`.
- SHA-256 de SKILL.md nos dois: `3170b16ace00aecb0dd7feb54c0b5aa642e7502acda06ecd24fd89a11c7127e9`.
- Node disponível: v22.22.2.

Instalação foi delegada às CLIs oficiais, autorizada pelo pedido explícito; o core GWD não foi modificado e não baixou bytes.

## Verificação já realizada

Para cada cópia instalada, executar `node hooks/always-on.mjs` com CLAUDE_CONFIG_DIR temporário:

1. Sem flag: exit 0 e stdout vazio, esperado.
2. Com flag temporária: exit 0, marcador ADHD MODE ACTIVE, regras completas e YAML removido, esperado.

Resultado: PASS nas quatro verificações; os diretórios temporários foram removidos. Evidência estruturada em `i-have-adhd-install-check.json`. Nenhuma flag de produção foi criada por esse teste. Não é teste de carregamento pelo harness nem avaliação de resposta real.

## Integração restante

- Implementar o alcance selado: a skill GWD atualizada aplica o padrão no projeto/fluxo GWD. Comprovar carregamento/comportamento em sessões novas dos dois ambientes, sem invocar i-have-adhd manualmente; verificar que sessões fora do GWD mantêm o padrão anterior. Não criar flag global ou alterar AGENTS.md global para cumprir esse requisito.
- Incorporar a dependência obrigatória, versão mínima observada e diagnóstico de ativação à entrega GWD, sem confundir instalado com funcional.
- Atualizar handoff, revisão documental e auditoria; invocar specify para cadeia sucessora e atualizar plan antes de tarefas. Preservar receipts já aceitos e todos os sete requisitos anteriores.

## Tentativa de sessão nova — evidência negativa

Ao iniciar o revisor documental em Codex, o harness parou antes de receber a tarefa: `Agent startup blocked: codex-hooks-review-prompt`. A interface mostrou `Hooks need review` com um hook novo. Navegar para `Review hooks` pelo Orca retornou `agent_prompt_blocked`, sem aceitar entrada. Não foi concedida confiança nem executado bypass. Registro: `i-have-adhd-review-start.json`. Esse resultado não comprova ativação; expõe um pré-requisito real de inicialização que a entrega precisa diagnosticar. Claude não teve prova de sessão nova nesta entrevista.

## Retomada após aprovação humana do hook

Usuário confirmou: "aprovei o hook em nova interface". Retry da mesma tarefa em nova sessão Codex alcançou `input_accepted` e `turn_started`, requested/effective `gpt-6-astra/high`; a inicialização não foi bloqueada pelo prompt de confiança. Registro: `i-have-adhd-review-retry.json`. Isso comprova que o revisor iniciou, não o default i-have-adhd pela skill GWD ainda não implementada.

Revisor da mesma tarefa concluiu `GO DOCUMENTAL`, sem findings bloqueantes e sem editar arquivos; ver REVIEW-I-HAVE-ADHD.md. A ampliação está pronta para incorporação canônica no ciclo externo; a implementação e a prova funcional permanecem pendentes.
