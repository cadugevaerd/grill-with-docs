# Research — FASE-001, destravar a ponte com o backlog operacional

Nenhum marcador `NEEDS CLARIFICATION` sobreviveu à especificação. As lacunas do enunciado já tinham decisão registrada na sessão de entrevista que originou a fase. Este documento consolida o que foi medido, para que a implementação não precise redescobrir.

## D1 — Por que `backlog-sync` recusa todo work item com artefato escrito

**Decision**: em `backlog_sync_command`, substituir `validate_bundle_integrity(bundle)` por `validate_metadata(bundle.metadata, args.work_id)`.

**Rationale**: `validate_bundle_integrity` (`grill_workspace.py:804`) compara o hash de cada arquivo vivo contra `initial_artifacts`, que é o retrato dos templates no instante do `init`. Escrever uma decisão adiada em `DECISION-BACKLOG.md` altera esse arquivo, logo invalida o pino. Como o espelho só tem serviço quando há decisão escrita, a pré-condição e a utilidade do comando são mutuamente exclusivas. Medido: os três work items existentes retornam `{"code":"BUNDLE-INTEGRITY","verdict":"BLOCKED"}`, e o pino de `DECISION-BACKLOG.md` do work item `feature-gauntlet-loop` diverge do vivo (`0ead85c2` contra `f89eaf9b`).

A garantia que importa preservar é outra: que o bloco imutável não foi adulterado. Isso é exatamente o que `validate_metadata` verifica, via `immutable_sha256`. A ponte crua, chamada sem o wrapper, já opera assim e responde `PREVIEW` normalmente — foi por ela que a única decisão espelhada até hoje passou.

**Alternatives considered**:
- Recalcular `initial_artifacts` a cada escrita: destruiria a propriedade tamper-evident que o campo existe para dar.
- Excluir `DECISION-BACKLOG.md` do conjunto pinado: resolveria só este comando e deixaria a mesma armadilha para qualquer futuro leitor de artefato mutável.

## D2 — Por que decisões encerradas nunca chegam ao backlog

**Decision**: remover o filtro de estado em `parse_deferred` e devolver toda decisão, carregando o estado lido.

**Rationale**: `backlog_bridge.py:150` descarta qualquer entrada cujo `state` não seja `open`. O auditor, em `audit_decisions.py:623`, reprova fase `ready` com decisão aberta, e em `:615` reprova milestone terminal com decisão aberta. As duas regras somadas fazem a janela em que há algo a espelhar coincidir exatamente com a janela em que o trabalho está bloqueado. Fechar o marco exige resolver tudo; resolvido, o espelho vira no-op permanente. É a explicação de 1 registro espelhado em 8.

**Alternatives considered**:
- Espelhar só no momento do bloqueio, via gate: manteria o acoplamento entre estar bloqueado e ser espelhável, que é a causa e não o sintoma.

## D3 — Mapa de estados contra a FSM real

**Decision**: item nasce em `in_progress`; decisão `resolved` transiciona para `done`; decisão `superseded` transiciona para `cancelled`. Os estados `open` e `merged` do backlog não são usados pela ponte.

**Rationale**: a FSM foi medida exaustivamente, os 25 pares, com `backlogctl 2.4.0` em banco descartável:

| de \ para | open | in_progress | done | cancelled | merged |
|---|---|---|---|---|---|
| **open** | ok | ok | **não** | ok | não |
| **in_progress** | ok | ok | ok | ok | não |
| **done** | não | não | ok | não | ok |
| **cancelled** | ok | não | não | ok | não |
| **merged** | não | não | não | não | ok |

`open → done` é ilegal, o que refuta o mapa ingênuo. Nascer em `in_progress` torna `resolved → done` e `superseded → cancelled` transições legais e diretas, de um passo, sem gravar nenhum estado que não ocorreu. Verificado que `item add --status in_progress` é aceito, porque `--status` no `add` é snapshot inicial e não transição.

**Alternatives considered**:
- Nascer em `open` e fazer `open → in_progress → done` ao resolver: grava no histórico do backlog um estado de duração nula que nunca existiu, atritando com a cláusula Evidência antes de afirmação.
- `item reconcile-status`, único caminho que ignora a FSM: exige `--confirm` e a documentação do próprio backlog o proíbe como transição normal ou atalho de migração. Descartado por contrato, não por gosto.

Registrado em ADR-0003.

## D4 — Deduplicação é responsabilidade da ponte

**Decision**: indexar por `(work_id, BL-NNNN)` lidos dos marcadores da `description`, e usar o índice tanto para evitar recriação quanto para reconciliar o estado de um item existente.

**Rationale**: verificado que o armazenamento aceita duplicata sem erro — um `item add` repetido com título e descrição idênticos criou um segundo item. Não há guarda no backlog, então um espelho que só cria produz itens repetidos a cada execução. O código atual já monta um conjunto `known` a partir dos marcadores, mas descarta a identidade do item; para reconciliar estado é preciso guardar também o `id` e o `status` atual.

O vínculo permanece nos marcadores dentro de `description` porque é o único lugar disponível: o shape documentado de `item add` é `--code --title --description [--status] [--criticality] [--category] [--due-at]`, as flags são command-scoped, e não existe campo estruturado de referência externa.

**Alternatives considered**:
- Guardar o mapa no bundle do work item: criaria uma segunda autoridade, capaz de divergir do backlog, contrariando a direção decidida em ADR-0001.
- Deduplicar por título: frágil, e colide entre work items que compartilham o mesmo identificador local de decisão.

## D5 — Como cobrir sem `backlogctl` real

**Decision**: usar os dois seams já existentes em `tests/validate_backlog_contract.py`.

**Rationale**: `StubToolchain` grava cada chamada e responde por tabela roteirizada por prefixo de argumentos, o que permite afirmar sobre o comando emitido, não só sobre o resultado. `MODULE.resolve_cli` é substituível, o que dispensa qualquer binário no PATH. A matriz roda em três sistemas e duas versões de Python sem `backlogctl` instalado, e isso é premissa fixa do projeto.

Para o caminho que passa por `grill_workspace.py backlog_sync_command`, o teste precisa de um bundle real em diretório temporário, com artefato escrito depois da criação, para provar que o gate trocado deixa de reprovar.

**Alternatives considered**:
- Testar contra um `backlogctl` real em CI: proibido pela restrição de ambiente e tornaria a suíte dependente de rede e de instalação de terceiro.
