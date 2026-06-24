# 📑 Guia Técnico: Infraestrutura Local e Arquitetura SamBot

Este documento fornece uma visão consolidada da camada de processamento local do projeto **SamBot**. Ele detalha como o **Ollama** atua como o motor de inteligência, integrando uma rede híbrida de hardware para equilibrar performance, economia de recursos e privacidade.

---

## 1. Visão Geral da Arquitetura

A SamBot utiliza uma abordagem de **IA Híbrida**. As tarefas são distribuídas entre um servidor de baixa potência (Acer ES1) e uma workstation potente (Xeon + RX 580), conectadas via rede Mesh (**Tailscale**).

### Por que esta arquitetura?

- **Privacidade e Custo:** O processamento local via Ollama reduz a dependência de APIs pagas e mantém dados sensíveis fora da nuvem.
- **Failover Inteligente:** Capacidade de alternar entre modelos locais e o Gemini (nuvem) caso algum nó da rede fique offline.
- **Otimização de Hardware:** Distribuição de carga conforme a complexidade da tarefa.

---

## 2. A "Stack" de Hardware

### 🚀 Nó de Alta Performance (Workstation Principal)

- **SO:** Linux Mint
- **CPU:** Intel Xeon E3-1270
- **RAM:** 24GB RAM
- **GPU:** AMD Radeon RX 580 (8GB VRAM)
- **Função:** Motor principal de processamento de LLMs pesados com aceleração ROCm.

### 🔋 Nó de Baixa Potência (Servidor)

- **SO:** Ubuntu Server
- **Dispositivo:** Acer ES1-573 (i3 6006u, 8GB RAM)
- **Função:** Host do bot, containers Docker e modelos ultra-leves para comandos rápidos.

---

## 3. Estratégia de Modelos (LLMs)

O SamBot utiliza três modelos específicos para diferentes propósitos:

| Modelo               | Função               | Localização        | Vantagem                            |
| -------------------- | -------------------- | ------------------ | ----------------------------------- |
| **Phi-3.5**          | Lógica e Raciocínio  | Workstation (Mint) | Alta precisão e velocidade via GPU. |
| **Qwen-2.5 1.5B**    | Comandos Rápidos     | Servidor (Ubuntu)  | Extremamente leve, evita latência.  |
| **Nomic-Embed-Text** | Memória (Embeddings) | Workstation/Server | Vetorização para o ChromaDB (RAG).  |

---

## 4. Instalação e Configuração

### 🛠️ Configuração no Linux Mint (Aceleração GPU RX 580)

No Linux, o Ollama utiliza o **ROCm** para acessar o poder da GPU AMD, o que é significativamente mais estável que as soluções Windows para esta placa.

1. **Instalar drivers ROCm:** Certifique-se de que os drivers de vídeo e suporte ROCm estão instalados no Mint.
2. **Instalar Ollama:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

3. **Baixar Modelos:**

```bash
ollama run phi3.5:latest
ollama pull nomic-embed-text:latest
```

> **Verificação:** Use `rocm-smi` ou verifique os logs do Ollama para confirmar a detecção da RX 580.

_Obs: Isso varia de placa e SO_

### ⚙️ Configuração no Ubuntu Server (Acer ES1)

1. **Instalar Ollama:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

2. **Baixar Modelo Leve:**

```bash
ollama run qwen2.5:1.5b
```

---

## 5. Conectividade e Rede Mesh (Tailscale)

Para que o SamBot no servidor Ubuntu consiga "falar" com o Ollama no PC Mint de forma segura pela internet, utilizamos o **Tailscale**.

### Passo a Passo da Conexão:

1. **Habilitar Acesso Externo (Nó Mint):**
   É necessário configurar o Ollama para aceitar conexões fora do localhost. No Linux, edite o serviço do systemd:

- Adicione a variável de ambiente: `OLLAMA_HOST=0.0.0.0`

2. **Configuração no arquivo `.env` da SamBot:**
   O bot deve apontar para o IP interno gerado pelo Tailscale para a workstation.

```env
# IP do Tailscale da Workstation Linux Mint
OLLAMA_REMOTE_URL="http://100.x.y.z:11434"

```

### Extra usando docker (meu caso)

## 1. Subindo o Container com Acesso Externo

Por padrão, o Ollama no Docker escuta apenas em `127.0.0.1`. Para liberar o acesso para outros IPs da sua rede local ou Tailscale, você deve definir a variável `OLLAMA_HOST`.

### Com Suporte a GPU (Recomendado para sua Workstation)

Se estiver no Linux Mint com drivers ROCm (AMD) ou NVIDIA instalados:

```bash
docker run -d \
  --name ollama \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  --device /dev/kfd --device /dev/dri \
  -e OLLAMA_HOST=0.0.0.0 \
  ollama/ollama

```

### Apenas CPU (Para o seu Acer ES1)

```bash
docker run -d \
  --name ollama \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  -e OLLAMA_HOST=0.0.0.0 \
  ollama/ollama

```

## 2. Entendendo os Parâmetros

- **`-p 11434:11434`**: Mapeia a porta interna do container para a porta física da sua máquina.
- **`-e OLLAMA_HOST=0.0.0.0`**: Esta é a chave. Ao definir como `0.0.0.0`, você diz ao Ollama para aceitar conexões de qualquer interface de rede, não apenas de dentro do container.
- **`-v ollama:/root/.ollama`**: Garante que os modelos que você baixar não sejam apagados se o container for reiniciado.

## 3. Configuração de CORS (Opcional, mas importante)

Se você pretende acessar o Ollama através de uma interface web (como o Open WebUI) rodando em outro domínio ou IP, você também precisará liberar as origens:

Adicione esta flag ao comando `docker run`:
`-e OLLAMA_ORIGINS="*"`

## 4. Validando o Acesso

Após subir o container, verifique se a porta está aberta e respondendo:

1. **Localmente:** `curl http://localhost:11434`
2. **De outro PC na rede:** `curl http://IP_DA_MAQUINA:11434`

Se o retorno for `Ollama is running`, a configuração foi bem-sucedida.

---

## 5. Exemplo com Docker Compose (Mais organizado)

Para facilitar a manutenção no seu servidor, use um arquivo `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama
    container_name: ollama
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_ORIGINS=*
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

### Como aplicar?

1. Salve o código acima em um arquivo chamado `docker-compose.yml`.
2. Rode o comando: `docker compose up -d`.

---

**Dica para sua rede Mesh:** Na SamBot, agora você pode apontar o `OLLAMA_REMOTE_URL` para o IP do Tailscale da máquina onde este container está rodando, seguido da porta `:11434`.

---

## 6. Dicas de Performance e Manutenção

> [!IMPORTANT]
> **Gestão de VRAM:** A RX 580 possui 8GB de VRAM. Modelos como o Phi-3.5 (3.8B) cabem inteiros na memória, garantindo respostas instantâneas. Evite rodar múltiplos modelos grandes simultaneamente para não forçar o uso de RAM (swap).

> [!TIP]
> **Persistência de Serviço:** No Linux Mint, configure o `systemd` para garantir que o Ollama inicie automaticamente no boot, permitindo que o SamBot funcione mesmo que a interface gráfica não esteja logada.

> [!NOTE]
> **Memória Infinita (RAG):** O uso do `nomic-embed-text` em conjunto com o ChromaDB permite que o bot consulte o histórico de conversas do Discord como uma base de conhecimento, criando uma sensação de continuidade e memória de longo prazo.

---

**Documentação atualizada em:** Novembro de 2025
