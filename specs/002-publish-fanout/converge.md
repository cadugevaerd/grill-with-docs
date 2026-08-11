# Converge — integração e evidência executada

Tarefas de `tasks.md` integradas na branch `002-publish-fanout`. Evidência é execução real contra clones dos dois marketplaces publicados, não leitura de código.

## Correção de premissa

A fase começou sobre evidência errada. Eu havia lido `plugins/grill-with-docs/` no checkout local em `~/.claude/plugins/marketplaces/claude-skills`, que está **70 commits à frente do `origin` e não empurrado**, e apresentei aquilo como estado publicado.

O estado publicado é outro: a entrada em `claude-skills` usa `source` do tipo `git-subdir` fixado em `v2.4.1`, sem cópia alguma; `codex-skills` não tem entrada. A implementação foi refeita sobre a evidência corrigida, e spec, plano, contrato e tarefas foram reescritos antes de qualquer código.

## Cenários contra os marketplaces reais

Clones rasos de `cadugevaerd/claude-skills` e `cadugevaerd/codex-skills`, release `2.5.0` / `v2.5.0` / `45f6b98…`.

| Cenário | Resultado | Diff |
|---|---|---|
| claude, entrada existente em `v2.4.1` | `UPDATED`, exit 0 | 3 inserções, 3 remoções |
| codex, entrada ausente | `CREATED`, exit 0 | 17 inserções, nenhuma remoção |
| segunda execução em ambos | `UNCHANGED`, exit 0 | nenhuma mudança adicional |
| índice ausente no alvo | `BLOCKED`, exit 1 | nada escrito |

Verificações estruturais após o apply, nos dois: JSON válido, 16 plugins, entrada com `source.source = git-subdir`, `version` e `ref` corretos, **15 entradas vizinhas byte-idênticas** e chaves de topo preservadas.

## Defeitos encontrados na própria verificação e corrigidos

1. **Reformatação de vizinhas.** A primeira versão reserializava o documento inteiro, normalizando a entrada `quality-security-gate`, que estava compactada à mão. O diff do Claude saía com 13 insertions/5 deletions em vez de 3/3. Corrigido com edição textual cirúrgica; coberto por teste que exige exatamente três linhas alteradas.
2. **Inserção aninhada.** O caminho de criação ancorava no último `}` do arquivo, que é o fecho do objeto `policy` do último plugin, e inseria a entrada nova **dentro** do vizinho, gerando JSON inválido. Corrigido ancorando pelo nome do último plugin com brace matching string-aware; coberto por teste de regressão.

Ambos foram achados executando contra os arquivos reais, não por leitura.

## Suíte

`python3 tests/run_validators.py` → exit `0`, **260 testes**, 1 skip dependente de ambiente. Os 23 novos são de `validate_publish_contract.py`. Baseline antes desta fase era 237.

## Fronteiras confirmadas

- Nada criado ou alterado em `plugin/`.
- `tests/publish_to_marketplace.py` não é coletado pelo glob `validate_*.py`.
- `.github/workflows/ci.yml` intocado; `publish.yml` é arquivo novo.
- O publicador não clona, não cria tag e não empurra: recebe checkout pronto. Toda operação com credencial vive no workflow.
