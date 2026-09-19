# Relatório de debug

## Status
- causa raiz comprovada

## Sintoma reproduzido
- Comando/cenário 1 (compactação): `_full_read(observed, {"messages": msgs + [compaction]}, load_request)` com os módulos de `29c9668`; em live, sessão Claude `064b802e-81c1-4af5-bc56-3bb9bfd87037` após `/compact` (compact_boundary `4da7db44-f5e1-4f96-b427-f362940a24ff`) rodou `preflight … --runtime claude --session-ref orca:ctx_ce9800b76aa7`.
- Resultado observado 1: leitura integral anterior à compactação continua aceita (`ACEITA`); em live o preflight retornou `verdict=OK`, `loading=loaded`, `use_ready=true` com `event_ref=orca:ctx_ce9800b76aa7:92ae25c6-d959-4cb2-bde4-f363f4b0f56a`, evento anterior ao compact_boundary.
- Comando/cenário 2 (macOS): `TMPDIR=<symlink> python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_every_work_entry_reobserves_authority_and_requires_presentation AgentOrchestrationContract.test_public_continuity_resume_observes_destination_before_commit`.
- Resultado observado 2: `FAILED (failures=3)`: `'STYLE-LOAD-UNCONFIRMED' != 'STYLE-SCOPE-CONFLICT'` e dois `2 != 0` com `STYLE-LOAD-UNCONFIRMED`; idêntico ao CI macOS 3.13 do run 35009700240. Com `TMPDIR` real: `OK`.
- Comando/cenário 3 (Windows): `tests/fixtures/orchestration/SKILL.md` convertido para CRLF e `python3 tests/validate_workspace_contract.py WorkspaceV2Contract.test_init_isolates_same_slug_and_never_writes_global`.
- Resultado observado 3: `FAILED (failures=1)` com `STYLE-CONTENT-INCOMPATIBLE`; idêntico ao CI Windows 3.13. Com LF: `OK`.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| Leitura aceita antes e depois de bloco `compaction` | script sobre `29c9668` com `orchestration_fixture.boundary` | `_full_read` ignora a fronteira de compactação |
| `compact_boundary` normalizado em bloco `compaction` | `agent_runtime.py:644-645` (e `:600` Codex) | a fronteira chega ao transcript, mas não é consumida |
| `_full_read` itera `_tool_results(transcript)` sem considerar compaction | `agent_runtime.py:825` | qualquer `cat --` válido do histórico inteiro satisfaz o request |
| Preflight OK pós-compactação com event_ref anterior | JSONL nativo `064b802e…`, msgs `53766b1b`, `fceffa8d`, `d6ebe6d9` | efeito em sessão real |
| TMPDIR symlink reproduz 3 falhas; TMPDIR real passa | execução local | a divergência é o alias de caminho |
| `project_root` retorna `path.resolve()` | `grill_workspace.py:270` | o core compara com root resolvido |
| fixture usa `root = Path(temp.name)` sem resolve | `tests/validate_agent_orchestration_contract.py:604` | o teste grava/compara root não resolvido |
| CI macOS mostra scope root `/private/var/folders/...` | run 35009700240 | alias `/var`→`/private/var` do macOS |
| Só o fixture em CRLF reproduz; só `SKILL.md` do GWD em CRLF passa | execução local isolando cada arquivo | o fixture de referência é o gatilho |
| `skill_sha256 = _sha256(raw)` comparado a digest aprovado | `agent_runtime.py:149-150` | hash de bytes crus, sensível a CRLF |
| Repositório sem `.gitattributes`; clone `core.autocrlf=true` converte o fixture (6 CR) e falha | clone local controlado | checkout Windows altera bytes do fixture |

## Caminho de investigação/Hipóteses eliminadas
1. Compactação: suspeita de `event_ref` reaproveitado → leitura do código de `_full_read` e experimento com bloco `compaction` após a leitura → aceita; hipótese confirmada.
2. macOS: hipótese de defeito lógico no guard de escopo → falsificada: com `TMPDIR` real os testes passam; só o alias de caminho reproduz.
3. Windows: hipótese de `gwd_skill_sha256` divergente (SKILL.md do GWD em CRLF) → eliminada: isolado, passa. Hipótese do fixture de referência em CRLF → confirmada isolando só esse arquivo.
4. Contrafactuais em cópia isolada (não persistidos neste diagnóstico): corte após última compaction faz o caso voltar a `None`; `Path(temp.name).resolve()` faz o validador inteiro passar com `TMPDIR` symlink (32 OK); `.gitattributes` `tests/fixtures/** -text` em clone autocrlf mantém LF e o teste passa.

## Causa raiz
1. `_full_read` (`agent_runtime.py:825`) procura `load_request` e `cat -- skill_ref` em todo o transcript normalizado, sem descartar eventos anteriores ao último bloco `compaction`. Após compactação, a leitura antiga satisfaz a prova de carga e o gate de apresentação fica aberto sem recarga.
2. macOS: `AgentOrchestrationContract.fixture()` cria o root com `Path(temp.name)` sem `.resolve()`, enquanto `project_root()` canonicaliza com `path.resolve()`; com `TMPDIR` sob `/var` (alias de `/private/var`) as duas representações do root divergem e o escopo do `load_request` não casa.
3. Windows: sem `.gitattributes`, o checkout com autocrlf grava `tests/fixtures/orchestration/SKILL.md` em CRLF; `approved_presentation_reference` faz hash dos bytes crus contra digest aprovado em LF e declara `STYLE-CONTENT-INCOMPATIBLE`.

## Cadeia causal
1. `/compact` → `compact_boundary` normalizado em bloco `compaction` → `_full_read` ignora a fronteira → `cat --` pré-compactação aceito → `loading=loaded`, `use_ready=true` sem corpo no contexto.
2. macOS runner `TMPDIR=/var/...` → fixture root não resolvido → `project_root` resolvido `/private/var/...` → scope root do request ≠ root do comando/transcript → `STYLE-LOAD-UNCONFIRMED`/exit 2 onde o teste espera outro resultado → 3 FAIL.
3. Windows checkout autocrlf sem `.gitattributes` → fixture de referência CRLF → sha256 ≠ digest aprovado → `STYLE-CONTENT-INCOMPATIBLE` → `init/audit/reconcile` bloqueados → 4 FAIL.

## Arquivos envolvidos
- `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`: `_full_read` (causa 1); `approved_presentation_reference` hash de bytes crus (causa 3).
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py`: `project_root` canonicaliza root (lado resolvido da causa 2).
- `tests/validate_agent_orchestration_contract.py`: `fixture()` sem resolve (causa 2).
- `tests/fixtures/orchestration/SKILL.md`: bytes convertidos no Windows (causa 3).
- `.gitattributes`: ausente (causa 3).

## Limitações/incertezas
- Causa 2 e 3 reproduzidas por simulação em Linux (symlink de TMPDIR e CRLF controlado), não em runners macOS/Windows locais; as mensagens e testes são idênticos aos do CI.
- Impacto de produção Windows para instalações reais de `i-have-adhd` (upstream sem `.gitattributes`) não medido em host Windows.

Diagnóstico encerrado. Nenhuma correção foi executada.
