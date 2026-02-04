"""
Script de teste para a API Revalida PDF Extractor
"""

import requests
import json
from pathlib import Path

# URL base da API
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Testa o endpoint de health check."""
    print("\n" + "="*60)
    print("TEST: Health Check")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✓ Health check passou!")


def test_extract_questions(pdf_path: str, gabarito_path: str = None):
    """Testa a extração de questões."""
    print("\n" + "="*60)
    print("TEST: Extract Questions")
    print("="*60)
    
    # Verifica se o arquivo existe
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return None
    
    print(f"Enviando PDF: {pdf_path}")
    
    # Prepara arquivos para upload
    files = {
        'pdf_file': open(pdf_path, 'rb')
    }
    
    if gabarito_path:
        gabarito_file = Path(gabarito_path)
        if gabarito_file.exists():
            print(f"Enviando gabarito: {gabarito_path}")
            files['gabarito_file'] = open(gabarito_path, 'rb')
    
    # Faz requisição
    response = requests.post(f"{BASE_URL}/extract", files=files)
    
    # Fecha arquivos
    for f in files.values():
        f.close()
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Extração concluída com sucesso!")
        print(f"  ID: {data['extraction_id']}")
        print(f"  Total de questões: {data['metadata']['total_questions']}")
        print(f"  Questões com imagem: {data['metadata']['questions_with_images']}")
        print(f"  Total de imagens: {data['metadata']['total_images']}")
        
        # Mostra primeira questão como exemplo
        if data['questions']:
            q = data['questions'][0]
            print(f"\n  Exemplo - Questão {q['number']}:")
            print(f"    Enunciado: {q['stem'][:100]}...")
            print(f"    Resposta: {q['correct_letter']}")
            print(f"    Tem imagem: {q['has_image']}")
        
        return data['extraction_id']
    else:
        print(f"❌ Erro na extração: {response.text}")
        return None


def test_list_extractions():
    """Testa listagem de extrações."""
    print("\n" + "="*60)
    print("TEST: List Extractions")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/extractions")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Total de extrações: {data['total']}")
        
        if data['extractions']:
            print("\nÚltimas extrações:")
            for ext in data['extractions'][:3]:
                print(f"  - {ext['extraction_id']}: {ext['total_questions']} questões")
    else:
        print(f"❌ Erro: {response.text}")


def test_get_extraction(extraction_id: str):
    """Testa obtenção de uma extração específica."""
    print("\n" + "="*60)
    print(f"TEST: Get Extraction ({extraction_id})")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/extraction/{extraction_id}")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Extração obtida com sucesso!")
        print(f"  Timestamp: {data['metadata']['timestamp']}")
        print(f"  Total de questões: {len(data['questions'])}")
    else:
        print(f"❌ Erro: {response.text}")


def test_list_images(extraction_id: str):
    """Testa listagem de imagens."""
    print("\n" + "="*60)
    print(f"TEST: List Images ({extraction_id})")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/extraction/{extraction_id}/images")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Total de imagens: {data['total_images']}")
        
        if data['images']:
            print("\nPrimeiras imagens:")
            for img in data['images'][:3]:
                print(f"  - {img['filename']} ({img['size']} bytes)")
    else:
        print(f"❌ Erro: {response.text}")


def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("REVALIDA PDF EXTRACTOR - TESTES DA API")
    print("="*60)
    
    try:
        # 1. Health Check
        test_health_check()
        
        # 2. Lista extrações existentes
        test_list_extractions()
        
        # 3. Extrai questões (ADAPTE O CAMINHO DO PDF!)
        pdf_path = "2025_1_PV_objetiva_regular.pdf"  # MUDE PARA SEU PDF
        gabarito_path = None  # Adicione caminho do gabarito se tiver
        
        extraction_id = test_extract_questions(pdf_path, gabarito_path)
        
        if extraction_id:
            # 4. Obtém extração específica
            test_get_extraction(extraction_id)
            
            # 5. Lista imagens
            test_list_images(extraction_id)
        
        print("\n" + "="*60)
        print("✓ TODOS OS TESTES CONCLUÍDOS!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
