import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from .manager import playlist_manager


class PlaylistsCommands(commands.GroupCog, name="playlist"):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "💾"

    async def playlist_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete em tempo real que busca as playlists salvas do usuário."""
        names = await playlist_manager.list_playlists(interaction.user.id)
        return [
            app_commands.Choice(name=name, value=name)
            for name in names
            if current.lower() in name.lower()
        ][
            :25
        ]  # Limite nativo de 25 opções do Discord

    @app_commands.command(
        name="salvar",
        description="Salva a música atual ou toda a fila em uma playlist pessoal.",
    )
    @app_commands.describe(
        nome="Nome da playlist",
        busca="Nome ou link de uma música específica (opcional)",
    )
    async def salvar(
        self, interaction: discord.Interaction, nome: str, busca: str = None
    ):
        await interaction.response.defer()
        tracks_to_save = []

        if busca:
            try:
                search: wavelink.Search = await wavelink.Playable.search(busca)
                if not search:
                    return await interaction.followup.send(
                        "❌ Nenhuma música encontrada com a busca fornecida."
                    )
                track = (
                    search[0]
                    if not isinstance(search, wavelink.Playlist)
                    else search.tracks[0]
                )
                tracks_to_save.append({"url": track.uri, "title": track.title})
            except Exception as e:
                return await interaction.followup.send(
                    f"❌ Erro ao processar a busca da música: {e}"
                )
        else:
            player: wavelink.Player = interaction.guild.voice_client
            if not player or not player.current:
                return await interaction.followup.send(
                    "❌ Não há nenhuma faixa tocando para ser salva."
                )

            # Adiciona a música atual e as próximas da fila
            tracks_to_save.append(
                {"url": player.current.uri, "title": player.current.title}
            )
            for track in player.queue:
                tracks_to_save.append({"url": track.uri, "title": track.title})

        success = await playlist_manager.create_playlist(
            interaction.user.id, nome, tracks_to_save
        )
        if success:
            await interaction.followup.send(
                f"💾 Playlist **{nome}** gravada com sucesso contendo **{len(tracks_to_save)}** música(s)!"
            )
        else:
            await interaction.followup.send(
                "❌ Ocorreu um erro interno ao salvar sua playlist."
            )

    @app_commands.command(
        name="carregar",
        description="Adiciona todas as faixas de uma de suas playlists na fila atual.",
    )
    @app_commands.describe(nome="Selecione uma de suas playlists salvas")
    @app_commands.autocomplete(nome=playlist_autocomplete)
    async def carregar(self, interaction: discord.Interaction, nome: str):
        if not interaction.user.voice:
            return await interaction.response.send_message(
                "❌ Você precisa estar em um canal de voz para carregar uma playlist.",
                ephemeral=True,
            )

        await interaction.response.defer()
        tracks_data = await playlist_manager.get_playlist(interaction.user.id, nome)
        if not tracks_data:
            return await interaction.followup.send(
                f"❌ A playlist **{nome}** não foi localizada ou está vazia."
            )

        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            try:
                player = await interaction.user.voice.channel.connect(
                    cls=wavelink.Player
                )
            except Exception as e:
                return await interaction.followup.send(
                    f"❌ Falha ao se conectar ao canal de voz: {e}"
                )

        player.reply_channel = interaction.channel
        added = 0

        for item in tracks_data:
            url = item.get("url")
            if url:
                try:
                    search: wavelink.Search = await wavelink.Playable.search(url)
                    if search:
                        track = (
                            search[0]
                            if not isinstance(search, wavelink.Playlist)
                            else search.tracks[0]
                        )
                        player.queue.put(track)
                        added += 1
                except Exception:
                    continue

        await interaction.followup.send(
            f"📥 Sucesso! **{added}** faixas da playlist **{nome}** foram injetadas na fila."
        )
        if not player.playing and not player.queue.is_empty:
            await player.play(player.queue.get())

    @app_commands.command(
        name="listar",
        description="Lista todas as suas playlists pessoais salvas localmente.",
    )
    async def listar(self, interaction: discord.Interaction):
        names = await playlist_manager.list_playlists(interaction.user.id)
        if not names:
            return await interaction.response.send_message(
                "📂 Você ainda não possui playlists guardadas na sua conta.",
                ephemeral=True,
            )

        embed = discord.Embed(
            title="📂 Suas Playlists Salvas", color=discord.Color.blue()
        )
        embed.description = "\n".join([f"🔹 **{n}**" for n in names])
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="apagar",
        description="Deleta permanentemente uma playlist da sua base de dados.",
    )
    @app_commands.describe(nome="Selecione a playlist que deseja remover")
    @app_commands.autocomplete(nome=playlist_autocomplete)
    async def apagar(self, interaction: discord.Interaction, nome: str):
        success = await playlist_manager.delete_playlist(interaction.user.id, nome)
        if success:
            await interaction.response.send_message(
                f"🗑️ A playlist **{nome}** foi removida permanentemente.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"❌ Não foi possível encontrar a playlist **{nome}**.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(PlaylistsCommands(bot))
