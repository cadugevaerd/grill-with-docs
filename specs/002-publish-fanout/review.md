## Review Report

Verdict: APPROVE
Source fingerprint: tree 865be940ae3243a8ae0ad07d9323072658bf228ed8f1bd444bb8221816e0fc75 / work 5ca57aa376734971ba8aa511e74f275034b333b684fb07fd8f7d0e7ba0ff7329 / plan 88814086ed1b31a2530b2b7b99f389353f1062e24107a7c01b06c9d3cc5f6479

### Test Quality

Os testes exercitam comportamento contra os schemas reais dos dois índices, incluindo uma entrada vizinha compactada à mão — é ela que denuncia reformatação indevida, e nenhum teste sobre a camada pura pegaria isso. `test_update_changes_only_three_lines` fixa o tamanho do diff, que é o requisito de revisibilidade escrito no plano.

Lacuna consciente: nenhum teste executa o workflow. Os passos de tag e de guard de segredo foram exercitados manualmente, extraídos do YAML e rodados contra um clone; ficam documentados em `converge.md`, não automatizados.

### Runtime Correctness

Três defeitos encontrados por execução durante esta fase, todos corrigidos e cobertos por regressão:

1. **Reformatação de vizinhas.** Reserializar o índice inteiro normalizava a entrada `quality-security-gate`, escrita à mão em forma compacta. O diff saía com 13 linhas em vez de 3. Corrigido com edição textual cirúrgica.
2. **Inserção aninhada.** O caminho de criação ancorava no último `}` do arquivo, que é o fecho do objeto `policy` do último plugin, e inseria a entrada nova dentro do vizinho, produzindo JSON inválido. Corrigido ancorando pelo nome do último plugin com brace matching string-aware.
3. **Patch na chave errada.** `retarget` usava regex com `count=1` sobre o texto da entrada. Com uma chave homônima aninhada ordenada antes da real — `meta.version` antes do `version` da entrada — patcheava a errada, corrompendo dado alheio e deixando a versão real intocada. Reproduzido. Corrigido com busca sensível a profundidade: `version` só no nível 1 da entrada, `ref` e `sha` só dentro do objeto `source`.

4. **Âncora textual pegando objeto errado (crítico, achado pelo revisor independente).** `object_span` assumia que `name` é a primeira chave da entrada. Com objeto aninhado antes dela, a âncora caía no aninhado e a publicação era colada lá dentro, deixando o índice resolvendo para o release velho enquanto a ferramenta reportava sucesso. Corrigido identificando a entrada pelo `name` parseado dos objetos do array `plugins`.
5. **Split-brain com entradas duplicadas (achado pelo revisor).** Decisão na primeira ocorrência, escrita na última. Agora recusa: índice ambíguo não é resolvido por escolha silenciosa.

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

### Revisão independente

O revisor reproduziu, com ataques próprios contra o módulo e contra os clones reais, duas corrupções que eu não havia encontrado — a crítica, de âncora textual, era a mais grave desta fase e passava por todos os 26 testes que existiam. Confirmou também, verificando e não apenas raciocinando: CRLF preservado, `plugins: []` recusado, idempotência real sem escrita, e o manuseio do token — `-c http.extraheader` nunca toca `.git/config`, `::add-mask::` precede o uso, e `permissions` está escopado ao job que precisa.

Um terceiro achado dele, sobre `retarget`, era de uma versão anterior à minha correção de profundidade; verifiquei o cenário exato contra o código atual e não se reproduz.

Ele apontou também que nenhum dos 26 testes cobria a premissa mais frágil — a posição de `name` dentro do objeto — apesar de o próprio código dizer esperar edição manual por humano. Quatro regressões foram acrescentadas por isso.

### Governance

ADR-0003 dizia "espelho de `plugin/` mais o README" com status `accepted`. A virada para referência não podia contradizê-lo em silêncio. `ADR-0006` foi escrito para substituí-lo, com a evidência corrigida registrada e as relações `amends: ADR-0001, ADR-0005` e `supersedes: ADR-0003`. ROADMAP, PLAN-CONTEXT e handoff da FASE-002 passaram a citar o ADR vigente. Auditoria após a mudança: `GO`, zero findings.

Esse gap foi apontado por um executor que se recusou a sobrescrever o arquivo em silêncio quando percebeu a contradição com um ADR aceito. A recusa estava certa.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`
