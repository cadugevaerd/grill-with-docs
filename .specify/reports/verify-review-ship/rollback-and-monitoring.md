# Rollback e monitoração — 027 sucessão explícita de escopo

Evidência exigida por `ship.require_rollback_plan` e
`ship.require_monitoring_notes`. Escrita em `.specify/reports/verify-review-ship/`
porque é evidência de gate, da mesma classe de `verify.md` e `review.md`, e esse
caminho é excluído do source fingerprint — registrá-la não invalida a medição que
ela acompanha.

Entrega: v5.2.1, merge de `fix/reconcile-scope-succession` em `main`.

## Superfície de risco

A mudança **remove uma recusa**. Esse é o risco, e ele não é de disponibilidade
nem de dados: é de autorização ampla demais. Um defeito aqui não derruba nada —
deixa passar uma sobreposição de escopo que deveria bloquear, em silêncio.

Consequência de um falso positivo em campo: dois trabalhos não relacionados
reconciliam o mesmo caminho sem declarar relação, e o recibo global registra
ownership que ninguém declarou. Não corrompe recibo existente e não muda schema,
então o estrago é de governança, não de integridade.

O que **não** muda, e portanto não precisa de rollback: nenhum formato de
recibo, nenhuma migração, nenhum estado persistido novo, nenhum I/O novo.
Recibos gravados antes da 5.2.1 continuam legíveis sem conversão — travado por
`test_reconcile_succession_targeted_apply_is_byte_idempotent_and_reuses_prior_receipt`.

## Plano de rollback

A tag `v5.2.1` é imutável por cláusula constitucional (*Bump obrigatório do
plugin*: "nunca reutilize uma tag publicada"). Rollback portanto **não** é
apagar a tag nem reescrever a release; é publicar uma versão que reverte.

1. Reverter o merge em `main`, preservando o primeiro pai:
   `git revert -m 1 <sha-do-merge>`
2. Bump de correção para `5.2.2` nos oito pontos que
   `tests/validate_distribution.py` fixa, e entrada no `CHANGELOG.md` dizendo o
   que foi revertido e por quê.
3. Deixar o `publish.yml` criar tag e release da 5.2.2 no push para `main`. Não
   criar release à mão: a cláusula *Release obrigatória por versão* trata isso
   como contorno, não como conformidade.
4. Consumidores voltam ao comportamento anterior atualizando o plugin. Nenhum
   passo de migração é necessário nos dois sentidos, porque nenhum dado mudou de
   forma.

Custo estimado: um ciclo de publicação. Sem janela de indisponibilidade, porque
o plugin não é serviço.

Reversão parcial não faz sentido aqui e não deve ser tentada: o predicado e os
dois call sites são uma unidade. Reverter só o caminho targeted deixaria os dois
caminhos com regras diferentes, que é exatamente o que FR-008 proíbe.

## O que monitorar

**Imediatamente após o push**, no `publish.yml`:

- job `release`: a tag `v5.2.1` foi criada e a GitHub Release está ancorada
  exatamente no mesmo commit. Tag sem release é publicação incompleta.
- job `publish`: os marketplaces apontam para 5.2.1.
- `bump-gate.yml`: reporta em toda PR e não deve ficar mudo.

**Sinal de defeito em campo**, na ordem em que apareceria:

1. Um `reconcile` que **deveria** recusar e não recusa. O sintoma observável é
   um recibo gravado para um trabalho cujo escopo se sobrepõe a outro sem
   `depends-on-work` declarado entre os dois. Detecção: rodar `reconcile` sem
   `--apply` sobre o conjunto completo — a pré-visualização é read-only e lista
   todos os conflitos.
2. `SCOPE-OVERLAP` desaparecendo de casos onde nenhuma dependência foi
   declarada. É o inverso do defeito que a 5.2.1 corrige e o sinal mais direto
   de que a autorização vazou.
3. `ADR-CONFLICT` deixando de ser emitido quando há dependência direta. Seria
   regressão do isolamento que `test_reconcile_succession_preserves_targeted_path_refusals`
   trava; se aparecer em campo, é porque alguém moveu o laço para dentro do gate.

**Auditoria de contenção**, se qualquer um dos três aparecer: os recibos
gravados sob 5.2.1 estão em `.grill/global/receipts/`, e cada um preserva o
escopo do trabalho. Comparar pares de recibos por sobreposição de caminho contra
o `depends-on-work` de cada bundle diz exatamente quais foram autorizados
indevidamente, sem depender de log.

## Limite honesto desta monitoração

Não há telemetria: o plugin roda na máquina de quem o usa e não reporta nada. A
detecção descrita acima é **sob demanda**, feita por quem opera o reconcile, não
automática. O que substitui telemetria aqui é a cerca de testes negativos que
FR-012 tornou obrigatória — ausência, terceiro e transitividade têm caso
dedicado, então uma regressão que reintroduza o vazamento reprova na suíte antes
de chegar a campo.
