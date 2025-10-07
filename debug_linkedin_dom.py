#!/usr/bin/env python3
"""
Debug LinkedIn DOM structure when authenticated to find correct selectors
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from urllib.parse import quote

# Import from agents
from agents.extract_agent.extract_agent import linkedin_login, setup_chrome_driver


def debug_linkedin_dom():
    """Debug LinkedIn job cards DOM structure after login"""
    print("🔍 DEBUG: Analisando estrutura DOM do LinkedIn após login...")

    try:
        driver = setup_chrome_driver()
        if not driver:
            print("❌ Não foi possível inicializar o navegador")
            return

        # Login first
        if not linkedin_login(driver):
            print("❌ Falha no login")
            driver.quit()
            return

        # Go to jobs search
        search_term = "Analista de Dados"
        encoded_search = quote(search_term)
        linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_search}&location=Brasil&geoId=106057199&f_TPR=r259200&f_LF=f_AL&sortBy=DD"

        print(f"🌐 Acessando: {linkedin_url}")
        driver.get(linkedin_url)
        time.sleep(5)

        # Find job cards
        job_cards = driver.find_elements(By.CSS_SELECTOR, ".job-search-card")
        print(f"📊 Encontrados {len(job_cards)} job cards")

        if job_cards:
            # Analyze first few job cards
            for i, card in enumerate(job_cards[:3]):
                print(f"\n🔍 ANALISANDO CARD {i+1}:")
                print("-" * 40)

                # Get the outer HTML of the card to see structure
                try:
                    card_html = card.get_attribute("outerHTML")[:1000]  # First 1000 chars
                    print(f"HTML Structure:\n{card_html}")
                    print("-" * 40)
                except:
                    print("❌ Erro ao obter HTML do card")

                # Try various selectors for title
                title_selectors = [
                    'h3 a span[aria-hidden="true"]',
                    "h3 a span:not([aria-hidden])",
                    "h3 a span",
                    "h3 a",
                    ".job-search-card__title a",
                    ".job-search-card__title",
                    "[data-job-title]",
                    'a[data-control-name="job_search_job_title"]',
                    ".base-search-card__title a",
                    ".base-search-card__title",
                    "h3",
                ]

                print("🎯 TESTANDO SELETORES DE TÍTULO:")
                for selector in title_selectors:
                    try:
                        elements = card.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            text = elements[0].text.strip()
                            print(f"✅ '{selector}': '{text}'" if text else f"⚠️  '{selector}': ELEMENTO SEM TEXTO")
                        else:
                            print(f"❌ '{selector}': não encontrado")
                    except Exception as e:
                        print(f"💥 '{selector}': erro - {str(e)}")

                # Try company selectors
                print("\n🏢 TESTANDO SELETORES DE EMPRESA:")
                company_selectors = [
                    'h4 a span[aria-hidden="true"]',
                    "h4 a span",
                    "h4 a",
                    ".job-search-card__subtitle a",
                    ".job-search-card__subtitle",
                    "[data-job-company-name]",
                    ".base-search-card__subtitle a",
                    ".base-search-card__subtitle",
                ]

                for selector in company_selectors:
                    try:
                        elements = card.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            text = elements[0].text.strip()
                            print(f"✅ '{selector}': '{text}'" if text else f"⚠️  '{selector}': ELEMENTO SEM TEXTO")
                        else:
                            print(f"❌ '{selector}': não encontrado")
                    except Exception as e:
                        print(f"💥 '{selector}': erro - {str(e)}")

                # Try description selectors
                print("\n📄 TESTANDO SELETORES DE DESCRIÇÃO:")
                desc_selectors = [
                    ".base-search-card__summary",
                    ".job-search-card__snippet",
                    ".base-card__summary",
                    ".job-search-card__summary",
                    "p[data-max-lines]",
                    ".job-search-card p",
                    ".base-search-card p",
                    "[data-job-description]",
                    ".job-search-card__description",
                ]

                for selector in desc_selectors:
                    try:
                        elements = card.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            text = elements[0].text.strip()
                            print(
                                f"✅ '{selector}': '{text[:100]}{'...' if len(text) > 100 else ''}'"
                                if text
                                else f"⚠️  '{selector}': ELEMENTO SEM TEXTO"
                            )
                        else:
                            print(f"❌ '{selector}': não encontrado")
                    except Exception as e:
                        print(f"💥 '{selector}': erro - {str(e)}")

                print("\n" + "=" * 50)

        # Take a screenshot for manual inspection
        driver.save_screenshot("linkedin_jobs_debug.png")
        print("📸 Screenshot salvo como 'linkedin_jobs_debug.png'")

        driver.quit()

    except Exception as e:
        print(f"💥 Erro: {str(e)}")
        if "driver" in locals():
            driver.quit()


if __name__ == "__main__":
    debug_linkedin_dom()
