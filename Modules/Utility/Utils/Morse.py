import discord
from discord import app_commands
from discord.ext import commands

DICIONARIO_MORSE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "0": "-----",
    " ": "/",
}

DICIONARIO_MORSE_INVERSO = {v: k for k, v in DICIONARIO_MORSE.items()}


class Morse(commands.GroupCog):
    morse = app_commands.Group(
        name="morse", description="Codifica e decodifica código morse"
    )

    @morse.command(name="para", description="Codifica o texto para código Morse")
    async def morse_para(self, interaction: discord.Interaction, texto: str):
        resultado = " ".join(DICIONARIO_MORSE.get(char, char) for char in texto.upper())

        if len(resultado) > 1950:
            return await interaction.response.send_message(
                "❌ O resultado ficou longo demais para o Discord!", ephemeral=True
            )

        await interaction.response.send_message(f"Texto em Morse:\n`{resultado}`")

    @morse.command(name="de", description="Decodifica código Morse para texto")
    async def morse_de(self, interaction: discord.Interaction, morse_texto: str):
        # Separa os símbolos por espaço
        simbolos = morse_texto.split(" ")

        resultado = "".join(
            DICIONARIO_MORSE_INVERSO.get(simbolo, simbolo) for simbolo in simbolos
        )

        await interaction.response.send_message(f"Morse traduzido:\n`{resultado}`")
