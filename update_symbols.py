import requests
import json
import os

def update_symbols():
    print("Borsa İstanbul güncel hisse listesi çekiliyor (TradingView)...")
    url = "https://scanner.tradingview.com/turkey/scan"
    payload = {
        "columns": ["name"],
        "filter": [{"left": "type", "operation": "in_range", "right": ["stock"]}],
        "options": {"lang": "en"}
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        # TradingView returns data like {"data": [{"d": ["THYAO"]}, ...]}
        # We append .IS for Yahoo Finance
        symbols = [item['d'][0] + '.IS' for item in data['data']]
        symbols.sort()
        
        # Sadece harf ve rakamdan oluşan hisseleri (BIST) alalım, bazı özel fonları atlayalım
        valid_symbols = [s for s in symbols if len(s.split('.')[0]) >= 3]
        
        print(f"Toplam {len(valid_symbols)} adet hisse bulundu. Dosya güncelleniyor...")
        
        # config/bist_symbols.py dosyasını okuyup BIST_SYMBOLS listesini güncelleyeceğiz
        config_path = "config/bist_symbols.py"
        
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Eski BIST_SYMBOLS listesini tamamen değiştiriyoruz
        # Ama GLOBAL_SYMBOLS ve diğerlerini bozmamamız lazım.
        # Bu yüzden sıfırdan bir dosya oluşturmak daha güvenli:
        
        new_content = f'''# Borsa İstanbul (BIST) Güncel Hisse Listesi (Otomatik Çekildi)
# Toplam: {len(valid_symbols)} Hisse

BIST_SYMBOLS = [
'''
        
        # Hisseleri 10'arlı gruplar halinde formatla
        for i in range(0, len(valid_symbols), 10):
            chunk = valid_symbols[i:i+10]
            line = "    " + ", ".join([f'"{s}"' for s in chunk]) + ",\n"
            new_content += line
            
        new_content += "]\n\n"
        
        new_content += '''# Macro and Index symbols
MACRO_SYMBOLS = {
    "BIST100": "XU100.IS",
    "USD/TRY": "TRY=X",
    "EUR/TRY": "EURTRY=X",
    "GOLD": "GC=F",
    "SILVER": "SI=F"
}

# V11 - Global Market Symbols (Örnek)
GLOBAL_SYMBOLS = [
    "AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "GOOGL",
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
    "EURUSD=X", "GBPUSD=X", "JPY=X"
]

ALL_GLOBAL_SYMBOLS = BIST_SYMBOLS + list(MACRO_SYMBOLS.values()) + GLOBAL_SYMBOLS
'''
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        print("BIST hisseleri başarıyla güncellendi!")
    else:
        print("Hata:", response.status_code)

if __name__ == "__main__":
    update_symbols()
