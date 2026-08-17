# FASE-006 — Detecção de skill sombreada no preflight

- phase: FASE-006
- state: planned
- roadmap: ROADMAP.md#FASE-006
- context-refs: Backlog operacional
- ADRs: none
- BLs: none

## WHY
O defeito foi observado ao vivo. Uma skill pessoal com o mesmo nome do plugin, instalada como atalho no diretório de skills do usuário, venceu a do plugin na resolução do comando de sessão. A versão pessoal não tem os subcomandos do protocolo, então o comando pedido não existia. Nada avisou: a descoberta veio de o argumento não fazer sentido para a skill que respondeu.

O modo de falha é silencioso e se reproduz em qualquer ambiente novo que tenha as duas instaladas. Um operador menos atento concluiria que o plugin está quebrado, e não que está sombreado.

O plugin já inspeciona e reporta o ambiente antes de iniciar um trabalho, então é ali que a checagem pertence. É o mesmo tipo de pergunta que ele já faz sobre as demais exigências externas.

O alcance fica nos nomes que o próprio plugin publica, porque é sobre eles que ele tem autoridade legítima. Opinar sobre nomes de terceiros geraria alarme falso e obrigaria a acompanhar o layout de cada agente hospedeiro.

Remover é mutação no ambiente do operador, fora do repositório. Um comando de diagnóstico não pode apagar arquivo por efeito colateral, e uma remoção automática destruiria uma skill pessoal que talvez o operador quisesse apenas renomear.

## WHAT
- delivery-units: DU-006
- development-type: platform-devops

A inspeção de ambiente passa a detectar quando um nome publicado pelo plugin está sombreado, e sabe desfazer isso sob autorização explícita.

Resultado observável: a inspeção reporta cada nome do plugin que esteja também presente como skill pessoal ou de projeto, dizendo onde está e para onde aponta quando for atalho; o relato aparece tanto na inspeção isolada quanto na criação de um trabalho; por padrão informa sem impedir; e existe uma autorização explícita que remove a cópia sombreadora.

Atores: o operador que instala o plugin em máquina nova, e o operador que já tem uma skill pessoal homônima de antes.

Cenários que precisam passar:
- ambiente limpo, sem sombra, que não deve gerar alarme;
- nome sombreado por skill pessoal, reportado;
- nome sombreado por skill de projeto, reportado;
- sombra na forma de atalho, reportada com o destino resolvido;
- execução padrão, que informa e não impede;
- execução com autorização explícita, que remove e confirma a remoção;
- nome de terceiro duplicado, que precisa ser ignorado.

Escopo excluído: colisão entre skills de terceiros, julgamento sobre nomes de outros plugins e remoção sem autorização.

Critérios de aceite: sombra detectada e reportada sem impedir por padrão; remoção apenas sob autorização explícita; nenhum alarme para nome fora do conjunto publicado pelo plugin; comportamento verificável nos três sistemas da matriz, com diretórios sintéticos e sem tocar o ambiente real.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
