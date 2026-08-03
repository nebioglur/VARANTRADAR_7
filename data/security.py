import os
import json
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class APIKeyVault:
    """
    CFG-03.1 — API KEY VAULT (Security Engine)
    
    Tüm API anahtarlarını şifreli olarak saklar.
    Açık metin olarak `.env` veya kod içinde anahtar bulundurmayı engeller.
    """
    
    def __init__(self):
        # Gerçek bir kurumsal yapıda master password dışarıdan (KMS vb.) gelir.
        # Bu prototip için makineye özel bir tuz (salt) kullanıyoruz.
        self._salt = b"varant_radar_enterprise_salt_123"
        self._vault_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            ".vault", 
            "api_keys.enc"
        )
        os.makedirs(os.path.dirname(self._vault_file), exist_ok=True)
        self._fernet = self._init_fernet()
        self._keys = self._load_vault()
        
    def _init_fernet(self) -> Fernet:
        # Kurumsal şifreleme türetici
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
        )
        # Sadece bu makineye özgü (şimdilik statik) bir şifre
        key = base64.urlsafe_b64encode(kdf.derive(b"v-radar-master-key"))
        return Fernet(key)
        
    def _load_vault(self) -> dict:
        if not os.path.exists(self._vault_file):
            return {}
        try:
            with open(self._vault_file, "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data)
        except Exception as e:
            print(f"[APIKeyVault] Vault çözme hatası: {e}")
            return {}
            
    def _save_vault(self):
        try:
            data_bytes = json.dumps(self._keys).encode('utf-8')
            encrypted_data = self._fernet.encrypt(data_bytes)
            with open(self._vault_file, "wb") as f:
                f.write(encrypted_data)
        except Exception as e:
            print(f"[APIKeyVault] Vault yazma hatası: {e}")
            
    def set_key(self, provider_name: str, api_key: str):
        """Yeni bir API anahtarını kasaya şifreleyerek kaydeder."""
        self._keys[provider_name.upper()] = api_key
        self._save_vault()
        
    def get_key(self, provider_name: str) -> Optional[str]:
        """İstenilen sağlayıcının API anahtarını kasadan döner."""
        # Eğer sistem değişkeni (Environment Variable) varsa onu öncele
        env_key = os.environ.get(f"{provider_name.upper()}_API_KEY")
        if env_key:
            return env_key
            
        return self._keys.get(provider_name.upper())

# Singleton instance
Vault = APIKeyVault()
