# 📑 Infraestrutura Local e Arquitetura SamBot

Este documento detalha a camada de infraestrutura física e virtual do projeto **SamBot**, abrangendo a topologia híbrida de hardware, conectividade segura via malha **Tailscale**, aceleração computacional por GPU via **AMD ROCm** e a orquestração de microsserviços em contêineres Docker.

## 1. Visão Geral da Topologia Híbrida e Hardware

A SamBot opera sob um modelo de **processamento distribuído**, dividindo as tarefas operacionais contínuas de um servidor leve e os nós satélites especializados em inferência pesada e processamento de áudio:

```text
 ┌────────────────────────────────────────────────────────┐
 │     NÓ DE BAIXA POTÊNCIA / PRINCIPAL (Servidor)        │
 │     - Dispositivo: Servidor Local / VPS (Ubuntu Server)│
 │     - CPU: Intel Core i3-6006U | 8 GB RAM              │
 │     - Serviços: Bot Core (discord.py/FastAPI), SQLite, │
 │       ChromaDB (Embeddings locais), Meilisearch        │
 └───────────────────────────┬────────────────────────────┘
                             │
                  [ Rede Mesh: Tailscale ]
             (Túnel Seguro Criptografado WireGuard)
                             │
 ┌───────────────────────────┴────────────────────────────┐
 │     NÓ DE ALTA PERFORMANCE (Workstation / GPU)         │
 │     - CPU: Intel Xeon E3-1270 | 24 GB RAM              │
 │     - GPU: AMD Radeon RX 580 (8 GB VRAM)               │
 │     - Serviços: Ollama (ROCm), Lavalink v4 / Navidrome │
 └────────────────────────────────────────────────────────┘

```

### Justificativa de Arquitetura:

- **Eficiência e Custos:** Tarefas rotineiras rodam 24/7 no servidor econômico; modelos locais pesados rodam na estação com GPU dedicada apenas quando ativa.
- **Failover Transparente:** Caso a workstation esteja desligada, o orquestrador comuta automaticamente para as APIs na nuvem configuradas (`LLMChainOrchestrator`).
- **Privacidade e Baixa Latência:** Dados sensíveis de RAG, rotas semânticas e acervos multimídia permanecem integralmente sob controle na rede local.

## 2. Catálogo de Modelos Locais

| Modelo              | Papel Operacional                       | Localização       | Vantagem Técnica                                       |
| :------------------ | :-------------------------------------- | :---------------- | :----------------------------------------------------- |
| **`phi3.5:latest`** | Raciocínio avançado, fallback e análise | Mint              | Alta velocidade e precisão via aceleração ROCm na GPU. |
| **`qwen2.5:1.5b`**  | Comandos rápidos e parsing auxiliar     | Servidor (Ubuntu) | Pegada de memória mínima em CPU sem latência de rede.  |

## 3. Rede Privada Mesh via Tailscale

Para que o servidor principal comunique-se de forma transparente com o nó de GPU e áudio, sem expor portas sensíveis na internet pública, utiliza-se a malha virtual **Tailscale** (baseada em WireGuard).

### 3.1. Instalação e Ativação nos Hosts

Em cada máquina da topologia (Linux):

```bash
# Instalação do agente Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Inicialização com parâmetros de roteamento e tags
sudo tailscale up --accept-routes --advertise-tags=tag:sambot-node
```

### 3.2. Apontamento de Serviços no `.env` e `config.yaml`

Uma vez integrados à malha, cada host recebe um IP fixo na faixa `100.x.y.z`. Os serviços remotos passam a apontar diretamente para esses endereços privados:

- **No arquivo `.env` (Inferência & Biblioteca):**

```env
# Endpoint Ollama no host GPU (Workstation)
OLLAMA_REMOTE_URL="http://100.100.100.100:11434"
MODEL_SMART_REMOTE="phi3.5:latest"

# Servidor Navidrome na malha (Modo Local)
NAVIDROME_URL="http://100.100.100.100:4533"
```

- **No arquivo `config.yaml` (Nó Lavalink Remoto):**

```yaml
music:
  mode: "ONLINE"
  lavalink:
    nodes:
      - name: "Node-Workstation-Tailscale"
        host: "100.100.100.100"
        port: 2333
        password: "youshallnotpass"
        secure: false
```

## 4. Aceleração por Hardware: AMD ROCm (Placas Gráficas Radeon)

