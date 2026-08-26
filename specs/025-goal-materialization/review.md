## Review Report

Verdict: APPROVE
Source fingerprint: tree 55fa1f6f65dfcef1f4d2a4da25d22836110c620db0b37b3b3b51046637595bf8 / work c41b9122785e297411ab55bc1ffec26f7eef2ecc8afd69632652c0734cd23324 / plan 2a8962d6a32f9c09f11057aeba8be817cc6cde901c7a6d31e6c2307e820f9f1a

Segunda passagem. A primeira devolveu `REQUEST CHANGES` por I1 sobre tree
`1be6f094…`; I1 foi corrigido e o verify reemitido pela cadeia sucessora
(`execution_round` 2, `chain_stale: []`). Este veredicto é sobre tree `55fa1f6f…`.

Converge: CONVERGED (zero findings, tasks.md inalterado). Verify: PASS.

Nota sobre o `work` do fingerprint: mudou de `ab7dd9bb…` para `c41b9122…` entre o verify e
este review. A única diferença é `.grill/work-items/<id>/receipts/`, que os próprios
checkpoints das gates escrevem e que **não** está em `converge.fingerprint_exclude` (lá
constam `state.json` e `ROUND-LOG.jsonl`, não `receipts/**`). Recalculando o diff com
`receipts/**` excluído, não sobra nenhuma mudança de conteúdo revisado. Evidência tratada
como fresca; ver Important I2.

### Test Quality

12 testes novos, todos stdlib, sem rede, sem ferramenta externa — a matriz de CI
(3 SOs × Python 3.10/3.13) roda sem `uv`, `specify`, `node` ou `backlogctl`. O teste que
remove cada item de `ESSENTIAL` um a um e exige que a reprovação **nomeie** o ausente é o
teste certo para FR-012/SC-005: fecha a porta para "documento não conforme" com onze
candidatos.

Duas armadilhas foram encontradas e corrigidas pelo próprio autor durante a escrita, e
ambas teriam produzido teste verde e inútil: `replace(item, "", 1)` removia só a primeira
ocorrência, e itens que aparecem mais de uma vez no template (`GOAL-HOLD:`, `PLAN_ONLY_STOP`)
continuavam presentes; e o scan de SSOT excluía qualquer caminho contendo `.git`, o que
zerava todos os hits quando o worktree vive sob `.git/grill/wt-…`. Registrar isso é o
oposto de ruído: é a diferença entre cobertura e aparência de cobertura.

**I1, corrigido nesta rodada.** `resolve_goal` era exercitado apenas para `CREATED`,
`REUSED` e o `BLOCKED` de destino-diretório. O validador foi de 12 para 19 testes e agora
cobre os três `reason` de `PRESERVED`, arquivo vazio, symlink com o alvo verificado intacto,
`invalid UTF-8 goal` e o exit 2 do CLI. Cada caso de `PRESERVED` compara `sha256`
antes/depois e exige que a raiz contenha exatamente `goal.md`.

O que fecha I1 não é a suíte verde, é a prova de mutação: com o ramo `PRESERVED` trocado por
uma sobrescrita, 4 dos novos casos reprovam; com o código restaurado, 19/19 `OK`. Isso
demonstra que os testes mordem o defeito específico que a lacuna deixava passar, em vez de
apenas acompanhar o comportamento atual.

### Runtime Correctness

- `read_regular` verifica `S_ISREG` sobre o `fstat` do **descritor já aberto**, com
  `O_NOFOLLOW`. Não há janela entre checar e abrir — é a forma correta, não a aproximação
  com `os.path.isfile` seguida de `open`.
- `atomic_create` apoia o no-clobber no kernel (`os.link` recusa destino existente), em vez
  de um `if exists` seguido de escrita. A garantia é estrutural, e o teste nomeia
  honestamente que exercita o ramo `FileExistsError`, não uma corrida real de processos.
- `fsync` do arquivo e do diretório, com o do diretório em best-effort e `OSError` engolido
  com justificativa — correto para os filesystems suportados.
- O temporário do `mkstemp` é removido no `finally`, inclusive quando `os.link` falha. Não
  deixa `.goal.md.XXXX` órfão na raiz do usuário.
- Revalidação pós-criação (`unsafe target after create`, `read-back validation failed`)
  relê do disco em vez de assumir o que foi escrito. É o que sustenta SC-004.
- `goal.md` humano em encoding não-UTF-8 faz o `init` inteiro falhar com `GOAL-UNAVAILABLE`
  em vez de `PRESERVED`. **Não é desvio**: `contracts/materialization-cli.md` linha 95 fixa
  `UnicodeError` → `BLOCKED, invalid UTF-8 goal`. Fica registrado como consequência
  operacional conhecida da decisão, não como defeito.

### Readability

