# FASE-001 — Detecção de extensão pelo registro

- phase: FASE-001
- state: complete
- roadmap: ROADMAP.md#FASE-001
- context-refs: registro de extensões, detecção de extensão, falso negativo, falso positivo, present, missing, undetermined, remediação, bump obrigatório
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

O preflight passa a responder corretamente se cada extensão exigida pelo `WORKFLOW.md` está utilizável, e a responder com base no registro de extensões do spec-kit em vez da saída de terminal.

Atores: o operador que roda `preflight` ou `init`; e o agente automatizado que consome o relatório para decidir se prossegue.

Cenários e critérios de aceitação:

1. **Ambiente íntegro.** As quatro extensões exigidas estão registradas e habilitadas. O preflight reporta `OK`; `missing_required` não contém nenhum item de extensão; cada extensão traz a versão registrada em vez de nulo.
2. **Extensão ausente.** Um slug exigido não está no registro. O item é reportado como não utilizável, com motivo de ausência e remediação de instalação.
3. **Extensão desabilitada.** O slug está registrado com `enabled: false`. O item bloqueia, o motivo diz que está registrada porém desabilitada, e a remediação é habilitar — nunca reinstalar.
4. **Registro não legível.** O registro está ausente, corrompido, ou traz uma versão de schema que este código não reconhece. Os três casos têm o mesmo desfecho: nenhuma extensão é declarada ausente, os itens de extensão ficam com presença não observada e sem remediação de instalação, e a causa aparece **uma vez** como dependência de caminho faltante. Sob `--require-dependencies` isso bloqueia.
5. **Nenhum falso positivo por texto livre.** Nenhuma extensão pode ser dada como presente por casamento de palavra em descrição, título ou qualquer texto de apresentação.
6. **Suíte offline.** Os testes cobrem os cinco cenários acima sem exigir `specify`, `node` ou `backlogctl` reais e sem tocar a rede, coerentes com a matriz de CI de três sistemas operacionais e duas versões de Python.
7. **Contrato de distribuição.** A versão do plugin é incrementada e permanece idêntica nos oito lugares que o validador de distribuição fixa, com entrada correspondente no changelog.

Escopo excluído: manter em paralelo o parser da saída de `specify extension list`; dependências de tipo `runtime` e `binary`; o catálogo de confiança `.specify/extension-catalogs.yml`; hooks; qualquer instalação delegada.

## WHY
O preflight afirma hoje o que não observou. Com as quatro extensões instaladas e habilitadas, ele reporta três como ausentes e uma como presente — e essa única "presente" também está errada, porque casou uma palavra na descrição da extensão, não o identificador. O parser acerta zero das quatro pelo caminho correto.

O dano não é ruído de relatório. Sob `--require-dependencies` o ciclo trava com o ambiente íntegro. E o relato empurra o operador para a ação errada: diante de extensões "faltando", a leitura natural é que falta autorizar a fonte de instalação, o que leva a rodar o preflight com a flag que registra o catálogo community como confiável — quando esse catálogo já está registrado com `install_allowed: true` e o próprio preflight o reporta como presente. Um defeito de detecção que induz ampliação desnecessária de superfície de confiança é mais caro que o defeito em si. Esse foi o caminho realmente percorrido antes deste work item existir, e é o que ele fecha.

A cláusula **Evidência antes de afirmação** é o que está em jogo: um relatório que declara ausência sem tê-la observado não é evidência. Por isso "não sei" e "não está" precisam ser desfechos distintos, e por isso a remediação precisa seguir o motivo observado — mandar instalar o que já está instalado é a mesma falha em outro ramo.

Evidência de origem no backlog: SGD-16.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
