#!/usr/bin/env python3
"""
Debug específico para verificar o que acontece após clicar no job card
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

from agents.extract_agent.linkedin_cookies import LinkedInCookieManager

def debug_click_capture():
    """Debug detalhado do processo de clique e captura"""
    
    print("🔍 DEBUG: PROCESSO DE CLIQUE E CAPTURA")
    print("=" * 60)
    
    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    profile_dir = f"/tmp/chrome_profile_click_{int(time.time())}"
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")
    
    driver = webdriver.Chrome(options=chrome_options)
    cookie_manager = LinkedInCookieManager()
    
    try:
        # Login
        driver.get("https://www.linkedin.com/login")
        
        if cookie_manager.load_cookies(driver):
            driver.refresh()
            time.sleep(3)
            print("🍪 Login realizado")
        
        # Go to job search
        linkedin_url = "https://www.linkedin.com/jobs/search/?keywords=Data%20Engineer&location=Brasil&geoId=106057199&f_TPR=r259200&f_LF=f_AL&sortBy=DD"
        driver.get(linkedin_url)
        time.sleep(5)
        
        # Find first job card
        cards = driver.find_elements(By.CSS_SELECTOR, '.job-search-card')
        if not cards:
            print("❌ Nenhum job card encontrado")
            return
            
        card = cards[0]
        print(f"✅ Primeira vaga encontrada")
        
        # Get title
        try:
            title = card.find_element(By.CSS_SELECTOR, '.base-search-card__title').text.strip()
            print(f"📝 Título: {title}")
        except:
            print("⚠️ Título não encontrado")
        
        print("\n🔄 ANTES DO CLIQUE:")
        print("Verificando se painel de detalhes já existe...")
        existing_details = driver.find_elements(By.CSS_SELECTOR, '.jobs-search__job-details')
        print(f"Painéis existentes: {len(existing_details)}")
        
        # Scroll and click
        print("\n👆 CLICANDO NO JOB CARD:")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
        time.sleep(1)
        
        card.click()
        print("✅ Clique executado")
        
        # Wait and check what appears
        for wait_time in [1, 2, 3, 5]:
            print(f"\n⏱️ APÓS {wait_time}s DO CLIQUE:")
            
            # Check for detail panels
            detail_panels = driver.find_elements(By.CSS_SELECTOR, '.jobs-search__job-details')
            print(f"Painéis de detalhes: {len(detail_panels)}")
            
            job_details = driver.find_elements(By.CSS_SELECTOR, '.job-details')  
            print(f"Job details: {len(job_details)}")
            
            description_content = driver.find_elements(By.CSS_SELECTOR, '.jobs-description__content')
            print(f"Description content: {len(description_content)}")
            
            html_content = driver.find_elements(By.CSS_SELECTOR, '.jobs-box__html-content')
            print(f"HTML content: {len(html_content)}")
            
            # Try to get any text from these areas
            if detail_panels:
                text = detail_panels[0].text.strip()[:200]
                print(f"📝 Texto do painel: {text}...")
            
            if wait_time < 5:
                time.sleep(wait_time - (wait_time - 1) if wait_time > 1 else 1)
        
        print(f"\n🔍 TESTANDO TODOS OS SELETORES:")
        test_selectors = [
            '.jobs-search__job-details .jobs-description__content',
            '.jobs-search__job-details',
            '.job-details .jobs-description__content',
            '.jobs-box__html-content',
            '.jobs-description-content',
            '[data-job-id] .jobs-description__content'
        ]
        
        for selector in test_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                text = elements[0].text.strip()
                if len(text) > 50:
                    print(f"✅ {selector}: {text[:100]}...")
                else:
                    print(f"⚠️ {selector}: {text}")
            else:
                print(f"❌ {selector}: não encontrado")
        
    except Exception as e:
        print(f"💥 Erro: {e}")
    
    finally:
        input("Pressione Enter para fechar o browser...")
        driver.quit()

if __name__ == "__main__":
    debug_click_capture()
