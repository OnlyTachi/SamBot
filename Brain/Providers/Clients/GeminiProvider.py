import os
import asyncio
import random
import time
from typing import List, Optional
from Brain.Providers.BaseLLM import BaseLLMProvider

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiDriver(BaseLLMProvider):
    def __init__(self, log_instance):
        self.log = log_instance
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
        self.embed_model_cloud = "gemini-embedding-2"

        # Carrega todas as chaves do seu .env
        self.keys = self._carregar_chaves()
        self.active_model = None

        # --- CACHE DE CASTIGO (Blacklist temporária para chaves com Rate Limit) ---
        # Guarda a estrutura: { "SUA_CHAVE_API": timestamp_do_bloqueio }
        self.blacklist_chaves = {}
        self.tempo_castigo = (
            60  # Tempo em segundos que a chave fica ignorada (1 minuto)
        )

        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        self.generation_config = {
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

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

    async def initialize(self) -> bool:
        """
        Executa o diagnóstico inicial testando as chaves disponíveis.
        Retorna True se pelo menos uma chave for válida para o bot operar.
        """
        if not GEMINI_AVAILABLE:
            self.log.warning(
                "  Biblioteca google-generativeai não encontrada. Gemini offline."
            )
            return False
        if not self.keys:
            self.log.error("  Nenhuma chave API do Gemini encontrada no .env!")
            return False

        self.log.info(
            f"  [Gemini] {len(self.keys)} chaves detectadas. Iniciando diagnóstico de inicialização..."
        )

        for index, key in enumerate(self.keys):
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(self.model_name)
                await model.generate_content_async(
                    "ping", generation_config={"max_output_tokens": 1}
                )
                self.active_model = self._criar_modelo()
                self.log.info(
                    f"  [Gemini] Conectado com sucesso usando a Chave {index + 1} no setup."
                )
                return True
            except Exception as e:
                key_preview = f"{key[:6]}..."
                self.log.warning(
                    f"  [Gemini] Chave {index + 1} ({key_preview}) falhou no teste inicial: {str(e)[:50]}..."
                )
                continue

        self.log.critical(
            "  Todas as chaves do Gemini falharam nos testes de boot. Módulo em modo OFFLINE."
        )
        return False

    def _criar_modelo(self, system_instruction: Optional[str] = None):
        if not GEMINI_AVAILABLE:
            return None
        return genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=self.safety_settings,
            generation_config=self.generation_config,
            system_instruction=system_instruction,
        )

    async def generate(
        self, prompt_parts: any, system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """
        Gera a resposta do Gemini usando balanceamento de carga aleatório (Random)
        e aplicando castigo automático em milissegundos para chaves com Rate Limit.
        """
        if not GEMINI_AVAILABLE or not self.keys:
            return None

        # 1. FILTRAGEM: Remove temporariamente as chaves que estão cumprindo castigo por 429
        agora = time.time()
        chaves_disponiveis = [
            k
            for k in self.keys
            if k not in self.blacklist_chaves
            or (agora - self.blacklist_chaves[k] > self.tempo_castigo)
        ]

        # Se TODAS as chaves estiverem no castigo, limpa o castigo para não deixar o bot offline
        if not chaves_disponiveis:
            self.log.warning(
                "  [Gemini] Todas as chaves estão esgotadas no momento. Forçando limpeza do cache de castigo."
            )
            self.blacklist_chaves.clear()
            chaves_disponiveis = self.keys.copy()

        # 2. SELEÇÃO ALEATÓRIA: Embaralha a lista de chaves válidas para balancear o uso
        random.shuffle(chaves_disponiveis)

        # 3. LOOP DE TENTATIVAS ULTRA-RÁPIDO
        for key in chaves_disponiveis:
            key_preview = f"{key[:6]}..."

            try:
                genai.configure(api_key=key)
                model = self._criar_modelo(system_instruction=system_instruction)

                # Timeout estrito de 2.5 segundos para não deixar a requisição mofando
                response = await asyncio.wait_for(
                    model.generate_content_async(prompt_parts), timeout=2.5
                )

                if not response.candidates or not response.candidates[0].content.parts:
                    continue

                self.active_model = model
                return response.text

            except asyncio.TimeoutError:
                self.log.warning(
                    f"  [Gemini] Timeout na chave [{key_preview}]. Pulando em milissegundos..."
                )
                continue

            except google_exceptions.ResourceExhausted:
                # 🛑 CAPTURA O 429: Salva a assinatura da chave no cache de castigo imediatamente
                self.log.warning(
                    f"  [Gemini] Chave [{key_preview}] estourou a cota (429). Castigada por {self.tempo_castigo}s."
                )
                self.blacklist_chaves[key] = time.time()
                continue  # Pula para a próxima chave embaralhada da fila na mesma hora

            except Exception as e:
                self.log.error(f"  [Gemini] Erro crítico na chave [{key_preview}]: {e}")
                continue

        return None

    async def get_embedding(self, text: str) -> List[float]:
        # Para embeddings, vamos usar a primeira chave disponível (aleatória) para manter a velocidade
        if not GEMINI_AVAILABLE or not self.keys:
            return []
        try:
            chaves_sadias = [k for k in self.keys if k not in self.blacklist_chaves]
            key = random.choice(chaves_sadias) if chaves_sadias else self.keys[0]
            genai.configure(api_key=key)
            result = await asyncio.to_thread(
                genai.embed_content,
                model=f"models/{self.embed_model_cloud}",
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as e:
            self.log.warning(f"  [Gemini] Falha ao gerar embedding na nuvem: {e}")
            return []
