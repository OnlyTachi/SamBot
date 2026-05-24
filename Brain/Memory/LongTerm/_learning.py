import logging
from datetime import datetime
import discord


class AprendizadoAtivo:
    def __init__(self, llm_factory, vector_store):
        self.llm_factory = llm_factory
        self.vector_store = vector_store
        self.logger = logging.getLogger("SamBot.Aprendizado")

    async def aprender_fatos(self, message: discord.Message, clean_text: str) -> str:
        if not clean_text or not self.llm_factory or not self.vector_store:
            return None

        gatilhos = [
            "meu nome",
            "eu gosto",
            "eu amo",
            "eu odeio",
            "eu moro",
            "sou ",
            "tenho ",
            "trabalho com",
        ]
        if not any(g in clean_text.lower() for g in gatilhos):
            return None

        try:
            user_name = message.author.display_name
            system_prompt = (
                "Você é o Núcleo de Memória da SamBot. Extraia fatos PERMANENTES.\n"
                "Se for relevante, extraia APENAS o fato curto. Se for lixo/piada/temporário, responda 'IGNORE'.\n"
                "Ex: 'Eu amo pizza' -> 'Gosta de pizza'"
            )

            extracao = await self.llm_factory.generate_response(
                prompt_parts=[f"Usuário {user_name} disse: '{clean_text}'"],
                system_instruction=system_prompt,
            )

            if "IGNORE" in extracao.upper() or len(extracao.strip()) < 3:
                return None

            if hasattr(self.vector_store, "add_memory"):
                # Bug corrigido: Parâmetro collection_name definido explicitamente
                await self.vector_store.add_memory(
                    collection_name="fatos_usuario",
                    text=f"Fato sobre {user_name}: {extracao}",
                    metadata={
                        "user_id": str(message.author.id),
                        "user_name": user_name,
                        "timestamp": str(datetime.now()),
                    },
                )

            await message.add_reaction("🧠")
            return extracao
        except Exception as e:
            self.logger.error(f"❌ Erro ao aprender: {e}")
            return None
