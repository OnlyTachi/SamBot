import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import datetime


def create_progress_bar(current: int, total: int, length: int = 15) -> str:
    """Gera uma barra de progresso visual em texto."""
    if total <= 0:
        return "🔘" + "▬" * (length - 1)

    percent = current / total
    filled = int(length * percent)
    filled = max(0, min(filled, length))

    bar = "▬" * filled + "🔘" + "▬" * (length - filled)
    return bar


def parse_duration(ms: int) -> str:
    """Converte milissegundos para o formato HH:MM:SS."""
    seconds = ms // 1000
    return str(datetime.timedelta(seconds=seconds))


class ExtraCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="nowplaying",
        aliases=["np", "atual"],
        description="Mostra detalhes da música atual.",
    )
    async def nowplaying(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.send(
                "❌ Não estou tocando nada no momento.", ephemeral=True
            )

        track = player.current
        posicao = player.position
        duracao = track.length

        barra = create_progress_bar(posicao, duracao, length=18)
        tempo_atual = parse_duration(posicao)
        tempo_total = parse_duration(duracao)

        embed = discord.Embed(
            title="🎵 Tocando Agora",
            description=f"**[{track.title}]({track.uri})**\n\n`{tempo_atual}` {barra} `{tempo_total}`",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=track.artwork)
        if track.author:
            embed.add_field(name="👤 Autor", value=track.author, inline=True)
        if player.queue.count > 0:
            embed.add_field(
                name="📋 Fila",
                value=f"`{player.queue.count}` músicas restantes",
                inline=True,
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="volume", aliases=["vol"], description="Ajusta o volume do bot."
    )
    @app_commands.describe(nivel="Nível do volume de 0 a 100.")
    async def volume(self, ctx: commands.Context, nivel: int):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.send(
                "❌ O bot precisa estar tocando algo para ajustar o volume.",
                ephemeral=True,
            )

        nivel = max(0, min(100, nivel))
        await player.set_volume(nivel)
        await ctx.send(f"🔊 Volume ajustado para **{nivel}%**!")

    @app_commands.command(
        name="filtro",
        description="Aplica equalizações e filtros de áudio avançados na reprodução atual.",
    )
    @app_commands.choices(
        efeito=[
            app_commands.Choice(name="Desativar Filtros", value="clear"),
            app_commands.Choice(
                name="Nightcore (Áudio Rápido e Agudo)", value="nightcore"
            ),
            app_commands.Choice(
                name="Vaporwave (Áudio Lento e Grave)", value="vaporwave"
            ),
            app_commands.Choice(name="Bassboost (Graves Fortes)", value="bassboost"),
        ]
    )
    async def filtro(self, interaction: discord.Interaction, efeito: str):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.playing:
            return await interaction.response.send_message(
                "❌ O bot precisa estar reproduzindo uma música para alterar os filtros.",
                ephemeral=True,
            )

        await interaction.response.defer()
        filters: wavelink.Filters = player.filters

        if efeito == "clear":
            filters.reset()
            await interaction.followup.send(
                "🎵 Todos os efeitos foram limpos. Áudio original restaurado!"
            )
        elif efeito == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1.0)
            await interaction.followup.send(
                "⚡ Filtro **Nightcore** aplicado com sucesso!"
            )
        elif efeito == "vaporwave":
            filters.timescale.set(pitch=0.8, speed=0.8, rate=1.0)
            await interaction.followup.send(
                "🔮 Filtro **Vaporwave** aplicado com sucesso!"
            )
        elif efeito == "bassboost":
            filters.equalizer.set(
                bands=[
                    wavelink.FilterBand(band=0, gain=0.30),
                    wavelink.FilterBand(band=1, gain=0.20),
                    wavelink.FilterBand(band=2, gain=0.10),
                ]
            )
            await interaction.followup.send(
                "🔊 Filtro **Bassboost** ativado! Graves reforçados."
            )

        await player.set_filters(filters)

    @app_commands.command(
        name="seek",
        description="Avança ou retrocede para um tempo específico da música atual.",
    )
    @app_commands.describe(
        segundos="Insira o tempo exato em segundos para onde quer pular (Ex: 90 para 1min30s)"
    )
    async def seek(self, interaction: discord.Interaction, segundos: int):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.playing:
            return await interaction.response.send_message(
                "❌ Não há nenhuma música tocando no momento.", ephemeral=True
            )

        posicao_ms = segundos * 1000
        if posicao_ms < 0 or posicao_ms > player.current.length:
            return await interaction.response.send_message(
                "❌ Tempo inválido! O valor excede a duração total da música.",
                ephemeral=True,
            )

        await player.seek(posicao_ms)
        await interaction.response.send_message(
            f"⏩ Posição da música alterada com sucesso para **{segundos} segundos**!"
        )

    @app_commands.command(
        name="remove",
        description="Remove uma música específica da fila com base em sua numeração.",
    )
    @app_commands.describe(numero="O número da música na fila (veja usando /queue)")
    async def remove(self, interaction: discord.Interaction, numero: int):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or player.queue.is_empty:
            return await interaction.response.send_message(
                "❌ A fila atual de reprodução está vazia.", ephemeral=True
            )

        index = numero - 1
        if index < 0 or index >= player.queue.count:
            return await interaction.response.send_message(
                f"❌ Posição inválida! Escolha um número entre 1 e {player.queue.count}.",
                ephemeral=True,
            )

        track = player.queue[index]
        del player.queue[index]
        await interaction.response.send_message(
            f"🗑️ A música **{track.title}** foi removida da fila."
        )

    @app_commands.command(
        name="skipto",
        description="Pula direto para uma música específica da fila, descartando as anteriores.",
    )
    @app_commands.describe(posicao="O número da música para a qual deseja saltar")
    async def skipto(self, interaction: discord.Interaction, posicao: int):
        player: wavelink.Player = interaction.guild.voice_client
        if not player or player.queue.is_empty:
            return await interaction.response.send_message(
                "❌ A fila atual está vazia.", ephemeral=True
            )

        index = posicao - 1
        if index < 0 or index >= player.queue.count:
            return await interaction.response.send_message(
                f"❌ Posição inválida! Escolha uma música válida de 1 a {player.queue.count}.",
                ephemeral=True,
            )

        for _ in range(index):
            player.queue.delete(0)

        proxima_track = player.queue.get()
        await player.play(proxima_track)
        await interaction.response.send_message(
            f"⏭️ Fila adiantada! Pulando diretamente para: **{proxima_track.title}**."
        )


async def setup(bot):
    await bot.add_cog(ExtraCommands(bot))
