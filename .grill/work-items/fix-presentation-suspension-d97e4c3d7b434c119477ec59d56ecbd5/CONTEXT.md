# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| apresentação local | Aplicação de `i-have-adhd@i-have-adhd` como referência de apresentação dentro do fluxo GWD, projetada por `project_leader_presentation` | modo, estilo global | SKILL.md "Bootstrap de apresentação obrigatório"; `agent_runtime.py:1121-1128` |
| suspensão | Estado `application=suspended_by_user` produzido pela frase `stop adhd mode` em mensagem de usuário da própria sessão; mantém `work_ready=true` e `use_ready=false` sem reinjetar o corpo | pausa, desligar skill | ADR-0001 |
| reativação | Frase `start adhd mode` em mensagem de usuário posterior à suspensão; volta a `application=active` e exige nova leitura integral | religar, retomar | ADR-0002 |
| fonte não-agente da sessão | Mensagem `role=user` do transcript nativo da própria sessão; exclui `assistant`, resumo de compactação e mensagens sintéticas | fonte humana, autorrelato | ADR-0001; laudo Q3 |
| bloco de compactação | Marca normalizada `compaction` que o adapter produz a partir de `compact_boundary` (Claude) e `compacted` (Codex); leituras anteriores a ela não contam como carga atual | boundary, resumo | `agent_runtime.py:637`, `:682`; laudo Q2 |
