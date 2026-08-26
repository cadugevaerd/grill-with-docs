# Quickstart — validar a sucessão explícita de escopo

Guia de validação executável. Todos os comandos rodam a partir da raiz do
worktree `fix/reconcile-scope-succession`.

## Pré-requisitos

- Python >= 3.10 no `PATH` como `python3`. Nada além da biblioteca padrão.
- Sem rede. Nenhum passo aqui baixa nada, e nenhum exige `specify`, `node` ou
  `backlogctl` reais.
- `git` disponível: o `reconcile --apply` exige árvore limpa e confere a branch
  de integração.

## 1. Suíte completa

```bash
python3 tests/run_validators.py
```

Esperado: exit `0`. Baseline de referência antes desta mudança: 1303 testes em
27 validadores, com 1 skip dependente de ambiente em
`validate_workspace_contract.py`. Depois desta mudança a contagem sobe pelos
casos novos de sucessão; o skip permanece.

> A suíte completa passa dos 120 s em algumas máquinas. Para iterar, rode só os
> dois validadores afetados:
>
> ```bash
> python3 tests/validate_workspace_contract.py
> python3 tests/validate_distribution.py
> ```

## 2. Contrato de sucessão isolado

```bash
python3 -m unittest -v tests.validate_workspace_contract -k succession
```

Esperado: os casos de sucessão passam. Cobrem, no mínimo — C-001 a C-007 de
[contracts/reconcile-scope-authorization.md](./contracts/reconcile-scope-authorization.md):

- sucessor com dependência direta atravessa, nos dois caminhos;
- ausência, terceiro e transitividade continuam bloqueando;
- self, ciclo, dependência não reconciliada e conflito de decisão continuam com
  as mesmas anotações.

## 3. Versão sincronizada

```bash
python3 tests/validate_distribution.py
```

Esperado: exit `0`, com `5.2.1` nos oito pontos. Conferência manual rápida:

```bash
grep -o '"version": "[^"]*"' plugin/.claude-plugin/plugin.json
grep -o '"version": "[^"]*"' plugin/.codex-plugin/plugin.json
grep -n '"version"' .claude-plugin/marketplace.json .agents/plugins/marketplace.json
grep -n '^VERSION' tests/validate_distribution.py
grep -n '^# Grill with Docs v' plugin/skills/grill-with-docs/SKILL.md
grep -n '^# Protocolo de sessão v' plugin/skills/grill-with-docs/references/session-protocol.md
grep -n '\*\*v5' README.md
```

Os oito precisam concordar. Divergência reprova o gate de bump, que roda em toda
PR e sempre reporta.

## 4. Prova ponta a ponta do defeito corrigido

Reproduz o caso do handoff em um repositório descartável: um trabalho anterior é
reconciliado, e um sucessor que o declara reutiliza o mesmo caminho.

```bash
WS=$(mktemp -d)
git -C "$WS" init -q && git -C "$WS" commit -q --allow-empty -m init
CLI=$PWD/plugin/skills/grill-with-docs/scripts/grill_workspace.py

# antecessor e sucessor, ambos declarando o mesmo caminho
python3 "$CLI" init "$WS" --type feature --slug owner --skip-backlog
python3 "$CLI" init "$WS" --type fix     --slug succ  --skip-backlog
```

Depois, em cada bundle sob `$WS/.grill/work-items/`:

1. leve os dois a estado terminal (`status: complete`,
   `milestone_status: completed`, `active_phase: null`, `audit_verdict: GO`, e
   `ROADMAP.md` com todas as fases `complete`);
2. declare o mesmo caminho em `scope.paths` nos dois;
3. no bundle do sucessor, ponha o `work_id` do antecessor em `depends-on-work`.

Então:

```bash
git -C "$WS" add -A && git -C "$WS" commit -q -m items
python3 "$CLI" reconcile "$WS" --work-id "<owner_id>" --apply --integration-branch main
python3 "$CLI" reconcile "$WS" --work-id "<succ_id>"
```

Esperado **depois** da correção: a segunda chamada devolve
`{"verdict": "PREVIEW", "code": "OK", ...}` com `conflicts` vazio e exit `0`.

Esperado **antes** da correção (é o defeito): exit `1`, `verdict: "NO-GO"` e um
`SCOPE-OVERLAP:<succ_id>:…<-><owner_id>:…` em `conflicts`.

Controle negativo — remova `depends-on-work` do sucessor e repita a última
chamada: o `SCOPE-OVERLAP` volta. Se não voltar, a autorização vazou e virou
waiver. Restaure a declaração antes de seguir para o passo 5.

## 5. Preview permanece read-only

Continua no mesmo `$WS` do passo 4 — não o remova antes daqui.

```bash
python3 "$CLI" reconcile "$WS" --work-id "<succ_id>"   # sem --apply
git -C "$WS" status --porcelain=v1 --untracked-files=all
```

Esperado: saída vazia no `status`. Preview não grava nada, autorizada ou não.

Só então descarte o repositório temporário:

```bash
rm -rf "$WS"
```

## Critérios de aceite deste guia

| # | Passo | Esperado |
|---|---|---|
| 1 | suíte completa | exit `0`, 1 skip de ambiente |
| 2 | contrato de sucessão | casos novos passam |
| 3 | distribuição | `5.2.1` idêntica nos oito pontos |
| 4 | ponta a ponta | sucessor declarado passa; sem declaração, bloqueia |
| 5 | preview | nenhum byte alterado |
