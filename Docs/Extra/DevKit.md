# 📚 Documentação Técnica de Desenvolvimento: SamBot (v4.0)

Esta documentação destina-se a desenvolvedores, mantenedores, colaboradores e curiosos (igual a mim). Seu objetivo é prover diretrizes claras para o setup de ambiente manual, containerização via Docker, extensão do ecossistema e submissão de forks e Pull Requests.

## Guia Rapido das Documentações do Sistema

| Documento                                                             | De que trata este documento?                                                                  | Quem precisa ler isso?                                        |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **[Arquitetura](/Docs/ARCHITECTURE.md) (`./Docs/ARCHITECTURE.md`)**   | Como o sistema é organizado por dentro e como a inteligência do projeto processa informações. | Quem desenvolve o sistema e cuida da Inteligência Artificial. |
| **[Mapeamento do Cérebro](./CerebroSam.md) (`CerebroSam.md`)**        | Como a "memória" e as ferramentas principais da IA estão organizadas.                         | Quem cuida do código do sistema e faz a manutenção diária.    |
| **[Guia de Configuração](/Docs/CONFIG_GUIDE.md) (`CONFIG_GUIDE.md`)** | Como ajustar o sistema (chaves de acesso, comandos básicos e textos de orientação da IA).     | Quem vai instalar, configurar ou ajustar o sistema.           |
| **[Infraestrutura e Servidores](/Docs/INFRA.md) (`INFRA.md`)**        | Como os servidores, placas de vídeo (GPU) e conexões seguras estão montados.                  | Quem cuida dos servidores, redes e estabilidade do sistema.   |
| **[Integrações e APIs](/Docs/API.md) (`API.md`)**                     | Lista de todos os serviços externos que o sistema usa para funcionar.                         | Quem precisa conectar este sistema com outros aplicativos.    |
| **[Música e Áudio](/Docs/Config/Music.md) (`Music.md`)**              | Como funciona a transmissão de áudio e músicas dentro da plataforma.                          | Quem trabalha com os recursos de som e mídia da plataforma.   |
| **[Histórico de Mudanças](/Docs/CHANGELOG.md)) (`CHANGELOG.md`)**     | Registro simples de tudo o que mudou, foi corrigido ou atualizado no projeto.                 | **Toda a equipe** (técnica, gestão ou produto).               |

## 1. Arquitetura Geral & Stack

A **SamBot** é um bot de Discord desacoplado, assíncrono e orientado a microserviços e Cogs.

```
       [ Gateway Discord ]
               │
          (discord.py)
               │
               ▼
        ┌─────────────┐
        │   main.py   │ ◄──── (Core/Bot.py)
        └──────┬──────┘
               │
       ┌───────┴──────────────┬──────────────────┐
       ▼                      ▼                  ▼
[ LLM Cascata ]       [ Lavalink Node ]   [ ChromaDB VectorStore ]
(Gemini / Groq /       (Wavelink/Java)     (RAG Persistente)
 Local Ollama)

```

## 2. Execução Manual (Sem usar `launcher.py` / `start.bat`)

Se você está desenvolvendo ou ajustando arquivos e prefere **não** utilizar os scripts de inicialização interativa (`launcher.py`, `start.bat`, `start.sh`), siga o procedimento abaixo.

### 2.1. Requisitos Prévios

- Python 3.11+ instalado e configurado nas variáveis de ambiente.
- Servidor Lavalink v4 rodando localmente (porta `2333`) ou um node remoto configurado.

### 2.2. Passo a Passo Nativo

1. **Clone o repositório:**

```bash
git clone https://github.com/OnlyTachi/sambot.git
cd sambot
```

