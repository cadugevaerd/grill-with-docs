# Acceptance Checklist: Gate de bump de versão

**Purpose**: Validar que a implementação satisfaz o handoff FASE-001 antes de `verify`
**Created**: 2026-08-11
**Feature**: [spec.md](../spec.md)

## Os quatro cenários do handoff

- [ ] CEN-1 — mudança apenas fora de `plugin/`, sem bump: aprovado, código `NO-PLUGIN-CHANGE`, exit `0`
- [ ] CEN-2 — mudança em `plugin/` sem bump: reprovado, código `MISSING-BUMP`, exit `1`
- [ ] CEN-3 — mudança em `plugin/` com bump: aprovado, código `BUMPED`, exit `0`
- [ ] CEN-4 — mudança em `plugin/` com versão reduzida: reprovado, código `VERSION-REGRESSION`, exit `1`

## Mensagem de falha (FR-004, SC-003)

- [ ] A mensagem nomeia a versão da base de merge
- [ ] A mensagem nomeia a versão do HEAD
- [ ] A mensagem diz explicitamente que a versão precisa aumentar
- [ ] A mensagem é suficiente para corrigir sem consultar outra fonte

## Fail-closed (FR-005, cláusula constitucional)

- [ ] Versão ausente reprova com `VERSION-UNREADABLE`, exit `2`
- [ ] Versão malformada reprova com `VERSION-UNREADABLE`, exit `2`
- [ ] Não existe flag, variável de ambiente ou caminho que aprove mudança de `plugin/` sem bump

## Fronteiras (FR-006, Structure Decision)

- [ ] Remoção de arquivo em `plugin/` conta como mudança de conteúdo
- [ ] Mudança apenas em `tests/**` não exige bump
- [ ] O gate não reimplementa as checagens de coerência de `validate_distribution.py`
- [ ] `tests/check_version_bump.py` não é coletado por `tests/run_validators.py`
- [ ] Nada foi adicionado dentro de `plugin/`

## Integração de CI (FR-007)

- [ ] O job roda apenas em `pull_request`
- [ ] O checkout usa histórico completo, sem o qual não há base de merge
- [ ] A reprovação bloqueia a integração
- [ ] A matriz de portabilidade existente permanece inalterada

## Notes

- Marcar cada item somente com evidência executada, não por leitura de código.
