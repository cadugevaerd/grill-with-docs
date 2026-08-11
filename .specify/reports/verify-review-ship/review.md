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

### Nota de procedimento

Um revisor independente foi despachado em paralelo e não entregou relatório. O achado acima veio da passada adversarial do orquestrador, reproduzida em clone real antes da correção. O gate não deve ser lido como tendo tido dois pares de olhos independentes.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`
