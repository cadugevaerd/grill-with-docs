# Research: Versão de workflow derivada do documento

**Phase**: 0 | **Date**: 2026-08-22 | **Spec**: [spec.md](./spec.md)

Insumo: `PLAN-CONTEXT.md`, `ADR-0001` e `ADR-0002` do work item `fix-audit-workflow-version-2a9e7a7ba01f42dcb24b3bb83d801b03`. Nenhum `NEEDS CLARIFICATION` entrou nesta fase — as cinco decisões abertas foram fechadas na entrevista. O que segue são achados novos, levantados na leitura do código durante o planejamento, e as decisões que eles obrigaram.

## R1 — `state_template` é o único ponto de mutação, e tem dois chamadores

**Decisão**: aplicar a derivação exclusivamente em `state_template` (`grill_workspace.py:687`).

**Rationale**: `initial_files` (`:695`) é a única função que escreve `state.json`, e é chamada de dois lugares — `init` (`:1434`) e `migrate` (`:2142`). Ambos passam pelo mesmo `state_template`, então uma única alteração cobre os dois writers. Não existe terceiro caminho de escrita do campo.

**Alternativas consideradas**: alterar cada chamador. Rejeitada — duplicaria a regra e deixaria o próximo writer livre para esquecê-la.

## R2 — A versão **não** entra em `immutable.workflow`

**Decisão**: resolver o marcador dentro de `state_template`, sem tocar `workflow_info()` (`:645`) nem `immutable_metadata()` (`:672`).

**Rationale**: `immutable["workflow"]` é serializado em `WORK-ITEM.json` e selado por `immutable_sha256`. Duas consequências matam a ideia de acrescentar `version` ali:

1. `work_item_v3.rebind_workflow_bundle` (`work_item_v3.py:1062`) reescreve `immutable["workflow"]["sha256"]` e nada mais. Um campo `version` ao lado ficaria obsoleto no rebind — exatamente a classe de defeito que este trabalho existe para eliminar, reintroduzida num lugar selado onde é mais caro corrigir.
2. Mudar o conjunto de chaves de `immutable.workflow` muda a construção do hash imutável para bundles novos, e `work_item_v3.require_v3` (`:275`) valida essa estrutura.

`state_template` já recebe `root`, então tem tudo de que precisa sem alargar a superfície selada.

**Alternativas consideradas**: `workflow_info()` devolver `version` e `state_template` apenas espalhar. Rejeitada pelos dois motivos acima — o valor vazaria para `immutable` por construção.

## R3 — Os dois campos têm domínios diferentes, e a diferença é real

**Achado**: `ACCEPTED_WORKFLOW_MARKERS` é `("v2", "v3", "v4")` (`audit_decisions.py:70`), mas `SEQUENCE_BY_VERSION` (`grill_workspace.py:2162`) só tem `v3` e `v4`. `development_workflow_version()` (`:2169`) devolve `None` para qualquer declaração fora desse mapa. Derivar cegamente o marcador para os dois campos faria um documento v2 produzir `development.workflow_version: "v2"` → `None` → bundle sem camada de desenvolvimento reconhecível, que é pior do que o estado atual.

**Decisão**: os dois campos derivam do mesmo marcador, com **uma equivalência documentada**: marcador `v2` produz `state.workflow.version: "v2"` e `development.workflow_version: "v3"`.

**Rationale**: os dois campos respondem perguntas diferentes, e a docstring de `development_workflow_version` já diz qual é a dela — *"which workflow version a development block speaks"*, não qual versão o documento é. v2 e v3 **falam a mesma sequência**: `WORKFLOW_SEQUENCE_BY_MARKER` (`audit_decisions.py:72`) lista as duas com tupla idêntica de onze passos. A equivalência já é precedente no próprio código: `DEVELOPMENT_SCHEMAS = {"grill-development/v1": "v3", ...}` (`:2161`) mapeia o schema que antecede o campo para v3 pelo mesmo raciocínio. Sob a semântica real do campo, `"v3"` para um documento v2 é verdadeiro, não aproximação.

