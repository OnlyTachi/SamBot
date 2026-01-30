# Usa uma imagem base leve do Python 3.11
FROM python:3.11-slim

# Define variáveis de ambiente para o Python não gerar arquivos .pyc e logs imediatos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho no container
WORKDIR /app
# Instala dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    nodejs \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos e instala as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código fonte para o container
COPY . .

# Comando para iniciar o bot
CMD ["python", "main.py"]