# Implementation Plan: Emissor da cadeia de atestação

**Branch**: `feature/goal-instruct` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/026-attestation-emitter/spec.md`

## Summary

O núcleo exige a cadeia `skill-resolution → dispatch-intent → skill-invocation →
step-output` em toda conclusão de etapa, sabe julgá-la e não sabe cunhá-la.
Nenhuma outra parte do sistema a cunha. O ciclo de onze etapas ficou
inalcançável em qualquer projeto na frontier ativa.

A abordagem está selada em quatro ADRs: o leader é executor legítimo para as
etapas que não têm worker por natureza (ADR-0201); a âncora é o digest do
artefato declarado (ADR-0202); uma tabela congelada delimita quem pode executar
o quê (ADR-0203); e a primeira entrega não é atestada por si mesma (ADR-0204).

**Estado**: a fundação está entregue — tabela de classes, recusa de leader em
etapa `worker-required`, âncora do artefato, 18 testes de contrato. Falta a
montagem dos quatro elos e a superfície de linha de comando.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão.

**Primary Dependencies**: Nenhuma externa. Internamente a emissão consome
`step_skills.resolve_shipped_workflow_skills` (que já produz `skill-resolution/v1`) e
`step_skills.sha256_jcs` (canonicalização JCS já implementada).

**Storage**: Bundle serializado em arquivo, lido por `load_checkpoint_attestation`.

**Testing**: `python3 tests/run_validators.py`. Contrato próprio em
`tests/validate_attestation_emitter_contract.py`.

**Target Platform**: Multiplataforma; a matriz cobre três SOs e duas versões de
Python, sem rede e sem runtime de agente.

**Project Type**: Biblioteca de núcleo mais interface de linha de comando.

**Performance Goals**: N/A — uma emissão por etapa, com uma leitura de arquivo.

**Constraints**:
- `attestation.py` não faz I/O próprio: recebe a fronteira de leitura do
  chamador, que é `safe_read_regular_fd` no CLI.
- As tabelas de classe são literais congelados, nunca derivadas das sequências.
- O que a cadeia prova precisa estar declarado em docstring e changelog sem
  eufemismo — a sobre-afirmação é o defeito que o mecanismo existe para impedir.

**Scale/Scope**: Duas versões de ciclo, onze etapas cada, quatro elos por
emissão, 20 requisitos funcionais.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Veredito | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | É a cláusula que motiva a feature. ADR-0202 ancora o registro num artefato lido e declara o limite; o docstring da seção de emissão diz o que a cadeia não prova. |
| Work item isolado e ownership | PASS | Identidade própria; o ROADMAP declara a origem em BL-0101. |
| Feature/fix plan-only | PASS (com desvio registrado) | A entrega da fundação ocorreu antes de `specify`, o que é desvio de ordem registrado no checkpoint e no commit — não um waiver. Ver Complexity Tracking. |
| Sequência obrigatória do desenvolvimento | PASS | A feature restaura a possibilidade de cumprir a sequência, hoje inalcançável. A tabela é declarada ao lado da ordem canônica e nunca derivada dela. |
| Verify/review antes de ship | PASS | Os critérios de aceite são executáveis e serão exercidos por verify. |
| Fail-closed sem waiver | PASS | Etapa não classificada, versão desconhecida, artefato ausente ou leitura inválida são recusas nomeadas. A alternativa "registrar e auditar depois" foi recusada em ADR-0203 por atravessar por default. |
| Rastreabilidade | PASS | Quatro DQs, quatro ADRs, cada DQ apontando o ADR que a encerrou. |
| Tier de modelo e esforço do worker Orca | NOT-APPLICABLE | Nenhum worker Orca despachado; a fundação foi escrita pelo leader. A cláusula volta a valer se a montagem dos elos for delegada. |
| Bump obrigatório do plugin | PASS | 5.0.0 → 5.1.0 sincronizado nos oito pontos; gate `BUMPED` contra `origin/main`. |
| Release obrigatória por versão | PASS | A release é criada pelo pipeline no merge para `main`; nenhuma à mão. |
| Governance | PASS | Constituição preservada, hash fixado. ADR-0201 amplia quem pode ser executor sem afrouxar o que o executor precisa provar. |

**Veredito**: PASS, com um desvio de ordem registrado — não uma violação
dispensada.

### Re-check pós-Fase 1

Os artefatos de desenho não introduzem violação nova. O contrato de emissão
declara explicitamente o limite da garantia, o que reforça *Evidência antes de
afirmação*; e a tabela de classes fecha a porta que ADR-0201 abriu, o que é o
que mantém *Fail-closed sem waiver* verdadeiro depois da ampliação.

## Project Structure

### Documentation (this feature)

```text
specs/026-attestation-emitter/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1 — a cadeia e seus elos
├── quickstart.md        # Fase 1 — como validar
├── contracts/
│   └── emission.md      # Superfície de emissão e suas recusas
└── tasks.md             # Fase 2
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/scripts/
├── grill_core/
│   ├── workflow_versions.py   # ENTREGUE: EXECUTION_CLASS_*, LEADER_WAVE_INDEX
│   ├── attestation.py         # ENTREGUE: execution_class, require_emission_allowed,
│   │                          #           artefact_digest, EmissionError, leader_lease,
│   │                          #           mint_chain, supersede_step_execution
│   ├── step_skills.py         # consumido: resolve_shipped_workflow_skills, sha256_jcs
│   └── store.py               # consumido: concessão de lease
└── grill_workspace.py         # ENTREGUE: verbo attest, supersessão no checkpoint

tests/
└── validate_attestation_emitter_contract.py   # ENTREGUE: 18 testes
```

**Structure Decision**: emissão e julgamento moram no mesmo módulo,
`attestation.py`. O contrato tem um dono só, e quem muda o que a cadeia exige vê,
no mesmo arquivo, o que a cunha. A alternativa — módulo separado — deixaria as
duas metades livres para divergir, que é a forma exata do defeito que a 5.0.0
teve de corrigir em outro lugar do sistema.

## Complexity Tracking

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| A fundação foi implementada antes de `specify`, `plan` e `tasks` | Nenhuma. É desvio de ordem, não necessidade: ADR-0204 previu implementar antes de **atestar**, não antes de **planejar** | Não há alternativa a rejeitar — o certo era planejar primeiro. O desvio está registrado no checkpoint e no commit, e esta regularização o corrige em vez de o normalizar |
| A feature altera `plugin/**` e depende de si mesma para fechar as próprias etapas | A circularidade é intrínseca a um emissor: a primeira cadeia não pode ser cunhada por um mecanismo que ainda não existe | Entregar pela trilha de incidente fecharia hoje sem atestação, mas esvaziaria tanto a trilha quanto o work item planejado (ADR-0204) |