**Alternativas consideradas**:

- **Acrescentar `"v2"` a `SEQUENCE_BY_VERSION` com tupla literal própria.** Tecnicamente o mais limpo — igualaria os domínios dos dois campos. Rejeitada por escopo: o handoff declara fora de escopo alterar as ordens canônicas de qualquer versão de workflow, e uma tabela de sequência nova é exatamente isso. Fica como candidata a work item próprio.
- **Recusar `init` sobre documento v2.** Rejeitada: transformaria um conserto de bug em corte de suporte a uma versão gerenciada que o sistema declara aceitar, e reprovaria repositórios que hoje funcionam.

## R4 — Detector estrito: contrato e paridade

**Decisão**: `sole_managed_version(text)` em `ensure_workflow.py`, ao lado de `managed_version` (`:111`), com `re.findall` e `len(markers) == 1`. `managed_version` fica intacta.

**Rationale**: sete chamadores em `ensure_workflow` mais `workflow_v3.marker_version` (`:356`) e dois testes dependem da semântica first-match; `:335` e `:473` dependem do `or VERSION` na materialização. Ver ADR-0002.

**Paridade**: `audit_decisions.py:361` mantém a regex própria — o módulo é stdlib puro por decisão, para o veredito ser reproduzível em qualquer clone. A concordância entre os dois vira teste, sobre a matriz de R5.

## R5 — Matriz de casos e origem da fixture

**Decisão**: a matriz é `{sem marcador, um marcador v2, um v3, um v4, dois marcadores iguais, dois marcadores distintos, um marcador desconhecido (v9)}`, exercitada em `sole_managed_version`, em `audit_decisions` e no `init` ponta a ponta.

**Rationale**: FR-006 exige concordância entre criação e auditoria; só uma matriz compartilhada prova isso. FR-009 exige que o insumo seja o documento real materializado — `tests/fixtures/` já hospeda repositórios sintéticos com `.specify/` próprios, e o `WORKFLOW.md` real é obtido materializando pelo `ensure_workflow`, não escrevendo um texto à mão a partir da regex. Fixture derivada do código já deixou passar bug de parsing neste repositório.

**Nota**: "dois marcadores iguais" é caso próprio porque a regra é unicidade da declaração, não distinção de valores — `findall` conta duas ocorrências de `v4` como duas declarações.

## R6 — Onde os testes entram

**Decisão**: estender `tests/validate_workspace_contract.py` (carimbo do `init`, recusa fail-closed), `tests/validate_contract.py` (asserção de estado da auditoria) e `tests/validate_workflow_v3_contract.py` (`sole_managed_version` e paridade). Nenhum arquivo de validador novo.

**Rationale**: `tests/run_validators.py` faz glob de `validate_*.py`, então um arquivo novo entraria sozinho na suíte — mas o contrato de cada um desses três já cobre a superfície exata que muda, e espalhar a mesma regra por um quarto arquivo dificulta ver que ela é uma só.

## R7 — Invariância da frota é caso de teste, não expectativa

**Decisão**: um teste dedicado audita bundles carimbados `"v2"` sobre documento v4 e exige veredito inalterado.

**Rationale**: é a única diferença observável entre a decisão tomada (pertencimento) e a rejeitada (cross-check contra o disco). Sem esse teste, nada impede uma "melhoria" futura de reintroduzir a comparação e derrubar a frota — que é precisamente o custo recusado em ADR-0001.

## R8 — `SEQUENCE_BY_VERSION` existe duas vezes

**Achado**: `grill_workspace.py:2162` declara sua própria `SEQUENCE_BY_VERSION`, e `grill_core/workflow_versions.py:103` declara outra, descrita no `CLAUDE.md` como o SSOT tabular. As duas coincidem hoje.

**Decisão**: não unificar nesta fase; registrar o achado.

**Rationale**: unificar é mudança de tabela de sequência, fora do escopo declarado. Mas a divergência é relevante para R3: qualquer futura entrada `v2` precisaria entrar nas duas, ou o defeito volta pelo lado que não foi tocado.
