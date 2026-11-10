# -*- coding: utf-8 -*-
with open("services/market_data.py", "r", encoding="utf-8") as f:
    code = f.read()

replacement = """                try:
                    cursor.executemany(insert_sql, all_rows)
                except Exception as e:
                    print(f"[CRITICAL] MarketData executemany hatasi: {e}")
                    try:
                        from services.telegram_bot import send_telegram_message
                        send_telegram_message(f"🚨 SIMULASYON VERI YAZMA HATASI!\\nMarket verileri (intraday) DB'ye yazilamadi!\\nHata: {e}")
                    except:
                        pass"""

code = code.replace("""                try:
                    cursor.executemany(insert_sql, all_rows)
                except Exception:
                    pass""", replacement)

with open("services/market_data.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patched market_data.py")