Para a execução de modelos de linguagem e embeddings (`phi3.5:latest`) acelerados por GPUs AMD, o nó de processamento deve configurar o runtime **AMD ROCm**.

### 4.1. Permissões de Usuário e Repositórios

Adicione o usuário operacional aos grupos de renderização e vídeo:

```bash
sudo usermod -a -G render,video $USER
```

### 4.2. Instalação dos Pacotes ROCm (Exemplo Debian/Ubuntu)

```bash
sudo apt-get update && sudo apt-get install -y wget gnupg2
wget https://repo.radeon.com/rocm/rocm.gpg.key -O - | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/rocm.gpg > /dev/null
echo "deb [arch=amd64 signed-by=/etc/apt/trusted.gpg.d/rocm.gpg] https://repo.radeon.com/rocm/apt/6.1 ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/rocm.list

sudo apt-get update
sudo apt-get install -y rocm-hip-sdk rocm-opencl-sdk
```

_Valide os aceleradores executando `rocminfo` ou `rocm-smi`._

### 4.3. Execução do Contêiner Ollama com Pass-Through de GPU

Para expor os nós de hardware (`/dev/kfd` e `/dev/dri`) ao contêiner Docker:

```bash
docker run -d \
  --name ollama_rocm \
  --restart unless-stopped \
  -p 11434:11434 \
  --device /dev/kfd \
  --device /dev/dri \
  -e OLLAMA_HOST=0.0.0.0 \
  -e OLLAMA_ORIGINS="*" \
  -e HSA_OVERRIDE_GFX_VERSION=8.0.3 \
  -v ollama_data:/root/.ollama \
  ollama/ollama:rocm
```

> ⚠️ **Nota de Compatibilidade (`HSA_OVERRIDE_GFX_VERSION`):** Em placas da família Polaris (ex: RX 580), utilize `8.0.3`. Para RDNA2 (ex: RX 6700 XT), utilize `10.3.0`, e para RDNA3 (RX 7000), utilize `11.0.0` para instruir corretamente a arquitetura gráfica.

## 5. Orquestração da Stack no Servidor (`docker-compose.yml`)

No servidor principal (Ubuntu Server), a infraestrutura essencial de microsserviços é mantida, isolada e orquestrada via Docker Compose:

### 5.1. Tabela de Portas e Volumes

| Serviço            | Imagem                      | Porta Padrão | Volume Hospedeiro            |                         Finalidade                         |
| :----------------- | :-------------------------- | :----------- | :--------------------------- | :--------------------------------------------------------: |
| **sambot**         | Build local (`Dockerfile`)  | —            | `./Data`, `./logs`           |       Lógica central do bot, cognição e agendadores.       |
| **lavalink_local** | `fredboat/lavalink:master`  | `2333`       | `./application.yml`          | Decodificação, streaming e mixagem de áudio no modo local. |
| **meilisearch**    | `getmeili/meilisearch:v1.7` | `7700`       | `./Data/Persistence/MeiliDB` |  Cache com TTL e busca full-text otimizada de promoções.   |

### 5.2. Arquivo de Composição (`docker-compose.yml`)

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

  meilisearch:
    image: getmeili/meilisearch:v1.7
    container_name: sambot_meili
    restart: unless-stopped
    ports:
      - "7700:7700"
    environment:
      - MEILI_NO_ANALYTICS=true
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}
      - MEILI_ENV=production
    volumes:
      - ./Data/Persistence/MeiliDB:/meili_data
```

## 6. Boas Práticas Operacionais e Monitoramento

- **Gestão de VRAM:** Evite executar múltiplos modelos massivos em paralelo na mesma GPU para prevenir estouro de VRAM e acionamento excessivo de swap na RAM do sistema.
- **Persistência do Meilisearch:** O mapeamento do volume `./Data/Persistence/MeiliDB` garante que o índice de ofertas e ordenações de cupons sobreviva a reinicializações dos contêineres.
- **Saúde dos Serviços (Healthchecks):**

```bash
# Monitoramento de recursos e memória dos contêineres
docker stats --no-stream

# Verificação do nó Lavalink
curl -i http://127.0.0.1:2333/version

# Checagem de integridade do Meilisearch
curl -i -H "Authorization: Bearer $MEILI_MASTER_KEY" http://127.0.0.1:7700/health
```
