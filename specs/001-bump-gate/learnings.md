# Ship fase A — aprendizados aprovados

Somente o que foi verificado nesta fase.

## Detecção de rename esconde remoção de escopo

`git diff --name-only A...B` reporta apenas o destino quando detecta rename. Qualquer verificação que decida "este conjunto de caminhos foi tocado?" a partir dessa saída tem um ponto cego: mover algo para **fora** do conjunto não aparece como mudança nele. Vale para este gate e valeria para qualquer gate futuro baseado em prefixo de caminho — por exemplo o de publicação da FASE-002. Use `--no-renames` quando a pergunta é sobre pertencimento a um escopo, não sobre a identidade do arquivo.

## O gate de review pagou por si nesta fase

O bypass não foi encontrado por teste unitário nem por leitura: apareceu numa passada adversarial contra clone git real, perguntando "como eu burlaria isso?". Testes de unidade sobre a camada pura estavam todos verdes e continuariam verdes com o defeito presente, porque o defeito vivia na fronteira com o git.

## Nome de arquivo como mecanismo de escopo

`run_validators.py` coleta por glob `validate_*.py`. Nomear o verificador fora do glob foi mais barato e mais honesto que adicionar uma condição de no-op para quando não há pull request — o no-op teria escondido ausência de verificação atrás de sucesso, que é justamente o que a cláusula fail-closed proíbe.

## Limite conhecido, não resolvido

Duas pull requests concorrentes que subam para a mesma versão passam isoladamente e conflitam no merge. Aceito para esta fase e registrado em `PLAN-CONTEXT.md#FASE-001`.
