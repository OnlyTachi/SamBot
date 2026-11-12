import asyncio
import os
from Core.Bot import SamBot
from Core.Logger import Logger


async def main():
    logger = Logger()
    logger.info("🔌 Iniciando Main Loop...")
    token = os.getenv("DISCORD_TOKEN")

    if not token:
        logger.critical("❌ Erro: DISCORD_TOKEN não encontrado no arquivo .env")
        return
    bot = SamBot()
    try:
        sistema_ok = await bot.run_diagnostics()

        if sistema_ok:
            logger.info("🔑 Tentando conexão com Discord Gateway...")
            await bot.start(token)
    except KeyboardInterrupt:
        logger.info("🛑 Interrupção manual detectada. Encerrando...")
        await bot.close()
    except Exception as e:
        logger.critical(f"🔥 Erro fatal na execução: {e}")
        await bot.close()
    finally:
        logger.info("👋 Bot encerrado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
