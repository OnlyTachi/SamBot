import logging
import json
from Brain.Providers.LLMFactory import LLMFactory
from Brain.Tools.BuscaTools import BuscaTool
from Brain.Memory.DataManager import data_manager


class AutoConhecimento:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.AutoConhecimento")
        self.llm = LLMFactory.get_instance()
        self.busca_tool = BuscaTool()
        self.data_manager = data_manager

    def _get_identity_data(self):
        """
        Recupera os dados de identidade de forma segura via DataManager.
        Agora respeitando o encapsulamento!
        """
        try:
            return self.data_manager.get_identity()
        except Exception as e:
            self.logger.error(f"Erro ao recuperar identidade do banco: {e}")
            return {"name": "SamBot"}  # Fallback seguro

    def is_self_inquiry(self, text: str) -> bool:
        """Verifica se a pergunta é sobre a identidade da bot."""
        gatilhos = [
            "quem é você",
            "quem e voce",
            "te criou",
            "seu autor",
            "sua tecnologia",
            "como você funciona",
        ]
        return any(g in text.lower() for g in gatilhos)

    def get_identity_prompt(self):
        """Retorna o prompt base de identidade para o Agent usar."""
        identity = self._get_identity_data()
        return (
            f"Você é a {identity.get('name', 'SamBot')}. "
            f"Sua descrição: {identity.get('description')}. "
            f"Responda de forma carismática baseando-se no seu JSON de identidade."
        )

    async def apresentar(self):
        """
        Gera uma apresentação baseada exclusivamente no JSON de identidade.
        """
        identity = self._get_identity_data()
        nome = identity.get("name", "SamBot")
        desc = identity.get("description", "Sou uma bot em desenvolvimento.")

        intro = (
            f"Olá! Eu sou a **{nome}**. 🤖✨\n"
            f"*{desc}*\n\n"
            "Sou um sistema complexo e modular. O que você gostaria de saber?\n"
            "🧠 **Meu Cérebro** (IA Híbrida)\n"
            "💾 **Minha Memória** (ChromaDB)\n"
            "🔊 **Meus Ouvidos** (Lavalink)\n"
            "🔧 **Minhas Ferramentas** (Jogos, Imagens, Web...)\n\n"
            "*Experimente perguntar: 'Quem te criou?' ou 'Como você toca música?'*"
        )
        return intro

    async def refletir_e_responder(self, pergunta: str):
        """
        Responde perguntas sobre si mesma usando o identity.json como base.
        Realiza pesquisa na web se houver comparação técnica.
        """
        pergunta = pergunta.lower()
        identity = self._get_identity_data()

        # 1. Detecção de Intenção de Comparação (Gatilho para Pesquisa)
        gatilhos_pesquisa = [
            "melhor que",
            "por que usa",
            "pq usa",
            "diferença entre",
            "ao invés de",
            "alternativa",
        ]
        precisa_pesquisar = any(g in pergunta for g in gatilhos_pesquisa)

        contexto_pesquisa = ""
        if precisa_pesquisar:
            self.logger.info(
                f"AutoConhecimento: Pesquisando contexto para '{pergunta}'"
            )
            # Pesquisa genérica sobre a stack da bot para dar contexto
            query = f"{pergunta} python discord bot technology comparison"
            resultados = self.busca_tool.buscar_na_cascata(query)
            contexto_pesquisa = (
                f"\n[CONTEXTO DA WEB - USE PARA COMPARAR]:\n{resultados}\n"
            )

        # 2. Montagem do Prompt com a Identidade Dinâmica
        identity_str = json.dumps(identity, indent=2, ensure_ascii=False)
        # dia 132 tentando melhorar a clareza do prompt
        prompt_sistema = (
            f"Você é a {identity.get('name', 'SamBot')}. Responda à pergunta do usuário sobre você.\n"
            "Seja carismática, use emojis moderados e fale na primeira pessoa.\n\n"
            "=== SUA IDENTIDADE (A ÚNICA VERDADE) ===\n"
            f"{identity_str}\n"
            "========================================\n"
            f"{contexto_pesquisa}\n"
            "DIRETRIZES:\n"
            "- BASEIE-SE ESTRITAMENTE no JSON acima para dizer o que você é/usa.\n"
            "- Se o JSON diz que você usa Lavalink, NÃO diga que usa ffmpeg puro.\n"
            "- Se o usuário perguntou 'Por que X?', use o CONTEXTO DA WEB para explicar as vantagens de X,\n"
            "  mas confirme que você usa X porque está na sua identidade.\n"
            "- Se perguntarem quem é o criador, cite o campo 'author'."
        )

        # 3. Geração da Resposta
        resposta = await self.llm.generate_response(prompt_sistema, pergunta)
        return resposta

    def get_resumo_cerebro(self):
        brain = self._get_identity_data().get("brain", {})
        return f"Meu cérebro é **{brain.get('type', 'Híbrido')}**. Uso principalmente **{brain.get('layer_1')}** para pensar, mas tenho **{brain.get('layer_2')}** e memória vetorial como backup!"

    def get_resumo_audio(self):
        arch = self._get_identity_data().get("architecture", {})
        return f"Para música, eu uso o motor **{arch.get('audio_engine', 'Lavalink')}**. Isso garante áudio de alta qualidade sem travar meu pensamento."


AutoConhecimentoManager = AutoConhecimento()
