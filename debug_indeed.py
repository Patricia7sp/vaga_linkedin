#!/usr/bin/env python3
"""
Debug Indeed scraping - check what's actually happening
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def debug_indeed_access():
    """Debug Indeed access and check page content"""
    print("🔍 DEBUG: Verificando acesso ao Indeed...")
    
    # Setup Chrome with debugging
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Test Indeed jobs URL
        url = "https://br.indeed.com/jobs?q=Analista%20de%20Dados&l=Brasil&sort=date&fromage=14"
        print(f"🌐 Acessando: {url}")
        
        driver.get(url)
        time.sleep(5)
        
        # Check page title and content
        print(f"📄 Título da página: {driver.title}")
        print(f"🌐 URL atual: {driver.current_url}")
        
        # Try to find job cards with different selectors
        selectors_to_test = [
            '[data-jk]',
            '.job_seen_beacon',
            '.slider_container .slider_item',
            '.jobsearch-result',
            '.result',
            '[data-testid="job-title"]',
            'h2[data-testid="job-title"] a span'
        ]
        
        for selector in selectors_to_test:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"✅ Seletor '{selector}': {len(elements)} elementos encontrados")
                if elements and len(elements) > 0:
                    # Try to get text from first element
                    try:
                        first_text = elements[0].text[:100] if elements[0].text else "SEM TEXTO"
                        print(f"   Primeiro elemento: {first_text}")
                    except:
                        print(f"   Primeiro elemento: ERRO AO OBTER TEXTO")
            except Exception as e:
                print(f"❌ Seletor '{selector}': erro - {str(e)}")
        
        # Check page source for clues
        page_source = driver.page_source[:2000]
        print(f"\n📝 Primeiros 2000 caracteres da página:")
        print(page_source)
        
        # Check for common blocking patterns
        blocking_keywords = [
            'blocked', 'captcha', 'robot', 'automation', 'security check',
            'suspicious activity', 'Please verify', 'Access Denied'
        ]
        
        for keyword in blocking_keywords:
            if keyword.lower() in driver.page_source.lower():
                print(f"🚫 POSSÍVEL BLOQUEIO: '{keyword}' encontrado na página")
        
        driver.quit()
        
    except Exception as e:
        print(f"💥 Erro: {str(e)}")
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    debug_indeed_access()
