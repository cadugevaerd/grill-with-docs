## Review Report

Verdict: APPROVE
Source fingerprint: tree eda0132e795fba921a0b21499e1f8a93675e688f7666a6723890beb934960cac / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan a67563382c5ff689ce514ad7e20a4b31422ccb06a7f7b7df68d20da86d2c110d

### Limitação de independência

Sem revisor independente, como nas três fases anteriores.

### Test Quality

21 para 32 testes no validador de dependências. Cobrem ambiente limpo, sombra pessoal, sombra de projeto, nome de terceiro ignorado, atalho com destino, atalho quebrado, sombra múltipla, diretório ausente, remoção de atalho preservando destino, remoção de diretório e falha de remoção.

O caso que mais importa é o do atalho quebrado, porque é o que uma implementação ingênua perde: `exists()` é falso para ele e o esconderia. O teste falharia contra a ordem errada de checagem.

Os testes usam `HOME` injetado e diretórios sintéticos, então nunca tocam o ambiente do operador — o que importa aqui mais que em outras fases, já que o código apaga arquivos.

### Runtime Correctness

`is_symlink()` antes de `exists()` é a decisão correta e está comentada no código com o motivo.

A remoção usa `unlink` para atalho e arquivo, e `rmtree` só para diretório real. Um atalho nunca é seguido, então o destino sobrevive — verificado por teste que confere o conteúdo do destino após a remoção.

Falha de remoção devolve `removed: False` com o tipo do erro, sem levantar, o que preserva o restante da inspeção.

Ponto examinado e considerado correto: o mesmo nome pode aparecer duas vezes quando o atalho e seu destino estão ambos em raízes pesquisadas. Não é duplicata espúria — os dois ocupam o nome, em lugares diferentes, e remover só um não resolve necessariamente. Reportar os dois é mais informativo que deduplicar.

### Readability

Três funções curtas, cada uma com uma responsabilidade. Os comentários explicam o defeito de origem e as duas armadilhas — a ordem das checagens e o perigo de seguir o atalho.

### Architecture

A verificação entra onde o ambiente já é inspecionado, sem mecanismo novo. `PUBLISHED_SKILLS` é uma tupla de um elemento hoje; se o plugin publicar mais nomes, o alcance acompanha sem mudança de código.

### Security

O código **apaga arquivos fora do repositório**, o que é a superfície mais sensível de toda a milestone. Três mitigações: só sob autorização explícita, só nomes que o plugin publica, e nunca seguindo atalho. Os testes exercitam a preservação do destino, que é a garantia que impede destruição colateral.

Não há interpolação em shell nem execução de conteúdo encontrado.

### Performance

Quatro verificações de caminho por nome publicado. Irrelevante.

### Critical Issues

Nenhum.

### Important Issues

Nenhum.

### Constitution References

- **Fail-closed sem waiver** — reportar sem bloquear é escolha declarada, não afrouxamento: recusar o preflight inteiro por causa de uma sombra esconderia o relatório de dependências que o operador foi buscar. O que exige autorização é a ação destrutiva.

### Final Recommendation

- APPROVE: run `/speckit.verify-review-ship.ship`

Ressalvas: sem revisor independente; SC-005 pendente da matriz de CI.
