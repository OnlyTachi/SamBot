# Brain/Memory/LongTerm/_embeddings.py
import logging
from typing import List, Optional
from chromadb.api.types import EmbeddingFunction
from fastembed import TextEmbedding

logger = logging.getLogger("SamBot.Embeddings")

try:
    import onnxruntime as ort

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    ort = None


class SmartEmbeddingFunction(EmbeddingFunction):
    """
    Motor de Embeddings.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.working_mode = "INITIALIZING"
        self.active_provider: Optional[str] = None

        self._diagnosticar_onnx_runtime()
        self._inicializar_modelo()

    def _diagnosticar_onnx_runtime(self) -> List[str]:
        """Inspeciona o ambiente para identificar acelerações suportadas."""
        if not ONNX_AVAILABLE or ort is None:
            logger.warning("Biblioteca 'onnxruntime' não detectada diretamente.")
            return []

        disponiveis = ort.get_available_providers()
        dispositivos = ort.get_device() if hasattr(ort, "get_device") else "N/A"

        logger.info(f"=== Diagnóstico ONNX Runtime ===")
        logger.info(f"Dispositivo base identificado: {dispositivos}")
        logger.info(f"Providers instalados/detectados: {', '.join(disponiveis)}")
        return disponiveis

    def _inicializar_modelo(self):
        # Ordem de prioridade: GPU Dedicada -> Aceleradores/DirectML -> CPU Pura
        provedores_prioritarios = [
            "CUDAExecutionProvider",  # NVIDIA CUDA
            "ROCMExecutionProvider",  # AMD ROCm
            "DmlExecutionProvider",  # DirectML (AMD/Intel/Windows)
            "OpenVINOExecutionProvider",  # Intel CPU/iGPU/NPU
            "CPUExecutionProvider",  # CPU Padrão Garantida
        ]

        # Filtra os que de fato existem instalados no runtime para evitar exceções desnecessárias
        providers_filtrados = provedores_prioritarios
        if ONNX_AVAILABLE and ort:
            instalados = set(ort.get_available_providers())
            providers_filtrados = [
                p for p in provedores_prioritarios if p in instalados
            ]
            if not providers_filtrados:
                providers_filtrados = ["CPUExecutionProvider"]

        try:
            self.model = TextEmbedding(
                model_name=self.model_name, providers=providers_filtrados
            )
            # Define o modo de trabalho de acordo com o provedor eleito
            if "CUDAExecutionProvider" in providers_filtrados:
                self.working_mode = "CUDA (NVIDIA GPU)"
            elif "ROCMExecutionProvider" in providers_filtrados:
                self.working_mode = "ROCm (AMD GPU)"
            elif "DmlExecutionProvider" in providers_filtrados:
                self.working_mode = "DirectML (GPU/iGPU)"
            elif "OpenVINOExecutionProvider" in providers_filtrados:
                self.working_mode = "OpenVINO (Intel Accel)"
            else:
                self.working_mode = "CPU"

            logger.info(
                f"TextEmbedding inicializado com sucesso | Modelo: {self.model_name} | Modo: {self.working_mode}"
            )
        except Exception as e:
            logger.warning(
                f"Falha ao carregar com aceleradores ({e}). Forçando CPU pura..."
            )
            try:
                self.model = TextEmbedding(
                    model_name=self.model_name, providers=["CPUExecutionProvider"]
                )
                self.working_mode = "CPU (Fallback)"
                logger.info(f"Modelo carregado em CPU puro.")
            except Exception as cpu_err:
                logger.error(
                    f"Erro crítico ao carregar modelo de embeddings: {cpu_err}"
                )
                self.model = None
                self.working_mode = "OFFLINE"

    async def get_single_embedding(self, text: str) -> List[float]:
        if not text or not self.model:
            return [0.0] * 384
        try:
            embeddings_generator = self.model.embed([text])
            vector = list(next(embeddings_generator))
            return [float(x) for x in vector]
        except Exception as e:
            logger.error(f"Erro ao inferir embedding: {e}")
            return [0.0] * 384

    def __call__(self, input: any) -> List[List[float]]:
        if not self.model:
            return [[0.0] * 384]
        texts = [input] if isinstance(input, str) else list(input)
        try:
            embeddings_generator = self.model.embed(texts)
            return [[float(x) for x in vec] for vec in embeddings_generator]
        except Exception as e:
            logger.error(f"Erro no lote do ChromaDB: {e}")
            return [[0.0] * 384 for _ in texts]
