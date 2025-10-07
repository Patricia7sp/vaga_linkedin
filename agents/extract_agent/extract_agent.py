#!/usr/bin/env python3
"""
Extract Agent: Real-time job extraction using Kafka + PySpark Streaming architecture.
Extracts job data from APIs and processes them through Kafka streaming to GCP.
"""

import json
import os
import random
import subprocess
import time
from datetime import datetime

from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# GCP Storage
try:
    from google.cloud import storage

    GCP_AVAILABLE = True
except ImportError:
    print("⚠️ Google Cloud Storage não disponível")
    GCP_AVAILABLE = False
from urllib.parse import quote

from .linkedin_cookies import LinkedInCookieManager


# Spark imports will be loaded only when needed
def _import_spark():
    """Import Spark only when needed to avoid dependency issues in offline mode"""
    import findspark

    findspark.init()
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, current_timestamp, from_json
    from pyspark.sql.types import ArrayType, BooleanType, IntegerType, StringType, StructField, StructType

    return (
        SparkSession,
        StructType,
        StructField,
        StringType,
        IntegerType,
        BooleanType,
        ArrayType,
        from_json,
        col,
        current_timestamp,
    )


# Load environment variables from project root .env file
import pathlib

project_root = pathlib.Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Set GCP credentials from environment

if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Configuration for LinkedIn scraping
LINKEDIN_CONFIG = {"base_url": "https://www.linkedin.com/jobs/search/", "location": "Brasil"}

# Kafka Configuration
KAFKA_CONFIG = {
    "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    "topic_name": "vagas_dados",
    "auto_offset_reset": "latest",
    "group_id": "vaga_linkedin_consumer_group",
}

# GCS Configuration for PySpark
GCS_CONFIG = {"bucket": "linkedin-dados-raw", "checkpoint_location": "gs://linkedin-dados-raw/spark-checkpoints/"}


def is_job_title_relevant(job_title, search_term, category):
    """
    Check if job title is relevant to the specific category.
    More flexible matching to capture relevant variations.
    """
    if not job_title:
        return False

    job_title_lower = job_title.lower()

    # More flexible matching for each category
    if category == "data_engineer":
        # Accept if contains any engineering/development related terms
        key_terms = [
            "engineer",
            "engenheiro",
            "developer",
            "desenvolvedor",
            "data",
            "dados",
            "software",
            "backend",
            "python",
            "java",
            "scala",
        ]
        return any(term in job_title_lower for term in key_terms)

    elif category == "data_analytics":
        # Accept if contains any analytics/analyst related terms
        key_terms = ["analyst", "analista", "analytics", "data", "dados", "business", "reporting", "insights", "bi"]
        return any(term in job_title_lower for term in key_terms)

    elif category == "digital_analytics":
        # Accept if contains digital/web/marketing analytics terms
        key_terms = ["analytics", "analista", "digital", "web", "marketing", "data", "dados", "metrics", "tracking"]
        return any(term in job_title_lower for term in key_terms)

    return True  # Default: accept job if no specific category filter


def upload_to_gcp_bucket(local_file_path, bucket_name, destination_blob_name):
    """
    Upload a file to GCP Cloud Storage bucket.
    """
    if not GCP_AVAILABLE:
        print("⚠️ GCP não disponível - dados salvos apenas localmente")
        return False

    try:
        # Initialize GCP client
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # Upload file
        blob.upload_from_filename(local_file_path)
        print(f"✅ Arquivo enviado para GCP: gs://{bucket_name}/{destination_blob_name}")
        return True

    except Exception as e:
        print(f"❌ Erro no upload para GCP: {e}")
        return False


def sync_data_to_gcp(data_dir, bucket_name="linkedin-dados-raw"):
    """
    Sync all extracted data files to GCP bucket with proper structure.
    """
    if not GCP_AVAILABLE:
        print("⚠️ GCP não disponível - dados permanecem apenas localmente")
        return False

    try:
        today_date = datetime.now().strftime("%Y-%m-%d")
        upload_count = 0

        # Walk through all data files
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if file.endswith(".jsonl"):
                    local_file_path = os.path.join(root, file)

                    # Extract category from path
                    relative_path = os.path.relpath(local_file_path, data_dir)
                    category = relative_path.split(os.sep)[0]  # data_engineer, data_analytics, etc.

                    # Create GCP path: category/date/filename
                    gcp_path = f"{category}/{today_date}/{file}"

                    # Upload to bucket
                    if upload_to_gcp_bucket(local_file_path, bucket_name, gcp_path):
                        upload_count += 1

        print(f"🚀 {upload_count} arquivos sincronizados com GCP bucket: {bucket_name}")
        return upload_count > 0

    except Exception as e:
        print(f"❌ Erro na sincronização GCP: {e}")
        return False


def setup_chrome_driver():
    """Setup Chrome driver with anti-detection measures and persistent session"""
    chrome_options = webdriver.ChromeOptions()

    # Basic setup
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # Rotate user agents to avoid detection
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

    # Enhanced anti-detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # Disable notifications and other distractions
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=chrome_options)

    # Enhanced anti-detection scripts
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")

    return driver


