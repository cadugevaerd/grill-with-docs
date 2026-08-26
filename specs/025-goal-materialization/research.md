# Research: Materialização e validação do goal.md

**Fase 0** | **Data**: 2026-08-26 | **Spec**: [spec.md](./spec.md)

Nenhum `NEEDS CLARIFICATION` restou aberto no Technical Context. As duas decisões
estruturais já vinham seladas pela entrevista do work item
`feature-goal-materialization-c29d98e49a524ca8a482615d8d528dab` (ADR-0101 e
ADR-0102); esta fase as reconfirma contra o código e resolve as três questões
menores que o desenho de implementação levanta.

## D1 — Onde vive o SSOT do contrato

**Decisão**: marcador, versão e tupla `ESSENTIAL` do `goal.md` vivem em
`plugin/skills/grill-with-docs/scripts/grill_core/goal_document.py`.
`ensure_goal.py` é fino: importa de lá e materializa. Validador, `init` e
consumidores futuros leem do mesmo módulo.

**Racional**: já selado em ADR-0101. A 5.0.0 desfez exatamente o padrão oposto
noutro lugar da CLI — as tabelas de versão estavam duplicadas, a contradição não
era reprovada por teste nenhum e apareceu em campo como `WORKFLOW-INCOMPATIBLE`.
FR-009 e FR-010 são a forma normativa dessa lição, e SC-006 é a sua verificação:
o conjunto exigido aparece declarado em exatamente **um** lugar do repositório,
verificável por busca textual.

**Alternativas rejeitadas**: tudo em `ensure_goal.py` (simetria com
`ensure_workflow.py`, ao custo de repetir a duplicação que a 5.0.0 removeu);
tudo dentro de `grill_workspace.py` (nenhum arquivo novo, ao custo de engordar
um arquivo de 213 KB e misturar fronteira de I/O com orquestração de comando).

**Consequência aceita**: `ensure_workflow.py` permanece byte-intacto. Convergir
as duas formas é trabalho próprio, com risco próprio, e não pertence a esta
entrega. A assimetria é deliberada e ADR-0101 é onde quem for unificá-las depois
encontra o motivo.

## D2 — O que acontece com arquivo homônimo preexistente

**Decisão**: no-clobber absoluto. Arquivo existente que não case o contrato
permanece byte a byte como está e é reportado como divergente. Nunca
sobrescrever, nunca renomear, nunca criar backup.

**Racional**: já selado em ADR-0102. O custo de errar é assimétrico — falhar em
entregar o documento adia um ganho; destruir arquivo humano perde trabalho que
ninguém recupera. `WORKFLOW.md` já resolve o caso equivalente da mesma forma, e
a seção "Release and safety notes" do `WORKFLOW.md` é o contrato que esta
entrega espelha.

**Alternativas rejeitadas**: sobrescrever com backup (o backup é consolo, não
consentimento); materializar sob outro nome na colisão (dois nomes possíveis
para o mesmo contrato, e o goal loop passaria a ter de descobrir qual ler).

## D3 — Vocabulário dos três estados

**Decisão**: `CREATED`, `REUSED`, `PRESERVED` — os mesmos três tokens que o
`init` já publica para a constituição e para o `WORKFLOW.md`.

**Racional**: FR-003 exige três valores distinguíveis **sem interpretar prosa**.
Reaproveitar o vocabulário existente evita um segundo dicionário no mesmo
payload JSON, onde `constitution` já reporta `CREATED`/`PRESERVED` e `workflow`
já reporta `CREATED`/`REUSED`/`BLOCKED`. ADR-0102 fixa esta correspondência
nominalmente.

**Nota de leitura**: `PRESERVED` não é sucesso. É o estado em que o consumidor
tem um arquivo homônimo e **não** recebeu o documento gerenciado. O `init` não
resolve por ele, e o payload precisa deixar isso legível sem prosa.

## D4 — Criação atômica e recusa de symlink

**Decisão**: reusar exatamente o mecanismo de `ensure_workflow.py` —
`tempfile.mkstemp` no mesmo diretório, `write` + `fsync`, `os.link` para o
destino final, `fsync` do diretório e `unlink` do temporário. `os.link` levanta
`FileExistsError` quando o destino já existe: é aí que o no-clobber é
estrutural, e não uma checagem TOCTOU. Leitura sempre por descritor com
`O_NOFOLLOW` e `S_ISREG`.

