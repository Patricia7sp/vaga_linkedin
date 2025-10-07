"""
LinkedIn Cookie Manager for persistent sessions
"""

import os
import pickle
from pathlib import Path


class LinkedInCookieManager:
    def __init__(self):
        self.cookie_file = Path.home() / ".linkedin_cookies.pkl"

    def save_cookies(self, driver):
        """Save cookies from current session"""
        try:
            cookies = driver.get_cookies()
            with open(self.cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            print("🍪 Cookies salvos com sucesso")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar cookies: {e}")
            return False

    def load_cookies(self, driver):
        """Load saved cookies into driver"""
        try:
            if not self.cookie_file.exists():
                print("⚠️ Arquivo de cookies não encontrado")
                return False

            # First navigate to LinkedIn to set domain
            driver.get("https://www.linkedin.com")

            # Load and add cookies
            with open(self.cookie_file, "rb") as f:
                cookies = pickle.load(f)

            for cookie in cookies:
                # LinkedIn cookies might have sameSite attribute that Selenium doesn't like
                if "sameSite" in cookie:
                    del cookie["sameSite"]
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"⚠️ Cookie ignorado: {e}")

            print("🍪 Cookies carregados com sucesso")

            # Refresh to apply cookies
            driver.refresh()
            return True

        except Exception as e:
            print(f"❌ Erro ao carregar cookies: {e}")
            return False

    def clear_cookies(self):
        """Remove saved cookies file"""
        try:
            if self.cookie_file.exists():
                self.cookie_file.unlink()
                print("🗑️ Cookies removidos")
            return True
        except Exception as e:
            print(f"❌ Erro ao remover cookies: {e}")
            return False
