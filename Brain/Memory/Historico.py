import discord
from Brain.Providers.LLMFactory import LLMFactory


class HistoricoManager:
    def __init__(self):
        self.llm = LLMFactory.get_instance()

    async def get_formatted_history(
        self, message: discord.Message, bot_user: discord.User, limit=20
    ):
        """
        Lê o histórico. Se houver mais de 10 mensagens, sumariza as antigas
        para economizar tokens e manter o contexto.
        """
        raw_messages = []

        async for msg in message.channel.history(limit=limit, before=message):
            if not msg.content:
                continue

            author_name = "SamBot" if msg.author == bot_user else "User"
            clean_content = msg.content.replace("\n", " ").strip()
            if clean_content:
                raw_messages.append(f"{author_name}: {clean_content}")

        raw_messages.reverse()

        # Lógica de Compressão
        if len(raw_messages) > 10:
            to_summarize = raw_messages[:-10]
            recent_context = raw_messages[-10:]

            text_block = "\n".join(to_summarize)

            try:
                summary = await self.llm.generate_response(
                    system_prompt="Você é um otimizador de memória. Resuma a conversa anterior em 1 parágrafo conciso, mantendo nomes e tópicos chave.",
                    user_prompt=f"Conversa antiga:\n{text_block}",
                )

                # Formata: Resumo + Chat Recente
                final_history = (
                    f"[RESUMO DA CONVERSA ANTERIOR]: {summary}\n"
                    f"[MENSAGENS RECENTES]:\n" + "\n".join(recent_context)
                )
                return final_history

            except Exception as e:
                # Fallback em caso de erro na LLM
                return "\n".join(raw_messages[-10:])

        # Se for curto, retorna tudo
        return "\n".join(raw_messages)