**Racional**: FR-002 (nunca sobrescrever), FR-008 (nunca seguir symlink) e
FR-015 (duas criações concorrentes produzem um único arquivo, a segunda
reportando reuso) são satisfeitos pela mesma primitiva. Uma checagem
`if not target.exists(): write()` teria uma janela entre o teste e a escrita e
falharia FR-015 sob concorrência real.

**Alternativa rejeitada**: `open(target, "x")`. Também é exclusivo, mas escreve
direto no destino final: uma falha no meio da escrita deixa um arquivo parcial
na raiz do consumidor, que na execução seguinte seria lido como documento
divergente e preservado para sempre.

## D5 — Como a conformidade é decidida

**Decisão**: presença de todas as substrings da tupla `ESSENTIAL` no texto, mais
o marcador `grill-with-docs-goal:v1`. Sem exigir ordem, sem proibir conteúdo
adicional.

**Racional**: FR-014 é explícito, e os Edge Cases da spec cobrem os dois lados
(ordem diferente continua conforme; conteúdo extra depois continua conforme).
`ensure_workflow.compatible()` já usa exatamente `all(item in text for item in
ESSENTIAL)` e é a referência de comportamento declarada.

**Consequência aceita e declarada**: acrescentar uma substring à tupla marca
como divergente todo `goal.md` já materializado em projeto consumidor, de uma
vez e sem caminho de migração. Por isso a tupla é congelada e uma mudança de
contrato exige marcador novo — `v2` ao lado de `v1`, nunca uma edição de `v1`.
É a mesma regra que o `CLAUDE.md` deste repositório já declara para
`ESSENTIAL` do `WORKFLOW.md`.

## D6 — Onde o hash é registrado

**Decisão**: em `state.json` do bundle, num bloco `goal` com `path` e `sha256`,
ao lado dos blocos `constitution` e `workflow` que já existem.

**Racional**: FR-004 exige caminho e hash no estado do work item; FR-005 exige
que o hash corresponda aos **bytes efetivamente materializados**, não ao
conteúdo esperado. O segundo requisito é o que força o hash a ser computado do
read-back, depois da escrita, e não do template em memória. É também a diferença
que a memória do projeto registra como "par writer/reader não verifica nada":
hash derivado da fonte, e não do disco, não detecta deriva nenhuma.

**Nota de escopo**: o bloco `goal` **não** entra em `WORK-ITEM.json` ao lado de
`constitution` e `workflow`. Aqueles dois são identidade imutável selada — mudar
a constituição invalida o work item. O `goal.md` é um artefato project-wide que
o item reporta, não uma âncora que ele sela; colocá-lo em `immutable` faria toda
edição legítima do documento matar work items vivos.

## D7 — Escrita não permitida na raiz

**Decisão**: `OSError` na criação vira estado `BLOCKED` com razão nomeada,
propagada pelo `init` como `GOAL-UNAVAILABLE`, no mesmo formato que
`WORKFLOW-UNAVAILABLE` já usa.

**Racional**: FR-016 exige falhar nomeando o impedimento, nunca prosseguir como
se tivesse fixado. `ensure_project_workflow` já converte `BLOCKED` em
`CliFailure(EXIT_BLOCKED, "BLOCKED", "WORKFLOW-UNAVAILABLE", reason)`; o par é
simétrico e não inventa vocabulário novo.

## D8 — Alcance do bump

**Decisão**: bump SemVer MINOR, sincronizado nos oito lugares que
`tests/validate_distribution.py` trava.

**Racional**: FR-017 e a cláusula constitucional **Bump obrigatório do plugin**.
A entrega acrescenta comportamento sem redefinir nem remover nada existente —
`init` passa a fixar um artefato a mais e a reportar um bloco a mais no payload.
Nenhum consumidor que não mude nada é afetado, logo MINOR e não MAJOR.

## Referências consultadas

- `plugin/skills/grill-with-docs/scripts/ensure_workflow.py` — referência de
  comportamento para materialização, leitura segura e vocabulário de estado.
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py:1133-1140`
  (`ensure_project_workflow`) e `:1403-1460` (`init_command`) — ponto de
  inserção.
- `plugin/skills/grill-with-docs/assets/GOAL.template.md` — o documento a
  transportar, entregue pelo work item `feature-goal-autopilot` e não reaberto
  aqui.
- ADR-0101 e ADR-0102 do work item.
- `.specify/memory/constitution.md` v2.1.0 — cláusulas **Bump obrigatório do
  plugin**, **Evidência antes de afirmação** e **Fail-closed sem waiver**.
