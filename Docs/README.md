# 🤖 SamBot: A Baiana do Meu HomeLab

A **SamBot** não é apenas uma bot de comandos: é uma **Agente Autônoma Híbrida** que atua como o coração experimental do meu HomeLab. Este projeto nasceu da necessidade de criar uma assistente funcional que respeitasse as limitações de hardware e as particularidades de uma rede privada, oferecendo memória de longo prazo, consciência contextual e áudio de alta fidelidade.

Ela utiliza **LLMs** (Large Language Models) para conversação natural e **RAG** (Retrieval-Augmented Generation) para recordar fatos, operando sob uma arquitetura resiliente que alterna entre processamento em nuvem e local.

_Curiosidade: O nome "SamBot" foi inspirado em uma pessoa muito querida para mim; este projeto foi um presente para ela._

## 📖 Guia de Documentação

- 🏗️ **[Arquitetura do Sistema](./ARCHITECTURE.md)** — Detalhes sobre o pipeline cognitivo, fluxo de eventos e estrutura de pastas.
- ⚙️ **[Guia de Configuração](./CONFIG.md)** — Como configurar as chaves de API, variáveis do `.env` e o `config.yaml`.
- 🌐 **[Infraestrutura e Redes](./Developers/Infra.md)** — Topologia de hardware, uso do Tailscale e Ubuntu Server.
- 📜 **[Histórico de Mudanças](./CHANGELOG.md)** — Registro completo de versões, melhorias e correções.
- 🔌 **[Serviços](./Services/ServiceManager.md) & [APIs](./Brain/Tools/Catalog.md)** — Catálogo de rotas internas, ferramentas externas e integrações.

## 💡 Filosofia do Projeto

Diferente de bots comerciais genéricos, a SamBot foi projetada para um ecossistema específico:

- **Foco Pessoal:** Desenvolvida para uso próprio e de amigos próximos.
- **Desenvolvimento Assistido:** O projeto é uma jornada de aprendizado contínuo, utilizando LLMs (como o Google Gemini) como "tutoras" para revisar código e auxiliar no debug de novas arquiteturas.
- **Otimização de Recursos:** Desenhada para ser resiliente e "compartilhar a potência" entre dispositivos, já que o hardware principal nem sempre fica ligado 24/7.

## ✨ Principais Funcionalidades

### 🧠 Inteligência & Memória

- **Conversação Natural:** Compreende contexto, ironia e intenções através de menções diretas ou respostas a mensagens.
- **Memória Infinita (RAG):** Utiliza **ChromaDB** para "aprender" e persistir fatos sobre os usuários ao longo do tempo. _Exemplo: se você disser "Meu nome é Tachi e gosto de jazz", ela lembrará disso semanas depois._
- **Identidade Sólida:** Personalidade ancorada em `identity.json` e personas dinâmicas (`padrao`, `nerd`, `amiga`), evitando alucinações sobre sua natureza.
- **Redundância Automática (Failover):** Rotação inteligente de chaves de API contra Rate Limit (HTTP 429) e transição silenciosa para modelos locais se a nuvem oscilar.

### 🎵 Sistema de Áudio (Wavelink / Lavalink)

- **Alta Fidelidade:** Integração com Lavalink v4 para reprodução fluida, equalizações dinâmicas (Bassboost, Nightcore) e playlists locais.
- **Status Dinâmico:** Atualiza automaticamente a presença e o status no Discord conforme a faixa em reprodução.
- **Modos Flexíveis:** Suporte a acervo local privado via **Navidrome** (API Subsonic) ou servidores remotos online.

### 🛠️ Ferramentas Autônomas (`Tools`)

A bot avalia a intenção via roteamento semântico local e decide quando acionar ferramentas externas:

- **Clima:** Condições meteorológicas em tempo real via Open-Meteo e Nominatim.
- **Compras & Cupons:** Comparador de preços (Mercado Livre, Pelando, Meilisearch) e busca de cupons ativos.
- **Jogos:** Consulta de metadados no IGDB, preços em BRL na Steam e descontos no CheapShark.
- **Animes:** Metadados via Jikan (MyAnimeList) e identificação de cenas por imagem no Trace.moe.
- **Busca Web & Visão:** Pesquisas na web em tempo real e interpretação multimodal de anexos.

## 🚀 Instalação Rápida

A SamBot conta com um **Painel Assistente Interativo**, permitindo gerenciar o ambiente sem precisar editar arquivos na mão:

1. **Clonar o Repositório:**

```bash
git clone https://github.com/OnlyTachi/SamBot.git
cd SamBot
```

2. **Iniciar o Assistente de Configuração:**

- No **Linux**: Execute `./start.sh`
- No **Windows**: Dê um duplo clique em `start.bat`
  _(Requisito: Python 3.11+ instalado e marcado no PATH)_

3. **Siga as instruções na tela:** O assistente guiará você passo a passo (com dicas contextuais ao digitar `?`) para criar o arquivo `.env`, validar chaves opcionais e iniciar o bot nativamente ou via **Docker Compose**.

## ⚠️ Nota sobre o Estado do Projeto

Este é um projeto em constante evolução que atua como laboratório prático de Python e Inteligência Artificial. O código passa por refatorações periódicas à medida que novos padrões de design e integrações são experimentados.

## 📝 Licença

Desenvolvido com curiosidade e carinho por **OnlyTachi**. Distribuído sob a licença **MIT**.
