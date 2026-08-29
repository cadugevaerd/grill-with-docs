# Ship 5.3.0 — plano de rollback e notas de monitoração

Feature: 025-goal-materialization
Work item: feature-goal-materialization-c29d98e49a524ca8a482615d8d528dab
Autorização humana: `.grill/work-items/<id>/receipts/human-authorization/ship.json` (scope `ship`, `APPROVED`)

## O que esta versão muda no comportamento observável

`init` passa a fixar `goal.md` na raiz do projeto de destino. Antes não fixava —
o documento simplesmente não era gerado. Todo projeto que rodar `init` na 5.3.0
passa a receber um arquivo novo na raiz que na 5.2.0 não recebia.

A superfície de escrita é exatamente uma: criar `goal.md` quando ele não existe.
Documento existente, em qualquer estado, nunca é tocado.

## Rollback

O rollback é a reversão da versão publicada; não há migração de dados a desfazer,
porque a entrega não altera nem apaga nada preexistente.

1. **Consumidor que quer voltar**: fixar a 5.2.0 no marketplace. `goal.md` já
   materializado permanece no projeto — é arquivo comum na raiz, sem registro
   externo que o exija. Removê-lo é `rm goal.md`, sem efeito colateral: nenhum
   work item selado o referencia (é justamente por isso que o bloco `goal` ficou
   fora de `WORK-ITEM.json` e de `immutable_metadata`, T017/T031b).
2. **Repositório**: a tag `5.3.0` é imutável por cláusula constitucional e **não**
   deve ser remarcada. Reverter é publicar 5.3.1 revertendo o merge
   (`git revert -m 1 <merge>`), nunca reescrever a tag ou a Release.
3. **Estado do work item**: `state.json` de work items criados sob a 5.3.0 carrega
   um bloco `goal`. Um plugin 5.2.0 lendo esse estado ignora a chave — o bloco é
   aditivo e nenhum leitor da 5.2.0 a exige.

Custo de rollback: baixo. Não há schema migrado, nem arquivo removido, nem estado
reescrito.

## O que monitorar depois do merge

| Sinal | Onde | O que significa |
|---|---|---|
| `GOAL-UNAVAILABLE` em `init` | saída do `init` no consumidor | Recusa nomeada: symlink, diretório, destino fora da raiz, UTF-8 inválido ou erro de filesystem. É fail-closed por desenho, mas um pico indica que algum caminho legítimo está sendo recusado |
| `"status":"PRESERVED"` com `reason` | payload do `init`, bloco `goal` | Documento humano encontrado. Esperado e benigno. Só é sinal de problema se vier acompanhado de reclamação de arquivo alterado — o que os 7 testes novos existem para tornar impossível |
| `goal.md` em encoding legado | relatos de consumidor | Consequência conhecida e documentada: `UnicodeError` → `BLOCKED`, `invalid UTF-8 goal`, e o `init` inteiro falha. Contrato fixa isso (materialization-cli.md:95). Se aparecer em uso real, é candidato a revisão do contrato, não bug de implementação |
| `bump-gate` e `ci.yml` na PR seguinte | GitHub Actions | A 5.3.0 precisa estar idêntica nos oito lugares. `validate_distribution.py` cobre isso |
| `validate_gauntlet_run_contract.py` | `ci.yml`, qualquer PR | Flaky **pré-existente**, caracterizado no `verify.md` por comparação controlada (0/8 dos dois lados na mesma árvore). Se reprovar, é esse teste, não esta entrega |

## Riscos residuais aceitos

- **I2** (`receipts/**` fora de `converge.fingerprint_exclude`): faz o componente
  `work` do fingerprint mudar entre gates do mesmo run sem que nada revisado mude.
  Não afeta o artefato publicado. Vai para o backlog.
- **Flaky do orquestrador do gauntlet**: idem, vai para o backlog. Pode reprovar o
  CI de uma PR qualquer, desta ou de outra feature.
- **Ato humano pendente do repositório**: `Version bump gate` ainda não é *required
  status check* na branch protection de `main` (SGD-4, SGD-7). Enquanto não for,
  FR-007 é convenção, não gate — a reprovação aparece em vermelho e nada impede o
  merge. Isso é anterior a esta entrega e não é resolvível por commit.
