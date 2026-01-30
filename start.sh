#!/bin/bash

# ==========================================
# CONFIGURAÇÃO DE CORES E ESTILO
# ==========================================
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Limpa a tela
clear

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    SAMBOT DOCKER MANAGER - INICIANDO     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ==========================================
# 1. VERIFICAÇÃO DE AMBIENTE (PRÉ-CHECK)
# ==========================================
echo -e "${CYAN}════════ VERIFICAÇÃO DE SISTEMA ════════${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "Docker          : [ ${RED}NÃO INSTALADO${NC} ] (Instale o Docker Desktop/Engine)"
    exit 1
else
    echo -e "Docker          : [ ${GREEN}   OK   ${NC} ]"
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "Docker Compose  : [ ${RED}NÃO INSTALADO${NC} ]"
    exit 1
else
    echo -e "Docker Compose  : [ ${GREEN}   OK   ${NC} ]"
fi

# Check Internet
if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    echo -e "Internet        : [ ${GREEN} ONLINE ${NC} ]"
else
    echo -e "Internet        : [ ${RED}OFFLINE ${NC} ]"
fi

# Check .env Features
echo -e "\n${CYAN}════════ STATUS DAS FUNÇÕES (.env) ════════${NC}"

if [ -f ".env" ]; then
    check_key() {
        if grep -qE "^$1=[^[:space:]]+" .env; then
            printf "%-16s: [ ${GREEN}%-6s${NC} ]\n" "$2" "ON"
        else
            printf "%-16s: [ ${RED}%-6s${NC} ]\n" "$2" "OFF"
        fi
    }

    # --- CRITICO ---
    check_key "DISCORD_TOKEN" "Bot Token"

    # --- IA (GEMINI) ---
    # Verifica se pelo menos uma das chaves do Gemini está configurada
    if grep -qE "^GEMINI_API_KEY_2=[^[:space:]]+" .env || grep -qE "^GEMINI_API_KEY_3=[^[:space:]]+" .env; then
        printf "%-16s: [ ${GREEN}%-6s${NC} ]\n" "IA (Gemini)" "ON"
    else
        printf "%-16s: [ ${RED}%-6s${NC} ]\n" "IA (Gemini)" "OFF"
    fi

    # --- BUSCA (SEARCH) ---
    if grep -qE "^GOOGLE_SEARCH_API_KEY=[^[:space:]]+" .env && grep -qE "^GOOGLE_SEARCH_CX=[^[:space:]]+" .env; then
        printf "%-16s: [ ${GREEN}%-6s${NC} ]\n" "Google Search" "ON"
    else
        printf "%-16s: [ ${RED}%-6s${NC} ]\n" "Google Search" "OFF"
    fi
    check_key "BRAVE_SEARCH_API_KEY" "Brave Search"

    # --- GAMES ---
    check_key "STEAM_API_KEY" "Steam API"
    
    if grep -qE "^IGDB_CLIENT_ID=[^[:space:]]+" .env && grep -qE "^IGDB_CLIENT_SECRET=[^[:space:]]+" .env; then
        printf "%-16s: [ ${GREEN}%-6s${NC} ]\n" "IGDB (Games)" "ON"
    else
        printf "%-16s: [ ${RED}%-6s${NC} ]\n" "IGDB (Games)" "OFF"
    fi
    
    check_key "KLIPY_API_KEY" "Klipy Clips"

    # --- OUTROS ---
    check_key "YOUTUBE_PLAYLIST_ID" "YT Playlist"

else
    echo -e "${RED}[ERRO] Arquivo .env não encontrado! Crie um .env.${NC}"
fi

echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""

# ==========================================
# 2. INICIAR LAVALINK (ISOLADO)
# ==========================================
echo -e "${YELLOW}[DOCKER] Subindo container do Lavalink...${NC}"

# Tenta derrubar containers antigos para limpar memória
docker compose down --remove-orphans >/dev/null 2>&1

# Sobe APENAS o lavalink primeiro (assume que o serviço chama 'lavalink' no yaml)
docker compose up -d lavalink

if [ $? -ne 0 ]; then
    echo -e "${RED}[ERRO] Falha ao iniciar o container do Lavalink.${NC}"
    echo -e "Verifique se o nome do serviço no docker-compose.yml é 'lavalink'."
    exit 1
fi

# ==========================================
# 3. AGUARDAR LAVALINK (PING)
# ==========================================
echo -e "\n${YELLOW}[WAIT] Aguardando Lavalink iniciar (Porta 2333)...${NC}"
echo -n "   Conectando"

RETRIES=0
MAX_RETRIES=40 # 80 segundos max
LAVALINK_READY=0

while [ $RETRIES -lt $MAX_RETRIES ]; do
    # Verifica se a porta 2333 do localhost está respondendo
    (echo > /dev/tcp/localhost/2333) >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        LAVALINK_READY=1
        break
    fi
    echo -n "."
    sleep 2
    RETRIES=$((RETRIES+1))
done

echo "" # Quebra de linha

if [ $LAVALINK_READY -eq 1 ]; then
    echo -e "   └─ Status: ${GREEN}ONLINE${NC} (Pronto para música)"
else
    echo -e "   └─ Status: ${RED}TIMEOUT${NC} (O Lavalink demorou demais ou não expôs a porta 2333)"
    echo -e "              Continuando mesmo assim, mas a música pode falhar."
fi

# ==========================================
# 4. INICIAR O BOT
# ==========================================
echo -e "\n${YELLOW}[DOCKER] Iniciando o Bot (Main)...${NC}"

# Sobe o resto dos serviços (o Bot)
docker compose up -d --build

echo -e "\n${GREEN}✔ Todos os serviços foram iniciados!${NC}"
echo -e "${CYAN}Exibindo logs em tempo real (Pressione Ctrl+C para sair dos logs, o bot continuará rodando)${NC}"
echo "-----------------------------------------------------"

# ==========================================
# 5. MOSTRAR LOGS
# ==========================================
docker compose logs -f sambot