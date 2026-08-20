# Review: release automática por versão publicada

## Risco técnico

**Baixo.** Um passo, no job que já tinha a permissão necessária, usando uma ferramenta que já está no
runner. Nenhuma dependência nova, nenhum segredo novo, nenhuma action de terceiro para manter pinada.

### O que poderia dar errado e não dá

- **Reexecução vermelha**: `gh release create` aborta com "already exists". Coberto pela guarda de
  existência e por teste.
- **Release órfã**: criar release para tag inexistente deixaria um anúncio sem artefato. `--verify-tag`
  recusa, e o teste fixa a flag.
- **Release apontando para outro commit**: a conferência de ancoragem reprova com `::error::`.
- **Injeção pelo payload do evento**: o passo só lê `REF` e `SHA` por `env:`, ambos derivados de
  `plugin.json` e do SHA do commit. O teste proíbe explicitamente `github.event` e `secrets.` dentro
  do passo, então uma regressão nesse sentido quebra a suíte.

## Escopo

Não cresceu além de uma guarda de shell para `publish.yml`, que estava faltando e é uma linha de
cobertura, não funcionalidade.

## A escolha que mais importa

Passo no mesmo job, não job separado. Job separado deixaria uma janela em que a tag existe e a
release não — que é precisamente o estado que esta mudança veio eliminar. Publicação precisa ser
indivisível na observação de quem consome.

## Dívida deixada em aberto

- As releases ausentes de `v2.4.2` a `v3.3.2` continuam ausentes, por decisão registrada na emenda da
  constituição: a cláusula vale das versões novas em diante. Fica como dívida declarada, não waiver.
- O contrato verifica estrutura e shell, não executa a API do GitHub. A primeira publicação depois do
  merge é a verificação de campo — mesma fronteira já aceita para tag e marketplace.
- Os sete work items que selaram o hash anterior da constituição seguem `CONSTITUTION-STALE` até
  re-selagem deliberada.

## Veredito

GO para merge.
