import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

if os.name == "nt":
    subprocess.run("", shell=True)

C_RESET = "\033[0m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_MAGENTA = "\033[95m"
C_BOLD = "\033[1m"


def clear_screen():
    """Limpa a tela do terminal usando sequências ANSI universais."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def print_header():
    """Exibe o cabeçalho estilizado do launcher."""
    clear_screen()
    print(f"{C_CYAN}{C_BOLD}")
    print(r"  ____                  ____        _   ")
    print(r" / ___|  __ _ _ __ ___ | __ )  ___ | |_ ")
    print(r" \___ \ / _` | '_ ` _ \|  _ \ / _ \| __|")
    print(r"  ___) | (_| | | | | | | |_) | (_) | |_ ")
    print(r" |____/ \__,_|_| |_| |_|____/ \___/ \__|")
    print(f"                               v3.3.1-beta{C_RESET}")
    print(f"{C_MAGENTA}>> Centro de Controle, Diagnóstico e Operação <<{C_RESET}\n")


def get_python_cmd():
    """Retorna o comando correto do Python dependendo do SO."""
    return "python" if os.name == "nt" else "python3"


def ping_host(host, port, timeout=2):
    """Testa se uma porta TCP está aberta."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def check_http_service(url, timeout=3):
    """Verifica se um serviço HTTP/HTTPS está acessível."""
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        req = urllib.request.Request(url, headers={"User-Agent": "SamBotLauncher/3.3"})
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


def save_env_file(env_data):
    """Grava as variáveis no arquivo .env com formatação segura."""
    with open(".env", "w", encoding="utf-8") as f:
        for k, v in env_data.items():
            if v is not None:
                f.write(f'{k}="{v}"\n')


def read_last_lines(filepath, num_lines=30):
    """Lê as últimas N linhas de um arquivo de log de forma segura."""
    if not os.path.exists(filepath):
        return f"{C_YELLOW}ℹ️ Nenhum registro encontrado neste arquivo ainda.{C_RESET}"

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            if not lines:
                return f"{C_YELLOW}ℹ️ O arquivo de log está vazio.{C_RESET}"
            return "".join(lines[-num_lines:])
    except Exception as e:
        return f"{C_RED}❌ Erro ao ler o log: {e}{C_RESET}"


def ensure_dependencies_and_get_python():
    """Verifica/instala dependências, criando venv se necessário (PEP 668)."""
    print(f"{C_YELLOW}[!] Verificando ambiente e dependências...{C_RESET}")
    if not os.path.exists("requirements.txt"):
        print(f"{C_RED}[X] requirements.txt não encontrado!{C_RESET}")
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
                f"{C_YELLOW}[!] Ambiente gerenciado (PEP 668). Criando .venv...{C_RESET}"
            )
            subprocess.run([base_python, "-m", "venv", ".venv"], check=True)
            print(f"{C_YELLOW}[!] Instalando pacotes no ambiente virtual...{C_RESET}")
            cmd = [venv_python, "-m", "pip", "install", "-r", "requirements.txt"]
            subprocess.run(cmd, check=True)
            print(f"{C_GREEN}[V] Dependências instaladas no .venv!{C_RESET}")
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
    """Verifica atualizações via Git e permite sincronização rápida."""
    print_header()
    print(f"{C_CYAN}--- Atualizador de Repositório (Git) ---{C_RESET}\n")

    try:
        subprocess.run(
            ["git", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except Exception:
        print(f"{C_RED}[X] O Git não está instalado ou disponível no PATH.{C_RESET}")
        input(f"\n{C_CYAN}Pressione ENTER para voltar...{C_RESET}")
        return

    print(f"{C_YELLOW}[!] Verificando branches remotas...{C_RESET}")
    subprocess.run(["git", "fetch"])
    status = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True)
    print(f"\n{status.stdout}")

    if "behind" in status.stdout or "atrás" in status.stdout:
        resp = input(f"{C_BOLD}Deseja puxar as atualizações agora? (s/n): {C_RESET}")
        if resp.lower() == "s":
            print(f"{C_GREEN}Atualizando repositório...{C_RESET}")
            subprocess.run(["git", "pull"])
            print(f"{C_GREEN}[V] Sistema atualizado com sucesso!{C_RESET}")
    elif "up to date" in status.stdout or "atualizado" in status.stdout:
        print(f"{C_GREEN}[V] O bot já está na versão mais recente.{C_RESET}")
    else:
        print(
            f"{C_YELLOW}[?] Existem modificações locais pendentes ou branch divergente.{C_RESET}"
        )

    input(f"\n{C_CYAN}Pressione ENTER para voltar...{C_RESET}")


def run_diagnostics():
    """Executa checagem de integridade das portas e microserviços."""
    print_header()
    print(f"{C_CYAN}--- Diagnóstico de Subsistemas & Rede ---{C_RESET}\n")
    print(f"Versão do Python: {C_YELLOW}{sys.version.split()[0]}{C_RESET}")

    # Internet
    print("Conexão Externa (Internet): ", end="")
    try:
        with urllib.request.urlopen("https://1.1.1.1", timeout=3):
            print(f"{C_GREEN}Online (1.1.1.1){C_RESET}")
    except Exception:
        print(f"{C_RED}Offline{C_RESET}")

    env_data = read_env_file()
    print("Arquivo de Configuração (.env): ", end="")
    print(f"{C_GREEN}Presente{C_RESET}" if env_data else f"{C_RED}Ausente{C_RESET}")

    # API Interna da SamBot (Porta 8001 padrão)
    api_port = 8001
    print(f"API Interna SamBot (0.0.0.0:{api_port}): ", end="")
    if ping_host("127.0.0.1", api_port):
        print(f"{C_GREEN}Online (Porta {api_port}){C_RESET}")
    else:
        print(f"{C_YELLOW}Offline / Não inicializada{C_RESET}")

    # Lavalink
    lava_host = env_data.get("LAVALINK_HOST", "127.0.0.1")
    lava_port = env_data.get("LAVALINK_PORT", "2333")
    print(f"Lavalink Audio Engine ({lava_host}:{lava_port}): ", end="")
    if ping_host(lava_host, lava_port):
        print(f"{C_GREEN}Porta Aberta{C_RESET}")
    else:
        print(f"{C_YELLOW}Inacessível / Aguardando start{C_RESET}")

    # Meilisearch
    meili_host = env_data.get("MEILI_HOST", "http://127.0.0.1:7700")
    print(f"Meilisearch ({meili_host}): ", end="")
    if check_http_service(meili_host):
        print(f"{C_GREEN}Online{C_RESET}")
    else:
        print(f"{C_RED}Inacessível{C_RESET}")

    # Navidrome
    navi_url = env_data.get("NAVIDROME_URL", "")
    if navi_url:
        print(f"Navidrome Server ({navi_url}): ", end="")
        if check_http_service(navi_url):
            print(f"{C_GREEN}Online{C_RESET}")
        else:
            print(f"{C_RED}Inacessível{C_RESET}")

    # Worker yt-dlp
    yt_url = env_data.get("YT_WORKER_URL", "http://127.0.0.1:4000")
    print(f"Download Worker yt-dlp ({yt_url}): ", end="")
    if check_http_service(yt_url):
        print(f"{C_GREEN}Online{C_RESET}")
    else:
        print(f"{C_YELLOW}Inacessível (Worker offline){C_RESET}")

    # Jellyfin
    jelly_url = env_data.get("JELLYFIN_URL", "")
    if jelly_url:
        print(f"Jellyfin Media ({jelly_url}): ", end="")
        if check_http_service(jelly_url):
            print(f"{C_GREEN}Online{C_RESET}")
        else:
            print(f"{C_YELLOW}Inacessível{C_RESET}")

    # Ollama Local
    ollama_url = env_data.get("OLLAMA_LOCAL_URL", "http://127.0.0.1:11434")
    if ollama_url:
        print(f"Ollama Local ({ollama_url}): ", end="")
        if check_http_service(ollama_url):
            print(f"{C_GREEN}Online{C_RESET}")
        else:
            print(f"{C_YELLOW}Inacessível{C_RESET}")

    input(f"\n{C_CYAN}Pressione ENTER para voltar ao menu...{C_RESET}")


def setup_wizard(first_time=False):
    """Assistente interativo de configuração de ambiente."""
    current_env = read_env_file()

    if first_time or not current_env:
        clear_screen()
        print(f"{C_CYAN}{C_BOLD}╔══════════════════════════════════════════╗")
        print(f"║      SAMBOT - ASSISTENTE DE CONFIG       ║")
        print(f"╚══════════════════════════════════════════╝{C_RESET}")
        print(
            f"\n{C_YELLOW}Configuração rápida das variáveis essenciais do sistema.{C_RESET}\n"
        )
    else:
        print_header()
        print(f"{C_GREEN}[!] Arquivo .env existente detectado.{C_RESET}")
        print("  [ 1 ] Atualizar variáveis mantendo as existentes")
        print("  [ 2 ] Redefinir do zero (Limpar arquivo)")
        print("  [ 0 ] Voltar")
        escolha = input(f"\n{C_BOLD}Escolha: {C_RESET}").strip()

        if escolha == "0":
            return
        elif escolha == "2":
            if (
                input(f"{C_RED}Confirma a limpeza do .env? (s/n): {C_RESET}").lower()
                != "s"
            ):
                return
            current_env = {}
        elif escolha != "1":
            return

    def ask(key, prompt, help_text, default_fallback=""):
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

    print(f"\n{C_MAGENTA}{C_BOLD}--- 📌 CONFIGURAÇÕES ESSENCIAIS ---{C_RESET}")
    print(f"{C_CYAN}(Pressione ENTER para manter ou digite '?' para ajuda){C_RESET}\n")

    env_data["DISCORD_TOKEN"] = ask(
        "DISCORD_TOKEN",
        "🔑 Token do Bot Discord",
        "Token oficial do Discord Developer Portal.",
    )
    env_data["OWNER_ID"] = ask(
        "OWNER_ID",
        "👑 ID do Proprietário (Owner)",
        "Seu ID numérico de usuário no Discord.",
    )
    env_data["API_SECRET_TOKEN"] = ask(
        "API_SECRET_TOKEN",
        "🛡️ Chave de Segurança da API Interna (X-Bot-Token)",
        "Token compartilhado entre o backend e a WebUI/Dashboard.",
        "sambot_secret_token_industrial_2026",
    )

    save_env_file(env_data)

    while True:
        clear_screen()
        print_header()
        print(f"{C_GREEN}{C_BOLD}✅ Configurações Base salvas!{C_RESET}")
        print(f"\nCategorias de subsistemas para personalização:")
        print(
            f"  {C_BOLD}[ 1 ] 🎵 Áudio & Mídia{C_RESET} (Navidrome, Lavalink, Worker yt-dlp)"
        )
        print(
            f"  {C_BOLD}[ 2 ] 🧠 Provedores de IA{C_RESET} (Gemini, Groq, DeepSeek, Mistral, Ollama)"
        )
        print(
            f"  {C_BOLD}[ 3 ] 🌐 Auth Discord & Webhooks{C_RESET} (OAuth2 Client ID/Secret)"
        )
        print(
            f"  {C_BOLD}[ 4 ] ✈️ Telegram & Meilisearch{C_RESET} (Telethon e Ingestão de Ofertas)"
        )
        print(
            f"  {C_BOLD}[ 5 ] 🛠️ Ferramentas & Pesquisa{C_RESET} (Google, Brave, IGDB, Pixabay, Jellyfin)"
        )
        print(f"\n  {C_GREEN}[ ENTER / 0 ] Concluir e Sair do Assistente{C_RESET}")

        opcao = input(f"\n{C_BOLD}Opção: {C_RESET}").strip()
        if opcao in ("", "0"):
            break

        # 1. ÁUDIO & MÍDIA
        elif opcao == "1":
            print(f"\n{C_MAGENTA}--- 🎵 Áudio & Mídia ---{C_RESET}")
            env_data["MUSIC_SOURCE_MODE"] = ask(
                "MUSIC_SOURCE_MODE",
                "Modo de Fonte (LOCAL / ONLINE)",
                "LOCAL = Navidrome | ONLINE = Web/Lavalink",
                "LOCAL",
            )
            env_data["LAVALINK_HOST"] = ask(
                "LAVALINK_HOST", "Lavalink Host", "Host do Lavalink", "lavalink"
            )
            env_data["LAVALINK_PORT"] = ask(
                "LAVALINK_PORT", "Lavalink Porta", "Porta do Lavalink", "2333"
            )
            env_data["LAVALINK_PASSWORD"] = ask(
                "LAVALINK_PASSWORD",
                "Lavalink Senha",
                "Senha no application.yml",
                "youshallnotpass",
            )
            env_data["NAVIDROME_URL"] = ask(
                "NAVIDROME_URL",
                "URL Navidrome",
                "Ex: http://navidrome:4533",
                "http://127.0.0.1:4533",
            )
            env_data["NAVIDROME_USER"] = ask(
                "NAVIDROME_USER",
                "Usuário Navidrome",
                "Conta para streaming da Sam",
                "sambot",
            )
            env_data["NAVIDROME_PASSWORD"] = ask(
                "NAVIDROME_PASSWORD", "Senha Navidrome", "Senha da conta", "sambot123"
            )
            env_data["YT_WORKER_URL"] = ask(
                "YT_WORKER_URL",
                "Worker yt-dlp",
                "Servidor de downloads",
                "http://127.0.0.1:4000",
            )
            save_env_file(env_data)
            time.sleep(1)

        # 2. IA / LLM
        elif opcao == "2":
            print(f"\n{C_MAGENTA}--- 🧠 Inteligência Artificial ---{C_RESET}")
            env_data["GEMINI_MODEL_NAME"] = ask(
                "GEMINI_MODEL_NAME",
                "Modelo Gemini",
                "Modelo primário Google",
                "gemini-2.5-flash",
            )
            env_data["GEMINI_API_KEY"] = ask(
                "GEMINI_API_KEY", "Chave Gemini Principal", "Google AI Studio Key"
            )
            env_data["GEMINI_API_KEY_1"] = ask(
                "GEMINI_API_KEY_1",
                "Chave Gemini Reserva 1",
                "Chave para rotação/rate limit",
            )
            env_data["GROQ_API_KEY"] = ask(
                "GROQ_API_KEY", "Chave Groq", "Groq Console API Key"
            )
            env_data["DEEPSEEK_API_KEY"] = ask(
                "DEEPSEEK_API_KEY", "Chave DeepSeek", "DeepSeek Platform Key"
            )
            env_data["MISTRAL_API_KEY"] = ask(
                "MISTRAL_API_KEY", "Chave Mistral AI", "Mistral Console Key"
            )
            env_data["OPENROUTER_API_KEY"] = ask(
                "OPENROUTER_API_KEY", "Chave OpenRouter", "OpenRouter Key"
            )
            env_data["OLLAMA_LOCAL_URL"] = ask(
                "OLLAMA_LOCAL_URL",
                "URL Ollama Local",
                "Ollama local/docker",
                "http://host.docker.internal:11434",
            )
            save_env_file(env_data)
            time.sleep(1)

        # 3. DISCORD OAUTH2
        elif opcao == "3":
            print(f"\n{C_MAGENTA}--- 🌐 Discord OAuth2 (WebUI) ---{C_RESET}")
            env_data["DISCORD_CLIENT_ID"] = ask(
                "DISCORD_CLIENT_ID", "Discord Client ID", "ID da aplicação Discord"
            )
            env_data["DISCORD_CLIENT_SECRET"] = ask(
                "DISCORD_CLIENT_SECRET",
                "Discord Client Secret",
                "Client Secret no portal de devs",
            )
            save_env_file(env_data)
            time.sleep(1)

        # 4. TELEGRAM & MEILISEARCH
        elif opcao == "4":
            print(f"\n{C_MAGENTA}--- ✈️ Telegram & Meilisearch ---{C_RESET}")
            env_data["TELEGRAM_ENABLED"] = ask(
                "TELEGRAM_ENABLED",
                "Habilitar Scraper (true/false)",
                "Telethon Ingestor",
                "false",
            )
            env_data["TELEGRAM_API_ID"] = ask(
                "TELEGRAM_API_ID", "Telegram API ID", "my.telegram.org"
            )
            env_data["TELEGRAM_API_HASH"] = ask(
                "TELEGRAM_API_HASH", "Telegram API Hash", "my.telegram.org"
            )
            env_data["MEILI_HOST"] = ask(
                "MEILI_HOST",
                "Meilisearch Host",
                "Endereço do Meilisearch",
                "http://meilisearch:7700",
            )
            env_data["MEILI_MASTER_KEY"] = ask(
                "MEILI_MASTER_KEY",
                "Meilisearch Master Key",
                "Chave de autenticação",
                "sua_chave_master_aqui",
            )
            save_env_file(env_data)
            time.sleep(1)

        # 5. FERRAMENTAS & PESQUISA
        elif opcao == "5":
            print(f"\n{C_MAGENTA}--- 🛠️ Ferramentas & Pesquisa ---{C_RESET}")
            env_data["GOOGLE_SEARCH_API_KEY"] = ask(
                "GOOGLE_SEARCH_API_KEY", "Google Search Key", "Chave Custom Search API"
            )
            env_data["GOOGLE_SEARCH_CX"] = ask(
                "GOOGLE_SEARCH_CX", "Google Search CX ID", "ID do motor Custom Search"
            )
            env_data["BRAVE_SEARCH_API_KEY"] = ask(
                "BRAVE_SEARCH_API_KEY", "Brave Search Key", "Brave Search API Key"
            )
            env_data["PIXABAY_API_KEY"] = ask(
                "PIXABAY_API_KEY", "Pixabay Key", "Chave do Pixabay"
            )
            env_data["GIPHY_API_KEY"] = ask(
                "GIPHY_API_KEY", "Giphy Key", "Chave de GIFs da Giphy"
            )
            env_data["IGDB_CLIENT_ID"] = ask(
                "IGDB_CLIENT_ID", "Twitch/IGDB Client ID", "Twitch Developer Console"
            )
            env_data["IGDB_CLIENT_SECRET"] = ask(
                "IGDB_CLIENT_SECRET", "Twitch/IGDB Secret", "Twitch Developer Secret"
            )
            env_data["JELLYFIN_URL"] = ask(
                "JELLYFIN_URL", "Jellyfin URL", "URL do servidor Jellyfin"
            )
            env_data["JELLYFIN_API_KEY"] = ask(
                "JELLYFIN_API_KEY", "Jellyfin API Key", "Token do Jellyfin"
            )
            save_env_file(env_data)
            time.sleep(1)

    save_env_file(env_data)
    print(f"\n{C_GREEN}[V] Arquivo .env gravado com sucesso!{C_RESET}")
    time.sleep(1.5)


def run_logs_menu():
    """Painel de inspeção de logs e estatísticas consolidadas."""
    while True:
        print_header()
        print(f"{C_CYAN}--- Monitor de Logs e Telemetria ---{C_RESET}\n")
        print("  [ 1 ] 📋 Ver Logs Gerais Recentes")
        print("  [ 2 ] ❌ Ver Logs de Erros")
        print("  [ 3 ] 🧹 Esvaziar Histórico de Logs")
        print("  [ 4 ] 📊 Inspecionar Telemetria / Estatísticas")
        print("  [ 0 ] Voltar")

        choice = input(f"\n{C_BOLD}Escolha uma opção: {C_RESET}").strip()

        if choice == "1":
            clear_screen()
            print(f"{C_CYAN}--- Últimos Logs Gerais ---{C_RESET}\n")
            print(read_last_lines("logs/sambot_general.log"))
            input(f"\nPressione {C_YELLOW}ENTER{C_RESET} para retornar...")
        elif choice == "2":
            clear_screen()
            print(f"{C_RED}--- Últimos Erros Registrados ---{C_RESET}\n")
            print(read_last_lines("logs/sambot_errors.log"))
            input(f"\nPressione {C_YELLOW}ENTER{C_RESET} para retornar...")
        elif choice == "3":
            if (
                input(
                    f"{C_RED}Deseja realmente limpar os logs? (s/n): {C_RESET}"
                ).lower()
                == "s"
            ):
                os.makedirs("logs", exist_ok=True)
                for f_name in ["logs/sambot_general.log", "logs/sambot_errors.log"]:
                    if os.path.exists(f_name):
                        with open(f_name, "w", encoding="utf-8") as f:
                            f.write("")
                print(f"{C_GREEN}Logs reiniciados com sucesso.{C_RESET}")
                time.sleep(1.5)
        elif choice == "4":
            clear_screen()
            print(f"{C_CYAN}--- Estatísticas Consolidadas do Bot ---{C_RESET}\n")
            stats_file = "logs/bot_stats.json"
            if os.path.exists(stats_file):
                try:
                    with open(stats_file, "r", encoding="utf-8") as f:
                        stats = json.load(f)
                    print(
                        f"  {C_YELLOW}⏱️  Tempo de Atividade:{C_RESET} {stats.get('uptime', '0:00:00')}"
                    )
                    print(
                        f"  {C_YELLOW}🏢 Servidores Ativos:{C_RESET} {stats.get('servers', 0)}"
                    )
                    print(
                        f"  {C_YELLOW}👥 Usuários Conectados:{C_RESET} {stats.get('users', 0)}"
                    )
                    print(
                        f"  {C_GREEN}✉️  Mensagens Lidas:{C_RESET} {stats.get('messages_read', 0)}"
                    )
                    print(
                        f"  {C_GREEN}⌨️  Comandos Executados:{C_RESET} {stats.get('commands_used', 0)}"
                    )
                    print(
                        f"  {C_GREEN}🎙️  Minutos de Voz/Música:{C_RESET} {stats.get('voice_time_minutes', 0)} min"
                    )
                except Exception as e:
                    print(f"{C_RED}Falha ao ler métricas: {e}{C_RESET}")
            else:
                print(
                    f"{C_YELLOW}O arquivo bot_stats.json ainda não foi inicializado.{C_RESET}"
                )
            input(f"\nPressione {C_YELLOW}ENTER{C_RESET} para retornar...")
        elif choice == "0":
            break


def docker_menu():
    """Gerenciamento de containers via Docker Compose."""
    while True:
        print_header()
        print(f"{C_CYAN}--- Controle Docker Compose ---{C_RESET}\n")
        print("  [ 1 ] 📄 Acompanhar Logs")
        print("  [ 2 ] 🛑 Encerrar Containers")
        print("  [ 3 ] 🔁 Reiniciar Serviços")
        print("  [ 4 ] 🔄 Reconstruir e Subir")
        print("  [ 0 ] Voltar")

        choice = input(f"\n{C_BOLD}Opção: {C_RESET}").strip()

        if choice == "1":
            print(
                f"{C_CYAN}Conectando ao stream do Compose... (Ctrl+C para sair){C_RESET}"
            )
            try:
                subprocess.run(["docker", "compose", "logs", "-f", "--tail=50"])
            except KeyboardInterrupt:
                pass
        elif choice == "2":
            subprocess.run(["docker", "compose", "down"])
            input(f"\n{C_YELLOW}Containers encerrados. Pressione ENTER...{C_RESET}")
        elif choice == "3":
            subprocess.run(["docker", "compose", "restart"])
            input(f"\n{C_GREEN}Serviços reiniciados. Pressione ENTER...{C_RESET}")
        elif choice == "4":
            subprocess.run(["docker", "compose", "up", "-d", "--build"])
            input(
                f"\n{C_GREEN}Rebuild concluído e ativo em background! Pressione ENTER...{C_RESET}"
            )
        elif choice == "0":
            break


def start_menu():
    """Seleção de inicialização."""
    if not os.path.exists(".env"):
        print(
            f"{C_RED}[X] Erro: Arquivo .env ausente! Execute o assistente primeiro.{C_RESET}"
        )
        time.sleep(2)
        return

    while True:
        print_header()
        print(f"{C_CYAN}--- Inicialização do Sistema ---{C_RESET}\n")
        print("  [ 1 ] 🐳 Iniciar via Docker Compose (Recomendado)")
        print("  [ 2 ] 💻 Iniciar Nativamente (Apenas Python local)")
        print("  [ 0 ] Voltar")

        choice = input(f"\n{C_BOLD}Escolha: {C_RESET}").strip()

        if choice == "1":
            print(f"\n{C_GREEN}Subindo stack Docker...{C_RESET}")
            subprocess.run(["docker", "compose", "up", "-d"])
            print(f"\n{C_GREEN}[V] Stack ativa em segundo plano!{C_RESET}")
            input(f"\n{C_CYAN}Pressione ENTER para voltar...{C_RESET}")
            break
        elif choice == "2":
            py_exec = ensure_dependencies_and_get_python()
            print(
                f"\n{C_GREEN}Iniciando SamBot nativamente... (Ctrl+C para encerrar){C_RESET}"
            )
            time.sleep(1)
            clear_screen()
            try:
                subprocess.run([py_exec, "main.py"])
            except KeyboardInterrupt:
                print(f"\n{C_YELLOW}Execução interrompida.{C_RESET}")
            except Exception as e:
                print(f"{C_RED}Erro ao iniciar o bot: {e}{C_RESET}")
                input("\nPressione ENTER para voltar...")
            break
        elif choice == "0":
            break


def clean_cache():
    """Remove pastas __pycache__ e arquivos .pyc compilados."""
    count = 0
    for path in Path(".").rglob("__pycache__"):
        try:
            shutil.rmtree(path)
            count += 1
        except Exception:
            pass
    print(f"{C_GREEN}[V] Concluído! {count} diretórios de cache eliminados.{C_RESET}")
    time.sleep(1.5)


def main_menu():
    """Menu central."""
    if not os.path.exists(".env"):
        setup_wizard(first_time=True)

    while True:
        print_header()
        status_env = (
            f"{C_GREEN}Configurado{C_RESET}"
            if os.path.exists(".env")
            else f"{C_RED}Pendente (.env){C_RESET}"
        )
        print(f"Status do Ambiente: {status_env}\n")

        print(f"  [ 1 ] {C_GREEN}Iniciar SamBot (Docker / Nativo){C_RESET}")
        print(f"  [ 2 ] {C_YELLOW}Assistente de Configuração (.env){C_RESET}")
        print(f"  [ 3 ] {C_MAGENTA}Sincronizar Atualizações (Git Pull){C_RESET}")
        print(f"  [ 4 ] Diagnóstico de Portas e Serviços")
        print(f"  [ 5 ] Gerenciador Docker Compose")
        print(f"  [ 6 ] Logs e Telemetria")
        print(f"  [ 7 ] Limpar Caches do Python")
        print(f"  [ 0 ] Sair")

        choice = input(f"\n{C_BOLD}Selecione uma opção: {C_RESET}").strip()

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
            print(f"{C_CYAN}Até logo! SamBot finalizada. ♡{C_RESET}")
            sys.exit(0)
        else:
            print(f"{C_RED}Opção inválida!{C_RESET}")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        clear_screen()
        print(f"\n{C_CYAN}Launcher encerrado.{C_RESET}")
        sys.exit(0)
