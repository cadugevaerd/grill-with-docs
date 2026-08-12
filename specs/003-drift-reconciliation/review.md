# Review — FASE-003

**Veredito: APPROVE**, com um bloqueio externo declarado e não contornado.

## Passada adversarial

O mandato foi procurar o **falso verde**: a verificação aprovar algo que não deveria. Nove sondagens contra `verify_release`, todas com um índice sintético e a release corrente.

| Sondagem | Resultado | Leitura |
|---|---|---|
| `sha` em maiúsculas no índice | reprova | correto — `parse_release` normaliza para minúsculo, a comparação é sobre o valor normalizado |
| `name` com espaço sobrando | reprova, "entrada ausente" | correto — o publicador também casa `name` exato, então a entrada realmente não é nossa |
| `name` com maiúsculas | reprova | idem |
| `version` numérica em vez de string | reprova | correto — `2.5` não é `"2.5.0"` |
| `plugins` com `null` ao lado da entrada | **aprova** | aceito, ver abaixo |
| `plugins` com string solta ao lado | **aprova** | aceito, ver abaixo |
| chave `version` duplicada na entrada | **aprova**, pelo último valor | aceito, ver abaixo |
| `source` com chave extra (`branch`) | **aprovava** | **defeito, corrigido** |
| entrada correta | aprova | linha de base |

## Defeito encontrado e corrigido

**`source` com chave a mais era aprovado.** Os cinco campos do pin podiam estar todos corretos e o destino ainda servir outra coisa, se a entrada carregasse uma segunda referência — `branch`, por exemplo — que o cliente resolvesse por cima do `sha`. É um falso verde legítimo: a releitura afirmaria "publicado" sobre um destino que aponta para um ramo móvel.

Corrigir só no verificador criaria o problema oposto. `plan_entry` preservava chaves desconhecidas no update (`{**source, **source_object(release)}`), então o publicador escreveria a entrada e a releitura, mais estrita, derrubaria o job **depois** do push — vermelho com o trabalho já feito.

A correção é nos dois lados, para que recusem o mesmo estado:

- `plan_entry` recusa com `TargetInvalid` uma entrada existente cujo `source` traga chave fora do pin. Falha **antes** de escrever.
- `verify_release` reporta `source.<chave> não pertence ao pin`. Defesa em profundidade, para estado que não foi escrito por nós.

Custo assumido: é fail-closed. Se um agregador adicionar um campo legítimo ao formato de `source`, a publicação para até alguém atualizar o publicador. Isso é intencional e está alinhado com o resto do módulo, que já recusa `source` vendorizado e entrada duplicada em vez de adivinhar. Evidência de que não afeta nada hoje: nos dois índices reais, nenhum dos 31 `source` carrega chave fora do formato declarado — os 15 vizinhos do codex usam `{source, path}` e os 15 do claude usam string.

Cobertura: `test_a_second_reference_inside_source_is_reported` e `test_the_publisher_refuses_what_the_verification_would_reject`.

## Aprovações conscientes

**Vizinho malformado não reprova.** Um `null` ou uma string solta na lista `plugins` é pulado pelo filtro `isinstance(p, dict)`, e a nossa entrada é verificada normalmente. É o comportamento certo: não somos donos dos vizinhos, e reprovar a nossa publicação por causa do erro de outro travaria a fase em algo que não podemos consertar. Fica registrado o limite: se o índice inteiro for rejeitado pelo cliente por causa desse vizinho, a nossa entrada não é servida e a verificação ainda aprova. `plan_entry` usa o mesmo filtro, então os dois lados concordam.

**Chave duplicada na entrada é resolvida pelo último valor.** `json.loads` fica com o último, e os parsers dos clientes fazem o mesmo. Aprovar pelo valor efetivo é aprovar o que o cliente vê. Diferente do caso que motivou o hotfix da FASE-002: lá o problema era *escrever* por cima de um valor sombreado, e o publicador continua recusando isso no texto.

## Orquestração

- Ordem dos passos conferida no YAML parseado: o push precede a releitura.
- A releitura não herda `working-directory: marketplace`; roda da raiz e clona em `marketplace-verify`, diretório distinto.
- `AUTH_HEADER` vem de `GITHUB_ENV`, já mascarado, e o passo de push anterior já o consumia da mesma forma. Nenhum segredo novo entra no ambiente e nenhuma URL carrega token.
- O passo roda mesmo quando o push é pulado por ausência de diff, e nesse caso é o que prova que o destino já estava em dia.
- A resolução de tag foi exercitada contra o canônico real: `v2.4.1` é tag anotada e a lógica entrega o **commit** `c6a9b070…`, não o objeto de tag `880827b1…`. Comparar contra o objeto de tag reprovaria toda publicação anotada. Tag ausente entrega vazio e derruba o passo.
- Sob `bash -e`, que é o shell padrão dos passos `run`, a saída 3 do verificador derruba o job.

## Revisão independente

O subagente `reviewer-003` foi despachado com escopo de leitura e mandato de refutar, e não devolveu parecer dentro da janela desta fase. O que está registrado acima é a passada adversarial da sessão primária, com as sondagens nomeadas e reproduzíveis. Isso é mais fraco do que a revisão independente que a FASE-002 teve, e fica declarado como tal em vez de ser apresentado como equivalente.

## Bloqueio não contornado

A execução real não aconteceu: o segredo de publicação não está instalado e instalá-lo é ato humano.

Publicar à mão a partir desta sessão produziria o resultado — os dois destinos em dia — mas não o objetivo declarado no handoff, que é exercitar a automação uma vez em condições reais. Uma reconciliação manual deixaria o pipeline tão não-exercitado quanto está hoje, e o primeiro teste real continuaria acontecendo às cegas num merge futuro. Por isso não foi feito, e não por falta de credencial disponível na máquina.
