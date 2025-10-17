#!/usr/bin/env python3
"""
Extract Agent - Modo Simplificado
Extração sem dependências externas (Kafka/APIs) para teste imediato
"""

import json
import os
import time
from datetime import datetime, timedelta
import random


def generate_realistic_jobs(search_term, count=20):
    """
    Gera dados mock realistas para teste
    """
    companies = [
        "Nubank",
        "Itaú",
        "Bradesco",
        "Magazine Luiza",
        "Mercado Livre",
        "iFood",
        "Stone",
        "PagSeguro",
        "Globo",
        "Petrobras",
        "Vale",
        "Embraer",
        "BRF",
        "JBS",
        "Ambev",
    ]

    cities = [
        "São Paulo, SP",
        "Rio de Janeiro, RJ",
        "Belo Horizonte, MG",
        "Porto Alegre, RS",
        "Curitiba, PR",
        "Recife, PE",
        "Remote, Brasil",
    ]

    job_levels = ["Júnior", "Pleno", "Sênior"]

    jobs = []
    for i in range(count):
        level = random.choice(job_levels)
        company = random.choice(companies)
        city = random.choice(cities)

        # Data realista entre 1-30 dias atrás
        days_ago = random.randint(1, 30)
        posted_date = (datetime.now() - timedelta(days=days_ago)).isoformat()

        job = {
            "job_id": f"job_{datetime.now().strftime('%Y%m%d')}_{i:03d}",
            "job_title": f"{search_term} {level}",
            "company_name": company,
            "location": city,
            "posted_date": posted_date,
            "job_url": f"https://linkedin.com/jobs/view/{random.randint(1000000, 9999999)}",
            "description_snippet": f"Vaga para {search_term} {level} em {company}. Responsabilidades incluem análise de dados, desenvolvimento de pipelines e criação de dashboards.",
            "salary_min": (
                random.randint(4000, 8000)
                if level == "Júnior"
                else random.randint(6000, 12000) if level == "Pleno" else random.randint(10000, 18000)
            ),
            "salary_max": (
                random.randint(6000, 10000)
                if level == "Júnior"
                else random.randint(8000, 15000) if level == "Pleno" else random.randint(15000, 25000)
            ),
            "is_remote": city == "Remote, Brasil",
            "experience_level": level.lower(),
            "required_skills": random.sample(
                [
                    "Python",
                    "SQL",
                    "Tableau",
                    "Power BI",
                    "Excel",
                    "Pandas",
                    "NumPy",
                    "Matplotlib",
                    "Seaborn",
                    "Git",
                    "AWS",
                    "GCP",
                ],
                random.randint(3, 6),
            ),
            "search_category": search_term.lower().replace(" ", "_"),
            "type": search_term.lower().replace(" ", "_"),
            "extracted_at": datetime.now().isoformat(),
            "data_source": "mock_realistic",
        }
        jobs.append(job)

    return jobs


def extract_all_categories():
    """
    Extrai todas as categorias definidas no projeto
    """
    print("🚀 Iniciando extração simplificada...")

    # Categorias do projeto
    categories = {
        "data_engineer": "Data Engineer",
        "data_analytics": "Data Analytics",
        "digital_analytics": "Digital Analytics",
    }

    # Criar diretório de dados
    data_dir = "data_extracts"
    os.makedirs(data_dir, exist_ok=True)

    results = {}
    timestamp = datetime.now().strftime("%Y-%m-%d")

    for category, search_term in categories.items():
        print(f"\n📂 Extraindo: {category.upper()}")

        # Gerar dados mock
        jobs = generate_realistic_jobs(search_term, count=25)

        # Salvar localmente
        filename = f"{category}_{timestamp.replace('-', '')}.json"
        filepath = os.path.join(data_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)

        print(f"✅ {len(jobs)} vagas salvas: {filename}")

        results[category] = {"count": len(jobs), "file": filepath, "jobs_sample": jobs[:3]}  # Amostra para verificação

    return results


def create_summary_report(results):
    """
    Cria relatório consolidado
    """
    total_jobs = sum(r["count"] for r in results.values())

    report = {
        "extraction_summary": {
            "timestamp": datetime.now().isoformat(),
            "total_jobs_extracted": total_jobs,
            "categories_processed": len(results),
            "status": "SUCCESS",
        },
        "category_breakdown": {
            category: {"count": data["count"], "file": data["file"]} for category, data in results.items()
        },
    }

    # Salvar relatório
    with open("data_extracts/extraction_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


if __name__ == "__main__":
    print("=== EXTRAÇÃO SIMPLIFICADA ===\n")

    # Executar extração
    results = extract_all_categories()

    # Criar relatório
    report = create_summary_report(results)

    print(f"\n📊 RESUMO FINAL:")
    print(f"Total de vagas: {report['extraction_summary']['total_jobs_extracted']}")
    print(f"Categorias: {list(results.keys())}")
    print(f"Arquivos criados em: data_extracts/")

    print("\n✅ Extração concluída com sucesso!")
