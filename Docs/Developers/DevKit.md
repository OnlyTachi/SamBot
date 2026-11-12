# 🛠️ DevKit & Guia de Contribuição

Este documento reúne todas as instruções necessárias para desenvolvedores prepararem o ambiente local de desenvolvimento, executarem a stack em containers, seguirem as convenções de código e submeterem contribuições com consistência e segurança.

## 1. Setup Manual do Ambiente

Para desenvolver e depurar componentes diretamente na máquina hospedeira sem intermediários.

### 1.1. Pré-requisitos

- **Python**: versão `3.11.x` instalada e configurada no `PATH`.
- **Git**: para versionamento e controle de branches.
- **Java Runtime (JRE/JDK 17+)**: caso execute uma instância local de Lavalink v4 nativamente.
- **Serviço Meilisearch**: binário local ou executando via container na porta `7700`.

### 1.2. Criação do Ambiente Virtual (`.venv`)

Clone o repositório e crie o ambiente isolado:

```bash
# Clonagem do repositório
git clone https://github.com/OnlyTachi/sambot.git
cd sambot

# Criação do virtualenv no Linux / macOS
python3.11 -m venv .venv
source .venv/bin/activate

# Criação do virtualenv no Windows (PowerShell / CMD)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 1.3. Instalação de Dependências e spaCy

Instale as dependências listadas no `requirements.txt` e faça o download do modelo linguístico treinado em português para o spaCy:

```bash
# Atualize o instalador de pacotes
pip install --upgrade pip setuptools wheel

# Dependências do projeto e utilitários de desenvolvimento
pip install -r requirements.txt
pip install black ruff mypy pytest pytest-asyncio

# Modelo de Processamento de Linguagem Natural
python -m spacy download pt_core_news_sm
```

### 1.4. Variáveis de Ambiente (`.env`) e Configuração

Crie uma cópia do arquivo de exemplo e defina suas credenciais locais de teste:

```bash
cp .env.example .env
```

Propriedades fundamentais para inicialização (as demais APIs externas são opcionais):

```env
DISCORD_TOKEN=seu_token_de_bot_aqui
OWNER_ID=seu_discord_id_numerico
BOT_PREFIX=+
MEILI_HOST=[http://127.0.0.1:7700](http://127.0.0.1:7700)
MEILI_MASTER_KEY=sua_chave_master_local
```

> ℹ️ **Nota:** As configurações de nós do Lavalink e modos de reprodução (`LOCAL` ou `ONLINE`) devem ser ajustadas no arquivo `config.yaml`.

### 1.5. Inicialização Manual

```bash
python main.py
```

## 2. Execução via Docker

Para garantir paridade total entre ambientes de desenvolvimento e produção, a stack pode ser executada por meio do Docker Compose.

### 2.1. Arquivo de Composição (`docker-compose.yml`)

```yaml
services:
  sambot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: sambot_core
    restart: unless-stopped
    depends_on:
      lavalink_local:
        condition: service_healthy
      meilisearch:
        condition: service_started
    env_file:
      - .env
    volumes:
      - ./Data:/app/Data
      - ./logs:/app/logs
    networks:
      - sambot_internal

  lavalink_local:
    image: fredboat/lavalink:master
    container_name: sambot_lavalink
    restart: unless-stopped
    ports:
      - "2333:2333"
    volumes:
      - ./application.yml:/opt/Lavalink/application.yml:ro
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:2333/version || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - sambot_internal

  meilisearch:
    image: getmeili/meilisearch:v1.7
    container_name: sambot_meili
    restart: unless-stopped
    ports:
      - "7700:7700"
    environment:
      - MEILI_NO_ANALYTICS=true
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}
      - MEILI_ENV=development
    volumes:
      - ./Data/Persistence/MeiliDB:/meili_data
    networks:
      - sambot_internal

networks:
  sambot_internal:
    driver: bridge
```

### 2.2. Comandos Operacionais

- Inicializar todos os serviços com build:

```bash
docker compose up -d --build
```

- Acompanhar os logs estruturados da aplicação:

```bash
docker compose logs -f sambot
```

- **Interromper a stack preservando os volumes montados:**

```bash
docker compose down
```

## 3. Padrões de Código e Diretrizes de Qualidade

Todo código adicionado ou alterado no projeto deve aderir aos seguintes requisitos de estilo, arquitetura e tipagem.

### 3.1. Tipagem Estática

- Todas as funções, métodos assíncronos e assinaturas de classes devem conter anotações de tipo explícitas (`typing`).
- Utilize tipos primitivos e genéricos modernos (`list[str]`, `dict[str, Any]`, `Optional[int]`, `Union[float, int]`).
- Validação estática executada com `mypy`:

```bash
mypy Brain/ Core/ Data/
```

Exemplo:

```python
from typing import Optional, Any

async def fetch_offer_by_id(self, offer_id: str) -> Optional[dict[str, Any]]:
    """Recupera uma oferta específica pelo identificador textual."""
    if not offer_id.strip():
        return None
    return await self._client.index("ofertas").get_document(offer_id)
```

### 3.2. Formatação e Linting (Black & Ruff)

- **Tamanho máximo de linha**: 100 caracteres.
- **Indentação**: 4 espaços (sem tabs).

- **Sem prints**: Sempre utilize o wrapper central de logging (`Core.Utils.Logger` ou `logging.getLogger("SamBot")`).

- Antes de submeter commits, execute a validação:

```bash
# Formatação automática
black --line-length 100 .

# Análise estática de erros e imports
ruff check . --fix
```

### 3.3. Segurança e Integridade de Dados

- **Zero Secrets no Git**: Nunca versionar `.env`, arquivos de banco de dados (`.db`), diretórios `VectorDB/` ou sessões do Telegram (`.session`).

- **Acesso Exclusivo via Facade**: Nunca manipule arquivos em `Data/Persistence/` diretamente com `open()`. Utilize sempre o `DataManager` e seus respectivos `SubManagers` para respeitar as travas de concorrência (`threading.Lock` / transações ACID).

- **Sanitização de Comandos**: Chamadas a interpretadores ou subsistemas não devem concatenar entradas vindas de usuários diretamente.

- **RAG e Privacidade**: Garantir que segredos, credenciais e chaves não sejam injetadas no ChromaDB durante ingestões de base de conhecimento.

## 4. Guia para Pull Requests (PRs)

Para manter a rastreabilidade e integridade da base de código:

### 4.1. Convenção de Branches

- Features novas: `feature/nome-da-funcionalidade`

- Correção de bugs: `fix/descricao-do-problema`

- Refatoração e performance: `refactor/modulo-alvo`
- Documentação: `docs/nome-do-documento`

### 4.2. Padrão de Commits (Conventional Commits)

Utilize prefixos semânticos e descrições imperativas em português ou inglês:

- `feat(offers): adiciona ordenacao por menor preco no meilisearch`
- `fix(audio): corrige reconexao automatica com lavalink v4`
- `refactor(database): segrega metodos de economia em SubManager dedicado`
- `docs(infra): atualiza topologia mesh com rotas tailscale`

### 4.3. Checklist para Submissão

1. [ ] A branch foi bifurcada a partir da `main` atualizada.
2. [ ] Todas as dependências novas foram adicionadas ao `requirements.txt`.
3. [ ] `ruff check .` e `black --check .` foram executados sem erros.
4. [ ] `mypy` executado com êxito nos arquivos modificados.
5. [ ] Documentação correspondente em `Docs/` atualizada, caso afete contratos de APIs ou fluxos operacionais.
6. [ ] Pull Request aberto com descrição clara das mudanças, testes manuais executados e eventuais breaking changes.
