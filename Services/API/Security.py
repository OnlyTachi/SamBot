# Services/API/Security.py
from fastapi import HTTPException, Header
from Core.ConfigLoader import AppConfig
from Brain.Memory.DataManager.Connections import data_manager


def get_expected_token() -> str:
    """Recupera o token configurado ou retorna None se não estiver definido."""
    token = AppConfig.get("api.secret_token") or AppConfig.get("API_SECRET_TOKEN")
    if not token:
        admin_secret = data_manager.get_knowledge("api_security") or {}
        token = admin_secret.get("staff_token")
    return token


def verify_bot_token(x_bot_token: str = Header(...)):
    """Valida a requisição garantindo que o token não seja nulo ou padrão."""
    token_esperado = get_expected_token()

    if not token_esperado:
        raise HTTPException(
            status_code=500,
            detail="Erro de configuração: Chave de API não definida no servidor.",
        )

    if x_bot_token != token_esperado:
        raise HTTPException(
            status_code=403,
            detail="Acesso não autorizado: Token de API inválido ou ausente.",
        )
