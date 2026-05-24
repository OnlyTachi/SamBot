#!/bin/bash

# Dá permissão de execução caso o usuário tenha esquecido
chmod +x "$0"

clear

# Verifica se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "\033[0;31m[ERRO] Python3 não encontrado! Instale-o com: sudo apt install python3\033[0m"
    exit 1
fi

# Executa o painel interativo
python3 launcher.py