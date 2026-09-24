# DECISION-BACKLOG

## BL-0001 — Marcar o work item de origem como superseded depois do ship da 6.0.31
- state: open
- phase: FASE-002
- owner: líder GWD deste work item (contexto ctx-146fb68d0d6e)
- decision: quando e como o work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d é encerrado como `superseded`: cercar sua atividade `interview-author-001` (sessão retida, dispatch ctx_2923e0218c89, contexto ctx-0c0155ef5a94, líder orca:ctx_ad48e72ddf4c) pelo verbo de fence autorizado publicado na 6.0.31, com autorização humana exata, e fechar o milestone de origem apontando para este work item; o resultado retido nunca é aceito
- trigger: release 6.0.31 publicada (tag imutável e GitHub Release criadas pelo publish.yml no merge para main) e plugin 6.0.31 instalado no harness do líder
- evidence-needed: `gh release view` da 6.0.31 com a tag ancorada no commit do ship; `preflight` do líder reportando o plugin 6.0.31; prévia do fence sobre o work item de origem com especialista terminal (ctx_2923e0218c89: dispatch completed, capability revogada) e veredicto do líder orca:ctx_ad48e72ddf4c; recibo humano (`receipt_ref`) da autorização com scope `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d:ctx-0c0155ef5a94:interview-author-001`
- next-action: depois do ship da FASE-001, o líder marca FASE-002 `blocked` até o gatilho; ao cumprir o gatilho, registra este BL como `resolved` com a evidência acima, promove FASE-002 a `ready-for-specify` e executa handoffs/FASE-002-SPECIFY-HANDOFF.md
- resolution: none

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
