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

O subagente `reviewer-004` foi despachado com escopo de leitura e mandato de refutar, e não devolveu parecer dentro da janela desta fase. O registrado acima é a passada adversarial da sessão primária, com sondagens nomeadas e reproduzíveis — mais fraco que revisão independente, e declarado como tal.

## Suíte

303 testes, exit 0. `validate_workspace_contract` 53 → 65.
