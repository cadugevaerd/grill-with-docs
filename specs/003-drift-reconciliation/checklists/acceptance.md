# Checklist de aceite — FASE-003

Cada item nomeia a evidência que o satisfaz. Item sem evidência nomeada não conta.

## Verificação do estado publicado (código novo)

- [ ] CHK-001 — `verify_release` aprova um índice que corresponde à release. *(teste)*
- [ ] CHK-002 — Reprova divergência em `version`, nomeando encontrado e esperado. *(teste)*
- [ ] CHK-003 — Reprova divergência em cada um dos cinco campos do pin: `source`, `url`, `path`, `ref`, `sha`. *(teste)*
- [ ] CHK-004 — Reprova entrada ausente. *(teste)*
- [ ] CHK-005 — Reprova entrada duplicada, em vez de escolher uma. *(teste)*
- [ ] CHK-006 — Acumula divergências: uma entrada com versão e sha errados reporta as duas. *(teste)*
- [ ] CHK-007 — Campos curados divergentes entre marketplaces não reprovam. *(teste)*
- [ ] CHK-008 — `--verify` sai `0` no estado correto e `3` na divergência. *(teste de CLI)*
- [ ] CHK-009 — `--verify` com `--apply` é recusado como erro de uso. *(teste de CLI)*
- [ ] CHK-010 — Ciclo `--apply` seguido de `--verify` sobre o mesmo checkout aprova. *(teste de CLI)*

## Orquestração

- [ ] CHK-011 — O workflow relê o índice de um clone novo do remoto, não do clone que editou. *(inspeção do YAML)*
- [ ] CHK-012 — O workflow reprova quando a tag publicada não resolve para o commit publicado. *(inspeção do YAML)*
- [ ] CHK-013 — O passo de verificação roda depois do push e falha o job quando reprova. *(inspeção do YAML)*
- [ ] CHK-014 — Nenhum segredo novo entra no ambiente; o cabeçalho reusado continua mascarado. *(inspeção do YAML)*
- [ ] CHK-015 — O gatilho manual continua declarado. *(inspeção do YAML)*

## Gates do repositório

- [ ] CHK-016 — `python3 tests/run_validators.py` termina exit 0, com contagem ≥ 270.
- [ ] CHK-017 — Nada em `plugin/` mudou; nenhuma versão foi alterada.
- [ ] CHK-018 — O publicador continua fora do glob `validate_*.py`.

## Execução real

- [ ] CHK-019 — Segredo de publicação instalado. **Ato humano.**
- [ ] CHK-020 — Disparo manual executado uma vez.
- [ ] CHK-021 — Os dois destinos declarando a versão corrente, com pin resolvendo para o commit publicado.
- [ ] CHK-022 — Segundo disparo imediato não produz commit em nenhum destino.
