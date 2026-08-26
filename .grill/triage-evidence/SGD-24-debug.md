# Relatório de debug

## Status
- causa raiz comprovada

## Sintoma reproduzido
- Comando/cenário: `python3 tests/validate_workspace_contract.py WorkspaceV2Contract.test_targeted_reconcile_rejects_scope_and_adr_against_receipt`, seguido de reprodução isolada que reconcilia `owner`, declara `consumer depends-on-work = ["owner"]`, sobrepõe `src/api/x.py` a `src/api` e executa `reconcile --work-id consumer`.
- Resultado observado: o teste canônico passa confirmando a recusa; no cenário com dependência explícita, `owner` retorna `APPLIED`/exit 0 e `consumer` retorna `NO-GO`/exit 1 com `SCOPE-OVERLAP:consumer:src/api/x.py<->owner:src/api`.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| `Ran 1 test ... OK` | `test_targeted_reconcile_rejects_scope_and_adr_against_receipt` | O contrato atual recusa qualquer sobreposição contra recibo histórico. |
| `owner_apply_exit: 0`, `consumer_preview_exit: 1`, conflito `SCOPE-OVERLAP` | reprodução isolada em repositório temporário | Declarar dependência explícita do sucessor sobre o trabalho concluído não evita a recusa. |
| O laço adiciona `SCOPE-OVERLAP` para todo recibo diferente do alvo antes de ler `depends-on-work` | `plugin/skills/grill-with-docs/scripts/grill_workspace.py:1997-2015` | A decisão de sobreposição não consulta relação de dependência. |
| `receipt_for` preserva `depends_on_work`, mas não registra estado; a presença do recibo só ocorre após target terminal e reconciliável | `plugin/skills/grill-with-docs/scripts/grill_workspace.py:1829-1838,1954-1984` | O recibo já representa trabalho concluído, mas seus dados não são usados para distinguir sucessão de concorrência. |

## Caminho de investigação/Hipóteses eliminadas
1. A hipótese de dependência ausente foi eliminada: o conflito persiste com `depends-on-work: ["owner"]`.
2. A hipótese de recibo concorrente foi eliminada: recibos válidos só são produzidos para bundles concluídos e reconciliáveis.
3. A geometria pai/filho de `scopes_overlap` está correta; a falha é aplicá-la indistintamente a sucessão e concorrência.

## Causa raiz
O reconciliador targeted trata todo escopo preservado em recibo como ownership exclusivo perpétuo. Em `reconcile_command`, o laço de `plugin/skills/grill-with-docs/scripts/grill_workspace.py:1997-2007` adiciona `SCOPE-OVERLAP` para qualquer interseção com qualquer recibo anterior, sem considerar que o recibo prova conclusão nem que `target.metadata["depends-on-work"]` declara sucessão explícita. A dependência só é validada depois, em `:2008-2015`, e nunca remove ou qualifica o conflito já criado.

## Cadeia causal
Work item concluído gera recibo com escopo → sucessor legítimo declara dependência e reutiliza arquivo desse escopo → laço compara contra todos os recibos sem consultar dependência → `scopes_overlap` adiciona conflito → preview retorna `NO-GO` → work items futuros não podem declarar escopo honesto sobre arquivos já tocados.

## Arquivos envolvidos
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py`: cria/lê recibos e classifica sobreposição no reconciliador targeted.
- `tests/validate_workspace_contract.py`: fixa hoje a recusa genérica, mas não cobre a distinção entre concorrência e sucessão explícita.
- `.grill/global/receipts/feature-workflow-v3-7dc283c84fb54e6b8f10a9c4546cd473.json`: recibo histórico real que bloqueia escopo verdadeiro.

## Limitações/incertezas
- Sucessão direta versus transitiva permanece decisão do work item.

Diagnóstico encerrado. Nenhuma correção foi executada.
