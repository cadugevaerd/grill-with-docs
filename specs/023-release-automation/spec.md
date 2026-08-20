# Feature Specification: Release automática por versão publicada

**Origem**: cláusula `Release obrigatória por versão`, constituição v1.2.0.
**Gap medido**: existe uma única release, `v2.4.1` (2026-08-10), enquanto as tags seguiram até
`v3.3.2`. `publish.yml` cria a tag anotada e para aí — o job se chama "Tag da release" e é
literalmente só isso.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Merge em main publica versão completa (Priority: P1)

Um merge para `main` que altera `plugin/**` com versão nova precisa deixar tag **e** release.

**Por que P1**: é a cláusula constitucional nova. Sem automação, ela é convenção, não gate — e a
dívida atual prova que convenção não segura.

**Teste de aceitação**: o job `release` de `publish.yml` cria a release ancorada na mesma tag, e o
passo roda depois da criação da tag e antes de qualquer escrita em marketplace.

### User Story 2 - Reexecução não quebra nem duplica (Priority: P1)

Reexecutar a publicação da mesma versão — `workflow_dispatch`, retry de job, push que reentra — não
pode falhar nem criar release duplicada.

**Por que P1**: o passo da tag já é idempotente por desenho; um passo de release que aborta em
"already exists" tornaria toda reexecução vermelha e treinaria o time a ignorar o pipeline.

**Teste de aceitação**: release já existente é sucesso com mensagem, não erro.

### User Story 3 - Release mentirosa reprova (Priority: P1)

A release precisa estar ancorada no commit que a publicação declara.

**Por que P1**: release apontando para outro commit distribui coisa diferente da que foi verificada,
e é exatamente o tipo de divergência que a cláusula "Evidência antes de afirmação" proíbe.

**Teste de aceitação**: se a tag da release resolver para commit diferente de `SHA`, o passo falha.

### Edge Cases

- Tag existe mas release não — estado atual do repositório: o passo cria só a release.
- Tag ausente: `--verify-tag` recusa criar release órfã.
- `workflow_dispatch` sem `github.event.before`: o passo de release não depende desse campo.

## Requirements *(mandatory)*

- **FR-001**: o job `release` MUST criar a release da tag da versão resolvida.
- **FR-002**: o passo MUST rodar depois de `Criar a tag, recusando remarcação`.
- **FR-003**: release preexistente MUST ser sucesso, nunca conflito.
- **FR-004**: o passo MUST falhar quando a tag resolver para commit diferente do publicado.
- **FR-005**: o passo MUST recusar criar release sem tag correspondente (`--verify-tag`).
- **FR-006**: as notas MUST ser geradas pelo GitHub (`--generate-notes`); nada de nota escrita à mão
  no pipeline, que seria texto não verificável.
- **FR-007**: MUST usar `${{ github.token }}` com a permissão `contents: write` que o job já declara;
  nenhum segredo novo.
- **FR-008**: a release MUST existir antes de o job `publish` apontar os marketplaces — garantido por
  `needs: release`.

## Success Criteria *(mandatory)*

- **SC-001**: contrato de workflow cobre criação, ordem, idempotência e ancoragem.
- **SC-002**: nenhuma dependência nova e nenhum segredo novo.
- **SC-003**: suíte segue verde e cresce com os testes do contrato novo.

## Assumptions

- Notas geradas pelo GitHub são suficientes; changelog curado é decisão futura.
- Releases faltantes de `v2.4.2` a `v3.3.2` seguem como dívida declarada — a cláusula vale das
  versões novas em diante, por decisão registrada na emenda.
