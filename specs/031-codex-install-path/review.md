## Review Report — rodada R1

Verdict: REQUEST CHANGES
Source fingerprint: tree f5762ff4e7b2f627c4e4df08ac59c952cdd392a843fd567e9ab5e5c69d2a5d24 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan f3a3415b8368a0e84237dffd47af325ebef8913f4c110bf5625d4d93e7663856
                    (igual a Converge `d291bff` e Verify `9f96fa1`)

Revisor: subagente `Code Reviewer`, modelo `fable`, read-only, distinto do líder (autor de spec/plan/tasks) e dos workers `sonnet` (autores do código). Seis dimensões em um revisor (diff de 8 arquivos).

### Test Quality
OK no essencial: fixture real 0.154.0, matriz negativa por campo, precedência de `installPath` relativo, divergência até `STYLE-CONTENT-INCOMPATIBLE`, Claude inalterado, sem CLI ou rede. Lacunas (Minor): tipos não-string (`version: 1`, `marketplaceName: null`), `installPath: null` presente, `installed` ausente, segmento com drive (`"D:"`, `"C:"`) — `tests/validate_agent_orchestration_contract.py:424-516`.

### Runtime Correctness
**Important I1** — `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py:522-525`: `Path.home()` sem HOME levanta `RuntimeError`; `is_dir`/`is_file` propagam `PermissionError` em Python 3.10–3.12. O ramo novo não trata o trio que `_runtime_config_axes` já trata (`:451`), e o call site (`:881`) não tem try: o preflight quebra com traceback em vez de falhar fechado em `STYLE-DEPENDENCY-UNDETERMINED`. Fix: envolver resolução do home e as duas verificações em `try/except (OSError, ValueError, RuntimeError)`, mantendo `installation` vazio.

### Readability
Minor: terceira cópia da resolução do home (`:440-441`, `:712`, `:522`); um helper de duas linhas cobriria as três. Não bloqueia.

### Architecture
OK: dependência na direção certa; não importa `ensure_dependencies`.

### Security
**Important I2** — `agent_runtime.py:514-516`: o filtro de barra e contrabarra não pega segmento com drive do Windows. `PureWindowsPath(r"C:\x\plugins\cache") / "D:" / "n" / "v"` resulta em `D:n\v`, fora do cache; `"C:"` colapsa um nível. O hash em `approved_presentation_reference` impede leitura útil, mas o invariante de FR-009 ("a localização nunca aponta fora do cache") quebra. Fix: exigir `PureWindowsPath(v).name == v` além de recusar vazio, `.` e `..`.
Symlink no cache: fechado por `O_NOFOLLOW` + hash no POSIX.

### Performance
OK: duas chamadas de `stat` por evento de listagem.

### Critical Issues
Nenhum.

### Important Issues
- I1 (runtime, fail-closed)
- I2 (segurança, FR-009 no Windows)

### Minor
- M1: `CHANGELOG.md:5` diz que o teste "passa a usar" a entrada real "em vez de" uma listagem derivada do código; o teste antigo (`:401-402`) continua existindo e o novo foi acrescentado.
- M2: lacunas de teste listadas em Test Quality.
- M3: resolução do home triplicada.

### Constitution References
Fail-closed sem waiver: I1 viola (falha por exceção em vez de recusa nomeada).

### Final Recommendation
- REQUEST CHANGES: corrigir I1, I2, M1 e M2 (M3 opcional), rodar `/speckit-converge`, depois verify e review de novo.
