# Quickstart: validar a observação Codex

1. Focado: `python3 tests/validate_agent_orchestration_contract.py` → os casos das histórias 1–3 passam: listagem real sem `installPath` + cópia em cache temporário → `present`; `installed=false`, diretório ausente, campo ausente → `{}`; `SKILL.md` com conteúdo divergente → `STYLE-CONTENT-INCOMPATIBLE`; listagem com `installPath` (Claude e Codex) → resultado anterior.
2. Suíte: `python3 tests/run_validators.py` (conte pelo marcador `==>`) e `git diff --check`.
3. Distribuição: `python3 tests/validate_distribution.py` com os 8 pontos em 6.0.2.
4. Live (fora do aceite desta entrega): após instalar 6.0.2, reexecutar C1 do T029 numa sessão Codex supervisionada e registrar `installation=present` e `load_request` no work item de origem.
