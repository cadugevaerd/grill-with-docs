# FASE-001 — Modelo mais recente: Codex por família e especialista Claude em Opus

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: família de modelo, catálogo local do Codex, slug resolvido, tier, papel de especialista, alias de modelo Claude
- ADRs: ADR-0001, ADR-0002
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

**Resultado observável.** Quando o GWD despacha um worker ou um especialista (autor/revisor) no runtime Codex, o modelo usado é o slug listado de menor `priority` no catálogo local do Codex para a família daquele tier/papel; uma geração nova só é escolhida quando o catálogo a prefere, sem editar o plugin. Com o catálogo atual: tier small → `gpt-6-luna`, tier medium → `gpt-5.6-terra`, tier large → `gpt-6-sol` (bloqueado para worker, como hoje), autor/revisor → `gpt-6-astra`. O modelo efetivamente escolhido fica registrado. No runtime Claude, autor e revisor especialista passam a ser Opus pelo alias `opus` (autor `xhigh`, revisor `high`), que acompanha a geração mais recente; `fable` deixa de ser exigido.

**Atores.** O líder GWD que declara workers e prepara atividades de especialista; a suíte de validadores offline.

**Cenários.**
1. Catálogo com `gpt-6-luna` (`priority=0`) e `gpt-5.6-luna` (`priority=10`) listados → tier small resolve para `gpt-6-luna` e o registro do worker guarda esse slug; com prioridades invertidas, mantém `gpt-5.6-luna` apesar da geração mais nova estar listada.
2. Catálogo sem terra da geração 6 → tier medium resolve para `gpt-5.6-terra` se ela tiver a menor `priority` entre as terras listadas; uma terra mais nova só a substitui se tiver `priority` menor.
3. Papel autor/revisor Codex → resolve para o astra listado de menor `priority`; a checagem de modelo efetivo do especialista compara com esse slug.
4. Catálogo ausente ou ilegível → recusa nomeada `TIER-MODEL-UNRESOLVED` antes de qualquer worktree, lease ou payload, sem usar modelo antigo.
5. Família sem nenhum slug listado (ex. só oculto) → mesma recusa nomeada.
6. Tier cuja família é frontier para ator worker → continua `FRONTIER-MODEL-FORBIDDEN`, antes de qualquer efeito.
7. Especialista autor/revisor no runtime Claude → exige `opus` com `xhigh`/`high`; pedido ou efetivo `fable` é recusado como par divergente.
8. Tiers de worker no runtime Claude (`haiku`/`sonnet`/`opus`) e recomendação do líder → comportamento atual, sem diferença.

**Escopo excluído.** Tiers Claude e seus aliases; slug fixo de modelo Claude; recomendação textual do líder; configuração global do Codex do usuário (incluindo o `model` do `config.toml`); alias de API `gpt-6`; qualquer acesso à rede; instalar ou atualizar o Codex.

**Critérios de aceite.**
- Os oito cenários cobertos por validadores offline, com fixture derivada da saída real do catálogo Codex 0.155.1 e sem depender de `codex`, `claude`, `node` ou rede reais; incluem caso de geração nova listada sem menor `priority`.
- Nenhum slug de geração fixado no código ou nos validadores como expectativa de despacho; o contrato fixa famílias no Codex e o alias `opus` no par de especialista Claude.
- Documentação pública (tabela de papéis e texto de autoria técnica) sem `fable` como par exigido.
- Work items e contextos já selados com a policy de orquestração atual continuam verificáveis.
- `python3 tests/run_validators.py` em exit 0 e `git diff --check` limpo.

## WHY

**Valor.** Hoje cada geração nova de modelos Codex exige edição manual do plugin, e enquanto ninguém edita o GWD despacha a geração anterior em silêncio: 7 workers reais rodaram `gpt-5.6-terra` com `gpt-6-*` disponível. O Claude já recebe o mais recente pelos aliases nos tiers; o Codex não tem alias equivalente. Por decisão humana, o modelo de ponta do Claude para autoria e revisão de julgamento passa a ser o Opus, e não mais `fable`.

**Evidência.** Triagem `tri-latest-models` (feature, medium) com laudo `code-debug` de causa raiz comprovada em `.grill/triage/latest-models-debug.md`; pesquisa de aliases no codex-cli 0.155.1 registrada no ADR-0001; decisão humana do par Claude registrada no ADR-0002.

**Restrições.** Fail-closed sem fallback para modelo antigo; somente biblioteca padrão; o core nunca baixa bytes; sem subprocesso novo; o piso não-frontier dos workers continua valendo; bump obrigatório do plugin nos oito pontos de versão e release correspondente.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
