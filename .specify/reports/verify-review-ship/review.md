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

---

## Review Report — rodada R2

Verdict: REQUEST CHANGES
Source fingerprint: tree d29da301a5cdabaabed7bd6e7b072066c24cb0c3633a1d62496be0993bf5c965 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 2e89ce66817ba0c51eeb8f56a7dab64ed26fd123be075d4eb2626a5fa2ab2c81
                    (igual a Converge r3 `1723d02` e Verify r2 `2df8987`)

Revisor: segundo subagente `Code Reviewer`/`fable`, independente do líder, dos workers e do revisor da R1.

### Achados da R1
- I1 (fail-closed) resolvido: `agent_runtime.py:521-529` com o mesmo trio de exceções de `:451`; testes em `tests/validate_agent_orchestration_contract.py:520-532`.
- I2 (drive do Windows) resolvido: `agent_runtime.py:519` com `PureWindowsPath(v).name == v`; testes `:479-500`.
- M1 (CHANGELOG) e M2 (lacunas de teste) resolvidos.
- M3 (resolução de home triplicada): não adotado, aceito pelo revisor como Minor sem risco funcional.

### Problemas novos
- **Important N1** — `tests/validate_agent_orchestration_contract.py:496`: o caso que semeia um diretório literal `"D:"` no cache usa `Path(home) / ... / "D:"`, e no Windows `"D:"` é âncora de drive: o join reancora para `D:i-have-adhd\0.3.0\...`, relativo ao cwd do drive D. No runner Windows do GitHub (checkout em `D:\a\...`) isso cria diretórios dentro do repositório, fora do `TemporaryDirectory`; se o cwd não estiver no drive D, vira `OSError` e o teste quebra. A asserção passa nos dois casos, então é fragilidade de CI, não falha de produto. Fix: semear apenas quando o nome literal é possível (`os.name != "nt"`), mantendo a asserção incondicional.
- Minor N2 (`except` abrangente) e Minor N3 (`PureWindowsPath(v).name == v` não recusa nome legítimo): verificados e aceitos.
- Ramo `installPath`, runtime Claude, segurança e performance: sem regressão.

### Decisão do líder
Corrigir N1 antes do ship (decisão do operador em 2026-09-19). Vai como tarefa de convergência T011.

---

## Review Report — rodada R3

Verdict: APPROVE
Source fingerprint: tree f79daecfaea68fec68f402183a87d5204669f02308d06f0a1ad999d221f9825a / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 15e0cee81a10cb63b7cb3e8b1c8d43580db5b77c59726b1c616329944fb2449f
                    (igual a Converge r5 e Verify r3 `db62bd2`)

Revisor: terceiro subagente `Code Reviewer`/`fable`, independente do líder, dos workers e dos revisores das rodadas R1 e R2.

### N1 resolvido
- Guarda em `tests/validate_agent_orchestration_contract.py:496-497` (`os.name != "nt"`); a semeadura não reancora fora do diretório temporário no Windows.
- Asserção de recusa incondicional em `:498-500`.
- Cobertura de I2 preservada nos três SOs: a recusa por filtro dos valores `D:` e `C:` nos três campos roda sem semeadura em `:476-481`, e o runtime usa `PureWindowsPath` em qualquer plataforma (`agent_runtime.py:519`). O caso semeado só acrescenta o cenário que é fisicamente possível apenas em POSIX.

### Passada final
- Testes: matriz cobre presente, idêntico, não instalado, campo ausente, valor inseguro, tipo errado, `installPath` nulo, `installed` ausente, `installPath` relativo, home ausente, `PermissionError`, cache vazio, bytes divergentes e Claude inalterado; sem `codex`, `claude` ou rede.
- Runtime: fail-closed mantido, inclusive byte nulo, que cai no bloco de exceções.
- Arquitetura, segurança e performance: sem regressão; o caminho composto não escapa do cache e o conteúdo continua julgado por `approved_presentation_reference`.
- Distribuição: os oito pontos em 6.0.2, sem resíduo de 6.0.1; entrada de CHANGELOG factual.

### Achados
- Critical: nenhum. Important: nenhum.
- Minor M3 (mantido das rodadas anteriores): predicado denso em `agent_runtime.py:516-519`; extração opcional para um helper. Não bloqueia o ship.

### Final Recommendation
- APPROVE: seguir para `ship`, que exige autorização humana.

---

## Review — adendo da árvore final do ship

Verdict: APPROVE
Source fingerprint: tree dc5dec79246a11c46c22e0440cf6d53ae88c700b42afbbb4e09f68e5aa88aafc / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 15e0cee81a10cb63b7cb3e8b1c8d43580db5b77c59726b1c616329944fb2449f

O gate de aprendizados do `ship` aplicou LRN-001 e LRN-002 no backlog `SGD` (itens `SGD-34` e `SGD-35`), LRN-003 na memória do projeto e LRN-004 no `CLAUDE.md`. Só o último toca o repositório.

Revisor independente (`Code Reviewer`/`fable`, quarta sessão distinta) avaliou o commit `91904e1` quanto a exatidão factual, seção correta e formatação: APPROVE, com dois Minors de prosa — a frase do `installPath` simplificava o comportamento, que é agnóstico de runtime, e a regra de segmento não citava a recusa de vazio, `.` e `..`. Os dois foram corrigidos em `fff13a3`.

Gates reexecutados nesta árvore final: suíte 30 validadores e 1477 testes (`exit 0`, 1 skip de macOS), smoke de portabilidade, bump `6.0.1 -> 6.0.2` e `git diff --check`, todos `exit 0`. Nenhum achado Critical ou Important permanece.
