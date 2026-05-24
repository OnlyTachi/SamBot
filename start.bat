@echo off
title SamBot Manager
color 0B

:: Verifica se o Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no sistema!
    echo Por favor, instale o Python 3.11+ e marque a caixa "Add Python to PATH".
    pause
    exit /b
)

:: Executa o painel
python launcher.py
pause