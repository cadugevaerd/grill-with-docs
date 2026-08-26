# PLAN-CONTEXT

## FASE-001 — Emissor da cadeia de atestação
- phase: FASE-001
- ADRs: ADR-0201, ADR-0202, ADR-0203, ADR-0204, ADR-0205
- BLs: BL-0201, BL-0202
- delivery-units: DU-001, DU-002
- development-type: platform-devops

### HOW
- A classe de execução por etapa é literal congelado ao lado de
  `grill_core/workflow_versions.py`, **nunca** derivado das sequências: derivá-la
  faria uma mudança de ordem alterar em silêncio quem pode executar o quê
  (ADR-0203). `implement-parallel` é `worker-required`; as outras oito do ciclo
  são `leader-allowed`; etapa sem entrada é recusa nomeada.
- O leader obtém `lease_id` e `fencing_token` pelo mesmo mecanismo que
  `grill_core/store.py` já concede a worker — os campos existem e são
  verdadeiros, muda apenas quem os origina (ADR-0201).
- `worktree_id` é o worktree do coordenador; `wave_index` é `0`, com significado
  semântico de execução fora de wave, não valor de preenchimento.
- O emissor monta os quatro elos com o que o núcleo já conhece: `project_id` de
  `store.project_identity`, `work_item_id` e revisão do bundle,
  `registry_sha256` da resolução de step-skills, `worktree_head` do Git,
  `recovery_generation_id` e `plan_revision` do estado corrente.
- A âncora do `step_output` é o digest do artefato declarado, lido pela fronteira
  segura que o núcleo já usa — descritor sem seguir link simbólico, sem caminho
  absoluto, sem travessia (ADR-0202). Artefato ausente, ilegível ou fora do
  projeto é recusa nomeada, nunca digest vazio.
- O emissor **não** decide se a skill foi invocada. Ele sela correlação
  estrutural, que é o nível declarado como escopo em
  `specs/010-execution-attestation/spec.md`. A documentação precisa dizer isso
  sem eufemismo: um receipt aprovado prova que houve artefato, não que houve
  invocação.
- Somente biblioteca padrão, Python >=3.10, sem rede e sem ferramenta externa: a
  matriz de integração não tem runtime de agente nenhum, e é por isso que exigir
  rastro de runtime foi recusado.
- Validador novo em `tests/`, nomeado `validate_*.py` para entrar na suíte pelo
  glob de `tests/run_validators.py`. Ele trava a tabela de classes, a recusa de
  etapa sem entrada e a recusa de artefato ilegível.
- A entrega altera `plugin/**`, logo exige bump SemVer sobre a versão publicada,
  sincronizado nos oito pontos travados, antes de merge ou push.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
