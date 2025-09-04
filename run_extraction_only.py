#!/usr/bin/env python3
"""
Executa apenas a etapa de extração do pipeline
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()

from agents.extract_agent.extract_agent import extract_jobs_via_linkedin_scraping, run_extract

def run_extraction_test():
    """Execute only the extraction step for testing"""
    
    print("🔄 EXECUTANDO EXTRAÇÃO LINKEDIN - TESTE")
    print("=" * 50)
    
    # Categories to extract
    categories = [
        {
            'name': 'DATA_ENGINEER',
            'search_terms': ['Data Engineer', 'Engenheiro de Dados'],
            'category': 'data_engineer'
        },
        {
            'name': 'DATA_ANALYTICS', 
            'search_terms': ['Data Analytics', 'Analista de Dados'],
            'category': 'data_analytics'
        },
        {
            'name': 'DIGITAL_ANALYTICS',
            'search_terms': ['Digital Analytics', 'Web Analytics'],
            'category': 'digital_analytics'
        }
    ]
    
    all_jobs = []
    total_by_category = {}
    
    for cat in categories:
        print(f"\n📂 Extraindo categoria: {cat['name']}")
        category_jobs = []
        
        for search_term in cat['search_terms']:
            print(f"🔍 Buscando: '{search_term}'")
            
            jobs = extract_jobs_via_linkedin_scraping(
                search_term=search_term,
                max_results=10,  # Limite pequeno para teste
                category=cat['category']
            )
            
            if jobs:
                category_jobs.extend(jobs)
                print(f"✅ {len(jobs)} vagas encontradas para '{search_term}'")
            else:
                print(f"⚠️ Nenhuma vaga encontrada para '{search_term}'")
        
        total_by_category[cat['name']] = len(category_jobs)
        all_jobs.extend(category_jobs)
        
        print(f"📊 {cat['name']}: {len(category_jobs)} vagas total")
    
    # Summary
    print("\n" + "=" * 50)
    print("📈 RESUMO DA EXTRAÇÃO")
    print("=" * 50)
    
    for cat_name, count in total_by_category.items():
        print(f"📁 {cat_name}: {count} vagas")
    
    print(f"\n🎯 TOTAL GERAL: {len(all_jobs)} vagas extraídas")
    
    if all_jobs:
        print("\n🔍 AMOSTRA DE VAGAS:")
        for i, job in enumerate(all_jobs[:5], 1):
            print(f"  {i}. {job['title']} - {job['company']} ({job['location']})")
        
        print("\n✅ Extração funcionando corretamente!")
        return True
    else:
        print("\n❌ Nenhuma vaga extraída - verificar configurações")
        return False

def run_extract_offline():
    return run_extraction_test()

def run_extraction_with_streaming():
    """Try streaming mode first, fallback to offline if needed"""
    print("🚀 TENTANDO MODO STREAMING COM KAFKA...")
    try:
        result = run_extract()  # Try streaming mode with Kafka
        return result is not None
    except Exception as e:
        print(f"⚠️ Streaming falhou: {e}")
        print("🔄 Usando modo offline como fallback...")
        return run_extraction_test()

if __name__ == "__main__":
    success = run_extraction_with_streaming()  # Try Kafka streaming first
    sys.exit(0 if success else 1)
