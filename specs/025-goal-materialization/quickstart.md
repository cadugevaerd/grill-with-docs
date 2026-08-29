# Quickstart: validar a materialização do goal.md

**Fase 1** | **Data**: 2026-08-26

Cenários executáveis que provam a entrega ponta a ponta. Nenhum toca a rede nem
exige ferramenta externa.

## Pré-requisitos

- Python >=3.10 no `PATH`.
- `git`, para criar os repositórios sintéticos dos cenários.
- Nada mais. Sem `uv`, sem `specify`, sem `node`, sem `backlogctl`.

Nos cenários abaixo, `PLUGIN` é
`plugin/skills/grill-with-docs/scripts` a partir da raiz deste repositório.

## Gate da suíte

```bash
python3 tests/run_validators.py
```

Esperado: exit `0`. O validador novo entra pelo glob de `validate_*.py`, sem
registro manual. A contagem de testes sobe em relação à baseline; o veredicto
não muda.

## Cenário 1 — O documento chega em projeto limpo (US1, SC-001)

```bash
mkdir -p /tmp/goal-c1 && cd /tmp/goal-c1
git init -q . && git commit -q --allow-empty -m init

GRILL_SKIP_DEPENDENCIES=1 python3 $PLUGIN/grill_workspace.py \
  init . --type feature --slug exemplo --skip-backlog
```

Esperado: no payload, `"goal":{"path":"goal.md","sha256":"<hex>","status":"CREATED","version":"v1"}`,
e `goal.md` presente na raiz com `<!-- grill-with-docs-goal:v1 -->` na primeira
linha.

Conferir que o hash reportado é o dos bytes no disco (SC-004):

```bash
python3 -c "import hashlib,sys;print(hashlib.sha256(open('goal.md','rb').read()).hexdigest())"
```

Esperado: idêntico ao `sha256` do payload **e** ao gravado em
`.grill/work-items/*/state.json` no bloco `goal`.

**Falha**: `goal.md` ausente, ou hash divergente. O segundo caso é o mais grave:
significa que o hash veio do conteúdo esperado e não do disco, e deixaria de
detectar qualquer deriva.

## Cenário 2 — Segunda execução reusa, não reescreve (US1, SC-003)

Continuando no mesmo diretório:

```bash
stat -c '%Y %s' goal.md
GRILL_SKIP_DEPENDENCIES=1 python3 $PLUGIN/grill_workspace.py \
  init . --type feature --slug exemplo-dois --skip-backlog
stat -c '%Y %s' goal.md
```

Esperado: `"status":"REUSED"` no bloco `goal`, mesmo `sha256` do Cenário 1, e
exatamente **um** `goal.md` na raiz.

**Falha**: `CREATED` de novo, ou hash diferente. Ambos significam reescrita.

## Cenário 3 — Arquivo humano é preservado (US2, SC-002)

```bash
mkdir -p /tmp/goal-c3 && cd /tmp/goal-c3
git init -q . && git commit -q --allow-empty -m init
printf 'meus objetivos do trimestre\n- crescer\n' > goal.md
sha256sum goal.md > /tmp/goal-c3-antes.txt

GRILL_SKIP_DEPENDENCIES=1 python3 $PLUGIN/grill_workspace.py \
  init . --type feature --slug exemplo --skip-backlog

sha256sum -c /tmp/goal-c3-antes.txt
ls -a | grep -i goal
```

Esperado: `"status":"PRESERVED"` com `reason`; `sha256sum -c` aprova (bytes
idênticos); e `ls` mostra **apenas** `goal.md` — nenhum `goal.md.bak`,
`goal.md.orig`, `goal.md~` ou cópia sob outro nome.

**Falha**: qualquer arquivo extra, ou bytes alterados. É o cenário cujo custo de
errar é perda de trabalho humano irrecuperável.

## Cenário 4 — Symlink é recusado, não seguido (FR-008)

