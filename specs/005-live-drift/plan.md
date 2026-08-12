# Plan: Deriva viva precisa

**Spec**: `spec.md` · **ADR**: ADR-0002

## Onde mora

`grill_status.py:87` — uma linha, um `or`, dois operandos de naturezas diferentes:

```python
if immutable.get("branch") != lv["branch"] or immutable.get("head") != lv["head"]: findings.append("LIVE-VS-RECORDED")
```

`state` já está carregado em `item_payload` desde `:70`, e carrega `status` e `milestone_status`. A informação necessária está toda em escopo; não é preciso ler mais nada.

## Decisões de desenho

1. **A metade de commit sai por completo, não vira campo novo.** A saída já expõe `recorded.head` e `locations[0].head`; quem quiser a diferença calcula. Criar um campo de deriva informativa seria inventar consumidor que não existe.
2. **Terminal é lido de `state`, a mesma fonte do auditor.** Duplicar a definição em outro lugar é como as duas leituras divergem. O auditor exige trabalho concluído e marco fechado; a situação usa os mesmos dois campos.
3. **Ausência de campos é não terminal.** É o lado conservador: um estado incompleto mantém o alarme em vez de silenciá-lo.
4. **O nome do achado não muda.** `LIVE-VS-RECORDED` continua sendo o achado, com significado agora satisfazível. Renomear quebraria quem já filtra por ele sem ganho.

## Camadas

| Camada | Onde | Novo |
|---|---|---|
| Decisão do achado | `grill_status.py`, `item_payload` | alterado |
| Contrato | `tests/validate_status_contract.py` | novo |

## Gates

- Suíte verde; baseline 303.
- Muda `plugin/`, então exige bump: 2.5.2 → 2.5.3, em oito lugares.
- O contrato de saída de `status` é preservado: JSON de linha única, byte-idêntico entre execuções, leitura read-only.

## Riscos

- **Acoplamento entre situação e auditor.** Se as duas noções de terminal divergirem, o alarme aparece ou some na hora errada. Mitigado por usarem os mesmos campos do mesmo arquivo.
- **Uma classe de adulteração deixa de ser observada por `status`.** Trocar o bundle entre commits não é mais denunciado por este caminho. Continua coberto pelo hash de identidade e pelo de governança, e está registrado como consequência em ADR-0002.
