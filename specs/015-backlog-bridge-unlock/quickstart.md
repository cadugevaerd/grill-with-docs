# Quickstart — validar a FASE-001

Guia de validação. Detalhes de comportamento estão em [contracts/backlog-sync-cli.md](./contracts/backlog-sync-cli.md) e [data-model.md](./data-model.md).

## Pré-requisitos

- Python >=3.10 no PATH.
- Repositório em `feat/backlog-ssot`, árvore limpa.
- Para os cenários 3 e 4, `backlogctl` disponível e repositório vinculado. Os cenários 1 e 2 não exigem nada externo.

## 1. Suíte completa, sem binário externo

Prova a restrição de ambiente: nenhuma cobertura depende de `backlogctl`, `specify` ou `node`.

```bash
python3 tests/run_validators.py
```

Esperado: exit 0. Baseline antes desta fase é 877 testes com 1 skip dependente de ambiente; o número cresce com as regressões acrescentadas.

## 2. Só o validador da ponte

Ciclo curto durante a implementação.

```bash
python3 tests/validate_backlog_contract.py -v
```

Esperado: exit 0, com os casos novos visíveis pelo nome — gate de identidade no lugar do de integridade, espelho de decisão encerrada, mapa de estados, e ausência de duplicata em reexecução.

## 3. Prévia sobre um work item real

Prova o defeito principal corrigido. Antes desta fase, os três work items retornavam `BUNDLE-INTEGRITY`.

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  backlog-sync . --work-id feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420
```

Esperado: `verdict: PREVIEW`, e `items` listando as quatro decisões do work item, todas com desfecho `PROPOSED`. Nenhuma escrita no backlog — prévia é o padrão.

Confirmar que nada mudou:

```bash
"$BACKLOGCTL_EXECUTABLE" --json item list --code SGD | python3 -c "import json,sys;print(len(json.load(sys.stdin)['data']))"
```

Esperado: mesma contagem antes e depois.

## 4. Idempotência sob aplicação

Executar apenas quando quiser de fato escrever no backlog. Requer confirmação explícita, e o segundo comando é a prova que importa.

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  backlog-sync . --work-id feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420 --apply
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  backlog-sync . --work-id feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420 --apply
```

Esperado: a primeira execução relata `APPLIED` por decisão e `changed: true`. A segunda relata `REUSED` em todas, `changed: false`, `verdict: PREVIEW`, e a contagem de itens do backlog não muda.

## 5. Recusas preservadas

O que **não** pode ter afrouxado.

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py backlog-sync . --work-id nao-existe
```

Esperado: recusa nomeada, exit diferente de 0, sem traceback.

Adulterar um byte do bloco `immutable` de um `WORK-ITEM.json` copiado para diretório temporário e repetir o comando deve produzir `IMMUTABLE-TAMPERED`.

## 6. Contrato de distribuição

Obrigatório porque a fase toca `plugin/**`.

```bash
python3 tests/validate_distribution.py
```

Esperado: exit 0 com a versão consistente nos oito lugares. Alvo desta fase: 2.9.0.
