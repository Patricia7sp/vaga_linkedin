#!/usr/bin/env python3
"""
Extract Agent: Extração de vagas LinkedIn com persistência em Cloud Storage.
Suporte opcional ao Kafka foi desabilitado por padrão para reduzir custos.
"""

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

try:
    from kafka import KafkaProducer
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import NoBrokersAvailable

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducer = None  # type: ignore
    KafkaAdminClient = None  # type: ignore
    NewTopic = None  # type: ignore
    NoBrokersAvailable = Exception  # type: ignore
import base64
import random

# Import Google Cloud Secret Manager
try:
    from google.cloud import secretmanager

    SECRET_MANAGER_AVAILABLE = True
    print("✅ Google Cloud Secret Manager disponível no Extract Agent")
except ImportError:
    print("⚠️  Google Cloud Secret Manager não disponível. Usando variáveis de ambiente.")
    SECRET_MANAGER_AVAILABLE = False


def access_secret_version(secret_name):
    """Acessa secret do GCP Secret Manager"""
    try:
        if not SECRET_MANAGER_AVAILABLE:
            return os.getenv(secret_name.replace("-", "_").upper())

        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT") or "vaga-linkedin"
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        return payload

    except Exception as e:
        print(f"❌ Erro ao acessar secret {secret_name}: {e}")
        return os.getenv(secret_name.replace("-", "_").upper())


import json
import os
import random
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
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
import tempfile
import uuid
from urllib.parse import quote

from bs4 import BeautifulSoup

from .linkedin_cookies import LinkedInCookieManager

# Import RapidAPI Hybrid Extractor (RapidAPI + Selenium fallback)
try:
    from .extract_agent_hybrid import extract_jobs_hybrid

    RAPIDAPI_HYBRID_AVAILABLE = True
    print("✅ RapidAPI Hybrid Extractor disponível (RapidAPI + Selenium fallback)")
except ImportError as e:
    RAPIDAPI_HYBRID_AVAILABLE = False
    print(f"⚠️ RapidAPI Hybrid não disponível: {e}. Usando apenas Selenium.")


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
import os

if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Configuration for LinkedIn scraping
LINKEDIN_CONFIG = {"base_url": "https://www.linkedin.com/jobs/search/", "location": "Worldwide"}  # Global extraction

# Kafka Configuration with Pub/Sub Kafka API support (opcional)

ENABLE_KAFKA = os.getenv("ENABLE_KAFKA", "false").lower() == "true"


def _resolve_ssl_cafile_path(value: str | None) -> str | None:
    """Resolve SSL CA file path, accepting direct paths, PEM text, or base64."""
    if not value:
        return None

    value = value.strip()
    if os.path.isfile(value):
        return value

    pem_bytes: bytes | None = None

    if value.startswith("-----BEGIN"):
        pem_bytes = value.encode("utf-8")
    else:
        try:
            decoded = base64.b64decode(value, validate=True)
            if decoded:
                pem_bytes = decoded
        except Exception:
            pem_bytes = None

    if pem_bytes:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        tmp.write(pem_bytes)
        tmp.flush()
        tmp.close()
        print(f"📄 Certificado SSL Kafka salvo em {tmp.name}")
        return tmp.name

    # Fallback: return original string (assume accessible path)
    return value


def _build_kafka_security_kwargs(kafka_config: dict) -> dict:
    """Build security kwargs for kafka-python clients based on configuration."""
    kwargs: dict = {}

    if kafka_config.get("security_protocol"):
        kwargs["security_protocol"] = kafka_config["security_protocol"]
    if kafka_config.get("sasl_mechanism"):
        kwargs["sasl_mechanism"] = kafka_config["sasl_mechanism"]
    if kafka_config.get("sasl_plain_username"):
        kwargs["sasl_plain_username"] = kafka_config["sasl_plain_username"]
    if kafka_config.get("sasl_plain_password"):
        kwargs["sasl_plain_password"] = kafka_config["sasl_plain_password"]
    if kafka_config.get("ssl_cafile_path"):
        kwargs["ssl_cafile"] = kafka_config["ssl_cafile_path"]
        kwargs.setdefault("ssl_check_hostname", True)

    return kwargs


