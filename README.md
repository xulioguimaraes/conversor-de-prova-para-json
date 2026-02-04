# Revalida PDF Extractor API

API REST para extração de questões de PDFs do Revalida com suporte a imagens.

## 📋 Características

- ✅ Extração de questões objetivas de PDFs
- ✅ Suporte a imagens incorporadas nas questões
- ✅ Parsing de opções (A-E)
- ✅ Extração automática de gabarito
- ✅ Suporte a gabarito separado (PDF ou TXT)
- ✅ API REST com FastAPI
- ✅ Dockerizado para fácil deploy
- ✅ Persistência de dados em volumes

## 🚀 Início Rápido

### Pré-requisitos

- Docker
- Docker Compose

### Instalação e Execução

1. Clone ou copie todos os arquivos para um diretório
2. Navegue até o diretório do projeto
3. Execute:

```bash
docker-compose up -d
```

A API estará disponível em: `http://localhost:8000`

## 📡 Endpoints da API

### 1. Health Check
```http
GET /health
```

Verifica se a API está funcionando.

**Resposta:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-02T15:00:00.000000"
}
```

### 2. Extrair Questões
```http
POST /extract
Content-Type: multipart/form-data

pdf_file: arquivo.pdf
gabarito_file: gabarito.pdf (opcional)
```

Extrai questões de um PDF.

**Resposta:**
```json
{
  "success": true,
  "extraction_id": "20260202_150000",
  "metadata": {
    "extraction_id": "20260202_150000",
    "timestamp": "2026-02-02T15:00:00",
    "pdf_filename": "prova.pdf",
    "total_questions": 100,
    "questions_with_images": 45,
    "total_images": 67
  },
  "questions": [
    {
      "number": 1,
      "stem": "Texto da questão...",
      "options": {
        "A": "Opção A",
        "B": "Opção B",
        "C": "Opção C",
        "D": "Opção D",
        "E": "Opção E"
      },
      "correct_letter": "C",
      "has_image": true,
      "images": ["path/to/image.png"]
    }
  ]
}
```

### 3. Listar Extrações
```http
GET /extractions
```

Lista todas as extrações realizadas.

**Resposta:**
```json
{
  "total": 5,
  "extractions": [
    {
      "extraction_id": "20260202_150000",
      "timestamp": "2026-02-02T15:00:00",
      "pdf_filename": "prova.pdf",
      "total_questions": 100,
      "questions_with_images": 45
    }
  ]
}
```

### 4. Obter Extração Específica
```http
GET /extraction/{extraction_id}
```

Retorna dados completos de uma extração.

### 5. Listar Imagens de uma Extração
```http
GET /extraction/{extraction_id}/images
```

Lista todas as imagens extraídas.

### 6. Obter Imagem
```http
GET /extraction/{extraction_id}/image/{image_filename}
```

Retorna uma imagem específica.

### 7. Deletar Extração
```http
DELETE /extraction/{extraction_id}
```

Remove uma extração e seus arquivos.

## 🐳 Comandos Docker Úteis

### Iniciar a API
```bash
docker-compose up -d
```

### Ver logs
```bash
docker-compose logs -f
```

### Parar a API
```bash
docker-compose down
```

### Rebuild após mudanças no código
```bash
docker-compose up -d --build
```

### Acessar o container
```bash
docker exec -it revalida-extractor-api bash
```

## 📁 Estrutura de Arquivos

```
.
├── api.py                          # API FastAPI
├── pdf_extractor_complete.py       # Módulo de extração
├── requirements.txt                # Dependências Python
├── Dockerfile                      # Configuração Docker
├── docker-compose.yml              # Orquestração Docker
├── .dockerignore                   # Arquivos ignorados pelo Docker
├── uploads/                        # PDFs enviados (persistente)
└── extractions/                    # Extrações processadas (persistente)
    └── 20260202_150000/
        ├── metadata.json
        ├── prova.pdf
        └── output/
            ├── questions_20260202_150000.json
            └── images/
                ├── page_1_img_1.png
                └── ...
```

## 🔧 Configuração Avançada

### Alterar a Porta

Edite `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Muda para porta 8080
```

### Adicionar Variáveis de Ambiente

Crie um arquivo `.env`:
```env
MAX_FILE_SIZE=50000000
DEBUG=true
```

E adicione no `docker-compose.yml`:
```yaml
env_file:
  - .env
```

## 🖥️ Deploy em PC Secundário

### 1. Preparar o PC Secundário

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### 2. Transferir Arquivos

```bash
# No seu PC principal
tar -czf revalida-api.tar.gz *

# Copiar para o PC secundário (substitua os valores)
scp revalida-api.tar.gz usuario@ip-do-pc:/home/usuario/

# No PC secundário
cd /home/usuario
tar -xzf revalida-api.tar.gz
```

### 3. Executar no PC Secundário

```bash
cd /home/usuario/revalida-api
docker-compose up -d
```

### 4. Configurar Firewall (se necessário)

```bash
sudo ufw allow 8000/tcp
```

### 5. Acessar Remotamente

A API estará disponível em: `http://IP_DO_PC_SECUNDARIO:8000`

### 6. Configurar Inicialização Automática

```bash
# Criar serviço systemd
sudo nano /etc/systemd/system/revalida-api.service
```

Conteúdo:
```ini
[Unit]
Description=Revalida API
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/usuario/revalida-api
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Ativar:
```bash
sudo systemctl enable revalida-api
sudo systemctl start revalida-api
```

## 📊 Testando a API

### Usando cURL

```bash
# Health check
curl http://localhost:8000/health

# Extrair questões
curl -X POST http://localhost:8000/extract \
  -F "pdf_file=@prova.pdf" \
  -F "gabarito_file=@gabarito.pdf"

# Listar extrações
curl http://localhost:8000/extractions

# Obter extração específica
curl http://localhost:8000/extraction/20260202_150000
```

### Usando Python

```python
import requests

# Upload de PDF
url = "http://localhost:8000/extract"
files = {
    'pdf_file': open('prova.pdf', 'rb'),
    'gabarito_file': open('gabarito.pdf', 'rb')  # Opcional
}
response = requests.post(url, files=files)
print(response.json())
```

### Usando Postman

1. Crie uma nova requisição POST
2. URL: `http://localhost:8000/extract`
3. Body → form-data
4. Adicione key `pdf_file` (tipo: File) e selecione o PDF
5. Opcionalmente adicione `gabarito_file`
6. Envie a requisição

## 🐛 Troubleshooting

### Erro: "Address already in use"
```bash
# Verificar processo usando a porta 8000
sudo lsof -i :8000

# Matar processo
sudo kill -9 PID

# Ou alterar a porta no docker-compose.yml
```

### Container não inicia
```bash
# Ver logs detalhados
docker-compose logs

# Rebuild forçado
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Problemas com permissões
```bash
# Dar permissões aos diretórios
sudo chmod -R 777 uploads extractions
```

## 📝 Notas

- Os arquivos são persistidos em volumes Docker
- Imagens são salvas com nomenclatura: `page_X_img_Y.{ext}`
- O gabarito é extraído automaticamente se presente no PDF da prova
- Suporta PDFs com acentuação em português
- Questões são identificadas pelo padrão "QUESTÃO XX"

## 🔒 Segurança

Para produção, considere:

1. Adicionar autenticação (JWT, API Key)
2. Limitar tamanho de upload
3. Configurar CORS adequadamente
4. Usar HTTPS (nginx + certbot)
5. Rate limiting

## 📄 Licença

Este projeto é fornecido como está, sem garantias.