2. **Crie e ative um ambiente virtual (`.venv`):**

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell / CMD)
python -m venv .venv
.venv\Scripts\activate
```

3. **Instale as dependências e o modelo NLP do Spacy:**

```bash
pip install -r requirements.txt
python -m spacy download pt_core_news_sm
```

4. **Configuração de Variáveis de Ambiente (`.env`):**
   Copie a estrutura base do `.env.example` e crie o seu arquivo `.env`:

```bash
cp .env.example .env
```

_Preencha obrigatoriamente_:

- `DISCORD_TOKEN`: Seu bot token gerado no _Discord Developer Portal_.
- `OWNER_ID`: Seu ID numérico no Discord.
- `BOT_PREFIX`: Prefixo desejado (ex: `+`).

_O resto das API sao totalmente opcionais, adicione so qual voce ira usar ou testar_

5. **Inicie o bot manualmente:**

```bash
python main.py
```

## 🐳 3. Execução e Desenvolvimento via Docker

Para isolamento de ambiente e rápida implantação do lavalink + bot, o projeto possui suporte nativo ao **Docker Compose**.

### 3.1. Estrutura dos Serviços

- **`lavalink_local`**: Container baseado em `fredboat/lavalink:master` rodando a porta `2333` e consumindo o arquivo de configuração `./application.yml`.
- **`sambot`**: Container construído via `Dockerfile` apontando para o Python 3.11 slim.

### 3.2. Comandos Docker Essenciais

- **Subir toda a stack em segundo plano (Recompilando se necessário):**

```bash
docker compose up -d --build
```

- **Acompanhar logs do Bot em tempo real:**

```bash
docker compose logs -f sambot
```

- **Acompanhar logs do Lavalink:**

```bash
docker compose logs -f lavalink
```

- **Derrubar os containers:**

```bash
docker compose down
```

---

## 📂 4. Estrutura de Diretórios e Persistência

Para entender a navegação no projeto:

```text
├── Data/
│   ├── Assets/              # Fontes (.otf) e imagens estáticas
│   ├── Knowledge/           # JSONs estáticos (preços de mercado, empregos, intents NLP)
│   ├── Persistence/         # Dados dinâmicos e banco vetorial
│   │   ├── VectorDB/        # Persistência do ChromaDB (chroma.sqlite3)
│   │   ├── Users/           # Usuários, XP e níveis (users.json)
│   │   └── identity.json    # Metadados de personalidade e diretrizes da SamBot
│   └── Prompts/             # System Prompts para as personas da IA (padrao, nerd, etc.)
├── Core/                    # Instância principal do SamBot e loggers
├── logs/                    # Logs em disco (sambot_general.log, sambot_errors.log)
├── main.py                  # Ponto de entrada assíncrono do sistema
├── launcher.py              # Central interativa de gerenciamento (CLI)
├── application.yml          # Configuração dos nós Lavalink
└── Dockerfile & docker-compose.yml

```

## 🤝 5. Guia para Contribuições e Forks

Agradecemos o apoio e o interesse em contribuir com a **SamBot**!

### 5.1. Diretrizes para Envio de PRs (Pull Requests)

1. **Faça um Fork do Repositório** para a sua conta do GitHub.
2. **Crie uma Branch Temática** para suas alterações:

```bash
git checkout -b feature/sua-feature-incrivel
# ou
git checkout -b fix/correcao-bug-audio
```

3. **Respeite o Estilo de Código**:

- Utilize tipo de identação padrão (4 espaços).
- Adicione logs apropriados usando o `Logger` em vez de chamadas `print()` soltas.

4. **Mantenha os Segredos Fora do Versionamento**:

- **NUNCA** envie tokens do Discord, API Keys do Gemini ou senhas de instâncias reais para o repositório (`.env` e `Data/Persistence/` estão no `.gitignore`).

5. **Faça o Commit e Push**:

```bash
git commit -m "feat(music): adiciona suporte a filtros avançados de áudio"
git push origin feature/sua-feature-incrivel
```

6. **Abra um Pull Request** detalhando as motivações das alterações e os testes realizados.

## 🔒 6. Diretrizes de Segurança para Desenvolvedores

> ⚠️ **ATENÇÃO:**
>
> - Nunca execute scripts de terminal arbitrários (`os.system` / `subprocess`) baseados em entrada não sanitizada vinda do Discord.
> - Ao adicionar novas chamadas ao `VectorDB` (ChromaDB), garanta que dados sensíveis de credenciais **não** sejam indexados na memória de longo prazo da IA.
