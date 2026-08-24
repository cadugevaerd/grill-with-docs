# Research: Emissor da cadeia de atestação

**Fase 0** | **Data**: 2026-08-24

Nenhum `NEEDS CLARIFICATION` restou. As quatro decisões materiais foram
investigadas e seladas na entrevista; este documento consolida o que foi medido,
a conclusão e o que ficou de fora.

---

## R-01 — O que exatamente está bloqueado, e desde quando

**Medição**: `checkpoint_attestation_required(root)` devolve `True` neste
repositório. `grill_workspace.py` recusa com `ATTESTATION-REQUIRED` quando
`--attestation` não é passado. Busca por emissor no núcleo encontra apenas
validadores — `validate_dispatch_intent`, `validate_step_output`,
`judge_step_output`, `judge_checkpoint_attestation`. Os únicos lugares que montam
um bundle são os testes.

**Conclusão**: o ciclo de onze etapas é inalcançável por checkpoint em qualquer
projeto na frontier ativa.

**O que isto não é**: regressão. O predicado perguntava apenas por v3, e um
documento v4 caía no `return False` — o próprio comentário do código diz que
isso fazia o ciclo "shippar com a atestação silenciosamente desativada". A
correção acertou o gate e revelou que a outra ponta nunca existiu.

---

## R-02 — Por que oito etapas não conseguem satisfazer o contrato

**Medição**: `validate_dispatch_intent` valida `worker_lease_id`, `run_id`,
`worktree_id` e `attempt_id` com `_text(...)` — presença obrigatória, sem
tratamento nulo — e `wave_index` com `_nonneg_int`.

**Conclusão**: não existe forma degenerada para etapa sem worker. Oito das onze
etapas do ciclo v4 não têm worker por natureza.

**Alternativa considerada e rejeitada**: tornar esses campos opcionais quando não
houvesse worker. Um envelope com metade dos campos nulos não correlaciona nada, e
o gate deixaria de distinguir execução atestada de não atestada — que é a única
coisa que ele faz.

**Fonte**: ADR-0201.

---

## R-03 — Se o desenho original previa um emissor

**Medição**: `specs/010-execution-attestation/spec.md` diz que "quando uma tarefa
começa, seu coordenador **pode** designar um subagente para montar e revisar o
receipt". A seção *Out* declara fora de escopo: proveniência criptográfica,
defesa contra agente hostil, chaves de runtime e serviços externos.

**Conclusão**: o coordenador sempre foi quem responde pelo receipt. Nunca faltou
permissão para o leader emitir — faltou o emissor concreto. E o nível de garantia
sempre foi correlação estrutural, não prova de execução.

**Consequência para o desenho**: exigir rastro do runtime de agente foi
rejeitado. Acoplaria o núcleo ao formato de cada runtime, transformaria ausência
de rastro em bloqueio do ciclo, e contrariaria um limite de escopo já declarado —
num projeto cuja matriz de integração não tem runtime de agente nenhum.

**Fonte**: ADR-0202.

---

## R-04 — Quanto do mecanismo já existe

**Medição**:

- `step_skills.resolve_workflow_skill` já produz o documento
  `skill-resolution/v1` completo, resolvido contra o registry por hash e contra
  os catálogos confiáveis.
- `step_skills.sha256_jcs` já implementa a canonicalização JCS e o prefixo
  `sha256:` que os digests do contrato exigem.
- `store.py` já valida e registra, por worker, `lease_id`, `fencing_token`,
  `state` e `recovery_count` — exatamente os campos que a cadeia pede.

**Conclusão**: metade do emissor já existe. O trabalho é conectar, não construir
do zero — e conectar consumindo esses produtores, nunca reimplementando-os, para
que não haja duas fontes do mesmo dado.

---

## R-05 — Como impedir que a permissão vire brecha

**Medição**: `WORKFLOW.md` §Execução paralela declara que o diff de cada branch é
verificado contra o grant antes do merge, e que tarefa que escreve evidência de
coordenador nunca é despachada a worker. O isolamento e o grant são o mecanismo
de segurança da etapa, não conveniência.

**Conclusão**: `implement-parallel` precisa ser `worker-required`. Um receipt de
leader para ela atestaria um isolamento que não houve — pior que receipt nenhum.

**Alternativa considerada e rejeitada**: derivar a fronteira do Execution DAG —
quem tem nó despachável exige worker. Ajustar-se-ia sozinha ao trabalho real, mas
um `tasks.md` degenerado, com tudo num nó só, deslocaria a fronteira sem que
ninguém decidisse. Este projeto acabou de produzir exatamente esse `tasks.md`, na
feature anterior.

**Fonte**: ADR-0203.

---

## R-06 — Como quebrar a circularidade

**Medição**: a trilha de incidente (`hotfix-go`) não consulta atestação — valida
escopo, integridade do bundle e roda o teste de correção.

**Conclusão**: seria possível entregar por ali hoje. Foi rejeitado: usar uma
trilha de contenção de incidente para entregar feature planejada com quatro ADRs
esvazia as duas coisas — a trilha deixa de significar incidente, e o work item
planejado vira ornamento.

**Decisão**: bootstrap declarado. Implementar, depois emitir. Fechar as etapas
retroativamente é legítimo porque os artefatos já existem e são lidos no momento
da emissão — é a mesma verificação que qualquer etapa futura receberá, não um
carimbo.

**Fonte**: ADR-0204.
