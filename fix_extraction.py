"""
Script Corretor - Extrai opções do stem quando elas não foram separadas
"""

import json
import re
from pathlib import Path

def extract_options_from_stem(stem: str) -> dict:
    """
    Extrai opções A-E de um texto onde elas estão misturadas com o enunciado.
    """
    
    # Procura pela primeira ocorrência de " A " seguido de texto (opção A)
    # Tenta vários padrões para encontrar a opção A
    first_option = (
        re.search(r'(?:^|\n)\s*A\s+(?=[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ])', stem, re.MULTILINE) or
        re.search(r'\s+A\s+', stem) or
        re.search(r'(?:^|\n)A\s', stem, re.MULTILINE)
    )
    
    if not first_option:
        return {
            "stem_clean": stem,
            "option_a": "",
            "option_b": "",
            "option_c": "",
            "option_d": "",
            "option_e": ""
        }
    
    # Separa enunciado limpo das opções
    split_pos = first_option.start()
    stem_clean = stem[:split_pos].strip()
    options_text = stem[split_pos:].strip()
    
    # Divide o texto pelas letras das opções
    # Padrão: espaço + letra (A-E) + espaço
    parts = re.split(r'\s+([A-E])\s+', options_text)
    
    # Monta dicionário de opções
    options = {}
    current_letter = None
    
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
            
        # Se é uma letra (A-E), marca como letra atual
        if part in ['A', 'B', 'C', 'D', 'E'] and len(part) == 1:
            current_letter = part
        # Se não, é o texto da opção atual
        elif current_letter:
            # Limpa o texto
            text = re.sub(r'\s+', ' ', part).strip()
            # Remove possível ponto no início
            text = re.sub(r'^\.\s*', '', text)
            
            # Limpa textos indesejados (ÁREA LIVRE, marcadores de página, etc)
            text = re.sub(r'\s*ÁREA\s+LIVRE.*$', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*---\s*PAGE\s+\d+\s*---.*$', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*PRIMEIRA\s+EDI[ÇC][ÃA]O.*$', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*SEGUNDA\s+EDI[ÇC][ÃA]O.*$', '', text, flags=re.IGNORECASE)
            text = text.strip()
            
            options[current_letter] = text
            current_letter = None
    
    return {
        "stem_clean": stem_clean,
        "option_a": options.get("A", ""),
        "option_b": options.get("B", ""),
        "option_c": options.get("C", ""),
        "option_d": options.get("D", ""),
        "option_e": options.get("E", "")
    }


def fix_json_file(input_file: str, output_file: str):
    """
    Corrige um arquivo JSON com questões onde as opções estão vazias.
    """
    
    print("="*60)
    print("CORRETOR DE EXTRAÇÃO - REVALIDA")
    print("="*60)
    
    # Lê o arquivo
    print(f"\nLendo arquivo: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    questions = data.get('questions', [])
    print(f"Total de questões: {len(questions)}")
    
    # Conta quantas precisam de correção
    need_fix = sum(1 for q in questions if not q['options']['A'] and not q['options']['B'])
    print(f"Questões sem opções: {need_fix}")
    
    if need_fix == 0:
        print("\n✅ Nenhuma questão precisa de correção!")
        return
    
    # Corrige cada questão
    print("\nCorrigindo questões...")
    fixed_count = 0
    
    for q in questions:
        # Se as opções estão vazias, tenta extrair do stem
        if not q['options']['A'] and not q['options']['B']:
            result = extract_options_from_stem(q['stem'])
            
            # Atualiza apenas se encontrou opções
            if result['option_a'] or result['option_b']:
                q['stem'] = result['stem_clean']
                q['options']['A'] = result['option_a']
                q['options']['B'] = result['option_b']
                q['options']['C'] = result['option_c']
                q['options']['D'] = result['option_d']
                q['options']['E'] = result['option_e']
                fixed_count += 1
    
    print(f"Questões corrigidas: {fixed_count}")
    
    # Salva arquivo corrigido
    print(f"\nSalvando arquivo corrigido: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Mostra exemplo de questão corrigida
    print("\n" + "="*60)
    print("EXEMPLO DE QUESTÃO CORRIGIDA")
    print("="*60)
    
    for q in questions[:3]:
        if q['options']['A']:
            print(f"\nQUESTÃO {q['number']}")
            print(f"\nEnunciado: {q['stem'][:150]}...")
            print(f"\nOpções:")
            print(f"  A) {q['options']['A'][:80]}...")
            print(f"  B) {q['options']['B'][:80]}...")
            print(f"  C) {q['options']['C'][:80]}...")
            print(f"  D) {q['options']['D'][:80]}...")
            if q['options']['E']:
                print(f"  E) {q['options']['E'][:80]}...")
            break
    
    print("\n" + "="*60)
    print("✅ CORREÇÃO CONCLUÍDA!")
    print("="*60)


if __name__ == "__main__":
    # Usa o arquivo que você forneceu
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "questions_fixed.json"
    else:
        input_file = "/home/claude/extraction_result.json"
        output_file = "/home/claude/questions_fixed.json"
    
    fix_json_file(input_file, output_file)