Os comentários explicam **por que**, não o que. Três exemplos que carregam peso real:
a docstring de `ESSENTIAL` explica que derivar a tupla do template faria o validador
confirmar que o template é igual a si mesmo; `managed_version` explica que um marcador solto
no meio faria um documento humano que apenas cita o marcador passar a ser julgado pelo
contrato; e o comentário em `initial_files` explica por que `goal` não entra em
`immutable_metadata`. Densidade condizente com o resto do repositório.

### Architecture

Direção de dependência correta e verificável: `grill_core/goal_document.py` não importa
`grill_workspace`, não toca disco no import, e é o único lugar onde `ESSENTIAL` é declarada
— asserção travada por teste, não por convenção. `ensure_goal.py` espelha `ensure_workflow.py`
(função de decisão pura + wrapper de CLI que detém o contrato de stdout), então quem conhece
um conhece o outro. `ensure_project_goal` é simétrica a `ensure_project_workflow`.

O bloco `goal` fora de `WORK-ITEM.json` e de `immutable_metadata` é a decisão de arquitetura
mais importante do diff: `goal.md` é artefato que um humano pode legitimamente editar depois,
e selá-lo na identidade do work item faria uma edição legítima invalidar work item vivo.
`state_template` ganhou `goal: dict | None = None`, então `migrate_command` — que nunca
materializa `goal.md` — produz `state.json` idêntico ao de antes.

### Security

- Symlink no destino é recusado antes de qualquer escrita, e o alvo apontado permanece
  intacto (verificado: Cenário 4 do quickstart, alvo segue com `segredo`). Fecha escrita
  guiada por link que o projeto não controla.
- Destino que resolve para fora da raiz é `BLOCKED`.
- Nenhum segredo, `.env` ou credencial no diff. Nenhuma chamada de rede introduzida;
  o único subprocesso é `git rev-parse --show-toplevel`, com argumentos fixos e sem shell.

### Performance

`read_regular` carrega o arquivo inteiro em memória. Para o `goal.md` gerenciado (12,3 KB)
é irrelevante; um arquivo humano arbitrariamente grande com esse nome na raiz seria lido
inteiro só para ser classificado como divergente. Custo aceitável, sem ação.

### Critical Issues

Nenhum.

### Important Issues

**I1 — RESOLVIDO.** `PRESERVED` e os ramos `BLOCKED` não tinham teste de regressão.
`tests/validate_goal_document_contract.py` cobre `CREATED`, `REUSED` e o `BLOCKED` de
diretório, mas não os três `reason` de `PRESERVED`, nem symlink, nem `invalid UTF-8 goal`,
nem `filesystem-error:<Tipo>`.

Por que importa: SC-002 é "nenhuma execução, em nenhum cenário, altera os bytes de um arquivo
preexistente", e o próprio quickstart diz que este é "o cenário cujo custo de errar é perda
de trabalho humano irrecuperável". Esse comportamento foi verificado **à mão** — por mim nos
Cenários 3 a 5 e pelo worker p04-a em oito repositórios de `/tmp` — e ambas as evidências são
efêmeras. Nada no repositório reprova se um refactor futuro trocar `PRESERVED` por
sobrescrita; o `init` passaria a destruir arquivo humano com a suíte verde.

Corrigido em `4083c25`, exatamente nesses termos, e verificado por mutação. O
comportamento nunca esteve errado — o que faltava era o repositório defendê-lo.

**I2 — `receipts/**` ausente de `converge.fingerprint_exclude`.**
`.specify/extensions/verify-review-ship/verify-review-ship-config.yml` linhas 13–19 excluem
`state.json` e `ROUND-LOG.jsonl`, mas não `.grill/work-items/**/receipts/**`. Como cada
checkpoint escreve receipts, o componente `work` muda entre duas gates do mesmo run sem que
nada revisado tenha mudado — exatamente o defeito que o próprio `verify` descreve como razão
para `HEAD` não entrar no fingerprint. Hoje isso força quem lê os relatórios a provar à mão
que a divergência é inócua.

Fora do escopo desta feature (é configuração do repositório, não do diff 025). Registrar
como item de backlog; não bloqueia este ship por si só.

### Constitution References (only for discovered conflicts)

Nenhum conflito descoberto. A cláusula `Bump obrigatório do plugin` está satisfeita e foi
verificada executavelmente pelo `verify` (`distribution: OK`, 5.3.0 nos oito lugares).

### Final Recommendation

APPROVE: run `/speckit.verify-review-ship.ship`

I1 está fechado com prova de mutação. I2 permanece aberto e é do repositório, não deste diff:
`receipts/**` fora de `converge.fingerprint_exclude` faz o componente `work` mudar entre
gates do mesmo run sem que nada revisado mude. Não bloqueia este ship; deve virar item de
backlog junto com o flaky de
`validate_gauntlet_run_contract.py::test_eight_concurrent_eligible_resumes_record_once_and_reuse_without_residue`,
que o `verify` caracterizou como externo a esta entrega por comparação controlada.
