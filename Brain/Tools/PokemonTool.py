import aiohttp
import asyncio
from typing import Dict, Any, Optional


class PokemonTool:
    """
    Ferramenta de consulta à PokéAPI integrada ao ecossistema da SamBot.
    Permite buscar informações detalhadas sobre Pokémon e itens do jogo."""

    BASE_URL = "https://pokeapi.co/api/v2"

    def __init__(self):
        self.headers = {
            "User-Agent": "SamBot/3.0 (Discord Bot, Cybersecurity/Edu Project)"
        }

    async def _fetch(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Método auxiliar interno para requisições GET assíncronas."""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(f"{self.BASE_URL}/{endpoint}") as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        return None
                    else:
                        # Log interno do bot ou tratamento de erro silencioso
                        return None
            except Exception:
                return None

    async def buscar_pokemon(self, nome_ou_id: str) -> str:
        """
        Busca dados gerais de um Pokémon (Status, Tipos, ID).
        """
        id_limpo = nome_ou_id.lower().strip()
        dados = await self._fetch(f"pokemon/{id_limpo}")

        if not dados:
            return f"❌ Pokémon '{nome_ou_id}' não foi encontrado na base de dados."

        nome = dados["name"].capitalize()
        id_poke = dados["id"]
        tipos = [t["type"]["name"].capitalize() for t in dados["types"]]
        tipos_str = " / ".join(tipos)

        # Coleta de estatísticas base
        stats = {s["stat"]["name"]: s["base_stat"] for s in dados["stats"]}

        resposta = (
            f"# 📋 Ficha de Pokémon: {nome} (Nº {id_poke})\n"
            f"**Tipo(s):** {tipos_str}\n"
            f"**Altura:** {dados['height'] / 10} m | **Peso:** {dados['weight'] / 10} kg\n\n"
            f"### 📊 Estatísticas Base:\n"
            f"* **HP:** {stats.get('hp')}\n"
            f"* **Ataque:** {stats.get('attack')}\n"
            f"* **Defesa:** {stats.get('defense')}\n"
            f"* **Ataque Especial:** {stats.get('special-attack')}\n"
            f"* **Defesa Especial:** {stats.get('special-defense')}\n"
            f"* **Velocidade:** {stats.get('speed')}\n"
        )
        return resposta

    async def buscar_item(self, nome_ou_id: str) -> str:
        """
        Busca informações sobre um item do inventário do jogo.
        """
        id_limpo = nome_ou_id.lower().replace(" ", "-").strip()
        dados = await self._fetch(f"item/{id_limpo}")

        if not dados:
            return f"❌ Item '{nome_ou_id}' não foi encontrado."

        nome = dados["name"].replace("-", " ").capitalize()
        custo = dados["cost"]

        # Filtra efeito em inglês ou primeiro disponível
        efeito = "Sem descrição disponível."
        for entry in dados.get("effect_entries", []):
            if entry["language"]["name"] == "en":
                efeito = entry["short_effect"]
                break

        resposta = (
            f"# 🎒 Item: {nome}\n"
            f"**Custo nas lojas:** {custo} PokéDollars\n"
            f"**Efeito:** {efeito}\n"
        )
        return resposta

    async def executar(self, acao: str, termo: str) -> str:
        """
        Ponto de entrada do roteador de ferramentas (JSON RPC padrão do SamBot).
        """
        if acao == "buscar_pokemon":
            return await self.buscar_pokemon(termo)
        elif acao == "buscar_item":
            return await self.buscar_item(termo)
        else:
            return "❌ Ação inválida para a ferramenta Pokémon."