def load_kafka_config():
    """Load Kafka configuration supporting Pub/Sub Kafka API (SASL/TLS)."""

    def _get_config(env_key: str, secret_name: str | None = None, default: str | None = None) -> str | None:
        value = os.getenv(env_key)
        if value:
            return value
        if secret_name:
            secret_value = access_secret_version(secret_name)
            if secret_value:
                return secret_value
        return default

    bootstrap = _get_config("KAFKA_BOOTSTRAP_SERVERS", "kafka-bootstrap-servers", "localhost:9092")
    topic_name = _get_config("KAFKA_TOPIC_NAME", "kafka-topic-name", "vagas_dados")
    group_id = _get_config("KAFKA_CONSUMER_GROUP", "kafka-consumer-group", "vaga_linkedin_consumer_group")
    auto_offset_reset = _get_config("KAFKA_AUTO_OFFSET_RESET", None, "latest")

    security_protocol = _get_config("KAFKA_SECURITY_PROTOCOL", "kafka-security-protocol", "PLAINTEXT")
    sasl_mechanism = _get_config("KAFKA_SASL_MECHANISM", "kafka-sasl-mechanism")
    sasl_username = _get_config("KAFKA_SASL_USERNAME", "kafka-sasl-username")
    sasl_password = _get_config("KAFKA_SASL_PASSWORD", "kafka-sasl-password")
    ssl_cafile = _get_config("KAFKA_SSL_CAFILE", "kafka-ssl-cafile")

    allow_admin = os.getenv("KAFKA_ALLOW_TOPIC_ADMIN", "false").lower() == "true"

    kafka_config = {
        "bootstrap_servers": bootstrap,
        "topic_name": topic_name,
        "auto_offset_reset": auto_offset_reset or "latest",
        "group_id": group_id or "vaga_linkedin_consumer_group",
        "security_protocol": security_protocol or "PLAINTEXT",
        "sasl_mechanism": sasl_mechanism,
        "sasl_plain_username": sasl_username,
        "sasl_plain_password": sasl_password,
        "ssl_cafile": ssl_cafile,
        "allow_topic_admin": allow_admin,
    }

    kafka_config["ssl_cafile_path"] = _resolve_ssl_cafile_path(ssl_cafile)

    print("🔧 Config Kafka carregada:")
    print(f"   • bootstrap_servers={kafka_config['bootstrap_servers']}")
    print(f"   • topic_name={kafka_config['topic_name']}")
    print(f"   • security_protocol={kafka_config['security_protocol']}")
    print(f"   • sasl_mechanism={kafka_config['sasl_mechanism'] or 'N/A'}")
    print(f"   • allow_topic_admin={kafka_config['allow_topic_admin']}")

    return kafka_config


KAFKA_CONFIG = load_kafka_config() if (ENABLE_KAFKA and KAFKA_AVAILABLE) else {}


