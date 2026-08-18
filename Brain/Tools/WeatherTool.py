import aiohttp
import re
from Brain.Memory.DataManager.Connections import data_manager
from Brain.Core.NetworkManager import NetworkManager


class WeatherTool:
    def __init__(self):
        self.geo_url = "https://nominatim.openstreetmap.org/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"

        self.termos_clima = [
            "chuva",
            "graus",
            "previsão",
            "calor",
            "frio",
            "vento",
            "clima",
            "tempo em",
            "chover",
            "ensolarado",
            "nublado",
            "temperatura",
        ]
        # Contexto Temporario

    def _tem_contexto_climatico(self, query: str) -> bool:
        """Verifica se a query realmente se refere a clima/meteorologia."""
        query_lower = query.lower()

        if any(termo in query_lower for termo in self.termos_clima):
            return True

        if "tempo" in query_lower:
            falsos_positivos = r"tempo\s+(médio|para|de\s+(ir|chegar|marchar|andar|correr|fazer|jogar|assistir|demora))"
            if re.search(falsos_positivos, query_lower):
                return False
            return True  # Ex: "como está o tempo?"

        return False

    def _extrair_localizacao(self, query: str) -> str | None:
        """Extrai a localização usando o state_mapping do nlp_data.json."""
        texto = query.lower().strip()
        nlp_data = data_manager.get_knowledge("nlp_data") or {}
        weather_intent = nlp_data.get("intents", {}).get("weather", {})
        state_map = weather_intent.get("state_mapping", {})
        stopwords = weather_intent.get("stopwords", [])

        palavras = texto.split()
        palavras_filtradas = [p for p in palavras if p not in stopwords]
        local_limpo = " ".join(palavras_filtradas).strip()

        if local_limpo in state_map:
            return state_map[local_limpo]

        for sigla, estado_extenso in state_map.items():
            if re.search(rf"\b{sigla}\b", texto):
                return estado_extenso

        return local_limpo if local_limpo else None

    async def get_weather(self, city_query: str):
        """Busca o clima para uma cidade/estado."""

        if not self._tem_contexto_climatico(city_query):
            return None

        try:
            local_busca = self._extrair_localizacao(city_query)
            if not local_busca:
                return None  # Early Return: Sem localização válida

            session = NetworkManager.get_aio_session()

            params = {
                "q": local_busca,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }
            headers = {"User-Agent": "SamBot/1.0"}
            async with session.get(
                self.geo_url, params=params, headers=headers
            ) as resp:
                if resp.status != 200:
                    return None
                geo_data = await resp.json()

                if not geo_data:
                    return None

                lat = geo_data[0]["lat"]
                lon = geo_data[0]["lon"]
                display_name = geo_data[0]["display_name"]

            w_params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
            }

            async with session.get(self.weather_url, params=w_params) as resp:
                if resp.status != 200:
                    return "Erro ao obter dados meteorológicos."
                w_data = await resp.json()
                curr = w_data["current"]
                daily = w_data["daily"]
                info = (
                    f"Local: {display_name}\n"
                    f"Agora: {curr['temperature_2m']}°C (Sensação: {curr['apparent_temperature']}°C)\n"
                    f"Vento: {curr['wind_speed_10m']} km/h\n"
                    f"Previsão Hoje (Max/Min): {daily['temperature_2m_max'][0]}°C / {daily['temperature_2m_min'][0]}°C\n"
                    f"Chuva Hoje (%): {daily['precipitation_probability_max'][0]}%"
                )
                return info
        except Exception as e:
            return None
