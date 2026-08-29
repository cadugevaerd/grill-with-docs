# Contrato: materialização e superfície de saída

**Fase 1** | **Data**: 2026-08-26

Duas superfícies expõem a materialização: o script `ensure_goal.py`, que a
executa, e o subcomando `init` de `grill_workspace.py`, que a consome. Ambas
falam o mesmo vocabulário de estado.

## Superfície 1 — `ensure_goal.py`

### Uso embutido (o que o `init` chama)

```python
resolve_goal(root_argument: str | Path) -> GoalResult
```

Materializa ou valida `<root>/goal.md` e devolve a decisão **sem imprimir**.
Quem é dono do stdout renderiza; o `init`, que tem contrato JSON de linha única,
consome o valor diretamente. É a mesma divisão que `ensure_workflow.resolve_workflow`
já mantém, e existe pela mesma razão.

`GoalResult` é um `NamedTuple` com `status`, `path`, `content`, `reason`
(ver `data-model.md` §E3).

### Uso como CLI

```bash
python3 plugin/skills/grill-with-docs/scripts/ensure_goal.py --ensure ROOT
```

Emite **uma** linha JSON com chaves ordenadas:

```json
{"path":"/abs/root/goal.md","sha256":"<hex>","status":"CREATED","version":"v1"}
```

Bloqueado:

```json
{"reason":"unsafe target","status":"BLOCKED"}
```

Códigos de saída: `0` para `CREATED`, `REUSED` e `PRESERVED`; `2` para
`BLOCKED`.

`PRESERVED` sai `0` porque não é falha do comando — o comando fez exatamente o
que devia, que é não tocar em arquivo alheio. O que distingue os casos é o
`status`, não o exit code (FR-003).

### Precondições verificadas antes de qualquer escrita

| Condição | Resultado |
|---|---|
| `ROOT` não é diretório existente | `BLOCKED`, `ROOT must be existing Git top-level` |
| `ROOT` não é o topo de um repositório Git | `BLOCKED`, `ROOT must be existing Git top-level` |
| `<root>/goal.md` é symlink | `BLOCKED`, `unsafe target` |
| `<root>/goal.md` resolve para fora de `<root>` | `BLOCKED`, `unsafe target` |
| `<root>/goal.md` existe e é diretório | `BLOCKED`, `unsafe target` — não removido, nada escrito dentro |
| Template embutido não casa o próprio contrato | `BLOCKED`, `invalid bundled template` |

A verificação do template contra o próprio contrato não é redundante: é o que
impede que um bundle corrompido materialize um documento não conforme na raiz de
um projeto consumidor e o declare `CREATED`.

### Algoritmo de criação (FR-002, FR-015)

```text
1. mkstemp no MESMO diretório do destino
2. write(bytes do template) + flush + fsync
3. os.link(temporário, destino)
     sucesso        → created = True
     FileExistsError → created = False   ← alguém venceu a corrida; não é erro
4. fsync do diretório (best-effort; indisponível em alguns filesystems)
5. unlink do temporário, sempre
6. reverificar symlink/contenção do destino
7. ler de volta por descritor (O_NOFOLLOW, S_ISREG)
8. validar marcador e compatible() sobre os bytes lidos
9. status = CREATED se created e validou; REUSED se não created e validou;
            PRESERVED se não validou; BLOCKED se a releitura falhou
```

O no-clobber é **estrutural**, não uma checagem: `os.link` recusa um destino
existente no próprio kernel. Um `if not exists(): write()` teria janela entre o
teste e a escrita e falharia FR-015 sob concorrência real.

O temporário é criado no mesmo diretório do destino porque `os.link` não
atravessa sistemas de arquivos.

### Leitura segura

Todo `read` passa por descritor aberto com `O_RDONLY | O_CLOEXEC | O_NOFOLLOW`,
com `S_ISREG` verificado sobre o `fstat` do descritor já aberto. O objeto
verificado é o objeto lido — não há janela entre checar e abrir (FR-008).

