import re
import unicodedata
import logging
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)
from Brain.Memory.DataManager.Connections import data_manager

logger = logging.getLogger("SamBot.CalculatorTool")


class CalculatorTool:
    def __init__(self):
        self.transformations = standard_transformations + (
            implicit_multiplication_application,
            convert_xor,
        )

    def _remover_acentos(self, texto: str) -> str:
        """Remove acentuação gráfica para facilitar o parsing."""
        nfkd = unicodedata.normalize("NFKD", texto)
        return "".join([c for c in nfkd if not unicodedata.combining(c)])

    def _processar_conversao_dinamica(self, texto: str) -> str | None:
        nlp_data = data_manager.get_knowledge("nlp_data") or {}
        conversoes = nlp_data.get("unit_conversions", {})

        match = re.search(
            r"(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)\s*(?:em|para|pra)\s*([a-zA-Z]+)", texto
        )
        if not match:
            return None

        val = float(match.group(1).replace(",", "."))
        de = match.group(2).lower()
        para = match.group(3).lower()

        # Conversão de Temperatura
        if de in ["c", "celsius"] and para in ["f", "fahrenheit"]:
            return f"Conversão: {val}°C = {(val * 9/5) + 32:g}°F"
        if de in ["f", "fahrenheit"] and para in ["c", "celsius"]:
            return f"Conversão: {val}°F = {(val - 32) * 5/9:g}°C"

        # Conversão Linear via JSON
        chave_busca = f"{de}_para_{para}"
        for _, grupo in conversoes.items():
            if chave_busca in grupo:
                fator = grupo[chave_busca]
                resultado = val * fator
                return f"Conversão: {val} {de} = {resultado:g} {para}"

        return None

    async def calculate(self, query: str) -> str:
        """Resolve expressões aritméticas, algébricas e conversões."""
        texto = self._remover_acentos(query.lower())

        # 1. Tenta conversão de unidades
        conversao = self._processar_conversao_dinamica(texto)
        if conversao:
            return conversao

        # 2. Limpeza de ruídos de comando
        expressao = re.sub(
            r"(quanto e|calcule|resolva|qual o valor de|resultado de)",
            "",
            texto,
            flags=re.IGNORECASE,
        ).strip()
        expressao = expressao.replace("x", "*").replace(",", ".")

        # 3. Tratamento de porcentagem (ex: 20% de 500 -> (20/100)*500)
        expressao = re.sub(
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:de|dos|das)?\s*(\d+(?:[.,]\d+)?)",
            r"(\1 / 100) * \2",
            expressao,
        )

        try:
            # Equações com incógnitas (ex: 2x + 10 = 20)
            if "=" in expressao:
                lados = expressao.split("=")
                lhs = parse_expr(lados[0].strip(), transformations=self.transformations)
                rhs = parse_expr(lados[1].strip(), transformations=self.transformations)
                eq = sp.Eq(lhs, rhs)
                simbolos = list(eq.free_symbols)
                if simbolos:
                    solucao = sp.solve(eq, simbolos[0])
                    return (
                        f"Equação: {expressao} | Solução para {simbolos[0]}: {solucao}"
                    )

            # Expressão Matemática Pura
            parsed = parse_expr(expressao, transformations=self.transformations)
            res = parsed.evalf()
            res_formatado = int(res) if res.is_integer else round(float(res), 4)

            return f"Expressão: {expressao} | Resultado Exato: {res_formatado}"
        except Exception as e:
            logger.debug(f"Erro ao processar cálculo '{query}': {e}")
            return "Não foi possível calcular a expressão fornecida."
