import asyncio
import os
import random
import time
from typing import Any, List, Optional
from Brain.Providers.BaseLLM import BaseLLMProvider
from Core.ConfigLoader import AppConfig

try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    types = None
    APIError = Exception


class GeminiDriver(BaseLLMProvider):
    def __init__(self, log_instance):
        self.log = log_instance
        self.model_name = AppConfig.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        self.embed_model_cloud = "gemini-embedding-2"

        # Carrega todas as chaves configuradas
        self.keys = self._carregar_chaves()
        self.active_model = self.model_name

        # Cache de castigo (Blacklist temporária para chaves com Rate Limit)
        self.blacklist_chaves = {}
        self.tempo_castigo = 60  # 1 minuto

    def _carregar_chaves(self) -> List[str]:
        keys = []
        k_default = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if k_default:
            keys.append(k_default.strip())
        i = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if not key:
                break
            key_stripped = key.strip()
            if key_stripped not in keys:
                keys.append(key_stripped)
            i += 1
        return keys

    def _obter_config(self, system_instruction: Optional[str] = None) -> Any:
        """Gera a configuração tipada do novo SDK."""
        return types.GenerateContentConfig(
            temperature=0.8,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            system_instruction=system_instruction,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ],
        )

    async def initialize(self) -> bool:
        """Testa as chaves disponíveis no boot usando a API nova."""
        if not GEMINI_AVAILABLE:
            self.log.warning(
                "⚠️ Biblioteca google-genai não encontrada. Gemini offline."
            )
            return False
        if not self.keys:
            self.log.error("❌ Nenhuma chave API do Gemini encontrada no .env!")
            return False

        self.log.info(
            f"🔑 {len(self.keys)} chaves detectadas. Iniciando diagnóstico de inicialização..."
        )

        for index, key in enumerate(self.keys):
            try:
                client = genai.Client(api_key=key)
                # Teste rápido assíncrono de conectividade
                await client.aio.models.generate_content(
                    model=self.model_name,
                    contents="ping",
                    config=types.GenerateContentConfig(max_output_tokens=1),
                )
                self.log.info(
                    f"✅ Conectado com sucesso usando a Chave {index + 1} no setup."
                )
                return True
            except Exception as e:
                key_preview = f"{key[:6]}..."
                self.log.warning(
                    f"Chave {index + 1} ({key_preview}) falhou no teste inicial: {str(e)[:50]}..."
                )
                continue

        self.log.critical(
            "❌ Todas as chaves do Gemini falharam nos testes de boot. Módulo em modo OFFLINE."
        )
        return False

    async def generate(
        self, prompt_parts: any, system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """Gera respostas com balanceamento entre chaves e bypass de Rate Limit (429)."""
        if not GEMINI_AVAILABLE or not self.keys:
            return None

        # 1. Filtra chaves ativas fora do castigo
        agora = time.time()
        chaves_disponiveis = [
            k
            for k in self.keys
            if k not in self.blacklist_chaves
            or (agora - self.blacklist_chaves[k] > self.tempo_castigo)
        ]

        if not chaves_disponiveis:
            self.log.warning(
                "⚠️ Todas as chaves estão em cooldown. Forçando limpeza do cache de castigo."
            )
            self.blacklist_chaves.clear()
            chaves_disponiveis = self.keys.copy()

        # 2. Embaralha para balancear requisições
        random.shuffle(chaves_disponiveis)
        config = self._obter_config(system_instruction=system_instruction)

        # 3. Execução assíncrona com fallback
        for key in chaves_disponiveis:
            key_preview = f"{key[:6]}..."
            try:
                client = genai.Client(api_key=key)

                # Timeout estrito
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=self.model_name,
                        contents=prompt_parts,
                        config=config,
                    ),
                    timeout=3.0,
                )

                if not response.text:
                    continue

                return response.text

            except asyncio.TimeoutError:
                self.log.warning(
                    f"⏱️ Timeout na chave [{key_preview}]. Tentando próxima..."
                )
                continue

            except APIError as e:
                # Tratamento de Rate Limit (429 / RESOURCE_EXHAUSTED)
                if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                    self.log.warning(
                        f"🛑 Chave [{key_preview}] estourou a cota (429). Castigada por {self.tempo_castigo}s."
                    )
                    self.blacklist_chaves[key] = time.time()
                else:
                    self.log.error(f"Erro de API na chave [{key_preview}]: {e}")
                continue

            except Exception as e:
                self.log.error(f"Erro crítico na chave [{key_preview}]: {e}")
                continue

        return None

    async def get_embedding(self, text: str) -> List[float]:
        """Gera embeddings assíncronos via SDK google-genai."""
        if not GEMINI_AVAILABLE or not self.keys:
            return []
        try:
            chaves_sadias = [k for k in self.keys if k not in self.blacklist_chaves]
            key = random.choice(chaves_sadias) if chaves_sadias else self.keys[0]

            client = genai.Client(api_key=key)
            result = await client.aio.models.embed_content(
                model=self.embed_model_cloud,
                contents=text,
            )
            # Extrai o vetor retornado
            if result.embeddings and len(result.embeddings) > 0:
                return result.embeddings[0].values
            return []
        except Exception as e:
            self.log.warning(f"Falha ao gerar embedding no Gemini: {e}")
            return []
