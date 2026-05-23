import time
import discord
from collections import defaultdict, deque


class SpamHandler:
    def __init__(self):
        self.user_timestamps = defaultdict(lambda: deque(maxlen=10))
        self.user_messages = defaultdict(lambda: deque(maxlen=5))

    async def analisar(self, message: discord.Message, config: dict) -> str | None:
        """
        Analisa a mensagem em busca de Flood e Repetição.
        Retorna o motivo da infração (string) ou None se estiver tudo OK.
        """
        # 1. CHECAGEM DE CANAIS PERMITIDOS (Whitelist)
        canais_permitidos = config.get("spam_whitelist", [])
        if message.channel.id in canais_permitidos:
            return None  # Canal ignorado pelo bot (ex: chat de spam, contagem, etc)

        user_id = str(message.author.id)
        agora = time.time()
        content = message.content.lower().strip()

        # 2. DEFINIÇÃO DE VARIÁVEIS DE CONFIGURAÇÃO (Com valores padrão seguros)
        max_mensagens = config.get("spam_max_msgs", 5)  # Máximo de mensagens permitidas
        janela_tempo = config.get("spam_time_window", 5.0)  # Dentro de quantos segundos
        max_repeticoes = config.get(
            "spam_max_reps", 3
        )  # Máximo de mensagens EXATAMENTE iguais seguidas

        # --- VERIFICAÇÃO 3: REPETIÇÃO EXATA (Padrão de texto) ---
        if (
            content
        ):  # Ignora mensagens vazias (ex: alguém enviando apenas um anexo/imagem)
            historico_msgs = self.user_messages[user_id]
            historico_msgs.append(content)

            # Se o usuário enviou a mesma mensagem repetidas vezes
            if len(historico_msgs) >= max_repeticoes:
                if historico_msgs.count(content) >= max_repeticoes:
                    historico_msgs.clear()  # Limpa o histórico para não aplicar 2 punições seguidas
                    return "Spam de Repetição (enviando o mesmo texto várias vezes)."

        # --- VERIFICAÇÃO 4: FLOOD (Mensagens rápidas demais) ---
        historico_tempo = self.user_timestamps[user_id]
        historico_tempo.append(agora)

        # Filtra os timestamps mantendo apenas os que ocorreram dentro da nossa "janela de tempo"
        mensagens_recentes = [t for t in historico_tempo if agora - t <= janela_tempo]

        if len(mensagens_recentes) >= max_mensagens:
            historico_tempo.clear()
            return f"Spam excessivo (Flood). Você enviou {max_mensagens} mensagens em menos de {janela_tempo}s."

        return None
