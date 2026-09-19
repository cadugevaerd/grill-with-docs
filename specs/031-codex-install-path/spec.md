# Feature Specification: Observar a instalação Codex do i-have-adhd

**Feature Branch**: `cadugevaerd/feat-new-subagents`

**Created**: 2026-09-19

**Status**: Draft

**Input**: Handoff `FASE-001-SPECIFY-HANDOFF.md` do work item `fix-codex-install-path-693af70e339f4e299fa51605d45bb1ff`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entrar no fluxo GWD numa sessão Codex com o estilo aprovado instalado (Priority: P1)

Quem conduz uma sessão Codex e invoca a entrada do fluxo GWD (iniciar ou retomar), com a cópia aprovada do componente de apresentação instalada e habilitada, chega ao pedido de leitura da referência de apresentação, igual ao que acontece numa sessão Claude, em vez de ser recusado por instalação indeterminada.

**Why this priority**: sem isso, nenhuma entrada GWD funciona no Codex, e a validação funcional dos dois runtimes (casos C1 e C2 da matriz de estilo) fica bloqueada.

**Independent Test**: fornecer ao observador de apresentação a listagem nativa real do Codex, que não informa caminho de instalação, com a cópia aprovada presente no local correspondente, e confirmar que a instalação é reconhecida e que a entrada segue para o pedido de leitura.

**Acceptance Scenarios**:

1. **Given** uma sessão Codex cuja listagem nativa declara o componente instalado, na versão aprovada, e a cópia correspondente existe com o conteúdo aprovado, **When** a entrada GWD avalia a apresentação, **Then** a instalação é reconhecida como presente e a entrada chega ao pedido de leitura da referência.
2. **Given** a mesma sessão, **When** a entrada GWD é repetida sem nenhuma mudança, **Then** o resultado é idêntico.

---

### User Story 2 - Continuar recusando quando a evidência não sustenta a instalação (Priority: P1)

Quem conduz uma sessão Codex continua sendo recusado sempre que a listagem nativa ou o estado em disco não sustentam que a cópia aprovada está instalada: por instalação indeterminada quando a cópia não pode ser localizada, e por conteúdo incompatível quando a cópia existe mas difere do aprovado, exatamente como já acontece no Claude.

**Why this priority**: o fluxo é fail-closed; ampliar a evidência aceita não pode abrir aceite de instalação falsa.

**Independent Test**: variar um elemento da evidência por vez e confirmar que cada variação mantém a instalação não reconhecida.

**Acceptance Scenarios**:

1. **Given** a listagem nativa declara o componente como não instalado, **When** a entrada GWD avalia a apresentação, **Then** a instalação não é reconhecida e a entrada é recusada.
2. **Given** a listagem nativa declara o componente instalado mas não existe cópia no local correspondente, **When** a entrada GWD avalia, **Then** a instalação não é reconhecida e a entrada é recusada.
3. **Given** a cópia existe mas o conteúdo da referência de apresentação difere do aprovado, **When** a entrada GWD avalia, **Then** a entrada é recusada por conteúdo incompatível, pela mesma verificação de conteúdo já aplicada ao Claude.
4. **Given** a entrada da listagem nativa não traz algum dos dados que identificam a cópia (origem, nome ou versão), **When** a entrada GWD avalia, **Then** a instalação não é reconhecida e a entrada é recusada.

---

### User Story 3 - Sessões Claude inalteradas (Priority: P2)

Quem conduz uma sessão Claude obtém exatamente o mesmo resultado de antes, porque a listagem nativa do Claude já informa o caminho da instalação.

**Why this priority**: regressão no runtime que já funciona anularia o ganho.

**Independent Test**: repetir os casos de apresentação existentes do Claude e confirmar resultados idênticos.

**Acceptance Scenarios**:

1. **Given** uma sessão Claude com listagem que informa o caminho, **When** a entrada GWD avalia a apresentação, **Then** o resultado é o mesmo produzido antes desta correção.

---

### Edge Cases

