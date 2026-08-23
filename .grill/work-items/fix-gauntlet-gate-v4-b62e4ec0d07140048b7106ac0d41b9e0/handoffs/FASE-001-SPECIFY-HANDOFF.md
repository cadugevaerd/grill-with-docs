# FASE-001 — Alinhar o gate do Gauntlet e a CLI à frontier ativa

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: gate de execução, módulo de gate, ponto de injeção, marcador de workflow, frontier ativa, tabela por versão
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0007, ADR-0008
- BLs: BL-0001

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

**Resultado observável.** `gauntlet-init` executado contra um repositório cujo
`WORKFLOW.md` é o da frontier ativa termina com sucesso, em vez de recusar com
`WORKFLOW-INCOMPATIBLE`.

**Atores.** Quem roda a CLI do grill num repositório consumidor; e a suíte de validadores,
que passa a exercer a frontier ativa no boundary da CLI.

**Cenários.**
1. `WORKFLOW.md` na frontier ativa → `gauntlet-init` bem-sucedido.
2. `WORKFLOW.md` numa versão que o runtime sabe ler mas não executa → recusa explícita,
   sem exceção não tratada.
3. Activation record imutável de versão anterior → continua revalidando; nenhuma tabela
   por versão perdeu a chave dele.
4. `state.json` já materializado com a grafia antiga do campo de schema → continua
   auditável, sem migração.
5. Uma frontier nova é declarada e os pontos de injeção não acompanham → a suíte reprova
   por conta própria.

**Escopo excluído.** Escolher o gate pela versão que o documento declara (adiado em
BL-0001); migrar bundle existente; remover a biblioteca da versão anterior da árvore;
mexer nas tabelas por versão além da amarração de teste.

**Critérios de aceite.**
- `gauntlet-init` bem-sucedido contra o `WORKFLOW.md` da frontier ativa, com a asserção
  lendo a frontier do SSOT e não de um literal.
- `python3 tests/run_validators.py` em exit 0; baseline de partida 1233 testes em 26
  validadores.
- Nenhum código de erro público muda de string.
- Nenhuma tabela por versão perde a chave da versão anterior.
- Versão do plugin incrementada nos oito lugares que o validador de distribuição fixa,
  antes de merge.

## WHY

**Valor.** O Gauntlet está inacessível no próprio repositório que o publica: a frontier que
a produção materializa é recusada pela CLI que deveria executá-la. Sem isso, a sequência de
onze etapas não pode ser iniciada por ninguém que esteja na versão corrente.

**Evidência.** A CLI declara a frontier ativa numa constante e injeta o gate da versão
anterior no mesmo arquivo, a poucas centenas de linhas de distância. A suíte não pegou
porque as cinco famílias de teste que exercitam `gauntlet-init` geram a própria entrada com
a mesma biblioteca que a CLI usa para lê-la — writer e reader concordam por construção, e o
par não prova nada. Nenhum teste menciona a frontier ativa.

**Restrições.** O runtime precisa continuar sabendo **ler** versões que já não executa:
recibos de ativação são imutáveis e são revalidados depois deste build, e oito dos nove
bundles deste repositório declaram a versão anterior. Separar "executa" de "sabe ler" é
pré-requisito, não refinamento. A entrega altera `plugin/**`, então o bump de versão é
pré-requisito de merge; a leitura SemVer proposta é major, por remoção de capacidade, e
fica como assunção a confirmar.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
