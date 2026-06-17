import os
import logging
import wavelink

# Configuração do Logger para o Wavelink
logger = logging.getLogger("SamBot.WavelinkCore")


async def setup_wavelink(bot):
    """
    Função para inicializar a conexão com o servidor Lavalink externo.
    """
    logger.info("Iniciando conexão com o Lavalink Externo...")

    lavalink_host = os.getenv("LAVALINK_HOST", "lavalinkv4.serenetia.com")
    lavalink_port = os.getenv("LAVALINK_PORT", "443")
    lavalink_password = os.getenv("LAVALINK_PASSWORD", "https://seretia.link/discord")

    uri = f"https://{lavalink_host}:{lavalink_port}"

    node = wavelink.Node(uri=uri, password=lavalink_password)

    try:
        await wavelink.Pool.connect(client=bot, nodes=[node])
        logger.info(
            f"Pool de conexão enviado para o Lavalink Externo ({lavalink_host}) com sucesso!"
        )
    except Exception as e:
        logger.error(f"Erro ao tentar iniciar o Pool do Wavelink: {e}")