`UnicodeError` na decodificação vira `BLOCKED`, `invalid UTF-8 goal`.
`OSError` vira `BLOCKED`, `filesystem-error:<NomeDoTipo>` (FR-016).

## Superfície 2 — `grill_workspace.py init`

### Função de costura

```python
ensure_project_goal(root: Path) -> dict[str, Any]
```

Simétrica a `ensure_project_workflow`. Converte `BLOCKED` em
`CliFailure(EXIT_BLOCKED, "BLOCKED", "GOAL-UNAVAILABLE", reason)` e devolve o
bloco do payload nos demais casos.

### Ordem dentro de `init_command`

```text
validar identidade
ensure_project_workflow(root)      ← já existe
ensure_project_goal(root)          ← NOVO, imediatamente após
dependency_report(...)
backlog_report(...)  [se não --skip-backlog]
...montagem do bundle
```

O `goal` vem logo após o `workflow` e **antes** das dependências porque é
fixação de artefato project-wide, não detecção de ambiente: agrupa com o que
lhe é semelhante, e um `GOAL-UNAVAILABLE` aparece antes de o comando gastar
trabalho com toolchain.

### Bloco no payload

```json
{
  "status": "CREATED",
  "work_id": "feature-exemplo-<hex>",
  "path": "/abs/.grill/work-items/feature-exemplo-<hex>",
  "fingerprint": "<hex>",
  "constitution": "CREATED",
  "constitution_sha256": "<hex>",
  "workflow": { "path": "WORKFLOW.md", "sha256": "<hex>", "status": "CREATED" },
  "goal":     { "path": "goal.md", "sha256": "<hex>", "status": "CREATED", "version": "v1" },
  "dependencies": { "...": "..." }
}
```

Em `PRESERVED`, o bloco carrega `reason` e o `sha256` é o do documento
**preexistente** — é o que permite detectar depois que ele mudou:

```json
{"goal": {"path": "goal.md", "reason": "human document", "sha256": "<hex>", "status": "PRESERVED"}}
```

`version` é omitido quando o documento preservado não tem marcador.

### Bloco em `state.json`

`state_template` grava, ao lado de `constitution` e `workflow`:

```json
{"goal": {"path": "goal.md", "sha256": "<hex>", "status": "CREATED"}}
```

O `sha256` é dos bytes lidos de volta do disco, nunca do template em memória
(FR-005, SC-004).

Gravado apenas no `state.json` que esta execução cria. Bundle reencontrado não é
reescrito para recebê-lo — ver `data-model.md` §E4.

**Fora de escopo, explicitamente**: o bloco `goal` **não** entra em
`WORK-ITEM.json`. Aquele documento é identidade imutável selada; um artefato que
pode ser legitimamente editado não pertence a ele.

### Efeito sobre `preflight`

Nenhum nesta entrega. `preflight` continua reportando `workflow` e
`dependencies`. Os requisitos falam da **criação de work item**; estender o
`preflight` é acréscimo defensável mas não pedido, e entraria como escopo não
solicitado.

## Vocabulário de estado — tabela única

| Token | Significado | Exit code do CLI | É sucesso? |
|---|---|---|---|
| `CREATED` | O documento nasceu nesta execução. | 0 | sim |
| `REUSED` | Já existia e casa o contrato. Nada foi escrito. | 0 | sim |
| `PRESERVED` | Já existia e **não** casa o contrato. Bytes intactos. O consumidor **não** tem o documento gerenciado. | 0 | não |
| `BLOCKED` | Impedimento nomeado. Nada foi escrito. | 2 | não |

Três valores distinguíveis sem interpretar prosa, como FR-003 exige. `PRESERVED`
é o que exige atenção de leitura: sai `0`, mas significa que o consumidor
continua sem o documento até agir.
