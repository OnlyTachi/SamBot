import discord
from discord.ext import commands
from discord import app_commands
import random


class Avaliar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    FRASES_WAIFU = {
        0: "Por favor, está na hora de arrumar outra Waifu.",
        1: "Sem condições. Troque de Waifu o quanto antes se você preza pelo seu próprio juízo.",
        2: "Olha, não quero me meter, mas se eu estivesse no seu lugar... já teria escolhido outra Waifu.",
        3: "Falta um pouco mais de personalidade e conteúdo nessa sua Waifu.",
        4: "Sua Waifu não é de todo mal, sério! Ela só precisa de um empurrãozinho para ficar bem mais fascinante.",
        5: "Não fede nem cheira. Uma Waifu totalmente mediana.",
        6: "Se passasse pelo boletim, sua Waifu ganharia um belo 'está acima da média'.",
        7: "A perfeição não existe no mundo das Waifus, e sejamos honestos: conviver com alguém perfeito seria um tédio.",
        8: "Uma Waifu fantástica, que consegue se destacar em tudo que há de bom.",
        9: "Uma escolha impecável! Sua Waifu é simplesmente maravilhosa.",
        10: "Absolutamente perfeita! Mantenha essa Waifu para sempre e não mude de ideia de jeito nenhum!",
    }

    FRASES_HUSBANDO = {
        0: "Por favor, está na hora de arrumar outro Husbando.",
        1: "Sem condições. Troque de Husbando o quanto antes se você preza pelo seu próprio juízo.",
        2: "Olha, não quero me meter, mas se eu estivesse no seu lugar... já teria escolhido outro Husbando.",
        3: "Falta um pouco mais de personalidade e conteúdo nesse seu Husbando.",
        4: "Seu Husbando não é de todo mal, sério! Ele só precisa de um empurrãozinho para ficar bem mais fascinante.",
        5: "Não fede nem cheira. Um Husbando totalmente mediano.",
        6: "Se passasse pelo boletim, seu Husbando ganharia um belo 'está acima da média'.",
        7: "A perfeição não existe no mundo dos Husbandos, e sejamos honestos: conviver com alguém perfeito seria um tédio.",
        8: "Um Husbando fantástico, que consegue se destacar em tudo que há de bom.",
        9: "Uma escolha impecável! Seu Husbando é simplesmente maravilhoso.",
        10: "Absolutamente perfeito! Mantenha esse Husbando para sempre e não mude de ideia de jeito nenhum!",
    }

    FRASES_ERRO_NOME = [
        "Que tal começar aprendendo a grafia correta do meu nome?",
        "Está precisando de óculos? Dá uma olhada direito em como se escreve meu nome.",
        "Parece que alguém matou as aulas de português e não sabe ler meu nome direito.",
    ]

    FRASES_ACERTO_NOME = [
        "Eu sou o próprio sinônimo de perfeição!",
        "A perfeição em pessoa sou eu, migx!",
        "Se você abrir o dicionário na palavra 'perfeita', vai ver uma foto minha lá.",
    ]

    def gerar_avaliacao(self, nome: str, tipo: str) -> str:
        nome_limpo = nome.lower().strip()

        nomes_corretos = [
            "samira",
            "Samira",
            "sami",
            "SamBot",
            "sam",
            "sami-chan",
            "sami chan",
        ]
        nomes_errados = ["san", "samiro", "samara", "samiraa"]

        if nome_limpo in nomes_corretos:
            frase = random.choice(self.FRASES_ACERTO_NOME)
            return f"A minha nota para **{nome}** é **10/10**! {frase}"

        if nome_limpo in nomes_errados:
            frase = random.choice(self.FRASES_ERRO_NOME)
            return f"A minha nota para **{nome}** é **0/10**! {frase}"

        random.seed(nome_limpo)
        nota = random.randint(0, 10)
        random.seed()

        dicionario = self.FRASES_WAIFU if tipo == "Waifu" else self.FRASES_HUSBANDO
        frase = dicionario[nota]

        mensagem = f"A minha nota para **{nome}** é **{nota}/10**! {frase}"
        return mensagem

    avaliar_grupo = app_commands.Group(
        name="avaliar", description="Deixe-me dar uma nota para sua cara metade!"
    )

    @avaliar_grupo.command(
        name="waifu",
        description="Já que precisa de validação para amar sua Waifu, deixe-me dar uma nota!",
    )
    @app_commands.describe(nome="Quem é a sua Waifu?")
    async def slash_waifu(self, interaction: discord.Interaction, nome: str):
        resposta = self.gerar_avaliacao(nome, "Waifu")
        await interaction.response.send_message(resposta)

    @avaliar_grupo.command(
        name="husbando",
        description="Já que precisa de validação para amar seu Husbando, deixe-me dar uma nota!",
    )
    @app_commands.describe(nome="Quem é o seu Husbando?")
    async def slash_husbando(self, interaction: discord.Interaction, nome: str):
        resposta = self.gerar_avaliacao(nome, "Husbando")
        await interaction.response.send_message(resposta)

    @commands.group(name="avaliar", invoke_without_command=True)
    async def prefixo_avaliar(self, ctx: commands.Context):
        await ctx.send(
            f"❌ {ctx.author.mention}, você precisa me dizer se é waifu ou husbando! Ex: `-avaliar waifu <nome>`"
        )

    @prefixo_avaliar.command(name="waifu")
    async def prefixo_sub_waifu(self, ctx: commands.Context, *, nome: str):
        resposta = self.gerar_avaliacao(nome, "Waifu")
        await ctx.send(resposta)

    @prefixo_avaliar.command(name="husbando")
    async def prefixo_sub_husbando(self, ctx: commands.Context, *, nome: str):
        resposta = self.gerar_avaliacao(nome, "Husbando")
        await ctx.send(resposta)

    @commands.command(
        name="ratewaifu",
        aliases=["avaliarwaifu", "ratemywaifu", "avaliarminhawaifu", "notawaifu"],
        description="Já que você precisa de validação de alguém para amar a sua Waifu, então deixe-me dar uma nota para você!",
    )
    async def alias_waifu(self, ctx: commands.Context, *, nome: str):
        resposta = self.gerar_avaliacao(nome, "Waifu")
        await ctx.send(resposta)

    @commands.command(
        name="ratehusbando",
        aliases=[
            "avaliarhusbando",
            "ratemyhusbando",
            "avaliarminhahusbando",
            "notahusbando",
        ],
        description="Já que você precisa de validação de alguém para amar o seu Husbando, então deixe-me dar uma nota para você!",
    )
    async def alias_husbando(self, ctx: commands.Context, *, nome: str):
        resposta = self.gerar_avaliacao(nome, "Husbando")
        await ctx.send(resposta)


async def setup(bot):
    await bot.add_cog(Avaliar(bot))
