# Data Model: Materialização e validação do goal.md

**Fase 1** | **Data**: 2026-08-26 | **Spec**: [spec.md](./spec.md)

Entidades derivadas da seção *Key Entities* da spec. Nenhuma delas é persistida
num banco: duas vivem em código congelado, uma no sistema de arquivos do projeto
consumidor e uma no `state.json` do bundle.

## E1 — Contrato do documento (`GoalDocumentContract`)

Constantes de módulo em `grill_core/goal_document.py`. É o SSOT exigido por
FR-009 e FR-010, e o único lugar do repositório onde o conjunto aparece
declarado (SC-006).

| Campo | Tipo | Valor | Regra |
|---|---|---|---|
| `VERSION` | `str` | `"v1"` | Versão do contrato do documento. Independente da versão publicada do plugin (FR-011). |
| `MARKER` | `str` | `"grill-with-docs-goal:v1"` | Marcador que identifica o documento gerenciado. |
| `ESSENTIAL` | `tuple[str, ...]` | ver contrato | Substrings cuja presença define conformidade. Literal congelado. |
| `TEMPLATE` | `Path` | `assets/GOAL.template.md` | Bytes a materializar. |

**Invariantes**

- `ESSENTIAL` é um literal congelado. Nunca é derivada da tupla de outro
  documento, de outra versão, nem computada a partir dos headings do template.
  Derivá-la do template faria um template mutilado validar-se a si mesmo.
- Acrescentar um item à tupla marca como divergente todo `goal.md` já
  materializado em projeto consumidor, de uma vez e sem migração. Uma mudança de
  contrato é `v2` **ao lado** de `v1`, com marcador novo e tupla nova — nunca uma
  edição de `v1`.
- Nenhum outro módulo redeclara qualquer um destes valores (FR-010).

**Operação pura exposta**

```text
compatible(text: str) -> bool
    Verdadeiro quando text não é vazio e toda substring de ESSENTIAL está
    presente. Não impõe ordem e não proíbe conteúdo adicional (FR-014).

managed_version(text: str) -> str | None
    A versão declarada pelo marcador, ou None quando não há marcador.
```

Ambas operam sobre texto já lido. O módulo não abre arquivo, não importa
`grill_workspace` e não toca disco — é o que permite ao validador exercitá-las
sem sistema de arquivos.

## E2 — Documento gerenciado (`goal.md`)

O arquivo na raiz do projeto consumidor.

| Atributo | Regra |
|---|---|
| Caminho | `<root>/goal.md`, exatamente. Nunca em subdiretório. |
| Primeira linha | Carrega `MARKER` (FR-011). |
| Tipo | Arquivo regular. Symlink é recusado, não seguido (FR-008). |
| Codificação | UTF-8. Falha de decodificação vira estado bloqueado nomeado. |
| Mutabilidade pelo core | Nenhuma após a criação. O core nunca reescreve, renomeia ou faz backup (FR-002, FR-006, FR-007). |

## E3 — Estado da fixação (`GoalResult`)

O valor que o resolvedor devolve, desacoplado de como é reportado — mesma forma
que `WorkflowResult` em `ensure_workflow.py`.

| Campo | Tipo | Significado |
|---|---|---|
| `status` | `str` | Um de `CREATED`, `REUSED`, `PRESERVED`, `BLOCKED`. |
| `path` | `Path \| None` | Caminho do documento; `None` quando bloqueado. |
| `content` | `bytes` | Bytes lidos de volta do disco; vazio quando bloqueado. |
| `reason` | `str \| None` | Motivo nomeado; preenchido apenas em `BLOCKED` e `PRESERVED`. |

**Transições** — decididas por uma única leitura do estado do disco, sem janela
entre teste e escrita:

