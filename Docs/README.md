# 🤖 SamBot: A Agente do meu HomeLab

A **SamBot** não é apenas uma bot de comandos: é uma **Agente Autônomo Híbrido** que atua como o coração experimental do meu HomeLab. Este projeto nasceu da necessidade de criar uma inteligência artificial funcional que respeitasse as limitações de hardware e as particularidades de uma rede privada, oferecendo memória de longo prazo, consciência contextual e áudio de alta fidelidade.

Ela utiliza **LLMs** (Large Language Models) para conversação natural e **RAG** (Retrieval-Augmented Generation) para recordar fatos, operando sob uma arquitetura resiliente que alterna entre o processamento em nuvem e local.

_Curiosidade: O nome "SamBot" foi inspiração de uma pessoa muito querida para mim, esse projeto foi um presente a ela_

## 📖 Guia de Documentação

[Arquitetura do Sistema](ARCHITECTURE.md) - Detalhes sobre o pipeline cognitivo e estrutura de pastas.

[Guia de Configuração](CONFIG_GUIDE.md) - Como configurar as chaves de API e o ficheiro .env.

[Infraestrutura](INFRA.md) - Detalhes sobre o uso do Tailscale e Ubuntu Server.

[Atualizações](CHANGELOG.md) - Informações sobre mudanças e atualizações

[Api](API.md) - Informações sobre ferramentas externas e APIs.

## 💡 Filosofia do Projeto

Diferente de bots comerciais, a SamBot foi projetado para um ecossistema específico:

- **Foco Pessoal:** Desenvolvido para uso próprio e de amigos próximos.
- **Desenvolvimento Assistido:** O projeto é uma jornada de aprendizado, utilizando LLMs (como o Google Gemini) como "professores" para revisar código e ajudar no debug de novas arquiteturas.
- **Otimização de Recursos:** Desenhado para ser resiliente e "compartilhar a potência" entre dispositivos, já que o hardware principal nem sempre está ligado 24/7.

---

## 🏗️ Arquitetura Híbrida & Infraestrutura

A bot opera numa estrutura de **Failover Inteligente** para garantir disponibilidade e eficiência:

1. **O "Cérebro" na Nuvem (Google Gemini):** Garante respostas constantes, mesmo com o hardware local desligado ou fora da rede.
2. **O "Músculo" Local (Ollama):** Quando a workstation está ativa, a bot prioriza o processamento local para economizar tokens e testar modelos personalizados.

### 🌐 Networking com Tailscale

A espinha dorsal da rede é o **Tailscale**, que permite:

- Comunicação segura entre o servidor (Ubuntu) e o Ollama (Windows) em máquinas distintas.
- Acesso remoto ao sistema de logs e persistência via DNS privado.
- Acesso seguro para amigos sem a necessidade de expor portas públicas.

### 💻 Hardware Atual (Humble Stack)

- **Servidor Principal:** Acer ES1 573 (i3 6006u | 8GB RAM) rodando Ubuntu Server.
- **Workstation:** E3-1270 | 24GB RAM | RX580 rodando Ollama via Tailscale.
- **Futuro:** Planejamento para migração para um servidor dedicado (Xeon E5 2470).

---

## ✨ Principais Funcionalidades

### 🧠 Inteligência & Memória

- **Conversação Natural:** Entende contexto, ironia e intenções através de menções diretas.
- **Memória Infinita (RAG):** Utiliza **ChromaDB** para "aprender" e persistir fatos sobre os usuários ao longo do tempo. Ex: Se você disser _"Meu nome é Tachi e gosto de Jazz"_, ela lembrará disso semanas depois.
- **Identidade Sólida:** Personalidade definida via `identity.json` e prompts dinâmicos (Nerd, Louco, Amiga, etc.), evitando alucinações sobre sua natureza.
- **Redundância (Failover):** \* Se a API do Google cair, ele aciona modelos locais automaticamente.Obs: Rotação automática de chaves de API para evitar limites de uso.

### 🎵 Sistema de Áudio (Wavelink)

- **Alta Fidelidade:** Integração com Lavalink para música sem lag e suporte a filtros/playlists.
- **Status Dinâmico:** Atualiza automaticamente o status no Discord com a música em reprodução.

### 🛠️ Ferramentas Autônomas

O bot decide autonomamente quando utilizar ferramentas externas para:

- **Clima:** Consultas meteorológicas em tempo real.
- **Jogos:** Busca de preços e informações na Steam ou IGDB.
- **Busca Web:** Pesquisas na internet para dados atualizados.
- **Busca Imagem:** Pesquisa imagens na internet.

---

## 🧱 Tech Stack

| Componente           | Tecnologia Utilizada               |
| -------------------- | ---------------------------------- |
| **Linguagem**        | Python 3.11                        |
| **Core Framework**   | Discord.py 2.0+                    |
| **Rede**             | Tailscale (Mesh VPN)               |
| **IA (Cloud/Local)** | Google Gemini 1.5/2.0 + Ollama     |
| **Vector DB**        | ChromaDB (Persistência de Memória) |
| **Container**        | Docker & Docker Compose            |
| **Áudio**            | Wavelink (Lavalink Wrapper)        |

---

## 🚀 Instalação Rápida

> [!NOTE]
> Ao iniciar, o bot verificará automaticamente a saúde dos sistemas de IA antes de se conectar ao Discord.

1. **Clonar e Configurar:**

```bash
git clone https://github.com/OnlyTachi/SamBot.git
cd sambot
cp .env.example .env
```

2. **Configuração:** Edite o `.env` com suas credenciais do Discord e chaves de API.
3. **Iniciar:**
   `./start.sh`

---

## ⚠️ Nota sobre o Estado do Projeto

Este é um projeto em constante evolução e funciona como um laboratório pessoal de Python e IA. O código pode conter redundâncias ou soluções técnicas temporárias ("jeitinhos") que são aprimoradas diariamente conforme o aprendizado avança. Obs: algumas documentaçoes podem estar erradas ou desatualizadas.

## 📝 Licença

Desenvolvido com amor e curiosidade por **OnlyTachi**. Distribuído sob a licença **MIT**.
