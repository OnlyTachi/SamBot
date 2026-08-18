import logging
from Brain.Memory.DataManager.Connections import data_manager
from Brain.Tools.Shopping.ProductSearch import ProductSearchTool


class PriceTracker:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.Shopping.PriceTracker")
        self.search_tool = ProductSearchTool()

    async def verificar_alertas_noturnos(self) -> dict:
        """
        Varre as listas de compras de todos os usuários.
        Retorna um dicionário {user_id: [mensagens_de_alerta]} para o bot enviar no Discord.
        """
        self.logger.info("  [PriceTracker] Iniciando varredura noturna de preços...")

        usuarios = data_manager._io_read_json(
            data_manager.folders["users"] / "users.json"
        )
        alertas_para_enviar = {}

        for str_user_id, dados in usuarios.items():
            lista_compras = dados.get("shopping_list", [])

            if not lista_compras:
                continue

            alertas_usuario = []
            lista_atualizada = []
            houve_alteracao = False

            for item in lista_compras:
                nome = item.get("nome")
                preco_alvo = item.get("preco_alvo")
                notificado = item.get("notificado", False)

                if not preco_alvo or notificado:
                    lista_atualizada.append(item)
                    continue

                resultado = await self.search_tool._buscar_pelando(nome)

                if resultado:
                    import re

                    precos_encontrados = re.findall(
                        r"R\$\s*(\d+(?:\.\d{1,2})?)", resultado.replace(",", ".")
                    )

                    for preco_str in precos_encontrados:
                        try:
                            preco_atual = float(preco_str)
                            if preco_atual <= preco_alvo:
                                alertas_usuario.append(
                                    f"🚨 **Alerta de Preço!**\n"
                                    f"O item **{nome}** atingiu seu alvo! Encontrei por **R$ {preco_atual:.2f}** (Alvo: R$ {preco_alvo:.2f}).\n"
                                    f"Resumo da oferta:\n{resultado}"
                                )
                                item["notificado"] = True
                                houve_alteracao = True
                                break
                        except ValueError:
                            continue

                lista_atualizada.append(item)

            if alertas_usuario:
                alertas_para_enviar[str_user_id] = alertas_usuario

            if houve_alteracao:
                data_manager.set_user_data(
                    str_user_id, "shopping_list", lista_atualizada
                )

        self.logger.info(
            f"  [PriceTracker] Varredura finalizada. Alertas gerados para {len(alertas_para_enviar)} usuários."
        )
        return alertas_para_enviar
