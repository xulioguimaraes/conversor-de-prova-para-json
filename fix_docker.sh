#!/bin/bash

echo "======================================================================"
echo "SCRIPT DE CORREÇÃO - DOCKER BUILD FAILED"
echo "======================================================================"

echo ""
echo "🔧 Passo 1: Limpando cache do Docker..."
docker builder prune -af

echo ""
echo "🔧 Passo 2: Removendo containers antigos..."
docker-compose down -v

echo ""
echo "🔧 Passo 3: Removendo imagens antigas..."
docker rmi files-revalida-api 2>/dev/null || true
docker rmi $(docker images -q --filter "dangling=true") 2>/dev/null || true

echo ""
echo "🔧 Passo 4: Limpando sistema Docker..."
docker system prune -af

echo ""
echo "✅ Limpeza concluída!"
echo ""
echo "======================================================================"
echo "Agora execute:"
echo "  docker-compose build --no-cache"
echo "  docker-compose up -d"
echo "======================================================================"
