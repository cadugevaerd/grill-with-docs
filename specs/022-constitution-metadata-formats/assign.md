# Agent assignment

Ciclo executado em sessão única, sem fan-out. A correção é um leitor de ~45 linhas mais um validador;
dividir entre agentes custaria mais coordenação do que trabalho.

| Task | Executor | Justificativa |
|---|---|---|
| T001–T002 reprodução e fixture | sessão principal | exige rodar o CLI e comparar saída real |
| T003–T005 implementação | sessão principal | um único arquivo, um único call site |
| T006 cobertura | sessão principal | o teste nasce da mesma leitura do formato real |
| T007–T010 gates e bump | sessão principal | mecânico e verificável |
| T011–T012 verify e review | sessão principal | evidência já coletada nos passos anteriores |

Exploração de escopo (mapa de testes, consumidores de `fields()`/`top_fields()`, formatos de
constituição no repo) foi delegada a um agente de leitura antes do plano — foi o que revelou que a
forma bullet shipada nunca passava pelo `audit` em teste.
