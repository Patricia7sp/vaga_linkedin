#!/usr/bin/env python3
"""
RapidAPI LinkedIn Extractor - Extract Agent Melhorado
Usa RapidAPI LinkedIn Job Search API para extração robusta sem bloqueios
"""

import json
import os
import pathlib
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

# Load environment variables
project_root = pathlib.Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


class RapidAPILinkedInExtractor:
    """Extrator de vagas LinkedIn via RapidAPI - 100% confiável"""

    API_URL = "https://fresh-linkedin-scraper-api.p.rapidapi.com/api/v1/job/search"

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa extrator RapidAPI

        Args:
            api_key: RapidAPI key (ou usa RAPIDAPI_KEY do .env)
        """
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY não encontrada. Configure no .env ou passe como parâmetro")

        self.headers = {"x-rapidapi-key": self.api_key, "x-rapidapi-host": "fresh-linkedin-scraper-api.p.rapidapi.com"}

        self.request_count = 0
        self.max_requests = 100  # Limite do plano gratuito

        print("✅ RapidAPI LinkedIn Extractor inicializado")
        print(f"📊 Limite: {self.max_requests} requests/mês")

    def search_jobs(
        self,
        keyword: str,
        location: str = "Brazil",
        job_type: Optional[str] = None,
        remote: bool = False,
        date_posted: str = "past_week",
        limit: int = 100,
    ) -> List[Dict]:
        """
        Busca vagas no LinkedIn via RapidAPI

        Args:
            keyword: Termo de busca (ex: "Data Engineer")
            location: Localização (ex: "Brazil", "São Paulo")
            job_type: Tipo da vaga (full_time, part_time, contract, temporary, internship, etc.)
            remote: Apenas vagas remotas
            date_posted: Filtro de data (past_24_hours, past_week, past_month, anytime)
            limit: Máximo de vagas (até 100 por request)

        Returns:
            Lista de vagas em formato estruturado
        """
        if self.request_count >= self.max_requests:
            print(f"⚠️ Limite de {self.max_requests} requests atingido. Use fallback Selenium.")
            return []

        params = {
            "keyword": keyword,
            "page": 1,
            "sort_by": "recent",
            "date_posted": date_posted,
            "geo_id": "106057199",  # Geocode para Brasil no LinkedIn
        }

        # Adicionar filtros opcionais
        if job_type:
            params["job_type"] = job_type

        if remote:
            params["remote"] = "remote"

        try:
            print(f"🔍 Buscando: '{keyword}' em {location} (geo_id: Brasil - últimos 7 dias)...")

            response = requests.get(self.API_URL, headers=self.headers, params=params, timeout=30)

            self.request_count += 1
            print(f"📊 Requests usados: {self.request_count}/{self.max_requests}")

            if response.status_code == 200:
                result = response.json()

                # Verificar se a resposta foi bem-sucedida
                if not result.get("success", False):
                    print(f"⚠️ API retornou erro: {result.get('message', 'Unknown error')}")
                    return []

                jobs = result.get("data", [])

                # Normalizar formato para compatibilidade com pipeline existente
                normalized_jobs = self._normalize_jobs(jobs, keyword)

                print(f"✅ {len(normalized_jobs)} vagas encontradas")
                return normalized_jobs[:limit]

            elif response.status_code == 429:
                print("⚠️ Rate limit atingido. Aguarde antes de nova requisição.")
                return []

            else:
                print(f"❌ Erro {response.status_code}: {response.text[:200]}")
                return []

        except Exception as e:
            print(f"❌ Exceção ao buscar vagas: {e}")
            return []

    def _normalize_jobs(self, jobs: List[Dict], search_term: str) -> List[Dict]:
        """
        Normaliza formato da API Fresh LinkedIn Scraper para o formato esperado pelo pipeline

        Mapeamento completo de campos:
        - Informações básicas: title, url, company, location
        - Detalhes da vaga: work_modality, contract_type, salary
        - Timestamps: posted_date, is_recent
        - Localização: city, state, country
        """
        normalized = []

        for job in jobs:
            try:
                # Extrair company info
                company = job.get("company", {})
                company_name = company.get("name", "") if isinstance(company, dict) else str(company if company else "")
                company_id = company.get("id", "") if isinstance(company, dict) else ""
                company_url = company.get("url", "") if isinstance(company, dict) else ""

                # Extrair localização detalhada
                location_raw = job.get("location", "")
                city = job.get("city", "")
                state = job.get("state", "")
                country = job.get("country", "")

                # Se location vem como string composta, tentar parsear
                if location_raw and not city:
                    location_parts = location_raw.split(",")
                    if len(location_parts) >= 2:
                        city = location_parts[0].strip()
                        state = location_parts[1].strip() if len(location_parts) > 1 else ""
                        country = location_parts[-1].strip() if len(location_parts) > 2 else "Brazil"

                # Extrair timestamp de postagem e inferir campos
                posted_time = job.get("listed_at", job.get("posted_at", ""))

                # Converter listed_at (string) para timestamp
                posted_time_ts = None
                is_recent = False
                if posted_time:
                    try:
                        from dateutil import parser

                        posted_dt = parser.parse(posted_time)
                        posted_time_ts = posted_dt

                        # Calcular se é recente (< 7 dias)
                        days_ago = (datetime.now() - posted_dt).days
                        is_recent = days_ago < 7
                    except Exception:  # noqa: E722
                        # Se falhar, usar timestamp atual
                        posted_time_ts = datetime.now()
                        is_recent = True

                # Inferir work_modality a partir do location
                work_modality = None
                location_lower = location_raw.lower() if location_raw else ""
                if "remote" in location_lower:
                    work_modality = "remote"
                elif "hybrid" in location_lower:
                    work_modality = "hybrid"
                elif location_raw and not ("remote" in location_lower or "hybrid" in location_lower):
                    work_modality = "onsite"

                # contract_type não pode ser inferido sem descrição
                contract_type = job.get("contract_type", job.get("job_type", None))

                # Extrair informações salariais
                salary_min = job.get("salary_min", None)
                salary_max = job.get("salary_max", None)
                salary_range = job.get("salary_range", None)
                has_salary_info = salary_min is not None or salary_max is not None or salary_range is not None

                normalized_job = {
                    # ===== CAMPOS OBRIGATÓRIOS =====
                    "job_id": str(job.get("id", job.get("job_id", ""))),
                    "job_title": job.get("title", ""),
                    "title": job.get("title", ""),  # Alias
                    "company_name": company_name,
                    "company": company_name,  # Alias
                    "location": location_raw or f"{city}, {state}, {country}".strip(", "),
                    "job_url": job.get("url", job.get("link", "")),
                    "url": job.get("url", job.get("link", "")),  # Alias
                    # ===== LOCALIZAÇÃO DETALHADA =====
                    "city": city,
                    "state": state,
                    "country": country or "Brazil",
                    # ===== INFORMAÇÕES DE DATA =====
                    "posted_date": posted_time,
                    "posted_time_ts": posted_time_ts,
                    "is_recent_posting": is_recent,
                    # ===== INFORMAÇÕES DE TRABALHO =====
                    "work_modality": work_modality,
                    "contract_type": contract_type,
                    # ===== INFORMAÇÕES SALARIAIS =====
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "salary_range": salary_range,
                    "has_salary_info": has_salary_info,
                    # ===== CAMPOS EXTRAS =====
                    "description_snippet": job.get("description", "")[:500] if job.get("description") else "",
                    "company_id": str(company_id),
                    "company_url": company_url,
                    "is_remote": (
                        work_modality == "remote"
                        if work_modality
                        else ("remote" in location_raw.lower() if location_raw else False)
                    ),
                    "is_easy_apply": job.get("is_easy_apply", job.get("easy_apply", False)),
                    "is_promoted": job.get("is_promote", job.get("is_promoted", False)),
                    # ===== METADADOS DA EXTRAÇÃO =====
                    "extraction_method": "rapidapi",
                    "extraction_timestamp": datetime.now().isoformat(),
                    "search_term": search_term,
                    "description_quality_score": "high" if job.get("description") else "low",
                }

                # Validação básica - exigir ao menos título OU url
                if normalized_job["job_title"] or normalized_job["job_url"]:
                    normalized.append(normalized_job)
                else:
                    print(f"⚠️ Vaga sem título e URL: {job.get('id', 'N/A')}")

            except Exception as e:
                print(f"⚠️ Erro ao normalizar vaga {job.get('id', 'N/A')}: {e}")
                import traceback

                traceback.print_exc()
                continue

        return normalized

    def get_usage_stats(self) -> Dict:
        """Retorna estatísticas de uso"""
        return {
            "requests_used": self.request_count,
            "requests_remaining": self.max_requests - self.request_count,
            "limit": self.max_requests,
            "usage_percentage": (self.request_count / self.max_requests) * 100,
        }


def extract_jobs_via_rapidapi(
    search_term: str, location: str = "Brazil", max_results: int = 100, category: str = "general"
) -> List[Dict]:
    """
    Função wrapper para compatibilidade com extract_agent.py existente

    Args:
        search_term: Termo de busca
        location: Localização
        max_results: Máximo de resultados
        category: Categoria da vaga

    Returns:
        Lista de vagas normalizadas
    """
    try:
        extractor = RapidAPILinkedInExtractor()
        jobs = extractor.search_jobs(keyword=search_term, location=location, date_posted="past_week", limit=max_results)

        # Adicionar categoria
        for job in jobs:
            job["category"] = category

        return jobs

    except Exception as e:
        print(f"❌ Erro na extração RapidAPI: {e}")
        return []


def run_extraction(categories: Optional[Dict[str, List[str]]] = None, output_dir: str = "./data/linkedin_jobs") -> Dict:
    """
    Executa extração completa para todas as categorias

    Args:
        categories: Dict com categorias e termos de busca
        output_dir: Diretório de saída

    Returns:
        Resumo da extração
    """
    if categories is None:
        categories = {
            "data_engineer": ["Data Engineer", "Engenheiro de Dados"],
            "data_analytics": ["Data Analytics", "Analista de Dados"],
            "digital_analytics": ["Digital Analytics"],
        }

    # Criar diretório
    os.makedirs(output_dir, exist_ok=True)

    extractor = RapidAPILinkedInExtractor()
    timestamp = datetime.now().strftime("%Y-%m-%d")
    results = {}

    print("\n" + "=" * 70)
    print("🚀 INICIANDO EXTRAÇÃO VIA RAPIDAPI")
    print("=" * 70 + "\n")

    for category, search_terms in categories.items():
        print(f"\n📂 CATEGORIA: {category.upper()}")
        print("-" * 70)

        all_jobs = []

        for search_term in search_terms:
            jobs = extractor.search_jobs(keyword=search_term, location="Brazil", date_posted="past_week", limit=50)

            # Adicionar categoria e termo de busca
            for job in jobs:
                job["category"] = category
                job["original_search_term"] = search_term

            all_jobs.extend(jobs)

            # Rate limiting
            time.sleep(1)

        # Remover duplicatas por job_id
        unique_jobs = {}
        for job in all_jobs:
            job_id = job.get("job_id")
            if job_id and job_id not in unique_jobs:
                unique_jobs[job_id] = job

        final_jobs = list(unique_jobs.values())

        # Salvar JSON
        filename = f"{category}_{timestamp.replace('-', '')}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_jobs, f, indent=2, ensure_ascii=False)

        print(f"✅ {len(final_jobs)} vagas salvas em {filename}")

        results[category] = {"count": len(final_jobs), "file": filepath}

    # Estatísticas finais
    stats = extractor.get_usage_stats()

    print("\n" + "=" * 70)
    print("📊 RESUMO DA EXTRAÇÃO")
    print("=" * 70)
    print(f"Total de vagas: {sum(r['count'] for r in results.values())}")
    print(f"Requests usados: {stats['requests_used']}/{stats['limit']}")
    print(f"Requests restantes: {stats['requests_remaining']}")
    print("=" * 70 + "\n")

    return {"results": results, "stats": stats, "timestamp": timestamp}


if __name__ == "__main__":
    # Teste standalone
    print("🧪 TESTE DO EXTRATOR RAPIDAPI\n")

    summary = run_extraction()

    print("\n✅ Extração concluída!")
    print("📁 Arquivos salvos em: ./data/linkedin_jobs/")
