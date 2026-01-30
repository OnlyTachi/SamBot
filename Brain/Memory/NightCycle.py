import logging
from datetime import datetime
from ..Providers.LLMFactory import LLMFactory
from .VectorStore import vector_store
from Brain.Memory.DataManager import data_manager

class NightCycle:
    """
    Gerencia a rotina de manutenção noturna do robô.
    Responsável por consolidar logs do dia em memórias de longo prazo.
    """
    def __init__(self):
        self.logger = logging.getLogger("SamBot.NightCycle")
        self.llm_factory = LLMFactory.get_instance()
        
    async def run_maintenance(self, chat_logs: list):
            """
            Executa a rotina de organização de memória.
            Processa os logs, extrai fatos e os indexa no banco vetorial.
            """
            self.logger.info("🌙 Iniciando ciclo noturno...")
            
            if not chat_logs:
                self.logger.info("💤 Nenhuma atividade recente para processar.")
                return

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
                self.logger.info(f"⏳ Sumarizando {len(chat_logs)} interações (Cascata: Phi-3.5 > Qwen)...")
                
                fatos_extraidos = await self.llm_factory.generate_summary(prompt_resumo)
                
                if not fatos_extraidos or "Erro:" in fatos_extraidos:
                    self.logger.error("🚫 Falha ao gerar resumo noturno: Provedores offline.")
                    return

                self.logger.info("✨ Fatos extraídos com sucesso:\n" + fatos_extraidos)

                linhas = fatos_extraidos.strip().split("\n") 
                fatos_filtrados = []

                for linha in linhas:
                    if ":" in linha and any(char.isdigit() for char in linha.split(':')[0]):
                        try:
                            partes = linha.split(":", 1)
                            user_id = "".join(filter(str.isdigit, partes[0]))
                            tags = partes[1].strip()

                            if user_id and tags:
                                data_manager.save_music_preference(user_id, tags)
                                self.logger.info(f"💾 Preferência musical salva para o usuário {user_id}: {tags}")
                        except Exception as parse_error:
                            self.logger.warning(f"⚠️ Erro ao processar linha de fato: {linha} | Erro: {parse_error}")
                            continue
                    else:
                        fatos_filtrados.append(linha)
                
                texto_final_fatos = "\n".join(fatos_filtrados).strip()
                
                if len(texto_final_fatos) > 15:
                    vector_store.add_memory(
                        collection_name="resumos_diarios", 
                        text=texto_final_fatos, 
                        metadata={
                            "date": datetime.now().strftime("%Y-%m-%d"), 
                            "type": "night_summary",
                            "context_length": len(chat_logs)
                        }
                    )
                    self.logger.info("💾 Memória de longo prazo atualizada no banco vetorial.")
                else:
                    self.logger.info("🗑️ Resumo muito curto ou irrelevante. Descartando indexação.")
                
            except Exception as e:
                self.logger.error(f"❌ Erro crítico no ciclo noturno: {e}")

            self.logger.info("☀️ Ciclo de manutenção finalizado.")