```text
não existe            → cria atomicamente → lê de volta → CREATED
                                          → colisão na criação → relê → REUSED | PRESERVED
existe, é symlink                                              → BLOCKED  (unsafe target)
existe, é diretório                                            → BLOCKED  (unsafe target)
existe, não é regular                                          → BLOCKED  (unsafe target)
existe, marcador v1, compatible()                              → REUSED
existe, marcador v1, não compatible()                          → PRESERVED (incompatible goal)
existe, marcador de outra versão                               → PRESERVED (managed version mismatch)
existe, sem marcador                                           → PRESERVED (human document)
existe, vazio                                                  → PRESERVED (incompatible goal)
raiz não gravável / erro de I/O                                → BLOCKED  (filesystem-error:<Tipo>)
```

**Invariantes**

- `PRESERVED` **nunca** é sucesso e nunca é confundível com `REUSED` sem ler
  prosa (FR-003). São tokens distintos no mesmo campo `status`.
- Em `PRESERVED`, os bytes do arquivo preexistente permanecem idênticos
  byte a byte (FR-006, SC-002), e nenhum arquivo novo é criado em lugar algum
  (FR-007).
- `CREATED` só é emitido quando a criação atômica venceu a corrida **e** o
  read-back valida. Perder a corrida para outra execução concorrente é `REUSED`,
  não erro (FR-015, SC-003).
- `content` é sempre o que foi lido do disco depois da escrita, nunca o template
  em memória (FR-005).

## E4 — Registro no work item

Bloco `goal` gravado em `.grill/work-items/<work_id>/state.json`, ao lado dos
blocos `constitution` e `workflow` que já existem.

| Campo | Tipo | Regra |
|---|---|---|
| `path` | `str` | Relativo à raiz: `"goal.md"`. |
| `sha256` | `str` | SHA-256 dos bytes lidos de volta do disco (FR-004, FR-005, SC-004). |
| `status` | `str` | O mesmo token de E3. |

**Alcance**: o bloco é gravado no `state.json` que a execução **cria**. Um work
item preexistente, que a execução apenas reencontra, não é reescrito para
recebê-lo: aquele estado foi selado por outra execução, e mutá-lo mudaria o
fingerprint de um bundle que ninguém pediu para alterar. A fixação continua
reportada no retorno (E5).

**Invariante de escopo**: o bloco `goal` **não** entra em `WORK-ITEM.json`.
`constitution` e `workflow` são identidade imutável selada — alterá-las invalida
o work item. O `goal.md` é artefato project-wide que o item reporta, não âncora
que ele sela; colocá-lo em `immutable` faria toda edição legítima do documento
matar work items vivos.

## E5 — Relatório do `init`

Bloco `goal` no payload JSON de `init_command`, irmão de `workflow`.

```json
{
  "goal": { "status": "CREATED", "path": "goal.md", "sha256": "<hex>", "version": "v1" }
}
```

| Campo | Regra |
|---|---|
| `status` | Token de E3. `PRESERVED` acompanha `reason`. |
| `path` | `"goal.md"`. |
| `sha256` | Hex dos bytes no disco. Em `PRESERVED`, é o hash do documento **preexistente** — é o que permite detectar depois que ele mudou. |
| `version` | A versão do marcador efetivamente lida, não a de bootstrap. Ausente quando o documento preservado não tem marcador. |
| `reason` | Presente apenas em `PRESERVED`. Nomeia por que o documento não casa o contrato. |

`BLOCKED` não aparece neste bloco: é convertido em `CliFailure` com código
`GOAL-UNAVAILABLE` antes de o payload existir, simétrico a `WORKFLOW-UNAVAILABLE`
(FR-016).

## Relação entre as entidades

```text
GoalDocumentContract  (E1, congelado em grill_core)
        │  lido por
        ├────────────► ensure_goal.resolve_goal() ──► GoalResult (E3)
        │                                                  │
        │                                                  ├──► goal.md na raiz (E2)
        │                                                  ├──► bloco em state.json (E4)
        │                                                  └──► bloco no payload do init (E5)
        │  lido por
        └────────────► tests/validate_goal_document_contract.py
```

Uma seta de leitura, nunca de cópia: nenhum consumidor redeclara o contrato.
