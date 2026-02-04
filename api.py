"""
API FastAPI para extração de questões do Revalida
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pathlib import Path
import shutil
import tempfile
import json
import re
from datetime import datetime

from pdf_extractor_complete import RevalidaPDFExtractor, ParsedQuestion


def fix_empty_options(questions_data: List[dict]) -> List[dict]:
    """
    Corrige opções vazias extraindo-as do campo stem.
    
    Args:
        questions_data: Lista de questões em formato dict
    
    Returns:
        Lista de questões com opções corrigidas
    """
    for q in questions_data:
        # Se as opções estão vazias
        if not q['options']['A'] and not q['options']['B']:
            stem = q['stem']
            
            # Procura pelo início das opções (mais flexível)
            # Tenta vários padrões para encontrar a opção A
            first_option = (
                re.search(r'(?:^|\n)\s*A\s+(?=[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ])', stem, re.MULTILINE) or
                re.search(r'\s+A\s+', stem) or
                re.search(r'(?:^|\n)A\s', stem, re.MULTILINE)
            )
            
            if first_option:
                split_pos = first_option.start()
                stem_clean = stem[:split_pos].strip()
                options_text = stem[split_pos:].strip()
                
                # Divide o texto pelas letras das opções
                parts = re.split(r'\s+([A-E])\s+', options_text)
                
                options = {}
                current_letter = None
                
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    
                    # Se é uma letra (A-E), marca como letra atual
                    if part in ['A', 'B', 'C', 'D', 'E'] and len(part) == 1:
                        current_letter = part
                    # Se não, é o texto da opção atual
                    elif current_letter:
                        text = re.sub(r'\s+', ' ', part).strip()
                        text = re.sub(r'^\.\s*', '', text)  # Remove ponto no início
                        
                        # Limpa textos indesejados (ÁREA LIVRE, marcadores de página, etc)
                        text = re.sub(r'\s*ÁREA\s+LIVRE.*$', '', text, flags=re.IGNORECASE)
                        text = re.sub(r'\s*---\s*PAGE\s+\d+\s*---.*$', '', text, flags=re.IGNORECASE)
                        text = re.sub(r'\s*PRIMEIRA\s+EDI[ÇC][ÃA]O.*$', '', text, flags=re.IGNORECASE)
                        text = re.sub(r'\s*SEGUNDA\s+EDI[ÇC][ÃA]O.*$', '', text, flags=re.IGNORECASE)
                        text = text.strip()
                        
                        options[current_letter] = text
                        current_letter = None
                
                # Atualiza a questão
                q['stem'] = stem_clean
                q['options']['A'] = options.get('A', '')
                q['options']['B'] = options.get('B', '')
                q['options']['C'] = options.get('C', '')
                q['options']['D'] = options.get('D', '')
                q['options']['E'] = options.get('E', '')
    
    return questions_data


app = FastAPI(
    title="Revalida PDF Extractor API",
    description="API para extração de questões de PDFs do Revalida com suporte a imagens",
    version="1.0.1"  # Versão atualizada
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretório para uploads temporários
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Diretório para extrações processadas
EXTRACTIONS_DIR = Path("extractions")
EXTRACTIONS_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    """Endpoint raiz com informações da API."""
    return {
        "message": "Revalida PDF Extractor API",
        "version": "1.0.0",
        "endpoints": {
            "POST /extract": "Extrai questões de um PDF",
            "GET /extractions": "Lista todas as extrações realizadas",
            "GET /extraction/{extraction_id}": "Obtém dados de uma extração específica",
            "GET /extraction/{extraction_id}/images": "Lista imagens de uma extração",
            "GET /health": "Verifica status da API"
        }
    }


@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/extract")
async def extract_questions(
    pdf_file: UploadFile = File(..., description="Arquivo PDF da prova"),
    gabarito_file: Optional[UploadFile] = File(None, description="Arquivo PDF ou TXT do gabarito (opcional)")
):
    """
    Extrai questões de um PDF do Revalida.
    
    Args:
        pdf_file: Arquivo PDF da prova
        gabarito_file: Arquivo opcional do gabarito (PDF ou TXT)
    
    Returns:
        JSON com as questões extraídas e ID da extração
    """
    
    # Valida extensão do arquivo
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="O arquivo da prova deve ser um PDF")
    
    # Gera ID único para esta extração
    extraction_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    extraction_dir = EXTRACTIONS_DIR / extraction_id
    extraction_dir.mkdir(exist_ok=True)
    
    # Salva o PDF temporariamente
    pdf_path = extraction_dir / pdf_file.filename
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(pdf_file.file, buffer)
    
    # Processa gabarito se fornecido
    gabarito_text = None
    if gabarito_file:
        gabarito_path = extraction_dir / gabarito_file.filename
        with open(gabarito_path, "wb") as buffer:
            shutil.copyfileobj(gabarito_file.file, buffer)
        
        if gabarito_file.filename.lower().endswith('.pdf'):
            import fitz
            doc = fitz.open(gabarito_path)
            gabarito_text = ""
            for page in doc:
                gabarito_text += page.get_text()
            doc.close()
        else:
            with open(gabarito_path, 'r', encoding='utf-8') as f:
                gabarito_text = f.read()
    
    try:
        # Cria diretório de saída dentro do extraction_dir
        output_dir = extraction_dir / "output"
        
        # Extrai questões
        extractor = RevalidaPDFExtractor(str(pdf_path), str(output_dir))
        questions = extractor.extract_questions(gabarito_text)
        
        # Salva JSON
        json_filename = f"questions_{extraction_id}.json"
        extractor.save_to_json(questions, json_filename)
        
        # Prepara resposta
        questions_data = [
            {
                "number": q.number,
                "stem": q.stem,
                "options": {
                    "A": q.option_a,
                    "B": q.option_b,
                    "C": q.option_c,
                    "D": q.option_d,
                    "E": q.option_e
                },
                "correct_letter": q.correct_letter,
                "has_image": q.has_image,
                "images": q.images
            }
            for q in questions
        ]
        
        # ✨ CORREÇÃO AUTOMÁTICA: Extrai opções do stem se estiverem vazias
        questions_data = fix_empty_options(questions_data)
        
        # Salva metadados da extração
        metadata = {
            "extraction_id": extraction_id,
            "timestamp": datetime.now().isoformat(),
            "pdf_filename": pdf_file.filename,
            "gabarito_filename": gabarito_file.filename if gabarito_file else None,
            "total_questions": len(questions),
            "questions_with_images": sum(1 for q in questions if q.has_image),
            "total_images": sum(len(q.images) for q in questions)
        }
        
        with open(extraction_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "extraction_id": extraction_id,
            "metadata": metadata,
            "questions": questions_data
        }
        
    except Exception as e:
        # Remove diretório em caso de erro
        shutil.rmtree(extraction_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")


@app.get("/extractions")
async def list_extractions():
    """Lista todas as extrações realizadas."""
    extractions = []
    
    for extraction_dir in EXTRACTIONS_DIR.iterdir():
        if extraction_dir.is_dir():
            metadata_file = extraction_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    extractions.append(metadata)
    
    # Ordena por timestamp (mais recente primeiro)
    extractions.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return {
        "total": len(extractions),
        "extractions": extractions
    }


@app.get("/extraction/{extraction_id}")
async def get_extraction(extraction_id: str):
    """
    Obtém dados de uma extração específica.
    
    Args:
        extraction_id: ID da extração
    
    Returns:
        JSON com questões e metadados
    """
    extraction_dir = EXTRACTIONS_DIR / extraction_id
    
    if not extraction_dir.exists():
        raise HTTPException(status_code=404, detail="Extração não encontrada")
    
    # Carrega metadados
    metadata_file = extraction_dir / "metadata.json"
    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail="Metadados não encontrados")
    
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Carrega questões
    output_dir = extraction_dir / "output"
    json_file = output_dir / f"questions_{extraction_id}.json"
    
    if not json_file.exists():
        raise HTTPException(status_code=404, detail="Arquivo de questões não encontrado")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    return {
        "metadata": metadata,
        "questions": questions
    }


@app.get("/extraction/{extraction_id}/images")
async def list_extraction_images(extraction_id: str):
    """
    Lista todas as imagens de uma extração.
    
    Args:
        extraction_id: ID da extração
    
    Returns:
        Lista de caminhos de imagens
    """
    extraction_dir = EXTRACTIONS_DIR / extraction_id
    images_dir = extraction_dir / "output" / "images"
    
    if not images_dir.exists():
        raise HTTPException(status_code=404, detail="Diretório de imagens não encontrado")
    
    images = []
    for img_file in images_dir.iterdir():
        if img_file.is_file():
            images.append({
                "filename": img_file.name,
                "path": str(img_file),
                "size": img_file.stat().st_size
            })
    
    return {
        "extraction_id": extraction_id,
        "total_images": len(images),
        "images": images
    }


@app.get("/extraction/{extraction_id}/image/{image_filename}")
async def get_image(extraction_id: str, image_filename: str):
    """
    Retorna uma imagem específica.
    
    Args:
        extraction_id: ID da extração
        image_filename: Nome do arquivo de imagem
    
    Returns:
        Arquivo de imagem
    """
    extraction_dir = EXTRACTIONS_DIR / extraction_id
    image_path = extraction_dir / "output" / "images" / image_filename
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    
    return FileResponse(image_path)


@app.delete("/extraction/{extraction_id}")
async def delete_extraction(extraction_id: str):
    """
    Remove uma extração e todos os seus arquivos.
    
    Args:
        extraction_id: ID da extração
    
    Returns:
        Confirmação de remoção
    """
    extraction_dir = EXTRACTIONS_DIR / extraction_id
    
    if not extraction_dir.exists():
        raise HTTPException(status_code=404, detail="Extração não encontrada")
    
    shutil.rmtree(extraction_dir)
    
    return {
        "success": True,
        "message": f"Extração {extraction_id} removida com sucesso"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
