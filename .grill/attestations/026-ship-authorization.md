# Autorização de publicação — 026-attestation-emitter

- work item: `feature-attestation-emitter-2a51feec6ce84a7fb1b7ebe1b6c1aa25`
- fase: FASE-001 — Emissor da cadeia de atestação
- versão: 5.2.0 (de 5.1.0)
- branch: `feature/goal-instruct` → `main`
- autorizado por: carlosaraujo
- decisão: APROVADO

## O que está sendo publicado

A cadeia de atestação passa a ter caminho de correção. Antes, editar o artefato
de uma etapa já fechada deixava a cadeia divergente para sempre, e quem
auditasse não conseguia distinguir edição legítima de adulteração — a única
distinção que a cadeia existe para sustentar (BL-0201, ADR-0205).

Correção agora emite **cadeia sucessora**: o receipt anterior não é reescrito
nem removido, o sucessor nomeia o que substitui e avança a ronda. As etapas a
jusante entram em `chain_stale`, e `ship` e a virada de fase recusam até a lista
esvaziar.

Junto vão: o pino da execução aceita (`attested_executions`), sem o qual a
prova de "este é o receipt substituído" era forjável; e `attest --authorization`,
sem o qual `ship` era inalcançável por checkpoint.

## Sobre o que a autorização vale

Autorizo **invocar** a skill `ship` registrada. Não substituo a skill e não
autorizo side effect direto — merge, push ou release feitos à mão continuam
fora do contrato (WORKFLOW.md, seção de invocação canônica).

## Evidência consumida

- Converge: doze passadas; a última devolveu `converged` com zero findings e
  `tasks.md` byte-idêntico.
- Verify: `PASS` — 1303 testes em 27 validadores, exit 0; `distribution: OK`.
- Review: `APPROVE` — três Important da primeira rodada corrigidos e travados
  por teste; nenhum Critical; quatro Nits registrados e não bloqueantes.
- Fingerprint casando nos três: `tree 415b3f088e85 / work e3b0c44298fc /
  plan 662848a8fc08`.

## Ressalva conhecida, aceita

O `content_sha256` de um `human-authorization/v1` — inclusive deste — não é
conferido contra o `receipt_ref` que ele resume. É limitação pré-existente do
schema, registrada como Nit no review, e o combinado é abrir BL depois do ship.
