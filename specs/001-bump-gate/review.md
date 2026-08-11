## Review Report

Verdict: APPROVE
Source fingerprint: tree 2e98159744c686a8e7bc81b0d442000845f5c131f37740491773da8c5c9cdb51 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 240d4f9b930d8c13fd6d55061462b3fc3e69298ee99ed59f6de249fed049e270

Confere com o fingerprint de Converge e Verify após a reconvergência.

### Test Quality

Os testes exercitam comportamento, não a implementação. `validate_bump_gate_contract.py` cobre os quatro cenários do handoff, as bordas, e agora o argv real da camada de git. `test_the_pure_layer_never_shells_out` substitui `subprocess.run` por uma função que levanta, provando que a decisão é pura — é o tipo de teste que falha quando alguém acopla git à lógica.

Lacuna aceita: não há teste que execute o binário `git` de verdade. Isso é deliberado — a matriz de CI cobre três sistemas e duas versões de Python, e um teste dependente de repositório seria frágil ali. A cobertura do caminho real veio da execução manual documentada em `converge.md`, contra clone git verdadeiro.

### Runtime Correctness

Um achado de severidade alta, reproduzido e corrigido durante este gate:

**Bypass por detecção de rename.** `git diff --name-only base...head` reporta somente o caminho de destino quando detecta rename. Mover um arquivo para fora de `plugin/` remove conteúdo do bundle publicado, mas a saída não continha nenhum caminho sob `plugin/`, produzindo `NO-PLUGIN-CHANGE` e exit `0`. Reproduzido em clone real: `git mv plugin/skills/grill-with-docs/references/upstream-attribution.md docs-attribution.md` passava no gate sem bump.

Correção em `tests/check_version_bump.py`, `changed_paths`: `--no-renames`. Com ele o par origem/destino aparece, o caminho sob `plugin/` reaparece e o veredicto vira `MISSING-BUMP`, exit `1`. Verificado no mesmo clone.

Vetores adicionais testados após a correção, todos corretamente reprovados: rename dentro de `plugin/`, mudança apenas de modo, substituição de arquivo por symlink, cópia de arquivo para dentro de `plugin/`.

Fail-closed confirmado nos caminhos sem informação: versão ausente, versão malformada e base inalcançável retornam exit `2`. Não há caminho que produza exit `0` por falta de dados.

### Readability

Separação explícita entre camada pura e camada de git, com comentário de fronteira. O comentário em `changed_paths` explica por que `--no-renames` é carregado de significado, que é exatamente onde um leitor futuro removeria a flag por parecer supérflua. Mensagens de erro nomeiam as duas versões comparadas, atendendo SC-003 sem consulta externa.

### Architecture

O verificador fica em `tests/`, fora de `plugin/`. Duas consequências corretas: não é distribuído aos consumidores, e alterar o próprio gate não dispara a exigência que ele impõe. O nome fora do glob `validate_*.py` evita que a matriz de portabilidade colete um verificador que precisa de contexto de pull request — e evita a alternativa pior, um no-op silencioso que esconderia ausência de verificação atrás de sucesso.

Nenhuma duplicação de `validate_distribution.py`: o gate compara ordem entre duas revisões e não reverifica coerência interna da versão, respeitando FR-006.

### Security

Nenhum segredo no diff. O job de CI mantém `permissions: contents: read`, não adiciona secret e usa `persist-credentials: false`. As actions estão fixadas por SHA completo, reusando os mesmos pins já presentes no arquivo. `github.event.pull_request.base.sha` vem do payload do evento e é usado como argumento de `git`, não interpolado em shell de forma perigosa — é passado por variável de ambiente.

### Performance

Irrelevante nesta escala: dois `git show` e um `git diff` por execução.

### Critical Issues

Nenhum pendente. O bypass de rename era crítico e está corrigido, com regressão coberta.

### Important Issues

Nenhum pendente.

Registrado como limite conhecido, não como defeito: duas pull requests concorrentes que subam para a mesma versão passam isoladamente e conflitam no merge. Já documentado em `PLAN-CONTEXT.md#FASE-001` como risco aceito desta fase.

### Constitution References

Nenhum conflito. A cláusula "Fail-closed sem waiver" foi o critério que orientou a verificação dos caminhos sem informação, e todos reprovam.

### Revisão independente

Um revisor independente foi despachado e entregou relatório. Ele **reproduziu o mesmo bypass de rename de forma independente**, em repositório descartável próprio, chegando à mesma causa: `git diff --name-only` liga detecção de rename por padrão, sem precisar de `-M`. Duas reproduções independentes do mesmo defeito.

Ele confirmou, verificando e não apenas raciocinando: os caminhos fail-closed, a comparação por tupla de inteiros, a ausência de sobreposição com `validate_distribution.py`, que nada foi adicionado em `plugin/`, e que o job de CI usa o campo correto do payload do evento.

Dois achados dele foram além do que eu tinha:

1. **A suíte nunca exercitava git de verdade.** Todo teste da camada de git usava monkeypatch; `test_diff_disables_rename_detection` apenas afirmava que `--no-renames` aparece no argv, sem provar o comportamento resultante. Foi exatamente essa lacuna que permitiu o bypass conviver com "228 testes OK". Corrigido: classe `RealGit` em `tests/validate_bump_gate_contract.py`, que sobe repositório git real em diretório temporário e exercita rename para fora, remoção simples, mudança fora do bundle, bump válido, a CLI completa e base inalcançável. Suíte foi de 29 para 35 testes.
2. **FR-007 não se fecha só com código.** Uma reprovação do job só bloqueia a integração se o check estiver registrado como required status check na branch protection de `main`. Nada no diff garante isso. Registrado como `SGD-4` no backlog externo.

Sobre a completude da correção, ele verificou os primos do vetor: detecção de cópia nunca esteve ligada (exige `-C`), mudança apenas de modo é listada normalmente, e symlink é blob como qualquer outro. Marcou explicitamente symlink e submódulo como raciocinados e não reproduzidos.

Resíduo de baixa prioridade apontado por ele e registrado como `SGD-5`: `on.pull_request` sem `types:` explícito usa o default `[opened, synchronize, reopened]`, então retargetar uma PR para outra base sem novo push não redispara o gate, mantendo um PASS calculado contra a base antiga. Não corrigido nesta fase porque `on.pull_request` é nível de workflow e incluir `edited` faria a matriz de portabilidade inteira rodar a cada edição de título. Comportamento padrão do GitHub Actions, não regressão desta mudança.

Veredito do revisor: APPROVE.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`
