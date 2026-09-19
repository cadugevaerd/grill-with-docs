# Relatório de debug

## Status
- causa raiz comprovada

## Sintoma reproduzido
- Comando/cenário: entrada `$grill-with-docs iniciar ROOT` numa sessão Codex supervisionada (dispatch `ctx_dc4fd5fc4d91`, codex-cli 0.154.0, GWD 6.0.0 candidato no HEAD `ba2ea64`). Reprodução offline isolada: `python3 -B repro_observer.py codex-plugin-list.json`, que chama `grill_core.agent_runtime._orca_presentation_axes` com a saída real de `codex plugin list --json` (sha256 `4bddc745a1b838fef569a93c985cda33bc93946e4ace11b401c92cf8739de721`), substituindo apenas a leitura de transcript (`_tool_results`/`_tool_command`) e o eixo de configuração.
- Resultado observado: ao vivo, `init` sai com `verdict=BLOCKED` e `code=STYLE-DEPENDENCY-UNDETERMINED` ("installation source unreadable or ambiguous"), mesmo com `enablement=enabled` e `trust=ready`. Offline, `installation={}` e `plugin_listing` registrado.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| Entrada `i-have-adhd@i-have-adhd`: `version=0.3.0`, `installed=true`, `enabled=true`, `source={"source":"git","url":…,"ref":"main"}`, **sem `installPath`** | `codex plugin list --json` (0.154.0) | O harness Codex não emite o campo de caminho |
| Reprodução com a saída real → `installation={}`, `plugin_listing` presente | `repro_observer.py` | O comando casou e exatamente um registro foi selecionado; mesmo assim, a instalação não é promovida |
| Contrafactual: mesma saída + só `installPath` → `installation.status=present`, `skill_ref=…/0.3.0/skills/i-have-adhd/SKILL.md` | `repro_observer.py` | A ausência de `installPath` é a única variável que separa falha de sucesso |
| `path, version = entry.get("installPath"), entry.get("version")`, e promoção só se `path` for absoluto | `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py:512-515` | Local exato da condição |
| `status = installation.get("status", "undetermined")` → ramo `STYLE-DEPENDENCY-UNDETERMINED` "installation source unreadable or ambiguous" | `agent_runtime.py:204`, `agent_runtime.py:218-219` | Mapeia `installation={}` para o código observado |
| Diagnóstico ao vivo com o texto "installation source unreadable or ambiguous" (8 ocorrências) | rollout Codex `01a0baa3-7e61-7142-b940-d467bc08d1d9` | O ramo exercitado ao vivo é o mesmo da reprodução |
| `codex plugin` só oferece `add`, `list`, `marketplace` e `remove` | `codex plugin --help` | Não existe outra fonte nativa de caminho no Codex 0.154.0 |
| `SKILL.md` aprovado presente em `~/.codex/plugins/cache/i-have-adhd/i-have-adhd/0.3.0/`, sha256 `3170b16a…27e9` | `sha256sum` | O defeito não é instalação ausente nem conteúdo divergente |

## Caminho de investigação/Hipóteses eliminadas
1. Plugin não instalado ou versão errada → refutada: a listagem nativa diz `installed=true` e `version=0.3.0`, e o cache tem o `SKILL.md` com o hash aprovado.
2. Enablement ou trust bloqueando → refutada: a escalada do C1 registra `enablement=enabled` e `trust=ready`, e o código emitido pertence ao eixo `installation`.
3. Comando de listagem não reconhecido (`_tool_command` diferente do exigido) → refutada: `plugin_listing` foi gravado na reprodução e só é gravado depois de o comando casar e de exatamente um registro ser selecionado (`agent_runtime.py:490-510`).
4. Filtro por `pluginId` falhando → refutada pelo mesmo `plugin_listing` e pela seleção de um registro.
5. Ausência de `installPath` → confirmada pelo contrafactual de uma variável.

## Causa raiz
O observer de instalação (`_orca_presentation_axes`, `agent_runtime.py:512-515`) só promove `installation=present` a partir do campo `installPath` da listagem nativa, que é o formato do `claude plugin list --json`. O `codex plugin list --json` 0.154.0 não emite esse campo e não há outro comando nativo que exponha o caminho. Por isso, no runtime Codex, `installation` fica sempre vazia, o status cai no padrão `undetermined` (`agent_runtime.py:204`) e a entrada GWD é recusada com `STYLE-DEPENDENCY-UNDETERMINED` (`agent_runtime.py:218-219`).

## Cadeia causal
Sessão Codex executa `codex plugin list --json` → a entrada `i-have-adhd@i-have-adhd` vem sem `installPath` → `agent_runtime.py:512-515` não preenche `installation` → `status` padrão `undetermined` (`:204`) → diagnóstico `STYLE-DEPENDENCY-UNDETERMINED` (`:218-219`) → `presentation.work_ready=false` → `init` retorna `BLOCKED` e nenhum trabalho GWD é liberado no Codex.

## Arquivos envolvidos
- `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`: observer de instalação (`:490-516`) e mapeamento para diagnóstico (`:204`, `:218-219`).
- `~/.codex/plugins/cache/i-have-adhd/i-have-adhd/0.3.0/`: instalação real, presente e íntegra, que o observer não consegue referenciar.

## Limitações/incertezas
- Nenhuma para o sintoma reproduzido. Não foi verificado se versões do Codex diferentes da 0.154.0 emitem `installPath`.

Diagnóstico encerrado. Nenhuma correção foi executada.
