# Review — FASE-001

**Veredito: APPROVE**, com um defeito encontrado e corrigido.

## Modo de falha 1 — guarda que deixou de rodar

A extração moveu recusa de symlink, resolução do item, snapshot global e leitura de estado para funções compartilhadas. O risco não é falha visível: é guarda que sai do caminho e só diverge sob concorrência ou ataque.

Comparação estática não bastou — as guardas mudaram de arquivo-função, então o diff de ordem acusa divergência mesmo quando o comportamento é idêntico. A prova foi funcional: rodar a versão anterior (`git show HEAD~1`) e a atual contra os mesmos casos e comparar os códigos de saída.

| Caso | Antes | Depois |
|---|---|---|
| passo inexistente | `INVALID-STEP` | `INVALID-STEP` |
| work-id com travessia (`../fuga`) | `INVALID-WORK-ID` | `INVALID-WORK-ID` |
| work item que é symlink | `WORK-ITEM-SYMLINK` | `WORK-ITEM-SYMLINK` |
| work item ausente | `WORK-ITEM-MISSING` | `WORK-ITEM-MISSING` |
| pular passos | `INVALID-TRANSITION` | `INVALID-TRANSITION` |

Cinco guardas, cinco códigos idênticos. A ordem de execução também: `INVALID-STEP` continua antes de tudo, o snapshot global continua sendo tirado antes do lock, e o `finally` continua cobrindo o mesmo bloco.

## Modo de falha 2 — mutação onde deveria haver recusa

**Defeito encontrado.** `development.audit` presente mas de outro tipo derrubava o comando com `AttributeError: 'dict' object has no attribute 'append'` — traceback cru, sem código nomeado, exatamente a classe que esta fase existe para eliminar.

Pior: o mesmo defeito já existia no `checkpoint`, que faz `setdefault("audit", []).append(...)` desde antes. Eu tinha copiado o padrão sem questioná-lo.

Corrigido nos dois: a trilha entra na validação de forma junto com `sequence` e `steps`, devolvendo `DEVELOPMENT-SCHEMA`. Ausente continua legítimo e vira lista; presente e de outro tipo é recusado antes de qualquer escrita. Coberto por `test_a_trail_that_is_not_a_list_is_named_not_a_traceback` e `test_checkpoint_also_names_a_trail_that_is_not_a_list`, ambos exigindo ausência de `Traceback` no stderr.

## Sondagens que não produziram defeito

| Ataque | Resultado | Leitura |
|---|---|---|
| `steps` com chave a mais | `TURNED`, chave extra descartada | a virada reescreve `steps` a partir de `SEQUENCE`; a chave inventada não sobrevive. Frouxidão pré-existente — nem `checkpoint` nem `status` validam chaves fora de `SEQUENCE` — e não introduzida aqui |
| `steps` com chave faltando | `PHASE-INCOMPLETE`, nomeia o passo | correto: ausente não é `complete` |
| `steps` com valor inválido (`"pizza"`) | `PHASE-INCOMPLETE`, nomeia o passo | correto pelo mesmo motivo |
| estado misto pending/complete | `PHASE-INCOMPLETE`, lista os 6 faltantes | correto |
| virada repetida | `REUSED`, arquivo byte-idêntico | idempotência antes da recusa, como o plano exigia |

## Ordem entre idempotência e recusa

O ponto mais delicado do desenho: "recusar quando nem tudo está `complete`" e "não fazer nada quando tudo está `pending`" descrevem estados que se sobrepõem. A idempotência é avaliada primeiro; invertê-la tornaria FR-004 inalcançável, porque um registro todo `pending` cairia em `PHASE-INCOMPLETE`. Verificado por teste, não por leitura.

## `step` fora de `SEQUENCE` na trilha

A virada grava `step: "phase-turn"`. Nenhum leitor itera `development.audit`: o único acesso em todo o core é o append. `grill_status.py` projeta `steps`, `current_step`, `completed` e `blocked`, nunca a trilha. Verificado por busca nos três scripts, não assumido.

## Revisão independente

O subagente `reviewer-004` devolveu parecer **depois** do ship desta fase. Veredito: sem achado aberto. O que ele acrescenta ao registrado acima:

- **Confirmou o Achado 1 de forma independente.** Encontrou o crash de `audit` não-lista por conta própria, com PoC em `/tmp` contra o código pré-correção, e só depois viu que já estava corrigido. Reproduziu contra o pós-correção e confirmou `DEVELOPMENT-SCHEMA`, exit 2. Também notou por que os 10 testes originais não pegavam: nenhum corrompia `audit` para tipo não-lista.
- **Verificou a extração linha a linha** contra `HEAD~1` e confirmou a ordem preservada. Acrescentou um ponto que minha prova funcional não cobria: `acquire_lock(root, args.work_id, item)` é chamado de forma idêntica nos dois comandos, sem `reuse_if_target_exists`, então `checkpoint` e `phase-turn` sobre o mesmo work item competem pelo mesmo lock e são serializados entre si.
- **Fechou os casos de borda de `phase_turn_command`** que o mandato pedia: chave ausente em `steps` vira `None`, nunca cai em `REUSED` por acidente; valor com caixa diferente é tratado como não-`complete`; `sequence` como tupla falha em `DEVELOPMENT-SCHEMA`, porque lista não é igual a tupla em Python; item repetido é impossível, já que só passa quem for igual a `SEQUENCE`.
- **Confirmou por busca que nenhum leitor itera a trilha**, nos dois scripts.

### Achado novo, herdado e não resolvido

`GLOBAL-MUTATION` é levantado dentro do `finally`, **depois** de `atomic_write` já ter persistido o estado. Um `raise` em `finally` descarta o `return`, então a escrita aconteceu e o operador recebe `BLOCKED` — que se lê como "nada aconteceu". Verificado por mim em Python puro após o apontamento.

Agravante que ele levantou e eu confirmei: `grep GLOBAL-MUTATION tests/` não retorna nada. O guard nunca foi exercitado positivamente por nenhum teste, novo ou antigo. Meu `test_phase_turn_refuses_to_disturb_the_global_projection` prova o caminho feliz — que o comando não mexe no global — e não que o guard dispara quando alguém mexe.

Ele sinalizou explicitamente que é comportamento herdado do `checkpoint`, não regressão desta fase. Registrado como SGD-14, não corrigido aqui.

### Registro de ordem

O parecer chegou depois do ship. Este arquivo dizia que ele não havia devolvido parecer — verdade quando escrito, falso agora. O Achado 1 é da sessão primária, e ele o confirmou de forma independente; o achado do `GLOBAL-MUTATION` é dele.

## Suíte

303 testes, exit 0. `validate_workspace_contract` 53 → 65.
