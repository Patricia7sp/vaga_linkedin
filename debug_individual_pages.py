#!/usr/bin/env python3
"""
Debug específico para navegação para páginas individuais de vagas
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

def debug_individual_page_navigation():
    """Debug navegação para páginas individuais"""
    
    print("🔍 DEBUG: NAVEGAÇÃO PARA PÁGINAS INDIVIDUAIS")
    print("=" * 60)
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    profile_dir = f"/tmp/chrome_profile_nav_{int(time.time())}"
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
        search_url = "https://www.linkedin.com/jobs/search/?keywords=Data%20Engineer&location=Brasil&geoId=106057199&f_TPR=r259200&f_LF=f_AL&sortBy=DD"
        driver.get(search_url)
        time.sleep(5)
        print(f"📍 Na página de busca: {driver.current_url}")
        
        # Find job cards
        cards = driver.find_elements(By.CSS_SELECTOR, '.job-search-card')
        print(f"✅ Encontrados {len(cards)} job cards")
        
        if not cards:
            print("❌ Nenhum job card encontrado")
            return
            
        # Test first card
        card = cards[0]
        
        # Get title
        try:
            title_elem = card.find_element(By.CSS_SELECTOR, '.base-search-card__title')
            title = title_elem.text.strip()
            print(f"📝 Testando vaga: {title}")
        except:
            print("⚠️ Título não encontrado")
            return
        
        print("\n🔍 PROCURANDO LINK DO TÍTULO:")
        print("-" * 40)
        
        # Test title link selectors
        title_link_selectors = [
            '.base-search-card__title a',
            '.job-search-card__title a', 
            'a[data-control-name="job_search_job_title"]',
            '.base-card__full-link',
            'h3 a',
            'a[href*="/view/"]'
        ]
        
        title_link = None
        for i, selector in enumerate(title_link_selectors, 1):
            try:
                elements = card.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    title_link = elements[0]
                    href = title_link.get_attribute('href')
                    print(f"✅ {i}. {selector}: {href}")
                    break
                else:
                    print(f"❌ {i}. {selector}: não encontrado")
            except Exception as e:
                print(f"💥 {i}. {selector}: erro - {e}")
        
        if not title_link:
            print("\n❌ NENHUM LINK ENCONTRADO")
            print("Vou tentar encontrar qualquer link no card:")
            
            all_links = card.find_elements(By.CSS_SELECTOR, 'a')
            for i, link in enumerate(all_links):
                href = link.get_attribute('href')
                text = link.text.strip()[:50]
                print(f"   Link {i+1}: {href} - \"{text}\"")
            return
        
        job_url = title_link.get_attribute('href')
        print(f"\n🎯 URL DA VAGA: {job_url}")
        
        if not job_url:
            print("❌ URL vazia")
            return
        
        print(f"\n🚀 NAVEGANDO PARA PÁGINA DA VAGA...")
        print("-" * 40)
        
        # Navigate to job page
        driver.get(job_url)
        time.sleep(5)
        
        print(f"📍 Navegou para: {driver.current_url}")
        print(f"📝 Título da página: {driver.title}")
        
        print(f"\n🔍 PROCURANDO DESCRIÇÃO NA PÁGINA:")
        print("-" * 40)
        
        # Test description selectors on job page
        job_page_selectors = [
            '.jobs-description__content .jobs-box__html-content',
            '.jobs-description__content', 
            'article.jobs-description__container .jobs-description__content',
            '.job-details-jobs-unified-top-card__job-description',
            '.jobs-box--fadein .jobs-description__content',
            '.jobs-box__html-content',
            '[class*="jobs-description"]',
            '[class*="job-details"]'
        ]
        
        found_description = False
        
        for i, selector in enumerate(job_page_selectors, 1):
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    text = elements[0].text.strip()
                    if len(text) > 50:
                        print(f"✅ {i}. {selector}: {len(text)} chars")
                        print(f"   📝 Amostra: {text[:200]}...")
                        found_description = True
                        break
                    else:
                        print(f"⚠️ {i}. {selector}: texto muito curto ({len(text)} chars)")
                else:
                    print(f"❌ {i}. {selector}: não encontrado")
            except Exception as e:
                print(f"💥 {i}. {selector}: erro - {e}")
        
        if not found_description:
            print("\n❌ NENHUMA DESCRIÇÃO ENCONTRADA")
            print("Vou mostrar todo o texto da página:")
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            print(f"Texto total da página ({len(body_text)} chars):")
            print(body_text[:500] + "...")
        
    except Exception as e:
        print(f"💥 Erro durante debug: {e}")
    
    finally:
        print(f"\n✅ Pressione Enter para fechar o browser...")
        input()
        driver.quit()

if __name__ == "__main__":
    debug_individual_page_navigation()
