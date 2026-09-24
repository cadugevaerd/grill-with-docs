# Quickstart: validar a continuidade

1. Focado: `python3 tests/validate_agent_orchestration_contract.py` e `python3 tests/validate_orchestrator_store_contract.py` — cenários das histórias 1 a 5: tomada aceita com dispatch terminal; recusa com condutor ativo; recusa por observação inconclusiva; recusa por condutor não observável; idempotência; sucessão registrada; troca preparada logo após o `init`; prévia do adopt igual ao apply; checkpoint v2 emitido e v1 ainda legível.
2. Suíte: `python3 tests/run_validators.py` (conte pelo marcador `==>`) e `git diff --check`.
3. Distribuição: `python3 tests/validate_distribution.py` com os 8 pontos em 6.0.3.
4. Live (fora do aceite desta entrega): após instalar 6.0.3, reexecutar o caso C2 da matriz T029 e registrar no work item de origem.
