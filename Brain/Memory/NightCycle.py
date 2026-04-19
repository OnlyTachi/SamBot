import logging
import random
from datetime import datetime
from ..Providers.LLMFactory import LLMFactory
from .VectorStore import vector_store
from Brain.Memory.DataManager import data_manager


class NightCycle:
    """
    Gerencia a rotina de manutenção noturna do robô.
    Agora também orquestra a flutuação do mercado e dividendos.
    """

    def __init__(self):
        self.logger = logging.getLogger("SamBot.NightCycle")
        self.llm_factory = LLMFactory.get_instance()

    async def run_maintenance(self, chat_logs: list):
        self.logger.info("🌙 Iniciando ciclo noturno...")

        # 1. PROCESSAR DINÂMICA DO MERCADO (Ações e FIIs)
        await self._update_market_calculations()

        # 2. SUMARIZAÇÃO DE LOGS
        if chat_logs:
            await self._process_chat_summaries(chat_logs)
        else:
            self.logger.info("💤 Nenhuma atividade recente para processar.")

        self.logger.info("☀️ Ciclo de manutenção finalizado.")

    async def _update_market_calculations(self):
        """Atualiza preços dos ativos e paga dividendos de FIIs."""
        self.logger.info("📈 Atualizando cotações e processando dividendos...")

        ativos = data_manager.get_knowledge("mercado") or {}
        if not ativos:
            return

        # --- Parte A: Flutuação de Preços ---
        for ticker, info in ativos.items():
            # Volatilidade baseada no tipo e na configuração do JSON
            if info["tipo"] == "Ação":
                # Ações oscilam mais (ex: -7% a +8%)
                volatilidade = 0.08 if info.get("volatilidade") == "alta" else 0.04
            else:
                # FIIs são mais estáveis (ex: -2% a +2%)
                volatilidade = 0.02

            variacao = 1 + random.uniform(
                -volatilidade, volatilidade + 0.01
            )  # Leve viés de alta
            info["preco_atual"] = round(info["preco_atual"] * variacao, 2)

        # Salva os novos preços no mercado.json
        data_manager.save_knowledge("mercado", ativos)

        # --- Parte B: Pagamento de Dividendos ---
        users_path = data_manager.folders["users"] / "users.json"
        todos_usuarios = data_manager._io_read_json(users_path)

        for user_id, user_data in todos_usuarios.items():
            portfolio = user_data.get("portfolio", {})
            if not portfolio:
                continue

            total_dividendos_recebidos = 0
            for ticker, posse in portfolio.items():
                if ticker in ativos and ativos[ticker]["tipo"] == "FII":
                    # Paga o dividendo por cada cota possuída
                    valor_div = ativos[ticker].get("dividendo_estimado", 0)
                    total_dividendos_recebidos += valor_div * posse["quantidade"]

            if total_dividendos_recebidos > 0:
                banco_atual = user_data.get("banco", 0)
                user_data["banco"] = round(banco_atual + total_dividendos_recebidos, 2)
                self.logger.info(
                    f"💰 Dividendos: {user_id} recebeu {total_dividendos_recebidos} em conta."
                )

        data_manager._io_save_json(users_path, todos_usuarios)

    async def _process_chat_summaries(self, chat_logs):
        """Lógica original de extração de fatos e memória vetorial."""

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
                f"⏳ Sumarizando {len(chat_logs)} interações (Cascata: Phi-3.5 > Qwen)..."
            )

            fatos_extraidos = await self.llm_factory.generate_summary(prompt_resumo)

            if not fatos_extraidos or "Erro:" in fatos_extraidos:
                self.logger.error(
                    "🚫 Falha ao gerar resumo noturno: Provedores offline."
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
                    "🗑️ Resumo muito curto ou irrelevante. Descartando indexação."
                )

        except Exception as e:
            self.logger.error(f"❌ Erro crítico no ciclo noturno: {e}")