def build_spark_kafka_options(kafka_config: dict) -> dict:
    """Build Spark Kafka option overrides for security protocols."""
    options: dict = {}

    sec_protocol = kafka_config.get("security_protocol")
    if sec_protocol:
        options["kafka.security.protocol"] = sec_protocol

    sasl_mechanism = kafka_config.get("sasl_mechanism")
    if sasl_mechanism:
        options["kafka.sasl.mechanism"] = sasl_mechanism

    username = kafka_config.get("sasl_plain_username")
    password = kafka_config.get("sasl_plain_password")
    if username and password:
        jaas = f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{username}" password="{password}";'
        options["kafka.sasl.jaas.config"] = jaas

    ssl_cafile = kafka_config.get("ssl_cafile_path")
    if ssl_cafile:
        options["kafka.ssl.truststore.location"] = ssl_cafile
        options["kafka.ssl.endpoint.identification.algorithm"] = "https"

    return options


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
    """Setup Chrome driver with ENHANCED headless configuration for Cloud Run containers"""
    chrome_options = webdriver.ChromeOptions()

    # ENHANCED: Cloud Run container compatibility
    chrome_options.add_argument("--headless=new")  # Usar novo modo headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")

    # ENHANCED: Container-specific settings
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=4096")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Acelerar carregamento
    # NOTE: JavaScript é necessário para LinkedIn - não desabilitar

    # ENHANCED: Realistic user agents with rotation
    user_agents = [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

    # ENHANCED: Anti-detection for headless
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")

    # ENHANCED: Performance and stability
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "profile.default_content_setting_values.media_stream": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # ENHANCED: Container-specific binary path detection
    chrome_binary_paths = [
        "/usr/bin/chromium",  # Container padrão
        "/usr/bin/chromium-browser",  # Debian/Ubuntu container
        "/usr/bin/google-chrome",  # Google Chrome container
        "/usr/bin/google-chrome-stable",
    ]

    for binary_path in chrome_binary_paths:
        if os.path.exists(binary_path):
            chrome_options.binary_location = binary_path
            print(f"🔍 Chrome binary encontrado: {binary_path}")
            break

    try:
        # ENHANCED: Service configuration for containers
        from selenium.webdriver.chrome.service import Service

        chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
        if not os.path.exists(chromedriver_path):
            raise FileNotFoundError(f"ChromeDriver não encontrado em {chromedriver_path}")

        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # ENHANCED: Anti-detection scripts (mesmo em headless)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script(
            "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})"
        )

        # ENHANCED: Verify driver is working
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)

        print("✅ Chrome headless driver configurado com sucesso para container")
        return driver

    except Exception as e:
        print(f"❌ Erro ao configurar Chrome driver: {e}")
        # Fallback: try without Service (older behaviour)
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("✅ Chrome driver configurado com fallback sem Service")
            return driver
        except Exception as e2:
            print(f"❌ Fallback também falhou: {e2}")
            return None


