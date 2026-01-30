import discord

class HistoricoManager:
    async def get_formatted_history(self, message: discord.Message, bot_user: discord.User, limit=10):
        """Lê e formata o histórico do canal para a IA entender o contexto."""
        history_data = []
        
        async for msg in message.channel.history(limit=limit, before=message):
            if not msg.content: continue
            
            author_name = "SamBot" if msg.author == bot_user else "User"
            clean_content = msg.content.replace("\n", " ")[:300] 
            history_data.append(f"{author_name}: {clean_content}")
            
        history_data.reverse() 
        
        return "\n".join(history_data)