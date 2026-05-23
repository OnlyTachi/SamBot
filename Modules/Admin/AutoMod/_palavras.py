import re
import discord


class WordsHandler:
    def __init__(self):
        # Tabela de tradução para Leetspeak (transforma números/símbolos em letras)
        # Ex: @ -> a, 4 -> a, 0 -> o, 3 -> e, 1 -> i, 5 -> s, 7 -> t
        self.leetspeak_map = str.maketrans("@403157$", "aaoeisss")

    def normalizar_texto(self, texto: str) -> str:
        """
        Limpa a string para evitar burlas de filtro.
        """
        # 1. Tudo minúsculo
        texto = texto.lower()

        # 2. Substitui caracteres que imitam letras
        texto = texto.translate(self.leetspeak_map)

        # 3. Remove TUDO que não for letra ou número (Isso destrói o p.a.l.a.v.r.a)
        texto = re.sub(r"[^a-z0-9]", "", texto)

        # 4. Remove letras repetidas em sequência (Ex: bboobboccaaa vira boboca)
        # O regex (idêntico capturado) substitui a sequência pela primeira letra
        texto = re.sub(r"(.)\1+", r"\1", texto)

        return texto

    async def analisar(self, message: discord.Message, config: dict) -> str | None:
        """
        Analisa a mensagem contra a lista negra de palavras.
        """
        # 1. VERIFICA WHITELISTS DE CANAIS (Para não punir em chats de desabafo/livres)
        canais_permitidos = config.get("words_whitelist_channels", [])
        if message.channel.id in canais_permitidos:
            return None

        palavras_bloqueadas = config.get("blocked_words", [])
        if not palavras_bloqueadas:
            return None

        # Pega a mensagem original e a versão totalmente "limpa" para análise
        conteudo_original = message.content.lower()
        conteudo_normalizado = self.normalizar_texto(conteudo_original)

        for palavra in palavras_bloqueadas:
            # Normalizamos a palavra da lista negra também!
            # Se a palavra bloqueada for "carro", ela vira "caro" no normalizador.
            # Como a mensagem do usuário também foi encolhida, o match é perfeito.
            palavra_limpa = self.normalizar_texto(palavra)

            # Checa na string normalizada (Pega burlas extremas)
            if palavra_limpa in conteudo_normalizado:
                return f"Uso de palavra bloqueada ou tentativa de burla."

            # Checa na string original usando fronteiras de palavras (\b)
            # Isso impede falsos positivos (ex: proibir "cu" e acabar bloqueando a palavra "documento")
            if re.search(rf"\b{re.escape(palavra)}\b", conteudo_original):
                return f"Uso de palavra bloqueada."

        return None
