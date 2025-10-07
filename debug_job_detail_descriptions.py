#!/usr/bin/env python3
"""
Debug avançado: clica nos job cards para verificar se descrições aparecem
baseado na análise do usuário sobre spans com parágrafos por frase
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

from agents.extract_agent.linkedin_cookies import LinkedInCookieManager


def debug_job_detail_descriptions():
    """Debug clicando em job cards para ver descrições detalhadas"""

    print("🔍 DEBUG: DESCRIÇÕES AO CLICAR EM JOB CARDS")
    print("=" * 60)

    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Create unique profile directory
    profile_dir = f"/tmp/chrome_profile_detail_{int(time.time())}"
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")

    driver = webdriver.Chrome(options=chrome_options)
    cookie_manager = LinkedInCookieManager()

    try:
        # Login
        driver.get("https://www.linkedin.com/login")

        if cookie_manager.load_cookies(driver):
            driver.refresh()
            time.sleep(3)
            print("🍪 Cookies carregados com sucesso")

        # Go to job search
        linkedin_url = "https://www.linkedin.com/jobs/search/?keywords=Data%20Engineer&location=Brasil&geoId=106057199&f_TPR=r259200&f_LF=f_AL&sortBy=DD"
        driver.get(linkedin_url)
        time.sleep(5)

        # Find job cards
        cards = driver.find_elements(By.CSS_SELECTOR, ".job-search-card")
        print(f"✅ Encontrados {len(cards)} job cards")

        if not cards:
            print("❌ Nenhum job card encontrado")
            return

        # Test clicking on first few job cards
        for i, card in enumerate(cards[:3], 1):
            print(f"\n🔹 TESTANDO JOB CARD {i}:")
            print("=" * 40)

            try:
                # Get title for reference
                title_elem = card.find_element(By.CSS_SELECTOR, ".base-search-card__title")
                title = title_elem.text.strip()
                print(f"📝 Título: {title}")

                # Scroll to card and click
                actions = ActionChains(driver)
                actions.move_to_element(card).perform()
                time.sleep(1)

                # Click on the card
                card.click()
                time.sleep(3)  # Wait for detail panel to load

                print("👆 Clicou no job card, procurando descrições...")

                # Look for description in detail panel/sidebar
                detail_selectors = [
                    # Based on user's analysis: spans with paragraphs for each sentence
                    ".jobs-search__job-details span p",
                    ".job-details span p",
                    ".jobs-description span p",
                    ".jobs-box__html-content span p",
                    # General detail containers
                    ".jobs-search__job-details .jobs-description__content",
                    ".job-details .jobs-description__content",
                    ".jobs-box__html-content",
                    ".jobs-description-content",
                    # Spans in detail area
                    ".jobs-search__job-details span",
                    ".job-details span",
                    ".jobs-box__html-content span",
                    # Broader selectors for detail area
                    ".jobs-search__job-details",
                    ".job-details",
                    ".jobs-description",
                    # Check for any content area with meaningful text
                    "[data-job-id] .jobs-description__content",
                    ".jobs-details-top-card__content",
                ]

                found_content = []

                for j, selector in enumerate(detail_selectors, 1):
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            texts = []
                            for elem in elements:
                                text = elem.text.strip()
                                if text and len(text) > 30:  # Meaningful content
                                    texts.append(text)

                            if texts:
                                print(f"✅ {selector}")
                                max_text = max(texts, key=len)
                                print(
                                    f"   └─ Conteúdo ({len(max_text)} chars): {max_text[:200]}{'...' if len(max_text) > 200 else ''}"
                                )

                                found_content.append({"selector": selector, "text": max_text, "length": len(max_text)})
                            else:
                                print(f"⚠️ {selector} (elementos sem texto significativo)")
                        else:
                            print(f"❌ {selector} (não encontrado)")
                    except Exception as e:
                        print(f"💥 {selector} (erro: {str(e)[:30]})")

                if found_content:
                    print(f"\n🎯 Encontrados {len(found_content)} seletores com conteúdo!")
                    # Show best candidate (longest text)
                    best = max(found_content, key=lambda x: x["length"])
                    print(f"🏆 Melhor: {best['selector']} ({best['length']} chars)")
                    print(f"📝 Texto: {best['text'][:300]}{'...' if len(best['text']) > 300 else ''}")
                else:
                    print("❌ Nenhuma descrição encontrada após clicar")

            except Exception as e:
                print(f"💥 Erro ao processar job card {i}: {e}")

            print("-" * 60)

    except Exception as e:
        print(f"💥 Erro durante debug: {e}")

    finally:
        driver.quit()
        print(f"\n✅ Debug concluído")


if __name__ == "__main__":
    debug_job_detail_descriptions()
