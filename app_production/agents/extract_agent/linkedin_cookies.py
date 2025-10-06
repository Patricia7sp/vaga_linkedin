"""
LinkedIn Cookie Manager for persistent sessions with GCS support
"""
import pickle
import os
import json
import subprocess
import tempfile
from pathlib import Path

# GCP Storage
try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

class LinkedInCookieManager:
    def __init__(self):
        self.cookie_file = Path.home() / '.linkedin_cookies.pkl'
        self.gcs_bucket = "linkedin-dados-raw"
        self.gcs_cookie_path = "auth/linkedin_cookies.pkl"
    
    def save_cookies(self, driver):
        """Save cookies from current session locally AND to GCS"""
        try:
            cookies = driver.get_cookies()
            
            # Save locally first
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            print("🍪 Cookies salvos localmente")
            
            # ENHANCED: Save to GCS for persistence across containers
            self._upload_cookies_to_gcs()
            
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar cookies: {e}")
            return False
    
    def load_cookies(self, driver):
        """Load saved cookies into driver from GCS or local storage"""
        try:
            # ENHANCED: Try to download cookies from GCS first
            self._download_cookies_from_gcs()
            
            if not self.cookie_file.exists():
                print("⚠️ Arquivo de cookies não encontrado localmente nem no GCS")
                return False
                
            # First navigate to LinkedIn to set domain
            driver.get("https://www.linkedin.com")
            
            # Load and add cookies
            with open(self.cookie_file, 'rb') as f:
                cookies = pickle.load(f)
                
            for cookie in cookies:
                # LinkedIn cookies might have sameSite attribute that Selenium doesn't like
                if 'sameSite' in cookie:
                    del cookie['sameSite']
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
        """Remove saved cookies file locally and from GCS"""
        try:
            # Clear local
            if self.cookie_file.exists():
                self.cookie_file.unlink()
                print("🗑️ Cookies locais removidos")
            
            # Clear GCS
            self._delete_cookies_from_gcs()
            
            return True
        except Exception as e:
            print(f"❌ Erro ao remover cookies: {e}")
            return False
    
    def _upload_cookies_to_gcs(self):
        """Upload cookies to GCS bucket for persistence"""
        try:
            if not self.cookie_file.exists():
                return False
                
            # Try with gsutil first (available in containers)
            result = subprocess.run([
                "gsutil", "cp", str(self.cookie_file), f"gs://{self.gcs_bucket}/{self.gcs_cookie_path}"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("☁️ Cookies salvos no GCS via gsutil")
                return True
            
            # Fallback: try with google-cloud-storage
            if GCS_AVAILABLE:
                client = storage.Client()
                bucket = client.bucket(self.gcs_bucket)
                blob = bucket.blob(self.gcs_cookie_path)
                blob.upload_from_filename(str(self.cookie_file))
                print("☁️ Cookies salvos no GCS via biblioteca")
                return True
                
        except Exception as e:
            print(f"⚠️ Não foi possível salvar cookies no GCS: {e}")
            
        return False
    
    def _download_cookies_from_gcs(self):
        """Download cookies from GCS bucket"""
        try:
            # Try with gsutil first
            result = subprocess.run([
                "gsutil", "cp", f"gs://{self.gcs_bucket}/{self.gcs_cookie_path}", str(self.cookie_file)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("☁️ Cookies baixados do GCS via gsutil")
                return True
            
            # Fallback: try with google-cloud-storage
            if GCS_AVAILABLE:
                client = storage.Client()
                bucket = client.bucket(self.gcs_bucket)
                blob = bucket.blob(self.gcs_cookie_path)
                
                if blob.exists():
                    blob.download_to_filename(str(self.cookie_file))
                    print("☁️ Cookies baixados do GCS via biblioteca")
                    return True
                    
        except Exception as e:
            print(f"⚠️ Não foi possível baixar cookies do GCS: {e}")
            
        return False
    
    def _delete_cookies_from_gcs(self):
        """Delete cookies from GCS bucket"""
        try:
            # Try with gsutil first
            result = subprocess.run([
                "gsutil", "rm", f"gs://{self.gcs_bucket}/{self.gcs_cookie_path}"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("🗑️ Cookies removidos do GCS")
                return True
                
        except Exception as e:
            print(f"⚠️ Erro ao remover cookies do GCS: {e}")
            
        return False
