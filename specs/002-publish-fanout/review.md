## Review Report

Verdict: APPROVE
Source fingerprint: tree 0bba2a1162bb8cc9a77da76983f8b39b7876a0d2a733f928c63539dd17526ffe / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 88814086ed1b31a2530b2b7b99f389353f1062e24107a7c01b06c9d3cc5f6479

### Test Quality

Os testes exercitam comportamento contra os schemas reais dos dois índices, incluindo uma entrada vizinha compactada à mão — é ela que denuncia reformatação indevida, e nenhum teste sobre a camada pura pegaria isso. `test_update_changes_only_three_lines` fixa o tamanho do diff, que é o requisito de revisibilidade escrito no plano.

Lacuna consciente: nenhum teste executa o workflow. Os passos de tag e de guard de segredo foram exercitados manualmente, extraídos do YAML e rodados contra um clone; ficam documentados em `converge.md`, não automatizados.

### Runtime Correctness

Três defeitos encontrados por execução durante esta fase, todos corrigidos e cobertos por regressão:

1. **Reformatação de vizinhas.** Reserializar o índice inteiro normalizava a entrada `quality-security-gate`, escrita à mão em forma compacta. O diff saía com 13 linhas em vez de 3. Corrigido com edição textual cirúrgica.
2. **Inserção aninhada.** O caminho de criação ancorava no último `}` do arquivo, que é o fecho do objeto `policy` do último plugin, e inseria a entrada nova dentro do vizinho, produzindo JSON inválido. Corrigido ancorando pelo nome do último plugin com brace matching string-aware.
3. **Patch na chave errada.** `retarget` usava regex com `count=1` sobre o texto da entrada. Com uma chave homônima aninhada ordenada antes da real — `meta.version` antes do `version` da entrada — patcheava a errada, corrompendo dado alheio e deixando a versão real intocada. Reproduzido. Corrigido com busca sensível a profundidade: `version` só no nível 1 da entrada, `ref` e `sha` só dentro do objeto `source`.

Sondagens adversariais adicionais, todas corretas após as correções: vizinho cujo nome contém o nosso, nossa entrada sendo a única, lista de plugins vazia (recusa por falta de âncora), indentação de 4 espaços, e vizinho com `}` e aspas escapadas dentro de string.

Fail-closed confirmado: índice ausente, JSON inválido, `plugins` que não é lista e `source` de tipo inesperado reprovam. Converter vendorização em referência é recusado em vez de adivinhado, porque mudaria o mecanismo de distribuição sem decisão registrada.

### Readability

Camadas explicitamente separadas: pura, sistema de arquivos, git. Os comentários explicam o que um leitor futuro removeria por parecer supérfluo — por que `--no-renames` no gate da fase anterior, por que ancorar pelo nome e não pelo último `}`, por que profundidade importa no patch.

### Architecture

O publicador não clona, não cria tag e não empurra: recebe um checkout pronto. Toda operação com credencial vive no workflow. Isso é o que torna a ferramenta inteiramente testável offline, e foi o que permitiu encontrar os três defeitos sem tocar em repositório remoto.

Fronteira preservada: nada em `plugin/`, nome fora do glob `validate_*.py`, `ci.yml` intocado.

### Security

O token vai por `http.extraheader`, nunca na URL do remote — uma URL com segredo fica gravada em `.git/config` e vaza em qualquer log que a imprima. `::add-mask::` é emitido antes de o header ser exportado. `permissions` no topo é `contents: read`; só o job de tag eleva para `contents: write`, e sobre o próprio repositório. Nenhum `|| true` que engula falha de gate: o único uso captura "tag ainda não existe" e está comentado.

Risco aceito e registrado: ADR-0004 escolheu um PAT com `admin:org`, `admin:enterprise` e `delete_repo` onde bastaria `contents: write` em dois repositórios. Acompanhado em `SGD-3`.

### Performance

Irrelevante: dois clones rasos e uma edição de JSON por execução.

### Critical Issues

Nenhum pendente.

### Important Issues

Nenhum pendente. Limites declarados: a publicação real nunca foi executada, porque o segredo não existe; e o merge desta fase não dispara o workflow, já que não toca `plugin/`. Ambos pertencem à FASE-003.

### Governance

ADR-0003 dizia "espelho de `plugin/` mais o README" com status `accepted`. A virada para referência não podia contradizê-lo em silêncio. `ADR-0006` foi escrito para substituí-lo, com a evidência corrigida registrada e as relações `amends: ADR-0001, ADR-0005` e `supersedes: ADR-0003`. ROADMAP, PLAN-CONTEXT e handoff da FASE-002 passaram a citar o ADR vigente. Auditoria após a mudança: `GO`, zero findings.

Esse gap foi apontado por um executor que se recusou a sobrescrever o arquivo em silêncio quando percebeu a contradição com um ADR aceito. A recusa estava certa.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`
