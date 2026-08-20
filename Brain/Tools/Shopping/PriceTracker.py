import json
import logging
import re
from Brain.Memory.DataManager.Connections import data_manager
from Brain.Tools.Shopping.ProductSearch import ProductSearchTool


class PriceTracker:

    def __init__(self):
        self.logger = logging.getLogger("SamBot.Shopping.PriceTracker")
        self.search_tool = ProductSearchTool()

    def _obter_todos_usuarios(self) -> dict:
        """Busca todos os usuários e seus metadados diretamente da tabela 'users' no SQLite

        ou via DataManager / Knowledge.
        """
        usuarios = {}
        try:
            if hasattr(data_manager, "db") and data_manager.db:
                rows = data_manager.db.execute_query(
                    "SELECT user_id, data FROM users", fetchall=True
                )
                if rows:
                    for user_id, raw_data in rows:
                        if raw_data:
                            try:
                                usuarios[str(user_id)] = (
                                    json.loads(raw_data)
                                    if isinstance(raw_data, str)
                                    else raw_data
                                )
                            except Exception as json_err:
                                self.logger.warning(
                                    f"Erro ao decodificar JSON do usuário {user_id}: {json_err}"
                                )
                                usuarios[str(user_id)] = {}
                return usuarios

            knowledge_users = data_manager.get_knowledge("users")
            if isinstance(knowledge_users, dict):
                return knowledge_users

        except Exception as e:
            self.logger.error(f"Erro ao carregar usuários do banco de dados: {e}")

        return usuarios

    async def verificar_alertas_noturnos(self) -> dict:
        """Varre as listas de compras de todos os usuários cadastrados no banco.

        Retorna um dicionário {user_id: [mensagens_de_alerta]} para envio no
        Discord.
        """
        self.logger.info("Iniciando varredura noturna de preços...")
        usuarios = self._obter_todos_usuarios()
        alertas_para_enviar = {}

        for str_user_id, dados in usuarios.items():
            lista_compras = dados.get("shopping_list", [])
            if not lista_compras or not isinstance(lista_compras, list):
                continue

            alertas_usuario = []
            lista_atualizada = []
            houve_alteracao = False

            for item in lista_compras:
                nome = item.get("nome")
                preco_alvo = item.get("preco_alvo")
                notificado = item.get("notificado", False)

                if not preco_alvo or notificado or not nome:
                    lista_atualizada.append(item)
                    continue

                resultado = await self.search_tool._buscar_pelando(nome)
                atingiu_alvo = False
                preco_encontrado_final = 0.0
                oferta_resumo = ""

                if isinstance(resultado, list) and resultado:
                    for oferta in resultado:
                        preco_oferta = oferta.get("preco", 0.0)
                        if 0 < preco_oferta <= float(preco_alvo):
                            atingiu_alvo = True
                            preco_encontrado_final = preco_oferta
                            oferta_resumo = f"- {oferta.get('titulo')} | **R$ {preco_oferta:.2f}** ({oferta.get('loja')})\n  Link: {oferta.get('link')}"
                            break
                elif isinstance(resultado, str) and resultado:
                    precos_encontrados = re.findall(
                        r"R\$\s*(\d+(?:\.\d{1,2})?)", resultado.replace(",", ".")
                    )
                    for preco_str in precos_encontrados:
                        try:
                            preco_atual = float(preco_str)
                            if preco_atual <= float(preco_alvo):
                                atingiu_alvo = True
                                preco_encontrado_final = preco_atual
                                oferta_resumo = resultado
                                break
                        except ValueError:
                            continue

                if atingiu_alvo:
                    alertas_usuario.append(
                        f"  **Alerta de Preço!**\n"
                        f"O item **{nome}** atingiu seu alvo! Encontrei por **R$ {preco_encontrado_final:.2f}** (Alvo: R$ {float(preco_alvo):.2f}).\n"
                        f"Resumo da oferta:\n{oferta_resumo}"
                    )
                    item["notificado"] = True
                    houve_alteracao = True

                lista_atualizada.append(item)

            if alertas_usuario:
                alertas_para_enviar[str_user_id] = alertas_usuario

            if houve_alteracao:
                data_manager.set_user_data(
                    str_user_id, "shopping_list", lista_atualizada
                )

        self.logger.info(
            f"Varredura finalizada. Alertas gerados para {len(alertas_para_enviar)} usuários."
        )
        return alertas_para_enviar
