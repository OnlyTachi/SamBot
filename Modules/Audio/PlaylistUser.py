import discord
from discord.ext import commands
from discord import app_commands
import wavelink

# Importando o gerenciador de playlists e utilitários locais
from ._PlaylistManager import playlist_manager
from ._utils import parse_duration


class PlaylistsUser(commands.Cog):
    def __init__(self, bot):
        """Gerenciamento de playlists pessoais dos utilizadores."""
        self.bot = bot
        self.emoji = "📁"

    @commands.hybrid_group(
        name="playlist", description="Comandos para gerir as suas playlists pessoais."
    )
    async def playlist(self, ctx: commands.Context):
        """Comando base para playlists."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @playlist.command(
        name="salvar", description="Guarda a fila atual ou uma música específica."
    )
    @app_commands.describe(
        nome="Nome da playlist", busca="Música específica para guardar (opcional)"
    )
    async def salvar(self, ctx: commands.Context, nome: str, busca: str = None):
        """Guarda músicas no seu banco de dados pessoal."""
        tracks_to_save = []

        if busca:
            # Salvar uma música específica via pesquisa
            results = await wavelink.Playable.search(busca)
            if not results:
                return await ctx.send("❌ Não encontrei a música para guardar.")
            tracks_to_save = [results[0]]
        else:
            # Salvar a fila atual (Música atual + Fila)
            vc: wavelink.Player = ctx.guild.voice_client
            if not vc or (not vc.current and vc.queue.is_empty):
                return await ctx.send("❌ Não há nada a tocar ou na fila para guardar.")

            if vc.current:
                tracks_to_save.append(vc.current)
            tracks_to_save.extend(list(vc.queue))

        # O manager trata de converter os objetos Wavelink em dicionários JSON
        success = await playlist_manager.create_playlist(
            ctx.author.id, nome, tracks_to_save
        )
        if success:
            await ctx.send(
                f"✅ Playlist **{nome}** guardada com **{len(tracks_to_save)}** músicas!"
            )
        else:
            await ctx.send("❌ Erro ao guardar a playlist.")

    @playlist.command(
        name="carregar", description="Adiciona uma das suas playlists à fila."
    )
    @app_commands.describe(nome="Nome da playlist")
    async def carregar(self, ctx: commands.Context, nome: str):
        """Lê a sua playlist guardada e adiciona ao player atual."""
        if not ctx.author.voice:
            return await ctx.send("❌ Precisas de estar num canal de voz.")

        tracks_data = await playlist_manager.get_playlist(ctx.author.id, nome)
        if not tracks_data:
            return await ctx.send(f"❌ Playlist **{nome}** não encontrada.")

        if not ctx.guild.voice_client:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(
                cls=wavelink.Player
            )
        else:
            vc: wavelink.Player = ctx.guild.voice_client

        await ctx.defer()
        added = 0
        for item in tracks_data:
            try:
                # Busca a música pela URL guardada para garantir compatibilidade
                res = await wavelink.Playable.search(item["url"])
                if res:
                    await vc.queue.put_wait(res[0])
                    added += 1
            except:
                continue

        await ctx.send(
            f"✅ **{added}** músicas da playlist **{nome}** adicionadas à fila."
        )
        if not vc.playing and not vc.queue.is_empty:
            await vc.play(vc.queue.get())

    @playlist.command(name="listar", description="Lista todas as suas playlists.")
    async def listar(self, ctx: commands.Context):
        """Exibe os nomes de todas as suas playlists criadas."""
        names = await playlist_manager.list_playlists(ctx.author.id)
        if not names:
            return await ctx.send("📭 Ainda não tens nenhuma playlist guardada.")

        embed = discord.Embed(title="📂 As Tuas Playlists", color=discord.Color.blue())
        embed.description = "\n".join([f"• {n}" for n in names])
        await ctx.send(embed=embed)

    @playlist.command(name="apagar", description="Remove uma playlist permanentemente.")
    @app_commands.describe(nome="Nome da playlist")
    async def apagar(self, ctx: commands.Context, nome: str):
        """Exclui uma playlist do banco de dados."""
        success = await playlist_manager.delete_playlist(ctx.author.id, nome)
        if success:
            await ctx.send(f"🗑️ Playlist **{nome}** removida com sucesso.")
        else:
            await ctx.send(f"❌ Playlist **{nome}** não encontrada.")

    @playlist.command(
        name="info", description="Mostra as músicas dentro de uma playlist."
    )
    @app_commands.describe(nome="Nome da playlist")
    async def info(self, ctx: commands.Context, nome: str):
        """Lista os títulos das músicas guardadas numa playlist específica."""
        tracks = await playlist_manager.get_playlist(ctx.author.id, nome)
        if not tracks:
            return await ctx.send("❌ Playlist não encontrada.")

        embed = discord.Embed(
            title=f"📝 Conteúdo: {nome}", color=discord.Color.light_grey()
        )
        content = ""
        for i, t in enumerate(tracks[:20]):
            content += f"`{i+1}.` {t['title'][:50]}\n"

        if len(tracks) > 20:
            content += f"\n*... e mais {len(tracks) - 20} músicas.*"

        embed.description = content or "Playlist vazia."
        embed.set_footer(text=f"Total: {len(tracks)} músicas")
        await ctx.send(embed=embed)

    @playlist.command(name="renomear", description="Altera o nome de uma playlist.")
    @app_commands.describe(antigo="Nome atual", novo="Novo nome")
    async def renomear(self, ctx: commands.Context, antigo: str, novo: str):
        """Troca o nome de uma playlist existente."""
        tracks = await playlist_manager.get_playlist(ctx.author.id, antigo)
        if not tracks:
            return await ctx.send(f"❌ Playlist **{antigo}** não encontrada.")

        # O manager cria a nova com os mesmos dados e apaga a antiga
        await playlist_manager.create_playlist(ctx.author.id, novo, tracks)
        await playlist_manager.delete_playlist(ctx.author.id, antigo)

        await ctx.send(f"✅ Playlist renomeada de **{antigo}** para **{novo}**.")


async def setup(bot):
    await bot.add_cog(PlaylistsUser(bot))
