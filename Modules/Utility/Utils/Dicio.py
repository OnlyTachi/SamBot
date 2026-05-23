import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import xml.etree.ElementTree as ET


class Dicionario(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="dicionario",
        aliases=["dicio", "definir", "palavra"],
        description="Busca o significado, sinônimos e frases de exemplo de uma palavra!",
    )
    @app_commands.describe(palavra="A palavra que você deseja pesquisar")
    async def dicionario(self, ctx: commands.Context, *, palavra: str):
        await ctx.defer()

        palavra_formatada = palavra.lower().strip()

        # URLs das duas APIs gratuitas que vamos cruzar
        url_dicio = f"https://api.dicionario-aberto.net/word/{palavra_formatada}"
        url_sinonimos = (
            f"https://api.datamuse.com/words?rel_syn={palavra_formatada}&v=pt_wiki"
        )

        async with aiohttp.ClientSession() as session:
            try:
                # Faz as requisições em paralelo para otimizar o tempo de resposta
                async with session.get(url_dicio) as resp_dicio, session.get(
                    url_sinonimos
                ) as resp_sino:
                    if resp_dicio.status != 200:
                        return await ctx.send(
                            "❌ Não consegui acessar o dicionário no momento."
                        )

                    dados_dicio = await resp_dicio.json()
                    dados_sino = (
                        await resp_sino.json() if resp_sino.status == 200 else []
                    )
            except Exception:
                return await ctx.send(
                    "❌ Ops! Os serviços de consulta linguística estão fora do ar."
                )

        if not dados_dicio:
            return await ctx.send(
                f"❌ A palavra **{palavra}** não foi encontrada. Verifique a ortografia!"
            )

        # 1. PROCESSANDO O SIGNIFICADO (XML do Dicionário Aberto)
        xml_data = dados_dicio[0].get("xml", "")
        try:
            root = ET.fromstring(xml_data)

            # Classe gramatical
            gram_grp = root.find(".//gramGrp")
            classe = (
                f"*{gram_grp.text.strip().capitalize()}*"
                if gram_grp is not None
                else "*Definição:*"
            )

            # Definições principais
            definicoes = []
            for def_tag in root.findall(".//def"):
                texto = "".join(def_tag.itertext()).strip()
                texto_limpo = " ".join(texto.split())
                if texto_limpo:
                    definicoes.append(texto_limpo)

            descricao_significado = ""
            for i, d in enumerate(definicoes[:2], 1):
                descricao_significado += f"**{i}.** {d}\n"
        except Exception:
            descricao_significado = "Erro ao processar a estrutura do significado."
            classe = "*Definição:*"

        # 2. PROCESSANDO OS SINÔNIMOS (Datamuse)
        if dados_sino:
            lista_sino = [item["word"] for item in dados_sino[:5]]
            texto_sinonimos = ", ".join(lista_sino)
        else:
            texto_sinonimos = "Nenhum sinônimo direto encontrado."

        # 3. EXTRAINDO UMA FRASE DE EXEMPLO (Se houver no XML original)
        frase_exemplo = ""
        if (
            xml_data and root.find(".//ℹ️") is not None
        ):  # Verifica tags de uso histórico/frases
            # Algumas entradas antigas guardam exemplos em marcas específicas ou citações
            ex_tag = root.find(".//eg")
            if ex_tag is not None:
                frase_exemplo = "".join(ex_tag.itertext()).strip()

        # Montando o Embed unificado
        embed = discord.Embed(
            title=f"📖 Significado de {palavra.capitalize()}", color=0x2ECC71
        )
        embed.add_field(
            name=classe,
            value=descricao_significado or "Sem definição textual disponível.",
            inline=False,
        )
        embed.add_field(name="🔀 Sinônimos", value=texto_sinonimos, inline=False)

        if frase_exemplo:
            embed.add_field(
                name="💬 Frase de Exemplo", value=f"*{frase_exemplo}*", inline=False
            )

        embed.set_footer(
            text=f"Solicitado por {ctx.author.name} • Dicionário Aberto & Datamuse"
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Dicionario(bot))
