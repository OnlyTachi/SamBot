import os
import shutil
import subprocess
import time
import socket

# Cores para o terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def check_port(port):
    """Verifica se uma porta local está respondendo (útil para o Lavalink)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ask_with_help(prompt_message, help_message, default_value=None):
    """
    Faz uma pergunta ao usuário. Se ele digitar '?', exibe a ajuda.
    """
    while True:
        answer = input(prompt_message).strip()

        if answer == "?":
            print(f"\n{YELLOW}--- 💡 DICA PARA INICIANTES ---{RESET}")
            print(help_message)
            print(f"{YELLOW}-------------------------------{RESET}\n")
        elif answer == "" and default_value is not None:
            return default_value
        elif answer == "":
            print(f"{RED}❌ Por favor, digite um valor ou '?' para ajuda.{RESET}")
        else:
            return answer


def setup_wizard():
    clear_screen()
    print(f"{CYAN}╔══════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║      SAMBOT - ASSISTENTE DE CONFIG       ║{RESET}")
    print(f"{CYAN}╚══════════════════════════════════════════╝{RESET}\n")

    if os.path.exists(".env"):
        print(
            f"{GREEN}✅ Arquivo .env já existe! Pulando configuração inicial.{RESET}\n"
        )
        return

    if not os.path.exists(".env.example"):
        print(
            f"{RED}❌ Arquivo .env.example não encontrado! Não é possível gerar a base.{RESET}"
        )
        exit(1)

    print(
        f"{YELLOW}Parece que é sua primeira vez aqui! Vamos configurar o básico.{RESET}"
    )
    print(
        f"{CYAN}(Dica: Se não souber o que responder, digite ? e aperte Enter){RESET}\n"
    )

    # Textos de ajuda básicos
    help_token = "Acesse https://discord.com/developers/applications, crie um Bot, copie o Token e cole aqui."
    help_owner = "Ative o Modo Desenvolvedor no Discord, clique com botão direito no seu nome e copie o ID."
    help_prefix = "O símbolo que a bot vai ouvir. Deixe em branco para usar '+'."

    # 1. CONFIGURAÇÃO OBRIGATÓRIA
    while True:
        token = ask_with_help(f"🔑 {CYAN}DISCORD_TOKEN do bot?{RESET} ", help_token)
        owner_id = ask_with_help(
            f"👤 {CYAN}Seu ID do Discord (OWNER_ID)?{RESET} ", help_owner
        )
        prefix = ask_with_help(
            f"⌨️  {CYAN}Prefixo do bot? [{YELLOW}+{CYAN}]:{RESET} ",
            help_prefix,
            default_value="+",
        )

        print("\n📝 Revise seus dados:")
        print(
            f"Token: {YELLOW}{token[:5]}...{token[-5:] if len(token) > 10 else ''}{RESET} | Dono: {YELLOW}{owner_id}{RESET} | Prefixo: {YELLOW}{prefix}{RESET}"
        )
        if input("\nOs dados estão corretos? (S/N): ").strip().lower() == "s":
            break
        print(f"\n{RED}Vamos tentar novamente!{RESET}\n")

    # 2. MENU AVANÇADO (OPCIONAL)
    advanced_keys = {}
    print(
        f"\n{GREEN}✅ Básico configurado! A SamBot já consegue ficar online com isso.{RESET}"
    )
    print(
        f"{YELLOW}No entanto, para ela falar, buscar jogos e tocar música, você precisará de chaves API.{RESET}"
    )

    do_advanced = (
        input(
            f"\nDeseja configurar as chaves avançadas agora? (S/N) [{YELLOW}N{RESET}]: "
        )
        .strip()
        .lower()
    )

    if do_advanced == "s":
        clear_screen()
        print(
            f"{CYAN}--- MODO AVANÇADO (Deixe em branco e aperte ENTER para pular uma chave) ---{RESET}\n"
        )

        print(f"{YELLOW}🧠 INTELIGÊNCIA ARTIFICIAL{RESET}")
        advanced_keys["GEMINI_API_KEY_1"] = ask_with_help(
            "Chave do Google Gemini Studio (API_KEY_1): ",
            "Acesse https://aistudio.google.com/ e crie uma chave gratuita.",
            "",
        )

        print(f"\n{YELLOW}🎮 GAMES E LOJAS{RESET}")
        advanced_keys["STEAM_API_KEY"] = ask_with_help(
            "Steam API Key: ", "Acesse https://steamcommunity.com/dev/apikey", ""
        )
        advanced_keys["IGDB_CLIENT_ID"] = ask_with_help(
            "IGDB Client ID (Twitch): ", "Acesse https://dev.twitch.tv/console", ""
        )
        advanced_keys["IGDB_CLIENT_SECRET"] = ask_with_help(
            "IGDB Client Secret (Twitch): ",
            "O segredo gerado no console da Twitch.",
            "",
        )

        print(f"\n{YELLOW}🔍 BUSCA WEB E IMAGENS{RESET}")
        advanced_keys["GOOGLE_SEARCH_API_KEY"] = ask_with_help(
            "Google Custom Search API Key: ", "Chave do GCP para buscas.", ""
        )
        advanced_keys["GOOGLE_SEARCH_CX"] = ask_with_help(
            "Google Search Engine ID (CX): ", "O ID do seu buscador programável.", ""
        )
        advanced_keys["BRAVE_SEARCH_API_KEY"] = ask_with_help(
            "Brave Search API Key: ", "Chave da API do Brave Search.", ""
        )
        advanced_keys["PIXABAY_API_KEY"] = ask_with_help(
            "Pixabay API Key: ", "Chave para buscar imagens.", ""
        )

    # 3. GRAVAÇÃO NO ARQUIVO .ENV
    print(f"\n{GREEN}Gerando arquivo .env...{RESET}")
    with open(".env.example", "r", encoding="utf-8") as f:
        env_content = f.read()

    # Substitui os obrigatórios
    env_content = env_content.replace(
        'DISCORD_TOKEN="seu_token_aqui"', f'DISCORD_TOKEN="{token}"'
    )
    env_content = env_content.replace(
        'OWNER_ID="seu_id_do_discord"', f'OWNER_ID="{owner_id}"'
    )
    env_content = env_content.replace('BOT_PREFIX="+"', f'BOT_PREFIX="{prefix}"')

    # Substitui os avançados (se o usuário preencheu, coloca o valor. Se pulou, deixa vazio para não causar erro fantasma)
    for key, user_value in advanced_keys.items():
        if user_value:  # Se o usuário digitou algo
            # Busca a linha original no .env.example (ex: STEAM_API_KEY="sua_chave_steam") e substitui
            import re

            env_content = re.sub(rf'{key}=".*?"', f'{key}="{user_value}"', env_content)
        else:
            # Se ele pulou, limpamos o valor padrão (ex: de "sua_chave_steam" para "")
            import re

            env_content = re.sub(rf'{key}=".*?"', f'{key}=""', env_content)

    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)

    print(f"{GREEN}✅ Setup concluído com sucesso! Bem-vindo à SamBot.{RESET}\n")
    time.sleep(2)


def run_menu():
    clear_screen()
    print(f"{CYAN}╔══════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║           SAMBOT STARTUP MENU            ║{RESET}")
    print(f"{CYAN}╚══════════════════════════════════════════╝{RESET}\n")

    # 1. VERIFICAÇÃO DE STATUS
    env_exists = os.path.exists(".env")
    if env_exists:
        print(f"Status Atual: {GREEN}✅ Configurado (Bot pronto para iniciar){RESET}\n")
    else:
        print(f"Status Atual: {RED}❌ Não Configurado (Falta arquivo .env){RESET}\n")

    print("O que você deseja fazer?\n")
    print(f"  {YELLOW}[ 1 ]{RESET} 🐳 Iniciar via Docker (Recomendado)")
    print(f"  {YELLOW}[ 2 ]{RESET} 💻 Iniciar Nativamente (Apenas Python)")

    # Menus dinâmicos (mudam se já estiver configurado)
    if env_exists:
        print(f"  {YELLOW}[ 3 ]{RESET} ⚙️  Refazer Configuração (Requer confirmação)")
        print(f"  {YELLOW}[ 4 ]{RESET} 🛑 Desligar Bot no Docker (Docker Down)")
    else:
        print(f"  {YELLOW}[ 3 ]{RESET} ⚙️  Fazer Configuração Inicial")

    print(f"  {YELLOW}[ 0 ]{RESET} ❌ Sair\n")

    choice = input("Escolha uma opção: ").strip()

    if choice == "1":
        if not env_exists:
            print(
                f"\n{RED}❌ Você precisa fazer a configuração (Opção 3) antes de iniciar!{RESET}"
            )
            time.sleep(2)
            run_menu()
            return

        print(f"\n{GREEN}🐳 Iniciando os containers Docker...{RESET}")
        subprocess.run(["docker", "compose", "up", "-d", "--build"])

        print(f"\n{YELLOW}⏳ Aguardando Lavalink na porta 2333...{RESET}")
        for _ in range(40):
            if check_port(2333):
                print(
                    f"{GREEN}✅ Lavalink ONLINE! A SamBot já está rodando em segundo plano.{RESET}"
                )
                break
            print(".", end="", flush=True)
            time.sleep(2)
        else:
            print(
                f"\n{RED}⚠️ Lavalink demorou a responder, mas o Docker continua tentando subir.{RESET}"
            )

    elif choice == "2":
        if not env_exists:
            print(
                f"\n{RED}❌ Você precisa fazer a configuração (Opção 3) antes de iniciar!{RESET}"
            )
            time.sleep(2)
            run_menu()
            return

        print(f"\n{GREEN}💻 Iniciando nativamente...{RESET}")
        if not check_port(2333):
            print(
                f"{RED}⚠️  AVISO: Lavalink não detectado na porta 2333. A música pode não funcionar!{RESET}"
            )
            time.sleep(2)

        subprocess.run(
            ["python", "main.py"] if os.name == "nt" else ["python3", "main.py"]
        )

    elif choice == "3":
        # 2. TRAVA DE SEGURANÇA AQUI
        if env_exists:
            print(
                f"\n{RED}⚠️  CUIDADO: Isso vai APAGAR todas as suas chaves atuais do .env!{RESET}"
            )
            confirm = (
                input("Tem certeza absoluta que deseja refazer a configuração? (S/N): ")
                .strip()
                .lower()
            )
            if confirm == "s":
                os.remove(".env")
                setup_wizard()
            else:
                print(f"{GREEN}Operação cancelada! Suas chaves estão a salvo.{RESET}")
                time.sleep(2)
        else:
            setup_wizard()
        run_menu()

    elif choice == "4" and env_exists:
        # 3. OPÇÃO PARA DESLIGAR O BOT COM SEGURANÇA
        print(f"\n{YELLOW}🛑 Desligando a SamBot e o Lavalink no Docker...{RESET}")
        subprocess.run(["docker", "compose", "down"])
        print(f"{GREEN}✅ Bot desligado com sucesso!{RESET}")
        time.sleep(2)
        run_menu()

    elif choice == "0":
        clear_screen()
        print(f"{CYAN}Obrigado por usar a SamBot! Até logo.{RESET}")
        exit(0)
    else:
        print(f"{RED}Opção inválida!{RESET}")
        time.sleep(1)
        run_menu()


if __name__ == "__main__":
    try:
        setup_wizard()
        run_menu()
    except KeyboardInterrupt:
        print(f"\n{RED}Operação cancelada pelo usuário.{RESET}")
