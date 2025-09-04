#!/usr/bin/env python3
"""
Debug específico para encontrar seletores corretos de descrição
baseado na análise DOM do usuário sobre spans com parágrafos
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

def debug_description_selectors():
    """Debug selectors específicos para descrições em spans com parágrafos"""
    
    print("🔍 DEBUG: SELETORES DE DESCRIÇÃO ESPECÍFICOS")
    print("=" * 60)
    
    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Create unique profile directory
    profile_dir = f"/tmp/chrome_profile_debug_{int(time.time())}"
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
        cards = driver.find_elements(By.CSS_SELECTOR, '.job-search-card')
        print(f"✅ Encontrados {len(cards)} job cards")
        
        if not cards:
            print("❌ Nenhum job card encontrado")
            return
            
        # Analyze first card in detail
        card = cards[0]
        print(f"\n🔹 ANALISANDO PRIMEIRO JOB CARD:")
        print("=" * 40)
        
        # Get title for reference
        try:
            title = card.find_element(By.CSS_SELECTOR, '.base-search-card__title').text.strip()
            print(f"📝 Título: {title}")
        except:
            print("⚠️ Título não encontrado")
        
        # Test all possible description selectors based on user's DOM analysis
        desc_selectors = [
            # Based on user's analysis: spans with paragraphs
            'span p',
            '.job-search-card span p', 
            '.base-search-card span p',
            'div[data-max-lines] span p',
            'span[data-max-lines] p',
            
            # More specific span selectors
            '.job-search-card__description span p',
            '.base-search-card__description span p',
            '.job-search-card__summary span p',
            '.base-search-card__summary span p',
            
            # General description containers
            '.job-search-card__description',
            '.base-search-card__description', 
            '.job-search-card__summary',
            '.base-search-card__summary',
            
            # Span containers with text
            'span[data-max-lines]',
            'div[data-max-lines] span',
            '.job-search-card span[class*="description"]',
            '.base-search-card span[class*="description"]',
            
            # Inspect all spans for content
            'span'
        ]
        
        print(f"\n📋 TESTANDO {len(desc_selectors)} SELETORES:")
        print("-" * 40)
        
        found_descriptions = []
        
        for i, selector in enumerate(desc_selectors, 1):
            try:
                elements = card.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    texts = []
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) > 20:  # Meaningful content only
                            texts.append(text)
                    
                    if texts:
                        print(f"✅ {i:2d}. {selector}")
                        for j, text in enumerate(texts[:2]):  # Show first 2 results
                            print(f"     └─ Text {j+1}: {text[:100]}{'...' if len(text) > 100 else ''}")
                        
                        found_descriptions.append({
                            'selector': selector,
                            'texts': texts,
                            'count': len(texts)
                        })
                    else:
                        print(f"⚠️ {i:2d}. {selector} (found elements but no meaningful text)")
                else:
                    print(f"❌ {i:2d}. {selector} (no elements)")
            except Exception as e:
                print(f"💥 {i:2d}. {selector} (error: {str(e)[:50]})")
        
        print(f"\n📊 RESUMO:")
        print(f"🎯 {len(found_descriptions)} seletores com conteúdo encontrados")
        
        if found_descriptions:
            print(f"\n🏆 MELHORES CANDIDATOS:")
            # Sort by text length (longer = more likely to be description)
            sorted_desc = sorted(found_descriptions, key=lambda x: max(len(t) for t in x['texts']), reverse=True)
            
            for i, desc in enumerate(sorted_desc[:3], 1):
                max_text = max(desc['texts'], key=len)
                print(f"{i}. {desc['selector']} ({len(max_text)} chars)")
                print(f"   └─ {max_text[:150]}{'...' if len(max_text) > 150 else ''}")
        
    except Exception as e:
        print(f"💥 Erro durante debug: {e}")
    
    finally:
        driver.quit()
        print(f"\n✅ Debug concluído")

if __name__ == "__main__":
    debug_description_selectors()
