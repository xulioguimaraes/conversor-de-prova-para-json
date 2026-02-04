"""
Extrator de questões do Revalida com suporte a imagens - VERSÃO CORRIGIDA
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF


@dataclass
class ParsedQuestion:
    """Representa uma questão extraída do PDF."""
    number: int
    stem: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    option_e: str
    correct_letter: str
    images: List[str]
    has_image: bool


class RevalidaPDFExtractor:
    """Extrator de questões do PDF do Revalida."""
    
    LETTERS = ["A", "B", "C", "D", "E"]
    QUESTION_HEADER_REGEX = re.compile(r'\n\s*QUEST[ÃAÀ]O\s*(\d{1,3})\s*[\s:\-]?', re.IGNORECASE)
    
    def __init__(self, pdf_path: str, output_dir: str = "extracted_questions"):
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
    def extract_text_and_images(self) -> Tuple[str, Dict[int, List[str]]]:
        """Extrai texto completo e imagens do PDF."""
        doc = fitz.open(self.pdf_path)
        full_text = ""
        page_images = {}
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            full_text += f"\n--- PAGE {page_num + 1} ---\n{text}"
            
            # Extrai imagens
            image_list = page.get_images()
            page_image_paths = []
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                image_path = self.images_dir / image_filename
                
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                page_image_paths.append(str(image_path))
            
            if page_image_paths:
                page_images[page_num + 1] = page_image_paths
        
        doc.close()
        return full_text, page_images
    
    def normalize_text(self, text: str) -> str:
        """Normaliza texto removendo espaços extras."""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def clean_option_text(self, text: str) -> str:
        """Limpa texto da opção removendo marcadores indesejados."""
        # Remove marcadores de página
        text = re.sub(r'---\s*PAGE\s+\d+\s*---', '', text, flags=re.IGNORECASE)
        # Remove "ÁREA LIVRE"
        text = re.sub(r'ÃREA\s+LIVRE', '', text, flags=re.IGNORECASE)
        text = re.sub(r'ÁREA\s+LIVRE', '', text, flags=re.IGNORECASE)
        # Remove cabeçalhos
        text = re.sub(r'PRIMEIRA\s+EDI[ÇC][ÃA]O', '', text, flags=re.IGNORECASE)
        text = re.sub(r'SEGUNDA\s+EDI[ÇC][ÃA]O', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Revalida\s*\d+/\d+', '', text, flags=re.IGNORECASE)
        # Normaliza
        text = self.normalize_text(text)
        return text
    
    def parse_question_block(self, block: str) -> Dict[str, str]:
        """
        Analisa um bloco de questão e extrai enunciado e opções.
        ✅ VERSÃO CORRIGIDA - Captura opções no formato "A texto"
        """
        block = block.replace('\r\n', '\n').replace('\r', '\n')
        options = {letter: "" for letter in self.LETTERS}
        stem = ""
        
        # Remove cabeçalho da questão
        block = re.sub(r'^\s*QUEST[ÃAÀ]O\s*\d{1,3}\s*[\s:\-]?\s*', '', block, flags=re.IGNORECASE)
        
        # 🔑 CORREÇÃO PRINCIPAL: Procura por opções no formato "\nLETRA espaço"
        # Exemplo: "\nA Texto da opção A"
        first_option_match = re.search(r'\n([A-E])\s+', block)
        
        if first_option_match:
            # Divide stem das opções
            stem = block[:first_option_match.start()].strip()
            options_section = block[first_option_match.start():].strip()
            
            # 🔑 Divide o texto usando o padrão \n + LETRA + espaço
            # Isso separa as opções corretamente
            parts = re.split(r'\n([A-E])\s+', options_section)
            
            # parts[0] = texto antes de A (geralmente vazio)
            # parts[1] = 'A', parts[2] = texto da opção A
            # parts[3] = 'B', parts[4] = texto da opção B, etc.
            
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    letter = parts[i].upper()
                    text = parts[i + 1].strip()
                    
                    # Remove ponto final se houver
                    text = re.sub(r'\.\s*$', '', text)
                    
                    # Limpa texto
                    text = self.clean_option_text(text)
                    
                    if letter in self.LETTERS and text:
                        options[letter] = text
        else:
            # Não encontrou opções, todo o bloco é stem
            stem = block.strip()
        
        stem = self.normalize_text(stem)
        
        return {
            "stem": stem[:8000],
            "option_a": options.get("A", ""),
            "option_b": options.get("B", ""),
            "option_c": options.get("C", ""),
            "option_d": options.get("D", ""),
            "option_e": options.get("E", ""),
        }
    
    def split_into_question_blocks(self, text: str) -> List[Tuple[int, str, int]]:
        """Divide o texto em blocos de questões."""
        blocks = []
        matches = list(self.QUESTION_HEADER_REGEX.finditer(text))
        
        for i, match in enumerate(matches):
            question_num = int(match.group(1))
            if not (1 <= question_num <= 200):
                continue
            
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[start:end]
            
            page_markers = text[:start].count('--- PAGE ')
            page_num = max(1, page_markers)
            
            blocks.append((question_num, block, page_num))
        
        return blocks
    
    def extract_gabarito(self, text: str) -> Dict[int, str]:
        """Extrai gabarito do texto."""
        gabarito = {}
        lower = text.lower()
        
        gabarito_index = max(
            lower.rfind("gabarito"),
            lower.rfind("respostas"),
            lower.rfind("resposta oficial")
        )
        
        section = text[gabarito_index:] if gabarito_index >= 0 else text[-3000:]
        pattern = re.compile(r'\b(\d{1,3})\s*[-\s.]?\s*([A-E])\b')
        
        for match in pattern.finditer(section):
            num = int(match.group(1))
            letter = match.group(2)
            if 1 <= num <= 200 and letter in self.LETTERS:
                gabarito[num] = letter
        
        return gabarito
    
    def associate_images_to_questions(
        self, 
        question_blocks: List[Tuple[int, str, int]], 
        page_images: Dict[int, List[str]]
    ) -> Dict[int, List[str]]:
        """Associa imagens às questões baseado na página."""
        question_images = {}
        
        for question_num, _, page_num in question_blocks:
            if page_num in page_images:
                question_images[question_num] = page_images[page_num]
            else:
                question_images[question_num] = []
        
        return question_images
    
    def extract_questions(self, gabarito_text: Optional[str] = None) -> List[ParsedQuestion]:
        """Extrai todas as questões do PDF."""
        print(f"Extraindo texto e imagens de {self.pdf_path}...")
        full_text, page_images = self.extract_text_and_images()
        
        print("Dividindo texto em questões...")
        question_blocks = self.split_into_question_blocks(full_text)
        
        print("Associando imagens às questões...")
        question_images = self.associate_images_to_questions(question_blocks, page_images)
        
        print("Extraindo gabarito...")
        if gabarito_text:
            gabarito = self.extract_gabarito(gabarito_text)
        else:
            gabarito = self.extract_gabarito(full_text)
        
        print("Analisando questões...")
        questions = []
        
        for question_num, block, _ in question_blocks:
            parsed = self.parse_question_block(block)
            
            correct_letter = gabarito.get(question_num, "")
            images = question_images.get(question_num, [])
            
            question = ParsedQuestion(
                number=question_num,
                stem=parsed["stem"],
                option_a=parsed["option_a"],
                option_b=parsed["option_b"],
                option_c=parsed["option_c"],
                option_d=parsed["option_d"],
                option_e=parsed["option_e"],
                correct_letter=correct_letter,
                images=images,
                has_image=len(images) > 0
            )
            
            questions.append(question)
        
        questions.sort(key=lambda q: q.number)
        
        print(f"\n✓ Extraídas {len(questions)} questões")
        print(f"✓ {sum(1 for q in questions if q.has_image)} questões com imagens")
        
        # Diagnóstico
        empty_options = [q.number for q in questions if not q.option_a]
        if empty_options:
            print(f"⚠️  {len(empty_options)} questões sem opção A: {empty_options[:10]}")
        
        return questions
    
    def save_to_json(self, questions: List[ParsedQuestion], output_file: str = "questions.json"):
        """Salva questões em arquivo JSON."""
        output_path = self.output_dir / output_file
        
        questions_dict = [asdict(q) for q in questions]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({"questions": questions_dict}, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Questões salvas em: {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extrai questões do Revalida')
    parser.add_argument('pdf_path', help='Caminho para o PDF')
    parser.add_argument('--gabarito', '-g', help='Caminho para gabarito (opcional)')
    parser.add_argument('--output', '-o', default='extracted_questions', help='Diretório de saída')
    parser.add_argument('--json', '-j', default='questions.json', help='Nome do JSON')
    
    args = parser.parse_args()
    
    extractor = RevalidaPDFExtractor(args.pdf_path, args.output)
    
    gabarito_text = None
    if args.gabarito:
        gabarito_path = Path(args.gabarito)
        if gabarito_path.suffix.lower() == '.pdf':
            doc = fitz.open(args.gabarito)
            gabarito_text = "".join(page.get_text() for page in doc)
            doc.close()
        else:
            with open(args.gabarito, 'r', encoding='utf-8') as f:
                gabarito_text = f.read()
    
    questions = extractor.extract_questions(gabarito_text)
    extractor.save_to_json(questions, args.json)
    
    print(f"\n{'='*60}")
    print("RESUMO")
    print(f"{'='*60}")
    print(f"Total: {len(questions)} questões")
    print(f"Com imagem: {sum(1 for q in questions if q.has_image)}")
    print(f"Sem imagem: {sum(1 for q in questions if not q.has_image)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()