# Converge — FASE-002

## O que entrou

Uma condição, em `grill_status.py`. A comparação de head saiu; a de branch passou a valer só quando o work item não é terminal **e** o branch registrado ainda existe.

## O refinamento que o uso impôs

A spec original recortava só por "não terminal". Aplicada, a consulta real mostrou:

```
antes do refinamento:
  feature-release-repo-sync (terminal)     findings=[]                      ← corrigido
  fix-high-defects          (em andamento) findings=['LIVE-VS-RECORDED']   ← ainda alarmando
```

O branch da criação, `fix/high-defects`, tinha sido apagado no ship da FASE-001. Como o protocolo entrega uma fase por branch, todo work item multi-fase perde o branch registrado na primeira entrega — e o defeito voltaria da segunda fase em diante.

```
depois:
  verdict: OK
  feature-release-repo-sync  findings=[]
  fix-high-defects           findings=[]
```

Primeira vez em toda a milestone que `status` devolve `OK`.

## Os quatro quadrantes

| work item | ramo registrado | leitura | alarme |
|---|---|---|---|
| em andamento | vivo | no ramo | não |
| em andamento | vivo | fora dele | **sim** |
| em andamento | apagado | qualquer | não |
| terminal | qualquer | qualquer | não |

Só um quadrante alarma, e é o único em que ler o bundle do lugar errado é anomalia.

## Suíte

309 testes, exit 0. `validate_status_contract` 28 → 34.
