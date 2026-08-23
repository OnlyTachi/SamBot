# Services/API/Security.py
from fastapi import HTTPException, Header
import os
from Core.ConfigLoader import AppConfig
from Brain.Memory.DataManager.Connections import data_manager


def verify_bot_token(x_bot_token: str = Header(...)):
    """
    Valida a requisição comparando com o token configurado no config.yaml,
    variável de ambiente ou no banco de dados.
    """
    token_esperado = AppConfig.get("API_SECRET_TOKEN") or os.getenv("API_SECRET_TOKEN")

    if not token_esperado:
        admin_secret = data_manager.get_knowledge("api_security")
        token_esperado = admin_secret.get("staff_token", "sambot_default_secret_token")

    if x_bot_token != token_esperado:
        raise HTTPException(
            status_code=403,
            detail="Acesso não autorizado: Token de API inválido ou ausente.",
        )
