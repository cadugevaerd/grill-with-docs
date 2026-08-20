# Review: metadados da constituição em suas três formas reais

## Risco técnico

**Baixo, com uma superfície bem delimitada.** A mudança de comportamento vive em um único leitor e
em um único call site. Tudo que o `audit` faz depois continua idêntico, inclusive as strings dos
findings, então nenhum consumidor do JSON precisa mudar.

### O que poderia dar errado e não dá

- **Contaminar outros artefatos**: seria o risco se `FIELD`/`TOP_FIELD` tivessem sido afrouxados.
  Não foram — zero linhas de diff neles. ROADMAP, DECISION-BACKLOG, handoffs, PLAN-CONTEXT,
  DECISION-FRONTIER e as descrições de work item lidas por `backlog_bridge.py` parseiam exatamente
  como antes, e os 1088 testes anteriores comprovam.
- **Abrir falso negativo**: a preocupação legítima ao relaxar um parser fail-closed. Coberta por três
  testes que exigem os findings quando o metadado falta de verdade, incluindo o caso do rodapé
  presente porém com versão não-SemVer.
- **Comentário virar dado**: o template oficial ship um rodapé de exemplo comentado com uma versão e
  datas plausíveis. Se ele fosse lido, uma constituição sem metadado passaria com os valores de
  exemplo — falso negativo silencioso e difícil de perceber. `HTML_COMMENT` é removido antes da
  extração e há teste dedicado.
- **Governança satisfeita pelo rodapé**: `## Governance` vazio seguido do rodapé teria corpo
  não-vazio se a linha do rodapé contasse. `section_body` a exclui, e há teste.

## Escopo

Não cresceu. O laudo pedia um parser que entendesse o formato real; foi isso que foi entregue.
Nenhuma refatoração oportunista, nenhum arquivo de constituição tocado, nenhuma mudança no gate de
hash/cláusulas do `grill_workspace.py` — que é outro mecanismo e está correto.

## Decisão de arquitetura revisada

Manter o leitor em `audit_decisions.py` em vez de `grill_core/` contraria o instinto de "lógica pura
vai para o core", mas é o certo aqui: o módulo é carregado por `backlog_bridge.py:184` via
`sibling()`, fora do pacote. Registrado no plan com a justificativa, para não ser "corrigido" depois
por quem só vê o padrão.

## O achado que vale mais que o fix

A exploração revelou que a forma bullet — a que o próprio plugin escreve em todo `init` — nunca
passava pelo `audit` em teste. Todas as fixtures usavam uma quarta variante, top-level, que nem o
asset shipado nem o Spec Kit produzem. É o mesmo padrão do defeito de ANSI no preflight
(`specs/021-...`): fixture derivada do código, não da saída real da ferramenta.

Por isso o validador novo gera a fixture bullet **a partir do asset shipado em tempo de teste**, com
a mesma substituição que `grill_workspace.py:397` faz. Se o template mudar, o teste acompanha; não há
como divergir em silêncio de novo.

## Dívida deixada em aberto

- Chaves do rodapé traduzidas não são reconhecidas. Premissa declarada, sem caso real conhecido.
- `triage` continua consultiva: este ciclo registrou a rota `bugfix` em
  `tri-9981372e1dbc4d7ebfcf532f09d9573a`, mas nada a exigiu. Torná-la obrigatória segue sendo a fase
  seguinte, fora deste escopo.
- Este ciclo rodou sem bundle de work item do grill. Um foi aberto durante a execução e depois
  removido: a entrevista do grill nunca foi conduzida para ele, então não havia ADR, `ROUND-LOG` nem
  `CONTEXT`, e sua auditoria travava em `CHECK-NOT-APPROVED`. Preencher o `CONSTITUTION-CHECK.md`
  seria inventar trilha de decisão — em particular, a cláusula "Feature/fix plan-only" não admite
  PASS honesto numa sessão que escreveu e mergeou código. O registro de triagem
  `tri-9981372e1dbc4d7ebfcf532f09d9573a` e este diretório `specs/022-...` são a trilha real.

## Veredito

GO para merge.
