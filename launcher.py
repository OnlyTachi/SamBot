import os
import sys
import subprocess
import time
import socket
import urllib.request
import urllib.parse
import json
import shutil
from pathlib import Path

os.system("")  # Enables ANSI colors support on Windows CMD
C_RESET = "\033[0m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_MAGENTA = "\033[95m"
C_BOLD = "\033[1m"


def clear_screen():
    """Limpa a tela do terminal de forma multiplataforma."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    """Exibe o cabeçalho estilizado do launcher."""
    clear_screen()
    print(f"{C_CYAN}{C_BOLD}")
    print(r"  ____                  ____        _   ")
    print(r" / ___|  __ _ _ __ ___ | __ )  ___ | |_ ")
    print(r" \___ \ / _` | '_ ` _ \|  _ \ / _ \| __|")
    print(r"  ___) | (_| | | | | | | |_) | (_) | |_ ")
    print(r" |____/ \__,_|_| |_| |_|____/ \___/ \__|")
    print(f"                                   v5.5{C_RESET}")
    print(f"{C_MAGENTA}>> Centro de Controle, Diagnóstico e Configuração <<{C_RESET}\n")


def get_python_cmd():
    """Retorna o comando correto do Python dependendo do SO."""
    return "python" if os.name == "nt" else "python3"


def ping_host(host, port, timeout=3):
    """Testa se uma porta TCP está aberta."""
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def check_http_service(url, timeout=3):
    """Verifica se um serviço HTTP/HTTPS está acessível."""
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        req = urllib.request.Request(url, headers={"User-Agent": "SamBotLauncher/5.5"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status < 500
    except Exception:
        return False


def read_env_file():
    """Lê o arquivo .env atual para um dicionário de configurações."""
    env_data = {}
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    val = val.strip().strip('"').strip("'")
                    env_data[key.strip()] = val
    return env_data


def read_last_lines(filepath, num_lines=25):
    """Lê as últimas N linhas de um arquivo de log de forma segura."""
    if not os.path.exists(filepath):
        return f"{C_YELLOW}ℹ️ Nenhum registro encontrado neste arquivo de log ainda.{C_RESET}"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                return f"{C_YELLOW}ℹ️ O arquivo de log está vazio.{C_RESET}"

            last_lines = lines[-num_lines:]
            return "".join(last_lines)
    except Exception as e:
        return f"{C_RED}❌ Erro ao ler o arquivo de log: {e}{C_RESET}"


def ensure_dependencies_and_get_python():
    """Verifica/instala dependências, criando venv se necessário (PEP 668)."""
    print(f"{C_YELLOW}[!] Verificando e instalando dependências...{C_RESET}")
    if not os.path.exists("requirements.txt"):
        print(
            f"{C_RED}[X] Arquivo requirements.txt não encontrado! Ignorando instalação.{C_RESET}"
        )
        return get_python_cmd()

    base_python = get_python_cmd()
    venv_python = os.path.join(
        ".venv", "Scripts" if os.name == "nt" else "bin", "python"
    )
    has_venv = os.path.exists(venv_python)
    active_python = venv_python if has_venv else base_python

    cmd = [active_python, "-m", "pip", "install", "-r", "requirements.txt"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{C_GREEN}[V] Dependências verificadas com sucesso!{C_RESET}")
            return active_python

        if "externally-managed-environment" in result.stderr:
            print(
                f"{C_YELLOW}[!] Ambiente gerenciado detectado (PEP 668). Criando .venv...{C_RESET}"
            )
            subprocess.run([base_python, "-m", "venv", ".venv"], check=True)
            print(
                f"{C_YELLOW}[!] Ambiente criado. Instalando dependências no .venv...{C_RESET}"
            )
            cmd = [venv_python, "-m", "pip", "install", "-r", "requirements.txt"]
            subprocess.run(cmd, check=True)
            print(f"{C_GREEN}[V] Dependências instaladas no ambiente virtual!{C_RESET}")
            return venv_python
        else:
            print(
                f"{C_RED}[X] Erro ao instalar dependências:{C_RESET}\n{result.stderr}"
            )
            return active_python

    except Exception as e:
        print(f"{C_RED}[X] Erro inesperado nas dependências: {e}{C_RESET}")
        return active_python


def git_updater():
    """Verifica atualizações via Git e permite baixar."""
    print_header()
    print(f"{C_CYAN}--- Atualizador Automático (Git) ---{C_RESET}\n")

    try:
        subprocess.run(
            ["git", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except Exception:
        print(
            f"{C_RED}[X] O 'git' não está instalado ou não está no PATH do sistema.{C_RESET}"
        )
        input(f"\n{C_CYAN}Pressione ENTER para voltar...{C_RESET}")
        return

    print(f"{C_YELLOW}[!] Buscando atualizações no repositório remoto...{C_RESET}")
    subprocess.run(["git", "fetch"])
    status = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True)
    print(f"\n{status.stdout}")

    if "behind" in status.stdout or "atrás" in status.stdout:
        resp = input(f"{C_BOLD}Deseja baixar as atualizações agora? (s/n): {C_RESET}")
        if resp.lower() == "s":
            print(f"{C_GREEN}Baixando e aplicando atualização...{C_RESET}")
            subprocess.run(["git", "pull"])
            print(f"{C_GREEN}[V] Atualização concluída com sucesso!{C_RESET}")
    elif "up to date" in status.stdout or "atualizado" in status.stdout:
        print(
            f"{C_GREEN}[V] O seu bot já está na versão mais recente do repositório!{C_RESET}"
        )
    else:
        print(
            f"{C_YELLOW}[?] Status de repositório desconhecido ou alterações locais pendentes.{C_RESET}"
        )

    input(f"\n{C_CYAN}Pressione ENTER para voltar ao menu...{C_RESET}")


def run_diagnostics():
    """Roda testes de rede, conexões de APIs e serviços configurados."""
    print_header()
    print(f"{C_CYAN}--- Executando Diagnóstico do Sistema ---{C_RESET}\n")

    print(f"Versão do Python: {C_YELLOW}{sys.version.split()[0]}{C_RESET}")

    # Teste de Internet
    print("Conexão com a Internet: ", end="")
    try:
        urllib.request.urlopen("https://1.1.1.1", timeout=3)
        print(f"{C_GREEN}Online{C_RESET}")
    except Exception:
        print(f"{C_RED}Offline{C_RESET}")

    # Teste de Arquivo .env
    print("Arquivo .env: ", end="")
    if os.path.exists(".env"):
        print(f"{C_GREEN}Encontrado{C_RESET}")
    else:
        print(f"{C_RED}Não encontrado (Use o Assistente de Configuração){C_RESET}")

    env_data = read_env_file()

    # Teste Meilisearch
    meili_host = env_data.get("MEILI_HOST", "http://meilisearch:7700")
    print(f"Meilisearch ({meili_host}): ", end="")
    if check_http_service(meili_host):
        print(f"{C_GREEN}Acessível{C_RESET}")
    else:
        print(f"{C_RED}Inacessível{C_RESET}")

    # Teste Lavalink Local
    lava_host = env_data.get("LAVALINK_LOCAL_HOST", "127.0.0.1")
    lava_port = int(env_data.get("LAVALINK_LOCAL_PORT", "2333"))
    print(f"Lavalink Local ({lava_host}:{lava_port}): ", end="")
    if ping_host(lava_host, lava_port):
        print(f"{C_GREEN}Porta Aberta{C_RESET}")
    else:
        print(f"{C_YELLOW}Inacessível / Não iniciado{C_RESET}")

    # Teste Navidrome
    navidrome_url = env_data.get("NAVIDROME_URL", "")
    if navidrome_url and navidrome_url != "https://seu-navidrome.com":
        print(f"Navidrome ({navidrome_url}): ", end="")
        if check_http_service(navidrome_url):
            print(f"{C_GREEN}Acessível{C_RESET}")
        else:
            print(f"{C_RED}Inacessível{C_RESET}")

    # Teste Jellyfin
    jellyfin_url = env_data.get("JELLYFIN_URL", "")
    if jellyfin_url and "SEU_IP_OU_DOMINIO" not in jellyfin_url:
        print(f"Jellyfin ({jellyfin_url}): ", end="")
        if check_http_service(jellyfin_url):
            print(f"{C_GREEN}Acessível{C_RESET}")
        else:
            print(f"{C_RED}Inacessível{C_RESET}")

    # Teste Ollama Local
    ollama_local = env_data.get("OLLAMA_LOCAL_URL", "")
    if ollama_local:
        print(f"Ollama Local ({ollama_local}): ", end="")
        if check_http_service(ollama_local):
            print(f"{C_GREEN}Acessível{C_RESET}")
        else:
            print(f"{C_YELLOW}Inacessível{C_RESET}")

    input(f"\n{C_CYAN}Pressione ENTER para voltar ao menu...{C_RESET}")


def setup_wizard(first_time=False):
    """
    Assistente interativo inteligente para geração e edição do .env.
    Configurações divididas em Principais (obrigatórias) e Opcionais por categoria.
    """
    current_env = read_env_file()

    if first_time or not current_env:
        clear_screen()
        print(f"{C_CYAN}{C_BOLD}")
        print(f"╔══════════════════════════════════════════╗")
        print(f"║       SAMBOT - ASSISTENTE DE CONFIG      ║")
        print(f"╚══════════════════════════════════════════╝{C_RESET}")
        print(
            f"\n{C_YELLOW}Vamos configurar o bot de maneira rápida e organizada!{C_RESET}"
        )
    else:
        print_header()
        print(
            f"{C_YELLOW}Bem-vindo ao Assistente de Configuração Inteligente!{C_RESET}"
        )
        print(f"\n{C_GREEN}[!] Um arquivo .env já foi detectado.{C_RESET}")
        print("  [ 1 ] Editar/Adicionar dados mantendo o existente")
        print("  [ 2 ] Redefinir do zero (Limpar arquivo)")
        print("  [ 0 ] Cancelar e voltar")
        escolha = input(f"\n{C_BOLD}Escolha: {C_RESET}").strip()

        if escolha == "0":
            return
        elif escolha == "2":
            confirm = input(
                f"{C_RED}Tem certeza? Isso limpará todas as chaves atuais! (s/n): {C_RESET}"
            )
            if confirm.lower() != "s":
                return
            current_env = {}
        elif escolha != "1":
            return

    def ask(key, prompt, help_text, default_fallback=""):
        """Pergunta interativa com suporte a atalhos e valores padrão."""
        default_val = current_env.get(key, default_fallback)
        while True:
            display_default = (
                f" [{C_GREEN}{default_val}{C_RESET}]" if default_val else ""
            )
            val = input(f"{C_BOLD}{prompt}{display_default}:{C_RESET} ").strip()

            if val == "?":
                print(f"\n{C_CYAN}💡 Ajuda:{C_RESET} {help_text}\n")
            elif val == "":
                return default_val
            else:
                return val

    env_data = current_env.copy()

    print(f"\n{C_MAGENTA}{C_BOLD}==========================================")
    print(f"📌 CONFIGURAÇÕES PRINCIPAIS (ESSENCIAIS)")
    print(f"=========================================={C_RESET}")
    print(
        f"{C_CYAN}(Pressione ENTER para manter o valor padrão ou aperte ? para ajuda){C_RESET}\n"
    )

    env_data["DISCORD_TOKEN"] = ask(
        "DISCORD_TOKEN",
        "🔑 Token do Bot (Discord)",
        "Obtenha seu token no Discord Developer Portal (https://discord.com/developers/applications).",
    )
    env_data["OWNER_ID"] = ask(
        "OWNER_ID",
        "👑 ID do Dono (Owner ID)",
        "Seu ID numérico de usuário no Discord.",
    )
    env_data["BOT_PREFIX"] = ask(
        "BOT_PREFIX",
        "⚡ Prefixo de Comandos de Texto",
        "Símbolo usado antes dos comandos (ex: +, !, .).",
        "+",
    )
    env_data["DEBUG_MODE"] = ask(
        "DEBUG_MODE",
        "🐛 Modo Debug (true/false)",
        "Exibe logs detalhados de erros e operações no console.",
        "false",
    )

    # Função auxiliar para salvar o arquivo .env
    def save_env():
        with open(".env", "w", encoding="utf-8") as f:
            for k, v in env_data.items():
                if v is not None:
                    f.write(f'{k}="{v}"\n')

    save_env()

    while True:
        clear_screen()
        print_header()
        print(f"{C_GREEN}{C_BOLD}✅ Configurações Principais registradas!{C_RESET}")
        print(f"\n{C_CYAN}{C_BOLD}💡 O Bot já estará pronto para iniciar!{C_RESET}")
        print(f"Caso queira algo extra, digite o número da categoria para configurar.")
        print(f"{C_YELLOW}(Caso queira pular ou finalizar, aperte ENTER){C_RESET}\n")

        print(f"  {C_BOLD}[ 1 ] 🎵 Música{C_RESET} (Lavalink e Navidrome)")
        print(
            f"  {C_BOLD}[ 2 ] ✈️ Telegram & Busca Indexada{C_RESET} (Meilisearch, Telegram API)"
        )
        print(f"  {C_BOLD}[ 3 ] 🏠 APIs Internas {C_RESET} (Ollama Local & Remoto)")
        print(
            f"  {C_BOLD}[ 4 ] 🌐 APIs Externas & Cloud AI{C_RESET} (Gemini, Groq, DeepSeek, OpenRouter, IGDB, Steam, Google, etc.)"
        )
        print(f"\n  {C_GREEN}[ ENTER / 0 ] Finalizar e Salvar{C_RESET}")

        opcao = input(f"\n{C_BOLD}Opção desejada: {C_RESET}").strip()

        if opcao == "" or opcao == "0":
            break

        # CATEGORIA 1: MÚSICA
        elif opcao == "1":
            print(f"\n{C_MAGENTA}--- 🎵 Configuração de Música ---{C_RESET}")
            print(f"{C_YELLOW}(Aperte ENTER para pular/manter padrão){C_RESET}\n")

            env_data["MUSIC_SOURCE_MODE"] = ask(
                "MUSIC_SOURCE_MODE",
                "🎧 Modo de Origem da Música (LOCAL / ONLINE)",
                "LOCAL usa Navidrome; ONLINE usa Lavalink/YouTube.",
                "ONLINE",
            )

            print(f"\n{C_CYAN}> Lavalink Local:{C_RESET}")
            env_data["LAVALINK_LOCAL_HOST"] = ask(
                "LAVALINK_LOCAL_HOST",
                "Host Local",
                "IP do Lavalink local.",
                "127.0.0.1",
            )
            env_data["LAVALINK_LOCAL_PORT"] = ask(
                "LAVALINK_LOCAL_PORT",
                "Porta Local",
                "Porta do servidor Lavalink local.",
                "2333",
            )
            env_data["LAVALINK_LOCAL_PASSWORD"] = ask(
                "LAVALINK_LOCAL_PASSWORD",
                "Senha Local",
                "Senha configurada no application.yml do Lavalink.",
                "youshallnotpass",
            )

            print(
                f"\n{C_CYAN}> Lavalink Online (Múltiplos separados por vírgula):{C_RESET}"
            )
            env_data["LAVALINK_ONLINE_HOSTS"] = ask(
                "LAVALINK_ONLINE_HOSTS",
                "Hosts Online",
                "Domínios de Lavalinks públicos/remotos.",
                "lavalinkv4.serenetia.com",
            )
            env_data["LAVALINK_ONLINE_PORTS"] = ask(
                "LAVALINK_ONLINE_PORTS", "Portas Online", "Portas.", "443"
            )
            env_data["LAVALINK_ONLINE_PASSWORDS"] = ask(
                "LAVALINK_ONLINE_PASSWORDS",
                "Senhas Online",
                "Senhas.",
                "https://seretia.link/discord",
            )

            print(f"\n{C_CYAN}> Servidores Pessoais (Navidrome / Jellyfin):{C_RESET}")
            env_data["NAVIDROME_URL"] = ask(
                "NAVIDROME_URL",
                "URL Navidrome",
                "URL do seu servidor Navidrome.",
                "https://seu-navidrome.com",
            )
            env_data["NAVIDROME_USER"] = ask(
                "NAVIDROME_USER", "Usuário Navidrome", "Nome de usuário.", "seu_usuario"
            )
            env_data["NAVIDROME_PASSWORD"] = ask(
                "NAVIDROME_PASSWORD", "Senha Navidrome", "Senha de acesso.", ""
            )
            env_data["JELLYFIN_URL"] = ask(
                "JELLYFIN_URL",
                "URL Jellyfin",
                "URL do seu servidor Jellyfin.",
                "http://SEU_IP_OU_DOMINIO:8096",
            )
            env_data["JELLYFIN_API_KEY"] = ask(
                "JELLYFIN_API_KEY",
                "Jellyfin API Key",
                "Chave criada no painel Jellyfin.",
                "",
            )

            save_env()
            print(f"\n{C_GREEN}[V] Configurações de Música salvas!{C_RESET}")
            time.sleep(1.5)

        # CATEGORIA 2: TELEGRAM & BUSCA INDEXADA
        elif opcao == "2":
            print(
                f"\n{C_MAGENTA}--- ✈️ Telegram & Busca Indexada (Meilisearch) ---{C_RESET}"
            )
            print(f"{C_YELLOW}(Aperte ENTER para pular/manter padrão){C_RESET}\n")

            env_data["TELEGRAM_ENABLED"] = ask(
                "TELEGRAM_ENABLED",
                "Ativar Telegram (true/false)",
                "Inicia o módulo de monitoramento do Telegram.",
                "false",
            )
            env_data["TELEGRAM_API_ID"] = ask(
                "TELEGRAM_API_ID",
                "Telegram API ID",
                "Obtido em https://my.telegram.org.",
            )
            env_data["TELEGRAM_API_HASH"] = ask(
                "TELEGRAM_API_HASH", "Telegram API Hash", "Obtido em my.telegram.org."
            )
            env_data["TELEGRAM_CHANNELS"] = ask(
                "TELEGRAM_CHANNELS",
                "Canais do Telegram",
                "Separados por vírgula.",
                "pelando,promocoes_br",
            )

            print(f"\n{C_CYAN}> Meilisearch (Mecanismo de Busca):{C_RESET}")
            env_data["MEILI_HOST"] = ask(
                "MEILI_HOST",
                "Host Meilisearch",
                "URL do container/servidor Meilisearch.",
                "http://meilisearch:7700",
            )
            env_data["MEILI_MASTER_KEY"] = ask(
                "MEILI_MASTER_KEY",
                "Master Key Meilisearch",
                "Chave mestra de autenticação.",
                "masterKey",
            )

            save_env()
            print(
                f"\n{C_GREEN}[V] Configurações de Telegram & Meilisearch salvas!{C_RESET}"
            )
            time.sleep(1.5)

        # CATEGORIA 3: APIS INTERNAS (HOMELAB & OLLAMA)
        elif opcao == "3":
            print(
                f"\n{C_MAGENTA}--- 🏠 APIs Internas & Homelab (Ollama Local/Remoto) ---{C_RESET}"
            )
            print(f"{C_YELLOW}(Aperte ENTER para pular/manter padrão){C_RESET}\n")

            print(f"{C_CYAN}> Ollama Remoto (Tailscale / Servidor dedicado):{C_RESET}")
            env_data["OLLAMA_REMOTE_URL"] = ask(
                "OLLAMA_REMOTE_URL",
                "URL Ollama Remoto",
                "Ex: http://100.x.y.z:11434",
                "http://ip_tailscale_workstation:11434",
            )
            env_data["MODEL_SMART_REMOTE"] = ask(
                "MODEL_SMART_REMOTE",
                "Modelo Remoto Inteligente",
                "Exemplo: phi3.5:latest, llama3.1:8b",
                "phi3.5:latest",
            )
            env_data["MODEL_EMBED_REMOTE"] = ask(
                "MODEL_EMBED_REMOTE",
                "Modelo Embed Remoto",
                "Ex: nomic-embed-text:latest",
                "nomic-embed-text:latest",
            )

            print(f"\n{C_CYAN}> Ollama Local (Mesma máquina / Docker):{C_RESET}")
            env_data["OLLAMA_LOCAL_URL"] = ask(
                "OLLAMA_LOCAL_URL",
                "URL Ollama Local",
                "Ex: http://host.docker.internal:11434 ou http://localhost:11434",
                "http://host.docker.internal:11434",
            )
            env_data["MODEL_FAST_LOCAL"] = ask(
                "MODEL_FAST_LOCAL",
                "Modelo Local Rápido",
                "Exemplo: qwen2.5:1.5b",
                "qwen2.5:1.5b",
            )
            env_data["MODEL_EMBED_LOCAL"] = ask(
                "MODEL_EMBED_LOCAL",
                "Modelo Embed Local",
                "Ex: nomic-embed-text:latest",
                "nomic-embed-text:latest",
            )

            save_env()
            print(f"\n{C_GREEN}[V] Configurações de APIs Internas salvas!{C_RESET}")
            time.sleep(1.5)

        # CATEGORIA 4: APIS EXTERNAS & CLOUD AI
        elif opcao == "4":
            print(
                f"\n{C_MAGENTA}--- 🌐 APIs Externas & Inteligência Artificial Cloud ---{C_RESET}"
            )
            print(f"{C_YELLOW}(Aperte ENTER para pular/manter padrão){C_RESET}\n")

            print(f"{C_CYAN}> Provedores de IA Cloud:{C_RESET}")
            env_data["GEMINI_MODEL_NAME"] = ask(
                "GEMINI_MODEL_NAME",
                "Modelo Gemini",
                "Nome do modelo Google Gemini.",
                "gemini-2.0-flash",
            )
            env_data["GEMINI_API_KEY_1"] = ask(
                "GEMINI_API_KEY_1",
                "Gemini API Key 1",
                "Chave de API do Google AI Studio.",
            )
            env_data["GEMINI_API_KEY_2"] = ask(
                "GEMINI_API_KEY_2", "Gemini API Key 2 (Opcional)", "Chave reserva."
            )
            env_data["GEMINI_API_KEY_3"] = ask(
                "GEMINI_API_KEY_3", "Gemini API Key 3 (Opcional)", "Chave reserva."
            )

            env_data["GROQ_API_KEY"] = ask(
                "GROQ_API_KEY", "Groq API Key", "Chave da Groq Console."
            )
            env_data["GROQ_MODEL"] = ask(
                "GROQ_MODEL", "Modelo Groq", "Modelo", "llama-3.1-8b-instant"
            )

            env_data["DEEPSEEK_API_KEY"] = ask(
                "DEEPSEEK_API_KEY", "DeepSeek API Key", "Chave da DeepSeek Platform."
            )
            env_data["DEEPSEEK_MODEL"] = ask(
                "DEEPSEEK_MODEL", "Modelo DeepSeek", "Modelo", "llama-3.1-8b-instant"
            )

            env_data["MISTRAL_API_KEY"] = ask(
                "MISTRAL_API_KEY", "Mistral API Key", "Chave Mistral AI."
            )
            env_data["MISTRAL_MODEL"] = ask(
                "MISTRAL_MODEL", "Modelo Mistral", "Modelo", "mistral-7b-instruct"
            )

            env_data["OPENROUTER_API_KEY"] = ask(
                "OPENROUTER_API_KEY", "OpenRouter API Key", "Chave OpenRouter."
            )
            env_data["OPENROUTER_MODEL"] = ask(
                "OPENROUTER_MODEL",
                "Modelo OpenRouter",
                "Modelo",
                "llama-3.1-8b-instant",
            )

            print(f"\n{C_CYAN}> Games, Buscas & Mídias:{C_RESET}")
            env_data["IGDB_CLIENT_ID"] = ask(
                "IGDB_CLIENT_ID", "IGDB Client ID", "ID da Twitch Dev Console."
            )
            env_data["IGDB_CLIENT_SECRET"] = ask(
                "IGDB_CLIENT_SECRET", "IGDB Client Secret", "Secret da Twitch Dev."
            )
            env_data["STEAM_API_KEY"] = ask(
                "STEAM_API_KEY", "Steam API Key", "Chave WebAPI da Steam."
            )
            env_data["GOOGLE_SEARCH_API_KEY"] = ask(
                "GOOGLE_SEARCH_API_KEY", "Google Search API Key", "Chave Custom Search."
            )
            env_data["GOOGLE_SEARCH_CX"] = ask(
                "GOOGLE_SEARCH_CX", "Google Search CX ID", "ID do motor de busca."
            )
            env_data["BRAVE_SEARCH_API_KEY"] = ask(
                "BRAVE_SEARCH_API_KEY", "Brave Search API Key", "Chave Brave API."
            )
            env_data["SERPAPI_KEY"] = ask(
                "SERPAPI_KEY", "SerpApi Key", "Chave SerpApi (Shopping/Ofertas)."
            )
            env_data["PIXABAY_API_KEY"] = ask(
                "PIXABAY_API_KEY", "Pixabay API Key", "Chave de imagens do Pixabay."
            )
            env_data["KLIPY_API_KEY"] = ask(
                "KLIPY_API_KEY", "Klipy API Key", "Chave de gifs/vídeos Klipy."
            )

            save_env()
            print(f"\n{C_GREEN}[V] Configurações de APIs Externas salvas!{C_RESET}")
            time.sleep(1.5)

    save_env()
    print(
        f"\n{C_GREEN}[V] Todas as alterações foram gravadas no arquivo .env com sucesso!{C_RESET}"
    )
    time.sleep(2)


def run_logs_menu():
    """Painel interativo para monitoramento de registros e logs locais."""
    while True:
        print_header()
        print(f"{C_CYAN}--- Painel de Logs e Status do Sistema ---{C_RESET}\n")
        print(f"  [ 1 ] 📋 Ver Logs Gerais Recentes")
        print(f"  [ 2 ] ❌ Ver Logs de Erros Registrados")
        print(f"  [ 3 ] 🧹 Limpar Histórico de Logs locais")
        print(f"  [ 4 ] 📊 Ver Estatísticas Gerais do Bot")
        print(f"  [ 0 ] Voltar")

        choice = input(f"\n{C_BOLD}Escolha uma opção de diagnóstico: {C_RESET}").strip()

        if choice == "1":
            clear_screen()
            print(
                f"{C_CYAN}--- Últimos Logs Gerais (logs/sambot_general.log) ---{C_RESET}\n"
            )
            print(read_last_lines("logs/sambot_general.log", num_lines=30))
            input(f"\nPressione {C_YELLOW}ENTER{C_RESET} para retornar...")
        elif choice == "2":
            clear_screen()
            print(
                f"{C_RED}--- Últimos Erros Críticos (logs/sambot_errors.log) ---{C_RESET}\n"
            )
            print(read_last_lines("logs/sambot_errors.log", num_lines=30))
            input(f"\nPressione {C_YELLOW}ENTER{C_RESET} para retornar...")
        elif choice == "3":
            confirm = (
                input(
                    f"\n{C_RED}⚠️ Deseja realmente esvaziar os arquivos de log? (s/n): {C_RESET}"
                )
                .strip()
                .lower()
            )
            if confirm == "s":
                try:
                    os.makedirs("logs", exist_ok=True)
                    for log_file in [
                        "logs/sambot_general.log",
                        "logs/sambot_errors.log",
                    ]:
                        if os.path.exists(log_file):
                            with open(log_file, "w", encoding="utf-8") as f:
                                f.write("")
                    print(f"{C_GREEN}✅ Histórico de logs reiniciado!{C_RESET}")
                except Exception as e:
                    print(
                        f"{C_RED}❌ Falha ao tentar resetar os arquivos: {e}{C_RESET}"
                    )
                time.sleep(2)
        elif choice == "4":
            clear_screen()
            print(f"{C_CYAN}╔══════════════════════════════════════════╗")
            print(f"║           ESTATÍSTICAS DE USO            ║")
            print(f"╚══════════════════════════════════════════╝{C_RESET}\n")
            stats_file = "logs/bot_stats.json"
            if os.path.exists(stats_file):
                try:
                    with open(stats_file, "r", encoding="utf-8") as f:
                        stats = json.load(f)
                    print(
                        f"  {C_YELLOW}⏱️  Tempo de Atividade:{C_RESET} {stats.get('uptime', '0:00:00')}"
                    )
                    print(
                        f"  {C_YELLOW}🏢 Servidores Conectados:{C_RESET} {stats.get('servers', 0)}"
                    )
                    print(
                        f"  {C_YELLOW}👥 Usuários Alcançados:{C_RESET} {stats.get('users', 0)}\n"
                    )
                    print(
                        f"  {C_GREEN}✉️  Mensagens Processadas:{C_RESET} {stats.get('messages_read', 0)}"
                    )
                    print(
                        f"  {C_GREEN}⌨️  Comandos Acionados:{C_RESET} {stats.get('commands_used', 0)}"
                    )
                    print(
                        f"  {C_GREEN}🎙️  Minutos Ativos em Chamada:{C_RESET} {stats.get('voice_time_minutes', 0)} min"
                    )
                except Exception as e:
                    print(f"{C_RED}❌ Falha na leitura das estatísticas: {e}{C_RESET}")
            else:
                print(
                    f"{C_YELLOW}ℹ️ O arquivo de métricas ainda não foi gerado pelo Bot.{C_RESET}"
                )
            input(f"\nPressione {C_YELLOW}ENTER{C_RESET} para retornar...")
        elif choice == "0":
            break


def docker_menu():
    """Painel de controle avançado para o Docker Compose."""
    while True:
        print_header()
        print(f"{C_CYAN}--- Gerenciador Docker (Compose) ---{C_RESET}")
        print("  [ 1 ] 📄 Ver Logs (Ao vivo + Últimas 50 linhas)")
        print("  [ 2 ] 🛑 Parar Containers (Down)")
        print("  [ 3 ] 🔁 Reiniciar Bot (Restart)")
        print("  [ 4 ] 🔄 Forçar Rebuild e Inicializar (Up -d --build)")
        print("  [ 0 ] Voltar")

        choice = input(f"\n{C_BOLD}Escolha uma opção: {C_RESET}")

        if choice == "1":
            print(
                f"{C_CYAN}Acompanhando logs do container... (Pressione Ctrl+C para voltar){C_RESET}"
            )
            try:
                subprocess.run(["docker", "compose", "logs", "-f", "--tail=50"])
            except KeyboardInterrupt:
                pass
        elif choice == "2":
            subprocess.run(["docker", "compose", "down"])
            input(
                f"\n{C_YELLOW}Containers desligados com sucesso! Pressione ENTER...{C_RESET}"
            )
        elif choice == "3":
            subprocess.run(["docker", "compose", "restart"])
            input(f"\n{C_GREEN}[V] Containers reiniciados! Pressione ENTER...{C_RESET}")
        elif choice == "4":
            subprocess.run(["docker", "compose", "up", "-d", "--build"])
            input(
                f"\n{C_GREEN}[V] Imagens reconstruídas e ativas em segundo plano! Pressione ENTER...{C_RESET}"
            )
        elif choice == "0":
            break


def start_menu():
    """Menu de inicialização."""
    if not os.path.exists(".env"):
        print(
            f"{C_RED}[X] Erro: Arquivo .env ausente! Execute o configurador (Opção 2).{C_RESET}"
        )
        time.sleep(3)
        return

    while True:
        print_header()
        print(f"{C_CYAN}--- Inicialização do Bot ---{C_RESET}")
        print(f"  [ 1 ] 🐳 Iniciar via Docker (Recomendado)")
        print(f"  [ 2 ] 💻 Iniciar Nativamente (Apenas Python)")
        print(f"  [ 0 ] Voltar")

        choice = input(f"\n{C_BOLD}Escolha como deseja iniciar: {C_RESET}")

        if choice == "1":
            print(f"\n{C_GREEN}Iniciando via Docker Compose...{C_RESET}")
            subprocess.run(["docker", "compose", "up", "-d"])
            print(f"\n{C_GREEN}[V] Bot iniciado em segundo plano!{C_RESET}")
            input(f"\n{C_CYAN}Pressione ENTER para voltar ao menu...{C_RESET}")
            break
        elif choice == "2":
            print(f"\n{C_MAGENTA}--- Preparando Ambiente Nativo ---{C_RESET}")
            python_exec = ensure_dependencies_and_get_python()
            print(
                f"\n{C_GREEN}Iniciando SamBot nativamente... (Pressione Ctrl+C para encerrar){C_RESET}"
            )
            time.sleep(1)
            clear_screen()
            try:
                subprocess.run([python_exec, "main.py"])
            except KeyboardInterrupt:
                print(f"\n{C_YELLOW}Desligamento manual solicitado.{C_RESET}")
            except Exception as e:
                print(f"{C_RED}Erro ao iniciar o bot nativamente: {e}{C_RESET}")
                input("\nPressione ENTER para voltar.")
            break
        elif choice == "0":
            break


def clean_cache():
    """Limpa a sujeira gerada pelo Python (pastas __pycache__)."""
    count = 0
    for path in Path(".").rglob("__pycache__"):
        try:
            shutil.rmtree(path)
            count += 1
        except Exception:
            pass
    print(
        f"{C_GREEN}[V] Limpeza finalizada! {count} diretórios de cache removidos.{C_RESET}"
    )
    time.sleep(1.5)


def main_menu():
    """Menu principal centralizador."""
    if not os.path.exists(".env"):
        setup_wizard(first_time=True)

    while True:
        print_header()
        env_status = (
            f"{C_GREEN}Configurado{C_RESET}"
            if os.path.exists(".env")
            else f"{C_RED}Pendente (.env){C_RESET}"
        )
        print(f"Status do Ambiente: {env_status}\n")

        print(f"  [ 1 ] {C_GREEN}Iniciar Bot (Docker / Nativo){C_RESET}")
        print(
            f"  [ 2 ] {C_YELLOW}Assistente de Configuração Inteligente (.env){C_RESET}"
        )
        print(
            f"  [ 3 ] {C_MAGENTA}Verificar Atualizações do Repositório (Git Pull){C_RESET}"
        )
        print(f"  [ 4 ] Diagnóstico Geral do Sistema (APIs, Mídia e Rede)")
        print(f"  [ 5 ] Gerenciador Docker Compose")
        print(f"  [ 6 ] Painel de Métricas e Logs Locais")
        print(f"  [ 7 ] Limpar Cache do Python (__pycache__)")
        print(f"  [ 0 ] Sair")

        choice = input(f"\n{C_BOLD}Selecione a ação desejada: {C_RESET}").strip()

        if choice == "1":
            start_menu()
        elif choice == "2":
            setup_wizard()
        elif choice == "3":
            git_updater()
        elif choice == "4":
            run_diagnostics()
        elif choice == "5":
            docker_menu()
        elif choice == "6":
            run_logs_menu()
        elif choice == "7":
            clean_cache()
        elif choice == "0":
            clear_screen()
            print(f"{C_CYAN}Até logo! Obrigado por utilizar a SamBot. ♡{C_RESET}")
            sys.exit(0)
        else:
            print(f"{C_RED}Opção inválida!{C_RESET}")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        clear_screen()
        print(f"\n{C_CYAN}Launcher encerrado de forma segura.{C_RESET}")
        sys.exit(0)