def linkedin_login(driver):
    """
    Perform LinkedIn login with multiple strategies to avoid 2FA
    1. Try loading saved cookies
    2. Check if session is already active
    3. Attempt login with credentials
    4. Save cookies after successful login
    """
    cookie_manager = LinkedInCookieManager()

    try:
        # Strategy 1: Try to load saved cookies first
        print("🍪 Tentando carregar cookies salvos...")
        if cookie_manager.load_cookies(driver):
            driver.get("https://www.linkedin.com/feed")
            time.sleep(3)

            if "feed" in driver.current_url or "/in/" in driver.current_url:
                print("✅ Login via cookies salvos bem-sucedido!")
                return True

        # Strategy 2: Check if we already have a valid session
        driver.get("https://www.linkedin.com/feed")
        time.sleep(3)

        if "feed" in driver.current_url or "/in/" in driver.current_url:
            print("✅ Sessão LinkedIn já ativa")
            cookie_manager.save_cookies(driver)  # Save for next time
            return True

        # Strategy 3: Try regular login
        linkedin_user = os.getenv("user")
        linkedin_password = os.getenv("senha")

        if not linkedin_user or not linkedin_password:
            print("❌ Credenciais do LinkedIn não encontradas no .env")
            print("💡 Configure as variáveis 'user' e 'senha' no arquivo .env")
            return False

        print("🔐 Fazendo login no LinkedIn...")
        driver.get("https://www.linkedin.com/login")
        time.sleep(3)

        # Fill login form
        try:
            email_field = driver.find_element(By.ID, "username")
            email_field.clear()
            email_field.send_keys(linkedin_user)

            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(linkedin_password)

            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()

            time.sleep(5)

        except Exception as e:
            print(f"❌ Erro ao preencher formulário de login: {e}")
            return False

        # 2FA está desabilitado - removido verificação desnecessária

        # Check if login was successful
        if "feed" in driver.current_url or "linkedin.com/in/" in driver.current_url:
            print("✅ Login realizado com sucesso!")
            cookie_manager.save_cookies(driver)  # Save cookies for future use
            return True

        # Final check after delay
        time.sleep(3)
        if "linkedin.com" in driver.current_url and "login" not in driver.current_url:
            print("✅ Login realizado com sucesso!")
            cookie_manager.save_cookies(driver)
            return True

        print("❌ Falha no login do LinkedIn")
        return False

    except Exception as e:
        print(f"❌ Erro durante login do LinkedIn: {str(e)}")
        return False


