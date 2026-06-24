import logging
from typing import List, Optional
from Brain.Providers.BaseLLM import BaseLLMProvider


class LLMChainOrchestrator:
    """
    Orquestrador genérico de Modelos de Linguagem (LLM).
    Gerencia uma cadeia linear de provedores com failover automático.
    Pode ser instanciado múltiplas vezes (ex: Cadeia Principal, Cadeia Auxiliar).
    """

    def __init__(self, name: str, providers: List[BaseLLMProvider], log_instance):
        """
        :param name: Nome identificador da cadeia (ex: "Principal", "Resumos")
        :param providers: Lista ordenada de drivers priorizados (ex: [Gemini, Groq, Ollama])
        :param log_instance: Instância de Logger compartilhada do sistema
        """
        self.name = name
        self.providers = providers
        self.active_providers: List[BaseLLMProvider] = []
        self.log = log_instance
        self.is_ready = False

    async def setup_chain(self):
        """
        Inicializa e diagnostica individualmente cada provedor fornecido.
        Apenas os provedores que passarem nos testes de conexão/chave entram na lista ativa.
        """
        self.active_providers = []
        self.log.info(
            f"⛓️ [Cadeia: {self.name}] Iniciando a preparação dos provedores..."
        )

        for provider in self.providers:
            try:
                if await provider.initialize():
                    self.active_providers.append(provider)
            except Exception as e:
                self.log.error(
                    f"❌ Erro crítico ao inicializar provedor {provider.__class__.__name__} na cadeia {self.name}: {e}"
                )

        self.is_ready = True
        self.log.info(
            f"✨ [Cadeia: {self.name}] Concluída! {len(self.active_providers)} de {len(self.providers)} provedores prontos para uso."
        )

    async def generate_response(
        self, prompt_parts: any, system_instruction: Optional[str] = None
    ) -> str:
        """
        Cascata Principal Dinâmica: Consome os provedores ativos na ordem estipulada.
        Se o primeiro falhar (ex: Rate Limit, rede descida), passa automaticamente para o próximo.
        """
        if not self.is_ready:
            await self.setup_chain()

        if not self.active_providers:
            return f"🤯 *[Cadeia: {self.name}] Todos os motores de IA estão offline ou desativados neste ambiente.*"

        for provider in self.active_providers:
            try:
                response = await provider.generate(prompt_parts, system_instruction)
                if response:
                    return response
            except Exception as e:
                self.log.warning(
                    f"🔄 [Cadeia: {self.name}] Falha no provedor {provider.__class__.__name__}. Acionando failover... Erro: {e}"
                )
                continue  # Avança para o próximo da cadeia

        return f"🤯 *[Cadeia: {self.name}] Meus sistemas falharam. Toda a esteira de IAs foi percorrida e nenhuma respondeu.*"

    async def get_embedding(self, text: str) -> List[float]:
        """
        Tenta gerar o embedding/vetor usando o primeiro provedor da cadeia que suporte essa função.
        Caso o provedor falhe ou não suporte, faz o failover para o próximo driver.
        """
        if not self.is_ready:
            await self.setup_chain()

        for provider in self.active_providers:
            try:
                embedding = await provider.get_embedding(text)
                if (
                    embedding
                ):  # Se retornar uma lista populada com os floats, valida sucesso
                    return embedding
            except Exception as e:
                self.log.warning(
                    f"⚠️ [Cadeia: {self.name}] Falha ao gerar embedding com {provider.__class__.__name__}: {e}"
                )
                continue

        return []

    async def check_health(self) -> bool:
        """Retorna se a cadeia possui pelo menos um provedor ativo operando."""
        if not self.is_ready:
            await self.setup_chain()
        return len(self.active_providers) > 0
