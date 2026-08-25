# Fechamento retroativo — bootstrap declarado

Quatro etapas deste work item foram concluídas **depois** de o artefato de cada
uma existir, e não no momento em que o trabalho aconteceu. Este documento diz
por quê, para que uma auditoria futura encontre a razão em vez de reconstruí-la.

## O que aconteceu

Este work item entrega o emissor da cadeia de atestação. Enquanto ele não
existia, nenhuma etapa de nenhum work item podia ser concluída por checkpoint —
o núcleo exigia a cadeia, sabia julgá-la, e nada no sistema sabia cunhá-la.
Inclusive as etapas deste próprio work item.

A ordem foi: implementar o emissor, depois usá-lo para fechar as etapas cujos
artefatos já estavam escritos e commitados.

## Por que isso não é carimbo

O emissor lê o artefato no momento da emissão e sela o digest dos bytes que
encontrou. As quatro cadeias foram cunhadas sobre arquivos que já existiam no
repositório, e cada uma passou pelo mesmo juiz que qualquer etapa futura vai
enfrentar — `judge_checkpoint_attestation`, sem exceção, sem caminho especial.

O que a cadeia afirma é verdadeiro sobre cada uma:

| Etapa | Artefato | Digest selado |
|---|---|---|
| `specify` | `specs/026-attestation-emitter/spec.md` | `sha256:0d4279…` |
| `plan` | `specs/026-attestation-emitter/plan.md` | `sha256:ab0ca2…` |
| `checklist` | `specs/026-attestation-emitter/checklists/requirements.md` | selado na emissão |
| `tasks` | `specs/026-attestation-emitter/tasks.md` | selado na emissão |

Alterar qualquer um desses arquivos agora quebra a correlação, exatamente como
quebraria numa etapa fechada em tempo real.

## O que continua não sendo provado

Que a skill registrada foi executada. Vale para estas quatro etapas e para
qualquer outra: a garantia é estrutural por desenho, e está declarada em
`SKILL.md` e em `specs/026-attestation-emitter/contracts/emission.md`.

## O desvio que não foi o bootstrap

Separado e registrado à parte: a fundação do emissor foi implementada antes de
`specify`, `plan` e `tasks` existirem. Isso é desvio de ordem, não consequência
do bootstrap — ADR-0204 previu implementar antes de **atestar**, nunca antes de
**planejar**. Está no `Complexity Tracking` de `specs/026-attestation-emitter/plan.md`
e no checkpoint que o registrou.

## Alcance

Esta exceção vale para este work item e só para ele. Um emissor já existe: o
próximo work item fecha suas etapas na ordem normal, sem nada retroativo.

## Achado: duas cadeias divergem, e isso é o mecanismo funcionando

A verificação da wave-0003 encontrou que o digest selado para `tasks` e para
`analyze` não corresponde mais aos bytes de
`specs/026-attestation-emitter/tasks.md`.

A causa é minha, e está no histórico: depois de fechar essas duas etapas, editei
`tasks.md` duas vezes — para fechar as lacunas de rastreabilidade que o
`analyze` apontou, e para corrigir o nome do resolvedor citado em T011. As duas
edições foram legítimas em conteúdo e ilegítimas em momento.

**Não corrigi silenciosamente.** As cadeias continuam selando o que era verdade
quando foram emitidas, e a divergência é a informação correta: houve edição
posterior, e ela é detectável. Apagar isso reescrevendo as cadeias seria
transformar a evidência em enfeite.

### O que isto revela sobre o desenho

O núcleo não oferece caminho de re-atestação. Uma etapa `complete` não volta a
`in-progress` — `INVALID-TRANSITION` —, então um artefato que precise de edição
legítima depois de atestado deixa a cadeia divergente para sempre, sem forma
de reconciliar.

Isso não é defeito do emissor entregue aqui; é lacuna do contrato de checkpoint,
que só descobri por usar o mecanismo em cima do próprio trabalho. Registrado em
BL-0201.

### Estado das seis cadeias

| Etapa | Artefato | Digest |
|---|---|---|
| `specify` | `spec.md` | corresponde |
| `plan` | `plan.md` | corresponde |
| `checklist` | `checklists/requirements.md` | corresponde |
| `tasks` | `tasks.md` | **diverge** — editado após o selo |
| `analyze` | `tasks.md` | **diverge** — mesmo artefato |
| `partition` | `execution-dag.json` | corresponde |
