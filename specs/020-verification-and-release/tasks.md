# Tasks: Verificação e publicação

- [x] T001 Conferir que cada defeito da milestone tem regressão nomeada
- [x] T002 Conferir a versão nos oito lugares
- [x] T003 Conferir que casos dependentes de plataforma pulam em vez de falhar
- [x] T004 Rodar a suíte completa e medir estabilidade
- [x] T005 Corrigir o provisionamento indevido de backlog pelo `init`
- [x] T006 Acrescentar `--db` a `init`, `preflight` e `backlog-adopt`
- [ ] T007 Matriz de portabilidade verde nos três sistemas — depende de a branch subir
- [ ] T008 Publicação — depende de autorização explícita do operador

## Resultado

Suíte final: **1028 testes, exit 0**. Treze de treze defeitos com regressão nomeada.

### Dois defeitos encontrados por esta fase

Um teste flaky foi o gatilho. Ele passava ou falhava conforme o provisionamento tivesse sucesso, e investigar a intermitência revelou que `init` **criava** um backlog quando não encontrava um — satisfazendo o pré-requisito ao inventar a própria coisa que deveria verificar. Em execução de teste isso produziu 14 backlogs de lixo no banco real do operador, todos com zero itens e ligados a caminhos temporários já inexistentes.

A causa raiz é a mesma que a FASE-001 já tinha corrigido para `backlog-sync`: sem `--db`, todo comando alcança o banco real. `init`, `preflight` e `backlog-adopt` ganharam a flag, e a classe de teste da FASE-003 passou a apontar para banco descartável.

Verificado depois da correção: execução completa da suíte deixa a contagem do backlog real inalterada.

T007 e T008 não são executáveis localmente e permanecem abertas por dependência externa declarada.
