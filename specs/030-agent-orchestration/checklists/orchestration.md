# Qualidade dos requisitos: orquestração e stack GWD

**Purpose**: Avaliar completude, clareza, consistência e mensurabilidade dos oito resultados aprovados antes de produzir tasks. Esta checklist avalia documentos, não comprova implementação.
**Created**: 2026-09-13
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md)

**Note**: Gerada pelo líder durante a invocação canônica de `speckit-checklist`. Profundidade padrão com ênfase nos riscos de perda de trabalho, continuidade, grants e alcance do estilo; destinada à revisão independente anterior a tasks. Escopo e audiência derivados do handoff e dos requisitos aprovados, sem nova decisão de produto.

## Completude

- [x] CHK001 Os momentos obrigatórios de limpeza incluem fechamento de etapa, wave e troca de CLI, inclusive intervalos elegíveis e especialistas somente leitura? [Completeness, Spec §FR-001–FR-002]
- [x] CHK002 Os critérios de preservação abrangem identidade incerta, trabalho não integrado, árvore suja, evidência exclusiva e falha, com motivo rastreável por recurso? [Completeness, Spec §FR-003–FR-004]
- [x] CHK003 A retomada está definida nos dois sentidos, na mesma worktree, preservando resultados aceitos e delimitando o trecho interrompido? [Completeness, Spec §FR-006–FR-007]
- [x] CHK004 O requisito de design inclui prévia visual corrente, revisão independente e aprovação humana dentro de plan, com exclusão explícita de trabalho sem frontend? [Completeness, Spec §FR-008–FR-010]
- [x] CHK005 Autoria de COMO e revisão de julgamento cobrem todas as atividades relevantes, incluindo requisitos, planos, tarefas, design, código e segurança? [Completeness, Spec §FR-011–FR-014]
- [x] CHK006 O padrão i-have-adhd abrange ambos os CLIs, início e retomada pela skill GWD atualizada, sem invocação manual? [Completeness, Spec §FR-021, §SC-008]

## Clareza e limites

- [x] CHK007 A recomendação Sol/Opus está distinguida da seleção obrigatória dos especialistas e de qualquer troca automática do modelo principal? [Clarity, Spec §FR-005, §FR-011, §FR-015]
- [x] CHK008 A definição de evidência separa valores solicitados, valores efetivos e afirmações não comprovadas, sem prometer prova criptográfica de execução? [Clarity, Spec §FR-015, §FR-020]
- [x] CHK009 A lista explícita de arquivos é definida como única autoridade do grant, incluindo arquivos novos, da raiz, subdiretórios e prefixo ./? [Clarity, Spec §FR-016–FR-017]
- [x] CHK010 O alcance projeto/fluxo GWD está definido sem ampliar o padrão a sessões externas ou modificar configurações alheias? [Clarity, Spec §FR-022, §SC-008]
- [x] CHK011 Presença/versão, habilitação, carregamento e comportamento possuem significados separados e critérios de evidência próprios? [Clarity, Spec §FR-023–FR-024]

## Consistência

- [x] CHK012 A reserva de coordenação ao líder é consistente entre participação especializada, grants e evidências de aceite? [Consistency, Spec §FR-012, §FR-019]
- [x] CHK013 A sequência de onze etapas e as classes congeladas permanecem consistentes com design frontend, tarefas fora do scheduler e o limite explícito de conjunto sem workers? [Consistency, Spec §FR-010, §FR-020; Plan §Grants e migração; contracts/task-files.md §DAG, brief e reconciliação]
- [x] CHK014 A exigência de independência dos revisores é compatível com atividades mistas e com validadores determinísticos que não substituem julgamento? [Consistency, Spec §FR-013–FR-014]
- [x] CHK015 O padrão de apresentação preserva integralmente conteúdo obrigatório, evidências e Ponytail, inclusive em documentos com mais de cinco itens? [Consistency, Spec §FR-022, §FR-024; Spec §Edge Cases]
- [x] CHK016 A suspensão humana do estilo permite continuar trabalho na mesma sessão após compactação, sem dispensar a stack nem contar como prova de estilo ativo, e a sessão nova retorna ao default? [Consistency, Spec §FR-021–FR-024; data-model.md §Estado do estilo GWD; contracts/integrations.md §Bootstrap local de apresentação nos dois CLIs]

## Critérios de aceite

- [x] CHK017 O aceite de limpeza exige confirmação por recurso e zero perda de trabalho/evidência, distinguindo tentativa de encerramento de sucesso? [Measurability, Spec §SC-001]
- [x] CHK018 O aceite de continuidade exige identidade preservada e zero duplicação de efeitos nos dois sentidos, além de recusa de concorrência e checkpoint incoerente? [Measurability, Spec §SC-002]
- [x] CHK019 Os critérios cobrem as quatro combinações de ambiente e início/retomada, tanto para recomendação principal quanto para estilo automático? [Coverage, Spec §SC-003, §SC-008]
- [x] CHK020 O aceite de frontend vincula a decisão humana à prévia atual e define impedimentos por pendência, rejeição ou alteração posterior? [Measurability, Spec §FR-009, §SC-005]
- [x] CHK021 O aceite dos grants define correspondência exata e ausência de autorização inferida, preservando DAGs selados? [Measurability, Spec §SC-006]
- [x] CHK022 O aceite do estilo exige sessões novas, respostas reais e controles externos nos dois ambientes, sem equiparar instalação ou hook aprovado a funcionamento? [Measurability, Spec §FR-024, §SC-008]

## Exceções, recuperação e dependências

- [x] CHK023 As recusas estão especificadas para identidade/capacidade incerta, modelo ou esforço divergentes e ausência de evidência, sem substituição silenciosa? [Coverage, Spec §FR-004, §FR-007, §FR-015, §FR-023]
- [x] CHK024 A adaptação de tarefas antigas e a recuperação preservam outputs aceitos e DAGs selados, sem repetir efeitos nem usar checkboxes como única prova? [Recovery, Spec §FR-006, §FR-018; contracts/task-files.md §Migração]
- [x] CHK025 As tarefas read-only/deferred mantêm barreiras de fase e aceite positivo definido, incluindo fases sem workers, última fase e retomada? [Coverage, Spec §FR-019–FR-020; contracts/task-files.md §DAG, brief e reconciliação]
- [x] CHK026 Os requisitos delimitam dependência ausente, incompatível, desabilitada, confiança pendente, compactação e insuficiência de prova, preservando o alcance local? [Edge Cases, Spec §FR-021–FR-024; Spec §Edge Cases]
- [x] CHK027 Estão explícitos os gates de versão, verify/review, autorização de ship e release pelo pipeline, bem como a distinção entre evidência atual de instalação e validação futura da integração? [Dependencies, Spec §FR-020, §SC-007; Spec §Assumptions]

## Notes

- Os itens começam pendentes; o revisor independente registra avaliação e referências antes de qualquer marcação positiva pelo líder.
- Aprovação documental não prova comportamento implementado. Os ensaios executáveis/live permanecem em [quickstart.md](../quickstart.md) para as etapas posteriores.

Avaliação independente: **GO, 27/27 PASS**, task_94dd224149e7 / ctx_a5cc085af588, gpt-6-astra/high solicitado=efetivo; mensagem msg_13188efb5085. O líder marcou os itens a partir desse retorno; relatório em `.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/CHECKLIST-REVIEW.md`. Nenhuma prova de implementação é inferida.
