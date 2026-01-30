import aiohttp
import urllib.parse

class WeatherTool:
    def __init__(self):
        self.geo_url = "https://nominatim.openstreetmap.org/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"

    async def get_weather(self, city_query: str):
        """Busca o clima para uma cidade/estado."""
        try:
            # 1. Geocodificação (Descobrir Lat/Lon do nome da cidade)
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': city_query,
                    'format': 'json',
                    'limit': 1,
                    'addressdetails': 1
                }
                headers = {'User-Agent': 'SamBot/1.0'} # OpenStreetMap exige User-Agent
                
                async with session.get(self.geo_url, params=params, headers=headers) as resp:
                    if resp.status != 200: return None
                    geo_data = await resp.json()
                    
                    if not geo_data: return f"Não encontrei a localização '{city_query}'."
                    
                    lat = geo_data[0]['lat']
                    lon = geo_data[0]['lon']
                    display_name = geo_data[0]['display_name']

            # 2. Busca Clima (Open-Meteo)
            async with aiohttp.ClientSession() as session:
                w_params = {
                    'latitude': lat,
                    'longitude': lon,
                    'current': 'temperature_2m,apparent_temperature,weather_code,wind_speed_10m',
                    'daily': 'temperature_2m_max,temperature_2m_min,precipitation_probability_max',
                    'timezone': 'auto'
                }
                async with session.get(self.weather_url, params=w_params) as resp:
                    if resp.status != 200: return "Erro ao obter dados meteorológicos."
                    w_data = await resp.json()
                    
                    curr = w_data['current']
                    daily = w_data['daily']
                    
                    # Formata um texto técnico para a IA ler e interpretar
                    info = (
                        f"Local: {display_name}\n"
                        f"Agora: {curr['temperature_2m']}°C (Sensação: {curr['apparent_temperature']}°C)\n"
                        f"Vento: {curr['wind_speed_10m']} km/h\n"
                        f"Previsão Hoje (Max/Min): {daily['temperature_2m_max'][0]}°C / {daily['temperature_2m_min'][0]}°C\n"
                        f"Chuva Hoje (%): {daily['precipitation_probability_max'][0]}%"
                    )
                    return info

        except Exception as e:
            return f"Erro interno no WeatherTool: {e}"