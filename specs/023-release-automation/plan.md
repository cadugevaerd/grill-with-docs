# Implementation Plan: Release automática por versão publicada

## Abordagem escolhida

Um passo novo no job `release` de `.github/workflows/publish.yml`, logo depois da criação da tag,
espelhando o desenho do passo que já existe: guarda de existência primeiro, ação depois, verificação
de ancoragem por último.

### Alternativas descartadas

- **Job separado**: exigiria novo checkout e novo `needs`, e deixaria a janela em que a tag existe e
  a release não. No mesmo job a publicação é atômica do ponto de vista de quem observa.
- **Action de terceiro** (`softprops/action-gh-release` etc.): dependência nova, pin de SHA para
  manter, e nenhuma capacidade que `gh` — já presente no runner — não tenha.
- **Notas curadas por arquivo de changelog**: exigiria manter o changelog em dia como pré-condição de
  merge, o que é outra dívida. `--generate-notes` deriva das PRs, que já são a fonte real.

## Desenho do passo

```
existing=$(gh release view "$REF" --json tagName -q .tagName 2>/dev/null || true)
if [ -n "$existing" ]; then
  echo "release $REF já existe; nada a criar"
else
  gh release create "$REF" --title "$REF" --generate-notes --verify-tag
fi
anchored=$(git rev-parse -q --verify "refs/tags/$REF^{commit}")
[ "$anchored" = "$SHA" ] || falha com ::error::
```

- `|| true` só captura "release inexistente"; a divergência de commit continua reprovando de forma
  explícita, mesma disciplina do comentário que já existe no passo da tag.
- `--verify-tag` recusa release órfã.
- `GH_TOKEN: ${{ github.token }}` usa a permissão `contents: write` que o job já declara. Sem segredo
  novo.
- Nada de payload de evento entra no shell: só `REF` e `SHA`, ambos derivados de `plugin.json` e do
  SHA do commit. Sem superfície de injeção.

## Ordem e garantias

`Criar a tag` → `Criar a release` → job `publish` (por `needs: release`). Quando o job `publish`
aponta os marketplaces, a release já existe. Se a tag já existia e apontava para o mesmo commit, o
passo da tag encerra cedo e o passo da release ainda roda — que é exatamente o estado do repositório
hoje, com tags sem release.

## Cobertura

Cinco testes novos em `tests/validate_bump_gate_contract.py`, classe `WorkflowWiring`: ordem,
permissão e ausência de segredo/payload, idempotência, falha por ancoragem divergente, e shell válido
em todo o `publish.yml` — que antes não era verificado, só `bump-gate.yml` e `ci.yml`.
