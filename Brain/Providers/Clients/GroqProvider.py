import os
from typing import List, Optional
from Brain.Providers.BaseLLM import BaseLLMProvider

try:
    from groq import AsyncGroq

    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class GroqDriver(BaseLLMProvider):
    """
    Driver específico para o Groq.
    Inclui otimização automática de histórico e poda de segurança de prompt
    para evitar erros 413 / TPM no plano gratuito.
    """

    def __init__(self, log_instance, generation_config: Optional[dict] = None):
        self.log = log_instance

        # Configurações do Groq obtidas do ambiente (.env)
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

        # Configuração de temperatura herdada ou padrão
        self.temperature = 0.7
        if generation_config and "temperature" in generation_config:
            self.temperature = generation_config["temperature"]

    async def initialize(self) -> bool:
        """Verifica se a biblioteca está disponível e se a chave API foi configurada."""
        if not GROQ_AVAILABLE:
            self.log.warning(
                "⚠️ Biblioteca 'groq' não encontrada. Camada Groq offline."
            )
            return False

        if not self.groq_key:
            self.log.warning(
                "⚠️ Nenhuma chave API do Groq encontrada no .env. Camada Groq desativada."
            )
            return False

        self.log.info(
            f"⚡ [Groq] Configurado com sucesso usando o modelo: {self.groq_model}"
        )
        return True

    async def generate(
        self, prompt_parts: any, system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """
        Gera a resposta usando a API do Groq com tratamento e poda de histórico para o plano free.
        """
        if not GROQ_AVAILABLE or not self.groq_key:
            return None

        # Normaliza o prompt para texto puro (remover imagens que o Groq possa não suportar neste modelo)
        text_only_prompt = prompt_parts
        if isinstance(prompt_parts, list):
            text_only_prompt = " ".join(
                [p if isinstance(p, str) else "[Imagem omitida]" for p in prompt_parts]
            )

        try:
            client = AsyncGroq(api_key=self.groq_key)

            # --- PODA DE SEGURANÇA PARA O GROQ (Evita Erro 413 / TPM) ---
            # Se o prompt do sistema ultrapassar ~3.500 palavras, otimiza o histórico recente
            sys_inst_filtrado = str(system_instruction) if system_instruction else ""

            if sys_inst_filtrado and len(sys_inst_filtrado.split()) > 3500:
                self.log.warning(
                    "⚡ [Groq] Prompt muito longo para o plano gratuito. Otimizando histórico..."
                )
                if "Histórico Recente:" in sys_inst_filtrado:
                    partes = sys_inst_filtrado.split("Histórico Recente:")
                    linhas_historico = partes[1].strip().split("\n")
                    historico_curto = "\n".join(linhas_historico[-4:])
                    sys_inst_filtrado = (
                        f"{partes[0]}\nHistórico Recente:\n{historico_curto}"
                    )

            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": sys_inst_filtrado})
            messages.append({"role": "user", "content": text_only_prompt})

            response = await client.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                max_tokens=1024,
                temperature=self.temperature,
            )

            return f"{response.choices[0].message.content}"

        except Exception as e:
            self.log.warning(
                f"⚠️ [Groq] Falha na execução do modelo {self.groq_model}: {e}"
            )

        return None

    async def get_embedding(self, text: str) -> List[float]:
        """
        O Groq foca em inferência rápida de texto.
        Geralmente não é usado para embeddings neste ecossistema, retornando vazio.
        """
        return []
