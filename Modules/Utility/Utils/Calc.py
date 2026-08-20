import ast
import operator
import re
import discord
from discord.ext import commands

# Operadores matemáticos permitidos
OPERADORES_PERMITIDOS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def avaliar_ast(no):
    """Percorre recursivamente a árvore AST executando apenas nós aritméticos."""
    if isinstance(no, ast.Constant):  # Python >= 3.8
        if isinstance(no.value, (int, float)):
            return no.value
        raise ValueError("Tipo de constante não suportado.")
    elif isinstance(no, ast.BinOp):
        op_tipo = type(no.op)
        if op_tipo not in OPERADORES_PERMITIDOS:
            raise ValueError(f"Operador não suportado: {op_tipo.__name__}")
        esquerda = avaliar_ast(no.left)
        direita = avaliar_ast(no.right)

        if op_tipo is ast.Pow and (direita > 1000 or len(str(esquerda)) > 100):
            raise ValueError("Expoente excessivamente grande.")
        return OPERADORES_PERMITIDOS[op_tipo](esquerda, direita)
    elif isinstance(no, ast.UnaryOp):
        op_tipo = type(no.op)
        if op_tipo not in OPERADORES_PERMITIDOS:
            raise ValueError(f"Operador unário não suportado: {op_tipo.__name__}")
        return OPERADORES_PERMITIDOS[op_tipo](avaliar_ast(no.operand))
    else:
        raise ValueError("Expressão contém elementos não numéricos ou inválidos.")


class Calculadora(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="calc",
        description="Calcule expressões matemáticas de forma inteligente e segura!",
    )
    async def calc(self, ctx: commands.Context, expressao: str):
        expressao_limpa = expressao.strip()

        if re.search(r"/\s*0(\.0*)?($|[^0-9])", expressao_limpa):
            return await ctx.send("❌ | Divisão por zero não é permitida.")

        try:
            expr_padronizada = expressao_limpa.replace(",", ".").replace("^", "**")
            arvore = ast.parse(expr_padronizada, mode="eval")
            resultado = avaliar_ast(arvore.body)

            if isinstance(resultado, float):
                resultado = (
                    int(resultado) if resultado.is_integer() else round(resultado, 10)
                )

            resultado_formatado = str(resultado).replace(".", ",")
            await ctx.send(f"📊 **Resultado:** `{resultado_formatado}`")
        except (ZeroDivisionError, OverflowError):
            await ctx.send(
                "❌ | Erro matemático: divisão por zero ou valor fora do limite."
            )
        except Exception:
            mensagem_erro = f"❌ | Tenho certeza de que `{expressao_limpa}` não é uma conta matemática válida."
            await ctx.send(mensagem_erro)


async def setup(bot):
    await bot.add_cog(Calculadora(bot))
