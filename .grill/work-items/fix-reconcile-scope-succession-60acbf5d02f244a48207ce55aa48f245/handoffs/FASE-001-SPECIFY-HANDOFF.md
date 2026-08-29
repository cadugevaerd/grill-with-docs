# FASE-001 — Sucessão explícita de escopo reconciliado

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: recibo histórico, sucessão explícita, sobreposição concorrente, ownership perpétuo
- ADRs: ADR-0001
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

O reconciliador deve aceitar que um trabalho posterior reutilize caminhos de um
trabalho já reconciliado somente quando declara dependência direta daquele
trabalho. Atores: autor do work item, operador de reconcile e revisor do recibo
global.

Cenários e critérios:

1. Um sucessor declara diretamente o owner histórico e sobrepõe seu escopo: o
   reconcile completo e o targeted não emitem `SCOPE-OVERLAP` para esse par.
2. A mesma sobreposição sem dependência, com dependência de terceiro ou apenas
   por cadeia transitiva continua bloqueada.
3. Dependência ausente, self, ciclo e conflito ADR mantêm seus códigos e não são
   dispensados pela autorização de escopo.
4. Preview permanece read-only; apply e reaplicação preservam atomicidade e
   idempotência existentes.
5. Receipts antigos continuam legíveis sem migração ou mudança de schema.
6. A versão patch e todos os pontos de distribuição permanecem sincronizados;
   validadores relevantes e suíte completa encerram com exit 0.

## WHY

Hoje um receipt concluído vira ownership perpétuo: qualquer trabalho futuro que
declare honestamente o mesmo arquivo é recusado. O diagnóstico SGD-24 reproduziu
o defeito mesmo com dependência explícita e localizou a classificação antes da
leitura de `depends-on-work`.

A dependência direta é a autorização mínima rastreável. Ela destrava sucessores
legítimos sem transformar conclusão em waiver global nem inferir relações
transitivas que o autor não declarou. Esta correção é pré-requisito para o
SGD-19 declarar escopo verdadeiro e, depois, para a 024 concluir T027/T028.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