- Listagem nativa com mais de uma entrada para o componente: continua não reconhecida (ambígua), como hoje.
- Diretório de configuração do Codex em local não padrão, declarado pelo ambiente: o local correspondente segue a mesma regra já usada pela verificação prévia de dependências.
- Versão listada diferente da versão aprovada, com cópia daquela versão presente: a política de compatibilidade existente decide; esta correção não muda a política.
- A listagem de uma versão futura do Codex passa a informar o caminho: o caminho informado continua valendo e tem precedência.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: No runtime Codex, o sistema DEVE reconhecer a instalação do componente de apresentação quando a listagem nativa declara o componente instalado e identifica origem, nome e versão, e a cópia correspondente existe no local de cache do Codex com a referência de apresentação no conteúdo aprovado.
- **FR-002**: O sistema DEVE manter a instalação não reconhecida (instalação indeterminada) quando o componente não estiver declarado instalado, faltar dado de identificação ou a cópia não existir no local correspondente; e DEVE recusar por conteúdo incompatível, pela verificação de conteúdo já existente e comum aos dois runtimes, quando a cópia existir com conteúdo diferente do aprovado.
- **FR-003**: O sistema DEVE usar a mesma regra de localização do cache do Codex já usada pela verificação prévia de dependências, inclusive o diretório de configuração declarado pelo ambiente.
- **FR-004**: Quando a listagem nativa informar o caminho da instalação, o sistema DEVE continuar usando esse caminho, com o comportamento atual; um caminho informado porém inválido (não absoluto) mantém a instalação não reconhecida e NÃO DEVE ser substituído pelo caminho composto de FR-001.
- **FR-005**: O comportamento no runtime Claude NÃO DEVE mudar.
- **FR-006**: O sistema NÃO DEVE executar processo adicional nem acessar a rede para essa decisão; o comando nativo exigido permanece o mesmo.
- **FR-007**: A validação automatizada DEVE cobrir os cenários das histórias 1 a 3 usando como entrada a saída real da listagem nativa do Codex 0.154.0, capturada da ferramenta, sem depender de Codex, Claude, node ou rede reais.
- **FR-008**: A entrega DEVE incrementar a versão do plugin de 6.0.1 para 6.0.2 em todos os pontos de versão do contrato de distribuição e publicar a release correspondente.
- **FR-009**: Os dados de identificação usados para localizar a cópia (origem, nome e versão) DEVEM ser aceitos somente como nomes simples: vazio, separador de diretório, `.` ou `..` mantêm a instalação não reconhecida, para que a localização nunca aponte fora do cache do Codex.

### Key Entities

- **Listagem nativa**: saída do comando de listagem de plugins do runtime, executado pela própria sessão; fonte dos dados de identificação do componente.
- **Instalação reconhecida**: estado em que o eixo de instalação da apresentação é `present`, com versão e referência de leitura definidas.
- **Referência de apresentação aprovada**: arquivo da skill do componente cujo conteúdo corresponde ao hash aprovado pela política.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com a cópia aprovada instalada, 100% das entradas GWD numa sessão Codex chegam ao pedido de leitura da referência, contra 0% hoje.
- **SC-002**: 100% das variações de evidência incompleta ou divergente (histórias 2.1 a 2.4) são recusadas: 2.1, 2.2 e 2.4 por instalação indeterminada, 2.3 por conteúdo incompatível.
- **SC-003**: Zero diferenças de resultado nos casos de apresentação Claude existentes.
- **SC-004**: A suíte completa de validadores do projeto passa sem nenhum validador desativado ou afrouxado.
- **SC-005**: A reexecução do caso C1 da matriz de estilo numa sessão Codex supervisionada chega ao pedido de leitura; essa evidência é registrada no work item de origem e não é critério de aceite desta entrega.

## Assumptions

- A listagem nativa do Codex 0.154.0 informa origem (`marketplaceName`), nome e versão do componente, e o Codex materializa plugins instalados no cache organizado por origem, nome e versão (ADR-0001 do work item).
- O Codex não oferece outro comando que exponha o caminho da instalação.
- A versão publicada corrente é 6.0.1.
- As demais lacunas registradas no ensaio T029 estão fora do escopo e têm work items próprios.
