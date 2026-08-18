# PLAN-CONTEXT

## FASE-001 — Triagem selada
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
A lógica pura vive em um módulo de core carregado por caminho, que não importa o CLI, não abre arquivo, não chama git e não cria processo filho: ele recebe texto que a fronteira pública já leu por descritor sem seguir symlink, para que as primitivas de segurança continuem existindo em um lugar só. O comando é pré-ciclo como o preflight — roda antes de existir work item, não pega lock e não lê bundle — e é preview por padrão, como todo comando mutante deste repositório.

A verificação do laudo é estrutural antes de semântica: primeiro a presença das seções obrigatórias, depois o status declarado. O status é casado por frase literal, sem acento removido e sem normalização, e a frase de negação é testada antes da de afirmação, porque uma ordem ingênua leria "não comprovada ainda" como prova. A matriz de evidência é uma tabela declarativa por rota, com um conjunto exigido e um conjunto proibido, e a recusa lista os campos exatos.

O registro é gravado por escrita atômica com fsync e rename, sob um selo que cobre o documento inteiro menos ele próprio. A releitura recomputa o selo antes de comparar conteúdo, para que adulteração e divergência de decisão sejam diagnósticos diferentes. Códigos são cunhados em SCREAMING_SNAKE no módulo de core e traduzidos para o vocabulário público na fronteira do CLI, pelo tradutor genérico que já existe.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
