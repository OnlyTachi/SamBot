import aiohttp
import base64
import logging
from io import BytesIO
from PIL import Image


class VisionTool:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.VisionTool")
        self.supported_formats = [
            "image/png",
            "image/jpeg",
            "image/webp",
            "image/heic",
            "image/heif",
        ]

    async def process_attachments(self, attachments):
        """
        Processa uma lista de anexos do Discord e retorna dados formatados para o Gemini.
        Retorna uma lista de partes de conteúdo (dicts com mime_type e data).
        """
        image_parts = []

        async with aiohttp.ClientSession() as session:
            for attachment in attachments:
                if not any(
                    attachment.content_type.startswith(fmt) for fmt in ["image/"]
                ):
                    continue  # Pula arquivos que não são imagem

                self.logger.info(
                    f"Processando imagem: {attachment.filename} ({attachment.content_type})"
                )

                try:
                    async with session.get(attachment.url) as resp:
                        if resp.status != 200:
                            self.logger.error(f"Falha ao baixar imagem: {resp.status}")
                            continue

                        data = await resp.read()

                        # Opcional: Validar/Redimensionar com PIL se necessário para economizar tokens
                        # Mas o Gemini 1.5 Pro/Flash lida bem com imagens grandes nativamente.

                        # Formato nativo esperado pela lib google-generativeai
                        image_part = {
                            "mime_type": attachment.content_type,
                            "data": data,
                        }
                        image_parts.append(image_part)

                except Exception as e:
                    self.logger.error(
                        f"Erro ao processar imagem {attachment.filename}: {e}"
                    )

        return image_parts

    def is_image_message(self, message):
        """Verifica rapidamente se uma mensagem tem anexos de imagem."""
        if not message.attachments:
            return False
        return any(
            att.content_type and att.content_type.startswith("image/")
            for att in message.attachments
        )
