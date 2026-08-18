import logging
import random
from datetime import datetime
from Brain.Memory.DataManager.Connections import data_manager
from Brain.Memory.LongTerm.VectorStore import vector_store
from Brain.Providers.LLMFactory import llm_factory
from Brain.Tools.Shopping.PriceTracker import PriceTracker
from Brain.Tools.JellyfinTool import JellyfinTool


class NightCycle:
    """
    Gerencia a rotina de manutenção noturna do robô.
    Orquestra a flutuação do mercado, dividendos, expurgo de cache e sumarização de logs.
    """

    def __init__(self):
        self.logger = logging.getLogger("SamBot.NightCycle")
        self.aux_chain = llm_factory.get_default_auxiliary_chain()

    async def run_maintenance(self, chat_logs: list):
        self.logger.info("  Iniciando ciclo noturno...")

        # 1. Mercado e Dividendos
        await self._update_market_calculations()

        # 2. Alertas de Preço
        tracker = PriceTracker()
        alertas = await tracker.verificar_alertas_noturnos()

        # 3. Expurgo de Ofertas Expiradas
        try:
            self.logger.info(
                "  [NightCycle] Iniciando limpeza do cache de ofertas (Meilisearch)..."
            )
            await data_manager.purge_expired_offers()
        except Exception as e:
            self.logger.error(f"Erro ao expurgar ofertas do cache: {e}")

        # 4. Sincronização de Mídia
        try:
            jellyfin = JellyfinTool()
            await jellyfin.sync_catalog()
        except Exception as e:
            self.logger.error(f"Erro ao atualizar o cache noturno do Jellyfin: {e}")

        # 5. Resumos de Memória Vetorial
        if chat_logs:
            await self._process_chat_summaries(chat_logs)
        else:
            self.logger.info("  Nenhuma atividade recente para processar.")

        self.logger.info("  Ciclo de manutenção finalizado.")
        return alertas

    async def _process_chat_summaries(self, chat_logs):
        """Lógica de extração de fatos e atualização da memória vetorial usando a Cadeia Auxiliar."""
        logs_text = "\n".join(chat_logs[:100])

        prompt_resumo = (
            "ATUE COMO UM ANALISTA DE DADOS E MEMÓRIA.\n"
            "Analise os logs de conversa abaixo e identifique informações relevantes sobre os usuários.\n"
            "FOCO: Nomes, preferências, eventos mencionados, ID usuario, humor recorrente, gosto musical e fatos biográficos.\n"
            "REGRAS: Ignore comandos do sistema, erros técnicos ou saudações vazias.\n"
            "FORMATO: Liste os fatos em tópicos diretos.\n"
            "EXEMPLO: 123456789/nome: rock, musicas calmas, gosta de humor acido e tem 44 anos\n"
            f"LOGS DO DIA:\n{logs_text}"
        )

        try:
            self.logger.info(
                f"⏳ Sumarizando {len(chat_logs)} interações através da Cadeia Auxiliar (Failover de segundo plano)..."
            )

            if not self.aux_chain.is_ready:
                await self.aux_chain.setup_chain()

            fatos_extraidos = await self.aux_chain.generate_response(
                prompt_parts=[logs_text], system_instruction=prompt_resumo
            )

            if not fatos_extraidos or "Todos os motores de IA" in fatos_extraidos:
                self.logger.error(
                    "🚫 Falha ao gerar resumo noturno: Provedores da cadeia offline."
                )
                return

            self.logger.info("✨ Fatos extraídos com sucesso:\n" + fatos_extraidos)

            linhas = fatos_extraidos.strip().split("\n")
            fatos_filtrados = []

            for linha in linhas:
                if ":" in linha and any(char.isdigit() for char in linha.split(":")[0]):
                    try:
                        partes = linha.split(":", 1)
                        user_id = "".join(filter(str.isdigit, partes[0]))
                        tags = partes[1].strip()

                        if user_id and tags:
                            gostos_antigos = data_manager.get_user_data(
                                user_id, "music_likes", default_value=[]
                            )
                            if tags not in gostos_antigos:
                                gostos_antigos.append(tags)
                                data_manager.set_user_data(
                                    user_id, "music_likes", gostos_antigos
                                )
                                self.logger.info(
                                    f"💾 Preferência musical atualizada para {user_id}: {tags}"
                                )
                                # Adiciona à lista que irá para o banco vetorial
                                fatos_filtrados.append(linha)
                    except Exception as parse_error:
                        self.logger.warning(
                            f"⚠️ Erro ao processar linha de fato: {linha} | Erro: {parse_error}"
                        )
                        continue

            texto_final_fatos = "\n".join(fatos_filtrados).strip()

            if len(texto_final_fatos) > 15:
                await vector_store.add_memory(
                    collection_name="resumos_diarios",
                    text=texto_final_fatos,
                    metadata={
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "type": "night_summary",
                        "context_length": len(chat_logs),
                    },
                )
                self.logger.info(
                    "💾 Memória de longo prazo atualizada no banco vetorial."
                )
            else:
                self.logger.info(
                    "🗑️ Resumo muito curto ou sem novos fatos estruturados. Descartando indexação."
                )

        except Exception as e:
            self.logger.error(f"❌ Erro crítico no ciclo noturno: {e}")