def extract_jobs_via_linkedin_scraping(search_term, max_results=50, category=None):
    """
    Extract jobs directly from LinkedIn using web scraping with authentication.
    """
    jobs = []

    try:
        print(f"🔗 Extraindo vagas do LinkedIn para '{search_term}'...")

        driver = setup_chrome_driver()
        if not driver:
            print("❌ Não foi possível inicializar o navegador")
            return jobs

        # First, login to LinkedIn
        if not linkedin_login(driver):
            print("❌ Não foi possível fazer login no LinkedIn")
            driver.quit()
            return jobs

        # Encode search term for URL
        encoded_search = quote(search_term)

        # LinkedIn Jobs search URL otimizada para Brasil
        # Parâmetros:
        # keywords: termo de busca
        # location: Brasil (código de país)
        # f_TPR=r259200: últimos 3 dias (259200 segundos = 3 * 24 * 60 * 60)
        # sortBy=DD: ordenar por data (mais recentes primeiro)
        # f_LF=f_AL: apenas vagas ativas
        # geoId=106057199: ID geográfico do Brasil no LinkedIn
        linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_search}&location=Brasil&geoId=106057199&f_TPR=r259200&f_LF=f_AL&sortBy=DD"

        print(f"🌐 Acessando busca de vagas: {linkedin_url}")
        driver.get(linkedin_url)

        # Wait for page to load
        time.sleep(5)

        # Enhanced job card detection with retry logic
        job_cards = []
        card_selectors = [
            ".job-search-card",
            ".base-card",
            ".base-search-card",
            ".jobs-search-results__list-item",
            ".scaffold-layout__list-item",
            '[data-entity-urn*="job"]',
        ]

        # Try multiple times with different strategies
        for attempt in range(3):
            for selector in card_selectors:
                try:
                    if attempt > 0:
                        # Wait longer on retry attempts
                        time.sleep(random.uniform(2, 4))

                    wait = WebDriverWait(driver, 15)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    job_cards = driver.find_elements(By.CSS_SELECTOR, selector)

                    if job_cards and len(job_cards) > 5:  # Ensure we have meaningful results
                        print(f"✅ Encontrados {len(job_cards)} elementos com seletor: {selector}")
                        break

                except Exception:
                    # Try scrolling to load more content
                    try:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(random.uniform(2, 4))

                        # Try a more aggressive scroll
                        for i in range(3):
                            driver.execute_script(f"window.scrollTo(0, {(i+1) * 1000});")
                            time.sleep(1)

                        job_cards = driver.find_elements(By.CSS_SELECTOR, selector)
                        if job_cards and len(job_cards) > 5:
                            print(f"✅ Após scroll (tentativa {attempt+1}): {len(job_cards)} vagas encontradas")
                            break
                    except Exception:  # noqa: E722
                        continue

            if job_cards and len(job_cards) > 5:
                break

            if attempt < 2:
                print(f"⚠️ Tentativa {attempt+1} falhou, tentando novamente...")
                time.sleep(random.uniform(3, 6))

        print(f"📡 LinkedIn encontrou {len(job_cards)} vagas para '{search_term}'")

        # Extract job data from found cards with anti-blocking measures
        processed = 0
        for card_index, card in enumerate(job_cards[:max_results], 1):
            try:
                processed = card_index

                # Random delay between jobs to avoid detection
                if processed > 1:
                    time.sleep(random.uniform(1, 3))

                # Get job title with improved selectors (LinkedIn frequently changes these)
                job_title = None
                title_selectors = [
                    ".base-search-card__title",
                    "h3 a",
                    "h3",
                    ".job-search-card__title",
                    ".base-card__title",
                    'a[data-control-name="job_search_job_title"]',
                    ".job-title-link",
                    '[data-test-id="job-title"]',
                    ".artdeco-entity-lockup__title",
                ]

                for selector in title_selectors:
                    try:
                        title_elements = card.find_elements(By.CSS_SELECTOR, selector)
                        if title_elements:
                            title_element = title_elements[0]
                            job_title = title_element.text.strip()
                            # Try multiple attributes to get title
                            if not job_title:
                                job_title = title_element.get_attribute("title")
                            if not job_title:
                                job_title = title_element.get_attribute("aria-label")
                            if not job_title:
                                job_title = title_element.get_attribute("innerText")
                            if not job_title:
                                job_title = title_element.get_attribute("textContent")
                            if job_title and len(job_title.strip()) > 2:
                                job_title = job_title.strip()
                                break
                    except Exception:
                        continue

                if not job_title:
                    print(f"⚠️  Vaga {processed}: título não encontrado")
                    continue

                # Apply flexible title filter (less restrictive)
                if not is_job_title_relevant(job_title, search_term, category):
                    print(f"⚠️  Vaga rejeitada: {job_title}")
                    continue

                # Get job URL
                job_url = None
                try:
                    url_element = card.find_element(By.CSS_SELECTOR, "h3 a")
                    job_url = url_element.get_attribute("hre")
                except Exception:  # noqa: E722
                    job_url = f"https://linkedin.com/jobs/search/{processed}"

                # Get company name with improved selectors
                company = "N/A"
                company_selectors = [
                    "h4 a",
                    ".base-search-card__subtitle",
                    ".job-search-card__subtitle-link",
                    ".base-card__subtitle",
                    'a[data-control-name="job_search_company_name"]',
                    ".company-name-link",
                    '[data-test-id="company-name"]',
                    ".base-search-card__subtitle a",  # Funciona!
                    ".base-search-card__subtitle",  # Funciona!
                ]

                for selector in company_selectors:
                    try:
                        company_element = card.find_element(By.CSS_SELECTOR, selector)
                        company = company_element.text.strip()
                        if company:
                            break
                    except Exception:  # noqa: E722
                        continue

                # Get location
                location = "Brasil"
                location_selectors = [".job-search-card__location", ".base-search-card__metadata span"]

                for selector in location_selectors:
                    try:
                        location_element = card.find_element(By.CSS_SELECTOR, selector)
                        location = location_element.text.strip()
                        if location and location != company:  # Avoid duplicating company name
                            break
                    except Exception:  # noqa: E722
                        continue

                # Extract description by clicking on job title link (opens full job page)
                description = "N/A"
                current_url = driver.current_url

                try:
                    # Find the job title link within the card
                    title_link_selectors = [
                        ".base-search-card__title a",
                        ".job-search-card__title a",
                        'a[data-control-name="job_search_job_title"]',
                        ".base-card__full-link",
                    ]

                    title_link = None
                    for selector in title_link_selectors:
                        try:
                            title_link = card.find_element(By.CSS_SELECTOR, selector)
                            if title_link:
                                break
                        except Exception:  # noqa: E722
                            continue

                    if title_link:
                        # Get the job URL
                        job_url = title_link.get_attribute("hre")

                        if job_url:
                            # Navigate to job page
                            driver.get(job_url)
                            time.sleep(3)  # Wait for page to load

                            # Extract description from full job page (individual page structure)
                            job_page_selectors = [
                                # Individual job page selectors (different from search results)
                                ".show-more-less-html__markup",
                                ".jobs-description .show-more-less-html__markup",
                                ".job-details-jobs-unified-top-card__job-description .show-more-less-html__markup",
                                ".jobs-unified-top-card__job-description .show-more-less-html__markup",
                                ".jobs-description",
                                ".job-details-jobs-unified-top-card__job-description",
                                ".jobs-unified-top-card__job-description",
                                # Fallback: get from body and extract relevant part
                                "body",
                            ]

                            for desc_selector in job_page_selectors:
                                try:
                                    desc_elements = driver.find_elements(By.CSS_SELECTOR, desc_selector)
                                    if desc_elements:
                                        desc_text = desc_elements[0].text.strip()

                                        # Special handling for body text (fallback)
                                        if desc_selector == "body" and len(desc_text) > 500:
                                            # Extract job description from body text
                                            lines = desc_text.split("\n")
                                            desc_started = False
                                            desc_lines = []

                                            for line in lines:
                                                line = line.strip()
                                                # Start capturing after job title or common phrases
                                                if not desc_started and any(
                                                    phrase in line.lower()
                                                    for phrase in [
                                                        "estamos em busca",
                                                        "sobre a",
                                                        "about the job",
                                                        "we are looking",
                                                        "buscamos",
                                                        "procuramos",
                                                        "oportunidade",
                                                    ]
                                                ):
                                                    desc_started = True
                                                    desc_lines.append(line)
                                                elif desc_started:
                                                    # Stop at common LinkedIn UI elements
                                                    if any(
                                                        stop in line.lower()
                                                        for stop in [
                                                            "candidatar",
                                                            "easy apply",
                                                            "salvar",
                                                            "save",
                                                            "reportar",
                                                            "report",
                                                        ]
                                                    ):
                                                        break
                                                    if line and len(line) > 10:
                                                        desc_lines.append(line)

                                            if desc_lines and len(" ".join(desc_lines)) > 100:
                                                description = " ".join(desc_lines)
                                                description = (
                                                    description[:1000] + "..."
                                                    if len(description) > 1000
                                                    else description
                                                )
                                                break

                                        # Regular description processing
                                        elif desc_text and len(desc_text) > 100:
                                            # Remove common LinkedIn artifacts
                                            lines = desc_text.split("\n")
                                            clean_lines = []

                                            for line in lines:
                                                line = line.strip()
                                                if line and len(line) > 10:
                                                    # Skip common LinkedIn UI text
                                                    skip_patterns = [
                                                        "see more",
                                                        "show less",
                                                        "easy apply",
                                                        "aplicar agora",
                                                        "sobre a vaga",
                                                        "about the job",
                                                        "candidatar",
                                                        "salvar",
                                                        "save",
                                                    ]
                                                    if not any(pattern in line.lower() for pattern in skip_patterns):
                                                        clean_lines.append(line)

                                            if clean_lines:
                                                description = " ".join(clean_lines)
                                                description = (
                                                    description[:1000] + "..."
                                                    if len(description) > 1000
                                                    else description
                                                )
                                                break
                                except Exception:
                                    continue

                            # Navigate back to search results
                            driver.get(current_url)
                            time.sleep(2)

                            # Re-find the cards since we navigated away
                            cards = driver.find_elements(By.CSS_SELECTOR, ".job-search-card")
                            if len(cards) <= card_index:
                                break  # Exit if we can't find our position

                except Exception:
                    # If navigation fails, return to search page
                    try:
                        driver.get(current_url)
                        time.sleep(2)
                    except Exception:  # noqa: E722
                        pass

                # Extract work modality (Remote, Hybrid, On-site) - usando título, localização e descrição
                work_modality = "N/A"
                try:
                    # Procura por indicadores no título, empresa, localização e descrição
                    available_text = (job_title + " " + company + " " + location + " " + description).lower()

                    if "remot" in available_text or "home office" in available_text or "remote" in available_text:
                        work_modality = "Remoto"
                    elif "híbrid" in available_text or "hybrid" in available_text:
                        work_modality = "Híbrido"
                    elif "presencial" in available_text or "on-site" in available_text:
                        work_modality = "Presencial"
                    else:
                        # Check job insights/metadata for work type info
                        job_insights = card.find_elements(
                            By.CSS_SELECTOR, ".job-search-card__job-insight, .job-search-card__job-benefit"
                        )
                        for insight in job_insights:
                            insight_text = insight.text.lower()
                            if "remot" in insight_text or "remote" in insight_text:
                                work_modality = "Remoto"
                                break
                            elif "híbrid" in insight_text or "hybrid" in insight_text:
                                work_modality = "Híbrido"
                                break
                            elif "presencial" in insight_text or "on-site" in insight_text:
                                work_modality = "Presencial"
                                break
                except Exception:  # noqa: E722
                    pass

                # Extract contract type - usando apenas título
                contract_type = "N/A"
                try:
                    title_text = job_title.lower()

                    if "estagiário" in title_text or "estágio" in title_text or "intern" in title_text:
                        contract_type = "Estágio"
                    elif "junior" in title_text or "júnior" in title_text or "trainee" in title_text:
                        contract_type = "Júnior"
                    elif "senior" in title_text or "sênior" in title_text or "sr." in title_text:
                        contract_type = "Sênior"
                    elif "pleno" in title_text or "mid" in title_text:
                        contract_type = "Pleno"
                    elif "freelanc" in title_text or "freela" in title_text:
                        contract_type = "Freelance"
                except Exception:  # noqa: E722
                    pass

                # Add job creation timestamp and unique identifier with today's date
                today_date = datetime.now().strftime("%Y-%m-%d")
                current_timestamp = datetime.now()

                job = {
                    "job_id": f"linkedin_{today_date}_{processed}_{hash(job_title + company) % 100000000:08x}",
                    "title": job_title,
                    "company": company,
                    "location": location,
                    "description": description,
                    "description_snippet": description[:200] + "..." if len(description) > 200 else description,
                    "description_length": len(description),
                    "url": job_url if job_url else f"https://linkedin.com/jobs/search/{processed}",
                    "posted_time": current_timestamp.isoformat(),
                    "posted_date": today_date,  # Always today for filtering
                    "extract_timestamp": current_timestamp.isoformat(),
                    "extract_date": today_date,  # Date for partitioning
                    "source": "linkedin_authenticated",
                    "search_term": search_term,
                    "category": category,
                    "location_country": "Brasil",
                    "has_company": bool(company),
                    "salary_min": None,
                    "salary_max": None,
                    "has_salary": False,
                    "work_modality": work_modality,
                    "contract_type": contract_type,
                    "is_new": True,  # Flag for new jobs (Kafka trigger)
                    "batch_id": f"{category}_{today_date}_{current_timestamp.strftime('%H%M%S')}",
                }

                jobs.append(job)
                print(f"✅ Vaga aceita: {job_title} ({company})")

            except Exception as e:
                print(f"⚠️  Erro ao processar vaga {processed}: {str(e)}")
                # On error, add small delay before continuing
                time.sleep(random.uniform(0.5, 1.5))
                continue

        driver.quit()

    except Exception as e:
        print(f"💥 Erro crítico na extração LinkedIn: {str(e)}")
        if "driver" in locals():
            driver.quit()

    print(f"✅ {len(jobs)} vagas válidas extraídas via LinkedIn autenticado")
    return jobs


