#!/usr/bin/env python3
"""
Debug completo do fluxo de extração de descrições
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

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

from agents.extract_agent.linkedin_cookies import LinkedInCookieManager


def debug_complete_extraction_flow():
    """Debug completo do fluxo de extração"""

    print("🔍 DEBUG COMPLETO: FLUXO DE EXTRAÇÃO DE DESCRIÇÕES")
    print("=" * 70)

    # Setup Chrome with more options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    profile_dir = f"/tmp/chrome_profile_complete_{int(time.time())}"
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    cookie_manager = LinkedInCookieManager()

    try:
        # Login
        driver.get("https://www.linkedin.com/login")
        if cookie_manager.load_cookies(driver):
            driver.refresh()
            time.sleep(3)
            print("🍪 Login realizado com sucesso")

        # Navigate to job search
        linkedin_url = "https://www.linkedin.com/jobs/search/?keywords=Data%20Engineer&location=Brasil&geoId=106057199&f_TPR=r259200&f_LF=f_AL&sortBy=DD"
        driver.get(linkedin_url)
        time.sleep(5)

        # Find job cards
        cards = driver.find_elements(By.CSS_SELECTOR, ".job-search-card")
        print(f"✅ Encontrados {len(cards)} job cards")

        if not cards:
            print("❌ Nenhum job card encontrado")
            return

        # Test first card
        card = cards[0]

        # Get basic info
        try:
            title_elem = card.find_element(By.CSS_SELECTOR, ".base-search-card__title")
            title = title_elem.text.strip()
            print(f"📝 Testando vaga: {title}")
        except:
            print("⚠️ Título não encontrado")
            return

        print("\n🔄 PASSO 1: ESTADO ANTES DO CLIQUE")
        print("-" * 50)

        # Check existing panels before click
        existing_panels = driver.find_elements(By.CSS_SELECTOR, ".jobs-search__job-details")
        print(f"Painéis existentes: {len(existing_panels)}")

        if existing_panels:
            existing_text = existing_panels[0].text.strip()[:100]
            print(f"Texto no painel existente: {existing_text}...")

        print("\n🔄 PASSO 2: CLICANDO NO JOB CARD")
        print("-" * 50)

        # Scroll to element
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
        time.sleep(1)

        # Click using JavaScript to avoid interception
        print("👆 Executando clique via JavaScript...")
        driver.execute_script("arguments[0].click();", card)

        print("\n🔄 PASSO 3: AGUARDANDO CARREGAMENTO DO PAINEL")
        print("-" * 50)

        # Wait for panel to appear with different strategies
        for wait_seconds in [1, 2, 3, 5]:
            time.sleep(1)

            print(f"\n⏱️ Após {wait_seconds}s do clique:")

            # Check for various panel elements
            panels = driver.find_elements(By.CSS_SELECTOR, ".jobs-search__job-details")
            print(f"  📋 .jobs-search__job-details: {len(panels)}")

            desc_containers = driver.find_elements(By.CSS_SELECTOR, ".jobs-description__container")
            print(f"  📋 .jobs-description__container: {len(desc_containers)}")

            desc_content = driver.find_elements(By.CSS_SELECTOR, ".jobs-description__content")
            print(f"  📋 .jobs-description__content: {len(desc_content)}")

            html_content = driver.find_elements(By.CSS_SELECTOR, ".jobs-box__html-content")
            print(f"  📋 .jobs-box__html-content: {len(html_content)}")

            # If we have content, show sample
            if desc_content:
                sample_text = desc_content[0].text.strip()
                print(f"  📝 Amostra de conteúdo ({len(sample_text)} chars): {sample_text[:150]}...")
                break
            elif panels:
                sample_text = panels[0].text.strip()
                print(f"  📝 Amostra do painel ({len(sample_text)} chars): {sample_text[:150]}...")

        print(f"\n🔄 PASSO 4: TESTANDO TODOS OS SELETORES POSSÍVEIS")
        print("-" * 50)

        # Test all possible selectors based on user's analysis
        test_selectors = [
            # Based on user's DOM analysis
            ".jobs-description__content .jobs-box__html-content",
            ".jobs-description__content",
            ".jobs-description__container .jobs-description__content",
            "article.jobs-description__container .jobs-description__content",
            ".jobs-box--fadein .jobs-description__content",
            ".jobs-search__job-details .jobs-description__content",
            ".jobs-details__main-content .jobs-description__content",
            ".jobs-box--fadein .jobs-box__html-content",
            ".jobs-search__job-details",
            # Additional selectors to try
            ".jobs-search__job-details .jobs-box__html-content",
            ".job-details-jobs-unified-top-card__content",
            ".jobs-details-top-card__content-container",
            "[data-job-id] .jobs-description__content",
            # Broad selectors
            '[class*="jobs-description"]',
            '[class*="job-details"]',
        ]

        found_descriptions = []

        for i, selector in enumerate(test_selectors, 1):
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for j, elem in enumerate(elements):
                        text = elem.text.strip()
                        if text and len(text) > 100:  # Meaningful content
                            print(f"✅ {i:2d}. {selector} (elem {j+1})")
                            print(f"     └─ Texto ({len(text)} chars): {text[:200]}...")

                            found_descriptions.append(
                                {"selector": selector, "element_index": j, "text": text, "length": len(text)}
                            )
                        else:
                            print(f"⚠️ {i:2d}. {selector} (elem {j+1}) - texto insuficiente: {text[:50]}")
                else:
                    print(f"❌ {i:2d}. {selector} - não encontrado")
            except Exception as e:
                print(f"💥 {i:2d}. {selector} - erro: {str(e)[:50]}")

        print(f"\n📊 RESUMO FINAL:")
        print("=" * 50)
        print(f"🎯 Total de seletores com conteúdo: {len(found_descriptions)}")

        if found_descriptions:
            # Sort by length (longer descriptions are better)
            best_descriptions = sorted(found_descriptions, key=lambda x: x["length"], reverse=True)

            print(f"\n🏆 MELHORES CANDIDATOS:")
            for i, desc in enumerate(best_descriptions[:3], 1):
                print(f"{i}. {desc['selector']} (elemento {desc['element_index']}) - {desc['length']} chars")
                print(f"   📝 {desc['text'][:300]}...")
                print()

            # Show the best selector implementation
            best = best_descriptions[0]
            print(f"💡 IMPLEMENTAR:")
            print(f"   Seletor: {best['selector']}")
            print(f"   Elemento: {best['element_index']}")
        else:
            print("❌ Nenhuma descrição encontrada")
            print("💡 Possíveis causas:")
            print("   - Clique não carregou painel")
            print("   - LinkedIn mudou estrutura DOM")
            print("   - Seletores incorretos")

    except Exception as e:
        print(f"💥 Erro durante debug: {e}")

    finally:
        print(f"\n✅ Pressione Enter para fechar o browser...")
        input()
        driver.quit()


if __name__ == "__main__":
    debug_complete_extraction_flow()
