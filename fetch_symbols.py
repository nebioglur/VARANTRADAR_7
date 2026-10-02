import requests
import json
import re

url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/default.aspx"
headers = {"User-Agent": "Mozilla/5.0"}
try:
    response = requests.get(url, headers=headers)
    matches = re.findall(r'"value":"([A-Z0-9]{4,5})"', response.text)
    if matches:
        symbols = sorted(list(set(matches)))
        print(f"Found {len(symbols)} symbols.")
        with open("all_bist.txt", "w", encoding="utf-8") as f:
            for s in symbols:
                f.write(s + ".IS\n")
    else:
        print("No symbols found.")
except Exception as e:
    print(f"Error: {e}")