```bash
mkdir -p /tmp/goal-c4 && cd /tmp/goal-c4
git init -q . && git commit -q --allow-empty -m init
printf 'segredo\n' > /tmp/goal-c4-alvo.txt
ln -s /tmp/goal-c4-alvo.txt goal.md

GRILL_SKIP_DEPENDENCIES=1 python3 $PLUGIN/grill_workspace.py \
  init . --type feature --slug exemplo --skip-backlog
cat /tmp/goal-c4-alvo.txt
```

Esperado: o comando falha com `GOAL-UNAVAILABLE` e razão `unsafe target`; o
arquivo apontado continua com `segredo`.

**Falha**: o conteúdo do alvo mudar. Seria escrita fora da raiz do projeto,
guiada por um link que o projeto não controla.

## Cenário 5 — Documento vazio não é recriado por cima (Edge Case)

```bash
mkdir -p /tmp/goal-c5 && cd /tmp/goal-c5
git init -q . && git commit -q --allow-empty -m init
: > goal.md

GRILL_SKIP_DEPENDENCIES=1 python3 $PLUGIN/grill_workspace.py \
  init . --type feature --slug exemplo --skip-backlog
wc -c goal.md
```

Esperado: `"status":"PRESERVED"` e `goal.md` com `0` bytes.

**Falha**: preencher o arquivo. Vazio é divergente, e divergente é preservado —
tratar vazio como "praticamente inexistente" abriria a exceção que FR-002 nega.

## Cenário 6 — Ordem trocada e conteúdo extra continuam conformes (FR-014)

```bash
python3 tests/validate_goal_document_contract.py
```

Esperado: os testes de reordenação e de acréscimo passam. Um documento com as
seções em ordem diferente é conforme; um documento com texto após a última
seção exigida é conforme. Presença basta.

**Falha**: reprovar qualquer um dos dois. Significaria que a regra virou
verificação de forma, não de presença, e todo documento legitimamente estendido
por um consumidor passaria a divergir.

## Cenário 7 — Faltar uma parte reprova e nomeia (US3, SC-005)

```bash
python3 tests/validate_goal_document_contract.py
```

Esperado: para **cada** item da tupla `ESSENTIAL`, existe um caso que remove
aquele item e verifica que a reprovação **nomeia o item ausente**. A saída diz
qual parte faltou sem que o leitor precise procurá-la.

**Falha**: reprovar sem nomear. O operador ficaria com "documento não conforme"
e onze candidatos.

## Cenário 8 — O conjunto exigido aparece em um só lugar (SC-006)

```bash
grep -rn "Cláusula residual" --include="*.py" plugin/ tests/
```

Esperado: exatamente **uma** ocorrência da tupla declarada, em
`plugin/skills/grill-with-docs/scripts/grill_core/goal_document.py`. Ocorrências
no validador aparecem apenas como leitura do módulo, nunca como redeclaração.

**Falha**: uma segunda cópia da tupla. É a duplicação que a 5.0.0 teve de
desfazer na CLI, e cujo defeito só apareceu em campo.

## Cenário 9 — Concorrência produz um único arquivo (FR-015, SC-003)

Coberto por teste, não por shell: dois `resolve_goal` sobre a mesma raiz, com o
segundo entrando depois de o primeiro ter criado o destino.

Esperado: um `CREATED`, um `REUSED`, um único arquivo íntegro. Nenhum dos dois
falha.

**Falha**: `BLOCKED` no segundo, ou arquivo truncado. Seria a janela TOCTOU que
`os.link` existe para fechar.

## Cenário 10 — Bump sincronizado (FR-017, SC-008)

```bash
python3 tests/validate_distribution.py
```

Esperado: exit `0`, com a versão idêntica nos oito lugares travados — quatro
manifests, a constante `VERSION` do próprio validador e três headings de
documentação.

**Falha**: qualquer divergência. O merge fica bloqueado pela cláusula
constitucional **Bump obrigatório do plugin**, e é isso que o gate reporta.

## Limpeza

```bash
rm -rf /tmp/goal-c1 /tmp/goal-c3 /tmp/goal-c4 /tmp/goal-c5 \
       /tmp/goal-c3-antes.txt /tmp/goal-c4-alvo.txt
```
