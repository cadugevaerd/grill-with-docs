# Quickstart — validar a FASE-002

Detalhes em [contracts/projection-cli.md](./contracts/projection-cli.md) e [data-model.md](./data-model.md).

## 1. Suíte completa, sem binário externo

```bash
python3 tests/run_validators.py
```

Esperado: exit 0, contagem acima da baseline da fase anterior, que fechou em 972.

## 2. Determinismo

```bash
S=plugin/skills/grill-with-docs/scripts/grill_workspace.py
W=feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4
python3 $S backlog-project . --work-id $W --apply
sha256sum .grill/work-items/$W/DECISION-BACKLOG.md
python3 $S backlog-project . --work-id $W --apply
sha256sum .grill/work-items/$W/DECISION-BACKLOG.md
```

Esperado: hashes idênticos, e a segunda execução devolve `REUSED` com `changed: false`.

## 3. Auditoria offline

```bash
HOME=/nonexistent python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  audit . --work-id feature-backlog-ssot-31293c736ce845a0bce7e738f08115d4
```

Esperado: conclui com veredito, sem recusa por indisponibilidade. Prova que o gate não depende da autoridade.

## 4. Frescor e divergência

```bash
python3 $S backlog-verify . --work-id $W
```

Esperado: `FRESH`. Depois, alterar o estado de uma decisão no backlog e repetir: `DIVERGED`, com a decisão nomeada.

## 5. Sem autoridade, a verificação recusa

```bash
HOME=/nonexistent python3 $S backlog-verify . --work-id $W
```

Esperado: `BACKLOG-UNAVAILABLE`, nunca `FRESH`.

## 6. Concordância dos parsers

```bash
python3 tests/validate_backlog_contract.py -k Parser -v
```

Esperado: cabeçalho com hífen ASCII, com três dígitos e sem título são vistos igualmente pelos dois leitores. Antes desta fase, os quatro casos divergiam.

## 7. Distribuição

```bash
python3 tests/validate_distribution.py
```

Esperado: exit 0 com 2.10.0 nos oito lugares.
