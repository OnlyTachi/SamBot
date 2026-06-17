import os
import sys
import subprocess
import time
import socket
import urllib.request
import re
import json
import shutil
from pathlib import Path

# --- Configuração de Cores ANSI (Multiplataforma) ---
os.system("")  # Habilita suporte a cores ANSI no CMD do Windows
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
    print(f"                                   v3.5{C_RESET}")
    print(f"{C_MAGENTA}>> Centro de Controle, Diagnóstico e Configuração <<{C_RESET}\n")


def get_python_cmd():
    """Retorna o comando correto do Python dependendo do SO."""
    return "python" if os.name == "nt" else "python3"


def ping_host(host, port, timeout=3):
    """Testa se uma porta TCP está aberta."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False


def read_env_file():
    """Lê o arquivo .env atual para um dicionário de configurações."""
    env_data = {}
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Ignora linhas vazias e comentários
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    # Limpa aspas se presentes
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
    """Verifica/instala dependências, criando venv se necessário (PEP 668). Retorna o comando python correto."""
    print(f"{C_YELLOW}[!] Verificando e instalando dependências...{C_RESET}")
    if not os.path.exists("requirements.txt"):
        print(
            f"{C_RED}[X] Arquivo requirements.txt não encontrado! Ignorando instalação.{C_RESET}"
        )
        return get_python_cmd()

    base_python = get_python_cmd()

    # Verifica se já existe um ambiente virtual
    venv_python = os.path.join(
        ".venv", "Scripts" if os.name == "nt" else "bin", "python"
    )
    has_venv = os.path.exists(venv_python)
    active_python = venv_python if has_venv else base_python

    cmd = [active_python, "-m", "pip", "install", "-r", "requirements.txt"]

    try:
        # Redirecionamos a saída para capturar o erro PEP 668 se ocorrer
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"{C_GREEN}[V] Dependências verificadas com sucesso!{C_RESET}")
            return active_python

        # Se falhou devido a ambiente gerenciado externamente
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

    except subprocess.CalledProcessError:
        print(f"{C_RED}[X] Falha crítica ao criar ou usar o ambiente virtual.{C_RESET}")
        return active_python
    except Exception as e:
        print(f"{C_RED}[X] Erro inesperado: {e}{C_RESET}")
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
            print(
                f"{C_YELLOW}Dica: Caso novas dependências tenham sido adicionadas, verifique-as ao iniciar o bot.{C_RESET}"
            )
    elif "up to date" in status.stdout or "atualizado" in status.stdout:
        print(
            f"{C_GREEN}[V] O seu bot já está na versão mais recente do repositório!{C_RESET}"
        )
    else:
        print(
            f"{C_YELLOW}[?] Status de repositório desconhecido ou você possui alterações locais pendentes.{C_RESET}"
        )

    input(f"\n{C_CYAN}Pressione ENTER para voltar ao menu...{C_RESET}")


def run_diagnostics():
    """Roda testes de rede, conexões de APIs e arquivos locais."""
    print_header()
    print(f"{C_CYAN}--- Executando Diagnóstico do Sistema ---{C_RESET}\n")

    print(f"Versão do Python: {C_YELLOW}{sys.version.split()[0]}{C_RESET}")

    print("Conexão com a Internet: ", end="")
    try:
        urllib.request.urlopen("https://1.1.1.1", timeout=3)
        print(f"{C_GREEN}Online{C_RESET}")
    except Exception:
        print(f"{C_RED}Offline{C_RESET}")

    print("Arquivo .env: ", end="")
    if os.path.exists(".env"):
        print(f"{C_GREEN}Encontrado{C_RESET}")
    else:
        print(f"{C_RED}Não encontrado (Use o Assistente de Configuração){C_RESET}")

    print("Lavalink Externo (lavalinkv4.serenetia.com:443): ", end="")
    if ping_host("lavalinkv4.serenetia.com", 443):
        print(f"{C_GREEN}Acessível{C_RESET}")
    else:
        print(f"{C_RED}Inacessível / Bloqueado{C_RESET}")

    input(f"\n{C_CYAN}Pressione ENTER para voltar ao menu...{C_RESET}")


def setup_wizard(first_time=False):
    """Assistente interativo inteligente para geração e edição do .env."""
    current_env = read_env_file()

    if first_time or not current_env:
        clear_screen()
        print(f"{C_CYAN}{C_BOLD}")
        print(f"╔══════════════════════════════════════════╗")
        print(f"║       SAMBOT - ASSISTENTE DE CONFIG      ║")
        print(f"╚══════════════════════════════════════════╝{C_RESET}")
        print(
            f"\n{C_YELLOW}Parece que é sua primeira vez aqui! Vamos configurar o básico.{C_RESET}"
        )
        print(
            f"({C_CYAN}Dica: Se não souber o que responder, digite ? e aperte Enter{C_RESET})\n"
        )
    else:
        print_header()
        print(
            f"{C_YELLOW}Bem-vindo ao Assistente de Configuração Inteligente!{C_RESET}"
        )
        print(f"\n{C_GREEN}[!] Um arquivo .env já foi detectado.{C_RESET}")
        print("  [ 1 ] Editar arquivo atual (Mantém as chaves se deixar em branco)")
        print("  [ 2 ] Sobrescrever tudo (Começar do zero)")
        print("  [ 0 ] Cancelar e voltar")
        escolha = input(f"\n{C_BOLD}Escolha: {C_RESET}")

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

        print(
            f"\n({C_CYAN}Dica: Digite '?' para ajuda ou aperte ENTER para manter o valor atual entre colchetes []{C_RESET})\n"
        )

    def ask(key, prompt, help_text, default_fallback=""):
        default_val = current_env.get(key, default_fallback)
        while True:
            display_default = (
                f" [{C_GREEN}{default_val}{C_RESET}]" if default_val else ""
            )
            val = input(f"{C_BOLD}{prompt}{display_default}{C_RESET} ").strip()

            if val == "?":
                print(f"\n{C_CYAN}💡 Ajuda:{C_RESET} {help_text}\n")
            elif val == "":
                return default_val
            else:
                return val

    # Dicionário temporário para guardar as novas edições
    env_data = current_env.copy()

    # Configurações Principais
    print(f"\n{C_MAGENTA}--- Configuração Principal ---{C_RESET}")
    env_data["DISCORD_TOKEN"] = ask(
        "DISCORD_TOKEN",
        "🔑 Token do bot?",
        "O token secreto do seu bot gerado no Discord Developer Portal (https://discord.com/developers/applications).",
    )
    env_data["OWNER_ID"] = ask(
        "OWNER_ID",
        "👑 ID do Dono (Owner ID)?",
        "Seu ID numérico do Discord para obter permissões administrativas máximas de dono no bot.",
    )
    env_data["BOT_PREFIX"] = ask(
        "BOT_PREFIX",
        "⚡ Prefixo do Bot?",
        "Símbolo para comandos de texto convencionais (ex: +).",
        "+",
    )

    # Configurações do Servidor de Áudio Lavalink
    print(f"\n{C_MAGENTA}--- Configuração de Áudio (Lavalink) ---{C_RESET}")
    env_data["LAVALINK_HOST"] = ask(
        "LAVALINK_HOST",
        "📻 Host do Lavalink?",
        "O endereço do servidor de áudio Lavalink.",
        "lavalinkv4.serenetia.com",
    )
    env_data["LAVALINK_PORT"] = ask(
        "LAVALINK_PORT",
        "🔌 Porta do Lavalink?",
        "A porta de comunicação do servidor (geralmente 443 para conexões seguras SSL).",
        "443",
    )
    env_data["LAVALINK_PASSWORD"] = ask(
        "LAVALINK_PASSWORD",
        "🔒 Senha do Lavalink?",
        "Senha de autenticação de sua instância Lavalink.",
        "https://seretia.link/discord",
    )

    # Configurações de Mídia / Navidrome
    print(f"\n{C_MAGENTA}--- Configuração do Navidrome (Mídia Local) ---{C_RESET}")
    env_data["MUSIC_SOURCE_MODE"] = ask(
        "MUSIC_SOURCE_MODE",
        "🔀 Modo de Busca (HIBRIDO, LOCAL, ONLINE)?",
        "Como o bot deve buscar músicas. HIBRIDO pesquisa no servidor local e faz fallback na internet.",
        "HIBRIDO",
    )
    env_data["NAVIDROME_URL"] = ask(
        "NAVIDROME_URL",
        "🌐 URL do Navidrome?",
        "A URL completa da sua instância Navidrome (Ex: http://192.168.1.100:4533).",
        "",
    )
    env_data["NAVIDROME_USER"] = ask(
        "NAVIDROME_USER",
        "👤 Usuário do Navidrome?",
        "Seu nome de usuário cadastrado no servidor Navidrome.",
        "admin",
    )
    env_data["NAVIDROME_PASSWORD"] = ask(
        "NAVIDROME_PASSWORD",
        "🔑 Senha do Navidrome?",
        "A senha correspondente ao usuário do Navidrome configurado.",
        "",
    )

    # Integrações Avançadas Opcionais
    print(f"\n{C_MAGENTA}--- Integrações Avançadas (Opcionais) ---{C_RESET}")
    do_advanced = (
        input(
            f"Deseja configurar integrações avançadas de APIs (IA, Jogos, Buscas)? (s/n) [{C_YELLOW}n{C_RESET}]: "
        )
        .strip()
        .lower()
    )

    if do_advanced == "s":
        print(f"\n{C_YELLOW}🧠 INTELIGÊNCIA ARTIFICIAL{C_RESET}")
        env_data["GEMINI_API_KEY_1"] = ask(
            "GEMINI_API_KEY_1",
            "Chave da API do Google Gemini?",
            "Sua chave gratuita criada no Google AI Studio (https://aistudio.google.com/) para habilitar IA.",
        )

        print(f"\n{C_YELLOW}🎮 GAMES E LOJAS{C_RESET}")
        env_data["STEAM_API_KEY"] = ask(
            "STEAM_API_KEY",
            "Steam API Key?",
            "Sua chave de desenvolvedor Steam para permitir consultas de jogos (https://steamcommunity.com/dev/apikey).",
        )
        env_data["IGDB_CLIENT_ID"] = ask(
            "IGDB_CLIENT_ID",
            "IGDB Client ID (Twitch)?",
            "O Client ID da Twitch Developers para buscas integradas de games.",
        )
        env_data["IGDB_CLIENT_SECRET"] = ask(
            "IGDB_CLIENT_SECRET",
            "IGDB Client Secret (Twitch)?",
            "O Client Secret gerado no console de desenvolvedor da Twitch.",
        )

        print(f"\n{C_YELLOW}🔍 BUSCA WEB E IMAGENS{C_RESET}")
        env_data["GOOGLE_SEARCH_API_KEY"] = ask(
            "GOOGLE_SEARCH_API_KEY",
            "Google Custom Search API Key?",
            "Sua chave de API do Google Cloud Platform para habilitar buscas na web.",
        )
        env_data["GOOGLE_SEARCH_CX"] = ask(
            "GOOGLE_SEARCH_CX",
            "Google Search Engine ID (CX)?",
            "O ID do mecanismo de busca programável personalizado do Google.",
        )
        env_data["BRAVE_SEARCH_API_KEY"] = ask(
            "BRAVE_SEARCH_API_KEY",
            "Brave Search API Key?",
            "Sua chave da API do Brave Search utilizada como mecanismo alternativo de busca.",
        )
        env_data["PIXABAY_API_KEY"] = ask(
            "PIXABAY_API_KEY",
            "Pixabay API Key?",
            "Sua chave da API Pixabay para envio de imagens temáticas no chat.",
        )

    print(f"\n{C_YELLOW}Salvando arquivo .env...{C_RESET}")
    with open(".env", "w", encoding="utf-8") as f:
        for k, v in env_data.items():
            if v is not None:
                f.write(f'{k}="{v}"\n')

    print(f"{C_GREEN}[V] Configurações salvas no arquivo .env com sucesso!{C_RESET}")
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
                    print(
                        f"{C_RED}❌ Falha na leitura do arquivo JSON de estatísticas: {e}{C_RESET}"
                    )
            else:
                print(
                    f"{C_YELLOW}ℹ️ O arquivo de métricas ainda não foi gerado pelo Bot.{C_RESET}"
                )
                print(
                    "   (Ligue o bot por alguns instantes para que as estatísticas sejam salvas)."
                )

            input(f"\nPressione {C_YELLOW}ENTER{C_RESET} para retornar...")

        elif choice == "0":
            break
        else:
            print(f"{C_RED}Opção inválida!{C_RESET}")
            time.sleep(1)


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
        else:
            print(f"{C_RED}Opção inválida!{C_RESET}")
            time.sleep(1)


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
            print(
                f"{C_YELLOW}Dica: Utilize a opção do Painel Docker no menu principal para ver os logs.{C_RESET}"
            )
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
        else:
            print(f"{C_RED}Opção inválida!{C_RESET}")
            time.sleep(1)


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
    # Detecta automaticamente se o arquivo de configuração não existe na primeira execução
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
        print(f"  [ 4 ] Diagnóstico Geral do Sistema (APIs e Rede)")
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
