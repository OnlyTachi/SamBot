import aiohttp
import time

class CurrencyService:
    def __init__(self):
        self.api_url = "https://economia.awesomeapi.com.br/last/USD-BRL"
        self._cache_rate = None
        self._cache_time = 0
        self._cache_duration = 7200  # 2 hora de cache para evitar muitas requisições

    async def get_usd_to_brl(self):
        """Retorna a cotação atual do Dólar para Real."""
        if self._cache_rate and (time.time() - self._cache_time < self._cache_duration):
            return self._cache_rate

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        rate = float(data['USDBRL']['bid'])
                        
                        self._cache_rate = rate
                        self._cache_time = time.time()
                        return rate
        except Exception as e:
            print(f"❌ [Currency] Erro ao buscar cotação: {e}")
            
        # Fallback se a API falhar (valor aproximado seguro)
        return 6.00