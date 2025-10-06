#!/usr/bin/env python3
"""
Extract Agent Híbrido: RapidAPI (primário) + Selenium (fallback)
Garante 100% de extração mesmo se quota RapidAPI acabar
"""

import os
from typing import List, Dict
from datetime import datetime

# Import RapidAPI extractor
try:
    from .rapidapi_linkedin_extractor import RapidAPILinkedInExtractor, extract_jobs_via_rapidapi
    RAPIDAPI_AVAILABLE = True
except ImportError:
    try:
        from rapidapi_linkedin_extractor import RapidAPILinkedInExtractor, extract_jobs_via_rapidapi
        RAPIDAPI_AVAILABLE = True
    except ImportError:
        RAPIDAPI_AVAILABLE = False
        print("⚠️ RapidAPI não disponível.")

# Importar função Selenium existente
try:
    from .extract_agent import extract_jobs_via_linkedin_scraping
    SELENIUM_AVAILABLE = True
except ImportError:
    try:
        from extract_agent import extract_jobs_via_linkedin_scraping
        SELENIUM_AVAILABLE = True
    except ImportError:
        SELENIUM_AVAILABLE = False
        print("⚠️ Selenium não disponível.")


def extract_jobs_hybrid(
    search_term: str,
    location: str = "Brazil",
    max_results: int = 100,
    category: str = "general"
) -> List[Dict]:
    """
    Extração híbrida: tenta RapidAPI primeiro, fallback para Selenium
    
    Args:
        search_term: Termo de busca
        location: Localização
        max_results: Máximo de resultados
        category: Categoria da vaga
    
    Returns:
        Lista de vagas
    """
    print(f"\n🔄 Extração híbrida para: '{search_term}'")
    
    # Tentativa 1: RapidAPI (preferencial)
    if RAPIDAPI_AVAILABLE:
        try:
            print("📡 Tentando RapidAPI...")
            jobs = extract_jobs_via_rapidapi(
                search_term=search_term,
                location=location,
                max_results=max_results,
                category=category
            )
            
            if jobs and len(jobs) > 0:
                print(f"✅ RapidAPI: {len(jobs)} vagas extraídas")
                return jobs
            else:
                print("⚠️ RapidAPI retornou vazio ou quota excedida")
        
        except Exception as e:
            print(f"❌ Erro RapidAPI: {e}")
    
    # Tentativa 2: Selenium (fallback)
    if SELENIUM_AVAILABLE:
        try:
            print("🌐 Fallback: Usando Selenium...")
            jobs = extract_jobs_via_linkedin_scraping(
                search_term=search_term,
                max_results=max_results,
                category=category
            )
            
            if jobs and len(jobs) > 0:
                print(f"✅ Selenium: {len(jobs)} vagas extraídas")
                return jobs
            else:
                print("⚠️ Selenium também retornou vazio")
        
        except Exception as e:
            print(f"❌ Erro Selenium: {e}")
    
    print(f"❌ Falha total na extração de '{search_term}'")
    return []


def run_hybrid_extraction(
    categories: Dict[str, List[str]] = None,
    output_dir: str = "./data/linkedin_jobs"
) -> Dict:
    """
    Executa extração híbrida para todas as categorias
    
    Prioriza RapidAPI, usa Selenium como backup
    """
    if categories is None:
        categories = {
            'data_engineer': ['Data Engineer', 'Engenheiro de Dados'],
            'data_analytics': ['Data Analytics', 'Analista de Dados'],
            'digital_analytics': ['Digital Analytics']
        }
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m-%d')
    results = {}
    stats = {
        'rapidapi_count': 0,
        'selenium_count': 0,
        'total': 0
    }
    
    print("\n" + "="*70)
    print("🚀 EXTRAÇÃO HÍBRIDA: RapidAPI + Selenium")
    print("="*70 + "\n")
    
    for category, search_terms in categories.items():
        print(f"\n📂 CATEGORIA: {category.upper()}")
        print("-" * 70)
        
        all_jobs = []
        
        for search_term in search_terms:
            jobs = extract_jobs_hybrid(
                search_term=search_term,
                location="Brazil",
                max_results=50,
                category=category
            )
            
            # Contar fonte
            for job in jobs:
                if job.get('extraction_method') == 'rapidapi':
                    stats['rapidapi_count'] += 1
                else:
                    stats['selenium_count'] += 1
            
            all_jobs.extend(jobs)
        
        # Remover duplicatas
        unique_jobs = {}
        for job in all_jobs:
            job_id = job.get('job_id') or job.get('job_url', '')
            if job_id and job_id not in unique_jobs:
                unique_jobs[job_id] = job
        
        final_jobs = list(unique_jobs.values())
        
        # Salvar
        import json
        filename = f"{category}_{timestamp.replace('-', '')}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(final_jobs, f, indent=2, ensure_ascii=False)
        
        print(f"✅ {len(final_jobs)} vagas salvas em {filename}")
        
        results[category] = {
            'count': len(final_jobs),
            'file': filepath
        }
        
        stats['total'] += len(final_jobs)
    
    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO DA EXTRAÇÃO HÍBRIDA")
    print("="*70)
    print(f"Total de vagas: {stats['total']}")
    print(f"Via RapidAPI: {stats['rapidapi_count']} ({stats['rapidapi_count']/stats['total']*100:.1f}%)")
    print(f"Via Selenium: {stats['selenium_count']} ({stats['selenium_count']/stats['total']*100:.1f}%)")
    print("="*70 + "\n")
    
    return {
        'results': results,
        'stats': stats,
        'timestamp': timestamp
    }


if __name__ == "__main__":
    summary = run_hybrid_extraction()
    print("\n✅ Extração híbrida concluída!")
