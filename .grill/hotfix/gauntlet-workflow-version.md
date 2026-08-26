# Evidência constitucional — hotfix `gauntlet-workflow-version`

Nenhuma cláusula é dispensada, enfraquecida ou reinterpretada por este hotfix.

## Evidência antes de afirmação

A divergência foi medida diretamente sobre o `WORKFLOW.md` deste repositório,
não inferida:

```text
marcador do documento: v4
workflow_v3.execution_gate(texto) -> Gate(status='BLOCKED', code='WORKFLOW_INCOMPATIBLE',
    missing=('agent-assign', 'agent-execute', 'workflow-step-skills.json',
             'canonical-external-step-order'))
workflow_v4.execution_gate(texto) -> Gate(status='OK', code=None, missing=())
```

Reprodução pelo CLI publicado:

```text
$ grill_workspace.py gauntlet-init . --work-id <ID> --max-workers 3
{"code":"WORKFLOW-INCOMPATIBLE","error":"workflow is not eligible for Gauntlet activation","verdict":"BLOCKED"}
```

## Fail-closed sem waiver

A correção **despacha por versão declarada**: cada documento passa a ser julgado
pela tupla `ESSENTIAL` da versão que ele próprio declara no marcador. Nenhum gate
é afrouxado, nenhuma substring é removida de nenhuma tupla, e um documento v3
continua sendo julgado por v3. Um documento sem marcador continua indo para v3,
que é o comportamento atual.

## Sequência obrigatória do desenvolvimento

O defeito torna `implement-parallel` inalcançável em todo projeto v4, o que
impede a sequência de ser cumprida sem saltos. Corrigi-lo restaura a sequência;
não a contorna.

## Work item isolado e ownership

O hotfix tem work item próprio, com identidade imutável e escopo fechado em três
caminhos declarados.

## Bump obrigatório do plugin

A correção altera `plugin/**`, logo exige bump SemVer de `4.0.1` para `4.0.2`,
sincronizado nos oito lugares travados por `tests/validate_distribution.py`,
antes de qualquer merge ou push. O bump faz parte deste hotfix, não de uma
entrega posterior.

## Release obrigatória por versão

A release de `4.0.2` é criada pelo pipeline no merge para `main`, ancorada no
mesmo commit da tag imutável. Nenhuma release é criada à mão.

## Rastreabilidade

Teste de correção: `tests/validate_gauntlet_workflow_version_contract.py`.
Achado originado durante a etapa `partition` do work item
`feature-goal-autopilot-6f0eaefce4064eebb6bc16d5734bee0c`, que ficou bloqueado
por ele.