def extract_jobs_via_adzuna(search_term, max_results=50, category=None):
    """
    Extract jobs using LinkedIn scraping (no fallback APIs).
    """
    # Use LinkedIn scraping as the primary method
    return extract_jobs_via_linkedin_scraping(search_term, max_results, category)


def extract_jobs_via_jsearch_fallback(search_term, max_results=50):
    """
    Extract jobs using LinkedIn scraping (no fallback APIs).
    """
    # Use LinkedIn scraping as the primary method
    return extract_jobs_via_linkedin_scraping(search_term, max_results)


def generate_mock_jobs(search_term, count=10):
    """
    Generate comprehensive mock job data with ALL possible fields for testing.
    """
    mock_companies = [
        "Tech Corp",
        "Data Solutions",
        "AI Startup",
        "Cloud Systems",
        "Analytics Pro",
        "Digital Labs",
        "Innovation Hub",
        "Future Tech",
        "Smart Data",
        "Growth Analytics",
    ]

    mock_locations = [
        "São Paulo, SP",
        "Rio de Janeiro, RJ",
        "Belo Horizonte, MG",
        "Porto Alegre, RS",
        "Recife, PE",
        "Remote, Brasil",
    ]

    jobs = []
    for i in range(count):
        # Generate comprehensive mock data with ALL possible fields
        job = {
            # Core standardized fields
            "job_title": f"{search_term} {'Sênior' if i % 3 == 0 else 'Pleno' if i % 3 == 1 else 'Junior'}",
            "company_name": mock_companies[i % len(mock_companies)],
            "location": mock_locations[i % len(mock_locations)],
            "posted_date": datetime.now().isoformat(),
            "job_url": f"https://linkedin.com/jobs/view/mock-{i}-{hash(search_term) % 10000}",
            "description_snippet": f"Vaga de {search_term} com foco em análise de dados, desenvolvimento de pipelines e visualização de insights...",
            # Extended mock fields (simulating ALL possible API fields)
            "job_id": f"mock_{datetime.now().strftime('%Y%m%d')}_{i:03d}",
            "employer_name": mock_companies[i % len(mock_companies)],
            "employer_logo": f"https://logo.company.com/{mock_companies[i % len(mock_companies)].lower().replace(' ', '')}.png",
            "employer_website": f"https://{mock_companies[i % len(mock_companies)].lower().replace(' ', '')}.com",
            "employer_company_type": "Technology" if i % 2 == 0 else "Startup",
            "job_publisher": "LinkedIn" if i % 3 == 0 else "Indeed",
            "job_employment_type": "FULLTIME" if i % 4 != 0 else "CONTRACTOR",
            "job_is_remote": i % 4 == 0,
            "job_posted_at_timestamp": int(datetime.now().timestamp()),
            "job_posted_at_datetime_utc": datetime.now().isoformat(),
            "job_city": mock_locations[i % len(mock_locations)].split(",")[0],
            "job_state": (
                mock_locations[i % len(mock_locations)].split(",")[-1].strip()
                if "," in mock_locations[i % len(mock_locations)]
                else ""
            ),
            "job_country": "BR",
            "job_latitude": -23.5505 + (i * 0.1),
            "job_longitude": -46.6333 + (i * 0.1),
            "job_benefits": ["Health Insurance", "Dental", "Remote Work", "Flexible Hours"][: (i % 4) + 1],
            "job_google_link": f"https://www.google.com/search?q={search_term.replace(' ', '+')}+{mock_companies[i % len(mock_companies)].replace(' ', '+')}",
            "job_offer_expiration_datetime_utc": (datetime.now().timestamp() + (30 * 24 * 3600)),  # 30 days
            "job_offer_expiration_timestamp": int(datetime.now().timestamp() + (30 * 24 * 3600)),
            "job_required_experience": {
                "no_experience_required": i % 5 == 0,
                "required_experience_in_months": (i % 4) * 12,
                "experience_mentioned": True,
                "experience_preferred": True,
            },
            "job_required_skills": ["Python", "SQL", "Data Analysis", "Machine Learning", "Statistics"][
                : ((i % 5) + 1)
            ],
            "job_required_education": {
                "postgraduate_degree": i % 6 == 0,
                "professional_certification": i % 4 == 0,
                "high_school": i % 10 == 0,
                "associates_degree": i % 8 == 0,
                "bachelors_degree": i % 3 != 0,
                "degree_mentioned": True,
                "degree_preferred": True,
                "professional_certification_mentioned": i % 5 == 0,
            },
            "job_experience_in_place_of_education": i % 7 == 0,
            "job_min_salary": 5000 + (i * 1000) if i % 3 == 0 else None,
            "job_max_salary": 10000 + (i * 1500) if i % 3 == 0 else None,
            "job_salary_currency": "BRL" if i % 3 == 0 else None,
            "job_salary_period": "YEAR" if i % 3 == 0 else None,
            "job_highlights": {
                "Qualifications": ["Bachelor's degree", "3+ years experience", "Python proficiency"],
                "Responsibilities": ["Data analysis", "Report generation", "Team collaboration"],
                "Benefits": ["Health insurance", "Remote work", "Professional development"],
            },
            "job_job_title": f"{search_term} {'Sênior' if i % 3 == 0 else 'Pleno' if i % 3 == 1 else 'Junior'}",
            "job_posting_language": "pt",
            "job_onet_soc": "15-1199.00",  # Data Scientists SOC code
            "job_onet_job_zone": "4",
            "job_naics_code": "541511",
            "job_naics_name": "Custom Computer Programming Services",
            "job_occupational_categories": ["15-1199.00"],
            "job_description": f"Descrição completa da vaga de {search_term}. Responsabilidades incluem análise de dados, desenvolvimento de modelos, criação de dashboards e colaboração com equipes multidisciplinares. Requisitos: experiência com Python, SQL, ferramentas de BI e conhecimento em estatística.",
            # Metadata
            "search_category": search_term.lower().replace(" ", "_"),
            "extracted_at": datetime.now().isoformat(),
            "data_source": "mock_fallback_complete",
            "raw_api_response": True,
            "api_response_complete": True,
            "total_fields_captured": "ALL_AVAILABLE",
        }
        jobs.append(job)

    return jobs


