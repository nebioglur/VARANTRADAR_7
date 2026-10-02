# VarantRadar X - Python SDK (Developer Platform - Modül 11)
import requests

class VarantRadar:
    """
    VarantRadar X API'sine bağlanmak için Kurumsal Python SDK'sı.
    """
    def __init__(self, api_key: str, base_url: str = 'http://localhost:8000/api/v1'):
        self.api_key = api_key
        self.base_url = base_url

    def analyze(self, symbol: str, interval: str = "1d") -> dict:
        """Belirtilen hisse/kripto/emtia için yapay zeka analiz raporu döndürür."""
        headers = {'Authorization': f'Bearer {self.api_key}'}
        payload = {'symbol': symbol, 'interval': interval}
        
        response = requests.post(f'{self.base_url}/analyze', json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
