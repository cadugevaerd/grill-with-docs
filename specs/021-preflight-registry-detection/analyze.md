# Analyze: Detecção de extensão pelo registro

**Date**: 2026-08-20 · Não destrutivo. Consistência entre `spec.md`, `plan.md`, `tasks.md` e o código existente.

## Consistência entre artefatos

| Verificação | Resultado |
|---|---|
| Toda FR tem cenário de aceitação | OK — mapa em `checklists/requirements.md` |
| Todo item da checklist de aceitação tem task | OK — A→T001/T003/T008, B→T004, C→T005/T006/T007, D→T012, E→T009/T010/T011, F→T008 |
| Toda task tem FR de origem | OK |
| Escopo do plano ⊆ escopo do ROADMAP FASE-001 | OK |
| Decisões do plano ⊆ ADR-0001..0004 | OK — nenhuma decisão nova introduzida em `plan.md` |

Sem contradição entre artefatos. Nenhum `[NEEDS CLARIFICATION]` pendente.

## Achado 1 — a suíte validava o parser contra um mundo que não existe

`tests/validate_dependencies_contract.py:178-189` alimenta o parser assim:

```python
("/stub/specify", "extension", "list"): (0, "git (v1.0.0)\nverify-review-ship (v0.4.2)\n"),
```

Texto limpo, sem escape ANSI, com o slug no início da linha. Contra essa entrada o `re.findall` funciona — e o teste passa. A saída real do `specify 0.15.1` é `\x1b[2mgit\x1b[0m` numa linha indentada, e contra ela o mesmo código produz `2mgit`.

**Este é o motivo de o defeito ter sobrevivido a uma suíte de 1066 testes.** A fixture era mais limpa que a realidade, então o teste confirmava o parser em vez de exercitá-lo. Vale registrar como aprendizado da fase, não só como teste a reescrever: fixture sintetizada à mão tende a herdar as suposições do código que ela deveria desafiar.

Consequência para o plano: **T009 não é "atualizar validadores"**, é reescrever três testes que codificam o comportamento antigo:

- `test_extensions_are_missing_without_specify_and_never_probe_it` — a premissa muda: sem `specify` a detecção continua possível, porque o registro é um arquivo. O teste passa a afirmar que o caminho de extensão **nunca** chama `run`.
- `test_extension_list_is_read_once_and_empty_state_is_not_a_match` — não há mais "ler a lista uma vez"; vira "o registro é lido uma vez".
- `test_installed_extension_is_detected` — reescrito sobre fixture de registro. **Deve ganhar o caso adversarial** que faltava: descrição contendo o slug de uma extensão não instalada (A3).

## Achado 2 — `spec-kit-community-catalog` tem ordenação testada; o registro precisa da mesma

`test_trusted_catalog_is_installed_before_the_community_extensions` fixa que o catálogo vem antes dos `ext:*` no manifest. O registro (T002) precisa de garantia equivalente, senão a causa raiz apareceria depois das consequências no relatório ordenado — exatamente o que ADR-0002 quer evitar. Acrescentar asserção de ordem, não só de presença.

## Achado 3 — `kind: path` não valida conteúdo estrutural

O ramo `path` de `detect()` só faz `target.exists()` e `contains` como substring. Sem T007, um registro com `schema_version: "2.0"` ficaria `present` enquanto os `ext:*` ficam `undetermined` — relatório internamente incoerente, e a incoerência apontaria para o lado errado (sugere que o registro está bom).

T007 é, portanto, **necessária e não opcional**. Risco de omiti-la: alto, porque o caso só aparece quando o spec-kit mudar de schema, isto é, no futuro e longe deste contexto.

## Achado 4 — `--allow-install` sobre indeterminação

`install()` itera `pending = [report["id"] for report in reports if report["status"] != "present"]`. Sem T006, `undetermined` entra em `pending` e `--allow-install` executaria `specify extension add` para extensões cujo estado não foi observado — instalando por cima do que talvez já esteja instalado. É C8, e é o modo de falha mais caro do conjunto, porque muta o ambiente do operador a partir de uma não-observação.

## Riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| Contrato interno do spec-kit muda o formato do `.registry` | Média | `schema_version` verificado antes do conteúdo; mudança vira `undetermined`, não falso negativo (C3) |
| `undetermined` adicionado a `grill-dependencies/v1` sem bump do schema | Baixa | Aceito e nomeado em ADR-0004; `missing_required` usa `!= "present"`, então consumidor de bloqueio não quebra; E3 cobre o resto |
| Correção cosmética passar como completa | **Alta** | A3 e A4 reprovam patch que só remove ANSI — é o guarda-chuva principal desta fase |
| D2 não reproduzível no CI | Média | Declarada manual em `tasks.md`; a matriz não tem `specify` por decisão de projeto |

## Dependências externas

Nenhuma nova. A mudança **remove** a dependência de invocar `specify` no caminho de detecção; `Toolchain` continua para binários.

## Veredito

Pronto para `agent-assign`. Nenhum bloqueio. Duas correções incorporadas ao escopo por este passo: T009 reclassificada de "atualizar" para "reescrever com caso adversarial", e asserção de ordem do manifest acrescentada a T002.
