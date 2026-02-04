"""
Extrator de questões do Revalida com suporte a imagens.
Baseado na lógica do parsePdf.ts mas com extração de imagens.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF
from PIL import Image
import io
import argparse


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
    images: List[str]  # Lista de caminhos para imagens
    has_image: bool


class RevalidaPDFExtractor:
    """Extrator de questões do PDF do Revalida."""
    
    LETTERS = ["A", "B", "C", "D", "E"]
    QUESTION_HEADER_REGEX = re.compile(r'\n\s*QUEST[ÃAÀ]O\s*(\d{1,3})\s*[\s:\-]?', re.IGNORECASE)
    OPTION_START_REGEX = re.compile(r'(?:^|\n)\s*([A-E])[.)\-]\s*', re.MULTILINE)
    FIRST_OPTION_STRICT = re.compile(r'(?:^|\n)\s*A[.)\-]\s*')
    
    def __init__(self, pdf_path: str, output_dir: str = "extracted_questions"):
        """
        Inicializa o extrator.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            output_dir: Diretório para salvar as imagens extraídas
        """
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
    def extract_text_and_images(self) -> Tuple[str, Dict[int, List[str]]]:
        """
        Extrai texto completo e imagens do PDF, associando imagens às páginas.
        
        Returns:
            Tupla (texto_completo, dicionário de página -> lista de caminhos de imagens)
        """
        doc = fitz.open(self.pdf_path)
        full_text = ""
        page_images = {}
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extrai texto da página
            text = page.get_text()
            full_text += f"\n--- PAGE {page_num + 1} ---\n{text}"
            
            # Extrai imagens da página
            image_list = page.get_images()
            page_image_paths = []
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Salva a imagem
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
        text = text.replace('\n', ' ')
        return text.strip()
    
    def preprocess_block(self, block: str) -> str:
        """Preprocessa bloco de texto."""
        block = block.replace('\r\n', '\n').replace('\r', '\n')
        block = re.sub(r'[ \t]+', ' ', block)
        block = re.sub(r'\n +\n', '\n\n', block)
        return block.strip()
    
    def find_option_starts(self, option_section: str) -> List[Tuple[str, int]]:
        """Encontra posições iniciais das opções."""
        matches = []
        for match in self.OPTION_START_REGEX.finditer(option_section):
            matches.append((match.group(1).upper(), match.start()))
        return matches
    
    def extract_options_by_slices(self, option_section: str) -> Dict[str, str]:
        """Extrai opções dividindo o texto entre marcadores."""
        options = {letter: "" for letter in self.LETTERS}
        starts = self.find_option_starts(option_section)
        max_option_length = 4000
        
        for i, (letter, start) in enumerate(starts):
            end = starts[i + 1][1] if i + 1 < len(starts) else len(option_section)
            raw = option_section[start:end]
            
            # Remove o marcador da opção (A. B. etc)
            after_marker = re.sub(r'^\s*[A-E][.)\-]\s*', '', raw)
            text = after_marker.strip()
            
            if 0 < len(text) <= max_option_length:
                options[letter] = self.normalize_text(text)
        
        return options
    
    def parse_question_block(self, block: str) -> Dict[str, str]:
        """Analisa um bloco de questão e extrai enunciado e opções."""
        block = self.preprocess_block(block)
        options = {letter: "" for letter in self.LETTERS}
        
        # Tenta encontrar onde começam as opções
        # Padrão mais flexível: A) ou A. ou A - seguido de texto
        option_pattern = re.compile(r'\n\s*([A-E])\s*[.)\-]\s*(.+?)(?=\n\s*[A-E]\s*[.)\-]|\Z)', re.DOTALL)
        
        # Procura pelo início das opções
        first_option_match = re.search(r'\n\s*A\s*[.)\-]\s*', block)
        
        if first_option_match:
            # Separa enunciado das opções
            stem_end = first_option_match.start()
            stem = block[:stem_end]
            option_section = block[stem_end:]
            
            # Remove cabeçalho da questão do stem
            stem = re.sub(r'^\s*QUEST[ÃAÀ]O\s*\d{1,3}\s*[\s:\-]?\s*', '', stem, flags=re.IGNORECASE)
            stem = self.normalize_text(stem)
            
            # Extrai cada opção
            for match in option_pattern.finditer(option_section):
                letter = match.group(1).upper()
                text = match.group(2).strip()
                
                # Remove possíveis fragmentos de outras opções
                text = re.split(r'\n\s*[A-E]\s*[.)\-]', text)[0]
                text = self.normalize_text(text)
                
                if letter in self.LETTERS and text:
                    options[letter] = text
        else:
            # Se não encontrou opções, todo o bloco é o enunciado
            stem = block
            stem = re.sub(r'^\s*QUEST[ÃAÀ]O\s*\d{1,3}\s*[\s:\-]?\s*', '', stem, flags=re.IGNORECASE)
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
        """
        Divide o texto em blocos de questões.
        
        Returns:
            Lista de tuplas (número_questão, bloco_texto, página_aproximada)
        """
        blocks = []
        matches = list(self.QUESTION_HEADER_REGEX.finditer(text))
        
        for i, match in enumerate(matches):
            question_num = int(match.group(1))
            if not (1 <= question_num <= 200):
                continue
            
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[start:end]
            
            # Estima a página pela posição no texto
            # Conta quantos marcadores de página aparecem antes deste bloco
            page_markers = text[:start].count('--- PAGE ')
            page_num = max(1, page_markers)
            
            blocks.append((question_num, block, page_num))
        
        return blocks
    
    def extract_gabarito(self, text: str) -> Dict[int, str]:
        """
        Extrai gabarito (respostas corretas) do texto.
        
        Args:
            text: Texto completo do PDF ou PDF de gabarito
            
        Returns:
            Dicionário número_questão -> letra_correta
        """
        gabarito = {}
        lower = text.lower()
        
        # Procura por seção de gabarito
        gabarito_index = max(
            lower.rfind("gabarito"),
            lower.rfind("respostas"),
            lower.rfind("resposta oficial")
        )
        
        # Se encontrou seção de gabarito, usa essa parte; senão usa os últimos 3000 caracteres
        section = text[gabarito_index:] if gabarito_index >= 0 else text[-3000:]
        
        # Padrão: número (1-3 dígitos) seguido de letra A-E
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
        """
        Associa imagens às questões baseado na página.
        
        Args:
            question_blocks: Lista de (número_questão, texto, página)
            page_images: Dicionário página -> lista de imagens
            
        Returns:
            Dicionário número_questão -> lista de imagens
        """
        question_images = {}
        
        for question_num, _, page_num in question_blocks:
            if page_num in page_images:
                question_images[question_num] = page_images[page_num]
            else:
                question_images[question_num] = []
        
        return question_images
    
    def extract_questions(self, gabarito_text: Optional[str] = None) -> List[ParsedQuestion]:
        """
        Extrai todas as questões do PDF.
        
        Args:
            gabarito_text: Texto opcional de gabarito separado
        
        Returns:
            Lista de questões extraídas
        """
        print(f"Extraindo texto e imagens de {self.pdf_path}...")
        full_text, page_images = self.extract_text_and_images()
        
        print("Dividindo texto em questões...")
        question_blocks = self.split_into_question_blocks(full_text)
        
        print("Associando imagens às questões...")
        question_images = self.associate_images_to_questions(question_blocks, page_images)
        
        print("Extraindo gabarito...")
        # Tenta extrair gabarito do texto fornecido ou do próprio PDF
        if gabarito_text:
            gabarito = self.extract_gabarito(gabarito_text)
        else:
            gabarito = self.extract_gabarito(full_text)
        
        print("Analisando questões...")
        questions = []
        
        for question_num, block, _ in question_blocks:
            parsed = self.parse_question_block(block)
            
            # Obtém resposta correta do gabarito
            correct_letter = gabarito.get(question_num, "A")
            
            # Obtém imagens associadas
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
        
        # Ordena por número
        questions.sort(key=lambda q: q.number)
        
        print(f"\n✓ Extraídas {len(questions)} questões")
        print(f"✓ {sum(1 for q in questions if q.has_image)} questões com imagens")
        
        return questions
    
    def cleanup_temp_files(self):
        """Remove diretório de imagens temporárias após salvar o JSON."""
        import shutil
        
        if self.images_dir.exists():
            try:
                shutil.rmtree(self.images_dir)
                print(f"✓ Arquivos temporários removidos: {self.images_dir}")
            except Exception as e:
                print(f"⚠️  Erro ao remover arquivos temporários: {e}")
    
    def save_to_json(self, questions: List[ParsedQuestion], output_file: str = "questions.json"):
        """
        Salva questões em arquivo JSON.
        
        Args:
            questions: Lista de questões
            output_file: Nome do arquivo de saída
        """
        output_path = self.output_dir / output_file
        
        # Converte dataclasses para dicionários
        questions_dict = [asdict(q) for q in questions]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(questions_dict, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Questões salvas em: {output_path}")
        
        # Limpa arquivos temporários após salvar
        self.cleanup_temp_files()


def main():
    """Função principal para execução via linha de comando."""
    parser = argparse.ArgumentParser(
        description='Extrai questões do PDF do Revalida com suporte a imagens'
    )
    parser.add_argument('pdf_path', help='Caminho para o arquivo PDF da prova')
    parser.add_argument('--gabarito', '-g', help='Caminho para PDF ou TXT do gabarito (opcional)')
    parser.add_argument('--output', '-o', default='extracted_questions', 
                       help='Diretório de saída (padrão: extracted_questions)')
    parser.add_argument('--json', '-j', default='questions.json',
                       help='Nome do arquivo JSON de saída (padrão: questions.json)')
    
    args = parser.parse_args()
    
    # Inicializa extrator
    extractor = RevalidaPDFExtractor(args.pdf_path, args.output)
    
    # Lê gabarito se fornecido
    gabarito_text = None
    if args.gabarito:
        gabarito_path = Path(args.gabarito)
        if gabarito_path.suffix.lower() == '.pdf':
            # Extrai texto do PDF de gabarito
            doc = fitz.open(args.gabarito)
            gabarito_text = ""
            for page in doc:
                gabarito_text += page.get_text()
            doc.close()
        else:
            # Assume que é arquivo de texto
            with open(args.gabarito, 'r', encoding='utf-8') as f:
                gabarito_text = f.read()
    
    # Extrai questões
    questions = extractor.extract_questions(gabarito_text)
    
    # Salva em JSON
    extractor.save_to_json(questions, args.json)
    
    print(f"\n{'='*60}")
    print("RESUMO DA EXTRAÇÃO")
    print(f"{'='*60}")
    print(f"Total de questões: {len(questions)}")
    print(f"Questões com imagem: {sum(1 for q in questions if q.has_image)}")
    print(f"Questões sem imagem: {sum(1 for q in questions if not q.has_image)}")
    print(f"Imagens extraídas: {sum(len(q.images) for q in questions)}")
    print(f"\nArquivos gerados:")
    print(f"  - JSON: {extractor.output_dir / args.json}")
    print(f"  - Imagens: {extractor.images_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
