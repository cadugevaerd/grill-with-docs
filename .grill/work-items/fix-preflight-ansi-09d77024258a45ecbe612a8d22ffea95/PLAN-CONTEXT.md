# PLAN-CONTEXT

## FASE-001 — Detecção de extensão pelo registro
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
A detecção deixa de parsear a saída de terminal e passa a ler o registro do spec-kit. A função que hoje tokeniza texto livre com `re.findall` sobre a saída inteira é substituída por leitura de JSON com chave exata: o slug é chave do mapa de extensões, então não existe mais superfície onde uma palavra de linha de descrição possa casar como se fosse um identificador. Isso elimina as duas classes de falha de uma vez — o escape ANSI que produzia `2mgit` e o casamento por substring que produzia o falso positivo em `bugfix` — porque nenhuma das duas depende de qual regex se escolhe, e sim de estar tokenizando texto de apresentação.

O seam de teste muda junto. Hoje a função recebe `Toolchain` e roda subprocess; passa a receber um caminho e ler arquivo, então o teste vira fixture JSON em vez de mock de processo filho. Isso mantém a suíte offline e sem exigir `specify` real, que é restrição dura da matriz de CI. O `Toolchain` continua existindo para as demais dependências de binário e não é removido.

A leitura é fail-closed por construção. `schema_version` é verificado antes de qualquer acesso ao conteúdo, e ausência do arquivo, JSON inválido ou versão de schema não reconhecida são o **mesmo** desfecho: o registro é declarado não legível. Nesse caso a presença não foi observada, e afirmar ausência seria inventar evidência — então os itens de extensão recebem status próprio, distinto de ausente, sem remediação de instalação. A causa raiz aparece uma vez, como dependência declarada de tipo caminho no manifest, ao lado dos dois artefatos de caminho que já existem lá.

A avaliação por extensão é presença da chave **e** `enabled`. Registrada porém desabilitada é não utilizável e bloqueia, mas o motivo observado passa a governar a remediação: a função que hoje só renderiza o campo `install` do manifest ganha um caminho condicional, para que o operador receba `enable` quando o problema é estado e `add` quando o problema é ausência. Emitir `add` para algo já instalado é a mesma família de erro que originou este trabalho, e repeti-la em outro ramo do código anularia a correção.

O status novo entra no schema de dependências sem trocar o identificador de versão do schema, e o preço disso é pago dentro do repositório: os validadores que enumeram status exaustivamente são atualizados na mesma fase, e a suíte é o que impede a adição de passar silenciosa. Consumidor que testa igualdade com `present` permanece correto sem mudança.

O bump acompanha a alteração de `plugin/**` e é replicado nos oito lugares que o validador de distribuição fixa — quatro manifests, a constante do próprio validador e três headings de documentação —, com entrada correspondente no changelog.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
