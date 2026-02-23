from PIL import Image, ImageOps
import io
import aiohttp
import functools
import asyncio

class ImageProcessor:
    def __init__(self):
        self.ascii_chars = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

    async def get_image_bytes(self, url: str):
        """Baixa a imagem da URL."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
        return None

    def _apply_sepia(self, image_bytes):
        """Aplica filtro Sépia (CPU bound - rodar em executor)."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Cria uma camada sépia
        sepia_data = []
        width, height = img.size
        pixels = img.load()

        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                sepia_data.append((min(255, tr), min(255, tg), min(255, tb)))
        
        img.putdata(sepia_data)
        
        output = io.BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output

    def _to_ascii(self, image_bytes, new_width=100):
        """Converte imagem para arte ASCII."""
        img = Image.open(io.BytesIO(image_bytes))
        
        # Redimensionar mantendo proporção
        width, height = img.size
        ratio = height / width / 1.65
        new_height = int(new_width * ratio)
        img = img.resize((new_width, new_height))
        
        # Converter para escala de cinza
        img = img.convert("L")
        
        pixels = img.getdata()
        characters = "".join([self.ascii_chars[pixel // 25] for pixel in pixels])
        
        pixel_count = len(characters)
        ascii_image = "\n".join([characters[index:(index + new_width)] for index in range(0, pixel_count, new_width)])
        
        return ascii_image

    def _invert_colors(self, image_bytes):
        """Inverte as cores da imagem."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = ImageOps.invert(img)
        
        output = io.BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output

    async def process_effect(self, loop, effect_type, image_url):
        """Wrapper assíncrono para não travar o bot."""
        img_bytes = await self.get_image_bytes(image_url)
        if not img_bytes: return None

        if effect_type == "sepia":
            return await loop.run_in_executor(None, functools.partial(self._apply_sepia, img_bytes))
        elif effect_type == "ascii":
            return await loop.run_in_executor(None, functools.partial(self._to_ascii, img_bytes))
        elif effect_type == "invert":
            return await loop.run_in_executor(None, functools.partial(self._invert_colors, img_bytes))
            
        return None