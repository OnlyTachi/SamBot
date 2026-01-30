import aiohttp
import os
import urllib.parse

class BuscaTool:
    def __init__(self):
        self.google_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.google_cx = os.getenv("GOOGLE_SEARCH_CX")
        self.brave_key = os.getenv("BRAVE_SEARCH_API_KEY")

    async def _google_search(self, query):
        """Busca via Google Custom Search API."""
        if not self.google_key or not self.google_cx:
            raise ValueError("Chaves Google ausentes")

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'q': query,
            'key': self.google_key,
            'cx': self.google_cx,
            'num': 3 
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get('items', [])
                    if not items: return None
                    
                    text = "🔎 Resultados Google:\n"
                    for item in items:
                        text += f"- {item.get('title')}: {item.get('snippet')} ({item.get('link')})\n"
                    return text
                return None

    async def _brave_search(self, query):
        """Busca via Brave Search API."""
        if not self.brave_key:
            raise ValueError("Chave Brave ausente")

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": self.brave_key}
        params = {"q": query, "count": 3}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get('web', {}).get('results', [])
                    if not results: return None

                    text = "🦁 Resultados Brave:\n"
                    for r in results:
                        text += f"- {r.get('title')}: {r.get('description')} ({r.get('url')})\n"
                    return text
                return None

    async def _duckduckgo_fallback(self, query):
        """Busca Instantânea DuckDuckGo (Gratuito/Sem Key)."""
        # Nota: A API Instant Answer do DDG é limitada e muitas vezes retorna vazio para buscas complexas.
        # É um último recurso.
        # melhor avisar do que nada.
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json(content_type=None) 
                        abstract = data.get("AbstractText")
                        source = data.get("AbstractURL")
                        heading = data.get("Heading")
                        
                        if abstract:
                            return f"🦆 Resumo DuckDuckGo ({heading}):\n{abstract}\nFonte: {source}"
                        
                        related = data.get("RelatedTopics", [])
                        if related and len(related) > 0:
                            text = f"🦆 Tópicos DuckDuckGo sobre '{query}':\n"
                            for i, topic in enumerate(related[:3]):
                                if 'Text' in topic:
                                    text += f"- {topic['Text']}\n"
                            return text
                            
                    except Exception:
                        pass
                return None

    async def buscar_na_cascata(self, query):
        """
        Orquestrador: Google > Brave > DuckDuckGo
        """
        try:
            res = await self._google_search(query)
            if res: return res
        except Exception:
            pass 
        try:
            res = await self._brave_search(query)
            if res: return res
        except Exception:
            pass
        try:
            res = await self._duckduckgo_fallback(query)
            if res: return res
        except Exception:
            pass

        return "❌ Nenhum resultado encontrado nas fontes de busca."