# Li-Vision — Geração e Anonimização de Dados (LGPD)

Módulo de privacidade do projeto **Li-Vision**: gera um dataset sintético com a mesma estrutura de dados que o aplicativo coleta na prática e aplica sobre ele um pipeline de anonimização compatível com a LGPD, com métricas que comprovam o resultado.

**Autores**

- Ana Beatriz Novais Pereira
- Andrei Nunes Pereira
- Carlos Eduardo Fernandades Farias

---

## Sumário

- [Por que este módulo existe](#por-que-este-módulo-existe)
- [Execução rápida](#execução-rápida)
- [Etapa 1 — Geração dos dados](#etapa-1--geração-dos-dados)
- [Etapa 2 — Anonimização](#etapa-2--anonimização)
- [Técnicas aplicadas](#técnicas-aplicadas)
- [k-anonimato e l-diversidade](#k-anonimato-e-l-diversidade)
- [Resultados](#resultados)
- [Arquitetura do código](#arquitetura-do-código)
- [Decisões técnicas](#decisões-técnicas)
- [Limitações](#limitações)

---

## Por que este módulo existe

O Li-Vision traduz LIBRAS para texto. Para treinar os modelos (MLP para sinais estáticos, GRU Bidirecional para dinâmicos), o aplicativo coleta amostras de gestos enviadas por colaboradores — e, junto com elas, uma quantidade considerável de dados pessoais.

O levantamento a seguir foi feito a partir dos tipos reais do aplicativo (`features/*/types.ts` e `services/`):

| Origem | Dados coletados |
|--------|-----------------|
| `auth` / `profile` | `user_id`, `full_name`, `email`, `avatar_url`, `role` |
| `collect/static` e `collect/dynamic` | 21 landmarks 3D da mão, `dataset_name`, `label` |
| `collect/ranking` | nome + total de amostras enviadas |
| dispositivo | modelo, versão do SO, IP, geolocalização, timestamps |
| WebSocket de inferência | gesto detectado, confiança, latência, duração da sessão |

O ponto mais sensível é o conjunto de landmarks. As proporções da mão — envergadura, comprimento dos dedos, razão entre polegar e indicador — são **estáveis por pessoa** e funcionam como impressão digital. Isso as enquadra como **dado biométrico**, categoria protegida pelo art. 5º, II da LGPD.

Um dataset assim não pode ser compartilhado com pesquisadores, publicado como benchmark ou usado fora do time sem tratamento. Este módulo faz esse tratamento.

---

## Execução rápida

**Requisitos:** Python 3.10+, `pandas`, `numpy`, `openpyxl`.

```bash
pip install pandas numpy openpyxl

# 1) Gera o dataset sintético (dados fictícios)
python gerar_dados.py

# 2) Anonimiza
python anonimizar.py
```

Saída:

| Arquivo | Conteúdo |
|---------|----------|
| `li_vision_dados_brutos.xlsx` | Dataset sintético com PII, simulando o banco real |
| `li_vision_dados_anonimizados.xlsx` | Versão anonimizada + 2 abas de auditoria |

### Parâmetros

```bash
# Volume de dados gerados
python gerar_dados.py --usuarios 500 --amostras 20000 --sessoes 3000

# Privacidade mais rigorosa: k maior, epsilon menor
python anonimizar.py --k 10 --epsilon 0.5
```

| Parâmetro | Padrão | Efeito |
|-----------|--------|--------|
| `--k` | 5 | Mínimo de pessoas por classe de equivalência |
| `--epsilon` | 1.0 | ε da privacidade diferencial — **menor = mais ruído = mais privado** |

---

## Etapa 1 — Geração dos dados

`gerar_dados.py` produz uma planilha com 6 abas que espelham a estrutura real do backend:

| Aba | Linhas | Origem no app |
|-----|--------|---------------|
| `usuarios` | 120 | `features/auth/types.ts`, `profile/types.ts` |
| `amostras_coleta` | 3.000 | `POST /collect/static`, `/collect/dynamic` |
| `sessoes_traducao` | 800 | `services/gestureWebSocket.ts` |
| `ranking` | 120 | `GET /collect/ranking` |
| `progresso_aprendizado` | 192 | `features/learning/types.ts` |
| `modelos_treinados` | 6 | ML Studio — `ModelInfo` |

Todos os dados são **fictícios**. Nenhum registro real de usuário é utilizado.

Alguns cuidados para que o dataset exercite o pipeline de forma realista:

- **Distribuição de Pareto** nas contribuições — poucos colaboradores respondem pela maior parte das amostras, como acontece em qualquer base de crowdsourcing.
- **CPFs com dígitos verificadores válidos** — formato correto, pessoas inexistentes.
- **Consistência interna** — o total de `samples` no ranking é calculado a partir das amostras, não sorteado.
- **Seed fixa (42)** — duas execuções produzem o mesmo arquivo.

---

## Etapa 2 — Anonimização

O pipeline processa cada aba em cinco etapas:

```
    ┌─────────────────────────────────────────────────────┐
    │  1. CLASSIFICAR                                     │
    │     Cada coluna → classe de risco + técnica         │
    │     (classificacao.py)                              │
    └───────────────────────┬─────────────────────────────┘
                            ▼
    ┌─────────────────────────────────────────────────────┐
    │  2. TRANSFORMAR                                     │
    │     Aplica a técnica coluna a coluna                │
    │     (registry.py → tecnicas.py)                     │
    └───────────────────────┬─────────────────────────────┘
                            ▼
    ┌─────────────────────────────────────────────────────┐
    │  3. DEDUPLICAR                                      │
    │     cidade + uf → ambas viram "regiao"; mantém uma  │
    └───────────────────────┬─────────────────────────────┘
                            ▼
    ┌─────────────────────────────────────────────────────┐
    │  4. IMPOR k-ANONIMATO                               │
    │     Generaliza e suprime combinações raras          │
    │     (kanonimato.py)                                 │
    └───────────────────────┬─────────────────────────────┘
                            ▼
    ┌─────────────────────────────────────────────────────┐
    │  5. MEDIR                                           │
    │     k-anonimato, l-diversidade, log de decisões     │
    │     (metricas.py)                                   │
    └─────────────────────────────────────────────────────┘
```

### Classificação de risco

Cada coluna é classificada em uma de quatro categorias:

| Classe | Significado | Exemplo |
|--------|-------------|---------|
| **Identificador direto** | Identifica sozinho uma pessoa | `full_name`, `cpf`, `email`, `device_id` |
| **Quase-identificador** | Não identifica sozinho; o cruzamento sim | `cidade` + `data_nascimento` + `device_model` |
| **Dado sensível** | Art. 5º II da LGPD | `genero`, `usa_libras`, biometria |
| **Não identificável** | Preservado integralmente | `label`, `confidence`, `n_frames` |

A classificação é por **regex sobre o nome da coluna**, avaliada em ordem — a primeira regra que casa vence. Toda a política está em [`classificacao.py`](livision_privacy/classificacao.py), num arquivo só, para que possa ser auditada sem ler o resto do código.

---

## Técnicas aplicadas

| Técnica | O que faz | Exemplo |
|---------|-----------|---------|
| **Supressão** | Remove a coluna | `cpf`, `telefone`, `avatar_url` → removidos |
| **Pseudonimização** | HMAC-SHA256 com sal secreto | `7` → `USR-225896CBD744` |
| **Mascaramento de nome** | Preserva iniciais e nº de tokens | `Ana Beatriz Silva` → `A. B. S.` |
| **Mascaramento de e-mail** | Preserva só o provedor | `ana.silva@gmail.com` → `a********@gmail.com` |
| **Generalização de IP** | Reduz para bloco /16 | `201.82.14.7` → `201.82.0.0/16` |
| **Generalização de data** | Timestamp → ano-mês | `2026-03-14 23:41:02` → `2026-03` |
| **Faixa etária** | Nascimento → faixa de 10 anos | `1990-05-10` → `30-39` |
| **Generalização geográfica** | Cidade/UF → macrorregião | `Curitiba` → `Sul` |
| **Generalização de aparelho** | Modelo + SO → plataforma | `iPhone 15 Pro` → `iOS` |
| **Agregação espacial** | lat/lon → grade de ~111 km | `-25.4284` → `-25.0` |
| **Bucketização** | Contínuo → faixas por quantil | `latência 247ms` → `180-320` |
| **Ruído Laplace (ε-DP)** | Privacidade diferencial | `envergadura 178.4` → `176.9` |

### Pseudonimização — por que HMAC e não hash simples

Um `SHA-256(user_id)` seria trivialmente reversível neste dataset: com apenas 120 usuários, basta testar os IDs de 1 a 120 e comparar os hashes. Segundos de trabalho.

O HMAC com sal secreto de 32 bytes elimina esse ataque — sem o sal, não há espaço de busca viável. E a função continua **estável**: a mesma entrada gera sempre a mesma saída, o que preserva o JOIN entre abas (o `user_id` do ranking continua batendo com o de `usuarios`).

O sal vem da variável de ambiente `LIVISION_ANON_SALT`. Sem ela, um sal aleatório é gerado a cada execução e **não é persistido** — irreversível, mas os pseudônimos mudam entre rodadas.

### Ruído Laplace — por que a biometria precisa dele

Pseudonimizar o `user_id` não basta. As medidas da mão são estáveis por pessoa: mesmo com o ID trocado, dá para agrupar todas as amostras que vieram da mesma mão apenas pela envergadura e pelas proporções entre dedos. Isso reconstrói o vínculo que a pseudonimização tentou cortar.

A privacidade diferencial resolve adicionando ruído calibrado:

```
ruído ~ Laplace(0, Δf/ε)     onde Δf = amplitude interquartil
```

Usamos a **amplitude interquartil** como sensibilidade porque ela é robusta a outliers — o range simples seria inflado por uma única medida extrema, gerando ruído excessivo.

O efeito: a distribuição agregada permanece útil para treinar os modelos (média de 177,7 px no bruto contra 176,3 px no anonimizado), mas o rastreamento individual quebra.

---

## k-anonimato e l-diversidade

### k-anonimato

**k** é o tamanho da menor classe de equivalência — o menor grupo de pessoas que compartilham exatamente a mesma combinação de quase-identificadores.

`k=1` significa que existe alguém único naquela combinação: reidentificável cruzando com qualquer base externa. `k=5` significa que cada pessoa está escondida entre pelo menos 4 outras idênticas.

**A imposição acontece em duas etapas**, e a ordem importa:

1. **Generalização por remoção.** Enquanto k estiver abaixo do mínimo, remove-se o quase-identificador de **maior cardinalidade**. O atributo mais granular é o que mais individualiza, então sai primeiro.
2. **Supressão residual.** Só então as células das classes que ainda ficaram abaixo de k são mascaradas com `*`.

A ordem não é detalhe de implementação. Numa versão anterior o código suprimia células diretamente, sem a etapa 1 — e o resultado foi a aba `usuarios` com 120 linhas **inteiramente mascaradas**. O k reportado era 120, mas era uma classe única de asteriscos: k alto no papel, utilidade analítica zero.

Suprimimos a **célula**, não a linha: as métricas de gesto e acurácia continuam válidas para análise, apenas o vínculo com a pessoa é cortado.

### l-diversidade

k-anonimato sozinho tem um ponto cego. Se todas as pessoas de uma classe compartilham o mesmo valor sensível, saber que alguém está na classe já revela esse valor — mesmo com k alto.

**l** mede quantos valores distintos de um atributo sensível existem dentro de uma classe. Os valores medidos nesta execução:

| Aba | Atributo | l |
|-----|----------|---|
| `usuarios` | `genero` | 1 |
| `usuarios` | `usa_libras` | 3 |
| `amostras_coleta` | `mao_dominante` | 2 |

O `l=1` em `genero` está reportado com transparência: existe pelo menos uma classe de equivalência homogênea quanto a gênero. Ver [Limitações](#limitações).

---

## Resultados

Execução com os parâmetros padrão (`k=5`, `ε=1.0`):

| Aba | Linhas | Colunas (entrada → saída) | k antes | k depois |
|-----|--------|---------------------------|---------|----------|
| `usuarios` | 120 | 22 → 12 | 1 | **7** |
| `amostras_coleta` | 3.000 | 30 → 25 | 1 | **76** |
| `sessoes_traducao` | 800 | 19 → 17 | 2 | **46** |
| `ranking` | 120 | 8 → 6 | 1 | **7** |
| `progresso_aprendizado` | 192 | 10 → 10 | 27 | **27** |
| `modelos_treinados` | 6 | 12 → 12 | — | — |

Todas as abas com dados pessoais atingiram **k ≥ 5**. Antes do tratamento, 96 dos 120 usuários eram registros únicos.

### Antes e depois

**Bruto:**

| user_id | full_name | email | cpf | cidade | device_model |
|---|---|---|---|---|---|
| 1 | Henrique Silva Andrade | henrique.andrade@hotmail.com | 196.001.338-67 | Curitiba | Xiaomi Redmi Note 12 |

**Anonimizado:**

| user_id | nome_mascarado | email_mascarado | ip_cadastro | plataforma | criado_em |
|---|---|---|---|---|---|
| USR-225896CBD744 | H. S. A. | h***************@hotmail.com | 186.3.0.0/16 | Android | 2026-02 |

### Verificações executadas

| Verificação | Resultado |
|-------------|-----------|
| Vazamento de nome, e-mail, CPF, telefone, IP ou device_id | **0 ocorrências** |
| `dataset_name` preservado | `ALFABETO_LIBRAS`, `GESTOS_DINAMICOS` |
| Distribuição de labels preservada | idêntica ao bruto |
| Média de envergadura (bruto → anonimizado) | 177,7 → 176,3 px |
| JOIN `ranking` → `usuarios` | 120/120 |

### Auditoria

O arquivo de saída inclui duas abas de rastreabilidade:

- **`_log_anonimizacao`** — uma linha por coluna processada: aba, nome original, classe de risco, técnica aplicada, nome de destino.
- **`_metricas_privacidade`** — por aba: k antes e depois, colunas removidas pelo k-anonimato, células suprimidas, registros únicos originais, l-diversidade.

---

## Arquitetura do código

O módulo é organizado por responsabilidade. A regra que guia a divisão: `tecnicas` não sabe o que é uma aba, `classificacao` não sabe transformar valores, e `pipeline` não sabe como uma técnica funciona.

```
data-privacy/
├── gerar_dados.py               CLI de geração
├── anonimizar.py                CLI de anonimização
└── livision_privacy/
    ├── config.py                Parâmetros e mapas. Só dados.
    ├── console.py               Encoding do terminal e formatação
    ├── io_excel.py              Único módulo que conhece openpyxl
    ├── classificacao.py         Decide O QUE cada coluna é
    ├── tecnicas.py              Implementa COMO transformar. Funções puras.
    ├── registry.py              Liga nome da técnica → implementação
    ├── metricas.py              Só MEDE privacidade
    ├── kanonimato.py            Só IMPÕE k-anonimato
    ├── pipeline.py              Orquestra. Não implementa nada.
    └── geracao/
        ├── vocabulario.py       Listas fictícias
        ├── fabricas.py          Uma função por aba
        └── sintetico.py         Ordem e dependências entre abas
```

Consequências práticas dessa separação:

- **Adicionar uma técnica** — escrever a função em `tecnicas.py` e registrá-la em `registry.py`. O pipeline não muda.
- **Auditar a política de privacidade** — ler `classificacao.py`, um arquivo só.
- **Trocar o formato de saída** (CSV, Parquet, banco) — reescrever `io_excel.py`. O pipeline devolve DataFrames e não sabe onde serão gravados.
- **Ajustar parâmetros** (nova UF, k padrão, nova aba) — editar `config.py`, sem tocar em código.
- **Testar** — cada camada roda isolada. As técnicas são funções puras, testáveis valor a valor.

---

## Decisões técnicas

Três escolhas que não são óbvias e cuja alternativa natural falharia.

### 1. Fronteira de token em vez de `\b` no regex

A classificação identifica colunas por regex sobre o nome. A escolha natural seria `\b` (fronteira de palavra), mas ela está **errada** aqui:

```python
re.search(r"\bnome\b", "colaborador_nome")   # None — não casa!
```

Em regex Python, `_` conta como caractere de palavra, então não há fronteira entre `colaborador` e `nome`. Com `\b`, a coluna `colaborador_nome` não seria classificada como PII e **vazaria intacta** — foi exatamente o que aconteceu antes da correção, em três abas.

A fronteira real em snake_case é o início da string, o fim, ou `_`:

```python
def _termos(*termos):
    return r"(?:^|_)(?:" + "|".join(termos) + r")(?:_|$)"
```

### 2. Substring solta destrói dados

O erro simétrico é não ancorar nada. Dois casos reais observados neste dataset:

| Padrão ingênuo | Casa indevidamente com | Consequência |
|---|---|---|
| `rg` | `enve`**`rg`**`adura_mao_px` | Medida biométrica suprimida como se fosse um RG |
| `name` | `dataset_`**`name`** | Nome do dataset mascarado como nome de pessoa |

Por isso existe uma **allowlist** avaliada antes de tudo, protegendo colunas cujo nome lembra PII mas descreve um objeto do domínio: `dataset_name`, `model_name`, `label`, `gesture`. A coluna `name` pura fica de fora da allowlist — na aba `ranking` ela é o nome da pessoa.

### 3. Coordenadas em grade de 111 km, não 11 km

Arredondar lat/lon para 1 casa decimal (~11 km) parece suficiente, mas ainda resolve a cidade: o par `(-25.4, -49.3)` é Curitiba sem ambiguidade. Isso **anularia** a generalização cidade → macrorregião feita em outra coluna — de nada adianta trocar `Curitiba` por `Sul` se as coordenadas ao lado entregam a cidade.

O padrão é 0 casas decimais (~111 km), e as coordenadas entram na lista de quase-identificadores do k-anonimato.

### Nota sobre o registro de técnicas

`registry.aplicar()` levanta `KeyError` para técnica não registrada, em vez de cair num fallback silencioso do tipo `HANDLERS.get(tecnica, _manter)`.

A diferença é relevante: durante a refatoração, `ruido_laplace` ficou sem registro. Com o `raise`, o pipeline abortou apontando a chave faltante. Com o fallback, as cinco colunas biométricas teriam sido **publicadas sem ruído**, em silêncio. Um typo na tabela de classificação vira falha visível, não vazamento.

---

## Limitações

Pontos que este pipeline **não** resolve, declarados abertamente:

**l-diversidade = 1 em `genero`.** Existe pelo menos uma classe de equivalência em que todos compartilham o mesmo gênero. O k-anonimato protege contra identificar *quem* é a pessoa, mas não impede inferir esse atributo a partir da classe. Corrigir exigiria impor l-diversidade como restrição ativa, ao custo de mais supressão.

**Sal efêmero por padrão.** Sem `LIVISION_ANON_SALT` definida, os pseudônimos mudam a cada execução. Isso é seguro, mas impede vincular exportações feitas em datas diferentes. Definir a variável a partir de um cofre de segredos resolve — e reintroduz o risco de reversão caso o sal vaze.

**Landmarks brutos fora do escopo.** O dataset sintético contém medidas *derivadas* dos landmarks (envergadura, proporções). Os 21 pontos 3D originais, se exportados, exigiriam tratamento próprio — provavelmente normalização por pulso mais ruído, ou não exportação.

**Ataques de composição.** Publicar múltiplas versões anonimizadas do mesmo dataset, com parâmetros diferentes, permite cruzá-las para reduzir a incerteza. O pipeline não rastreia versões já publicadas.

**k-anonimato não protege contra conhecimento externo.** Se um atacante já sabe que determinada pessoa está na base e conhece alguns atributos dela, o k efetivo é menor do que o reportado.

---

## Referências

- **LGPD** — Lei nº 13.709/2018, art. 5º (definições), art. 12 (dados anonimizados)
- Sweeney, L. (2002). *k-anonymity: A Model for Protecting Privacy*
- Machanavajjhala, A. et al. (2007). *l-diversity: Privacy Beyond k-anonymity*
- Dwork, C. (2006). *Differential Privacy*

---

Projeto acadêmico — Projeto Integrador. Documentação do módulo de privacidade do Li-Vision.
