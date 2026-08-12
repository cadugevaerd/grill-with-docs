# Plan: Reconciliação do drift existente

**Spec**: `spec.md` · **Branch**: `003-drift-reconciliation`

## O que já existe e não se refaz

FASE-002 entregou o gatilho manual (`workflow_dispatch` em `.github/workflows/publish.yml`), a criação da tag imutável, o publicador cirúrgico (`tests/publish_to_marketplace.py`) e a matriz de dois jobs independentes. FR-001, FR-002, FR-006 e FR-007 já são propriedades desse código; esta fase os **verifica**, não os reimplementa.

O que falta é o que separa "escrevi e o push não deu erro" de "publiquei": a releitura do estado publicado. É o único código novo.

## Decisões de desenho

1. **A releitura vem do remoto, não do clone de trabalho.** Verificar o arquivo que o próprio passo acabou de editar prova apenas que a edição aconteceu na memória do runner. Um push para o lugar errado, um commit que não incluiu o arquivo ou um índice reescrito por outra execução concorrente passariam. A verificação clona de novo, raso, e lê o que o remoto serve.
2. **Camada pura decide, camada shell coleta.** `verify_release(index, release)` é uma função sem I/O sobre o índice já carregado, coberta pela suíte canônica. O clone e a resolução da tag ficam no YAML, que a matriz de portabilidade não roda. Mesma divisão de `check_version_bump.py`.
3. **Divergência não é destino inválido.** Um índice que não corresponde à release é uma reprovação de estado, não um alvo malformado. Ganha código de saída próprio (`3`), separado de `1` (alvo inválido) e `2` (uso). Confundir os dois faria o operador procurar defeito de configuração diante de um push perdido.
4. **A verificação nomeia todas as divergências, não a primeira.** Parar na primeira transformaria uma entrada com versão e pin errados em duas rodadas de investigação.
5. **`--verify` recusa conviver com `--apply`.** Verificar e escrever na mesma invocação faria a verificação atestar a própria escrita — exatamente a circularidade que a decisão 1 elimina.
6. **A resolução da tag usa a URL pública do canônico, sem credencial.** O que se prova é que a referência publicada resolve para o commit publicado *para quem instala o plugin*, e quem instala não tem o segredo.

## Camadas

| Camada | Arquivo | Novo | Coberto por |
|---|---|---|---|
| Decisão pura | `tests/publish_to_marketplace.py` — `verify_release` | sim | `tests/validate_publish_contract.py` |
| CLI | `tests/publish_to_marketplace.py` — `--verify`, saída `3` | sim | `tests/validate_publish_contract.py` |
| Orquestração | `.github/workflows/publish.yml` — passo de releitura | sim | execução real |
| Publicação | resto de `publish_to_marketplace.py` | não | já coberto |

## Contrato de `verify_release`

Entrada: o índice já carregado e a `Release`. Saída: veredito e a lista de divergências, cada uma nomeando campo, valor encontrado e valor esperado.

Reprova quando: a entrada não existe; existe mais de uma com o mesmo nome; `version` diverge; `source` não é objeto; qualquer um de `source`, `url`, `path`, `ref`, `sha` diverge. Campos curados fora do pin não são comparados — eles variam por marketplace por decisão de ADR-0006, e compará-los transformaria curadoria legítima em reprovação.

## Gates

- `python3 tests/run_validators.py` verde. Baseline a bater: 270 testes, exit 0.
- Nada em `plugin/` muda, logo o gate de bump responde `NO-PLUGIN-CHANGE` e nenhuma versão sobe. A reconciliação publica a `2.5.0` que já está declarada; inventar uma `2.5.1` só para ter o que publicar contradiz FR-006.
- O caminho `tests/**` está no filtro do CI, então a mudança dispara a matriz de portabilidade.

## Sequência de execução real

1. Merge desta fase na main. Não toca `plugin/`, logo não dispara publicação automática — como esperado.
2. Instalação do segredo de publicação. **Ato humano**, fora do alcance desta sessão.
3. Disparo manual único.
4. Leitura do resultado nos dois destinos.

O passo 2 é bloqueio duro: sem ele o passo 3 falha no primeiro passo que consome a credencial. Tudo que não depende dele é entregue nesta fase.

## Riscos

- **A verificação passa a poder reprovar uma publicação que funcionou.** Se o pin tiver um campo legitimamente diferente do esperado, a releitura barra. Mitigação: comparar exatamente os cinco campos que o publicador escreve, nunca mais que isso.
- **O clone de verificação custa uma segunda credencial em memória.** Reusa o cabeçalho já mascarado; nenhum segredo novo entra no ambiente.
- **Concorrência.** Duas execuções simultâneas poderiam intercalar push e releitura. O grupo de concorrência do workflow já serializa a publicação.
