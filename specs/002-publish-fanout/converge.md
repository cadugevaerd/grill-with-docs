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

## Terceira rodada: achados do revisor independente

O revisor reproduziu, em ataques próprios, duas corrupções que eu não tinha encontrado. Ambas corrigidas e cobertas.

1. **Âncora textual pegava objeto errado (crítico).** `object_span` fazia `rindex("{")` a partir do match de `"name"`, o que assume que `name` é a primeira chave da entrada. Com qualquer objeto aninhado antes dela — um `compat` que um humano acrescente ao reordenar campos — a âncora caía no objeto aninhado. O `retarget` não achava as três chaves naquele span, o fallback reserializava a entrada inteira e a colava **dentro** do aninhado. O arquivo continuava JSON válido por acidente de balanceamento, com chaves duplicadas; `json.loads`, que é last-wins, resolvia para o **release velho**. A ferramenta reportava `APPLIED / entry UPDATED / version 2.5.0` e o workflow empurraria isso. Falha silenciosa, sem exceção.

   Corrigido substituindo a âncora textual: `entry_spans` percorre o array `plugins` na profundidade do array, faz brace matching de cada objeto e o parseia, identificando a entrada pelo `name` parseado. A ordem das chaves passou a ser irrelevante.

2. **Split-brain com entradas duplicadas.** `plan_entry` decidia pela primeira ocorrência e `locate` escrevia na última. Com duas entradas de mesmo nome, o índice terminava com duas declarações divergentes do mesmo plugin. Agora ambos recusam com `TargetInvalid`: índice ambíguo não é resolvido por escolha silenciosa.

Um terceiro achado do revisor, sobre `retarget` casar chave aninhada, era de uma versão anterior à minha correção de profundidade e não se reproduz no código atual — verificado rodando o cenário exato dele.

Achados menores registrados e não corrigidos: `detect_indent` ignora tabulação, caindo no default de 2 espaços (cosmético; os dois índices reais usam espaços), e a mensagem de colisão de tag não nomeia "faltou bump" como causa provável (DX).

Suíte após esta rodada: **267 testes**, exit `0`. `validate_publish_contract.py` foi de 26 para 30.
