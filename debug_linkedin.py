#!/usr/bin/env python3
"""
Debug LinkedIn scraping - check what's actually happening
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time


def debug_linkedin_access():
    """Debug LinkedIn access and check page content"""
    print("🔍 DEBUG: Verificando acesso ao LinkedIn...")

    # Setup Chrome with debugging
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    )

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Test LinkedIn jobs URL
        url = "https://www.linkedin.com/jobs/search/?keywords=Analista%20de%20Dados&location=Brasil&f_TPR=r604800&sortBy=DD"
        print(f"🌐 Acessando: {url}")

        driver.get(url)
        time.sleep(5)

        # Check page title and content
        print(f"📄 Título da página: {driver.title}")
        print(f"🌐 URL atual: {driver.current_url}")

        # Check if we're being redirected or blocked
        if "linkedin.com/jobs" not in driver.current_url:
            print("⚠️ REDIRECIONAMENTO DETECTADO!")
            print(f"URL redirecionada: {driver.current_url}")

        # Try to find job cards with different selectors
        selectors_to_test = [
            "[data-job-id]",
            ".job-search-card",
            ".jobs-search__results-list li",
            ".job-result-card",
            '[class*="job"]',
            "li[data-occludable-job-id]",
        ]

        for selector in selectors_to_test:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"✅ Seletor '{selector}': {len(elements)} elementos encontrados")
                if elements:
                    break
            except Exception as e:
                print(f"❌ Seletor '{selector}': erro - {str(e)}")

        # Check page source for clues
        page_source = driver.page_source[:1000]
        print(f"\n📝 Primeiros 1000 caracteres da página:")
        print(page_source)

        # Check for common LinkedIn blocking patterns
        blocking_keywords = [
            "authwall",
            "sign in",
            "login",
            "blocked",
            "captcha",
            "Please sign in",
            "Join LinkedIn",
            "authgate",
        ]

        for keyword in blocking_keywords:
            if keyword.lower() in driver.page_source.lower():
                print(f"🚫 BLOQUEIO DETECTADO: '{keyword}' encontrado na página")

        driver.quit()

    except Exception as e:
        print(f"💥 Erro: {str(e)}")
        if "driver" in locals():
            driver.quit()


if __name__ == "__main__":
    debug_linkedin_access()
