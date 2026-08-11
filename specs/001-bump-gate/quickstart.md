# Quickstart — validar o gate de bump

## Pré-requisitos

Python 3.10+ e `git`. Nenhuma dependência externa.

## Testes da lógica pura

```bash
python3 tests/validate_bump_gate_contract.py
```

Exercita `parse_version`, `touches_plugin` e `decide` sem git e sem contexto de pull request. Precisa passar em qualquer máquina, inclusive na matriz de CI onde não há pull request.

## Suíte completa do repositório

```bash
python3 tests/run_validators.py
```

O novo arquivo entra pelo glob `validate_*.py` sem registro manual. `tests/check_version_bump.py` **não** entra, por não casar o glob — isso é intencional.

## Exercício de ponta a ponta contra o repositório real

Com o repositório em uma branch derivada de `main`:

```bash
# cenário: nada em plugin/ mudou -> PASS
python3 tests/check_version_bump.py --base-ref main --json

# cenário: plugin/ mudou sem bump -> FAIL com MISSING-BUMP
printf '\n' >> plugin/skills/grill-with-docs/SKILL.md && git commit -qam "toca plugin sem bump"
python3 tests/check_version_bump.py --base-ref main --json; echo "exit=$?"
```

Esperado no segundo caso: exit `1`, `code` igual a `MISSING-BUMP`, e a mensagem citando as duas versões.

## Verificação no CI

Na pull request, o job de gate aparece separado da matriz de portabilidade. Ele só existe em `pull_request` e faz checkout com histórico completo, porque a base de merge é indispensável.
