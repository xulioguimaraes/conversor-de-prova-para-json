FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias para PyMuPDF e healthcheck
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmupdf-dev \
    mupdf-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia arquivo de requisitos
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY pdf_extractor_complete.py .
COPY api.py .

# Cria diretórios necessários
RUN mkdir -p uploads extractions

# Expõe a porta da API
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
