import datetime


def create_progress_bar(current: int, total: int, length: int = 15) -> str:
    """Gera uma barra de progresso em texto."""
    if total <= 0:
        return "🔘" + "▬" * (length - 1)
    percent = current / total
    filled = int(length * percent)
    filled = max(0, min(filled, length - 1))
    return "▬" * filled + "🔘" + "▬" * (length - filled - 1)


def parse_duration(ms: int) -> str:
    """Converte milissegundos para o formato HH:MM:SS."""
    seconds = ms // 1000
    return str(datetime.timedelta(seconds=seconds))
