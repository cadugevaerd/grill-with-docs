# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| observer de instalação | Parte do core que transforma a listagem nativa de plugins do runtime no eixo `installation` da apresentação (`present`, `undetermined`) | detector, scanner | agent_runtime.py:490-516 |
| listagem nativa | Saída de `<runtime> plugin list --json` executada pela própria sessão, com o comando literal exigido | inventário, catálogo | REQUEST.md |
| layout do cache Codex | Diretório `<CODEX_HOME>/plugins/cache/<marketplaceName>/<name>/<version>/` onde o Codex materializa um plugin instalado | pasta do plugin | ADR-0001 |
