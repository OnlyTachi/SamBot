import logging
from Brain.Memory.DataManager.Connections import data_manager
from Brain.Tools.Shopping.ProductSearch import ProductSearchTool


class ShoppingListManager:
    def __init__(self):
        self.logger = logging.getLogger("SamBot.Shopping.ShoppingList")
        self.search_tool = ProductSearchTool()

    def adicionar_item(self, user_id: str, item: str, preco_alvo: float = None) -> str:
        """Adiciona um item à lista de compras do usuário."""
        lista_atual = data_manager.get_user_data(
            user_id, "shopping_list", default_value=[]
        )

        novo_item = {"nome": item, "preco_alvo": preco_alvo, "notificado": False}

        lista_atual.append(novo_item)
        data_manager.set_user_data(user_id, "shopping_list", lista_atual)

        alvo_str = f" com preço alvo de R$ {preco_alvo:.2f}" if preco_alvo else ""
        return f"✅ **{item}** adicionado à sua lista de compras{alvo_str}."

    def remover_item(self, user_id: str, nome_item: str) -> str:
        """Remove um item da lista de compras pelo nome."""
        lista_atual = data_manager.get_user_data(
            user_id, "shopping_list", default_value=[]
        )

        lista_filtrada = [
            i for i in lista_atual if i["nome"].lower() != nome_item.lower()
        ]

        if len(lista_atual) == len(lista_filtrada):
            return f"❌ Não encontrei **{nome_item}** na sua lista."

        data_manager.set_user_data(user_id, "shopping_list", lista_filtrada)
        return f"🗑️ **{nome_item}** foi removido da lista."

    def listar_itens(self, user_id: str) -> str:
        """Mostra os itens atualmente na lista."""
        lista_atual = data_manager.get_user_data(
            user_id, "shopping_list", default_value=[]
        )

        if not lista_atual:
            return "Sua lista de compras está vazia no momento."

        report = "📝 **Sua Lista de Compras:**\n"
        for i, item in enumerate(lista_atual, 1):
            alvo_str = (
                f" (Alvo: R$ {item['preco_alvo']:.2f})"
                if item.get("preco_alvo")
                else ""
            )
            report += f"{i}. {item['nome']}{alvo_str}\n"

        return report

    async def orcar_lista(self, user_id: str) -> str:
        """Busca as melhores ofertas atuais para todos os itens da lista."""
        lista_atual = data_manager.get_user_data(
            user_id, "shopping_list", default_value=[]
        )

        if not lista_atual:
            return "Sua lista de compras está vazia. Adicione itens primeiro!"

        report = "🛒 **Orçamento da sua Lista de Compras:**\n\n"

        for item in lista_atual:
            nome = item["nome"]
            report += f"🔍 **Buscando: {nome}**\n"
            resultado_busca = await self.search_tool.search(nome)

            if "Não encontrei" in resultado_busca:
                report += "> Sem boas ofertas hoje.\n\n"
            else:
                ofertas = resultado_busca.replace(
                    f"🛒 **Relatório de Compras para: {nome}**\n\n", ""
                )
                report += ofertas + "\n"

        return report