def linkedin_login(driver, max_retries=3):
    """
    ENHANCED: Perform LinkedIn login with retry logic and multiple strategies
    1. Try loading saved cookies from GCS
    2. Check if session is already active
    3. Attempt login with credentials (with retries)
    4. Save cookies after successful login to GCS
    """
    cookie_manager = LinkedInCookieManager()

    for attempt in range(max_retries):
        try:
            print(f"🔄 Tentativa de login {attempt + 1}/{max_retries}")

            # Strategy 1: Try to load saved cookies first (from GCS)
            print("🍪 Tentando carregar cookies salvos do GCS...")
            if cookie_manager.load_cookies(driver):
                driver.get("https://www.linkedin.com/feed")
                time.sleep(5)  # Aumentado para containers

                # ENHANCED: Multiple URL checks
                current_url = driver.current_url.lower()
                if any(keyword in current_url for keyword in ["feed", "/in/", "linkedin.com/in", "mynetwork"]):
                    print("✅ Login via cookies salvos bem-sucedido!")
                    return True

            # Strategy 2: Check if we already have a valid session
            print("🔍 Verificando sessão ativa...")
            driver.get("https://www.linkedin.com/feed")
            time.sleep(5)

            current_url = driver.current_url.lower()
            if any(keyword in current_url for keyword in ["feed", "/in/", "linkedin.com/in", "mynetwork"]):
                print("✅ Sessão LinkedIn já ativa")
                cookie_manager.save_cookies(driver)  # Save to GCS for next time
                return True

            # Strategy 3: Try regular login with enhanced credentials from Secret Manager
            print("🔐 Carregando credenciais LinkedIn do Secret Manager...")
            linkedin_user = access_secret_version("linkedin-email")
            linkedin_password = access_secret_version("linkedin-password")

            if not linkedin_user or not linkedin_password:
                print("❌ Credenciais do LinkedIn não encontradas")
                print("💡 Configure LINKEDIN_EMAIL e LINKEDIN_PASSWORD nas secrets")
                return False

            print("🔐 Fazendo login no LinkedIn...")
            driver.get("https://www.linkedin.com/login")
            time.sleep(5)

            # ENHANCED: Fill login form with better selectors
            try:
                # Wait for login form to load
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.support.ui import WebDriverWait

                wait = WebDriverWait(driver, 15)

                # Find email field
                email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
                email_field.clear()
                email_field.send_keys(linkedin_user)

                # Find password field
                password_field = driver.find_element(By.ID, "password")
                password_field.clear()
                password_field.send_keys(linkedin_password)

                # Find and click login button
                login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                login_button.click()

                print("📝 Formulário de login preenchido")
                time.sleep(8)  # Aumentado para containers

            except Exception as e:
                print(f"❌ Erro ao preencher formulário de login: {e}")
                if attempt < max_retries - 1:
                    print(f"🔄 Tentando novamente em 10 segundos...")
                    time.sleep(10)
                    continue
                return False

            # ENHANCED: Check if login was successful with multiple verifications
            current_url = driver.current_url.lower()

            # Check for successful login indicators
            success_indicators = ["feed", "/in/", "linkedin.com/in", "mynetwork", "dashboard"]
            if any(indicator in current_url for indicator in success_indicators):
                print("✅ Login realizado com sucesso!")
                cookie_manager.save_cookies(driver)  # Save to GCS for future use
                return True

            # Check for potential blocks or challenges
            if any(
                block_keyword in current_url for block_keyword in ["challenge", "blocked", "security", "checkpoint"]
            ):
                print("⚠️ LinkedIn detectou atividade suspeita - usando fallback")
                if attempt < max_retries - 1:
                    time.sleep(30)  # Wait longer before retry
                    continue

            # Final check after delay
            time.sleep(5)
            current_url = driver.current_url.lower()
            if "linkedin.com" in current_url and "login" not in current_url:
                print("✅ Login realizado com sucesso (verificação final)!")
                cookie_manager.save_cookies(driver)
                return True

            print(f"⚠️ Tentativa {attempt + 1} falhou. URL atual: {driver.current_url}")

            if attempt < max_retries - 1:
                print(f"🔄 Aguardando antes da próxima tentativa...")
                time.sleep(15)  # Wait between retries

        except Exception as e:
            print(f"❌ Erro durante tentativa {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(10)
                continue

    print("❌ Todas as tentativas de login falharam")
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

        # LinkedIn Jobs search URL otimizada para extração global
        # Parâmetros:
        # keywords: termo de busca
        # location: Worldwide (sem restrição geográfica)
        # f_TPR=r1728000: últimos 20 dias (1728000 segundos = 20 * 24 * 60 * 60) - CORRIGIDO
        # sortBy=DD: ordenar por data (mais recentes primeiro)
        # f_LF=f_AL: apenas vagas ativas
        # Removido geoId para permitir vagas globais
        linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_search}&location=Worldwide&f_TPR=r1728000&f_LF=f_AL&sortBy=DD"

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

                except Exception as e:
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
                    except:
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

                # Get job title with UPDATED selectors (LinkedIn mudou estrutura)
                job_title = None
                title_selectors = [
                    # ENHANCED 2025: Mais seletores com base em estrutura atual
                    "h3.base-search-card__title a span[title]",
                    'h3.base-search-card__title a span[aria-hidden="true"]',
                    "h3.base-search-card__title a span",
                    "h3.base-search-card__title a",
                    "h3.base-search-card__title",
                    ".base-search-card__title a span[title]",
                    '.base-search-card__title a span[aria-hidden="true"]',
                    ".base-search-card__title a span",
                    ".base-search-card__title a",
                    ".base-search-card__title",
                    ".job-search-card__title",
                    ".job-card-list__title",
                    ".job-card-container__title",
                    "a.job-card-list__title",
                    "a.job-card-container__link",
                    ".artdeco-entity-lockup__title",
                    '[data-test-id="job-card-title"]',
                    # Fallbacks robustos
                    "h3 a span[title]",
                    'h3 a span[aria-hidden="true"]',
                    "h3 a span",
                    "h3 a",
                    "h3",
                    ".job-search-card__title",
                    ".base-card__title",
                    'a[data-control-name="job_search_job_title"]',
                    'a[data-tracking-control-name="public_jobs_jserp-result_search-card"]',
                    ".job-title-link",
                    '[data-test-id="job-title"]',
                    ".artdeco-entity-lockup__title",
                    # Seletores genéricos como último recurso
                    'a[href*="/jobs/view/"]',
                    'a[href*="linkedin.com/jobs"]',
                ]

                # ENHANCED: Método robusto para extração de título
                for selector in title_selectors:
                    try:
                        title_elements = card.find_elements(By.CSS_SELECTOR, selector)
                        for title_element in title_elements:
                            # Método 1: Texto direto
                            job_title = title_element.text.strip()
                            if job_title and len(job_title) > 3:
                                break

                            # Método 2: Atributos específicos
                            for attr in ["title", "aria-label", "data-title"]:
                                job_title = title_element.get_attribute(attr)
                                if job_title and len(job_title.strip()) > 3:
                                    job_title = job_title.strip()
                                    break

                            if job_title:
                                break

                            # Método 3: JavaScript execution para casos complexos
                            try:
                                job_title = driver.execute_script(
                                    "return arguments[0].innerText || arguments[0].textContent || '';", title_element
                                ).strip()
                                if job_title and len(job_title) > 3:
                                    break
                            except:
                                pass

                            # Método 4: Buscar dentro de elementos filhos
                            try:
                                child_elements = title_element.find_elements(By.CSS_SELECTOR, "span, a, strong, em")
                                for child in child_elements:
                                    child_text = child.text.strip()
                                    if child_text and len(child_text) > 3 and not child_text.lower().startswith("http"):
                                        job_title = child_text
                                        break
                                if job_title:
                                    break
                            except:
                                pass

                        if job_title and len(job_title.strip()) > 3:
                            job_title = job_title.strip()
                            break

                    except Exception as e:
                        continue

                if not job_title:
                    try:
                        outer_html = card.get_attribute("outerHTML")
                        if outer_html:
                            soup = BeautifulSoup(outer_html, "html.parser")
                            title_candidates = [
                                soup.select_one("a.job-card-list__title"),
                                soup.select_one("span.job-card-list__title"),
                                soup.select_one("h3.base-search-card__title"),
                                soup.select_one("a.base-card__full-link"),
                                soup.select_one("a.job-search-card__title"),
                            ]
                            for candidate in title_candidates:
                                if candidate and candidate.get_text(strip=True):
                                    job_title = candidate.get_text(strip=True)
                                    break
                    except Exception:
                        pass

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
                    job_url = url_element.get_attribute("href")
                except:
                    job_url = f"https://linkedin.com/jobs/search/{processed}"

                # Get company name with improved selectors
                company = "N/A"
                company_selectors = [
                    # ENHANCED: Seletores mais específicos para empresa
                    "h4.base-search-card__subtitle a span[title]",
                    "h4.base-search-card__subtitle a span",
                    "h4.base-search-card__subtitle a",
                    "h4.base-search-card__subtitle",
                    ".base-search-card__subtitle a span[title]",
                    ".base-search-card__subtitle a span",
                    ".base-search-card__subtitle a",
                    ".base-search-card__subtitle",
                    "h4 a span[title]",
                    "h4 a span",
                    "h4 a",
                    "h4",
                    ".job-search-card__subtitle-link",
                    ".base-card__subtitle",
                    'a[data-control-name="job_search_company_name"]',
                    'a[data-tracking-control-name="public_jobs_jserp-result_job-search-card-subtitle"]',
                    ".company-name-link",
                    '[data-test-id="company-name"]',
                    # Fallbacks
                    ".job-card-container__company-name",
                    ".job-card__company-name",
                ]

                for selector in company_selectors:
                    try:
                        company_element = card.find_element(By.CSS_SELECTOR, selector)
                        company = company_element.text.strip()
                        if company:
                            break
                    except:
                        continue

                # Get location (now global)
                location = "Global"
                location_selectors = [".job-search-card__location", ".base-search-card__metadata span"]

                for selector in location_selectors:
                    try:
                        location_element = card.find_element(By.CSS_SELECTOR, selector)
                        location = location_element.text.strip()
                        if location and location != company:  # Avoid duplicating company name
                            break
                    except:
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
                        except:
                            continue

                    if title_link:
                        # Get the job URL
                        job_url = title_link.get_attribute("href")

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

                except Exception as e:
                    # If navigation fails, return to search page
                    try:
                        driver.get(current_url)
                        time.sleep(2)
                    except:
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
                except:
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
                except:
                    pass

                # Define today_date first
                today_date = datetime.now().strftime("%Y-%m-%d")

                # Extract real posted date from LinkedIn
                real_posted_date = today_date  # Default fallback
                try:
                    # Try to find posted date in the card
                    posted_date_selectors = [
                        ".job-search-card__listdate",
                        ".base-search-card__metadata time",
                        "time[datetime]",
                        ".job-posting-date",
                    ]

                    for date_selector in posted_date_selectors:
                        try:
                            date_element = card.find_element(By.CSS_SELECTOR, date_selector)
                            date_text = date_element.text.strip() or date_element.get_attribute("datetime")

                            if date_text:
                                # Parse various LinkedIn date formats
                                if "hour" in date_text.lower() or "hora" in date_text.lower():
                                    real_posted_date = today_date
                                elif "day" in date_text.lower() or "dia" in date_text.lower():
                                    days_ago = 1
                                    if any(char.isdigit() for char in date_text):
                                        days_ago = int("".join(filter(str.isdigit, date_text))) or 1
                                    posted_dt = datetime.now() - timedelta(days=days_ago)
                                    real_posted_date = posted_dt.strftime("%Y-%m-%d")
                                elif "week" in date_text.lower() or "semana" in date_text.lower():
                                    weeks_ago = 1
                                    if any(char.isdigit() for char in date_text):
                                        weeks_ago = int("".join(filter(str.isdigit, date_text))) or 1
                                    posted_dt = datetime.now() - timedelta(weeks=weeks_ago)
                                    real_posted_date = posted_dt.strftime("%Y-%m-%d")
                                break
                        except:
                            continue
                except:
                    pass

                # Generate consistent job_id based on content, not extraction date
                current_timestamp = datetime.now()

                # FIXED: Use job content for stable job_id
                job_content_hash = hash(f"{job_title}_{company}_{location}") % 100000000
                job_id = f"linkedin_{job_content_hash:08x}"

                job = {
                    "job_id": job_id,  # FIXED: Stable ID based on job content
                    "title": job_title,
                    "company": company,
                    "location": location,
                    "description": description,
                    "description_snippet": description[:200] + "..." if len(description) > 200 else description,
                    "description_length": len(description),
                    "url": job_url if job_url else f"https://linkedin.com/jobs/search/{processed}",
                    "posted_time": current_timestamp.isoformat(),
                    "posted_date": real_posted_date,  # FIXED: Real posted date from LinkedIn
                    "extract_timestamp": current_timestamp.isoformat(),
                    "extract_date": today_date,  # Date for partitioning (extraction date)
                    "source": "linkedin_authenticated",
                    "search_term": search_term,
                    "category": category,
                    "location_country": "Global",
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
        "New York, NY",
        "London, UK",
        "Berlin, Germany",
        "Toronto, Canada",
        "Sydney, Australia",
        "Singapore",
        "Amsterdam, Netherlands",
        "Remote, Worldwide",
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
    if not KAFKA_CONFIG:
        return False

    try:
        print("🔧 Configurando infraestrutura Kafka...")

        if not KAFKA_CONFIG.get("allow_topic_admin"):
            print("ℹ️  Admin Kafka desabilitado (KAFKA_ALLOW_TOPIC_ADMIN=false). Pulando criação de tópicos.")
            return True

        # Create Kafka admin client
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_CONFIG["bootstrap_servers"],
            client_id="vaga_linkedin_admin",
            **_build_kafka_security_kwargs(KAFKA_CONFIG),
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

    except NoBrokersAvailable as e:
        print(f"⚠️  Kafka indisponível ({e}). Entrando em modo offline.")
        return False
    except Exception as e:
        print(f"❌ Erro na configuração Kafka: {e}")
        return False


def create_kafka_producer():
    """
    Create Kafka producer for job data ingestion.
    """
    if not KAFKA_CONFIG:
        return None

    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_CONFIG["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retries=3,
            batch_size=16384,
            linger_ms=10,
            **_build_kafka_security_kwargs(KAFKA_CONFIG),
        )
        print("✅ Kafka Producer criado com sucesso")
        return producer
    except NoBrokersAvailable as e:
        print(f"⚠️  Kafka indisponível ({e}). Producer não será criado (modo offline).")
        return None
    except Exception as e:
        print(f"❌ Erro ao criar Kafka Producer: {e}")
        return None


def start_pyspark_streaming_consumer():
    """
    Start PySpark Structured Streaming job to consume from Kafka and write to GCS.
    """
    if not KAFKA_CONFIG:
        return None, None

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
            import os

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

        import os

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
    if not KAFKA_CONFIG or not producer:
        return 0

    try:
        messages_sent = 0
        for job in jobs:
            # Add job type for filtering in Spark
            job["type"] = job_type

            # Send to Kafka
            future = producer.send(KAFKA_CONFIG["topic_name"], key=job_type, value=job)

            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            messages_sent += 1

        producer.flush()
        print(f"✅ {messages_sent} mensagens de {job_type} enviadas para Kafka")
        return messages_sent

    except Exception as e:
        print(f"❌ Erro ao enviar para Kafka: {e}")
        return 0


def check_for_new_jobs(category_path, new_jobs):
    """
    FIXED: Check for new jobs by comparing against ALL historical job IDs in GCS bucket.
    Returns only jobs that haven't been seen before across all time.
    """
    try:
        existing_job_ids = set()
        bucket_name = "linkedin-dados-raw"
        category_name = os.path.basename(category_path)

        print(f"🔍 Verificando vagas novas para categoria: {category_name}")

        # FIXED: Load from ALL historical files in GCS bucket for this category
        try:
            # Use gsutil to list ALL files for this category in the bucket
            result = subprocess.run(
                ["gsutil", "ls", f"gs://{bucket_name}/{category_name}/**/*.json*"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                gcs_files = result.stdout.strip().split("\n")
                print(f"📁 Encontrados {len(gcs_files)} arquivos históricos no GCS")

                for gcs_file in gcs_files:
                    if gcs_file.strip():  # Skip empty lines
                        try:
                            # Download and read each historical file
                            temp_result = subprocess.run(
                                ["gsutil", "cat", gcs_file.strip()], capture_output=True, text=True, timeout=15
                            )

                            if temp_result.returncode == 0:
                                content = temp_result.stdout
                                # Handle both JSON and JSONL formats
                                if content.strip():
                                    try:
                                        # Try as JSON array first
                                        jobs_data = json.loads(content)
                                        if isinstance(jobs_data, list):
                                            for job in jobs_data:
                                                job_id = job.get("job_id")
                                                if job_id:
                                                    existing_job_ids.add(job_id)
                                    except json.JSONDecodeError:
                                        # Try as JSONL (line by line)
                                        for line in content.strip().split("\n"):
                                            if line.strip():
                                                try:
                                                    job = json.loads(line.strip())
                                                    job_id = job.get("job_id")
                                                    if job_id:
                                                        existing_job_ids.add(job_id)
                                                except:
                                                    continue
                        except subprocess.TimeoutExpired:
                            print(f"⚠️ Timeout ao ler arquivo: {gcs_file}")
                            continue
                        except Exception as e:
                            print(f"⚠️ Erro ao processar arquivo {gcs_file}: {e}")
                            continue

        except Exception as e:
            print(f"⚠️ Erro ao acessar GCS, verificando arquivos locais: {e}")

        # Fallback: Check local files if GCS fails
        if len(existing_job_ids) == 0:
            print("📂 Verificando arquivos locais...")
            data_extracts_dir = "data_extracts"
            if os.path.exists(data_extracts_dir):
                for date_dir in os.listdir(data_extracts_dir):
                    date_path = os.path.join(data_extracts_dir, date_dir)
                    if os.path.isdir(date_path):
                        category_dir = os.path.join(date_path, category_name)
                        if os.path.exists(category_dir):
                            for filename in os.listdir(category_dir):
                                if filename.endswith((".json", ".jsonl")):
                                    filepath = os.path.join(category_dir, filename)
                                    try:
                                        with open(filepath, "r", encoding="utf-8") as f:
                                            content = f.read()
                                            # Handle both JSON and JSONL
                                            try:
                                                jobs_data = json.loads(content)
                                                if isinstance(jobs_data, list):
                                                    for job in jobs_data:
                                                        job_id = job.get("job_id")
                                                        if job_id:
                                                            existing_job_ids.add(job_id)
                                            except json.JSONDecodeError:
                                                # Try JSONL
                                                for line in content.strip().split("\n"):
                                                    if line.strip():
                                                        try:
                                                            job = json.loads(line.strip())
                                                            job_id = job.get("job_id")
                                                            if job_id:
                                                                existing_job_ids.add(job_id)
                                                        except:
                                                            continue
                                    except Exception as e:
                                        print(f"⚠️ Erro ao ler arquivo local {filepath}: {e}")
                                        continue

        print(f"📊 Base histórica carregada: {len(existing_job_ids)} job_ids únicos")

        # Find truly new jobs
        new_job_alerts = []
        for job in new_jobs:
            job_id = job.get("job_id")
            if job_id and job_id not in existing_job_ids:
                new_job_alerts.append(job)

        print(f"🆕 Vagas novas identificadas: {len(new_job_alerts)} de {len(new_jobs)} extraídas")

        return new_job_alerts

    except Exception as e:
        print(f"⚠️ Erro ao verificar vagas novas: {e}")
        print("🔄 Retornando todas as vagas como novas (fallback)")
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
            # Use Hybrid Extractor: RapidAPI (primary) + Selenium (fallback)
            if RAPIDAPI_HYBRID_AVAILABLE:
                print(f"🔄 Usando extração híbrida: RapidAPI (primário) + Selenium (fallback)")
                jobs = extract_jobs_hybrid(
                    search_term=search_term, location="Brazil", max_results=30, category=category
                )
            else:
                # Fallback para Selenium puro se híbrido não disponível
                print(f"🌐 Usando apenas Selenium (RapidAPI não disponível)")
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
    print(f"\n🔄 Sincronizando dados com GCP Cloud Storage...")
    sync_success = sync_data_to_gcp(data_dir)

    if sync_success:
        print(f"✅ Dados sincronizados com sucesso no bucket GCP!")
    else:
        print(f"⚠️ Dados salvos apenas localmente - verifique configuração GCP")

    total_jobs = sum(result["count"] for result in results.values())
    print(f"\n📊 Total extraído: {total_jobs} vagas")
    print(f"📂 Dados locais: {data_dir}")
    print(f"☁️ Bucket GCP: linkedin-dados-raw (se configurado)")

    return results


def run_extract(instructions=None):
    """
    Executa extração principal. Usa Kafka somente se ENABLE_KAFKA=true e biblioteca instalada.
    """
    if not ENABLE_KAFKA or not KAFKA_AVAILABLE:
        print("ℹ️ Kafka desabilitado ou biblioteca indisponível. Executando modo GCS-only.")
        return run_extract_offline()

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
        results = {}

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
                # Use Hybrid Extractor: RapidAPI (primary) + Selenium (fallback)
                if RAPIDAPI_HYBRID_AVAILABLE:
                    print(f"🔄 Usando extração híbrida: RapidAPI (primário) + Selenium (fallback)")
                    jobs = extract_jobs_hybrid(
                        search_term=search_term, location="Brazil", max_results=30, category=category
                    )
                else:
                    # Fallback para Selenium puro se híbrido não disponível
                    print(f"🌐 Usando apenas Selenium (RapidAPI não disponível)")
                    jobs = extract_jobs_via_linkedin_scraping(search_term, max_results=30, category=category)

                if not jobs:
                    print(f"⚠️  Nenhuma vaga encontrada para '{search_term}'")

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
            required_fields = ["job_title", "company_name", "location", "posted_date", "job_url", "description_snippet"]

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
