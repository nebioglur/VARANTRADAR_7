import sqlite3
import requests
import json

try:
    conn = sqlite3.connect('database/varantradar.db')
    c = conn.cursor()
    c.execute("SELECT setting_value FROM settings WHERE setting_key='telegram_token'")
    row = c.fetchone()
    if row and row[0]:
        token = row[0]
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        print("RESULT:", r.json())
    else:
        print("RESULT: Token bulunamadi.")
except Exception as e:
    print("ERROR:", e)
