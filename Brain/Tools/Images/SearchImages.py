import requests
import os
import logging

class ImageSearchTool:
    def __init__(self):
        self.pixabay_key = os.getenv('PIXABAY_API_KEY')

    def buscar_pixabay(self, query):
        """Busca imagens gratuitas no Pixabay."""
        if not self.pixabay_key:
            logging.warning("Chave do Pixabay não configurada.")
            return None

        try:
            url = f"https://pixabay.com/api/?key={self.pixabay_key}&q={query}&per_page=3&lang=pt"
            res = requests.get(url, timeout=10)
            data = res.json()
            
            if data.get('hits'):
                return data['hits'][0]['largeImageURL']
        except Exception as e:
            logging.error(f"Erro ao buscar no Pixabay: {e}")
        
        return None

    def obter_imagem(self, query):
        """
        Função principal que busca a imagem.
        :param query: O termo da busca (ex: 'gato de botas')
        """
        link = self.buscar_pixabay(query)
        
        return link