def setup_kafka_infrastructure():
    """
    Setup Kafka broker and create topic 'vagas_dados'.
    """
    try:
        print("🔧 Configurando infraestrutura Kafka...")

        # Create Kafka admin client
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_CONFIG["bootstrap_servers"], client_id="vaga_linkedin_admin"
        )

        # Create topic if it doesn't exist
        topic = NewTopic(name=KAFKA_CONFIG["topic_name"], num_partitions=3, replication_factor=1)

        try:
            admin_client.create_topics([topic])
            print(f"✅ Tópico '{KAFKA_CONFIG['topic_name']}' criado com sucesso")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"ℹ️  Tópico '{KAFKA_CONFIG['topic_name']}' já existe")
            else:
                print(f"⚠️  Erro ao criar tópico: {e}")

        return True

    except Exception as e:
        print(f"❌ Erro na configuração Kafka: {e}")
        return False


def create_kafka_producer():
    """
    Create Kafka producer for job data ingestion.
    """
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_CONFIG["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retries=3,
            batch_size=16384,
            linger_ms=10,
        )
        print("✅ Kafka Producer criado com sucesso")
        return producer
    except Exception as e:
        print(f"❌ Erro ao criar Kafka Producer: {e}")
        return None


def start_pyspark_streaming_consumer():
    """
    Start PySpark Structured Streaming job to consume from Kafka and write to GCS.
    """
    try:
        print("🚀 Iniciando PySpark Structured Streaming...")

        # Import Spark components only when needed
        (
            SparkSession,
            StructType,
            StructField,
            StringType,
            IntegerType,
            BooleanType,
            ArrayType,
            from_json,
            col,
            current_timestamp,
        ) = _import_spark()

        # Enhanced Spark configuration for robust streaming
        try:

            # Debug environment variables
            java_home = os.environ.get("JAVA_HOME")
            print(f"🔍 DEBUG - JAVA_HOME: {java_home}")

            if not java_home:
                print("⚠️  JAVA_HOME não configurado, configurando automaticamente...")
                os.environ["JAVA_HOME"] = "/usr/local/opt/openjdk@11"
                print(f"✅ JAVA_HOME configurado: {os.environ['JAVA_HOME']}")

            spark = (
                SparkSession.builder.appName("VagaLinkedInStreamingProcessor")
                .config(
                    "spark.jars.packages",
                    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.apache.kafka:kafka-clients:3.5.0",
                )
                .config("spark.sql.adaptive.enabled", "true")
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
                .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoints")
                .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
                .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")
                .config("spark.sql.streaming.stopGracefullyOnShutdown", "true")
                .config("spark.sql.streaming.kafka.bootstrap.servers", KAFKA_CONFIG["bootstrap_servers"])
                .config("spark.sql.streaming.kafka.maxOffsetsPerTrigger", "1000")
                .config("spark.sql.streaming.kafka.startingOffsets", "latest")
                .config("spark.sql.streaming.kafka.failOnDataLoss", "false")
                .config("spark.network.timeout", "300s")
                .config("spark.sql.execution.arrow.pyspark.enabled", "true")
                .master("local[*]")
                .getOrCreate()
            )

        except Exception as e:
            print(f"🔍 DEBUG - Erro detalhado: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            raise

        # Set log level to reduce noise
        spark.sparkContext.setLogLevel("WARN")

        # Define schema matching the actual producer output (from extract_jobs_via_linkedin_scraping)
        job_schema = StructType(
            [
                StructField("job_id", StringType(), True),
                StructField("title", StringType(), True),
                StructField("company", StringType(), True),
                StructField("location", StringType(), True),
                StructField("description", StringType(), True),
                StructField("description_snippet", StringType(), True),
                StructField("description_length", IntegerType(), True),
                StructField("url", StringType(), True),
                StructField("posted_time", StringType(), True),
                StructField("posted_date", StringType(), True),
                StructField("extract_timestamp", StringType(), True),
                StructField("extract_date", StringType(), True),
                StructField("source", StringType(), True),
                StructField("search_term", StringType(), True),
                StructField("category", StringType(), True),
                StructField("location_country", StringType(), True),
                StructField("has_company", BooleanType(), True),
                StructField("salary_min", IntegerType(), True),
                StructField("salary_max", IntegerType(), True),
                StructField("has_salary", BooleanType(), True),
                StructField("work_modality", StringType(), True),
                StructField("contract_type", StringType(), True),
                StructField("is_new", BooleanType(), True),
                StructField("batch_id", StringType(), True),
                StructField("type", StringType(), True),  # Added by producer
            ]
        )

        # Read from Kafka topic with enhanced options
        kafka_df = (
            spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", KAFKA_CONFIG["bootstrap_servers"])
            .option("subscribe", KAFKA_CONFIG["topic_name"])
            .option("startingOffsets", "latest")
            .option("failOnDataLoss", "false")
            .option("kafka.session.timeout.ms", "30000")
            .option("kafka.request.timeout.ms", "40000")
            .option("kafka.max.poll.records", "500")
            .load()
        )

        print("✅ Kafka stream configurado com sucesso")

        # Parse JSON value from Kafka with error handling
        parsed_df = kafka_df.select(
            from_json(col("value").cast("string"), job_schema).alias("data"),
            col("timestamp").alias("kafka_timestamp"),
            col("key").cast("string").alias("kafka_key"),
        ).select("data.*", "kafka_timestamp", "kafka_key")

        # Filter jobs by category and ensure data quality
        filtered_df = parsed_df.filter(
            (col("category").isin(["data_analytics", "data_engineer", "digital_analytics"]))
            & (col("extract_timestamp").isNotNull())
            & (col("title").isNotNull())
            & (col("company").isNotNull())
        )

        os.makedirs("streaming_output", exist_ok=True)

        # Create separate streaming queries for each job type with date partitioning
        job_types = ["data_engineer", "data_analytics", "digital_analytics"]
        queries = []
        today_date = datetime.now().strftime("%Y-%m-%d")

        for job_type in job_types:
            # Filter by job type and today's date only
            type_filtered_df = filtered_df.filter((col("category") == job_type) & (col("extract_date") == today_date))

            # Create checkpoint directory with date
            checkpoint_path = f"/tmp/checkpoints/{job_type}_{today_date}"
            os.makedirs(checkpoint_path, exist_ok=True)

            # Output path with date partitioning for better organization
            output_path = f"streaming_output/{job_type}/date={today_date}/"
            os.makedirs(output_path, exist_ok=True)

            query = (
                type_filtered_df.writeStream.format("json")
                .option("path", output_path)
                .option("checkpointLocation", checkpoint_path)
                .outputMode("append")
                .trigger(processingTime="30 seconds")
                .start()
            )

            queries.append(query)
            print(f"✅ Streaming iniciado para {job_type} - apenas dados de {today_date}")

        # Return the first query for monitoring (all will run in parallel)
        streaming_query = queries[0] if queries else None

        print("✅ PySpark Streaming iniciado - processando em tempo real")
        return streaming_query, spark

    except Exception as e:
        print(f"❌ Erro ao iniciar PySpark Streaming: {e}")
        return None, None


def produce_jobs_to_kafka(producer, jobs, job_type):
    """
    Send job data to Kafka topic with proper formatting.
    """
    try:
        messages_sent = 0
        for job in jobs:
            # Add job type for filtering in Spark
            job["type"] = job_type

            # Send to Kafka
            future = producer.send(KAFKA_CONFIG["topic_name"], key=job_type, value=job)

            # Wait for confirmation
            _record_metadata = future.get(timeout=10)  # noqa: F841
            messages_sent += 1

        producer.flush()
        print(f"✅ {messages_sent} mensagens de {job_type} enviadas para Kafka")
        return messages_sent

    except Exception as e:
        print(f"❌ Erro ao enviar para Kafka: {e}")
        return 0


def check_for_new_jobs(existing_jobs_path, new_jobs):
    """
    Check for new jobs that don't exist in storage - for Kafka real-time alerts.
    """
    try:
        existing_job_ids = set()

        # Load existing job IDs from today's files
        if os.path.exists(existing_jobs_path):
            for filename in os.listdir(existing_jobs_path):
                if filename.endswith(".json"):
                    filepath = os.path.join(existing_jobs_path, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                job = json.loads(line.strip())
                                existing_job_ids.add(job.get("job_id", ""))
                            except Exception:  # noqa: E722
                                continue

        # Find truly new jobs
        new_job_alerts = []
        for job in new_jobs:
            if job.get("job_id") not in existing_job_ids:
                new_job_alerts.append(job)

        return new_job_alerts

    except Exception as e:
        print(f"⚠️ Erro ao verificar vagas novas: {e}")
        return new_jobs  # Return all jobs if check fails


def run_extract_offline():
    """
    Extraction mode with append functionality and duplicate prevention.
    Uses LinkedIn scraping with date-based organization.
    """
    print("🔄 Iniciando extração em modo offline com append...")

    # Criar diretório de dados com data atual
    today_date = datetime.now().strftime("%Y-%m-%d")
    data_dir = f"data_extracts/{today_date}"
    os.makedirs(data_dir, exist_ok=True)

    # Categorias de busca
    search_categories = {
        "data_engineer": ["Data Engineer", "Engenheiro de Dados"],
        "data_analytics": ["Data Analytics", "Analista de Dados"],
        "digital_analytics": ["Digital Analytics", "Product Analytics", "Marketing Analytics"],
    }

    results = {}
    timestamp = today_date

    for category, search_terms in search_categories.items():
        print(f"\n📂 Extraindo categoria: {category.upper()}")
        category_jobs = []

        for search_term in search_terms:
            # Use LinkedIn scraping as the ONLY method
            jobs = extract_jobs_via_linkedin_scraping(search_term, max_results=30, category=category)
            category_jobs.extend(jobs)

        # Remover duplicatas
        unique_jobs = []
        seen_identifiers = set()
        for job in category_jobs:
            identifier = job.get("job_url", "") + job.get("job_id", "")
            if identifier and identifier not in seen_identifiers:
                unique_jobs.append(job)
                seen_identifiers.add(identifier)

        # Check for new jobs (for Kafka alerts)
        category_data_dir = os.path.join(data_dir, category)
        os.makedirs(category_data_dir, exist_ok=True)

        new_jobs_only = check_for_new_jobs(category_data_dir, unique_jobs)

        # Append to daily file instead of overwrite
        filename = f"{category}_{timestamp.replace('-', '')}.jsonl"  # Use JSONL for append
        filepath = os.path.join(category_data_dir, filename)

        # Append mode - add only new jobs
        with open(filepath, "a", encoding="utf-8") as f:
            for job in unique_jobs:
                f.write(json.dumps(job, ensure_ascii=False) + "\n")

        print(f"✅ {len(unique_jobs)} vagas processadas ({len(new_jobs_only)} novas): {filename}")

        # For Kafka: send alerts for new jobs only
        if new_jobs_only:
            results[category] = {"total": len(unique_jobs), "new": len(new_jobs_only), "jobs": new_jobs_only}
        else:
            results[category] = {"total": len(unique_jobs), "new": 0, "jobs": []}

        results[category] = {"count": len(unique_jobs), "file": filepath}

    # After all categories are processed, sync to GCP
    print("\n🔄 Sincronizando dados com GCP Cloud Storage...")
    sync_success = sync_data_to_gcp(data_dir)

    if sync_success:
        print("✅ Dados sincronizados com sucesso no bucket GCP!")
    else:
        print("⚠️ Dados salvos apenas localmente - verifique configuração GCP")

    total_jobs = sum(result["count"] for result in results.values())
    print(f"\n📊 Total extraído: {total_jobs} vagas")
    print(f"📂 Dados locais: {data_dir}")
    print("☁️ Bucket GCP: linkedin-dados-raw (se configurado)")

    return results


def run_extract(instructions=None):
    """
    Run real-time job extraction using Kafka + PySpark Streaming architecture.
    """
    print("🚀 Iniciando extração com Kafka + PySpark Streaming...")

    try:
        # Step 1: Setup Kafka infrastructure
        if not setup_kafka_infrastructure():
            print("❌ Falha na configuração Kafka - usando modo offline")
            return run_extract_offline()

        # Step 2: Create Kafka producer
        producer = create_kafka_producer()
        if not producer:
            print("❌ Falha na criação do Producer - usando modo offline")
            return run_extract_offline()

        # Step 3: Start PySpark Streaming consumer
        streaming_query, spark = start_pyspark_streaming_consumer()
        if not streaming_query:
            print("❌ Falha no PySpark Streaming - usando modo offline")
            return run_extract_offline()

        # Step 4: Extract and produce job data

        # Create data directory
        data_dir = "data_extracts"
        os.makedirs(data_dir, exist_ok=True)

        # Always use LinkedIn scraping as the primary method
        use_api = "linkedin"
        print("✅ Usando LinkedIn scraping autenticado como fonte primária.")

        # Define search categories with specific job titles only
        search_categories = {
            "data_engineer": ["Data Engineer", "Engenheiro de Dados"],
            "data_analytics": ["Data Analytics", "Analista de Dados"],
            "digital_analytics": ["Digital Analytics"],
        }

        # Create results structure as per extract_agente.md specification
        extraction_results = {}
        timestamp = datetime.now().strftime("%Y-%m-%d")

        for category, search_terms in search_categories.items():
            print(f"\n📂 Extraindo categoria: {category.upper()}")
            category_jobs = []

            # Extract jobs for each search term in the category
            for search_term in search_terms:
                # Use LinkedIn scraping as the ONLY method (with authentication)
                jobs = extract_jobs_via_linkedin_scraping(search_term, max_results=30, category=category)

                # No fallbacks - only LinkedIn scraping is used
                if not jobs:
                    print(f"⚠️  Nenhuma vaga encontrada via LinkedIn para '{search_term}'")

                category_jobs.extend(jobs)

                # Rate limiting between API calls
                time.sleep(1 if use_api == "adzuna" else 2)

            # Remove duplicates based on job_url and job_id
            unique_jobs = []
            seen_identifiers = set()
            for job in category_jobs:
                identifier = job.get("job_url", "") + job.get("job_id", "")
                if identifier and identifier not in seen_identifiers:
                    unique_jobs.append(job)
                    seen_identifiers.add(identifier)

            # Validate required fields as per extract_agente.md
            valid_jobs = []

            for job in unique_jobs:
                # Required validation: must have essential fields
                if not job.get("title") or not job.get("company"):
                    print(f"⚠️  Vaga rejeitada por campos faltantes: {job.get('title', 'N/A')}")
                    continue

                # Title relevance validation: only accept jobs matching category
                if not is_job_title_relevant(job.get("title"), search_term, category):
                    print(f"⚠️  Vaga rejeitada por título irrelevante: {job.get('title')}")
                    continue

                valid_jobs.append(job)

            # Save with exact naming convention from extract_agente.md
            category_filename = f"{category}_{timestamp.replace('-', '')}.json"
            category_file = os.path.join(data_dir, category_filename)

            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(valid_jobs, f, indent=2, ensure_ascii=False)

            print(f"✅ {category}: {len(valid_jobs)} vagas válidas salvas em {category_filename}")

            # Upload to GCP with EXACT structure from extract_agente.md
            gcp_storage_path = None
            try:
                result = subprocess.run(["gsutil", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    bucket_name = "linkedin-dados-raw"
                    # Exact path structure: gs://linkedin-dados-raw/data_engineer/2025-09-01/data_engineer_2025-09-01.json
                    gcp_storage_path = f"gs://{bucket_name}/{category}/{timestamp}/{category}_{timestamp}.json"

                    # Ensure directory exists in bucket
                    subprocess.run(["gsutil", "cp", category_file, gcp_storage_path], check=True)
                    print(f"✅ Dados enviados para GCP: {gcp_storage_path}")

                    # Verify file is not empty before confirming
                    if len(valid_jobs) == 0:
                        print(f"⚠️  Arquivo {category} está vazio!")
                else:
                    print("ℹ️  gsutil não disponível - dados salvos apenas localmente")
            except subprocess.CalledProcessError as e:
                print(f"❌ Erro no upload para GCP: {e}")

            # Store results in EXACT format from extract_agente.md
            extraction_results[category] = {
                "count": len(valid_jobs),
                "storage_path": gcp_storage_path or f"local:{category_file}",
            }

        # Generate final summary report matching extract_agente.md format
        total_jobs = sum(result["count"] for result in extraction_results.values())

        # Save detailed summary
        summary_data = {
            "extraction_date": timestamp,
            "total_jobs_extracted": total_jobs,
            "categories_processed": len(extraction_results),
            "extraction_results": extraction_results,
            "api_used": use_api,
            "extraction_metadata": {"extracted_at": datetime.now().isoformat(), "search_categories": search_categories},
        }

        summary_file = os.path.join(data_dir, f"extraction_summary_{timestamp.replace('-', '')}.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        # Print results in the exact format expected by extract_agente.md
        print(f"\n📊 RESUMO DA EXTRAÇÃO - {timestamp}")
        print("=" * 50)
        for category, data in extraction_results.items():
            print(f"📁 {category.upper()}: {data['count']} vagas")
            print(f"   💾 Path: {data['storage_path']}")
        print(f"\n🎯 TOTAL: {total_jobs} vagas extraídas")

        # Return structured response for control_agent validation
        return f"LinkedIn extraction completed: {total_jobs} jobs extracted across {len(extraction_results)} categories. Files saved with timestamp {timestamp}."

    except Exception as e:
        error_msg = f"Erro crítico na extração: {e}"
        print(f"❌ {error_msg}")
        return error_msg


if __name__ == "__main__":
    run_extract()
