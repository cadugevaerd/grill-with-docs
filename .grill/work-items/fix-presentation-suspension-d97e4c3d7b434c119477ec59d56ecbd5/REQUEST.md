# Pedido e escopo único

Owner: Carlos Araújo. Sessão condutora: Claude Code (Opus). Branch: cadugevaerd/feat-new-subagents.
Origem: T029 do work item `feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa` (2026-09-19). Achado F2 da revisão high independente (`REVIEW-A-HALF.md`, sha256 `7634bfaf…e8e8`, incorporado em `STYLE-LIVE-VALIDATION.md`, commit `3d177d9`). Triagem: ainda não executada.

## Requisito solicitado

Fazer o core registrar e respeitar a suspensão (`stop adhd mode`) e a compactação no eixo de apresentação, como o contrato exige: após compactação com aplicação ativa, `use_ready` só volta com carga atual; com `stop adhd mode` documentado na mesma sessão/incarnation/escopo, `work_ready` continua `true` e `use_ready=false`, sem reinjetar o corpo.

## Evidência observada

- A1 (transcript `bb37d5f5-8145-4530-a8de-404a03c62954`): `stop adhd mode` às 16:41, `/compact` às 16:42:04Z, retomada GWD. O preflight devolveu `application=active`, `use_ready=true` e `suspension=null`, com base na leitura anterior à compactação. Quem cumpriu o contrato foi a sessão: ela não releu e tratou `use_ready` como `false`. O core não impôs.
- O mesmo core também aceitou a carga pré-compactação como atual depois da **primeira** compactação ativa. A sessão releu por iniciativa própria (16:40:10Z), mas o core não teria exigido.
- Revisor: "registro de suspensão não comprovado, `grill_workspace.py` não passa `suspension`".

## Restrições conhecidas

- O core não enxerga a compactação diretamente: definir a observação nativa aceita (evento do harness no transcript, marcador de boundary) sem autorrelato.
- A suspensão exige fonte humana vinculada; não aceitar o texto do agente como prova.
- Stdlib apenas; testes offline.

## Fora do escopo

Conformidade das respostas do modelo (achado F1: fatos citados só pelo número). É comportamento de sessão e se resolve reexecutando a matriz, não no core.
